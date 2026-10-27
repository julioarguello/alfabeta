"""Classroom captures → domain items (spec 001 T037, contracts/capture.schema.json, data-model.md).

A capture holds the texts exactly as Classroom shows them; this module interprets them: dates
through `DateResolver`, and the status of an assignment or question from its detail page, never
from the listing (FR-008a), with the table of data-model.md «Status from the detail texts». The
essential keys are checked by hand, so reading a capture needs no dependency.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from alfabeta.dates import MADRID, DateError, DateResolver
from alfabeta.model import (
    Attachment,
    AttachmentKind,
    AttachmentRole,
    Grading,
    GradingState,
    Item,
    ItemStatus,
    ItemType,
)

if TYPE_CHECKING:
    from pathlib import Path

CAPTURE_TYPES = frozenset({"classes", "class", "stop"})
_ESSENTIAL = ("version", "type", "run", "captured_at")
_ESSENTIAL_CLASS = ("complete", "class", "topics", "items", "stream")
# «Publicado: 6 oct», «Fecha de creación: 23 oct», «Última modificación: 8 oct»: a label before the date.
_LABEL = re.compile(r"^[^\d:]+:\s*")
_MODIFIED = re.compile(r"\(\s*última modificación:\s*([^)]*)\)", re.IGNORECASE)
_NO_DUE = "sin fecha de entrega"

# data-model.md, «Status from the detail texts».
# Nothing turned in yet: pending until the due date passes, overdue after it. «Sin entregar» is what a
# question shows (seen on 2026-10-25); the operator set its meaning on 2026-10-27.
_WAITING = frozenset({"asignado", "falta", "sin entregar"})
_TURNED_IN = frozenset({"entregado", "entregado con retraso"})
_RETURNED = frozenset({"calificado", "devuelto"})
_MISSING_NOTICE = "falta esto"
_TITLE_CHARS = 100


class CaptureError(ValueError):
    """A capture that does not have the shape of the contract."""


@dataclass(frozen=True)
class ClassCapture:
    """One class, normalized: its items and what could not be interpreted."""

    class_id: str
    title: str
    run: str
    captured_at: dt.datetime
    complete: bool
    topics: dict[str, str]
    items: tuple[Item, ...]
    unknown_statuses: tuple[str, ...] = ()
    unreadable: tuple[str, ...] = field(default=())


def read(path: Path) -> dict[str, Any]:
    """A capture file, with its essential keys checked."""
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as err:
        raise CaptureError("the capture is not readable JSON") from err
    return check(data)


def check(data: object) -> dict[str, Any]:
    """The capture if its essential keys are there; CaptureError naming the first missing one."""
    if not isinstance(data, dict):
        raise CaptureError("a capture is a JSON object")
    capture = cast("dict[str, Any]", data)
    for key in _ESSENTIAL:
        if key not in capture:
            raise CaptureError(f"the capture has no {key!r}")
    if capture["version"] != 1 or capture["type"] not in CAPTURE_TYPES:
        raise CaptureError("unknown capture version or type")
    if capture["type"] == "class":
        for key in _ESSENTIAL_CLASS:
            if key not in capture:
                raise CaptureError(f"the class capture has no {key!r}")
    return capture


def captured_at(capture: dict[str, Any]) -> dt.datetime:
    """The capture's instant, in Madrid."""
    moment = dt.datetime.fromisoformat(capture["captured_at"].replace("Z", "+00:00"))
    if moment.tzinfo is None:
        raise CaptureError("captured_at carries no time zone")
    return moment.astimezone(MADRID)


def _strip_label(text: str) -> str:
    return _LABEL.sub("", text.strip(), count=1)


def _date(resolver: DateResolver, text: str | None) -> dt.date | None:
    if not text or text.strip().lower() == _NO_DUE:
        return None
    value = resolver.resolve(_strip_label(text))
    return value.date() if isinstance(value, dt.datetime) else value


def _due(resolver: DateResolver, text: str | None) -> dt.datetime | dt.date | None:
    if not text or _strip_label(text).lower() == _NO_DUE or text.strip().lower() == _NO_DUE:
        return None
    return resolver.resolve(_strip_label(text))


def _is_past(due: dt.datetime | dt.date | None, now: dt.datetime) -> bool:
    if due is None:
        return False
    if isinstance(due, dt.datetime):
        return due < now
    return due < now.date()


def status_of(detail: dict[str, Any], due: dt.datetime | dt.date | None, now: dt.datetime) -> ItemStatus | None:
    """The table of data-model.md; None when Classroom shows a text the table does not know."""
    notice = (detail.get("status_notice_text") or "").lower()
    if _MISSING_NOTICE in notice:
        return ItemStatus.MISSING_PER_TEACHER
    text = (detail.get("status_text") or "").strip().lower()
    if text in _WAITING:
        return ItemStatus.OVERDUE if _is_past(due, now) else ItemStatus.PENDING
    if text in _TURNED_IN:
        return ItemStatus.TURNED_IN
    if text in _RETURNED:
        return ItemStatus.RETURNED
    return None


