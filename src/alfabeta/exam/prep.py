"""`exam prep`'s steps (spec 002 contracts/cli.md, FR-029 to FR-037).

Steps 1 to 4 find what the command needs and ask the notebook for nothing: a refusal there is a
`Refusal` and prints nothing. Steps 5 to 9 are `ExamPrep.run`: from there a failure is code 3 and
stops nothing after it — a refresh or a guide that fails still lets both sheets be asked for, and a
sheet that fails does not stop the other.

The agenda is spec 001's `agenda.json`, read by its schema. An exam's announcement is the note spec
001 wrote for the item the exam was detected in, found through that item's `announcement` replica in
`data/state.json`; any other exam has none. The pack record (FR-024) is `study-pack.json` in the
student's data folder, keyed by the topic's path under the base folder; the refresh record is spec
005's `notebook-refresh.json` beside it.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import re
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, cast

from alfabeta.exam.nlm import NlmError
from alfabeta.exam.prompts import short_day, weekday
from alfabeta.notes.refresh import LocalRefreshStore
from alfabeta.notes.run import topic_name
from alfabeta.placement import MAX_NAME_BYTES, NO_TOPIC
from alfabeta.sources import CLASSROOM
from alfabeta.state import write_atomic

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from alfabeta.exam.nlm import Artifact, Notebook

EXIT_OK, EXIT_INVALID, EXIT_PARTIAL, EXIT_NLM = 0, 1, 3, 5
EXAM_FOLDER = "exam"
START_TITLE = "Empieza aquí"  # after the moment: piece 0 is the pack's plan (FR-015)
SOLUTIONS = "Soluciones"
PACK_RECORD = "study-pack.json"
DEFAULT_MINUTES = 90
PAGES_PER_90_MINUTES = 4  # measured once, 2026-10-28
SOURCE_SETTLE_SECONDS = 120  # a Drive source took one to two minutes to catch up (spec 005, 2026-10-27)
POLL_SECONDS = 30
WAIT_SECONDS = 30 * 60
COMPLETED, FAILED = "completed", "failed"

_DATED = re.compile(r"^(\d{8}) - (.+)$")
_SLOT = re.compile(r"^(\d{2}):(\d{2})-(\d{2}):(\d{2})$")
_TOPIC_NUMBER = re.compile(r"\bTema (\d{2})\b")
_ANNOUNCEMENT = re.compile(r"^(\d{8}) - aviso - .+\.md$")
_GUIDE = re.compile(r"gu[ií]a de estudio|study guide", re.IGNORECASE)
_PLAN = re.compile(r"^0\s*·")  # piece 0, the plan «0 · Guía de estudio» (FR-015): never a theory guide
EN_DASH = "\u2013"  # between the slot's clock times, as `prompts.md` writes them


class Refusal(Exception):
    """The command stops before it asks the notebook for anything; `reason` is the CLI's code."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


def _say(message: str) -> None:
    print(f"alfabeta: {message}", file=sys.stderr)


@dataclass(frozen=True)
class Slot:
    """The study slot: its length sets the theory sheet's pages, its clock times go into the plan."""

    minutes: int
    words: str  # `{slot}` of the prompts

    @classmethod
    def parse(cls, value: str | None) -> Slot:
        """`HH:MM-HH:MM`, or 90 minutes with no clock times."""
        if value is None:
            return cls(DEFAULT_MINUTES, f"{DEFAULT_MINUTES} minutos")
        found = _SLOT.match(value)
        if found is None:
            raise Refusal("invalid_slot", "--slot is HH:MM-HH:MM")
        h1, m1, h2, m2 = (int(g) for g in found.groups())
        if max(h1, h2) > 23 or max(m1, m2) > 59 or (h2 * 60 + m2) <= (h1 * 60 + m1):
            raise Refusal("invalid_slot", "--slot ends after it starts, within one day")
        return cls((h2 * 60 + m2) - (h1 * 60 + m1), f"{value[:5]}{EN_DASH}{value[6:]}")

    @property
    def pages(self) -> int:
        """Four A4 pages per 90 minutes, rounded up."""
        return math.ceil(PAGES_PER_90_MINUTES * self.minutes / 90)


