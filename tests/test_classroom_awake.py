"""The Mac awake for a read (spec 006 FR-015, FR-028): the sleep meter and the keep-awake assertion."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from alfabeta.classroom import awake


def test_the_meter_counts_the_wall_time_the_mac_was_not_awake() -> None:
    now = [100.0, 50.0]
    meter = awake.SleepMeter(lambda: (now[0], now[1]))
    now[0] += 20
    now[1] += 20
    assert meter.slept() == 0 and meter.wall() == 20
    now[0] += 600  # asleep: the wall clock alone runs
    now[0] += 5
    now[1] += 5
    assert meter.slept() == 600 and meter.wall() == 625


def test_a_wall_clock_set_back_is_no_negative_sleep() -> None:
    now = [100.0, 50.0]
    meter = awake.SleepMeter(lambda: (now[0], now[1]))
    now[0] -= 30
    now[1] += 1
    assert meter.slept() == 0


def test_the_real_clocks_see_no_sleep_in_a_short_stretch() -> None:
    assert awake.SleepMeter().slept() < 1


class FakeProcess:
    def __init__(self, argv: list[str], **kw: Any) -> None:
        self.argv, self.kw = argv, kw
        self.terminated = self.waited = False
        STARTED.append(self)

    def terminate(self) -> None:
        self.terminated = True

    def wait(self, timeout: float) -> int:
        self.waited = True
        return 0


STARTED: list[FakeProcess] = []


def test_keep_awake_holds_caffeinate_for_the_block_and_ends_it(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    STARTED.clear()
    tool = tmp_path / "caffeinate"
    tool.write_text("")
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(awake, "CAFFEINATE", tool)
    monkeypatch.setattr(subprocess, "Popen", FakeProcess)
    with awake.keep_awake():
        (held,) = STARTED
        assert held.argv == [str(tool), "-i", "-s", "-w", str(os.getpid())] and not held.terminated
    assert held.terminated and held.waited


def test_keep_awake_ends_it_when_the_block_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    STARTED.clear()
    tool = tmp_path / "caffeinate"
    tool.write_text("")
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(awake, "CAFFEINATE", tool)
    monkeypatch.setattr(subprocess, "Popen", FakeProcess)
    with pytest.raises(RuntimeError), awake.keep_awake():
        raise RuntimeError("the read failed")
    assert STARTED[0].terminated


def test_without_caffeinate_the_block_runs_and_nothing_is_held(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    STARTED.clear()
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(awake, "CAFFEINATE", tmp_path / "missing")
    monkeypatch.setattr(subprocess, "Popen", FakeProcess)
    ran = False
    with awake.keep_awake():
        ran = True
    assert ran and STARTED == []


def test_a_caffeinate_that_cannot_start_holds_nothing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tool = tmp_path / "caffeinate"
    tool.write_text("")
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(awake, "CAFFEINATE", tool)

    def refuse(*_a: Any, **_k: Any) -> None:
        raise PermissionError("not executable")

    monkeypatch.setattr(subprocess, "Popen", refuse)
    ran = False
    with awake.keep_awake():
        ran = True
    assert ran
