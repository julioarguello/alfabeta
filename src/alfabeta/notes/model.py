"""The domain of spec 005 (data-model.md): immutable values, their states and the rules between them.

Ids here are Drive file ids, Drive folder ids and notebook source ids. They are kept, never printed,
and never reach the repository or a log.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Protocol

from alfabeta.placement import SUBMISSION_FOLDER

if TYPE_CHECKING:
    from collections.abc import Mapping

# A photo that keeps failing is retried on this many later runs, then left until it changes.
MAX_RETRIES = 3
# Formats the transcription takes, and the largest photo it sends (research R5).
TRANSCRIBABLE = frozenset({"image/jpeg", "image/png", "image/webp"})
MAX_PHOTO_BYTES = 10 * 1024 * 1024

# Spec 001's roles `submission` and `grading`, whatever follows the prefix (constitution III).
_STUDENT_WORK = re.compile(r"^(entrega - |correccion)", re.IGNORECASE)
# The submission's folder, and its name until 2026-10-28 (#110), so a folder not yet renamed stays out.
_SUBMISSION_FOLDERS = frozenset({SUBMISSION_FOLDER, "entrega"})
# A previous version spec 001 keeps beside an edited replica (spec 001 FR-015b).
_PREVIOUS_VERSION = re.compile(r" \(anterior \d{4}-\d{2}-\d{2}\)(\.[^.]+)?$")
# An announcement note spec 001 writes in `No topic`.
_ANNOUNCEMENT = re.compile(r"^\d{8} - aviso - ")
# How spec 001 names a Classroom item: its posting date, then its title (constitution, Storage).
_POSTED = re.compile(r"^(\d{8}) - (.+)$")
# A link of `enlaces.md`, `[title](address)` (spec 001 FR-017).
_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")

PDF_TYPE = "application/pdf"
DOC = "application/vnd.google-apps.document"
SHEET = "application/vnd.google-apps.spreadsheet"
SLIDES = "application/vnd.google-apps.presentation"
# Google-native files Drive exports to PDF (research R6).
EXPORTABLE = frozenset({DOC, SHEET, SLIDES, "application/vnd.google-apps.drawing"})
# The Google type Drive copies each Office format into before exporting it (research R6).
OFFICE_TYPES = {
    ".doc": DOC,
    ".docx": DOC,
    ".odt": DOC,
    ".rtf": DOC,
    ".xls": SHEET,
    ".xlsx": SHEET,
    ".ods": SHEET,
    ".ppt": SLIDES,
    ".pptx": SLIDES,
    ".odp": SLIDES,
}
_TEXT = frozenset({".md", ".txt"})
_IMAGES = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp"})


class Clock(Protocol):
    """The current instant, injected so runs and tests agree on it."""

    def now(self) -> dt.datetime:
        """The current instant, zone-aware."""
        ...


class Kind(StrEnum):
    """What a file under a topic folder is to spec 005."""

    NOTES_PHOTO = "notes_photo"
    NOTES_TRANSCRIPT = "notes_transcript"
    NOTES_TEXT = "notes_text"
    CLASSROOM_ITEM = "classroom_item"
    LIVING_FILE = "living_file"
    UNEXPECTED = "unexpected"


class PhotoState(StrEnum):
    """Where a photo of the notes is."""

    SEEN = "seen"
    TRANSCRIBED = "transcribed"
    IN_LIVING_FILE = "in_living_file"
    DUPLICATE = "duplicate"
    UNSUPPORTED = "unsupported"
    UNREADABLE = "unreadable"
    FAILED = "failed"
    FAILED_FINAL = "failed_final"
    BUDGET_WAIT = "budget_wait"
    GONE = "gone"


class ItemState(StrEnum):
    """Where a Classroom item is."""

    SEEN = "seen"
    IN_LIVING_FILE = "in_living_file"
    FAILED = "failed"
    FAILED_FINAL = "failed_final"
    GONE = "gone"
    LEFT_OUT = "left_out"  # not material: an announcement, a previous version, a name spec 001 never writes


_PHOTO_TRANSITIONS: Mapping[PhotoState, frozenset[PhotoState]] = {
    PhotoState.SEEN: frozenset(
        {
            PhotoState.TRANSCRIBED,
            PhotoState.DUPLICATE,
            PhotoState.UNSUPPORTED,
            PhotoState.UNREADABLE,
            PhotoState.FAILED,
            PhotoState.BUDGET_WAIT,
        }
    ),
    PhotoState.TRANSCRIBED: frozenset({PhotoState.IN_LIVING_FILE}),
    PhotoState.FAILED: frozenset(
        {
            PhotoState.TRANSCRIBED,
            PhotoState.UNREADABLE,
            PhotoState.FAILED,
            PhotoState.FAILED_FINAL,
            PhotoState.BUDGET_WAIT,
            PhotoState.DUPLICATE,  # a copy of it got its page meanwhile
        }
    ),
    # A refused budget holds every pending photo, a failed one too, day after day (research R5).
    PhotoState.BUDGET_WAIT: frozenset(
        {
            PhotoState.TRANSCRIBED,
            PhotoState.UNREADABLE,
            PhotoState.FAILED,
            PhotoState.BUDGET_WAIT,
            PhotoState.DUPLICATE,
        }
    ),
    PhotoState.IN_LIVING_FILE: frozenset(),
    PhotoState.DUPLICATE: frozenset(),
    PhotoState.UNSUPPORTED: frozenset(),
    PhotoState.UNREADABLE: frozenset(),
    PhotoState.FAILED_FINAL: frozenset(),
    PhotoState.GONE: frozenset(),
}
# A photo can be removed in Drive from any state; a new version starts it again from `seen`.
_PHOTO_ANYTIME = frozenset({PhotoState.GONE, PhotoState.SEEN})

_ITEM_TRANSITIONS: Mapping[ItemState, frozenset[ItemState]] = {
    ItemState.SEEN: frozenset({ItemState.IN_LIVING_FILE, ItemState.FAILED}),
    ItemState.FAILED: frozenset({ItemState.IN_LIVING_FILE, ItemState.FAILED, ItemState.FAILED_FINAL}),
    ItemState.IN_LIVING_FILE: frozenset(),
    ItemState.FAILED_FINAL: frozenset(),
    ItemState.GONE: frozenset(),
    ItemState.LEFT_OUT: frozenset(),
}
# An item can leave or stop being material from any state; a new version starts it again from `seen`.
_ITEM_ANYTIME = frozenset({ItemState.GONE, ItemState.SEEN, ItemState.LEFT_OUT})


class Review(StrEnum):
    """What the student said about a transcription."""

    AUTOMATIC = "automatic"
    CHECKED = "checked"
    WRONG = "wrong"


class PageSource(StrEnum):
    """Where a page's transcription came from."""

    CLAUDE = "claude"
    ADOPTED = "adopted"


