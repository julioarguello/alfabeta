"""The Mac awake for a read (spec 006 FR-015, FR-028): the sleep a run can measure, and the assertion it holds.

A Mac asleep runs a process only in its short maintenance wakes (DarkWake), a few seconds each: the
scheduled read of 2026-11-26 started in one at 15:19, the lid closed, and Classroom's home did not
load in either of its tries. The wall clock keeps time across a sleep; `time.monotonic` does not
(on macOS it is `mach_absolute_time`), so over a stretch the wall time less the monotonic time is
the time the Mac slept in it: `SleepMeter`. Fail open: a meter only reads two clocks.

`keep_awake` holds `caffeinate -i -s` while the read runs: it keeps an idle Mac awake, and on power
a system sleep away too. It never keeps awake a Mac whose lid is closed with no external display:
macOS sleeps it anyway (`AppleClamshellCausesSleep`). Where `caffeinate` cannot start, nothing is
held and the read goes on as before.
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

CAFFEINATE = Path("/usr/bin/caffeinate")


def clocks() -> tuple[float, float]:
    """The wall time and the Mac's awake time, in seconds."""
    return time.time(), time.monotonic()


@dataclass
class SleepMeter:
    """The seconds the Mac slept since the meter started."""

    read: Callable[[], tuple[float, float]] = clocks
    _start: tuple[float, float] = field(init=False)

    def __post_init__(self) -> None:
        """Start measuring."""
        self._start = self.read()

    def wall(self) -> float:
        """The wall seconds since the start."""
        return self.read()[0] - self._start[0]

    def slept(self) -> float:
        """The wall seconds since the start that the Mac was not awake; never negative."""
        wall, awake = self.read()
        return max(0.0, (wall - self._start[0]) - (awake - self._start[1]))


@contextlib.contextmanager
def keep_awake() -> Generator[None]:
    """Hold an idle-sleep assertion for the block; nothing where `caffeinate` cannot start."""
    if sys.platform != "darwin" or not CAFFEINATE.exists():
        yield
        return
    try:
        # `-w`: the assertion ends with this process, whatever ends it.
        held = subprocess.Popen(
            [str(CAFFEINATE), "-i", "-s", "-w", str(os.getpid())],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        yield
        return
    try:
        yield
    finally:
        held.terminate()
        with contextlib.suppress(Exception):
            held.wait(timeout=5)
