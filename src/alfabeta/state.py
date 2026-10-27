"""State, run log and lock of one student (spec 001 research R6, contracts/cli.md, FR-025, FR-030).

`data/state.json` is written atomically and only when it changes. `data/log.jsonl` gets one JSON
line per run, with counters and reasons and never the student's name or an address.

The lock is two `fcntl.flock`s, the student's `data/lock` and the Mac's `<home>/.browser.lock`,
held by a detached watcher process for the whole run (research R1, S2: such a process survives the
tool call that starts it). The lease the subcommands renew lives in `data/lock.json`, a separate
file: renewing it atomically replaces that file, and replacing the flocked file would hand a
second run a fresh inode to lock. If `lock_idle_minutes` pass without a renewal the watcher writes
a `stopped` line with reason `idle` and releases both; if the watcher dies, the system releases them.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import fcntl
import json
import os
import secrets
import select
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any, cast

from alfabeta.model import RunMode, StopReason

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

RUN_ENV = "ALFABETA_RUN"
BROWSER_LOCK = ".browser.lock"
_WATCH_TICK_SECONDS = 2.0
_HANDSHAKE_SECONDS = 15.0
_RELEASE_SECONDS = 5.0


class LockError(Exception):
    """The lock is busy, not held, or held by another run."""

    def __init__(self, reason: StopReason, message: str) -> None:
        """Keep the reason the command reports."""
        super().__init__(message)
        self.reason = reason


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def write_atomic(path: Path, text: str) -> bool:
    """Replace `path` with `text` through a temporary file and a rename; False if it already holds it."""
    if path.is_file() and path.read_text() == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(text)
    temporary.replace(path)
    return True


def _dumps(data: Mapping[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


@dataclass(frozen=True)
class StateStore:
    """The student's state file and run log in their data folder."""

    data_dir: Path

    @property
    def state_path(self) -> Path:
        """`data/state.json`."""
        return self.data_dir / "state.json"

    @property
    def log_path(self) -> Path:
        """`data/log.jsonl`."""
        return self.data_dir / "log.jsonl"

    def load(self) -> dict[str, Any]:
        """The state, or an empty one before the first run."""
        if not self.state_path.is_file():
            return {}
        return cast("dict[str, Any]", json.loads(self.state_path.read_text()))

    def save(self, state: Mapping[str, Any]) -> bool:
        """Write the state if it changed; True if it was written (FR-025)."""
        return write_atomic(self.state_path, _dumps(state))

    def log(self, line: Mapping[str, Any]) -> None:
        """Append one run line to the log."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a") as handle:
            handle.write(json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n")


def stopped_line(run: str | None, reason: StopReason, lease: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The `stopped` line of a run, with what its lease knows (start, mode)."""
    line: dict[str, Any] = {"run": run, "result": "stopped", "reason": str(reason), "ended_at": _now().isoformat()}
    if lease is not None and lease.get("run") == run:
        line["started_at"] = lease["started_at"]
        line["mode"] = lease["mode"]
    return line


