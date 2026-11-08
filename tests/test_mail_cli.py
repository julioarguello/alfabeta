"""Spec 010: the `mail` commands, in-process, on the sandbox's invented student. No request leaves the test."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from alfabeta import __main__, sandbox
from alfabeta.google import gmail
from alfabeta.google.transport import Response
from tests.conftest import MemoryStore
from tests.test_gmail import FakeGmail

ADDRESS = "buzon.inventado@example.com"
MODIFY = "https://www.googleapis.com/auth/gmail.modify"
SETTINGS = "https://www.googleapis.com/auth/gmail.settings.basic"


def _mail_account(alias: str, scopes: list[str]) -> str:
    return f'\n[google.accounts.{alias}]\nrole = "mail"\naddress = "{ADDRESS}"\nscopes = {json.dumps(scopes)}\n'


@pytest.fixture
def home(tmp_path: Path) -> Path:
    sandbox.prepare(tmp_path, "s9")
    return tmp_path


def _add_account(home: Path, text: str) -> None:
    config = home / "s9" / "config.toml"
    config.write_text(config.read_text() + text)


class Wire:
    """Google's token endpoint, then the invented mailbox."""

    def __init__(self, box: FakeGmail, token_status: int = 200) -> None:
        self.box = box
        self.token_status = token_status
        self.urls: list[str] = []

    def request(
        self, method: str, url: str, *, headers: dict[str, str] | None = None, body: bytes | None = None
    ) -> Response:
        self.urls.append(url)
        if url.startswith("https://oauth2.googleapis.com/token"):
            if self.token_status != 200:
                return Response(400, json.dumps({"error": "invalid_grant", "error_description": "revoked"}).encode())
            return Response(200, json.dumps({"access_token": "acceso"}).encode())
        return self.box.request(method, url, headers=headers, body=body)


@pytest.fixture
def store() -> MemoryStore:
    s = MemoryStore()
    s.set("s9/client", json.dumps({"client_id": "id-inventado", "client_secret": "secreto-inventado"}))
    s.set("s9/mailbox", "refresco-inventado")
    return s


def _patch(monkeypatch: pytest.MonkeyPatch, store: MemoryStore, wire: Any = None) -> None:
    monkeypatch.setattr(__main__, "KeychainStore", lambda: store)
    if wire is not None:
        monkeypatch.setattr(__main__, "UrllibTransport", lambda: wire)
    else:
        monkeypatch.setattr(__main__, "UrllibTransport", lambda: pytest.fail("no network expected"))


def _main(home: Path, argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, dict[str, Any], str]:
    code = __main__.main(["--home", str(home), *argv, "--student", "s9"])
    out, err = capsys.readouterr()
    return code, json.loads(out.strip().splitlines()[-1]), err