@dataclass(frozen=True)
class Exam:
    """The exam and its announcement: the scope of both sheets (FR-030)."""

    day: dt.date
    announcement: str
    announced: dt.date


def _day(value: object) -> dt.date | None:
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        return dt.date.fromisoformat(value[:10])
    except ValueError:
        return None


def _announcement(state: dict[str, Any], base: Path, entry: dict[str, Any]) -> tuple[str, dt.date] | None:
    """The text and date of the announcement an exam was detected in, or None."""
    origin = entry.get("origin")  # only a detected exam has one (agenda.schema.json)
    if not isinstance(origin, str):
        return None
    replicas = cast("dict[str, dict[str, Any]]", state.get("replicas", {}))
    path = replicas.get(f"{CLASSROOM}|{origin}|#announcement", {}).get("path")
    if not isinstance(path, str):
        return None
    note = base / path
    named = _ANNOUNCEMENT.match(note.name)
    if named is None or not note.is_file():
        return None
    text = note.read_text().strip()
    return (text, dt.datetime.strptime(named.group(1), "%Y%m%d").date()) if text else None


def _records(path: Path, reason: str) -> dict[str, Any]:
    """A JSON record of spec 001, or a refusal that names it when it cannot be read."""
    try:
        read: object = json.loads(path.read_text()) if path.is_file() else {}
    except (OSError, ValueError):
        read = None
    if not isinstance(read, dict):
        raise Refusal(reason, f"{path.name} is not readable JSON; run the sync again")
    return cast("dict[str, Any]", read)


def find_exam(agenda: Path, state: Path, base: Path, subject: str, wanted: dt.date | None, today: dt.date) -> Exam:
    """The subject's exam on `wanted`, or its next one from today on, with its announcement (step 3)."""
    listed: object = _records(agenda, "unreadable_agenda").get("entries", [])
    rows = cast("list[object]", listed) if isinstance(listed, list) else []
    entries = [cast("dict[str, Any]", e) for e in rows if isinstance(e, dict)]
    exams = [
        (day, e)
        for e in entries
        if e.get("category") == "exam" and e.get("subject") == subject and (day := _day(e.get("date"))) is not None
    ]
    on = wanted or min((day for day, _ in exams if day >= today), default=None)
    found = [e for day, e in exams if day == on]
    if on is None or not found:
        raise Refusal("no_exam", "the agenda holds no exam of the subject on that day, or none to come")
    records = _records(state, "unreadable_state")
    for entry in found:
        announced = _announcement(records, base, entry)
        if announced is not None:
            return Exam(on, *announced)
    raise Refusal(
        "no_announcement",
        "the exam has no captured announcement (one announced in class, or detected in a material or an"
        " assignment, has none); nothing was asked",
    )


def topic_folder(subject_dir: Path, wanted: str | None) -> Path:
    """The named topic folder, or the subject's most recent one, by the date its name starts with (step 4)."""
    if wanted is not None:
        folder = subject_dir / wanted
        if "/" in wanted or wanted in (".", "..") or not folder.is_dir():
            raise Refusal("no_topic", "--topic is not a folder of the subject")
        return folder
    dated = [
        (found.group(1), p.name, p)
        for p in (subject_dir.iterdir() if subject_dir.is_dir() else ())
        if p.is_dir() and (found := _DATED.match(p.name)) and found.group(2) != NO_TOPIC
    ]
    if not dated:
        raise Refusal("no_topic", "the subject has no topic folder")
    return max(dated)[2]


def topic_number(folder: str) -> str:
    """`T02` for a `Tema 02 - …` folder; a teacher's topic with no number goes by its name."""
    found = _TOPIC_NUMBER.search(folder)
    return f"T{found.group(1)}" if found else topic_name(folder)


