"""Printing the exam sheets with the study pack's printer, and refreshing the mirrors (step 8).

`print_pack.py report` downloads one report and prints it to A4 PDF; it runs with this interpreter,
which has alfabeta installed, and reads the profile it is given. The mirrors are refreshed as the
pack's step 9 does: `rsync -rlt --exclude .DS_Store <base>/ <mirror>/`, never `--delete`. A mirror
that is not mounted is not written to: rsync would create the folder on the Mac's own disk.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from alfabeta.google.keychain import run_command

if TYPE_CHECKING:
    from collections.abc import Iterable

    from alfabeta.google.keychain import Runner

PRINT_PACK = Path(__file__).resolve().parents[3] / "skills" / "study-pack" / "scripts" / "print_pack.py"


class PrintPack:
    """`Printer` over `print_pack.py report`, with one `nlm` profile."""

    def __init__(self, profile: str, runner: Runner = run_command) -> None:
        self._profile = profile
        self._run = runner

    def print_report(self, notebook: str, artifact: str, out: Path, *, break_before: str = "") -> bool:
        """Print one report; True once the PDF is there."""
        argv = [sys.executable, str(PRINT_PACK), "report", notebook, artifact, str(out), "--profile", self._profile]
        if break_before:
            argv += ["--break-before", break_before]
        done = self._run(argv, None)
        # Its own lines name keys and headings, never a value; nlm's, which may hold ids, stay out.
        for line in done.stderr.splitlines():
            if line.startswith("print_pack: "):
                print(f"alfabeta: {line}", file=sys.stderr)
        return done.returncode == 0 and out.is_file()

    def pages(self, pdf: Path) -> int:
        """The PDF's page count; 0 when it cannot be read."""
        try:
            return len(PdfReader(pdf).pages)
        except (OSError, PdfReadError):
            return 0


def refresh_mirrors(base: Path, mirrors: Iterable[Path], runner: Runner = run_command) -> int:
    """Bring every mirror up to date from the base folder; how many were not."""
    failed = 0
    for mirror in mirrors:
        if not mirror.is_dir():
            failed += 1
            continue
        done = runner(["rsync", "-rlt", "--exclude", ".DS_Store", f"{base}/", f"{mirror}/"], None)
        failed += done.returncode != 0
    return failed
