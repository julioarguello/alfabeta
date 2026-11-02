"""The mirrors of the master folder (spec 001 FR-011a, T069; contracts/cli.md, `drive sync-mirrors`).

Each folder in `drive.mirrors` gets what is new or changed in the master, one way: nothing is
deleted from a mirror and nothing is copied back. A mirror is named by its position in the list,
never by its path, which carries the account's address (FR-031).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from alfabeta.google.keychain import run_command

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from alfabeta.google.keychain import Runner

REASONS = ("not_mounted", "copy_failed")


def sync(base: Path, mirrors: Sequence[Path], runner: Runner = run_command) -> dict[str, Any]:
    """Bring every mirror up to date from `base`; one that fails is reported and the rest go on."""
    failed: list[dict[str, Any]] = []
    for index, folder in enumerate(mirrors):
        if not folder.is_dir():
            failed.append({"index": index, "reason": "not_mounted"})
            continue
        # -rlt compares size and time, so a mirror already up to date receives no write (FR-025).
        done = runner(["rsync", "-rlt", "--exclude", ".DS_Store", f"{base}/", f"{folder}/"], None)
        if done.returncode != 0:
            failed.append({"index": index, "reason": "copy_failed"})
    return {"up_to_date": len(mirrors) - len(failed), "failed": failed}


def counts(result: dict[str, Any]) -> dict[str, int]:
    """How many mirrors are up to date and how many failed: what a log line and a summary carry."""
    return {"up_to_date": result["up_to_date"], "failed": len(result["failed"])}


def summary(result: dict[str, Any]) -> str:
    """The family's line, in Spanish, with counts only."""
    return f"espejos al día: {result['up_to_date']}, fallidos: {len(result['failed'])}"
