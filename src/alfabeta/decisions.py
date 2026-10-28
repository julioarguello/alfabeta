"""Claude's proposals and the family's decisions, in `data/decisions.json` (spec 001 T038, research R7).

One decision per `(type, origin)` is in force at a time; the others are `superseded`, never deleted.
Claude proposes (class links, topic and item matches, detected exams, dismissed candidates) with a
reason and a confidence; the family confirms, rejects, corrects a detected exam or changes a match.
A proposal for a key that already has a decision in force writes nothing, except where the
contract reopens it: a rejected decision whose origin changed after the rejection, and a detected
exam or dismissed candidate whose source text changed and the family has not corrected.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, cast

from alfabeta.dates import MADRID
from alfabeta.model import Confidence, Decision, DecisionState, DecisionType
from alfabeta.state import write_atomic

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

PROPOSABLE = frozenset(DecisionType) - {DecisionType.EXAM_CORRECTION}
_HASHED = frozenset({DecisionType.DETECTED_EXAM, DecisionType.DISMISSED_CANDIDATE})


class DecisionError(ValueError):
    """A proposal that does not fit the contract, or a decision that does not exist."""


def today() -> dt.date:
    """Today in Madrid."""
    return dt.datetime.now(MADRID).date()


@dataclass(frozen=True)
class Record:
    """A decision and what its origin looked like when it was proposed."""

    decision: Decision
    origin_title: str | None = None
    book_topics: tuple[str, ...] = ()

    def as_json(self) -> dict[str, Any]:
        """Its line in `decisions.json`."""
        d = self.decision
        return {
            "type": str(d.type),
            "origin": d.origin,
            "target": dict(d.target),
            "reason": d.reason,
            "state": str(d.state),
            "date": d.date.isoformat(),
            "confidence": str(d.confidence) if d.confidence else None,
            "origin_hash": d.origin_hash,
            "origin_title": self.origin_title,
            "book_topics": list(self.book_topics),
        }

    @classmethod
    def from_json(cls, raw: dict[str, Any]) -> Record:
        """A record read back from the file."""
        decision = Decision(
            type=DecisionType(raw["type"]),
            origin=raw["origin"],
            target={str(k): str(v) for k, v in cast("dict[str, Any]", raw["target"]).items()},
            reason=raw["reason"],
            state=DecisionState(raw["state"]),
            date=dt.date.fromisoformat(raw["date"]),
            confidence=Confidence(raw["confidence"]) if raw.get("confidence") else None,
            origin_hash=raw.get("origin_hash"),
        )
        return cls(decision, raw.get("origin_title"), tuple(raw.get("book_topics") or ()))


@dataclass(frozen=True)
class Proposal:
    """One proposal from Claude, with the state of its origin now."""

    decision: Decision
    origin_title: str | None
    book_topics: tuple[str, ...]
    origin_modified: dt.date | None

    @classmethod
    def parse(cls, raw: object, on: dt.date) -> Proposal:
        """A proposal from the `--file` JSON, or DecisionError saying what does not fit."""
        if not isinstance(raw, dict):
            raise DecisionError("a proposal is a JSON object")
        p = cast("dict[str, Any]", raw)
        try:
            kind = DecisionType(p["type"])
        except (KeyError, ValueError):
            raise DecisionError("a proposal needs a type Claude can propose") from None
        if kind not in PROPOSABLE:
            raise DecisionError("only the family corrects an exam")
        if not isinstance(p.get("origin"), str) or not p["origin"]:
            raise DecisionError("a proposal needs its origin")
        if not isinstance(p.get("reason"), str) or not p["reason"].strip():
            raise DecisionError("a proposal needs its reason")
        try:
            confidence = Confidence(p["confidence"])
        except (KeyError, ValueError):
            raise DecisionError("a proposal needs a confidence: high, medium or low") from None
        target = p.get("target")
        if not isinstance(target, dict):
            raise DecisionError("a proposal needs its target")
        origin_hash = p.get("origin_hash")
        if kind in _HASHED and not origin_hash:
            raise DecisionError("a detected exam or dismissed candidate needs the hash of its text")
        modified = p.get("origin_modified")
        decision = Decision(
            type=kind,
            origin=p["origin"],
            target={str(k): str(v) for k, v in cast("dict[str, Any]", target).items()},
            reason=p["reason"].strip(),
            state=DecisionState.PROPOSED,
            date=on,
            confidence=confidence,
            origin_hash=origin_hash,
        )
        return cls(
            decision,
            p.get("origin_title"),
            tuple(p.get("book_topics") or ()),
            dt.date.fromisoformat(modified) if modified else None,
        )


@dataclass
class DecisionStore:
    """`data/decisions.json`: every decision, the superseded ones too."""

    path: Path
    records: list[Record] = field(default_factory=list[Record])

    @classmethod
    def open(cls, data_dir: Path) -> DecisionStore:
        """The student's decisions, or none yet."""
        path = data_dir / "decisions.json"
        if not path.is_file():
            return cls(path)
        raw = cast("dict[str, Any]", json.loads(path.read_text()))
        return cls(path, [Record.from_json(r) for r in raw.get("decisions", [])])

    def save(self) -> bool:
        """Write the file if it changed (FR-025)."""
        text = json.dumps({"decisions": [r.as_json() for r in self.records]}, ensure_ascii=False, indent=1)
        return write_atomic(self.path, text + "\n")

    def in_force(self, kind: DecisionType, origin: str) -> Record | None:
        """The decision of `(kind, origin)` that is not superseded, if any."""
        for record in reversed(self.records):
            d = record.decision
            if d.type == kind and d.origin == origin and d.state != DecisionState.SUPERSEDED:
                return record
        return None

    def decisions(self) -> list[Decision]:
        """Every decision in force."""
        return [r.decision for r in self.records if r.decision.state != DecisionState.SUPERSEDED]

    def _supersede(self, record: Record, on: dt.date) -> None:
        index = self.records.index(record)
        self.records[index] = replace(record, decision=record.decision.moved_to(DecisionState.SUPERSEDED, on))

    def _reopens(self, current: Record, proposal: Proposal) -> bool:
        """Whether a proposal reopens the decision in force for its key (contracts/cli.md)."""
        old, new = current.decision, proposal.decision
        if new.type in _HASHED and new.origin_hash != old.origin_hash:
            return self.in_force(DecisionType.EXAM_CORRECTION, new.origin) is None
        if old.state != DecisionState.REJECTED:
            return False
        if proposal.origin_modified is not None and proposal.origin_modified > old.date:
            return True
        if new.type == DecisionType.TOPIC_MATCH:
            title_changed = proposal.origin_title is not None and proposal.origin_title != current.origin_title
            new_book_topic = bool(set(proposal.book_topics) - set(current.book_topics))
            return title_changed or new_book_topic
        return False

    def propose(self, proposals: Iterable[Proposal], on: dt.date) -> tuple[list[Decision], list[Decision]]:
        """Record what is new; returns (recorded, ignored)."""
        recorded: list[Decision] = []
        ignored: list[Decision] = []
        for proposal in proposals:
            current = self.in_force(proposal.decision.type, proposal.decision.origin)
            if current is not None and not self._reopens(current, proposal):
                ignored.append(proposal.decision)
                continue
            if current is not None:
                self._supersede(current, on)
            self.records.append(Record(proposal.decision, proposal.origin_title, proposal.book_topics))
            recorded.append(proposal.decision)
        return recorded, ignored

    def confirm(self, kind: DecisionType, origin: str, on: dt.date, *, reject: bool = False) -> Decision:
        """Confirm or reject the proposal of `(kind, origin)`."""
        if reject and kind == DecisionType.DETECTED_EXAM:
            raise DecisionError("a detected exam is not rejected; discard it with `decisions correct --discard`")
        current = self.in_force(kind, origin)
        if current is None or current.decision.state != DecisionState.PROPOSED:
            raise DecisionError("there is no proposal of that type for that origin")
        moved = current.decision.moved_to(DecisionState.REJECTED if reject else DecisionState.CONFIRMED, on)
        self.records[self.records.index(current)] = replace(current, decision=moved)
        return moved

    def correct(self, origin: str, target: dict[str, str], on: dt.date) -> Decision:
        """The family's correction of a detected exam; it prevails in the following runs.

        One correction adds to the one before: a date and then a category keep both. Correcting the date
        or the category of a discarded exam says it is an exam after all.
        """
        if self.in_force(DecisionType.DETECTED_EXAM, origin) is None:
            raise DecisionError("there is no detected exam with that origin")
        merged = dict(target)
        previous = self.in_force(DecisionType.EXAM_CORRECTION, origin)
        if previous is not None:
            self._supersede(previous, on)
            merged = {**previous.decision.target, **target}
            if "discarded" not in target:
                merged.pop("discarded", None)
        correction = Decision(
            DecisionType.EXAM_CORRECTION, origin, merged, "corrected by the family", DecisionState.CONFIRMED, on
        )
        self.records.append(Record(correction))
        return correction

    def change(self, kind: DecisionType, origin: str, target: dict[str, str], on: dt.date) -> Decision:
        """Replace a confirmed or rejected decision with the family's new one."""
        current = self.in_force(kind, origin)
        if current is None or current.decision.state not in (DecisionState.CONFIRMED, DecisionState.REJECTED):
            raise DecisionError("there is no confirmed or rejected decision of that type for that origin")
        self._supersede(current, on)
        changed = Decision(kind, origin, target, "changed by the family", DecisionState.CONFIRMED, on)
        self.records.append(Record(changed, current.origin_title, current.book_topics))
        return changed
