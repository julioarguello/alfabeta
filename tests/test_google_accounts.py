import datetime as dt
import json
from collections.abc import Callable
from pathlib import Path

import pytest

from alfabeta import config
from alfabeta.google import accounts, oauth
from tests.conftest import GRANTED, SCHOOL_ADDRESS, STUDENT_ADDRESS, FakeTransport, MemoryStore, json_response

TODAY = dt.date(2026, 10, 27)
EXPIRED = {"error": "invalid_grant", "error_description": "Token has been expired or revoked."}


def _no_browser(_url: str) -> None:
    return None


def _grant(email: str | None, scopes: str = GRANTED) -> oauth.Grant:
    return oauth.Grant("refresco", "acceso", frozenset(scopes.split()), email)


@pytest.fixture
def cfg(home: Path) -> config.StudentConfig:
    return config.load(home, "s9", ("classroom", "calendar", "google"))


def _link(
    cfg: config.StudentConfig, store: MemoryStore, monkeypatch: pytest.MonkeyPatch, grant: oauth.Grant
) -> tuple[FakeTransport, Callable[[], tuple[str, ...]]]:
    def fake_receive(*_args: object, **_kwargs: object) -> tuple[str, str, str]:
        return "codigo", "verificador", "http://127.0.0.1:1"

    def fake_exchange(*_args: object, **_kwargs: object) -> oauth.Grant:
        return grant

    monkeypatch.setattr(oauth, "receive_code", fake_receive)
    monkeypatch.setattr(oauth, "exchange_code", fake_exchange)
    t = FakeTransport([json_response(200, {}), json_response(200, {})])

    def run() -> tuple[str, ...]:
        return accounts.link_account(cfg, "student", store, t, _no_browser, TODAY)

    return t, run


def test_link_stores_token_and_record(cfg: config.StudentConfig, store: MemoryStore, monkeypatch: pytest.MonkeyPatch):
    _, run = _link(cfg, store, monkeypatch, _grant(STUDENT_ADDRESS))
    run()
    assert store.get("s9/student") == "refresco"
    record = json.loads((cfg.data_dir / "google" / "accounts.json").read_text())
    assert record == {"student": {"linked_on": "2026-10-27"}}


@pytest.mark.parametrize(
    ("email", "scopes", "reason"),
    [
        ("otra.persona@example.com", GRANTED, "wrong_account"),
        (SCHOOL_ADDRESS, GRANTED, "school_account"),
        (None, GRANTED, "wrong_account"),
        (STUDENT_ADDRESS, "openid https://www.googleapis.com/auth/userinfo.email", "missing_scope"),
    ],
)
def test_link_refuses_and_revokes(
    cfg: config.StudentConfig,
    store: MemoryStore,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    email: str | None,
    scopes: str,
    reason: str,
):
    t, run = _link(cfg, store, monkeypatch, _grant(email, scopes))
    with pytest.raises(accounts.LinkError) as err:
        run()
    assert err.value.reason == reason
    assert store.get("s9/student") is None
    assert t.calls and t.calls[0][1] == oauth.REVOKE_URL
    assert STUDENT_ADDRESS not in str(err.value)
    assert STUDENT_ADDRESS not in capsys.readouterr().out


def test_relink_replaces_the_token(cfg: config.StudentConfig, store: MemoryStore, monkeypatch: pytest.MonkeyPatch):
    store.set("s9/student", "viejo")
    _, run = _link(cfg, store, monkeypatch, _grant(STUDENT_ADDRESS))
    run()
    assert store.get("s9/student") == "refresco"


def test_check_ok_and_no_token(cfg: config.StudentConfig, store: MemoryStore):
    assert accounts.check_accounts(cfg, store, FakeTransport(), TODAY) == [
        accounts.AccountStatus("student", "no_token")
    ]
    store.set("s9/student", "refresco")
    t = FakeTransport([json_response(200, {"access_token": "a"})])
    assert accounts.check_accounts(cfg, store, t, TODAY) == [accounts.AccountStatus("student", "ok")]


def test_check_flags_testing_when_expired_soon_after_linking(
    cfg: config.StudentConfig, store: MemoryStore, monkeypatch: pytest.MonkeyPatch
):
    _, run = _link(cfg, store, monkeypatch, _grant(STUDENT_ADDRESS))
    run()
    [soon] = accounts.check_accounts(
        cfg, store, FakeTransport([json_response(400, EXPIRED)]), TODAY + dt.timedelta(days=7)
    )
    assert soon == accounts.AccountStatus("student", "expired", testing_suspected=True)
    [later] = accounts.check_accounts(
        cfg, store, FakeTransport([json_response(400, EXPIRED)]), TODAY + dt.timedelta(days=30)
    )
    assert later.testing_suspected is False


def test_set_client_reads_the_desktop_json(tmp_path: Path, store: MemoryStore):
    f = tmp_path / "client.json"
    f.write_text(json.dumps({"installed": {"client_id": "x", "client_secret": "y"}}))
    accounts.set_client(store, "s9", f)
    assert json.loads(store.get("s9/client") or "") == {"client_id": "x", "client_secret": "y"}
    f.write_text(json.dumps({"web": {}}))
    with pytest.raises(accounts.LinkError):
        accounts.set_client(store, "s9", f)


def test_unlink_revokes_and_forgets(cfg: config.StudentConfig, store: MemoryStore):
    store.set("s9/student", "refresco")
    t = FakeTransport([json_response(200, {})])
    accounts.unlink_account(cfg, "student", store, t)
    assert store.get("s9/student") is None
    assert t.calls[0][1] == oauth.REVOKE_URL


def test_check_without_client_says_so(cfg: config.StudentConfig):
    [status] = accounts.check_accounts(cfg, MemoryStore(), FakeTransport(), TODAY)
    assert status == accounts.AccountStatus("student", "no_client")
