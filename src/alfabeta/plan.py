"""The plan of a run: what to download, what each item becomes and what needs a decision (spec 001 T039).

`plan` reads the latest capture of each class in scope, the state and the decisions, and writes
`data/plan.json`. It downloads only what is new, what the teacher modified after the last replica,
what changed name, or everything when the periodic full review is due (FR-026, research R3/S1).
Two attachments with the same expected name never share a batch, so each downloaded file has one
owner. Exam candidates and the matches of topics that span several book topics arrive with US2.
"""

from __future__ import annotations

import datetime as dt
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, cast

from alfabeta import capture
from alfabeta.dates import MADRID
from alfabeta.model import AttachmentKind, DecisionState, DecisionType, Item, ReplicaRole, Subject
from alfabeta.placement import Placer, book_topics
from alfabeta.sources import CLASSROOM
from alfabeta.state import write_atomic

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from alfabeta.capture import ClassCapture
    from alfabeta.decisions import DecisionStore

# Where Drive serves each kind (research R3, spike S1, measured 2026-10-26).
_EXPORT = {"document": "document", "presentation": "presentation", "spreadsheet": "spreadsheets"}
# What US1 places; the student's submissions and the grading arrive with US6.
US1_ROLES = frozenset(
    {ReplicaRole.STATEMENT, ReplicaRole.MATERIAL, ReplicaRole.DESCRIPTION, ReplicaRole.LINKS, ReplicaRole.ANNOUNCEMENT}
)


class PlanError(ValueError):
    """The plan cannot be made; `reason` is the run's stop reason."""

    def __init__(self, reason: str, message: str) -> None:
        """Keep the reason the command reports."""
        super().__init__(message)
        self.reason = reason


def download_url(attachment: dict[str, Any], account_index: int) -> str | None:
    """The URL that leaves the file in the downloads folder, or None for what is never downloaded."""
    kind = attachment["kind"]
    if kind == AttachmentKind.FILE:
        return f"https://drive.usercontent.google.com/download?id={attachment['id']}&export=download&authuser={account_index}"
    if kind == AttachmentKind.GOOGLE_DOC:
        doc_type = _EXPORT.get(attachment.get("google_type") or "", "document")
        if doc_type == "presentation":
            return f"https://docs.google.com/presentation/d/{attachment['id']}/export/pdf?authuser={account_index}"
        return f"https://docs.google.com/{doc_type}/d/{attachment['id']}/export?format=pdf&authuser={account_index}"
    return None


def expected_name(name: str, kind: str) -> str:
    """The name the browser gives the download: Google files arrive as PDF."""
    if kind == AttachmentKind.GOOGLE_DOC and PurePosixPath(name).suffix.lower() != ".pdf":
        return f"{name}.pdf"
    return name


def latest_captures(captures_dir: Path) -> dict[str, dict[str, Any]]:
    """The newest capture of each class, and the newest class list under the key `classes`."""
    newest: dict[str, dict[str, Any]] = {}
    for path in sorted(captures_dir.glob("alfabeta-capture-*.json")):
        try:
            data = capture.read(path)
        except capture.CaptureError:
            continue
        key = data["class"]["id"] if data["type"] == "class" else data["type"]
        if data["type"] == "stop":
            continue
        if key not in newest or data["captured_at"] > newest[key]["captured_at"]:
            newest[key] = data
    return newest


def last_full_review(log_path: Path) -> dt.date | None:
    """The date of the last run line with `full_review: true` (research R3, not a state field)."""
    if not log_path.is_file():
        return None
    found: dt.date | None = None
    for line in log_path.read_text().splitlines():
        try:
            entry = cast("dict[str, Any]", json.loads(line))
        except ValueError:
            continue
        if entry.get("full_review") and entry.get("ended_at"):
            found = dt.datetime.fromisoformat(str(entry["ended_at"])).date()
    return found


