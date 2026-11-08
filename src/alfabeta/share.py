"""The school-year folder shared with the student's other accounts (spec 001 FR-011a, #220).

Each account in `drive.share_with` can edit the school-year folder of the master Drive, so it sees the
same files the moment they are written, with no copy. alfabeta adds a missing permission and raises a
lower one; it never removes one. The alfabeta root is not shared: the state folder and the reports
stay the family's (constitution VII). An account is named by its position in the list, never by its
address (FR-031).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from alfabeta.google.drive import DriveError, OutsideFolderError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from alfabeta.google.drive import ScopedDrive

# Why an account did not get the folder: no school-year folder in Drive yet, Drive refused the share
# (the other account's domain may not take shares from outside), or another answer from Drive.
REASONS = ("no_folder", "refused", "failed", "not_reached")


def share(drive: ScopedDrive, school_year: str, accounts: Sequence[str]) -> dict[str, Any]:
    """Make sure every account can edit the school-year folder; one that fails is reported and the rest go on."""
    if not accounts:
        return {"shared": 0, "failed": []}
    try:
        folder = drive.lookup(drive.root.id, school_year)
    except DriveError:
        return not_reached(len(accounts), "failed")
    if folder is None or not folder.is_folder:
        return not_reached(len(accounts), "no_folder")
    failed: list[dict[str, Any]] = []
    for index, address in enumerate(accounts):
        try:
            drive.share_writer(folder.id, address)
        except DriveError as err:
            failed.append({"index": index, "reason": "refused" if err.status == 403 else "failed"})
        except OutsideFolderError:
            failed.append({"index": index, "reason": "failed"})
    return {"shared": len(accounts) - len(failed), "failed": failed}


def not_reached(count: int, reason: str = "not_reached") -> dict[str, Any]:
    """Every account failed for the same reason: Drive was not reached, or had no folder to share."""
    return {"shared": 0, "failed": [{"index": i, "reason": reason} for i in range(count)]}


def counts(result: dict[str, Any]) -> dict[str, int]:
    """How many accounts can edit the folder and how many failed: what a log line and a summary carry."""
    return {"shared": result["shared"], "failed": len(result["failed"])}


def summary(result: dict[str, Any]) -> str:
    """The family's line, in Spanish, with counts only."""
    return f"carpeta del curso compartida con {result['shared']} cuenta(s), fallidas: {len(result['failed'])}"
