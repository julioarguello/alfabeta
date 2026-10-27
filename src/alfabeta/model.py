"""The domain of spec 001 (data-model.md): immutable values, their closed vocabularies and invariants.

Identifiers here are opaque Classroom, Drive or book ids. They are kept, never printed in full, and
never reach the repository.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Iterable, Mapping

_STUDENT_ID = re.compile(r"[a-z][a-z0-9_-]*")
_ACCOUNT_INDEX = re.compile(r"/u/\d+(?=/|$)")
MAX_NAME_BYTES = 255


class DecisionType(StrEnum):
    """What a decision links or states."""

    CLASS_LINK = "class_link"
    TOPIC_MATCH = "topic_match"
    ITEM_MATCH = "item_match"
    DETECTED_EXAM = "detected_exam"
    DISMISSED_CANDIDATE = "dismissed_candidate"
    EXAM_CORRECTION = "exam_correction"


class Confidence(StrEnum):
    """How sure Claude is of a proposal."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DecisionState(StrEnum):
    """Where a decision is in its life."""

    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


_TRANSITIONS: Mapping[DecisionState, frozenset[DecisionState]] = {
    DecisionState.PROPOSED: frozenset({DecisionState.CONFIRMED, DecisionState.REJECTED}),
    DecisionState.CONFIRMED: frozenset({DecisionState.SUPERSEDED}),
    DecisionState.REJECTED: frozenset({DecisionState.SUPERSEDED}),
    DecisionState.SUPERSEDED: frozenset(),
}
# These count from the moment they are proposed (data-model, Decision).
_COUNT_WHEN_PROPOSED = frozenset({DecisionType.DETECTED_EXAM, DecisionType.DISMISSED_CANDIDATE})


class ItemType(StrEnum):
    """Kind of Classroom post."""

    ASSIGNMENT = "assignment"
    MATERIAL = "material"
    QUESTION = "question"
    ANNOUNCEMENT = "announcement"


class ItemStatus(StrEnum):
    """Status of an assignment or question, from its detail texts."""

    PENDING = "pending"
    TURNED_IN = "turned_in"
    TURNED_IN_LATE = "turned_in_late"
    RETURNED = "returned"
    OVERDUE = "overdue"
    MISSING_PER_TEACHER = "missing_per_teacher"


_WITH_STATUS = frozenset({ItemType.ASSIGNMENT, ItemType.QUESTION})


class AttachmentKind(StrEnum):
    """What an attachment points to."""

    FILE = "file"
    GOOGLE_DOC = "google_doc"
    VIDEO = "video"
    LINK = "link"
    FORM = "form"


_NOT_DOWNLOADED = frozenset({AttachmentKind.VIDEO, AttachmentKind.LINK, AttachmentKind.FORM})


class AttachmentRole(StrEnum):
    """Why an attachment is on an item."""

    STATEMENT = "statement"
    SUBMISSION = "submission"
    MATERIAL = "material"


class ReplicaRole(StrEnum):
    """Name prefix of a replica in its folder (data-model, Language of names)."""

    STATEMENT = "statement"
    SUBMISSION = "submission"
    GRADING = "grading"
    LINKS = "links"
    DESCRIPTION = "description"
    MATERIAL = "material"
    ANNOUNCEMENT = "announcement"


class GradingState(StrEnum):
    """How far the teacher got with a submission."""

    GRADED = "graded"
    RETURNED = "returned"


class AgendaList(StrEnum):
    """The agenda's three lists."""

    PENDING = "pending"
    DONE = "done"
    POSTED = "posted"


class AgendaCategory(StrEnum):
    """One category per agenda entry, in order of precedence."""

    EXAM = "exam"
    QUIZ = "quiz"
    ASSIGNMENT = "assignment"
    MATERIAL = "material"
    ANNOUNCEMENT = "announcement"

    @classmethod
    def pick(cls, candidates: Iterable[AgendaCategory]) -> AgendaCategory:
        """The one that wins: exam > quiz > assignment > material > announcement."""
        found = set(candidates)
        for category in cls:
            if category in found:
                return category
        raise ValueError("an agenda entry needs at least one category")


