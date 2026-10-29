"""The student's agenda of one school year (spec 001 T050, FR-020…FR-020c, FR-021, FR-025).

`agenda.json` (contracts/agenda.schema.json, the reminders epic's input) and `agenda.md` (what the
family reads, in Spanish) live in the school-year folder of the student's base folder. Both come
from the state (each item's last normalized version and its replicas), the decisions in force
(detected exams and the family's corrections) and the instant of each class's newest capture in
`data/captures/`. Nothing in them depends on the day they are generated, so they carry no
timestamp, and each file is rewritten only if its bytes change. An item withdrawn from Classroom
(FR-027) is no longer a fact of the agenda, nor is an exam deduced from it.

A notice is a line for the family at the top of `agenda.md` while a condition holds, such as the
notebook owner's session not working (spec 005 FR-019; spec 004 research R9, its third channel). It
is not an entry: `agenda.json` never carries it. Neither do the lines of «Informes de apuntes» at the
end of `agenda.md`, one per report the cloud run left in Drive (spec 005 T036), built from the
Mac's own record of them.
"""

from __future__ import annotations

import datetime as dt
import json
import posixpath
from collections import Counter
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any, cast

from alfabeta import capture
from alfabeta.classification import text_hash
from alfabeta.dates import MADRID
from alfabeta.model import (
    AgendaCategory,
    AgendaEntry,
    AgendaList,
    DecisionState,
    DecisionType,
    ItemStatus,
    ItemType,
    ReplicaRole,
)
from alfabeta.replicas import item_from_json
from alfabeta.sources import CLASSROOM
from alfabeta.state import write_atomic

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from alfabeta.classification import Classifier
    from alfabeta.model import Decision, Item, Subject

VERSION = 1
FILES = ("agenda.json", "agenda.md")
CLASSROOM_URL = "https://classroom.google.com"
# Detail pages per kind (research R3, S3); a stream post has no measured page of its own.
_DETAIL = {ItemType.ASSIGNMENT: "a", ItemType.MATERIAL: "m", ItemType.QUESTION: "mc"}
_DONE = frozenset({ItemStatus.TURNED_IN, ItemStatus.TURNED_IN_LATE, ItemStatus.RETURNED})
_POSTED = frozenset({AgendaCategory.MATERIAL, AgendaCategory.ANNOUNCEMENT})
_LISTS = (AgendaList.PENDING, AgendaList.DONE, AgendaList.POSTED)

# data-model.md, «Language of names»: what the family reads in `agenda.md`.
LIST_NAMES = {AgendaList.PENDING: "Pendiente", AgendaList.DONE: "Hecho", AgendaList.POSTED: "Publicado"}
CATEGORY_NAMES = {
    AgendaCategory.EXAM: "examen",
    AgendaCategory.ASSIGNMENT: "entrega",
    AgendaCategory.QUIZ: "cuestionario",
    AgendaCategory.MATERIAL: "material",
    AgendaCategory.ANNOUNCEMENT: "aviso",
}
STATUS_NAMES = {
    ItemStatus.PENDING: "pendiente",
    ItemStatus.TURNED_IN: "entregada",
    ItemStatus.TURNED_IN_LATE: "entregada tarde",
    ItemStatus.RETURNED: "devuelta",
    ItemStatus.OVERDUE: "vencida",
    ItemStatus.MISSING_PER_TEACHER: "falta según el profesor",
}
DETECTED = "detectado"
CORRECTED = "corregido"
NO_DATE = "sin fecha"
OPEN_WITH = "Los enlaces de Classroom se abren con la cuenta del colegio."
NOTHING = "Nada."
REPORTS = "Informes de apuntes"
_BOXES = {AgendaList.PENDING: "- [ ] ", AgendaList.DONE: "- [x] ", AgendaList.POSTED: "- "}
# Classroom's own abbreviations («13 sept»), as dates.py reads them (FR-021).
_MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic")

When = dt.datetime | dt.date


def classroom_link(item: Item) -> str:
    """Where the item opens in Classroom, without `/u/<n>`: the index is not stable (data-model, Agenda entry).

    Classwork has a detail page per item; for the stream only the class's own page was measured,
    so an announcement links to it.
    """
    stream = f"{CLASSROOM_URL}/c/{item.class_id}"
    kind = _DETAIL.get(item.type)
    return f"{stream}/{kind}/{item.id}/details" if kind else stream


def _end_of(day: dt.date) -> dt.datetime:
    """The end of `day` in Madrid: the first instant of the next one."""
    return dt.datetime.combine(day + dt.timedelta(days=1), dt.time(), MADRID)


def _instant(when: When) -> dt.datetime:
    """The instant a date stands for: its time when Classroom gives one, else the end of that day."""
    return when if isinstance(when, dt.datetime) else _end_of(when)


def later_than(captured: dt.datetime | None, when: When | None) -> bool:
    """Whether a capture is later than an exam's instant or, for a date, the end of that day in Madrid (FR-020c)."""
    if captured is None or when is None:
        return False
    if isinstance(when, dt.datetime):
        return captured > when
    return captured >= _end_of(when)