class LivingKind(StrEnum):
    """The two living files of a topic."""

    NOTES = "notes"
    CLASSROOM = "classroom"

    @property
    def prefix(self) -> str:
        """How the living file's name starts, in Spanish: `<prefix> · <topic>.pdf`."""
        return "Apuntes" if self is LivingKind.NOTES else "Classroom"


class Health(StrEnum):
    """Whether a recorded living file is still where it was set up."""

    OK = "ok"
    MISSING = "missing"


class PartKind(StrEnum):
    """How one file of a Classroom item becomes pages."""

    PDF = "pdf"
    EXPORT = "export"
    OFFICE = "office"
    TEXT = "text"
    IMAGE = "image"
    NAMED = "named"


class RunResult(StrEnum):
    """How a run ended."""

    OK = "ok"
    PARTIAL = "partial"
    FAILED = "failed"


class RanOn(StrEnum):
    """Where a run ran."""

    CLOUD = "cloud"
    MAC = "mac"


def is_student_work(name: str) -> bool:
    """Whether a file is the student's own work or its grading, which never enters a living file.

    `name` is the file's name or its path inside the item's folder: anything under `submission/` is
    the student's (spec 001 FR-015a, amended 2026-10-28), and so is the older `entrega - <name>`.
    """
    parts = name.replace("\\", "/").split("/")
    return any(p.casefold() in _SUBMISSION_FOLDERS for p in parts[:-1]) or bool(_STUDENT_WORK.match(parts[-1]))


def is_previous_version(name: str) -> bool:
    """Whether a file is a previous version spec 001 keeps beside the current one."""
    return bool(_PREVIOUS_VERSION.search(name))


def is_announcement(name: str) -> bool:
    """Whether a Classroom note is an announcement, which is not material."""
    return bool(_ANNOUNCEMENT.match(name))


def is_part(name: str) -> bool:
    """Whether a file of a Classroom item may become pages of a living file."""
    return not (is_student_work(name) or is_previous_version(name))


def posted_title(name: str, *, folder: bool) -> tuple[dt.date, str] | None:
    """The posting date and title of an item named `YYYYMMDD - <title>[.<ext>]`; None for any other name."""
    named = _POSTED.match(name if folder else PurePosixPath(name).stem)
    if named is None:
        return None
    day = named.group(1)
    try:
        return dt.date(int(day[:4]), int(day[4:6]), int(day[6:])), named.group(2)
    except ValueError:
        return None


