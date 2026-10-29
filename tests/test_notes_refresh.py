"""The owner's refresh with fakes: `nlm`, the state, the Mac's notifications (spec 005 T045, FR-018, FR-019).

Every id, checksum and address is invented. No test runs `nlm`, opens a browser or writes outside
`tmp_path`.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path
from typing import Any

import pytest

from alfabeta.google.accounts import LinkError
from alfabeta.google.drive import DriveError, ScopedDrive
from alfabeta.google.transport import Response
from alfabeta.notes import cli
from alfabeta.notes.model import RefreshRecord, Session, SourceRead
from alfabeta.notes.refresh import (
    AGENDA_LINE,
    NOTICE,
    RECORD,
    LocalRefreshStore,
    RefreshDeps,
    agenda_notices,
    refresh_sources,
)
from alfabeta.notes.sources import SourcesError
from alfabeta.notes.state import DriveNotesStateStore
from tests.conftest import FakeTransport, json_response
from tests.notes_fakes import MADRID, FakeNotifier, FakeOwner, FakeState, FixedClock, living_state
from tests.test_google_drive_scope import file, folder, listing

NOW = dt.datetime(2026, 10, 28, 10, 0, tzinfo=MADRID)
MD5_A, MD5_B = "a" * 32, "b" * 32


def world(
    tmp_path: Path, state: dict[str, Any], owner: FakeOwner | None = None
) -> tuple[RefreshDeps, FakeOwner, FakeNotifier]:
    made_owner, notifier = owner or FakeOwner(), FakeNotifier()
    deps = RefreshDeps(FakeState(state), made_owner, LocalRefreshStore(tmp_path / "data"), notifier, FixedClock(NOW))
    return deps, made_owner, notifier


def record(tmp_path: Path) -> dict[str, Any]:
    return json.loads((tmp_path / "data" / RECORD).read_text())


# --- an idle pass (SC-004) ---------------------------------------------------------------------


def test_an_idle_pass_makes_no_nlm_call_writes_no_record_and_lists_no_folder(tmp_path: Path):
    state = living_state(("notes", "src-1", MD5_A, "ok"), ("classroom", "src-2", MD5_B, "ok"))
    store = LocalRefreshStore(tmp_path / "data")
    read_at = NOW - dt.timedelta(minutes=15)
    store.save(
        RefreshRecord(
            {"src-1": SourceRead(MD5_A, 2, read_at), "src-2": SourceRead(MD5_B, 2, read_at)}, Session.OK, read_at
        )
    )
    before = (store.path.read_bytes(), store.path.stat().st_mtime_ns)
    cache = tmp_path / "drive.json"
    cache.write_text(json.dumps({"root_id": "raiz", "root_path": "alfabeta"}, indent=1) + "\n")
    t = FakeTransport(
        [
            json_response(200, folder("raiz", "root", "alfabeta")),  # the cached root, by id
            listing(folder("conf", "raiz", ".alfabeta")),  # `.alfabeta` by name
            listing(file("estado", "conf", "state.json")),  # `state.json` by name
            json_response(200, {"headRevisionId": "rev-1"}),
            Response(200, json.dumps(state).encode()),
        ]
    )
    drive = ScopedDrive.open_root(t, "acceso", "alfabeta", cache)
    owner, notifier = FakeOwner(), FakeNotifier()
    out = refresh_sources(RefreshDeps(DriveNotesStateStore(drive), owner, store, notifier, FixedClock(NOW)))
    assert len(owner.calls) == 0, owner.calls  # no `nlm` call at all: not even the session check
    assert len(t.calls) == 5 and not t.responses  # the root, two look-ups by name, state.json's revision and bytes
    assert not [url for _, url, _, _ in t.calls if "in+parents" in url and "name+%3D" not in url]  # no listing
    assert (store.path.read_bytes(), store.path.stat().st_mtime_ns) == before
    assert out == {"ok": True, "read": 0, "unchanged": 2, "missing": 0, "renewed": False, "session": "ok"}
    assert notifier.texts == []


def test_an_idle_pass_before_any_session_check_reports_no_session(tmp_path: Path):
    deps, owner, _ = world(tmp_path, living_state(("notes", None, MD5_A, "ok")))  # waiting for setup
    assert refresh_sources(deps)["session"] is None
    assert owner.calls == [] and not (tmp_path / "data" / RECORD).exists()


# --- a changed living file: one read, the confirming read, then nothing ------------------------


def test_a_changed_living_file_is_read_then_confirmed_then_left(tmp_path: Path):
    deps, owner, _ = world(tmp_path, living_state(("notes", "src-1", MD5_A, "ok")))
    first = refresh_sources(deps)
    assert owner.calls == ["check", "read src-1"]  # a source with no entry counts as changed
    assert first == {"ok": True, "read": 1, "unchanged": 0, "missing": 0, "renewed": False, "session": "ok"}
    assert record(tmp_path)["sources"]["src-1"] == {"read_md5": MD5_A, "reads": 1, "read_at": NOW.isoformat()}

    owner.calls.clear()
    assert refresh_sources(deps)["read"] == 1
    assert owner.calls == ["check", "read src-1"]
    assert record(tmp_path)["sources"]["src-1"]["reads"] == 2

    owner.calls.clear()
    assert refresh_sources(deps)["read"] == 0 and owner.calls == []


def test_a_new_build_after_the_confirming_read_is_read_again_from_one(tmp_path: Path):
    deps, owner, _ = world(tmp_path, living_state(("notes", "src-1", MD5_A, "ok")))
    refresh_sources(deps)
    refresh_sources(deps)
    deps = RefreshDeps(
        FakeState(living_state(("notes", "src-1", MD5_B, "ok"))), owner, deps.record, deps.notifier, deps.clock
    )
    owner.calls.clear()
    assert refresh_sources(deps)["read"] == 1 and owner.calls == ["check", "read src-1"]
    assert record(tmp_path)["sources"]["src-1"]["read_md5"] == MD5_B
    assert record(tmp_path)["sources"]["src-1"]["reads"] == 1


def test_exam_preps_first_read_gets_its_confirming_read(tmp_path: Path):
    # `exam prep` writes `reads = 1` and no session (spec 002 contracts/cli.md, step 5).
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / RECORD).write_text(json.dumps({"sources": {"src-1": {"read_md5": MD5_A, "reads": 1}}}))
    deps, owner, _ = world(tmp_path, living_state(("notes", "src-1", MD5_A, "ok")))
    assert refresh_sources(deps)["read"] == 1 and owner.calls == ["check", "read src-1"]
    assert record(tmp_path)["sources"]["src-1"]["reads"] == 2


def test_a_missing_living_file_is_not_read(tmp_path: Path):
    state = living_state(("notes", "src-1", MD5_A, "missing"), ("classroom", "src-2", MD5_B, "ok"))
    deps, owner, _ = world(tmp_path, state)
    out = refresh_sources(deps)
    assert owner.calls == ["check", "read src-2"]
    assert (out["read"], out["missing"]) == (1, 1)
    assert "src-1" not in record(tmp_path)["sources"]


def test_a_living_file_never_built_or_never_set_up_is_not_read(tmp_path: Path):
    deps, owner, _ = world(tmp_path, living_state(("notes", "src-1", None, "ok"), ("classroom", None, MD5_B, "ok")))
    assert refresh_sources(deps) == {
        "ok": True,
        "read": 0,
        "unchanged": 0,
        "missing": 0,
        "renewed": False,
        "session": None,
    }
    assert owner.calls == []


def test_a_read_that_fails_is_not_recorded_and_the_pass_is_not_ok(tmp_path: Path):
    state = living_state(("notes", "src-1", MD5_A, "ok"), ("classroom", "src-2", MD5_B, "ok"))
    deps, owner, _ = world(tmp_path, state, FakeOwner(failing={"src-1": SourcesError(signed_out=False)}))
    out = refresh_sources(deps)
    assert owner.calls == ["check", "read src-1", "read src-2"]  # one failure does not stop the other
    assert (out["ok"], out["read"], out["session"]) == (False, 1, "ok")
    assert set(record(tmp_path)["sources"]) == {"src-2"}


# --- the owner's session (FR-019, research R14) ------------------------------------------------


def test_a_failing_session_that_http_only_fixes_needs_no_browser(tmp_path: Path):
    deps, owner, notifier = world(tmp_path, living_state(("notes", "src-1", MD5_A, "ok")), FakeOwner([False, True]))
    out = refresh_sources(deps)
    assert owner.calls == ["check", "renew http-only", "check", "read src-1"]
    assert (out["renewed"], out["session"], out["read"]) == (True, "ok", 1)
    assert notifier.texts == []


def test_unattended_a_failing_session_is_renewed_once_without_a_browser_then_told_once(tmp_path: Path):
    deps, owner, notifier = world(tmp_path, living_state(("notes", "src-1", MD5_A, "ok")), FakeOwner([False]))
    out = refresh_sources(deps)
    assert owner.calls == ["check", "renew http-only", "check"]  # never the default mode, which uses a browser
    assert out == {"ok": False, "read": 0, "unchanged": 0, "missing": 0, "renewed": True, "session": "signed_out"}
    assert notifier.texts == [NOTICE]
    saved = record(tmp_path)
    assert (saved["session"], saved["session_since"], saved["sources"]) == ("signed_out", NOW.isoformat(), {})


def test_a_renewal_that_does_not_run_is_not_checked_again(tmp_path: Path):
    deps, owner, _ = world(tmp_path, living_state(("notes", "src-1", MD5_A, "ok")), FakeOwner([False], [False]))
    assert refresh_sources(deps)["session"] == "signed_out"
    assert owner.calls == ["check", "renew http-only"]


def test_with_a_person_at_the_mac_the_browser_renewal_is_the_second_try(tmp_path: Path):
    deps, owner, notifier = world(tmp_path, living_state(("notes", "src-1", MD5_A, "ok")), FakeOwner([False]))
    assert refresh_sources(deps, browser=True)["session"] == "signed_out"
    assert owner.calls == ["check", "renew http-only", "check", "renew browser", "check"]
    assert notifier.texts == [NOTICE]


def test_a_second_failing_pass_gives_no_second_notice(tmp_path: Path):
    deps, _, notifier = world(tmp_path, living_state(("notes", "src-1", MD5_A, "ok")), FakeOwner([False]))
    refresh_sources(deps)
    since = record(tmp_path)["session_since"]
    assert refresh_sources(deps)["session"] == "signed_out"
    assert notifier.texts == [NOTICE]  # once, when it turned
    assert record(tmp_path)["session_since"] == since


def test_a_session_that_works_in_between_gives_a_new_notice_when_it_fails_again(tmp_path: Path):
    owner = FakeOwner([False, False, True, False])  # fails even after renewing, works next pass, fails on the third
    deps, _, notifier = world(tmp_path, living_state(("notes", "src-1", MD5_A, "ok")), owner)
    assert refresh_sources(deps)["session"] == "signed_out"
    assert refresh_sources(deps)["session"] == "ok"  # the check works: the source is read
    assert record(tmp_path)["session"] == "ok"
    assert refresh_sources(deps)["session"] == "signed_out"  # the confirming read finds it failing again
    assert notifier.texts == [NOTICE, NOTICE]


def test_a_read_that_finds_the_owner_signed_out_stops_like_a_failing_session(tmp_path: Path):
    state = living_state(("notes", "src-1", MD5_A, "ok"), ("classroom", "src-2", MD5_B, "ok"))
    owner = FakeOwner(failing={"src-2": SourcesError(signed_out=True)})
    deps, _, notifier = world(tmp_path, state, owner)
    out = refresh_sources(deps)
    assert (out["session"], out["read"]) == ("signed_out", 1)
    assert set(record(tmp_path)["sources"]) == {"src-1"}  # what was read before stays recorded
    assert notifier.texts == [NOTICE]


# --- the record (data-model.md, RefreshRecord) -------------------------------------------------


def test_the_record_is_readable_by_its_user_alone_and_written_only_when_it_changes(tmp_path: Path):
    deps, _, _ = world(tmp_path, living_state(("notes", "src-1", MD5_A, "ok")))
    refresh_sources(deps)
    path = tmp_path / "data" / RECORD
    assert path.stat().st_mode & 0o777 == 0o600
    store = LocalRefreshStore(tmp_path / "data")
    assert store.save(store.load()) is False  # the same record: nothing written


def test_an_absent_record_is_an_empty_one(tmp_path: Path):
    assert LocalRefreshStore(tmp_path / "data").load() == RefreshRecord()


# --- FR-019's agenda line -----------------------------------------------------------------------


@pytest.mark.parametrize(("session", "lines"), [("signed_out", (AGENDA_LINE,)), ("ok", ()), (None, ())])
def test_the_agenda_line_shows_while_the_session_is_signed_out(tmp_path: Path, session: str | None, lines: tuple[str]):
    data = tmp_path / "data"
    data.mkdir()
    body: dict[str, Any] = {"sources": dict[str, Any]()}
    if session:
        body |= {"session": session, "session_since": NOW.isoformat()}
    (data / RECORD).write_text(json.dumps(body))
    assert agenda_notices(data) == lines


def test_no_record_no_agenda_line(tmp_path: Path):
    assert agenda_notices(tmp_path / "data") == ()


def test_the_notice_and_the_agenda_line_speak_spanish_and_name_nothing():
    for text in (NOTICE, AGENDA_LINE):
        assert "sesión" in text and "nlm login" in text and "@" not in text


# --- the command: JSON on stdout, codes, and nothing that names a source ------------------------


def run_cli(deps: RefreshDeps | Exception, browser: bool = False) -> int:
    def factory(cfg: Any, store: Any) -> RefreshDeps:
        if isinstance(deps, Exception):
            raise deps
        return deps

    return cli.cmd_notebook_refresh(None, None, browser=browser, factory=factory)  # type: ignore[arg-type]


def printed(capsys: pytest.CaptureFixture[str]) -> tuple[dict[str, Any], str]:
    captured = capsys.readouterr()
    return json.loads(captured.out.strip().splitlines()[-1]), captured.err


def test_the_command_prints_the_counts_and_exits_0(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    deps, _, _ = world(tmp_path, living_state(("notes", "src-1", MD5_A, "ok")))
    assert run_cli(deps) == 0
    out, _ = printed(capsys)
    assert set(out) == {"ok", "read", "unchanged", "missing", "renewed", "session"}


def test_a_signed_out_owner_exits_5_and_names_no_source(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
):
    caplog.set_level(logging.DEBUG)
    owner = FakeOwner([False])
    deps, _, notifier = world(tmp_path, living_state(("notes", "src-secreto-1", MD5_A, "ok")), owner)
    assert run_cli(deps) == 5
    out, err = printed(capsys)
    assert (out["session"], out["renewed"]) == ("signed_out", True)
    every = json.dumps(out) + err + caplog.text + "".join(notifier.texts)
    assert "src-secreto-1" not in every and MD5_A not in every and "@" not in every
    assert "nlm login" in err


def test_nothing_the_command_prints_names_a_source_or_a_checksum(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
):
    caplog.set_level(logging.DEBUG)
    state = living_state(("notes", "src-secreto-1", MD5_A, "ok"), ("classroom", "src-secreto-2", MD5_B, "missing"))
    owner = FakeOwner(failing={"src-secreto-1": SourcesError(signed_out=False)})
    deps, _, _ = world(tmp_path, state, owner)
    assert run_cli(deps) == 3  # a read failed: partial
    out, err = printed(capsys)
    every = json.dumps(out) + err + caplog.text
    assert "src-secreto" not in every and MD5_A not in every and MD5_B not in every and "vivo-" not in every


def test_nlm_that_cannot_be_run_exits_1_no_nlm_never_5(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    deps, _, notifier = world(tmp_path, living_state(("notes", "src-1", MD5_A, "ok")), FakeOwner(missing=True))
    assert run_cli(deps) == 1
    out, _ = printed(capsys)
    assert out == {"ok": False, "reason": "no_nlm"}
    assert notifier.texts == [] and not (tmp_path / "data" / RECORD).exists()


@pytest.mark.parametrize(
    ("error", "code", "reason"),
    [
        (LinkError("revoked"), 2, "revoked"),
        (DriveError("Drive API returned 500", 500), 3, "drive_failed"),
    ],
)
def test_the_google_side_failing_exits_2_or_3(
    error: Exception, code: int, reason: str, capsys: pytest.CaptureFixture[str]
):
    assert run_cli(error) == code
    assert printed(capsys)[0] == {"ok": False, "reason": reason}


def test_a_session_check_that_says_nothing_exits_3_and_changes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    class Broken(FakeOwner):
        def session_ok(self) -> bool:
            raise SourcesError(signed_out=False)

    deps, _, notifier = world(tmp_path, living_state(("notes", "src-1", MD5_A, "ok")), Broken())
    assert run_cli(deps) == 3
    assert printed(capsys)[0] == {"ok": False, "reason": "nlm_failed"}
    assert notifier.texts == [] and not (tmp_path / "data" / RECORD).exists()


def test_the_browser_renewal_is_reached_only_through_the_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    for browser in (False, True):
        deps, owner, _ = world(
            tmp_path / str(browser), living_state(("notes", "src-1", MD5_A, "ok")), FakeOwner([False])
        )
        run_cli(deps, browser=browser)
        assert ("renew browser" in owner.calls) is browser
    capsys.readouterr()