def _attachments(raw: object, role: AttachmentRole) -> tuple[Attachment, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(
        Attachment(str(a["id"]), AttachmentKind(a["kind"]), str(a["name"]), role)
        for a in cast("list[dict[str, Any]]", raw)
    )


def _grading(resolver: DateResolver, detail: dict[str, Any]) -> Grading | None:
    text = (detail.get("status_text") or "").strip().lower()
    if text not in _RETURNED:
        return None
    return Grading(
        GradingState.GRADED if text == "calificado" else GradingState.RETURNED,
        grade=detail.get("grade_text") or "",
        max_points=detail.get("points") or "",
        teacher_comment=detail.get("teacher_comment") or "",
        returned_at=_date(resolver, detail.get("returned_text")),
    )


def _item(raw: dict[str, Any], class_id: str, resolver: DateResolver, now: dt.datetime) -> tuple[Item, bool]:
    """The item and whether its status text was unknown."""
    kind = ItemType(raw["type"])
    detail = cast("dict[str, Any] | None", raw.get("detail"))
    if detail is None:
        raise CaptureError("an item has no detail")
    listing_modified = _MODIFIED.search(raw.get("listing_date_text") or "")
    modified_text = detail.get("modified_text") or (listing_modified.group(1) if listing_modified else None)
    due = _due(resolver, detail.get("due_text"))
    status: ItemStatus | None = None
    unknown = False
    if kind in (ItemType.ASSIGNMENT, ItemType.QUESTION):
        status = status_of(detail, due, now)
        unknown = status is None and bool((detail.get("status_text") or "").strip())
    role = AttachmentRole.MATERIAL if kind == ItemType.MATERIAL else AttachmentRole.STATEMENT
    posted = _date(resolver, detail.get("posted_text"))
    if posted is None:
        raise CaptureError("an item has no posting date")
    item = Item(
        id=str(raw["id"]),
        class_id=class_id,
        topic_id=raw.get("topic"),
        type=kind,
        title=str(raw["title"]),
        posted_at=posted,
        modified_at=_date(resolver, modified_text),
        due_at=due,
        status=status,
        description=detail.get("description") or "",
        attachments=_attachments(detail.get("attachments"), role),
        submission=_attachments(detail.get("submission"), AttachmentRole.SUBMISSION),
        grading=_grading(resolver, detail) if kind in (ItemType.ASSIGNMENT, ItemType.QUESTION) else None,
    )
    return item, unknown


def _announcement(raw: dict[str, Any], class_id: str, resolver: DateResolver) -> Item:
    text = str(raw["text"]).strip()
    posted = _date(resolver, raw["created_text"])
    if posted is None:
        raise CaptureError("an announcement has no creation date")
    first_line = text.splitlines()[0] if text else ""
    return Item(
        id=str(raw["id"]),
        class_id=class_id,
        topic_id=None,
        type=ItemType.ANNOUNCEMENT,
        title=first_line[:_TITLE_CHARS],
        posted_at=posted,
        description=text,
        attachments=_attachments(raw.get("attachments"), AttachmentRole.MATERIAL),
    )


def normalize_class(capture: dict[str, Any], school_year: str) -> ClassCapture:
    """A class capture as domain items; an item that cannot be read is listed, not guessed."""
    check(capture)
    if capture["type"] != "class":
        raise CaptureError("not a class capture")
    now = captured_at(capture)
    resolver = DateResolver(school_year, now)
    class_id = str(capture["class"]["id"])
    items: list[Item] = []
    unknown: list[str] = []
    unreadable: list[str] = []
    for raw in cast("list[dict[str, Any]]", capture["items"]):
        try:
            item, is_unknown = _item(raw, class_id, resolver, now)
        except (CaptureError, DateError, KeyError, ValueError):
            unreadable.append(str(raw.get("id", "")))
            continue
        items.append(item)
        if is_unknown:
            unknown.append(item.id)
    for raw in cast("list[dict[str, Any]]", capture["stream"]):
        try:
            items.append(_announcement(raw, class_id, resolver))
        except (CaptureError, DateError, KeyError, ValueError):
            unreadable.append(str(raw.get("id", "")))
    topics = {
        str(t["id"]): str(t["title"])
        for t in cast("list[dict[str, Any]]", capture["topics"])
        if t.get("id") is not None
    }
    return ClassCapture(
        class_id=class_id,
        title=str(capture["class"]["title"]),
        run=str(capture["run"]),
        captured_at=now,
        complete=bool(capture["complete"]),
        topics=topics,
        items=tuple(items),
        unknown_statuses=tuple(unknown),
        unreadable=tuple(unreadable),
    )
