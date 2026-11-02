"""The mirrors of the master folder (spec 001 FR-011a, T068): one-way, never deleting, never named.

Every folder and file is invented; the copies are real `rsync` runs on temporary folders.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from alfabeta import mirror
from tests.test_plan_apply_us1 import Box, cli

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

needs_rsync = pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync is not installed")


def files(folder: Path) -> dict[str, tuple[int, int, int]]:
    """Each file under `folder`: size, modification second (rsync keeps whole seconds) and inode (a rewrite changes it)."""
    return {
        str(p.relative_to(folder)): (p.stat().st_size, int(p.stat().st_mtime), p.stat().st_ino)
        for p in sorted(folder.rglob("*"))
        if p.is_file()
    }


@pytest.fixture
def master(tmp_path: Path) -> Path:
    base = tmp_path / "base"
    (base / "2026-2027" / "FyQ" / "20261001 - Tema 01 - Materia inventada").mkdir(parents=True)
    (base / "2026-2027" / "FyQ" / "20261001 - Tema 01 - Materia inventada" / "apuntes.pdf").write_bytes(b"%PDF-1")
    (base / "2026-2027" / "agenda.md").write_text("# Agenda inventada\n")
    (base / ".DS_Store").write_bytes(b"finder")
    return base


@needs_rsync
def test_every_mirror_gets_the_master_with_size_and_time(master: Path, tmp_path: Path):
    mirrors = [tmp_path / "m1", tmp_path / "m2"]
    for m in mirrors:
        m.mkdir()
    assert mirror.sync(master, mirrors) == {"up_to_date": 2, "failed": []}
    expected = {k: v[:2] for k, v in files(master).items() if not k.endswith(".DS_Store")}
    for m in mirrors:
        assert {k: v[:2] for k, v in files(m).items()} == expected


@needs_rsync
def test_a_second_sync_with_no_change_writes_nothing(master: Path, tmp_path: Path):
    copy = tmp_path / "m1"
    copy.mkdir()
    mirror.sync(master, [copy])
    before = files(copy)
    assert mirror.sync(master, [copy]) == {"up_to_date": 1, "failed": []}
    assert files(copy) == before


@needs_rsync
def test_nothing_is_deleted_from_a_mirror_nor_copied_back(master: Path, tmp_path: Path):
    copy = tmp_path / "m1"
    copy.mkdir()
    mirror.sync(master, [copy])
    (master / "2026-2027" / "agenda.md").rename(master / "2026-2027" / "agenda movida.md")
    (copy / "solo en el espejo.txt").write_text("añadido a mano")
    mirror.sync(master, [copy])
    assert (copy / "2026-2027" / "agenda.md").is_file()
    assert (copy / "2026-2027" / "agenda movida.md").is_file()
    assert not (master / "solo en el espejo.txt").exists()


def test_a_mirror_not_mounted_fails_by_index_and_the_others_go_on(master: Path, tmp_path: Path):
    calls: list[list[str]] = []

    def runner(argv: list[str], stdin: str | None) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 23 if argv[-1].startswith(str(tmp_path / "broken")) else 0, "", "")

    for name in ("m0", "broken"):
        (tmp_path / name).mkdir()
    mirrors = [tmp_path / "m0", tmp_path / "absent", tmp_path / "broken"]
    result = mirror.sync(master, mirrors, runner)
    assert result == {
        "up_to_date": 1,
        "failed": [{"index": 1, "reason": "not_mounted"}, {"index": 2, "reason": "copy_failed"}],
    }
    assert calls[0] == ["rsync", "-rlt", "--exclude", ".DS_Store", f"{master}/", f"{tmp_path / 'm0'}/"]
    assert len(calls) == 2  # the absent one is never copied to
    assert mirror.counts(result) == {"up_to_date": 1, "failed": 2}


def test_no_mirrors_is_nothing_to_do(master: Path):
    assert mirror.sync(master, []) == {"up_to_date": 0, "failed": []}


@pytest.fixture
def box(tmp_path: Path) -> Iterator[Box]:
    b = Box(tmp_path / "box")
    assert cli(b.home, "sandbox", "prepare").returncode == 0
    b.take()
    yield b
    b.release()


def with_mirrors(box: Box, *mirrors: Path) -> None:
    config = box.home / "sample" / "config.toml"
    listed = ", ".join(json.dumps(str(m)) for m in mirrors)
    config.write_text(config.read_text().replace("mirrors = []", f"mirrors = [{listed}]"))


@needs_rsync
def test_sync_mirrors_reports_each_failure_and_never_a_path(box: Box, tmp_path: Path):
    copy = tmp_path / "m0"
    copy.mkdir()
    with_mirrors(box, copy, tmp_path / "absent")
    done = box("drive", "sync-mirrors", "--student", "sample")
    assert done.returncode == 1, done.stderr
    assert json.loads(done.stdout) == {"up_to_date": 1, "failed": [{"index": 1, "reason": "not_mounted"}]}
    assert {k: v[:2] for k, v in files(copy).items()} == {
        k: v[:2] for k, v in files(box.base).items() if not k.endswith(".DS_Store")
    }
    log = (box.data / "log.jsonl").read_text()
    line = json.loads(log.splitlines()[-1])
    assert (line["type"], line["result"], line["mirrors"]) == ("mirrors", "failed", {"up_to_date": 1, "failed": 1})
    for text in (done.stdout, done.stderr, log):
        assert str(tmp_path) not in text


@needs_rsync
def test_sync_mirrors_with_every_mirror_up_to_date_exits_0(box: Box, tmp_path: Path):
    (tmp_path / "m0").mkdir()
    with_mirrors(box, tmp_path / "m0")
    done = box("drive", "sync-mirrors", "--student", "sample")
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == {"up_to_date": 1, "failed": []}
    assert "espejos al día: 1, fallidos: 0" in done.stderr


def test_sync_mirrors_needs_the_lock(box: Box):
    box.release()
    done = box("drive", "sync-mirrors", "--student", "sample")
    box.take()
    assert done.returncode == 1
    assert json.loads(done.stdout)["ok"] is False


@needs_rsync
def test_classroom_apply_ends_with_the_mirrors_up_to_date(box: Box, tmp_path: Path):
    copy = tmp_path / "m0"
    copy.mkdir()
    with_mirrors(box, copy, tmp_path / "absent")
    box.collect_and_plan()
    result, summary = box.apply()
    assert result["mirrors"] == {"up_to_date": 1, "failed": 1}
    assert "espejos al día: 1, fallidos: 1" in summary
    placed = {k: v[:2] for k, v in files(box.base).items() if not k.endswith(".DS_Store")}
    assert placed and {k: v[:2] for k, v in files(copy).items()} == placed
    line = json.loads((box.data / "log.jsonl").read_text().splitlines()[-1])
    assert line["mirrors"] == {"up_to_date": 1, "failed": 1}
    assert str(tmp_path) not in summary + json.dumps(result) + json.dumps(line)
    before = files(copy)
    again, _ = box.apply()
    assert (again["added"], again["changed"]) == (0, 0)
    assert files(copy) == before  # an apply with no changes writes nothing to a mirror (FR-025)


def test_classroom_apply_with_no_mirrors_says_nothing_of_them(box: Box):
    box.collect_and_plan()
    result, summary = box.apply()
    assert result["mirrors"] == {"up_to_date": 0, "failed": 0}
    assert "espejos" not in summary
