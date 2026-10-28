"""The JSON and exit codes of `notes run`, `notebook setup` and `claude key set` (spec 005 T020)."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest

from alfabeta import __main__, config
from alfabeta.google.accounts import LinkError
from alfabeta.notes import cli
from alfabeta.notes.model import PhotoState, RanOn
from alfabeta.notes.run import COUNTS
from alfabeta.notes.sources import SourcesError
from alfabeta.notes.transcribe import Transcription, claude_key_name
from tests.conftest import CONFIG, MemoryStore
from tests.notes_fakes import MemoryDrive, ScriptedFeed, ScriptedTranscriber, deps, fixed
from tests.test_notes_setup import TITLE, FakeNotebook, SetupDriveFake, drive_with_photo

NOTES_TABLES = """
[student]
display_name = "Alumna Inventada"
school_year = "2026-2027"
grade_level = "3º ESO"
languages = ["es", "en"]

[drive]
root = "alfabeta"
mirrors = []

[notebook]
enabled = false
share_with = []
title_pattern = "{grade}. {subject}. {topic}"
nlm_profile = "prueba"
owner = "familia@example.com"
refresh_minutes = 15

[notes]
model = "claude-sonnet-5-5"
price_in = 2.0
price_out = 10.0
warn_pages = 100
cloud_stale_hours = 2
"""


@pytest.fixture
def cfg(tmp_path: Path) -> config.StudentConfig:
    (tmp_path / "s9").mkdir()
    (tmp_path / "s9" / "config.toml").write_text(CONFIG + NOTES_TABLES)
    return config.load(tmp_path, "s9", __main__.TABLES["notebook"])


def out(capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    return json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def test_notes_run_prints_the_report(cfg: config.StudentConfig, capsys: pytest.CaptureFixture[str]):
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    code = cli.cmd_notes_run(
        cfg,
        MemoryStore(),
        factory=fixed(deps(drive, ScriptedFeed(drive, [["foto-1"]]), ScriptedTranscriber()), drive),
    )
    report = out(capsys)
    assert code == 0
    assert set(report) == {"ok", "topics", "budget_wait", "no_key", "spend"}
    assert set(report["topics"][0]) == {"topic", *COUNTS}
    assert report["topics"][0]["topic"] == 0


def test_a_spent_budget_exits_0(cfg: config.StudentConfig, capsys: pytest.CaptureFixture[str]):
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    tr = ScriptedTranscriber([Transcription(PhotoState.BUDGET_WAIT)])
    code = cli.cmd_notes_run(
        cfg, MemoryStore(), factory=fixed(deps(drive, ScriptedFeed(drive, [["foto-1"]]), tr), drive)
    )
    assert (code, out(capsys)["budget_wait"]) == (0, 1)


@pytest.mark.parametrize(("ran_on", "code"), [(RanOn.MAC, 0), (RanOn.CLOUD, 3)])
def test_no_key_exits_0_on_the_mac_and_3_in_the_cloud(
    cfg: config.StudentConfig, ran_on: RanOn, code: int, capsys: pytest.CaptureFixture[str]
):
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    assert (
        cli.cmd_notes_run(
            cfg, MemoryStore(), ran_on, fixed(deps(drive, ScriptedFeed(drive, [["foto-1"]]), None), drive)
        )
        == code
    )
    assert out(capsys)["no_key"]


def test_an_unusable_link_exits_2(cfg: config.StudentConfig, capsys: pytest.CaptureFixture[str]):
    def broken(*_: object):
        raise LinkError("invalid_grant")

    assert cli.cmd_notes_run(cfg, MemoryStore(), factory=broken) == 2
    assert out(capsys) == {"ok": False, "reason": "invalid_grant"}


def test_setup_prints_states_and_counts(cfg: config.StudentConfig, capsys: pytest.CaptureFixture[str]):
    drive = drive_with_photo()
    nb = FakeNotebook(notebooks={TITLE: "nb-1"})
    code = cli.cmd_notebook_setup(
        cfg,
        MemoryStore(),
        "FyQ/20260915 - Tema 01 - Materia inventada",
        factory=fixed(deps(drive, ScriptedFeed(drive, [["foto-1"]]), ScriptedTranscriber()), drive),
        sources=lambda profile: nb,
    )
    printed = out(capsys)
    assert code == 0
    assert printed == {
        "ok": True,
        "notes_source": "created",
        "classroom_source": "created",
        "plain_sources_to_remove": 1,
    }
    assert "familia@example.com" not in json.dumps(printed)


@pytest.mark.parametrize(
    ("error", "code", "reason"),
    [(SourcesError(signed_out=True), 5, "nlm_signed_out"), (SourcesError(signed_out=False), 3, "nlm_failed")],
)
def test_setup_tells_signed_out_apart(
    cfg: config.StudentConfig, capsys: pytest.CaptureFixture[str], error: SourcesError, code: int, reason: str
):
    class Broken(FakeNotebook):
        def find_notebook(self, title: str) -> str | None:
            raise error

    drive = drive_with_photo()
    assert (
        cli.cmd_notebook_setup(
            cfg,
            MemoryStore(),
            "FyQ/20260915 - Tema 01 - Materia inventada",
            factory=fixed(deps(drive, ScriptedFeed(drive, []), None), drive),
            sources=lambda p: Broken(),
        )
        == code
    )
    assert out(capsys)["reason"] == reason


def test_an_unknown_topic_exits_1_before_asking_the_notebook(
    cfg: config.StudentConfig, capsys: pytest.CaptureFixture[str]
):
    drive = SetupDriveFake()
    code = cli.cmd_notebook_setup(
        cfg,
        MemoryStore(),
        "FyQ/x",
        factory=fixed(deps(drive, ScriptedFeed(drive, []), None), drive),
        sources=lambda p: FakeNotebook(),
    )
    assert (code, out(capsys)["reason"]) == (1, "no_topic")


def test_no_notebook_exits_1(cfg: config.StudentConfig, capsys: pytest.CaptureFixture[str]):
    drive = drive_with_photo()
    code = cli.cmd_notebook_setup(
        cfg,
        MemoryStore(),
        "FyQ/20260915 - Tema 01 - Materia inventada",
        factory=fixed(deps(drive, ScriptedFeed(drive, []), None), drive),
        sources=lambda p: FakeNotebook(notebooks={}),
    )
    assert (code, out(capsys)["reason"]) == (1, "no_notebook")


def test_claude_key_set_reads_stdin_and_refuses_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    (tmp_path / "s9").mkdir()
    store = MemoryStore()
    monkeypatch.setattr(__main__, "KeychainStore", lambda: store)
    monkeypatch.setattr("sys.stdin", io.StringIO("  sk-ant-clave-inventada\n"))
    assert __main__.main(["--home", str(tmp_path), "claude", "key", "set", "--student", "s9"]) == 0
    assert store.get(claude_key_name("s9")) == "sk-ant-clave-inventada"
    assert "sk-ant" not in capsys.readouterr().out
    monkeypatch.setattr("sys.stdin", io.StringIO("\n"))
    assert __main__.main(["--home", str(tmp_path), "claude", "key", "set", "--student", "s9"]) == 1
    assert out(capsys)["reason"] == "empty_key"
