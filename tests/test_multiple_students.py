"""Two students in one `--home` (spec 001 T058, US5, SC-006): a second student is a second folder."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from alfabeta import config, state

if TYPE_CHECKING:
    from collections.abc import Iterator

REPO = Path(__file__).resolve().parents[1]
STUDENTS = ("sample", "sample2")


def cli(home: Path, *args: str, run: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != state.RUN_ENV}
    if run:
        env[state.RUN_ENV] = run
    return subprocess.run(
        [sys.executable, "-m", "alfabeta", "--home", str(home), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


@pytest.fixture
def home(tmp_path: Path) -> Iterator[Path]:
    home = tmp_path / "box"
    for student in STUDENTS:
        done = cli(home, "sandbox", "prepare", "--student", student)
        assert done.returncode == 0, done.stderr
    yield home
    for student in STUDENTS:  # no watcher outlives its test
        lease = state.Lock(home, home / student / "data").lease()
        if lease:
            os.kill(int(lease["pid"]), signal.SIGKILL)


def take(home: Path, student: str) -> str:
    done = cli(home, "lock", "take", "--student", student, "--mode", "interactive")
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)["run"]


def sync(home: Path, student: str, run: str) -> None:
    """Scenario 2 of quickstart.md for one student: captures, plan, attachments, apply."""
    for args, checked in (
        (("sandbox", "download", "--student", student, "--captures"), True),
        (("downloads", "collect", "--student", student), True),
        (("plan", "--student", student), True),
        (("sandbox", "download", "--student", student, "--batch", "0"), True),
        (("downloads", "collect", "--student", student), False),  # 1 while a later batch is pending
        (("apply", "--student", student), True),
    ):
        done = cli(home, *args, run=run)
        assert done.returncode == 0 or not checked, (args, done.stderr)


def tree(folder: Path) -> dict[str, tuple[int, int]]:
    """Every file under `folder`, with its size and modification time."""
    return {
        str(p.relative_to(folder)): (p.stat().st_size, p.stat().st_mtime_ns) for p in folder.rglob("*") if p.is_file()
    }


def git_status() -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), "status", "--porcelain", "--untracked-files=all"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_both_students_come_from_the_template_with_their_own_folders(home: Path):
    for student in STUDENTS:
        assert config.check(home, student) == ([], [])
    bases = {config.load(home, s, ("storage",)).base for s in STUDENTS}
    assert len(bases) == len(STUDENTS)
    assert not any(a in b.parents for a in bases for b in bases)


def test_syncing_one_writes_only_its_root_state_and_log(home: Path):
    repo_before = git_status()
    before = tree(home)
    run = take(home, "sample")
    sync(home, "sample", run)
    assert cli(home, "lock", "release", "--student", "sample", run=run).returncode == 0
    after = tree(home)
    changed = {path for path in before.keys() | after.keys() if before.get(path) != after.get(path)}
    own = ("drive/sample/", "sample/data/")
    assert [path for path in sorted(changed) if not path.startswith(own)] == [state.BROWSER_LOCK]
    assert any(path.startswith("drive/sample/2026-2027/") for path in changed)  # the root
    assert {"sample/data/state.json", "sample/data/log.jsonl"} <= changed
    assert not (home / "sample2" / "data" / "log.jsonl").exists()
    assert list((home / "downloads").iterdir()) == []  # the shared downloads are left as found
    assert git_status() == repo_before


def test_while_one_syncs_the_other_cannot_take_the_browser(home: Path):
    first, second = (state.Lock(home, home / s / "data") for s in STUDENTS)
    assert first.browser_lock == second.browser_lock  # one Chrome, one downloads folder
    assert first.student_lock != second.student_lock
    run = take(home, "sample")
    assert cli(home, "sandbox", "download", "--student", "sample", "--captures", run=run).returncode == 0
    assert cli(home, "downloads", "collect", "--student", "sample", run=run).returncode == 0
    running = tree(home / "sample")

    busy = cli(home, "lock", "take", "--student", "sample2", "--mode", "interactive")
    assert busy.returncode == 1 and '"lock_busy"' in busy.stdout
    lines = [json.loads(line) for line in (home / "sample2" / "data" / "log.jsonl").read_text().splitlines()]
    assert [(line["result"], line["reason"]) for line in lines] == [("stopped", "lock_busy")]
    # The first run's run id holds nothing of the other student's, and the refusal left it alone.
    other = cli(home, "plan", "--student", "sample2", run=run)
    assert other.returncode == 1 and '"lock_not_held"' in other.stdout
    assert first.held() and not second.held()
    assert tree(home / "sample") == running

    assert cli(home, "plan", "--student", "sample", run=run).returncode == 0
    assert cli(home, "lock", "release", "--student", "sample", run=run).returncode == 0
    later = take(home, "sample2")
    assert second.held() and not first.held()
    assert cli(home, "lock", "release", "--student", "sample2", run=later).returncode == 0
