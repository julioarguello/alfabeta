"""`docker/classroom/read.py` against a local fake (spec 006 T005; FR-006, FR-008, FR-009, FR-027, FR-029, FR-030).

The module is loaded from its file and its host constants are set in the module object to the
fake's address — never through an environment variable or an option of the program. Playwright's
own Chromium plays Google Chrome. No real account, keychain value or Google host is reached.
"""

from __future__ import annotations

import importlib.util
import io
import json
import time
from pathlib import Path
from typing import Any

import jsonschema
import playwright.sync_api as playwright  # dev dependency; CI installs its Chromium (T007), never skipped
import pytest

from tests.fake_classroom import ACCOUNT, PASSWORD, UNREADABLE, FakeGoogle

ROOT = Path(__file__).resolve().parents[1]
READ = ROOT / "docker" / "classroom" / "read.py"
SCHEMA = json.loads((ROOT / "src" / "alfabeta" / "schemas" / "capture.schema.json").read_text())


def _load(fake: FakeGoogle, tmp_path: Path, only: frozenset[str]) -> tuple[Any, list[dict[str, Any]]]:
    spec = importlib.util.spec_from_file_location(f"read_{id(fake)}", READ)
    assert spec and spec.loader
    module: Any = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.CLASSROOM_HOME = f"{fake.origin}/u/5/h"
    module.SIGN_IN_URL = f"{fake.origin}/v3/signin/identifier"
    module.ACCOUNT_HOSTS = frozenset({"127.0.0.1", "localhost"})  # localhost: where an expired session lands
    module.CLASSROOM_HOSTS = frozenset({"127.0.0.1"})
    module.REDIRECT_HOSTS = frozenset()
    module.EXTRACTOR = ROOT / "skills" / "classroom-sync" / "scripts" / "extract.js"
    module.PROFILE = tmp_path / "profile"
    module.OUT = tmp_path / "out"
    module.CHANNEL = None
    module.IGNORE_DEFAULT_ARGS = []
    module.PACE = 0.0
    module.ONLY = only
    module.FORM_HOSTS = frozenset({"forms.invalid"})
    events: list[dict[str, Any]] = []
    module.emit = events.append
    return module, events


def _read(
    mode: str,
    tmp_path: Path,
    request: dict[str, Any],
    only: frozenset[str] = frozenset({"none"}),
    seed: Any = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], FakeGoogle]:
    with FakeGoogle(mode) as fake:
        module, events = _load(fake, tmp_path, only)
        if seed:
            seed(module, fake)
        end: dict[str, Any] = module.run({"run": "run0000000000001", "account": ACCOUNT, **request})
        return end, events, fake


SIGN_IN = {"password": PASSWORD, "signin": True}


def _no_secret(events: list[dict[str, Any]], end: dict[str, Any], tmp_path: Path) -> None:
    text = json.dumps(events, ensure_ascii=False) + json.dumps(end, ensure_ascii=False)
    out = tmp_path / "out"
    captures: list[Path] = sorted(out.glob("*.json")) if out.exists() else []
    for path in captures:
        text += path.read_text()
    assert PASSWORD not in text and ACCOUNT not in text


def test_signs_in_reads_and_writes_valid_captures(tmp_path: Path) -> None:
    end, events, fake = _read("ok", tmp_path, SIGN_IN, only=frozenset({"synth-71"}))
    assert end["outcome"] == "ok" and end["classes"] == {"read": 1, "failed": 0}, end
    assert fake.password_attempts == 1
    captures = sorted((tmp_path / "out").glob("alfabeta-capture-run0000000000001-*.json"))
    assert len(captures) == 2
    for path in captures:
        data = json.loads(path.read_text())
        jsonschema.validate(data, SCHEMA)
        if data["type"] == "class":
            assert data["complete"] is True and data["items"]
    # The guard, each count on its own: the planted press, form submit, form host, and two frames
    # (a page outside FR-007's pages, a third-party one); the outside page never reaches the server.
    blocked = end["blocked"]
    assert blocked.get("presses", 0) >= 1 and blocked.get("form_submits", 0) >= 1 and blocked.get("form_hosts", 0) >= 1
    assert blocked.get("frames", 0) >= 2
    assert "/u/5/outside" not in fake.served
    # The sign-in pages are logged by host and path only.
    pages = [e for e in events if e["event"] == "signin_page"]
    assert pages and all("?" not in e["path"] for e in pages)
    _no_secret(events, end, tmp_path)


