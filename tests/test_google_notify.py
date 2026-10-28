"""A lost link is loud, never silent (spec 004 T014, US4, FR-013…FR-015, research R9)."""

import datetime as dt
import subprocess
from pathlib import Path

import pytest

from alfabeta import __main__, config
from alfabeta.google import accounts, notify
from tests.conftest import SCHOOL_ADDRESS, STUDENT_ADDRESS, FakeTransport, MemoryStore, json_response

TODAY = dt.date(2026, 10, 27)
REVOKED = {"error": "invalid_grant", "error_description": "Token has been expired or revoked."}


class Recorder:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def notify(self, text: str) -> None:
        self.texts.append(text)


@pytest.fixture
def cfg(home: Path) -> config.StudentConfig:
    return config.load(home, "s9", ("classroom", "calendar", "google"))


def test_a_failed_link_notifies_once_naming_the_alias_only(cfg: config.StudentConfig, store: MemoryStore):
    seen = Recorder()
    [status] = accounts.check_accounts(cfg, store, FakeTransport(), TODAY, seen)
    assert status.status == "no_token"
    [text] = seen.texts
    assert "«student»" in text
    assert STUDENT_ADDRESS not in text and SCHOOL_ADDRESS not in text and "s9" not in text


def test_a_working_link_notifies_nothing(cfg: config.StudentConfig, store: MemoryStore):
    store.set("s9/student", "refresco")
    seen = Recorder()
    accounts.check_accounts(cfg, store, FakeTransport([json_response(200, {"access_token": "a"})]), TODAY, seen)
    assert seen.texts == []


@pytest.mark.parametrize("status", accounts.STATUSES[1:])
def test_every_failure_reads_in_spanish(status: str):
    text = notify.link_failed("student", status)
    assert text.startswith("alfabeta no puede usar la cuenta «student»: ") and status not in text.split(": ", 1)[1]


def test_the_mac_notification_carries_the_text_as_an_argument_never_as_script():
    calls: list[list[str]] = []
    notify.MacNotifier(run=calls.append).notify('Texto "con comillas" inventado')
    [argv] = calls
    assert argv[0] == "osascript" and argv[-2:] == ['Texto "con comillas" inventado', notify.TITLE]
    assert all("inventado" not in a for a in argv[:-2])  # nothing the text says reaches the script


@pytest.mark.parametrize("error", [FileNotFoundError("osascript"), subprocess.CalledProcessError(1, "osascript")])
def test_a_mac_that_cannot_show_it_loses_only_this_channel(error: Exception, capsys: pytest.CaptureFixture[str]):
    def fails(_argv: list[str]) -> None:
        raise error

    notify.MacNotifier(run=fails).notify("Texto inventado")
    assert "no se pudo mostrar el aviso" in capsys.readouterr().err


def test_google_check_exits_2_and_notifies_the_mac(home: Path, store: MemoryStore, monkeypatch: pytest.MonkeyPatch):
    seen = Recorder()
    store.set("s9/student", "refresco")
    monkeypatch.setattr(__main__, "KeychainStore", lambda: store)
    monkeypatch.setattr(__main__, "MacNotifier", lambda: seen)
    monkeypatch.setattr(__main__, "UrllibTransport", lambda: FakeTransport([json_response(400, REVOKED)]))
    assert __main__.main(["--home", str(home), "google", "check", "--student", "s9"]) == 2
    assert len(seen.texts) == 1 and "«student»" in seen.texts[0]