_POSTED_ONLY = frozenset({AgendaCategory.MATERIAL, AgendaCategory.ANNOUNCEMENT})


class RunMode(StrEnum):
    """How a run was started (`lock take --mode`)."""

    INTERACTIVE = "interactive"
    SCHEDULED = "scheduled"


class RunResult(StrEnum):
    """How a run ended."""

    OK = "ok"
    PARTIAL = "partial"
    STOPPED = "stopped"


class StopReason(StrEnum):
    """Why a run stopped or was partial (contracts/cli.md, `log stop`)."""

    SESSION_EXPIRED = "session_expired"
    CHALLENGE = "challenge"
    UNEXPECTED_UI = "unexpected_ui"
    DRIVE_NOT_MOUNTED = "drive_not_mounted"
    LOCK_BUSY = "lock_busy"
    LOCK_NOT_HELD = "lock_not_held"
    INVALID_CONFIG = "invalid_config"
    IDLE = "idle"


@dataclass(frozen=True)
class Subject:
    """One subject of the student's configuration."""

    folder: str
    classroom_class: str
    book: str = ""
    book_class: str = ""

    def __post_init__(self) -> None:
        """Reject a value the data model forbids."""
        if not self.folder:
            raise ValueError("a subject needs its folder")
        if bool(self.book) != bool(self.book_class):
            raise ValueError("book and book_class go together")


@dataclass(frozen=True)
class Student:
    """The student a run acts on; `display_name` is never printed by the command."""

    id: str
    display_name: str = field(repr=False)
    school_year: str
    grade_level: str
    languages: tuple[str, ...]
    subjects: tuple[Subject, ...]

    def __post_init__(self) -> None:
        """Reject a value the data model forbids."""
        if not _STUDENT_ID.fullmatch(self.id):
            raise ValueError("the student id must be lowercase ASCII")
        if not re.fullmatch(r"(\d{4})-(\d{4})", self.school_year) or int(self.school_year[5:]) != (
            int(self.school_year[:4]) + 1
        ):
            raise ValueError("school_year must be two consecutive years, YYYY-YYYY")
        if not self.subjects:
            raise ValueError("a student needs at least one subject")


@dataclass(frozen=True)
class Decision:
    """A proposal by Claude or a correction by the family, unique per `(type, origin)`."""

    type: DecisionType
    origin: str
    target: Mapping[str, str]
    reason: str
    state: DecisionState
    date: dt.date
    confidence: Confidence | None = None
    origin_hash: str | None = None

    def __post_init__(self) -> None:
        """Reject a value the data model forbids."""
        if self.type == DecisionType.DETECTED_EXAM and self.state == DecisionState.REJECTED:
            raise ValueError("a detected exam is not rejected; it is discarded with an exam_correction")

    @property
    def key(self) -> tuple[DecisionType, str]:
        """The uniqueness key among the non-superseded decisions."""
        return (self.type, self.origin)

    @property
    def counts(self) -> bool:
        """Whether the run acts on it."""
        if self.state == DecisionState.CONFIRMED:
            return True
        return self.state == DecisionState.PROPOSED and self.type in _COUNT_WHEN_PROPOSED

    def moved_to(self, state: DecisionState, on: dt.date) -> Decision:
        """The same decision in `state`, if the transition is allowed."""
        # A detected exam or dismissed candidate counts while proposed, so a change in its source text
        # supersedes it straight from there (contracts/cli.md, `decisions propose`).
        reopened = (
            self.state == DecisionState.PROPOSED
            and state == DecisionState.SUPERSEDED
            and self.type in _COUNT_WHEN_PROPOSED
        )
        if state not in _TRANSITIONS[self.state] and not reopened:
            raise ValueError(f"a decision cannot go from {self.state} to {state}")
        return replace(self, state=state, date=on)