def test_a_live_profile_reads_without_signing_in(tmp_path: Path) -> None:
    def seed(module: Any, fake: FakeGoogle) -> None:
        with playwright.sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(str(module.PROFILE), headless=True)
            ctx.add_cookies([{"name": "fakesid", "value": "ok", "url": fake.origin, "expires": time.time() + 3600}])
            ctx.close()

    end, events, fake = _read("ok", tmp_path, {"password": None, "signin": False}, seed=seed)
    assert end["outcome"] == "ok" and end["classes"] == {"read": 0, "failed": 0} and fake.password_attempts == 0
    assert not [e for e in events if e["event"] == "typed"]


def test_no_session_and_sign_in_forbidden_is_session_expired_with_nothing_typed(tmp_path: Path) -> None:
    end, events, fake = _read("ok", tmp_path, {"password": None, "signin": False})
    assert end["reason"] == "session_expired" and end["outcome"] == "stopped"
    assert fake.password_attempts == 0 and not [e for e in events if e["event"] == "typed"]


def test_no_password_when_a_sign_in_is_needed(tmp_path: Path) -> None:
    end, _, fake = _read("ok", tmp_path, {"password": None, "signin": True})
    assert end["reason"] == "no_password" and fake.password_attempts == 0


def test_cookies_are_cleared_so_no_account_chooser_shows(tmp_path: Path) -> None:
    def seed(module: Any, fake: FakeGoogle) -> None:
        with playwright.sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(str(module.PROFILE), headless=True)
            ctx.add_cookies([{"name": "fakestale", "value": "1", "url": fake.origin, "expires": time.time() + 3600}])
            ctx.close()

    end, events, _ = _read("ok", tmp_path, SIGN_IN, seed=seed)
    assert end["outcome"] == "ok", end
    assert not [e for e in events if e["event"] == "signin_page" and "chooser" in e["path"]]


@pytest.mark.parametrize(
    ("mode", "code", "typed"),
    [
        ("captcha", "challenge", ["account"]),
        ("rejected", "rejected", ["account"]),
        ("second_factor", "second_factor", ["account", "password"]),
        ("other_sign_in", "other_sign_in", ["account"]),
    ],
)
def test_a_check_stops_the_sign_in_and_nothing_is_typed_past_it(
    tmp_path: Path, mode: str, code: str, typed: list[str]
) -> None:
    end, events, _ = _read(mode, tmp_path, SIGN_IN)
    assert end["reason"] == code and end["outcome"] == "stopped", end
    if mode == "other_sign_in":
        assert end["blocked"].get("pages", 0) >= 1  # the sign-in's guard refused the other site's page
    assert [e["field"] for e in events if e["event"] == "typed"] == typed
    _no_secret(events, end, tmp_path)


def test_a_wrong_password_is_tried_once(tmp_path: Path) -> None:
    end, events, fake = _read("ok", tmp_path, {"password": "otra-inventada", "signin": True})
    assert end["reason"] == "wrong_password" and fake.password_attempts == 1
    assert "otra-inventada" not in json.dumps(events)


def test_another_account_is_session_expired_with_nothing_read(tmp_path: Path) -> None:
    end, events, _ = _read("other_account", tmp_path, SIGN_IN)
    assert end["reason"] == "session_expired" and end["classes"] == {"read": 0, "failed": 0}
    assert {"event": "account", "result": "other_account"} in events
    assert not list((tmp_path / "out").glob("*.json")) if (tmp_path / "out").exists() else True