def part_kind(name: str, mime_type: str) -> PartKind:
    """How a file of a Classroom item becomes pages (research R6): by Drive's type, then by extension."""
    ext = PurePosixPath(name).suffix.lower()
    if mime_type == PDF_TYPE or ext == ".pdf":
        return PartKind.PDF
    if mime_type in EXPORTABLE:
        return PartKind.EXPORT
    if ext in OFFICE_TYPES:
        return PartKind.OFFICE
    if ext in _TEXT or mime_type in ("text/markdown", "text/plain"):
        return PartKind.TEXT
    if ext in _IMAGES:
        return PartKind.IMAGE
    return PartKind.NAMED


def addresses(links: str) -> tuple[str, ...]:
    """The lines of an `enlaces.md` as the cover shows them: `- [title](address) · date` is `title: address · date`."""
    found: list[str] = []
    for raw in links.splitlines():
        line = raw.strip()
        if line.startswith(("- ", "* ")):
            found.append(_LINK.sub(lambda m: f"{m.group(1)}: {m.group(2)}" if m.group(1) else m.group(2), line[2:]))
    return tuple(found)


@dataclass(frozen=True)
class Topic:
    """A topic folder, keyed by its Drive id, never by its name."""

    folder_id: str
    name: str  # the folder's name after its date, `<topic>` in living file names

    def living_file_name(self, kind: LivingKind) -> str:
        """The living file's name, in Spanish, in the topic's `notes/` or `classroom/`."""
        return f"{kind.prefix} · {self.name}.pdf"


@dataclass(frozen=True)
class Arrival:
    """One file seen under a topic folder."""

    file_id: str
    topic: str
    kind: Kind
    version: str  # Drive's md5Checksum, or modifiedTime for a Google-native file
    own: bool = False
    made_for: str | None = None  # properties.alfabeta_for of an own file


@dataclass(frozen=True)
class Photo:
    """A photo of the notes and the state it is in."""

    arrival: Arrival
    state: PhotoState = PhotoState.SEEN
    retries: int = 0

    def moved_to(self, state: PhotoState) -> Photo:
        """The same photo in `state`, if the transition is allowed; failures count towards the cap."""
        if state not in _PHOTO_TRANSITIONS[self.state] and state not in _PHOTO_ANYTIME:
            raise ValueError(f"a photo cannot go from {self.state} to {state}")
        if state == PhotoState.SEEN:
            return replace(self, state=state, retries=0)
        if state == PhotoState.FAILED:
            retries = self.retries + 1
            if retries > MAX_RETRIES:
                return replace(self, state=PhotoState.FAILED_FINAL, retries=retries)
            return replace(self, state=state, retries=retries)
        return replace(self, state=state)


@dataclass(frozen=True)
class ClassroomItem:
    """A Classroom item and the state it is in."""

    arrival: Arrival
    state: ItemState = ItemState.SEEN
    retries: int = 0

    def moved_to(self, state: ItemState) -> ClassroomItem:
        """The same item in `state`, if the transition is allowed; failures count towards the cap, like a photo's."""
        if state not in _ITEM_TRANSITIONS[self.state] and state not in _ITEM_ANYTIME:
            raise ValueError(f"an item cannot go from {self.state} to {state}")
        if state == ItemState.SEEN:
            return replace(self, state=state, retries=0)
        if state == ItemState.FAILED:
            retries = self.retries + 1
            if retries > MAX_RETRIES:
                return replace(self, state=ItemState.FAILED_FINAL, retries=retries)
            return replace(self, state=state, retries=retries)
        return replace(self, state=state)


@dataclass(frozen=True)
class Usage:
    """Tokens one Claude call used."""

    tokens_in: int
    tokens_out: int


@dataclass(frozen=True)
class NotesPage:
    """One photo and its literal transcription."""

    photo_id: str
    photo_version: str
    markdown: str
    order: int
    review: Review = Review.AUTOMATIC
    source: PageSource = PageSource.CLAUDE
    pdf_id: str | None = None
    markdown_id: str | None = None
    markdown_version: str | None = None
    model: str | None = None
    usage: Usage | None = None

    def marked(self, review: Review) -> NotesPage:
        """The page after the student renamed its PDF."""
        return replace(self, review=review)

    def corrected(self, photo_id: str, photo_version: str, markdown: str, *, markdown_version: str) -> NotesPage:
        """The page after a correction: same place, new text, automatic again (research R7).

        `markdown_version` is the version of the Markdown alfabeta wrote back, so the next run does not
        read its own write as the student's correction.
        """
        return replace(
            self,
            photo_id=photo_id,
            photo_version=photo_version,
            markdown=markdown,
            markdown_version=markdown_version,
            review=Review.AUTOMATIC,
        )

    @property
    def heading(self) -> str:
        """The heading the page carries in the living file, in Spanish."""
        return {
            Review.AUTOMATIC: "Transcripción automática",
            Review.CHECKED: "Revisada por el alumno",
            Review.WRONG: "En corrección",
        }[self.review]


