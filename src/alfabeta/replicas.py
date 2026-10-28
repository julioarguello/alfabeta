"""Placing the run's material in the student's base folder (spec 001 T041, FR-015…FR-019, FR-025).

`apply` takes the newest capture of each class in scope, places each statement and material file
the run collected, writes the notes (descriptions, statements, links, announcements), and records
every replica in the state. A file identical to its replica is only deleted from `data/`; a file
that changed keeps the previous one beside it as «<name> (anterior YYYY-MM-DD)» (FR-015b). An
attachment that never arrived is noted in its item's `enlaces.md` as «no traído». Whatever the
scope, every replica is placed again with the decisions in force, from the last version of its
item kept in the state, so a match confirmed after a first run moves files instead of copying them.
Nothing is written outside the base folder, and no message shows an absolute path (FR-031).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import shutil
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, cast

from alfabeta import capture
from alfabeta.model import (
    Attachment,
    AttachmentKind,
    AttachmentRole,
    Grading,
    GradingState,
    Item,
    ItemStatus,
    ItemType,
    ReplicaRole,
    Subject,
)
from alfabeta.placement import Placer, Target
from alfabeta.plan import PLACED_ROLES
from alfabeta.sources import CLASSROOM
from alfabeta.state import write_atomic

if TYPE_CHECKING:
    from collections.abc import Iterable

    from alfabeta.decisions import DecisionStore

NOT_ARRIVED = "no llegó a la carpeta de descargas"
# Roles whose replica is a downloaded file.
_FILE_ROLES = frozenset({ReplicaRole.STATEMENT, ReplicaRole.MATERIAL, ReplicaRole.SUBMISSION})


def sha256(path: Path) -> str:
    """The file's SHA-256."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 16), b""):
            digest.update(block)
    return digest.hexdigest()


def link_of(attachment: Attachment) -> str:
    """Where an attachment can be opened (with the school account)."""
    if attachment.kind == AttachmentKind.VIDEO and not attachment.id.startswith("http"):
        return f"https://www.youtube.com/watch?v={attachment.id}"
    if attachment.kind == AttachmentKind.FILE:
        return f"https://drive.google.com/file/d/{attachment.id}/view"
    if attachment.kind == AttachmentKind.GOOGLE_DOC:
        return f"https://drive.google.com/open?id={attachment.id}"
    if attachment.kind == AttachmentKind.FORM and not attachment.id.startswith("http"):
        return f"https://docs.google.com/forms/d/{attachment.id}"
    return attachment.id


def item_to_json(item: Item, topic_title: str | None) -> dict[str, Any]:
    """The last normalized version of an item, as the state keeps it."""

    def attachments(found: tuple[Attachment, ...]) -> list[dict[str, str]]:
        return [{"id": a.id, "kind": str(a.kind), "name": a.name, "role": str(a.role)} for a in found]

    return {
        "id": item.id,
        "class_id": item.class_id,
        "topic_id": item.topic_id,
        "topic_title": topic_title,
        "type": str(item.type),
        "title": item.title,
        "posted_at": item.posted_at.isoformat(),
        "modified_at": item.modified_at.isoformat() if item.modified_at else None,
        "status": str(item.status) if item.status else None,
        "description": item.description,
        "attachments": attachments(item.attachments),
        "submission": attachments(item.submission),
        "grading": str(item.grading.grading_state) if item.grading else None,
    }


def item_from_json(raw: dict[str, Any]) -> tuple[Item, str | None]:
    """An item back from the state, with its teacher's topic title."""

    def attachments(found: list[dict[str, str]]) -> tuple[Attachment, ...]:
        return tuple(
            Attachment(a["id"], AttachmentKind(a["kind"]), a["name"], AttachmentRole(a["role"])) for a in found
        )

    item = Item(
        id=raw["id"],
        class_id=raw["class_id"],
        topic_id=raw["topic_id"],
        type=ItemType(raw["type"]),
        title=raw["title"],
        posted_at=dt.date.fromisoformat(raw["posted_at"]),
        modified_at=dt.date.fromisoformat(raw["modified_at"]) if raw.get("modified_at") else None,
        status=ItemStatus(raw["status"]) if raw.get("status") else None,
        description=raw.get("description", ""),
        attachments=attachments(raw.get("attachments", [])),
        submission=attachments(raw.get("submission", [])),
        grading=Grading(GradingState(raw["grading"])) if raw.get("grading") else None,
    )
    return item, raw.get("topic_title")