def test_plan_needs_no_link_and_no_network(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _patch(monkeypatch, MemoryStore())
    code, out, err = _main(home, ["mail", "plan"], capsys)
    assert code == 0
    assert out["labels"] == ["Alfabeta", "Alfabeta/3º ESO", "Alfabeta/3º ESO/FyQ", "Alfabeta/3º ESO/Ingles"]
    assert [f["subject"] for f in out["filters"]] == ["FyQ", "Ingles"]
    assert out["filters"][0]["query"].endswith(' subject:"3º ESO. FyQ."')
    assert "alfabeta: filter FyQ -> Alfabeta/3º ESO/FyQ" in err


def test_build_writes_the_file_with_no_link(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _patch(monkeypatch, MemoryStore())
    out_file = home / "filtros.xml"
    code, out, err = _main(home, ["mail", "build", "--out", str(out_file)], capsys)
    assert (code, out["filters"]) == (0, 2)
    assert out_file.read_text().count("<apps:property") == 6
    assert "Alfabeta/3º ESO/Ingles" in err


def test_build_to_an_unwritable_place_is_invalid_out(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    _patch(monkeypatch, MemoryStore())
    code, out, _ = _main(home, ["mail", "build", "--out", str(home / "no" / "f.xml")], capsys)
    assert (code, out["reason"]) == (1, "invalid_out")


@pytest.mark.parametrize("accounts", ["", _mail_account("a", [SETTINGS]) + _mail_account("b", [SETTINGS])])
def test_apply_needs_exactly_one_mail_account(
    home: Path, monkeypatch: pytest.MonkeyPatch, store: MemoryStore, capsys: pytest.CaptureFixture[str], accounts: str
):
    _add_account(home, accounts)
    _patch(monkeypatch, store)
    code, out, _ = _main(home, ["mail", "apply"], capsys)
    assert (code, out["reason"]) == (1, "invalid_config")


def test_apply_creates_everything_and_moves_existing_notices(
    home: Path, monkeypatch: pytest.MonkeyPatch, store: MemoryStore, capsys: pytest.CaptureFixture[str]
):
    _add_account(home, _mail_account("mailbox", [SETTINGS, MODIFY, "openid", "email"]))
    box = FakeGmail()
    _patch(monkeypatch, store, Wire(box))
    _, out, _ = _main(home, ["mail", "plan"], capsys)
    box.messages = {"m0": (out["filters"][1]["query"], {"INBOX"})}
    code, out, err = _main(home, ["mail", "apply"], capsys)
    assert code == 0
    assert [r["status"] for r in out["labels"]] == ["created"] * 4
    assert [r["status"] for r in out["filters"]] == ["created"] * 2
    assert out["existing_mail"][1] == {"subject": "Ingles", "matched": 1, "in_inbox": 1}
    assert "Ingles: 1 notices labelled, 1 were in the inbox" in err
    assert ADDRESS not in err + json.dumps(out)
    code, out, _ = _main(home, ["mail", "apply"], capsys)
    assert [r["status"] for r in out["labels"] + out["filters"]] == ["existing"] * 6


@pytest.mark.parametrize("scopes", [[SETTINGS, "openid", "email"], [MODIFY, "openid", "email"]])
def test_an_account_without_both_gmail_scopes_is_missing_scope(
    home: Path,
    monkeypatch: pytest.MonkeyPatch,
    store: MemoryStore,
    capsys: pytest.CaptureFixture[str],
    scopes: list[str],
):
    _add_account(home, _mail_account("mailbox", scopes))
    box = FakeGmail()
    wire = Wire(box)
    _patch(monkeypatch, store, wire)
    code, out, err = _main(home, ["mail", "apply"], capsys)
    assert (code, out["reason"]) == (2, "missing_scope")
    assert "--account mailbox" in err
    assert wire.urls == []


def test_an_error_after_a_write_says_to_run_it_again(
    home: Path, monkeypatch: pytest.MonkeyPatch, store: MemoryStore, capsys: pytest.CaptureFixture[str]
):
    _add_account(home, _mail_account("mailbox", [SETTINGS, MODIFY]))

    class FailsOnFilters(FakeGmail):
        def request(self, method: str, url: str, **kw: Any) -> Response:
            if "/settings/filters" in url:
                return Response(500, b"{}")
            return super().request(method, url, **kw)

    box = FailsOnFilters()
    _patch(monkeypatch, store, Wire(box))
    code, out, err = _main(home, ["mail", "apply"], capsys)
    assert (code, out["reason"]) == (2, "network")
    assert "run it again" in err
    assert "Alfabeta" in box.labels.values()


def test_a_revoked_link_writes_nothing_and_names_the_alias(
    home: Path, monkeypatch: pytest.MonkeyPatch, store: MemoryStore, capsys: pytest.CaptureFixture[str]
):
    _add_account(home, _mail_account("mailbox", [SETTINGS, MODIFY]))
    box = FakeGmail()
    _patch(monkeypatch, store, Wire(box, token_status=400))
    code, out, err = _main(home, ["mail", "apply"], capsys)
    assert (code, out["reason"]) == (2, "revoked")
    assert "google account link --student s9 --account mailbox" in err
    assert box.calls == []


def test_a_missing_token_is_no_token(home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    _add_account(home, _mail_account("mailbox", [SETTINGS, MODIFY]))
    bare = MemoryStore()
    bare.set("s9/client", json.dumps({"client_id": "i", "client_secret": "s"}))
    _patch(monkeypatch, bare, Wire(FakeGmail()))
    code, out, _ = _main(home, ["mail", "apply"], capsys)
    assert (code, out["reason"]) == (2, "no_token")


def test_a_server_error_creating_a_label_is_network(
    home: Path, monkeypatch: pytest.MonkeyPatch, store: MemoryStore, capsys: pytest.CaptureFixture[str]
):
    _add_account(home, _mail_account("mailbox", [SETTINGS, MODIFY]))

    class FailsOnCreate(FakeGmail):
        def request(self, method: str, url: str, **kw: Any) -> Response:
            if method == "POST" and url.endswith("/labels"):
                return Response(500, b"{}")
            return super().request(method, url, **kw)

    box = FailsOnCreate()
    _patch(monkeypatch, store, Wire(box))
    code, out, err = _main(home, ["mail", "apply"], capsys)
    assert (code, out["reason"]) == (2, "network")
    assert "run it again" in err
    assert box.filters == []


def test_a_401_is_revoked(
    home: Path, monkeypatch: pytest.MonkeyPatch, store: MemoryStore, capsys: pytest.CaptureFixture[str]
):
    _add_account(home, _mail_account("mailbox", [SETTINGS, MODIFY]))

    class Unauthorised(FakeGmail):
        def request(self, method: str, url: str, **kw: Any) -> Response:
            return Response(401, b"{}")

    _patch(monkeypatch, store, Wire(Unauthorised()))
    code, out, _ = _main(home, ["mail", "apply"], capsys)
    assert (code, out["reason"]) == (2, "revoked")


def test_a_403_is_missing_scope(
    home: Path, monkeypatch: pytest.MonkeyPatch, store: MemoryStore, capsys: pytest.CaptureFixture[str]
):
    _add_account(home, _mail_account("mailbox", [SETTINGS, MODIFY]))

    class Forbidden(FakeGmail):
        def request(self, method: str, url: str, **kw: Any) -> Response:
            return Response(403, b"{}")

    _patch(monkeypatch, store, Wire(Forbidden()))
    code, out, err = _main(home, ["mail", "apply"], capsys)
    assert (code, out["reason"]) == (2, "missing_scope")
    assert "--account mailbox" in err
    assert gmail.MODIFY_SCOPE == MODIFY
