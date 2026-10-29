"""The Mac's watch over what the cloud run leaves in Drive (spec 005 T036; research R8, R13).

The Mac's sync opens the student's Drive at the root (`ScopedDrive.open_root`, no tree walk), lists
`reports/` alone, records every report it has not listed before in `notes-reports.json` of the
student's data folder (constitution V: its own record), and hands spec 001's agenda one line per
report, newest first, under «Informes de apuntes». The record is the only source of those lines, so
`agenda.md` stays a function of the records and never of the day it is written. A record that cannot
be read counts as empty and is written again whole. T026 adds here the check that the cloud ran
recently (FR-017).
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

from alfabeta.agenda import shown
from alfabeta.dates import MADRID
from alfabeta.notes.report import REPORTS_FOLDER
from alfabeta.state import write_atomic

if TYPE_CHECKING:
    from pathlib import Path

    from alfabeta.google.drive import DriveFile

RECORD = "notes-reports.json"
VERSION = 1
# How many reports the agenda shows; the record keeps them all.
SHOWN = 10
REPORT_LABEL = "informe de apuntes"
_NAMED = re.compile(r"^Informe (\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})\.md$")


class ReportsDrive(Protocol):
    """What listing `reports/` needs of spec 004's `ScopedDrive`."""

    @property
    def root(self) -> DriveFile:
        """The alfabeta folder."""
        ...

    def lookup(self, folder_id: str, name: str) -> DriveFile | None:
        """The item with that name in the folder, asked of Drive now."""
        ...

    def listing(self, folder_id: str) -> list[DriveFile]:
        """What is directly inside the folder, asked of Drive now."""
        ...


@dataclass(frozen=True)
class SeenReport:
    """One report the Mac has listed."""

    file_id: str
    name: str

    @property
    def written(self) -> dt.datetime | None:
        """The run's instant, from the name alfabeta gave the report; None for another name."""
        named = _NAMED.match(self.name)
        if named is None:
            return None
        year, month, day, hour, minute = (int(g) for g in named.groups())
        try:
            return dt.datetime(year, month, day, hour, minute, tzinfo=MADRID)
        except ValueError:
            return None

    def link(self) -> str:
        """Where the family opens it."""
        return f"https://drive.google.com/file/d/{self.file_id}/view"


def load_seen(data_dir: Path) -> list[SeenReport]:
    """Every report recorded so far, in the order recorded."""
    path = data_dir / RECORD
    if not path.is_file():
        return []
    try:
        data = cast("dict[str, Any]", json.loads(path.read_text()))
        rows = cast("list[dict[str, Any]]", data.get("reports", []))
        return [SeenReport(str(r["id"]), str(r["name"])) for r in rows]
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return []  # unreadable: the next listing records every report again (constitution V)


def _save(data_dir: Path, seen: list[SeenReport]) -> None:
    document = {"version": VERSION, "reports": [{"id": r.file_id, "name": r.name} for r in seen]}
    write_atomic(data_dir / RECORD, json.dumps(document, ensure_ascii=False, indent=1) + "\n")


def list_reports(drive: ReportsDrive, data_dir: Path) -> list[SeenReport]:
    """Record the reports in `reports/` not listed before; returns the new ones (T036)."""
    folder = drive.lookup(drive.root.id, REPORTS_FOLDER)
    if folder is None or not folder.is_folder:
        return []
    seen = load_seen(data_dir)
    known = {r.file_id for r in seen}
    new = [SeenReport(f.id, f.name) for f in drive.listing(folder.id) if not f.is_folder and f.id not in known]
    if new:
        _save(data_dir, [*seen, *new])
    return new


def report_lines(data_dir: Path, limit: int = SHOWN) -> list[str]:
    """The agenda's lines for the newest `limit` reports recorded, newest first, in Spanish."""
    seen = sorted(load_seen(data_dir), key=lambda r: (r.written or dt.datetime.min.replace(tzinfo=MADRID), r.name))
    lines: list[str] = []
    for found in reversed(seen[-limit:]):
        when = found.written
        parts = [shown(when) if when else found.name.removesuffix(".md"), REPORT_LABEL, f"[abrir]({found.link()})"]
        lines.append(" · ".join(parts))
    return lines
