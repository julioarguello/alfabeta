"""`notebook share`: each topic's notebook, editable by the student's accounts (spec 001 FR-011b, #233).

Every account in `notebook.share_with` is an editor of every topic notebook. The command walks the
topic folders of the school year, names each one's notebook with `notebook.title_pattern` and reads
who the notebook lists: a missing account is invited as editor, a lower role is raised, an editor is
left alone. It never removes a collaborator and never makes a notebook public. A share counts only
when the notebook lists the account as editor afterwards. An account is named by its position in the
list, never by its address (FR-031).

Measured 2026-11-12 with nlm 0.15.8: `nlm share invite <id> <account> --role editor` on an account
listed as viewer raises it to editor (`nlm share status` before and after); the invite mails a notice.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from alfabeta.notes.run import topic_name
from alfabeta.notes.sources import SourcesError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

# Roles that already edit a notebook; any other role listed is raised.
EDITING = frozenset({"editor", "owner"})
# Why an account is not an editor of a notebook: two notebooks carry the topic's title, the notebook's
# sharing could not be read, the invite was refused, or the notebook does not list it as editor after it.
REASONS = ("ambiguous", "status_failed", "refused", "not_confirmed")


class NotebookShares(Protocol):
    """Who each notebook is shared with, and the invite of one account."""

    def notebooks(self) -> list[tuple[str, str]]:
        """The id and the title of every notebook of the owner."""
        ...

    def collaborators(self, notebook: str) -> dict[str, str]:
        """The role of each address the notebook lists."""
        ...

    def invite_editor(self, notebook: str, address: str) -> None:
        """Make one account an editor of the notebook; raises a role it already holds."""
        ...


@dataclass(frozen=True)
class TopicNotebook:
    """A topic folder and the title its notebook has."""

    topic: str  # `<subject>/<topic folder>`
    title: str


def topics(year: Path, title_pattern: str, grade: str) -> list[TopicNotebook]:
    """Every topic folder of the school year, in order, with its notebook's title; hidden folders are not topics."""
    if not year.is_dir():
        return []
    found: list[TopicNotebook] = []
    for subject in sorted(p for p in year.iterdir() if p.is_dir() and not p.name.startswith(".")):
        for folder in sorted(p for p in subject.iterdir() if p.is_dir() and not p.name.startswith(".")):
            title = title_pattern.format(grade=grade, subject=subject.name, topic=topic_name(folder.name))
            found.append(TopicNotebook(f"{subject.name}/{folder.name}", title))
    return found


def share_notebooks(
    port: NotebookShares, wanted: Sequence[TopicNotebook], accounts: Sequence[str], *, dry_run: bool = False
) -> dict[str, Any]:
    """Make every account an editor of every wanted topic's notebook; one that fails is reported and the rest go on.

    A topic with no notebook is passed over. With `dry_run` nothing is invited: the counts say what would be.
    """
    report: dict[str, Any] = {
        "ok": True,
        "dry_run": dry_run,
        "notebooks": 0,
        "invited": 0,
        "raised": 0,
        "already": 0,
        "failed": [],
        "changed": [],
    }
    if not accounts or not wanted:
        return report
    by_title: dict[str, list[str]] = {}
    for notebook, title in port.notebooks():
        by_title.setdefault(title, []).append(notebook)
    failed: list[dict[str, Any]] = report["failed"]
    for topic in wanted:
        ids = by_title.get(topic.title, [])
        if not ids:
            continue
        report["notebooks"] += 1
        if len(ids) > 1:  # never a guess between two notebooks with one title
            failed += [{"topic": topic.topic, "index": i, "reason": "ambiguous"} for i in range(len(accounts))]
            continue
        outcome = _share_one(port, ids[0], accounts, dry_run=dry_run)
        for key in ("invited", "raised", "already"):
            report[key] += outcome[key]
        failed += [{"topic": topic.topic, **failure} for failure in outcome["failed"]]
        if outcome["invited"] or outcome["raised"]:
            report["changed"].append(topic.topic)
    report["ok"] = not failed
    return report


def _share_one(port: NotebookShares, notebook: str, accounts: Sequence[str], *, dry_run: bool) -> dict[str, Any]:
    """One notebook: who is invited, raised, already an editor, and who failed."""
    everyone = [{"index": i, "reason": "status_failed"} for i in range(len(accounts))]
    outcome: dict[str, Any] = {"invited": 0, "raised": 0, "already": 0, "failed": []}
    failures: list[dict[str, Any]] = []
    try:
        before = port.collaborators(notebook)
    except SourcesError:
        return outcome | {"failed": everyone}
    asked: dict[int, str] = {}  # the account's position → what the invite is for it
    for index, address in enumerate(accounts):
        role = before.get(address)
        if role in EDITING:
            outcome["already"] += 1
            continue
        kind = "raised" if role else "invited"
        if dry_run:
            outcome[kind] += 1
            continue
        try:
            port.invite_editor(notebook, address)
        except SourcesError:
            failures.append({"index": index, "reason": "refused"})
        else:
            asked[index] = kind
    if not asked:
        return outcome | {"failed": failures}
    try:
        after = port.collaborators(notebook)
    except SourcesError:
        after = {}
    for index, kind in asked.items():
        if after.get(accounts[index]) in EDITING:
            outcome[kind] += 1
        else:
            failures.append({"index": index, "reason": "not_confirmed"})
    return outcome | {"failed": sorted(failures, key=_position)}


def _position(failure: dict[str, Any]) -> int:
    return int(failure["index"])


def counts(report: dict[str, Any]) -> dict[str, int]:
    """The counts a log line carries: notebooks, and accounts invited, raised, already editors and failed."""
    return {key: report[key] for key in ("notebooks", "invited", "raised", "already")} | {
        "failed": len(report["failed"])
    }


def summary(report: dict[str, Any]) -> str:
    """The family's line, in Spanish, with counts only."""
    c = counts(report)
    lead = "simulación, nada cambiado: " if report["dry_run"] else ""
    return (
        f"{lead}{c['notebooks']} cuaderno(s) compartidos como editor: cuentas invitadas {c['invited']}, "
        f"subidas a editor {c['raised']}, ya editoras {c['already']}, fallidas {c['failed']}"
    )