@dataclass(frozen=True)
class Lock:
    """The paths of one student's lock."""

    home: Path
    data_dir: Path

    @property
    def student_lock(self) -> Path:
        """`data/lock`, the student's flock."""
        return self.data_dir / "lock"

    @property
    def browser_lock(self) -> Path:
        """`<home>/.browser.lock`, shared by every student on this Mac."""
        return self.home / BROWSER_LOCK

    @property
    def lease_path(self) -> Path:
        """`data/lock.json`: run, mode, start, last renewal, collected classes, watcher pid."""
        return self.data_dir / "lock.json"

    def lease(self) -> dict[str, Any] | None:
        """The current lease, if any."""
        try:
            return cast("dict[str, Any]", json.loads(self.lease_path.read_text()))
        except (OSError, ValueError):
            return None

    def held(self) -> bool:
        """Whether some process holds the student's flock."""
        if not self.student_lock.exists():
            return False
        with self.student_lock.open("a") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return True
            fcntl.flock(handle, fcntl.LOCK_UN)
            return False

    def require(self, run: str | None) -> dict[str, Any]:
        """The lease of `run`, if that run holds the lock; else LockError(lock_not_held)."""
        lease = self.lease()
        if not run:
            raise LockError(StopReason.LOCK_NOT_HELD, f"{RUN_ENV} is not set")
        if lease is None or lease.get("run") != run or not self.held():
            raise LockError(StopReason.LOCK_NOT_HELD, "the lock is not held by this run")
        return lease

    def renew(self, run: str | None) -> dict[str, Any]:
        """Renew the lease of `run` (every subcommand that needs the lock calls this)."""
        lease = self.require(run)
        lease["renewed_at"] = _now().isoformat()
        write_atomic(self.lease_path, _dumps(lease))
        return lease

    def take(self, mode: RunMode, idle_minutes: int) -> str:
        """Start a watcher that takes both flocks; the new run's id, or LockError(lock_busy)."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        run = secrets.token_hex(8)
        watcher = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "alfabeta.state",
                str(self.home),
                str(self.data_dir),
                run,
                str(mode),
                str(idle_minutes),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            text=True,
        )
        answer = _read_line(cast("IO[str]", watcher.stdout), _HANDSHAKE_SECONDS)
        if answer != "ok":
            watcher.wait(timeout=_HANDSHAKE_SECONDS)
            raise LockError(StopReason.LOCK_BUSY, "another run holds the lock")
        return run

    def release(self, run: str | None) -> dict[str, Any]:
        """End the watcher of `run` and wait until both flocks are free."""
        lease = self.require(run)
        self.lease_path.unlink(missing_ok=True)
        with contextlib.suppress(ProcessLookupError):
            os.kill(int(lease["pid"]), signal.SIGTERM)
        deadline = time.monotonic() + _RELEASE_SECONDS
        while self.held() and time.monotonic() < deadline:
            time.sleep(0.05)
        return lease


def _read_line(stream: IO[str], timeout: float) -> str:
    ready, _, _ = select.select([stream], [], [], timeout)
    return stream.readline().strip() if ready else ""


def _try_flock(path: Path) -> IO[str] | None:
    handle = path.open("a")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    return handle


def watch(
    lock: Lock,
    run: str,
    mode: RunMode,
    idle_minutes: int,
    answer: Callable[[str], None],
    clock: Callable[[], dt.datetime] = _now,
    sleep: Callable[[float], None] = time.sleep,
) -> StopReason | None:
    """The watcher: take both flocks, keep them while the lease is renewed, release on idleness.

    Returns `idle` if it released the lock for lack of renewal, None if the run released it.
    """
    lock.data_dir.mkdir(parents=True, exist_ok=True)
    student = _try_flock(lock.student_lock)
    browser = _try_flock(lock.browser_lock) if student else None
    if student is None or browser is None:
        if student is not None:
            student.close()
        answer("busy")
        StateStore(lock.data_dir).log(stopped_line(run, StopReason.LOCK_BUSY) | {"mode": str(mode)})
        return StopReason.LOCK_BUSY
    started = clock().isoformat()
    lease: dict[str, Any] = {
        "run": run,
        "mode": str(mode),
        "started_at": started,
        "renewed_at": started,
        "classes": [],
    }
    write_atomic(lock.lease_path, _dumps(lease | {"pid": os.getpid()}))
    answer("ok")
    try:
        while True:
            sleep(_WATCH_TICK_SECONDS)
            current = lock.lease()
            if current is None or current.get("run") != run:
                return None
            renewed = dt.datetime.fromisoformat(current["renewed_at"])
            if clock() - renewed >= dt.timedelta(minutes=idle_minutes):
                StateStore(lock.data_dir).log(stopped_line(run, StopReason.IDLE, current))
                lock.lease_path.unlink(missing_ok=True)
                return StopReason.IDLE
    finally:
        browser.close()
        student.close()


def _main(argv: list[str]) -> int:
    home, data_dir, run, mode, idle = argv

    def stop(_signum: int, _frame: object) -> None:
        sys.exit(0)

    signal.signal(signal.SIGTERM, stop)

    def answer(word: str) -> None:
        print(word, flush=True)
        # Nobody reads after the handshake; a later write must not kill the watcher.
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())

    watch(Lock(Path(home), Path(data_dir)), run, RunMode(mode), int(idle), answer)
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
