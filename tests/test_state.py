"""State, run log and lock (spec 001 T024). Real watchers through the command; idleness in-process."""

from __future__ import annotations

import datetime as dt
import json
import os
import signal
import subprocess
import sys
import time
from typing import TYPE_CHECKING

import pytest

from alfabeta import state
from alfabeta.model import RunMode, StopReason

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

NAME = "Alumna Inventada"
ADDRESS = "alumna.inventada@colegio.example"
CONFIG = f"""
[student]
display_name = "{NAME}"
[classroom]
account = "{ADDRESS}"
[drive]
root = 5
[sync]
full_review_days = 7
lock_idle_minutes = 30
kept_captures = 10
"""


@pytest.fixture
def home(tmp_path: Path) -> Iterator[Path]:
    for student in ("s9", "s8"):
        (tmp_path / student).mkdir()
        (tmp_path / student / "config.toml").write_text(CONFIG)
    yield tmp_path
    for student in ("s9", "s8"):  # no watcher outlives its test
        lease = state.Lock(tmp_path, tmp_path / student / "data").lease()
        if lease:
            os.kill(int(lease["pid"]), signal.SIGKILL)


def cli(home: Path, *args: str, run: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != state.RUN_ENV}
    if run is not None:
        env[state.RUN_ENV] = run
    return subprocess.run(
        [sys.executable, "-m", "alfabeta", "--home", str(home), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def take(home: Path, student: str = "s9") -> subprocess.CompletedProcess[str]:
    return cli(home, "lock", "take", "--student", student, "--mode", "interactive")


def log_lines(home: Path, student: str = "s9") -> list[dict[str, object]]:
    path = home / student / "data" / "log.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def lock_of(home: Path, student: str = "s9") -> state.Lock:
    return state.Lock(home, home / student / "data")


def test_atomic_write_and_no_rewrite_without_changes(tmp_path: Path):
    store = state.StateStore(tmp_path / "data")
    assert store.save({"items": {"synth-1": {"hash": "a"}}}) is True
    first = store.state_path.stat().st_mtime_ns
    time.sleep(0.01)
    assert store.save({"items": {"synth-1": {"hash": "a"}}}) is False
    assert store.state_path.stat().st_mtime_ns == first
    assert store.load() == {"items": {"synth-1": {"hash": "a"}}}
    assert [p.name for p in store.data_dir.iterdir()] == ["state.json"]


def test_take_stores_the_mode_and_returns_a_run(home: Path):
    done = take(home)
    assert done.returncode == 0, done.stderr
    run = json.loads(done.stdout)["run"]
    lease = lock_of(home).lease()
    assert lease is not None and lease["run"] == run and lease["mode"] == "interactive"
    assert lock_of(home).held()
    assert cli(home, "lock", "release", "--student", "s9", run=run).returncode == 0
    assert not lock_of(home).held()


def test_a_second_run_is_busy_for_the_same_student_and_for_another(home: Path):
    run = json.loads(take(home).stdout)["run"]
    for student in ("s9", "s8"):
        before = len(log_lines(home, student))
        busy = take(home, student)
        assert busy.returncode == 1 and '"lock_busy"' in busy.stdout
        lines = log_lines(home, student)[before:]
        assert [(line["result"], line["reason"]) for line in lines] == [("stopped", "lock_busy")]
    assert cli(home, "lock", "release", "--student", "s9", run=run).returncode == 0
    assert take(home, "s8").returncode == 0


def test_another_run_can_neither_renew_nor_release(home: Path):
    run = json.loads(take(home).stdout)["run"]
    for verb in ("renew", "release"):
        other = cli(home, "lock", verb, "--student", "s9", run="otro-run")
        assert other.returncode == 1 and '"lock_not_held"' in other.stdout
        missing = cli(home, "lock", verb, "--student", "s9")
        assert missing.returncode == 1 and '"lock_not_held"' in missing.stdout
    assert lock_of(home).held()
    assert cli(home, "lock", "release", "--student", "s9", run=run).returncode == 0


def test_renew_moves_the_lease_forward(home: Path):
    run = json.loads(take(home).stdout)["run"]
    before = lock_of(home).lease()
    time.sleep(0.01)
    assert cli(home, "lock", "renew", "--student", "s9", run=run).returncode == 0
    after = lock_of(home).lease()
    assert before and after and after["renewed_at"] > before["renewed_at"]
    cli(home, "lock", "release", "--student", "s9", run=run)


def test_take_reads_only_sync(home: Path):
    # [drive] root = 5 is invalid, and there is no Drive at all: the lock does not care.
    run = json.loads(take(home).stdout)["run"]
    cli(home, "lock", "release", "--student", "s9", run=run)
    (home / "s9" / "config.toml").write_text(CONFIG.replace("lock_idle_minutes = 30", 'lock_idle_minutes = "x"'))
    done = take(home)
    assert done.returncode == 1 and '"invalid_config"' in done.stdout
    assert [(line["result"], line["reason"]) for line in log_lines(home)][-1] == ("stopped", "invalid_config")
    assert not lock_of(home).held()


class FakeClock:
    def __init__(self) -> None:
        self.now = dt.datetime(2026, 10, 27, 16, 15, tzinfo=dt.UTC)

    def __call__(self) -> dt.datetime:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += dt.timedelta(minutes=10)


def test_the_watcher_releases_an_idle_lock(home: Path):
    lock, clock = lock_of(home), FakeClock()
    answers: list[str] = []
    result = state.watch(lock, "run-1", RunMode.SCHEDULED, 30, answers.append, clock, clock.sleep)
    assert result == StopReason.IDLE and answers == ["ok"]
    assert not lock.held() and lock.lease() is None
    [line] = log_lines(home)
    assert (line["run"], line["reason"], line["mode"]) == ("run-1", "idle", "scheduled")


def test_a_renewed_lock_is_not_idle(home: Path):
    lock, clock = lock_of(home), FakeClock()

    def sleep(seconds: float) -> None:
        clock.sleep(seconds)
        lease = lock.lease()
        assert lease is not None
        if clock.now < dt.datetime(2026, 10, 27, 18, 0, tzinfo=dt.UTC):
            lease["renewed_at"] = clock.now.isoformat()
            state.write_atomic(lock.lease_path, json.dumps(lease))

    assert state.watch(lock, "run-1", RunMode.SCHEDULED, 30, lambda _: None, clock, sleep) == StopReason.IDLE
    # Ticks of 10 minutes: last renewal at 17:55, idle 30 minutes later; unrenewed it would be 16:45.
    assert clock.now == dt.datetime(2026, 10, 27, 18, 25, tzinfo=dt.UTC)


def test_a_dead_watcher_leaves_no_lock(home: Path):
    take(home)
    lease = lock_of(home).lease()
    assert lease is not None
    os.kill(int(lease["pid"]), signal.SIGKILL)
    deadline = time.monotonic() + 5
    while lock_of(home).held() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not lock_of(home).held()
    assert take(home).returncode == 0
    run = lock_of(home).lease()
    assert run is not None
    cli(home, "lock", "release", "--student", "s9", run=str(run["run"]))


@pytest.mark.parametrize("reason", [r for r in StopReason if r != StopReason.IDLE])
def test_log_stop_writes_every_listed_reason(home: Path, reason: StopReason):
    (home / "s9" / "config.toml").write_text("not toml at all [")
    done = cli(home, "log", "stop", "--student", "s9", "--reason", str(reason))
    assert done.returncode == 0, done.stderr
    assert [(line["result"], line["reason"]) for line in log_lines(home)] == [("stopped", str(reason))]


@pytest.mark.parametrize("reason", ["idle", "porque_si"])
def test_log_stop_rejects_a_reason_not_in_the_list(home: Path, reason: str):
    assert cli(home, "log", "stop", "--student", "s9", "--reason", reason).returncode == 1
    assert log_lines(home) == []


def test_log_stop_releases_its_own_run(home: Path):
    run = json.loads(take(home).stdout)["run"]
    assert cli(home, "log", "stop", "--student", "s9", "--reason", "challenge", run=run).returncode == 0
    assert not lock_of(home).held()
    [line] = log_lines(home)
    assert (line["run"], line["mode"], line["reason"]) == (run, "interactive", "challenge")


def test_the_log_never_carries_the_name_or_an_address(home: Path):
    run = json.loads(take(home).stdout)["run"]
    take(home)
    cli(home, "log", "stop", "--student", "s9", "--reason", "session_expired", run=run)
    text = (home / "s9" / "data" / "log.jsonl").read_text()
    assert len(text.splitlines()) == 2
    assert NAME not in text and ADDRESS not in text and "@" not in text