@dataclass
class Planner:
    """Sources + state + decisions → plan, for one student."""

    school_year: str
    subjects: Sequence[Subject]
    base: Path
    decisions: DecisionStore
    state: dict[str, Any]
    full_review_days: int
    today: dt.date
    last_review: dt.date | None = None
    _plan: dict[str, Any] = field(init=False, default_factory=dict[str, Any])

    def linked_classes(self) -> dict[str, Subject]:
        """Class id → subject, from the confirmed class links."""
        by_folder = {s.folder: s for s in self.subjects}
        links: dict[str, Subject] = {}
        for d in self.decisions.decisions():
            subject = by_folder.get(d.target.get("subject", ""))
            if d.type == DecisionType.CLASS_LINK and d.state == DecisionState.CONFIRMED and subject:
                links[d.origin] = subject
        return links

    @property
    def full_review(self) -> bool:
        """Whether every attachment is downloaded again in this run."""
        return self.last_review is None or (self.today - self.last_review).days >= self.full_review_days

    def _replica(self, item: str, attachment: str) -> dict[str, Any] | None:
        replicas = cast("dict[str, Any]", self.state.get("replicas", {}))
        return cast("dict[str, Any] | None", replicas.get(f"{CLASSROOM}|{item}|{attachment}"))

    def _why(self, item: Item, attachment: dict[str, Any]) -> str | None:
        """Why this attachment is downloaded now, or None (FR-026)."""
        replica = self._replica(item.id, attachment["id"])
        if replica is None:
            return "new"
        seen = replica.get("modified_seen")
        if item.modified_at and (not seen or item.modified_at > dt.date.fromisoformat(seen)):
            return "modified"
        if replica.get("name") != attachment["name"] or replica.get("kind") != attachment["kind"]:
            return "renamed"
        return "review" if self.full_review else None

    def _pending_classes(self, classes: dict[str, Any] | None) -> list[dict[str, Any]]:
        linked = {d.origin for d in self.decisions.decisions() if d.type == DecisionType.CLASS_LINK}
        listed = cast("list[dict[str, Any]]", classes["classes"]) if classes else []
        return [
            {
                "type": str(DecisionType.CLASS_LINK),
                "origin": c["id"],
                "title": c["title"],
                "visibility": c["visibility"],
            }
            for c in listed
            if c["id"] not in linked
        ]

    def _pending_topics(self, normalized: ClassCapture, subject: Subject, book: list[str]) -> list[dict[str, Any]]:
        if not subject.book:
            return []
        pending: list[dict[str, Any]] = []
        for topic_id, title in normalized.topics.items():
            record = self.decisions.in_force(DecisionType.TOPIC_MATCH, topic_id)
            if record is not None:
                if record.decision.state != DecisionState.REJECTED:
                    continue
                reopened = record.origin_title != title or bool(set(book) - set(record.book_topics))
                if not reopened:
                    continue
            pending.append(
                {"type": str(DecisionType.TOPIC_MATCH), "origin": topic_id, "title": title, "book_topics": book}
            )
        return pending

    def plan(self, captures: dict[str, dict[str, Any]], scope: Iterable[str], run: str) -> dict[str, Any]:
        """The plan for the classes in `scope`."""
        links = self.linked_classes()
        classes = captures.get("classes")
        account = int(classes["account_index"]) if classes else 0
        downloads: list[dict[str, Any]] = []
        changes: list[dict[str, Any]] = []
        pending = self._pending_classes(classes)
        for class_id in sorted(scope):
            raw = captures.get(class_id)
            subject = links.get(class_id)
            if raw is None or subject is None:
                continue
            if not _in_school_year(raw, self.school_year):
                raise PlanError("invalid_config", "a capture was taken outside the configured school year")
            normalized = capture.normalize_class(raw, self.school_year)
            subject_dir = self.base / self.school_year / subject.folder
            book = book_topics(subject_dir, subject.book)
            pending += self._pending_topics(normalized, subject, book)
            existing = [p.name for p in subject_dir.iterdir() if p.is_dir()] if subject_dir.is_dir() else []
            placer = Placer(self.school_year, subject, existing, self.decisions.decisions())
            items = sorted(normalized.items, key=lambda i: (i.posted_at, i.id))
            raw_attachments = _raw_attachments(raw)
            for item in items:
                placed = placer.place(item, normalized.topics.get(item.topic_id or ""))
                targets = [t for t in placed if t.role in US1_ROLES]
                for target in targets:
                    changes.append(
                        {
                            "item": item.id,
                            "attachment": target.attachment,
                            "role": str(target.role),
                            "path": target.path,
                        }
                    )
                for target in targets:
                    if not target.attachment or target.role == ReplicaRole.LINKS:
                        continue
                    attachment = raw_attachments.get((item.id, target.attachment))
                    url = download_url(attachment, account) if attachment else None
                    why = self._why(item, attachment) if attachment and url else None
                    if attachment and url and why:
                        downloads.append(
                            {
                                "class": class_id,
                                "item": item.id,
                                "attachment": attachment["id"],
                                "url": url,
                                "expected_name": expected_name(attachment["name"], attachment["kind"]),
                                "why": why,
                            }
                        )
        seen: Counter[str] = Counter()
        for download in downloads:
            download["batch"] = seen[download["expected_name"]]
            seen[download["expected_name"]] += 1
        return {
            "run": run,
            "created_at": dt.datetime.now(MADRID).isoformat(),
            "full_review": self.full_review,
            "downloads": downloads,
            "changes": changes,
            "pending_decisions": pending,
        }


def _raw_attachments(raw: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    found: dict[tuple[str, str], dict[str, Any]] = {}
    for item in cast("list[dict[str, Any]]", raw["items"]):
        detail = cast("dict[str, Any] | None", item.get("detail")) or {}
        for key in ("attachments", "submission"):
            for attachment in cast("list[dict[str, Any]]", detail.get(key) or []):
                found[(str(item["id"]), str(attachment["id"]))] = attachment
    for post in cast("list[dict[str, Any]]", raw["stream"]):
        for attachment in cast("list[dict[str, Any]]", post.get("attachments") or []):
            found[(str(post["id"]), str(attachment["id"]))] = attachment
    return found


def _in_school_year(raw: dict[str, Any], school_year: str) -> bool:
    first = int(school_year[:4])
    day = capture.captured_at(raw).date()
    return dt.date(first, 9, 1) <= day <= dt.date(first + 1, 8, 31)


def write(plan: dict[str, Any], data_dir: Path) -> Path:
    """`data/plan.json`."""
    path = data_dir / "plan.json"
    write_atomic(path, json.dumps(plan, ensure_ascii=False, indent=1) + "\n")
    return path