@dataclass(frozen=True)
class LivingFile:
    """One of a topic's two living files."""

    topic: str
    kind: LivingKind
    file_id: str | None = None  # set only by `notebook setup`
    source_id: str | None = None
    built_md5: str | None = None
    pages: int = 0
    health: Health = Health.OK

    @property
    def waiting_setup(self) -> bool:
        """Whether the Mac has not set this file up yet; nothing creates it but the setup."""
        return self.file_id is None

    def set_up(self, file_id: str, source_id: str) -> LivingFile:
        """The file once `notebook setup` created it and added it as a source."""
        if self.file_id is not None and self.file_id != file_id:
            raise ValueError("a living file's id never changes once set")
        return replace(self, file_id=file_id, source_id=source_id)

    def built(self, md5: str, pages: int) -> tuple[LivingFile, bool]:
        """The file after a rebuild, and whether the new bytes must be uploaded."""
        return replace(self, built_md5=md5, pages=pages), md5 != self.built_md5

    def over(self, warn_pages: int) -> bool:
        """Whether the family is warned about its size."""
        return self.pages > warn_pages


@dataclass(frozen=True)
class Part:
    """One file of a Classroom item and how it becomes pages."""

    file_id: str
    name: str
    kind: PartKind


@dataclass(frozen=True)
class ClassroomEntry:
    """A Classroom item as the living Classroom file holds it."""

    item_id: str
    item_version: str
    title: str
    posted: dt.date
    description: str = ""
    addresses: tuple[str, ...] = ()
    parts: tuple[Part, ...] = ()

    def __post_init__(self) -> None:
        """Reject a part the constitution keeps out of every living file."""
        bad = [p.name for p in self.parts if not is_part(p.name)]
        if bad:
            raise ValueError("the student's work, its grading and previous versions are never parts")

    @property
    def links_only(self) -> bool:
        """Whether the entry is only its cover page."""
        return all(p.kind == PartKind.NAMED for p in self.parts)


@dataclass(frozen=True)
class RunLog:
    """The run's own log, written at the end of every run."""

    started: dt.datetime
    ended: dt.datetime
    result: RunResult
    ran_on: RanOn
    last_ok_ended: dt.datetime | None = None
    page_token: str | None = None

    def next(
        self,
        started: dt.datetime,
        ended: dt.datetime,
        result: RunResult,
        ran_on: RanOn,
        page_token: str | None,
        *,
        writes_ok: bool,
    ) -> RunLog:
        """The log a later run writes: only a run whose writes all succeeded moves the cursor (data-model.md).

        A partial run moves the clock, but its cursor only if none of its writes failed, so the next run
        reads again the changes a failed write left behind. Only the cloud's success moves the clock.
        """
        moves_cursor = result != RunResult.FAILED and writes_ok
        moves_ok = result != RunResult.FAILED and ran_on == RanOn.CLOUD
        return RunLog(
            started=started,
            ended=ended,
            result=result,
            ran_on=ran_on,
            last_ok_ended=ended if moves_ok else self.last_ok_ended,
            page_token=page_token if moves_cursor else self.page_token,
        )


@dataclass(frozen=True)
class SpendLedger:
    """Tokens and cost of every Claude call, per month (`YYYY-MM`)."""

    months: Mapping[str, Usage] = field(default_factory=lambda: dict[str, Usage]())

    def add(self, month: str, usage: Usage) -> SpendLedger:
        """The ledger with one more call."""
        old = self.months.get(month, Usage(0, 0))
        months = {**self.months, month: Usage(old.tokens_in + usage.tokens_in, old.tokens_out + usage.tokens_out)}
        return SpendLedger(months)

    def cost(self, month: str, prices: tuple[float, float]) -> float:
        """The month's spend in USD at the configured prices per million tokens."""
        usage = self.months.get(month, Usage(0, 0))
        return (usage.tokens_in * prices[0] + usage.tokens_out * prices[1]) / 1_000_000


def reportable(before: str | None, after: str) -> bool:
    """Whether a state is a change to report: a state that persists is reported once (FR-013)."""
    return before != after