def _exam_date(text: str | None) -> When | None:
    """A detected exam's date: `YYYY-MM-DD`, an ISO date-time (Madrid when it names no zone), or none.

    A text that is neither reads as no date, the case FR-020b already gives a place: «sin fecha».
    """
    if not text:
        return None
    try:
        if len(text) == len("YYYY-MM-DD"):
            return dt.date.fromisoformat(text)
        if "T" not in text:  # «20261105» is a date Python reads as midnight; it is no form of the contract
            return None
        moment = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    return (moment if moment.tzinfo else moment.replace(tzinfo=MADRID)).astimezone(MADRID)


def _folder(item: str, replicas: Mapping[str, Any]) -> str:
    """The folder holding an item's replicas, relative to the base folder; "" if it has none.

    The folder every replica shares, counting what the student turned in from the assignment's own
    folder: an assignment's or a material's folder, or `classroom/` for a material that is one file
    or an announcement that is one note.
    """
    prefix = f"{CLASSROOM}|{item}|"
    folders: list[str] = []
    for key, raw in replicas.items():
        if not key.startswith(prefix):
            continue
        record = cast("dict[str, Any]", raw)
        parent = PurePosixPath(str(record["path"])).parent
        if record.get("role") == ReplicaRole.SUBMISSION:
            parent = parent.parent
        folders.append(str(parent))
    return posixpath.commonpath(folders) if folders else ""


def _order(entry: AgendaEntry) -> tuple[int, bool, float, str, str, str]:
    """«Pendiente» nearest first, «Hecho» and «Publicado» most recent first; the undated ones last (FR-020c)."""
    moment = _instant(entry.date).timestamp() if entry.date is not None else 0.0
    if entry.list != AgendaList.PENDING:
        moment = -moment
    return (_LISTS.index(entry.list), entry.date is None, moment, entry.subject, entry.title, entry.item)


def capture_instants(captures: Mapping[str, Mapping[str, Any]]) -> dict[str, dt.datetime]:
    """Class id → the instant of its newest capture, from `plan.latest_captures`."""
    return {key: capture.captured_at(dict(data)) for key, data in captures.items() if data.get("type") == "class"}


