"""The closed category of each item, and the exam candidates Claude judges (spec 001 T048, FR-020a, FR-020b, FR-021b).

Every item gets exactly one category, the first that fits of exam, quiz, assignment, material,
announcement. An assignment or a question is an exam when its title carries a hint of a test in
one of the student's languages; a question, or an assignment whose attachments are all forms, is a
quiz. A material or an announcement keeps its own category: the exam it may announce is not
deduced here but by Claude, from a candidate this module lists, and becomes an agenda entry of its
own (`<item>#exam-<k>`). A candidate is an announcement or a material whose text carries a hint; it
stays pending until a decision in force was taken on that same text (`origin_hash`).
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from alfabeta.model import AgendaCategory, AttachmentKind, DecisionState, DecisionType, ItemType

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from alfabeta.model import Decision, Item

# Words that name a test, per language code of `[student] languages`, written without accents and
# matched as whole words, whatever their case or accents. Not measured on Classroom: the smallest
# set that names a test in either language of the sample student; a language missing here gives none.
EXAM_HINTS: Mapping[str, tuple[str, ...]] = {
    "es": ("examen", "examenes", "prueba", "pruebas", "control", "controles", "test", "tests"),
    "en": ("exam", "exams", "test", "tests"),
}
# The `type` of a candidate in `plan.json`'s `pending_decisions`.
CANDIDATE = "exam_candidate"
_SOURCES = frozenset({ItemType.MATERIAL, ItemType.ANNOUNCEMENT})


def _fold(text: str) -> str:
    """`text` in lower case and without accents, so «EXÁMENES» reads as «examenes»."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def candidate_text(item: Item) -> str:
    """The text an exam is deduced from: an announcement's own text, or a material's title and description."""
    if item.type == ItemType.ANNOUNCEMENT:
        return item.description
    return f"{item.title}\n{item.description}"


def text_hash(item: Item) -> str:
    """The SHA-256 of `candidate_text`: the `origin_hash` of the decisions taken on it."""
    return hashlib.sha256(candidate_text(item).encode()).hexdigest()


@dataclass(frozen=True)
class Classifier:
    """Categories and exam candidates for one student's languages."""

    languages: tuple[str, ...]
    _hint: re.Pattern[str] | None = field(init=False, repr=False, compare=False, default=None)

    def __post_init__(self) -> None:
        """Compile the hints of the student's languages into one whole-word pattern."""
        words = sorted({w for code in self.languages for w in EXAM_HINTS.get(code, ())})
        pattern = re.compile(rf"\b(?:{'|'.join(map(re.escape, words))})\b") if words else None
        object.__setattr__(self, "_hint", pattern)

    def hints(self, text: str) -> bool:
        """Whether `text` names a test in one of the student's languages."""
        return self._hint is not None and self._hint.search(_fold(text)) is not None

    def category(self, item: Item) -> AgendaCategory:
        """The one category of `item` (FR-020a)."""
        if item.type == ItemType.MATERIAL:
            return AgendaCategory.MATERIAL
        if item.type == ItemType.ANNOUNCEMENT:
            return AgendaCategory.ANNOUNCEMENT
        found = {AgendaCategory.QUIZ if item.type == ItemType.QUESTION else AgendaCategory.ASSIGNMENT}
        if item.attachments and all(a.kind == AttachmentKind.FORM for a in item.attachments):
            found.add(AgendaCategory.QUIZ)
        if self.hints(item.title):
            found.add(AgendaCategory.EXAM)
        return AgendaCategory.pick(found)

    def candidates(self, items: Iterable[Item], decisions: Iterable[Decision]) -> list[dict[str, Any]]:
        """The pending exam candidates among `items`, one per item, for `plan.json` (T048).

        Claude reads each one and proposes a `detected_exam` per exam it announces (origin
        `<item>#exam-<k>`) or a `dismissed_candidate` (origin `<item>`), copying its `origin_hash`.
        """
        in_force = [d for d in decisions if d.state != DecisionState.SUPERSEDED]
        pending: list[dict[str, Any]] = []
        for item in items:
            if item.type not in _SOURCES or not self.hints(candidate_text(item)):
                continue
            digest = text_hash(item)
            if _settled(item.id, digest, in_force):
                continue
            pending.append(
                {
                    "type": CANDIDATE,
                    "origin": item.id,
                    "title": item.title,
                    "text": item.description,
                    "posted_at": item.posted_at.isoformat(),
                    "origin_hash": digest,
                }
            )
        return pending


def _settled(item: str, digest: str, in_force: list[Decision]) -> bool:
    """Whether a decision in force was taken on this text of `item`.

    A rejected dismissal does not count, and a decision on an older text counts only if the family
    corrected that exam (contracts/cli.md, `decisions propose`).
    """
    corrected = {d.origin for d in in_force if d.type == DecisionType.EXAM_CORRECTION}
    dismissed = any(
        d.type == DecisionType.DISMISSED_CANDIDATE
        and d.origin == item
        and d.state != DecisionState.REJECTED
        and d.origin_hash == digest
        for d in in_force
    )
    detected = any(
        d.type == DecisionType.DETECTED_EXAM
        and d.origin.startswith(f"{item}#exam-")
        and (d.origin_hash == digest or d.origin in corrected)
        for d in in_force
    )
    return dismissed or detected
