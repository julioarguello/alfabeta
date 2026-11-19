"""`docker/classroom/read.py` against a local fake (spec 006 T005; FR-006, FR-008, FR-009, FR-027, FR-029, FR-030).

The module is loaded from its file and its host constants are set in the module object to the
fake's address — never through an environment variable or an option of the program. Playwright's
own Chromium plays Google Chrome. No real account, keychain value or Google host is reached.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import importlib.util
import io
import json
import time
from pathlib import Path
from typing import Any, cast

import jsonschema
import playwright.sync_api as playwright  # dev dependency; CI installs its Chromium (T007), never skipped
import pytest

from tests.fake_classroom import ACCOUNT, PASSWORD, PDF, UNREADABLE, FakeGoogle

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
    module.ACCOUNT_WAIT_SECONDS = 0
    module.LIST_PAUSE_MS = 100
    module.ONLY = only
    module.FORM_HOSTS = frozenset({"forms.invalid"})
    module.DRIVE_DOWNLOAD = f"{fake.other_origin}/download"
    module.DOCS_ORIGIN = fake.other_origin
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


def _live(*origins: str) -> Any:
    """A seed that leaves a live session in the profile, its cookie on each origin named."""

    def seed(module: Any, fake: FakeGoogle) -> None:
        with playwright.sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(str(module.PROFILE), headless=True)
            for origin in origins:
                url = getattr(fake, origin)
                ctx.add_cookies([{"name": "fakesid", "value": "ok", "url": url, "expires": time.time() + 3600}])
            ctx.close()

    return seed


def _want(item: str, file_id: str, name: str, url: str | None = None) -> dict[str, Any]:
    return {
        "item": item,
        "attachment": file_id,
        "url": url or f"{{drive}}?id={file_id}&export=download&authuser=5",
        "expected_name": name,
    }


def _fetch(
    tmp_path: Path,
    wanted: list[dict[str, Any]],
    seed: Any = None,
    request: dict[str, Any] | None = None,
    **constants: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]], FakeGoogle]:
    with FakeGoogle("ok") as fake:
        module, events = _load(fake, tmp_path, frozenset({"none"}))
        for name, value in constants.items():
            setattr(module, name, value)
        (seed or _live("origin", "other_origin"))(module, fake)
        for w in wanted:
            w["url"] = w["url"].replace("{drive}", module.DRIVE_DOWNLOAD).replace("{docs}", module.DOCS_ORIGIN)
        base = {"run": "run0000000000001", "account": ACCOUNT, "password": None, "signin": False}
        end: dict[str, Any] = module.run(base | (request or {}) | {"fetch": wanted})
        return end, events, fake


def _inbox(tmp_path: Path, item: str, file_id: str, name: str) -> Path:
    return tmp_path / "out" / "inbox" / f"{item}__{file_id}" / name


def test_listed_attachments_are_fetched_into_the_inbox(tmp_path: Path) -> None:
    wanted = [
        _want("i1", "f-pdf", "Tema 3.pdf"),
        _want("i2", "f-hop", "Ejercicios.pdf"),  # a redirect within R4's host is followed
        _want("i3", "doc-1", "Apuntes.pdf", "{docs}/document/d/doc-1/export?format=pdf&authuser=5"),
    ]
    end, events, fake = _fetch(tmp_path, wanted)
    assert end["outcome"] == "ok" and end["attachments"] == {"brought": 3, "not_brought": 0, "refused": 0}, end
    assert _inbox(tmp_path, "i1", "f-pdf", "Tema 3.pdf").read_bytes() == PDF
    assert _inbox(tmp_path, "i2", "f-hop", "Ejercicios.pdf").read_bytes() == PDF
    assert _inbox(tmp_path, "i3", "doc-1", "Apuntes.pdf").read_bytes() == PDF
    assert fake.password_attempts == 0 and not [e for e in events if e["event"] == "typed"]
    _no_secret(events, end, tmp_path)


def test_an_unlisted_file_a_non_r4_route_or_a_bad_name_is_refused_before_its_request(tmp_path: Path) -> None:
    wanted = [
        _want("i1", "f-pdf", "a.pdf", "{drive}?id=f-other&export=download&authuser=5"),  # not its own id
        _want("i2", "f-pdf", "a.pdf", "http://third.invalid/download?id=f-pdf&export=download"),
        _want("i3", "f-pdf", "a.pdf", "https://docs.google.com/forms/d/f-pdf/viewform"),
        _want("i4", "quiz", "a.pdf", "{docs}/forms/d/quiz/export"),
        _want("i5", "f-pdf", "../fuera.pdf"),
        _want("i/6", "f-pdf", "a.pdf"),
    ]
    end, events, fake = _fetch(tmp_path, wanted)
    assert end["attachments"] == {"brought": 0, "not_brought": 0, "refused": 6}, end
    assert "/download" not in fake.served and not any("/forms/" in path for path in fake.served)
    assert not (tmp_path / "out" / "inbox").exists() and not (tmp_path / "fuera.pdf").exists()
    assert [e["why"] for e in events if e["event"] == "attachment"] == ["route"] * 4 + ["name"] * 2


def test_a_redirect_to_another_host_is_refused_and_logged_by_host_only(tmp_path: Path) -> None:
    end, events, _ = _fetch(tmp_path, [_want("i1", "f-away", "a.pdf")])
    assert end["attachments"]["refused"] == 1
    assert {"event": "attachment", "result": "refused", "why": "host", "host": "third.invalid"} in events


def test_a_page_or_a_missing_file_is_not_brought_and_not_retried(tmp_path: Path) -> None:
    end, events, fake = _fetch(tmp_path, [_want("i1", "f-html", "a.pdf"), _want("i2", "f-gone", "b.pdf")])
    assert end["outcome"] == "ok" and end["attachments"] == {"brought": 0, "not_brought": 2, "refused": 0}
    assert [e["why"] for e in events if e["event"] == "attachment"] == ["html", "status_404"]
    assert fake.served.count("/download") == 2


def test_an_expired_session_stops_the_pass_and_brings_nothing_more(tmp_path: Path) -> None:
    # Classroom still opens, but the download host has no session: its sign-in redirect ends the pass.
    wanted = [_want("i1", "f-pdf", "a.pdf"), _want("i2", "f-pdf", "b.pdf")]
    end, _, fake = _fetch(tmp_path, wanted, seed=_live("origin"))
    assert end["outcome"] == "stopped" and end["reason"] == "session_expired"
    assert end["attachments"] == {"brought": 0, "not_brought": 2, "refused": 0}
    assert fake.served.count("/download") == 1


def test_the_attachments_pass_never_signs_in(tmp_path: Path) -> None:
    def no_session(module: Any, fake: FakeGoogle) -> None:
        pass

    end, events, fake = _fetch(tmp_path, [_want("i1", "f-pdf", "a.pdf")], seed=no_session, request=SIGN_IN)
    assert end["reason"] == "session_expired" and fake.password_attempts == 0
    assert not [e for e in events if e["event"] == "typed"] and "/download" not in fake.served


class ModuleContainer:
    """`ReadContainer` that runs this very `read.py` in-process against the fake, both passes."""

    def __init__(self, module: Any) -> None:
        self.module = module
        self.requests: list[dict[str, Any]] = []

    def available(self) -> bool:
        return True

    def ensure_image(self) -> str:
        return "in-process"

    def memory(self, image: str) -> None:
        return None  # not read: the read goes on

    def run(self, image: str, request: dict[str, Any], profile: Path, out: Path, on_event: Any) -> dict[str, Any]:
        self.requests.append({k: v for k, v in request.items() if k != "password"})
        self.module.PROFILE, self.module.OUT, self.module.emit = profile, out, on_event
        return cast("dict[str, Any]", self.module.run(dict(request)))


def test_refresh_places_what_the_real_read_fetched(tmp_path: Path) -> None:
    from alfabeta import state
    from alfabeta.classroom import refresh
    from tests.test_classroom_refresh import FakeNotifier, FakeSteps, FakeStore

    with FakeGoogle("ok") as fake:
        module, _ = _load(fake, tmp_path, frozenset({"none"}))  # the class list alone: fast
        data = tmp_path / "home" / "s9" / "data"
        module.PROFILE = data / "classroom-profile"
        _live("origin", "other_origin")(module, fake)
        url = f"{module.DRIVE_DOWNLOAD}?id=f-pdf&export=download&authuser=5"
        wanted = {"item": "synth-71-i1", "attachment": "f-pdf", "url": url, "expected_name": "Tema 3.pdf"}
        steps = FakeSteps(downloads=[wanted | {"batch": 0, "why": "new"}])
        reader = ModuleContainer(module)
        cfg = refresh.RefreshConfig("s9", ACCOUNT, True, data, tmp_path / "downloads", 5)
        deps = refresh.Deps(reader, FakeStore(), FakeNotifier(), steps, dt.date(2026, 11, 18), False, "command")
        result = refresh.refresh(cfg, state.Lock(tmp_path / "home", data), deps, None)
    assert result["outcome"] == "ok", result
    assert result["capture"]["attachments"] == {"brought": 1, "not_brought": 0, "refused": 0}
    assert (data / "inbox" / "synth-71-i1__f-pdf" / "Tema 3.pdf").read_bytes() == PDF
    assert [r.get("fetch") is not None for r in reader.requests] == [False, True]
    assert sorted(p.name for p in (tmp_path / "downloads").iterdir())[0].startswith("alfabeta-capture-")


def test_a_body_over_the_limit_is_not_brought(tmp_path: Path) -> None:
    # Declared too large, and too large with nothing declared.
    wanted = [_want("i1", "f-pdf", "a.pdf"), _want("i2", "f-nolen", "b.pdf")]
    end, events, _ = _fetch(tmp_path, wanted, FETCH_MAX_BYTES=5)
    assert end["attachments"]["not_brought"] == 2
    assert [e["why"] for e in events if e["event"] == "attachment"] == ["too_large", "too_large"]
    assert not (tmp_path / "out" / "inbox").exists() or not list((tmp_path / "out" / "inbox").rglob("*.pdf"))


def test_a_compressed_body_is_brought_whole(tmp_path: Path) -> None:
    end, _, _ = _fetch(tmp_path, [_want("i1", "f-gzip", "a.pdf")])
    assert end["attachments"]["brought"] == 1, end
    folder = _inbox(tmp_path, "i1", "f-gzip", "a.pdf").parent
    assert (folder / "a.pdf").read_bytes() == PDF * 50 and [p.name for p in folder.iterdir()] == ["a.pdf"]
    assert not list(folder.parent.glob(".part-*"))


def test_a_redirect_that_changes_scheme_is_not_followed(tmp_path: Path) -> None:
    end, events, _ = _fetch(tmp_path, [_want("i1", "f-scheme", "a.pdf")], ACCOUNT_HOSTS=frozenset({"127.0.0.1"}))
    assert end["attachments"]["refused"] == 1
    assert {"event": "attachment", "result": "refused", "why": "host", "host": "localhost"} in events


def _production() -> Any:
    """`read.py` with its own constants, as the image runs it (no fake's hosts)."""
    spec = importlib.util.spec_from_file_location("read_production", READ)
    assert spec and spec.loader
    module: Any = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_measured_setsid_redirect_is_allowed_only_while_signing_in() -> None:
    module = _production()
    guard = module.Guard()
    setsid = "https://accounts.google.es/accounts/SetSID"
    guard.phase = "signin"
    assert guard.allows_document(setsid, True)
    guard.phase = "read"
    assert not guard.allows_document(setsid, True)


class _Frame:
    parent_frame = None


class _Request:
    def __init__(self, url: str) -> None:
        self.url = url
        self.redirected_from = object()
        self.resource_type = "document"
        self.frame = _Frame()


def test_a_redirect_to_an_unknown_host_names_the_host_only() -> None:
    module = _production()
    events: list[dict[str, Any]] = []
    module.emit = events.append
    guard = module.Guard()
    guard.watch(_Request("https://accounts.google.de/accounts/SetSID?continue=x&ssdc=1"))
    assert guard.breached
    assert events == [
        {"event": "redirect", "to": "other", "path": "", "main_frame": True, "host": "accounts.google.de"}
    ]


def test_each_step_says_where_the_read_is(tmp_path: Path) -> None:
    end, events, _ = _read("ok", tmp_path, SIGN_IN, only=frozenset({"synth-71"}))
    steps = [e["event"] for e in events if e["event"] in ("home", "signin_start", "signin", "account", "classes")]
    assert steps == ["home", "signin_start", "signin", "home", "account", "classes"]
    assert [e.get("state") for e in events if e["event"] == "home"] == ["expired", "alive"]
    assert {"event": "account", "result": "ok"} in events
    listed = next(e for e in events if e["event"] == "classes")
    assert listed["to_read"] == 1 and listed["listed"] >= 1
    assert [e for e in events if e["event"] == "class_start"] == [{"event": "class_start", "index": 1, "total": 1}]
    assert end["step"] == "classes"


def test_a_stop_names_its_step(tmp_path: Path) -> None:
    end, _, _ = _read("ok", tmp_path, {"password": None, "signin": False})
    assert end["reason"] == "session_expired" and end["step"] == "home"
    end, _, _ = _read("captcha", tmp_path / "c", SIGN_IN)
    assert end["reason"] == "challenge" and end["step"] == "signin"


def test_a_page_that_names_no_account_stops_at_the_account_check(tmp_path: Path) -> None:
    end, events, _ = _read("no_account", tmp_path, SIGN_IN)
    assert end["reason"] == "unexpected_ui" and end["step"] == "account"
    assert {"event": "account", "result": "none"} in events


def test_a_class_list_painted_late_is_read_again(tmp_path: Path) -> None:
    def slow(module: Any, fake: FakeGoogle) -> None:
        module.LIST_PAUSE_MS = 700  # three more tries: 0.7, 1.4, 2.1 s; the cards come at 1.5 s
        _live("origin")(module, fake)

    with FakeGoogle("slow_list") as fake:
        module, events = _load(fake, tmp_path, frozenset({"none"}))
        slow(module, fake)
        end: dict[str, Any] = module.run(
            {"run": "run0000000000001", "account": ACCOUNT, "password": None, "signin": False}
        )
    assert end["outcome"] == "ok", end
    assert next(e for e in events if e["event"] == "classes")["listed"] >= 1


class _ListingPage:
    """A page whose class list holds one class: enough for `capture` to reach its loop."""

    def evaluate(self, script: str, arg: Any = None) -> Any:
        if arg is None:
            return None  # the extractor's source
        capture = {"type": "classes", "classes": [{"id": "c1", "title": "t"}], "account_index": 0}
        return {"name": "alfabeta-capture-r-classes.json", "capture": capture}

    def wait_for_timeout(self, ms: int) -> None:
        pass


def test_a_breach_before_the_first_class_is_a_stop_not_ok(tmp_path: Path) -> None:
    module = _production()
    module.EXTRACTOR = ROOT / "skills" / "classroom-sync" / "scripts" / "extract.js"
    events: list[dict[str, Any]] = []
    module.emit = events.append
    guard = module.Guard()
    guard.breached = True
    result = module.capture(_ListingPage(), guard, "r", tmp_path, module.Crash())
    assert result == {"outcome": "stopped", "reason": "unexpected_ui", "classes": {"read": 0, "failed": 0}}


def test_an_exception_in_the_read_keeps_its_step(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with FakeGoogle("ok") as fake:
        module, _ = _load(fake, tmp_path, frozenset({"none"}))
        _live("origin")(module, fake)

        def boom(*_: Any) -> Any:
            raise RuntimeError("x")

        monkeypatch.setattr(module, "capture", boom)
        end: dict[str, Any] = module.run(
            {"run": "r0000000000000001", "account": ACCOUNT, "password": None, "signin": False}
        )
    assert end["outcome"] == "stopped" and end["reason"] == "unexpected_ui" and end["step"] == "classes"
    assert "blocked" in end and "seconds" in end


def _recording(module: Any, said: list[bool]) -> None:
    """Keep what `says_crashed` answered for each error it was shown."""
    says = module.says_crashed

    def recording(err: BaseException) -> bool:
        said.append(says(err))
        return said[-1]

    module.says_crashed = recording


def _dying_at(marker: str, said: list[bool]) -> Any:
    """A seed: a live session, and the page's renderer dies when a request for `marker` is routed.

    `chrome://crash` is Chromium's own crash page. What follows — the page's `crash` event and the
    error of the call that was pending — is the browser's and Playwright's, not this test's.
    """

    def seed(module: Any, fake: FakeGoogle) -> None:
        _live("origin")(module, fake)
        _recording(module, said)
        holder: dict[str, Any] = {}
        capture, route = module.capture, module.Guard.route

        def capturing(page: Any, *rest: Any) -> Any:
            holder["page"] = page
            return capture(page, *rest)

        def routing(self: Any, routed: Any, request: Any) -> None:
            if marker in request.url and "page" in holder:
                with contextlib.suppress(playwright.Error):
                    holder.pop("page").goto("chrome://crash")
                with contextlib.suppress(playwright.Error):
                    routed.abort()
                return
            route(self, routed, request)

        module.capture, module.Guard.route = capturing, routing

    return seed


def test_a_browser_that_dies_midway_stops_there_with_browser_crashed(tmp_path: Path) -> None:
    said: list[bool] = []
    only = frozenset({"synth-71", "synth-74", "synth-75"})
    live = {"password": None, "signin": False}
    end, events, _ = _read("ok", tmp_path, live, only=only, seed=_dying_at("synth-74", said))
    assert end["outcome"] == "partial" and end["reason"] == "browser_crashed", end
    assert end["classes"] == {"read": 1, "failed": 1} and end["step"] == "classes"
    stops = [e for e in events if e["event"] == "class" and e["type"] == "stop"]
    assert [e["reason"] for e in stops] == ["browser_crashed"]
    # The class after the dead one is not tried: a dead page reads nothing.
    assert [e["index"] for e in events if e["event"] == "class_start"] == [1, 2]
    # Playwright's own error for the pending call was read as the crash (`Page.evaluate: Target crashed`).
    assert said == [True]
    assert len(list((tmp_path / "out").glob("alfabeta-capture-*-synth-7*.json"))) == 1  # the class read is kept


def test_a_browser_dead_before_the_read_is_browser_crashed_not_what_it_looks_like(tmp_path: Path) -> None:
    said: list[bool] = []

    def seed(module: Any, fake: FakeGoogle) -> None:
        _live("origin")(module, fake)
        _recording(module, said)
        open_home = module.open_home

        def dead_home(page: Any) -> str:
            with contextlib.suppress(playwright.Error):
                page.goto("chrome://crash")
            return cast("str", open_home(page))

        module.open_home = dead_home

    end, events, _ = _read("ok", tmp_path, {"password": None, "signin": False}, seed=seed)
    # A load on a dead page fails as an aborted load: the step saw `unreachable`, and no error said "crashed".
    assert {"event": "home", "state": "unreachable"} in events and said == []
    # Only the page's `crash` event told; the end names it, in the step it happened.
    assert end["outcome"] == "stopped" and end["reason"] == "browser_crashed" and end["step"] == "home", end


class _TwoClasses(_ListingPage):
    """Two classes listed; reading a class raises the error given."""

    def __init__(self, error: Exception) -> None:
        self.error = error
        self.asked: list[str] = []

    def evaluate(self, script: str, arg: Any = None) -> Any:
        if arg is not None and "classId" in arg:
            self.asked.append(arg["classId"])
            raise self.error
        if arg is None:
            return None
        classes = [{"id": "c1", "title": "t"}, {"id": "c2", "title": "u"}]
        capture = {"type": "classes", "classes": classes, "account_index": 0}
        return {"name": "alfabeta-capture-r-classes.json", "capture": capture}


def _captured(tmp_path: Path, error: Exception) -> tuple[dict[str, Any], list[str], list[dict[str, Any]]]:
    module = _production()
    module.EXTRACTOR = ROOT / "skills" / "classroom-sync" / "scripts" / "extract.js"
    events: list[dict[str, Any]] = []
    module.emit = events.append
    page = _TwoClasses(error)
    return module.capture(page, module.Guard(), "r", tmp_path, module.Crash()), page.asked, events


def test_the_error_of_a_dead_page_alone_stops_the_classes(tmp_path: Path) -> None:
    # The text Playwright 1.64.1 raised for the pending call on 2026-11-19; the test above gets it
    # from a real browser, this one shows it is enough without the page's `crash` event.
    result, asked, events = _captured(tmp_path, Exception("Page.evaluate: Target crashed "))
    assert result == {"outcome": "stopped", "reason": "browser_crashed", "classes": {"read": 0, "failed": 1}}
    assert asked == ["c1"] and [e["reason"] for e in events if e["event"] == "class"] == ["browser_crashed"]


def test_any_other_error_in_a_class_stops_that_class_alone(tmp_path: Path) -> None:
    result, asked, events = _captured(tmp_path, RuntimeError("x"))
    assert result == {"outcome": "stopped", "reason": "unexpected_ui", "classes": {"read": 0, "failed": 2}}
    assert asked == ["c1", "c2"] and [e["reason"] for e in events if e["event"] == "class"] == ["unexpected_ui"] * 2


@pytest.mark.parametrize(
    ("text", "crashed"),
    [
        ("Page.evaluate: Target crashed ", True),  # a call pending or made on a dead page
        ("Page.wait_for_timeout: Page crashed", True),
        ("Page.goto: net::ERR_ABORTED; maybe frame was detached?", False),  # a load on a dead page
        ('Locator.fill: Timeout 10000ms exceeded.\nCall log:\n  - fill("crashed")', False),  # a call log is not read
        ("Page.evaluate: Error: «The site crashed» has no classwork tab", False),  # a script's own message
        ("", False),
    ],
)
def test_only_an_errors_first_line_says_crashed(text: str, crashed: bool) -> None:
    assert _production().says_crashed(Exception(text)) is crashed


def test_a_code_read_before_the_page_died_is_kept(tmp_path: Path) -> None:
    def seed(module: Any, fake: FakeGoogle) -> None:
        sign_in = module.sign_in

        def dying_after(ctx: Any, page: Any, *rest: Any) -> Any:
            code = sign_in(ctx, page, *rest)
            with contextlib.suppress(playwright.Error):
                page.goto("chrome://crash")
            with contextlib.suppress(playwright.Error):
                page.evaluate("1")  # the next call: the page's `crash` event arrives with its error
            return code

        module.sign_in = dying_after

    end, _, _ = _read("ok", tmp_path, {"password": "otra-inventada", "signin": True}, seed=seed)
    assert end["reason"] == "wrong_password" and end["outcome"] == "stopped", end


def test_a_page_that_dies_after_the_sign_in_is_browser_crashed_not_session_expired(tmp_path: Path) -> None:
    def seed(module: Any, fake: FakeGoogle) -> None:
        open_home = module.open_home
        loads: list[int] = []

        def home(page: Any) -> str:
            loads.append(1)
            if len(loads) == 2:  # the load after the sign-in
                with contextlib.suppress(playwright.Error):
                    page.goto("chrome://crash")
            return cast("str", open_home(page))

        module.open_home = home

    end, events, _ = _read("ok", tmp_path, SIGN_IN, seed=seed)
    assert {"event": "signin", "result": "signed_in"} in events
    # The dead load is `unreachable`, which this step calls `session_expired`: neither names the stop.
    assert end["outcome"] == "stopped" and end["reason"] == "browser_crashed" and end["step"] == "home", end