def _previous_name(path: Path, today: dt.date) -> Path:
    return path.with_name(f"{path.stem} (anterior {today.isoformat()}){path.suffix}")


@dataclass
class Applier:
    """Places one run's material for one student."""

    base: Path
    data_dir: Path
    school_year: str
    subjects: list[Subject]
    decisions: DecisionStore
    state: dict[str, Any]
    today: dt.date
    downloads: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])
    added: int = 0
    changed: int = 0
    not_fetched: dict[str, str] = field(default_factory=dict[str, str])
    unknown_statuses: int = 0
    unreadable: list[str] = field(default_factory=list[str])

    @property
    def replicas(self) -> dict[str, Any]:
        """`state.json` «replicas»: `<source>|<item>|<attachment>` → its record."""
        return cast("dict[str, Any]", self.state.setdefault("replicas", {}))

    @property
    def items(self) -> dict[str, Any]:
        """`state.json` «items»: the last normalized version of each item."""
        return cast("dict[str, Any]", self.state.setdefault("items", {}))

    def _inbox(self, item: str, attachment: str) -> Path | None:
        for download in self.downloads:
            if download["item"] == item and download["attachment"] == attachment:
                path = self.data_dir / "inbox" / f"{item}__{attachment}" / str(download["expected_name"])
                return path if path.is_file() else None
        return None

    def _write_note(self, relative: str, text: str) -> bool:
        path = self.base / relative
        if path.is_file() and path.read_text() == text:
            return False
        path.parent.mkdir(parents=True, exist_ok=True)
        return write_atomic(path, text)

    def _move(self, record: dict[str, Any], relative: str) -> None:
        """Move a replica whose target changed; never a second copy."""
        old = self.base / str(record["path"])
        new = self.base / relative
        if old == new or not old.exists():
            record["path"] = relative
            return
        new.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old), new)
        record["path"] = relative
        self.changed += 1

    def _place_file(self, item: Item, target: Target, attachment: Attachment) -> bool:
        """Place one collected file; False if it never arrived."""
        key = f"{CLASSROOM}|{item.id}|{attachment.id}"
        record = cast("dict[str, Any] | None", self.replicas.get(key))
        if record is not None:
            self._move(record, target.path)
        incoming = self._inbox(item.id, attachment.id)
        if incoming is None:
            return record is not None
        digest = sha256(incoming)
        destination = self.base / target.path
        if record is not None and record.get("hash") == digest and destination.exists():
            incoming.unlink()  # verified identical: nothing to write
            return True
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            shutil.move(str(destination), _previous_name(destination, self.today))
        shutil.move(str(incoming), destination)
        self.replicas[key] = {
            "role": str(target.role),
            "path": target.path,
            "hash": digest,
            "version": int(record["version"]) + 1 if record else 1,
            "name": attachment.name,
            "kind": str(attachment.kind),
            "modified_seen": item.modified_at.isoformat() if item.modified_at else None,
        }
        if record is None:
            self.added += 1
        else:
            self.changed += 1
        return True

    def _note_record(self, item: Item, target: Target, text: str) -> None:
        key = f"{CLASSROOM}|{item.id}|#{target.role}"
        record = cast("dict[str, Any] | None", self.replicas.get(key))
        if record is not None and record.get("path") != target.path:
            old = self.base / str(record["path"])
            if old.exists():
                old.unlink()
        if self._write_note(target.path, text):
            if record is None:
                self.added += 1
            else:
                self.changed += 1
        self.replicas[key] = {
            "role": str(target.role),
            "path": target.path,
            "hash": hashlib.sha256(text.encode()).hexdigest(),
        }

    def place_item(self, placer: Placer, item: Item, topic_title: str | None) -> None:
        """Every file a run places for one item."""
        targets = [t for t in placer.place(item, topic_title) if t.role in PLACED_ROLES]
        by_id = {a.id: a for a in (*item.attachments, *item.submission)}
        missing: list[Attachment] = []
        for target in targets:
            if target.attachment and target.role in _FILE_ROLES:
                attachment = by_id[target.attachment]
                if not self._place_file(item, target, attachment):
                    missing.append(attachment)
                    self.not_fetched[f"{item.id}|{attachment.id}"] = NOT_ARRIVED
        links = [a for a in item.attachments if not a.downloaded]
        for target in targets:
            if target.role == ReplicaRole.LINKS or (
                missing and target.role in (ReplicaRole.MATERIAL, ReplicaRole.STATEMENT)
            ):
                continue
            if target.role in (ReplicaRole.DESCRIPTION, ReplicaRole.ANNOUNCEMENT):
                self._note_record(item, target, f"{item.description.strip()}\n")
        if links or missing:
            folder = _links_folder(targets)
            if folder is not None:
                self._note_record(
                    item, Target(ReplicaRole.LINKS, "", f"{folder}/enlaces.md"), _links_note(item, links, missing)
                )
        self.items[item.id] = item_to_json(item, topic_title)

    def apply(self, captures: dict[str, dict[str, Any]], scope: Iterable[str], links: dict[str, Subject]) -> list[str]:
        """Apply the classes in scope; then move every other replica a decision changed. Returns the classes applied."""
        applied: list[str] = []
        placers: dict[str, Placer] = {}
        for class_id in sorted(scope):
            raw, subject = captures.get(class_id), links.get(class_id)
            if raw is None or subject is None:
                continue
            try:
                normalized = capture.normalize_class(raw, self.school_year)
            except (capture.CaptureError, KeyError, TypeError, ValueError):
                self.unreadable.append(class_id)  # FR-029: one class does not stop the others
                continue
            placer = placers.setdefault(subject.folder, self._placer(subject))
            self.unknown_statuses += len(normalized.unknown_statuses)
            for item in sorted(normalized.items, key=lambda i: (i.posted_at, i.id)):
                self.place_item(placer, item, normalized.topics.get(item.topic_id or ""))
            applied.append(class_id)
        for raw in sorted(self.items.values(), key=lambda r: (r["posted_at"], r["id"])):
            if raw["class_id"] in applied or raw["class_id"] not in links:
                continue
            subject = links[raw["class_id"]]
            placer = placers.setdefault(subject.folder, self._placer(subject))
            item, topic_title = item_from_json(raw)
            self._replace(placer, item, topic_title)
        return applied

    def _replace(self, placer: Placer, item: Item, topic_title: str | None) -> None:
        """Move the replicas of an item outside the scope to where the decisions in force put them."""
        for target in placer.place(item, topic_title):
            if target.role not in PLACED_ROLES:
                continue
            suffix = target.attachment or f"#{target.role}"
            record = cast("dict[str, Any] | None", self.replicas.get(f"{CLASSROOM}|{item.id}|{suffix}"))
            if record is not None:
                self._move(record, target.path)

    def _placer(self, subject: Subject) -> Placer:
        subject_dir = self.base / self.school_year / subject.folder
        existing = [p.name for p in subject_dir.iterdir() if p.is_dir()] if subject_dir.is_dir() else []
        return Placer(self.school_year, subject, existing, self.decisions.decisions())


