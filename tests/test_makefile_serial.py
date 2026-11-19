"""The Makefile runs one job at a time, whatever `-j` asks for (issue 273).

The goals of the gate line are not independent: `setup-node` removes and reinstalls `node_modules`
while `test-js` reads it, so under a parallel make the gate failed. CI's runner sets no `-j`, and
would never notice the line going; these tests ask for four jobs themselves.

The probe adds two targets to the Makefile's text, runs both under `-j4` and reads the order in which
they started and ended. The control runs the same probe without the line and must see the two
overlap: a probe that cannot see two jobs at once would pass for any Makefile.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

MAKEFILE = Path(__file__).resolve().parents[1] / "Makefile"
SERIAL = ".NOTPARALLEL:"
PROBE = """
probe-a probe-b:
\t@echo "start-$@" >> "$(TRACE)"; sleep 0.5; echo "end-$@" >> "$(TRACE)"
"""
# What the make that runs the tests exported: a child would read its job count from them.
INHERITED = {"MAKEFLAGS", "MFLAGS", "MAKELEVEL"}


def trace(makefile: str, tmp_path: Path) -> list[str]:
    """The starts and ends of the two probe targets, in order, when make is asked for four jobs."""
    (tmp_path / "Makefile").write_text(makefile + PROBE, encoding="utf-8")
    out = tmp_path / "trace"
    env = {name: value for name, value in os.environ.items() if name not in INHERITED}
    subprocess.run(
        ["make", "-j4", f"TRACE={out}", "probe-a", "probe-b"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.read_text(encoding="utf-8").split()


def test_two_goals_of_one_invocation_never_run_at_the_same_time(tmp_path: Path):
    events = trace(MAKEFILE.read_text(encoding="utf-8"), tmp_path)
    assert events == ["start-probe-a", "end-probe-a", "start-probe-b", "end-probe-b"]


def test_control_without_the_line_the_probe_sees_two_jobs_at_once(tmp_path: Path):
    lines = MAKEFILE.read_text(encoding="utf-8").splitlines(keepends=True)
    kept = [line for line in lines if line.strip() != SERIAL]
    assert len(kept) == len(lines) - 1, f"the Makefile declares {SERIAL} exactly once, on a line of its own"
    events = trace("".join(kept), tmp_path)
    assert sorted(events[:2]) == ["start-probe-a", "start-probe-b"]