@dataclass(frozen=True)
class LivingNotes:
    """What step 5 needs of the topic's living notes file (spec 005)."""

    source: str  # its notebook source
    built_md5: str
    revised: dt.datetime  # the time Drive gives for its last revision


class LivingNotesError(Exception):
    """Step 5 could not use the living notes file; `missing` when it is set up but not in place."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class LivingNotesReader(Protocol):
    """The topic's living notes file, from spec 005's records in Drive."""

    def living_notes(self, subject: str, folder: str) -> LivingNotes | None:
        """None while the topic's living files are not set up yet; raises when the file is not in place."""
        ...


class Printer(Protocol):
    """`print_pack.py report` and the page count of what it printed."""

    def print_report(self, notebook: str, artifact: str, out: Path, *, break_before: str = "") -> bool:
        """Print one report to `out`; False when it did not print."""
        ...

    def pages(self, pdf: Path) -> int | None:
        """The printed PDF's page count; None when it cannot be read."""
        ...


@dataclass
class ExamDeps:
    """The ports of one `exam prep`."""

    notebook: Notebook
    living: LivingNotesReader
    printer: Printer
    mirrors: Callable[[], int]  # refreshes every mirror; how many failed
    sleep: Callable[[float], None]
    now: Callable[[], dt.datetime]


@dataclass(frozen=True)
class Sheet:
    """One of the two exam sheets."""

    kind: str  # `theory` or `problems`, as the output names it
    name: str  # in its title and its file name
    prompt: str
    break_before: str = ""


def _cut(text: str, limit: int) -> str:
    """`text` cut to `limit` UTF-8 bytes."""
    while len(text.encode()) > limit:
        text = text[:-1]
    return text.rstrip(" .")


def _read(path: Path) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads(path.read_text())) if path.is_file() else {}


