"""Printing the exam sheets with the study pack's printer (step 8).

`print_pack.py report` downloads one report and prints it to A4 PDF; it runs with this interpreter,
which has alfabeta installed, and reads the profile it is given. The student's other accounts see the
sheets through the shared school-year folder (spec 001 FR-011a): nothing is copied to them.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from alfabeta.google.keychain import run_command

if TYPE_CHECKING:
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

    def pages(self, pdf: Path) -> int | None:
        """The PDF's page count; None when it cannot be read."""
        try:
            return len(PdfReader(pdf).pages)
        except (OSError, PdfReadError):
            return None