@dataclass(frozen=True)
class AgendaBuilder:
    """State + decisions + the classes' newest captures → the agenda of one school year."""

    school_year: str
    links: Mapping[str, Subject]
    classifier: Classifier
    decisions: Sequence[Decision]
    state: Mapping[str, Any]
    captured: Mapping[str, dt.datetime]
    notices: Sequence[str] = ()  # lines at the top of agenda.md, in Spanish, with no date
    reports: Sequence[str] = ()  # «Informes de apuntes» at the end, newest first, in Spanish (spec 005 T036)

    def _items(self) -> dict[str, tuple[Item, Subject]]:
        """The items of the linked classes that Classroom still shows."""
        found: dict[str, tuple[Item, Subject]] = {}
        for raw in cast("dict[str, Any]", self.state.get("items", {})).values():
            record = cast("dict[str, Any]", raw)
            subject = self.links.get(str(record["class_id"]))
            if subject is None or record.get("withdrawn_at"):
                continue
            item, _ = item_from_json(record)
            found[item.id] = (item, subject)
        return found

    def entries(self) -> list[AgendaEntry]:
        """Every entry, in the order of `agenda.md`."""
        items = self._items()
        replicas = cast("Mapping[str, Any]", self.state.get("replicas", {}))
        found = [self._entry(item, subject, replicas) for item, subject in items.values()]
        found += self._detected(items, replicas)
        return sorted(found, key=_order)

    def _entry(self, item: Item, subject: Subject, replicas: Mapping[str, Any]) -> AgendaEntry:
        """A Classroom item's own entry, in its list per the table of FR-020c."""
        category = self.classifier.category(item)
        posted = category in _POSTED
        date = item.posted_at if posted else item.due_at
        if posted:
            listed = AgendaList.POSTED
        elif item.status == ItemStatus.MISSING_PER_TEACHER:
            listed = AgendaList.PENDING
        elif item.status in _DONE:
            listed = AgendaList.DONE
        elif category == AgendaCategory.EXAM and later_than(self.captured.get(item.class_id), date):
            listed = AgendaList.DONE  # it took place: wins over pending, overdue or no status
        else:
            listed = AgendaList.PENDING
        return AgendaEntry(
            item=item.id,
            subject=subject.folder,
            list=listed,
            date_only=not isinstance(date, dt.datetime),
            category=category,
            title=item.title,
            date=date,
            classroom_link=classroom_link(item),
            status=item.status,
            folder=_folder(item.id, replicas),
        )

    def _detected(self, items: Mapping[str, tuple[Item, Subject]], replicas: Mapping[str, Any]) -> list[AgendaEntry]:
        """One entry per detected exam in force, with the family's correction over it (FR-020b)."""
        corrections = {
            d.origin: d
            for d in self.decisions
            if d.type == DecisionType.EXAM_CORRECTION and d.state != DecisionState.SUPERSEDED
        }
        found: list[AgendaEntry] = []
        for decision in self.decisions:
            if decision.type != DecisionType.DETECTED_EXAM or not decision.counts:
                continue
            source = items.get(decision.origin.split("#exam-", 1)[0])
            if source is None:  # withdrawn, of a class not linked, or not applied yet
                continue
            item, subject = source
            correction = corrections.get(decision.origin)
            if correction is None and decision.origin_hash != text_hash(item):
                continue  # taken on a text the teacher has since changed: the candidate is pending again
            target = {**decision.target, **(correction.target if correction else {})}
            if target.get("discarded") == "true":
                continue
            category = AgendaCategory(target["category"]) if target.get("category") else AgendaCategory.EXAM
            date = _exam_date(target.get("date"))
            if category in _POSTED:
                listed = AgendaList.POSTED
            elif category == AgendaCategory.EXAM and later_than(self.captured.get(item.class_id), date):
                listed = AgendaList.DONE
            else:
                listed = AgendaList.PENDING
            found.append(
                AgendaEntry(
                    item=decision.origin,
                    subject=subject.folder,
                    list=listed,
                    date_only=not isinstance(date, dt.datetime),
                    category=category,
                    title=item.title,
                    date=date,
                    classroom_link=classroom_link(item),
                    detected=True,
                    origin=item.id,
                    corrected=correction is not None,
                    folder=_folder(item.id, replicas),
                )
            )
        return found

    def counts(self) -> Counter[AgendaList]:
        """How many entries each list holds."""
        return Counter(e.list for e in self.entries())

    def to_json(self, entries: Sequence[AgendaEntry] | None = None) -> str:
        """`agenda.json` (contracts/agenda.schema.json): every key, no timestamp."""
        found = self.entries() if entries is None else entries
        document = {"version": VERSION, "school_year": self.school_year, "entries": [_as_json(e) for e in found]}
        return json.dumps(document, ensure_ascii=False, indent=1) + "\n"

    def to_markdown(self, entries: Sequence[AgendaEntry] | None = None) -> str:
        """`agenda.md`: «Pendiente», «Hecho» and «Publicado», in Spanish."""
        found = self.entries() if entries is None else entries
        lines = [f"# Agenda {self.school_year}", ""]
        for notice in self.notices:
            lines += [notice, ""]
        lines.append(OPEN_WITH)
        for listed in _LISTS:
            rows = [self._line(e) for e in found if e.list == listed]
            lines += ["", f"## {LIST_NAMES[listed]}", "", *(rows or [NOTHING])]
        if self.reports:
            lines += ["", f"## {REPORTS}", "", *(f"- {line}" for line in self.reports)]
        return "\n".join(lines) + "\n"

    def _line(self, entry: AgendaEntry) -> str:
        parts = [shown(entry.date), entry.subject, CATEGORY_NAMES[entry.category], " ".join(entry.title.split())]
        if entry.status is not None:
            parts.append(STATUS_NAMES[entry.status])
        if entry.detected:
            parts.append(DETECTED)
        if entry.corrected:
            parts.append(CORRECTED)
        parts.append(f"[Classroom]({entry.classroom_link})")
        if entry.folder:
            # agenda.md sits in the school-year folder: the link is relative to it.
            parts.append(f"[carpeta](<{entry.folder.removeprefix(f'{self.school_year}/')}>)")
        return _BOXES[entry.list] + " · ".join(parts)

    def write(self, base: Path) -> list[str]:
        """Write each file whose bytes changed; returns their paths relative to the base folder (FR-025)."""
        found = self.entries()
        written: list[str] = []
        for name, text in zip(FILES, (self.to_json(found), self.to_markdown(found)), strict=True):
            relative = f"{self.school_year}/{name}"
            if write_atomic(base / relative, text):
                written.append(relative)
        return written


def shown(when: When | None) -> str:
    """A date as Classroom shows it, in Madrid: «13 oct», «13 oct, 8:00», or «sin fecha» (FR-021)."""
    if when is None:
        return NO_DATE
    if isinstance(when, dt.datetime):
        local = when.astimezone(MADRID)
        return f"{local.day} {_MONTHS[local.month - 1]}, {local.hour}:{local.minute:02d}"
    return f"{when.day} {_MONTHS[when.month - 1]}"


def _as_json(entry: AgendaEntry) -> dict[str, Any]:
    return {
        "item": entry.item,
        "subject": entry.subject,
        "list": str(entry.list),
        "category": str(entry.category),
        "title": entry.title,
        "date": entry.date.isoformat() if entry.date is not None else None,
        "date_only": entry.date_only,
        "status": str(entry.status) if entry.status else None,
        "detected": entry.detected,
        "origin": entry.origin,
        "corrected": entry.corrected,
        "classroom_link": entry.classroom_link,
        "folder": entry.folder or None,
    }
