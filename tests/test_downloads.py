"""The downloads folder (spec 001 T040): only this run's captures and the files the plan asked for."""

from __future__ import annotations

import datetime as dt
import json
import time
from typing import TYPE_CHECKING, Any

from alfabeta.downloads import DownloadsInbox, collect, inbox_path, matches
from alfabeta.plan import write

if TYPE_CHECKING:
    from pathlib import Path


def setup(tmp_path: Path, created_at: dt.datetime | None = None) -> tuple[DownloadsInbox, dict[str, Any]]:
    downloads, data = tmp_path / "downloads", tmp_path / "data"
    downloads.mkdir()
    plan: dict[str, Any] = {
        "run": "r1",
        "created_at": (created_at or dt.datetime.now(dt.UTC) - dt.timedelta(seconds=5)).isoformat(),
        "downloads": [
            {"item": "synth-1", "attachment": "synth-a", "expected_name": "ficha.pdf", "batch": 0},
            {"item": "synth-2", "attachment": "synth-b", "expected_name": "ficha.pdf", "batch": 1},
        ],
    }
    write(plan, data)
    return DownloadsInbox(downloads, data), plan


def test_two_attachments_with_one_name_end_in_their_own_item(tmp_path: Path):
    inbox, plan = setup(tmp_path)
    (inbox.folder / "ficha.pdf").write_bytes(b"first")
    first = collect(inbox, "r1")
    assert first["collected"] == ["ficha.pdf"] and first["pending"] == ["ficha.pdf"]
    (inbox.folder / "ficha (1).pdf").write_bytes(b"second")
    second = collect(inbox, "r1")
    assert second["collected"] == ["ficha.pdf"] and second["pending"] == []
    assert inbox_path(inbox.data_dir, plan["downloads"][0]).read_bytes() == b"first"
    assert inbox_path(inbox.data_dir, plan["downloads"][1]).read_bytes() == b"second"


def test_a_file_older_than_the_plan_is_not_collected(tmp_path: Path):
    inbox, _ = setup(tmp_path, created_at=dt.datetime.now(dt.UTC) + dt.timedelta(seconds=30))
    (inbox.folder / "ficha.pdf").write_bytes(b"old")
    result = collect(inbox, "r1")
    assert result["collected"] == [] and (inbox.folder / "ficha.pdf").exists()


def test_a_half_downloaded_file_waits(tmp_path: Path):
    inbox, _ = setup(tmp_path)
    (inbox.folder / "ficha.pdf.crdownload").write_bytes(b"half")
    (inbox.folder / "ficha.pdf").write_bytes(b"")
    clock = iter(range(100))
    result = collect(inbox, "r1", wait_seconds=3, sleep=lambda _: None, clock=lambda: float(next(clock)))
    assert result["collected"] == [] and result["pending"] == ["ficha.pdf", "ficha.pdf"]


def test_only_this_runs_captures_move(tmp_path: Path):
    inbox, _ = setup(tmp_path)
    base: dict[str, Any] = {
        "version": 1,
        "type": "class",
        "captured_at": "2026-10-27T16:22:00+01:00",
        "complete": True,
        "class": {"id": "synth-1", "title": "x"},
        "topics": [],
        "items": [],
        "stream": [],
    }
    (inbox.folder / "alfabeta-capture-r1-synth-1-20261027-162200.json").write_text(json.dumps(base | {"run": "r1"}))
    (inbox.folder / "alfabeta-capture-r2-synth-1-20261027-162200.json").write_text(json.dumps(base | {"run": "r2"}))
    (inbox.folder / "alfabeta-capture-r1-synth-9-20261027-162200.json").write_text(json.dumps(base | {"run": "r2"}))
    assert collect(inbox, "r1")["classes"] == ["synth-1"]
    assert sorted(p.name for p in inbox.folder.glob("alfabeta-capture-*")) == [
        "alfabeta-capture-r1-synth-9-20261027-162200.json",  # its field says another run
        "alfabeta-capture-r2-synth-1-20261027-162200.json",
    ]


def test_names_the_browser_gives():
    assert matches("ficha.pdf", "ficha.pdf") and matches("ficha (2).pdf", "ficha.pdf")
    assert not matches("ficha (2).docx", "ficha.pdf") and not matches("otra.pdf", "ficha.pdf")
    assert not matches("ficha.pdf.crdownload", "ficha.pdf")
    time.sleep(0)
