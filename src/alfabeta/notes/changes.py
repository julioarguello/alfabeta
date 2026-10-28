"""What changed under the topic folders since the last run (spec 005 research R2, FR-004).

The feed from `ScopedDrive.changes` becomes arrivals, the student's marks and corrections, and the
recorded files that are gone. Layout (spec 001): `<year>/<subject>/<topic>/` with `notes/` and
`classroom/` inside, each holding its living file, nothing at the topic's root, and `.alfabeta/` and
`reports/` at the root of the alfabeta folder.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from alfabeta.google.drive import Change
from alfabeta.notes.model import Arrival, Kind, LivingKind

if TYPE_CHECKING:
    from collections.abc import Mapping

    from alfabeta.google.drive import DriveFile

NOTES_FOLDER = "notes"
CLASSROOM_FOLDER = "classroom"
# The folder of the topic each living file sits in (spec 005 FR-009).
LIVING_FOLDERS = {LivingKind.NOTES: NOTES_FOLDER, LivingKind.CLASSROOM: CLASSROOM_FOLDER}
SKIPPED = frozenset({".alfabeta", "reports"})
TRANSCRIPT_MARK = " · transcripción"
_TOPIC_DEPTH = 3  # root / year / subject / topic


@dataclass(frozen=True)
class Known:
    """What the state records of a file, as far as the feed needs it."""

    kind: Kind
    version: str
    own: bool = False
    name: str | None = None  # a transcription PDF's recorded name, to see the student's mark
    topic: str | None = None  # the topic folder it was recorded under; a move to another arrives


@dataclass(frozen=True)
class Mark:
    """The student renamed a transcription PDF (research R7)."""

    file_id: str
    name: str


@dataclass(frozen=True)
class Correction:
    """The student edited a transcription Markdown alfabeta wrote (research R7)."""

    file_id: str
    version: str


@dataclass
class FeedResult:
    """One run's reading of the feed."""

    cursor: str
    arrivals: list[Arrival] = field(default_factory=lambda: [])
    marks: list[Mark] = field(default_factory=lambda: [])
    corrections: list[Correction] = field(default_factory=lambda: [])
    gone: list[str] = field(default_factory=lambda: [])


class FeedSource(Protocol):
    """What the feed needs of spec 004's `ScopedDrive`."""

    def items(self) -> list[DriveFile]:
        """Everything listed under the root this run."""
        ...

    def relist(self) -> None:
        """List the tree again from Drive."""
        ...

    def ancestors(self, item_id: str) -> list[DriveFile]:
        """The folders from below the root down to the item's parent."""
        ...

    def start_page_token(self) -> str:
        """The cursor of now."""
        ...

    def changes(self, page_token: str, known_ids: frozenset[str]) -> tuple[list[Change], str]:
        """The kept changes since the cursor, and the next cursor."""
        ...


class ChangeFeed(Protocol):
    """Reads what changed since a cursor."""

    def read(self, cursor: str | None, known: Mapping[str, Known]) -> FeedResult:
        """The run's arrivals, marks, corrections and gone files."""
        ...


def _is_living(item: DriveFile, kind: LivingKind) -> bool:
    """Whether a file directly in `notes/` or `classroom/` carries that folder's living file name."""
    stem = item.name.rsplit(".", 1)[0]
    return item.name.startswith(f"{kind.prefix} · ") and item.name.endswith(".pdf") and TRANSCRIPT_MARK not in stem


def _kind_in_notes(item: DriveFile) -> Kind:
    if item.mime_type.startswith("image/"):
        return Kind.NOTES_PHOTO  # the model decides whether it can be transcribed
    stem = item.name.rsplit(".", 1)[0]
    if item.name.endswith(".pdf") and TRANSCRIPT_MARK in stem:
        return Kind.NOTES_TRANSCRIPT
    if _is_living(item, LivingKind.NOTES):
        return Kind.LIVING_FILE
    if item.name.endswith(".md"):
        return Kind.NOTES_TEXT
    return Kind.UNEXPECTED


class DriveChangeFeed:
    """`ChangeFeed` over `ScopedDrive`."""

    def __init__(self, drive: FeedSource) -> None:
        self._drive = drive

    def read(self, cursor: str | None, known: Mapping[str, Known]) -> FeedResult:
        """With no cursor, take the new cursor first and then the whole tree once (FR-004)."""
        if cursor is None:
            new_cursor = self._drive.start_page_token()
            self._drive.relist()  # after the cursor: what arrives in between is in one or the other
            changes = [Change(item.id, left=False, file=item) for item in self._drive.items()]
        else:
            changes, new_cursor = self._drive.changes(cursor, frozenset(known))
        result = FeedResult(new_cursor)
        arrivals: dict[str, Arrival] = {}
        for change in changes:
            if change.left or change.file is None:
                if change.file_id in known and change.file_id not in result.gone:
                    result.gone.append(change.file_id)
                continue
            self._take(change.file, known, result, arrivals)
        result.arrivals = list(arrivals.values())
        return result

    def _take(
        self, item: DriveFile, known: Mapping[str, Known], result: FeedResult, arrivals: dict[str, Arrival]
    ) -> None:
        placed = self._place(item)
        if placed is None:
            return
        topic, kind, arrival_id = placed
        record = known.get(item.id)
        if record is not None and record.own:
            # An echo of alfabeta's own write, except the student's two changes (research R2).
            if record.kind == Kind.NOTES_TRANSCRIPT and record.name is not None and item.name != record.name:
                result.marks.append(Mark(item.id, item.name))
            elif record.kind == Kind.NOTES_TEXT and item.version != record.version:
                result.corrections.append(Correction(item.id, item.version))
            return
        if record is not None and record.version == item.version and record.topic in (None, topic):
            return  # renamed, or moved within its topic, same content: nothing new
        arrivals[arrival_id] = Arrival(arrival_id, topic, kind, item.version)

    def _place(self, item: DriveFile) -> tuple[str, Kind, str] | None:
        """(topic id, kind, arrival id), or None for anything that is not under a topic's own folders."""
        chain = self._drive.ancestors(item.id)
        if (chain and chain[0].name in SKIPPED) or (not chain and item.name in SKIPPED):
            return None
        if len(chain) < _TOPIC_DEPTH:
            return None  # a year, a subject, a topic folder itself, or a file beside them
        topic, below = chain[_TOPIC_DEPTH - 1], chain[_TOPIC_DEPTH:]
        if not below:
            if item.is_folder:
                return None  # notes/, classroom/ or another folder of the topic
            return topic.id, Kind.UNEXPECTED, item.id  # nothing alfabeta writes sits at a topic's root
        section = below[0].name
        if section == NOTES_FOLDER:
            if item.is_folder:
                return None
            return topic.id, _kind_in_notes(item) if len(below) == 1 else Kind.UNEXPECTED, item.id
        if section == CLASSROOM_FOLDER:
            if len(below) == 1 and not item.is_folder and _is_living(item, LivingKind.CLASSROOM):
                return topic.id, Kind.LIVING_FILE, item.id  # never an item of itself
            # An item is a file or a folder directly in classroom/; a file deeper is part of its item.
            owner = item if len(below) == 1 else below[1]
            return topic.id, Kind.CLASSROOM_ITEM, owner.id
        return None