@dataclass(frozen=True)
class Attachment:
    """A file, document, video, link or form on an item."""

    id: str
    kind: AttachmentKind
    name: str
    role: AttachmentRole

    @property
    def downloaded(self) -> bool:
        """Videos, links and forms are noted, never downloaded."""
        return self.kind not in _NOT_DOWNLOADED


@dataclass(frozen=True)
class Grading:
    """The return of a submission; the item's status stays in `Item.status`."""

    grading_state: GradingState
    grade: str = ""
    max_points: str = ""
    teacher_comment: str = ""
    returned_at: dt.date | None = None


@dataclass(frozen=True)
class Item:
    """A Classroom post, normalized."""

    id: str
    class_id: str
    topic_id: str | None
    type: ItemType
    title: str
    posted_at: dt.date
    modified_at: dt.date | None = None
    due_at: dt.datetime | dt.date | None = None
    status: ItemStatus | None = None
    description: str = ""
    attachments: tuple[Attachment, ...] = ()
    submission: tuple[Attachment, ...] = ()
    grading: Grading | None = None

    def __post_init__(self) -> None:
        """Reject a value the data model forbids."""
        if self.status is not None and self.type not in _WITH_STATUS:
            raise ValueError("only assignments and questions have a status")


@dataclass(frozen=True)
class Replica:
    """A copy of an attachment or text in the student's folder, unique per `(source, item, attachment)`."""

    source: str
    item: str
    attachment: str
    role: ReplicaRole
    path: str
    hash: str
    version: int = 1
    modified_seen: dt.date | None = None
    withdrawn_at: dt.date | None = None

    def __post_init__(self) -> None:
        """Reject a value the data model forbids."""
        if self.version < 1:
            raise ValueError("a replica's version starts at 1")
        if self.path.startswith("/") or any(len(part.encode()) > MAX_NAME_BYTES for part in self.path.split("/")):
            raise ValueError("a replica's path is relative and each name holds 255 UTF-8 bytes at most")

    @property
    def key(self) -> tuple[str, str, str]:
        """Its unique key."""
        return (self.source, self.item, self.attachment)


@dataclass(frozen=True)
class AgendaEntry:
    """One line of the agenda (contracts/agenda.schema.json)."""

    item: str
    subject: str
    list: AgendaList
    date_only: bool
    category: AgendaCategory
    title: str
    date: dt.datetime | dt.date | None
    classroom_link: str
    status: ItemStatus | None = None
    detected: bool = False
    origin: str | None = None
    corrected: bool = False
    folder: str = ""

    def __post_init__(self) -> None:
        """Reject a value the data model forbids."""
        if (self.origin is not None) != self.detected:
            raise ValueError("an entry has an origin exactly when it is detected")
        if self.category in _POSTED_ONLY and self.list != AgendaList.POSTED:
            raise ValueError("material and announcements go to the posted list")
        if _ACCOUNT_INDEX.search(self.classroom_link):
            raise ValueError("a Classroom link carries no /u/<n> account index")


@dataclass(frozen=True)
class Run:
    """One run's line in `data/log.jsonl`; counters only, never student data."""

    run: str
    started_at: dt.datetime
    ended_at: dt.datetime
    mode: RunMode
    result: RunResult
    reason: StopReason | None = None
    account_index: int | None = None
    classes: tuple[str, ...] = ()
    added: int = 0
    changed: int = 0
    withdrawn: int = 0
    not_fetched: Mapping[str, str] = field(default_factory=dict[str, str])
    unknown_statuses: int = 0
    pending_decisions: int = 0
    full_review: bool = False

    def __post_init__(self) -> None:
        """Reject a value the data model forbids."""
        if (self.reason is None) != (self.result == RunResult.OK):
            raise ValueError("a stopped or partial run has a reason, and an ok run has none")
        if self.ended_at < self.started_at:
            raise ValueError("a run ends after it starts")