def _write(path: Path, record: dict[str, Any]) -> None:
    """A record of the data folder, readable by its user alone (spec 005 T044)."""
    write_atomic(path, json.dumps(record, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    path.chmod(0o600)


@dataclass
class ExamPrep:
    """Steps 5 to 9 for one exam of one topic, whose notebook was found."""

    deps: ExamDeps
    data_dir: Path
    base: Path
    subject: str
    folder: Path
    notebook: str
    exam: Exam
    slot: Slot
    sheets: tuple[Sheet, Sheet]
    start_note: Callable[[str], str]  # the start note's text for the theory sheet's title
    partial: bool = field(init=False, default=False)

    @property
    def _key(self) -> str:
        return self.folder.relative_to(self.base).as_posix()

    def _wait(self, ids: list[str]) -> dict[str, str]:
        """Each artifact's last status, polling Studio until all end or the wait runs out."""
        status = dict.fromkeys(ids, "in_progress")
        for _ in range(WAIT_SECONDS // POLL_SECONDS):
            if not ids:
                break
            try:
                listed = {a.id: a.status for a in self.deps.notebook.artifacts(self.notebook)}
            except NlmError:
                listed = {}  # a failed poll is polled again
            status |= {i: listed[i] for i in ids if i in listed}
            if all(s in (COMPLETED, FAILED) for s in status.values()):
                break
            self.deps.sleep(POLL_SECONDS)
        return status

    def _refresh(self, living: LivingNotes) -> None:
        """Read the notes source once when the notebook may not hold its latest build (spec 005 FR-018).

        Only the first read (`reads = 1`); `notebook refresh` makes the confirming one (spec 005 R14).
        """
        store = LocalRefreshStore(self.data_dir)
        record = store.load()
        read = record.sources.get(living.source)
        if read is not None and read.read_md5 == living.built_md5:
            return
        self.deps.notebook.read_source(living.source)
        store.save(record.after_read(living.source, living.built_md5, self.deps.now()))
        self.deps.sleep(SOURCE_SETTLE_SECONDS)

    def _guide(self, living: LivingNotes, pack: dict[str, Any]) -> bool:
        """Regenerate the study guide when it predates the notes' last revision, or there is none (FR-033).

        The plan of piece 0 also says «guía de estudio»; it is never taken for the guide, so it is never
        compared, retitled or deleted.
        """
        recorded = cast("dict[str, Any]", pack.get("guide", {})).get("id")
        guides = [
            a
            for a in self.deps.notebook.artifacts(self.notebook)
            if a.type == "report"
            and a.status == COMPLETED
            and not _PLAN.match(a.title)
            and (a.id == recorded or _GUIDE.search(a.title))
        ]
        current = next((a for a in guides if a.id == recorded), None) or max(
            guides, key=lambda a: a.created_at or dt.datetime.min.replace(tzinfo=dt.UTC), default=None
        )
        if current is not None and current.created_at is not None and current.created_at >= living.revised:
            return False
        made = self.deps.notebook.create_report(self.notebook, "Study Guide", "es")
        if self._wait([made])[made] != COMPLETED:
            _say("the new study guide did not complete; the guide may be stale")
            self.partial = True
            return False
        pack["guide"] = {"id": made, "made": self.deps.now().date().isoformat()}
        try:
            if current is not None and current.title:
                self.deps.notebook.rename(made, current.title)
            for old in guides:
                self.deps.notebook.delete(self.notebook, old.id)
        except NlmError:
            _say("the new study guide is in the notebook, but the previous one was not retitled or removed")
            self.partial = True
        return True

    def _notes_and_guide(self, pack: dict[str, Any]) -> bool:
        """Step 5; whether the guide was regenerated."""
        try:
            living = self.deps.living.living_notes(self.subject, self.folder.name)
        except LivingNotesError as err:
            cause = (
                "the topic's living notes file is not where `notebook setup` put it"
                if err.reason == "missing"
                else "Drive did not answer"
            )
            _say(f"{cause}; the class notes were not compared and the study guide may be stale")
            self.partial = True
            return False
        if living is None:
            _say("the topic's living files are not set up yet: the study guide was not compared with the notes")
            return False
        try:
            self._refresh(living)
        except NlmError:
            _say("the notebook did not read the class notes again; the study guide may be stale")
            self.partial = True
        try:
            return self._guide(living, pack)
        except NlmError:
            _say("the study guide could not be checked or regenerated; it may be stale")
            self.partial = True
            return False

    def _ask(self) -> dict[str, str]:
        """Step 6: both reports, waited for together; the completed ones by kind."""
        asked: dict[str, str] = {}
        for sheet in self.sheets:
            try:
                asked[sheet.kind] = self.deps.notebook.create_report(
                    self.notebook, "Create Your Own", "es", sheet.prompt
                )
            except NlmError:
                _say(f"the notebook did not take the request for «{sheet.name}»")
        status = self._wait(list(asked.values()))
        done = {kind: art for kind, art in asked.items() if status[art] == COMPLETED}
        for sheet in self.sheets:
            if sheet.kind in asked and sheet.kind not in done:
                _say(f"«{sheet.name}» never completed in the notebook")
        if len(done) < len(self.sheets):
            self.partial = True
        return done

    def _number(self, artifacts: list[Artifact], moment: str, new: set[str]) -> int:
        """The first number after the pieces the moment already holds (FR-014)."""
        held = re.compile(rf"^{re.escape(moment)}(?: (\d+))? ·")
        numbers = [int(found.group(1) or 1) for a in artifacts if a.id not in new and (found := held.match(a.title))]
        return max(numbers, default=0) + 1

    def _title(self, done: dict[str, str], pack: dict[str, Any]) -> dict[str, str]:
        """Step 7: titles from the last piece to the first, the start note last, the pack record."""
        moment = f"EXAMEN {weekday(self.exam.day)}"
        try:
            first = self._number(self.deps.notebook.artifacts(self.notebook), moment, set(done.values()))
        except NlmError:
            _say("the notebook's pieces could not be listed; the sheets are numbered from 1")
            self.partial = True
            first = 1
        titles = {
            s.kind: f"{moment} {first + i} · {s.name} · {topic_name(self.folder.name)}"
            for i, s in enumerate(self.sheets)
        }
        try:
            for sheet in reversed(self.sheets):
                if sheet.kind in done:
                    self.deps.notebook.rename(done[sheet.kind], titles[sheet.kind])
            theory = self.sheets[0].kind
            if theory in done:
                # The moment's own note; a «0 · …» note is the pack's, retired by FR-015, and left as it is.
                title = f"{moment} · {START_TITLE}"
                start = next((n for n in self.deps.notebook.notes(self.notebook) if n.title == title), None)
                self.deps.notebook.write_note(
                    self.notebook, start.id if start else None, title, self.start_note(titles[theory])
                )
        except NlmError:
            _say("the notebook did not take the titles or the start note")
            self.partial = True
        pieces = cast("list[dict[str, Any]]", pack.setdefault("pieces", []))
        pieces += [
            {
                "id": done[s.kind],
                "kind": f"exam_{s.kind}",
                "moment": moment,
                "title": titles[s.kind],
                "language": "es",
                "verification": "pages_only",  # FR-009: nothing else of an exam sheet is checked
                "exam": self.exam.day.isoformat(),
                "made": self.deps.now().date().isoformat(),
            }
            for s in self.sheets
            if s.kind in done
        ]
        return titles

    def _print(self, done: dict[str, str]) -> dict[str, int | None]:
        """Step 8: each completed sheet into the topic's `exam/`, then the mirrors; pages by kind."""
        pages: dict[str, int | None] = {}
        if not done:
            return pages
        exam_dir = self.folder / EXAM_FOLDER
        exam_dir.mkdir(exist_ok=True)
        day = f" ({short_day(self.exam.day)}).pdf"
        for sheet in self.sheets:
            if sheet.kind not in done:
                continue
            # A long teacher's topic is cut, never the exam's date that tells two exams apart.
            out = (
                exam_dir
                / f"{_cut(f'{sheet.name} · {topic_number(self.folder.name)}', MAX_NAME_BYTES - len(day.encode()))}{day}"
            )
            if self.deps.printer.print_report(self.notebook, done[sheet.kind], out, break_before=sheet.break_before):
                pages[sheet.kind] = self.deps.printer.pages(out)
                if pages[sheet.kind] is None:
                    _say(f"«{sheet.name}» printed, but its pages could not be counted")
                    self.partial = True
            else:
                _say(f"«{sheet.name}» did not print")
                self.partial = True
        failed = self.deps.mirrors()
        if failed:
            _say(f"{failed} mirror(s) of the base folder were not refreshed")
            self.partial = True
        return pages

    def run(self) -> dict[str, Any]:
        """Steps 5 to 9; the command's JSON but `ok` and `topic`."""
        path = self.data_dir / PACK_RECORD
        record = _read(path)
        pack = cast("dict[str, Any]", record.setdefault("topics", {}).setdefault(self._key, {}))
        regenerated = self._notes_and_guide(pack)
        done = self._ask()
        if done:
            self._title(done, pack)
        _write(path, record)
        pages = self._print(done)
        theory = self.sheets[0].kind
        if (pages.get(theory) or 0) > self.slot.pages:
            _say(f"the theory sheet has {pages[theory]} pages; the slot allows {self.slot.pages}. It was printed.")
        return {
            "exam_date": self.exam.day.isoformat(),
            "guide_regenerated": regenerated,
            "slot_minutes": self.slot.minutes,
            "pages_allowed": self.slot.pages,
            "sheets": [{"kind": s.kind, "printed": s.kind in pages, "pages": pages.get(s.kind)} for s in self.sheets],
        }