def _links_folder(targets: list[Target]) -> str | None:
    """The item's own folder, where `enlaces.md` goes.

    A one-file material is the file itself, with no folder; when that file did not arrive, the note
    goes in a folder named as the file would have been, so the missing attachment is still noted.
    """
    for target in targets:
        if target.role == ReplicaRole.LINKS:
            return str(PurePosixPath(target.path).parent)
    files = [PurePosixPath(t.path) for t in targets if t.role in (ReplicaRole.STATEMENT, ReplicaRole.MATERIAL)]
    if not files:
        handed = [PurePosixPath(t.path) for t in targets if t.role == ReplicaRole.SUBMISSION]
        return str(handed[0].parent.parent) if handed else None
    if files[0].parent.name == CLASSROOM:
        return str(files[0].parent / files[0].stem)
    return str(files[0].parent)


def _links_note(item: Item, links: list[Attachment], missing: list[Attachment]) -> str:
    """`enlaces.md`: title, date and link of what is not downloaded, and what did not arrive (FR-017, FR-019)."""
    day = item.posted_at.strftime("%d/%m/%Y")
    lines = ["# Enlaces", ""]
    lines += [f"- [{a.name}]({link_of(a)}) · {day}" for a in links]
    lines += [f"- [{a.name}]({link_of(a)}) · {day} · no traído: {NOT_ARRIVED}" for a in missing]
    return "\n".join(lines) + "\n"