def test_an_unreadable_class_stops_alone(tmp_path: Path) -> None:
    end, events, _ = _read("ok", tmp_path, SIGN_IN, only=frozenset({UNREADABLE, "synth-71"}))
    assert end["outcome"] == "partial" and end["reason"] == "unexpected_ui", end
    assert end["classes"] == {"read": 1, "failed": 1}
    stops = [e for e in events if e["event"] == "class" and e["type"] == "stop"]
    assert [e["reason"] for e in stops] == ["unexpected_ui"]


def test_a_session_ending_midway_keeps_the_classes_read(tmp_path: Path) -> None:
    end, _, _ = _read("expire_mid", tmp_path, SIGN_IN, only=frozenset({"synth-71", "synth-74", "synth-75"}))
    assert end["outcome"] == "partial" and end["reason"] == "session_expired", end
    assert end["classes"]["read"] == 1


def test_the_browser_runs_in_madrid_and_spanish(tmp_path: Path) -> None:
    _, events, _ = _read("ok", tmp_path, {"password": None, "signin": False})
    browser = next(e for e in events if e["event"] == "browser")
    assert browser["timezone"] == "Europe/Madrid" and browser["locale"] == "es-ES"
    # 07:00Z in January and 06:00Z in July are both 08:00 in Madrid (winter and summer time).
    assert browser["winter"] == "08:00" and browser["summer"] == "08:00"


def test_a_fill_that_fails_leaks_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    end, events, _ = _read("readonly", tmp_path, SIGN_IN)
    assert end["reason"] == "challenge"
    out = capsys.readouterr()
    assert PASSWORD not in out.out + out.err + json.dumps(events, ensure_ascii=False)


def test_a_redirect_outside_breaks_the_read(tmp_path: Path) -> None:
    end, _, _ = _read("redirect", tmp_path, SIGN_IN, only=frozenset({"synth-71"}))
    assert end["blocked"].get("redirects", 0) >= 1
    assert end["outcome"] == "stopped" and end["reason"] == "unexpected_ui"


def _main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, line: str) -> tuple[int, list[dict[str, Any]]]:
    with FakeGoogle("ok") as fake:
        module, events = _load(fake, tmp_path, frozenset({"none"}))
        monkeypatch.setattr("sys.stdin", io.StringIO(line))
        return module.main(), events


def test_main_reads_one_line_and_ends_with_a_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request = json.dumps({"run": "run0000000000001", "account": ACCOUNT, "password": None, "signin": False})
    code, events = _main(tmp_path, monkeypatch, request + "\n")
    assert code == 1 and events[-1]["event"] == "end" and events[-1]["reason"] == "session_expired"


@pytest.mark.parametrize("line", ["not json\n", '{"account": "alumno@example.test"}\n', '{"run": "r"}\n'])
def test_main_refuses_a_bad_request_without_a_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], line: str
) -> None:
    code, events = _main(tmp_path, monkeypatch, line)
    stopped = {"event": "end", "outcome": "stopped", "reason": "unexpected_ui", "classes": {"read": 0, "failed": 0}}
    assert code == 1 and events[-1] == stopped
    assert "Traceback" not in capsys.readouterr().err


def test_a_redirect_during_a_class_drops_it_and_stops_the_read(tmp_path: Path) -> None:
    end, events, _ = _read("redirect_in_class", tmp_path, SIGN_IN, only=frozenset({"synth-71", "synth-75"}))
    assert end["outcome"] == "stopped" and end["reason"] == "unexpected_ui", end
    assert end["classes"]["read"] == 0 and end["blocked"].get("redirects", 0) >= 1
    assert not list((tmp_path / "out").glob("*-synth-71-*.json"))  # the breaching class is not kept
    redirects = [e for e in events if e["event"] == "redirect"]
    assert redirects and all("?" not in e["path"] for e in redirects)
