"""`classroom refresh`, the container read (spec 006 T008; FR-019, FR-020, FR-022, FR-024a, FR-027, FR-028, FR-032)."""

from __future__ import annotations

import dataclasses
import datetime as dt
import json
import re
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from alfabeta import state
from alfabeta.classroom import cli, refresh
from alfabeta.classroom.container import ContainerError, Memory, memory_argv
from alfabeta.classroom.password import MARK
from alfabeta.google.keychain import KeychainError
from alfabeta.model import RunMode

if TYPE_CHECKING:
    from collections.abc import Callable

ROOT = Path(__file__).resolve().parents[1]
STUDENT = "s9"
ACCOUNT = "alumno@example.test"
PASSWORD = "contraseña-inventada-123"
TODAY = dt.date(2026, 11, 18)  # a Wednesday
NOW = dt.datetime(2026, 11, 18, 8, 10)  # ten minutes after the schedule's time
TIMES = dict.fromkeys(("monday", "tuesday", "wednesday", "thursday", "friday"), "08:00") | {
    "saturday": "",
    "sunday": "",
}


class FakeStore:
    def __init__(self, password: str | None = PASSWORD, locked: bool = False) -> None:
        self.secrets: dict[str, str] = {STUDENT: password} if password else {}
        self.locked = locked
        self.asked = 0

    def get(self, account: str) -> str | None:
        self.asked += 1
        if self.locked:
            raise KeychainError("locked")
        return self.secrets.get(account)

    def set(self, account: str, secret: str) -> None:
        self.secrets[account] = secret

    def delete(self, account: str) -> None:
        self.secrets.pop(account, None)


class FakeNotifier:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def notify(self, text: str) -> None:
        self.texts.append(text)


PLENTY = Memory(total_mb=7835, available_mb=5725)  # the Mac's Docker on 2026-11-19, 8 containers up
# What `free -m` read in an idle container of the image on 2026-11-19, before the loads that died (#268).
SHORT = Memory(total_mb=7835, available_mb=1213)


class FakeContainer:
    """Answers with a scripted end event, writing the captures a read would leave."""

    def __init__(
        self,
        end: dict[str, Any],
        up: bool = True,
        builds: bool = True,
        dies: bool = False,
        takes: float = 0.0,
        events: list[dict[str, Any]] | None = None,
        brings: frozenset[str] = frozenset(),
        fetch_dies: bool = False,
        fetch_events: list[dict[str, Any]] | None = None,
        plant: Callable[[Path], None] | None = None,
        memory: Memory | None = PLENTY,
        fetch_reason: str | None = None,
        first_ends: list[dict[str, Any]] | None = None,
    ) -> None:
        self.first_ends = list(first_ends or [])  # ends the first read gives before `end`, in order
        self.memory_read = memory
        self.fetch_reason = fetch_reason
        self.probed: list[str] = []
        self.fetch_dies = fetch_dies
        self.fetch_events = fetch_events or []
        self.plant = plant
        self.end = end
        self.events = events or []
        self.brings = brings
        self.up = up
        self.builds = builds
        self.dies = dies
        self.takes = takes
        self.requests: list[dict[str, Any]] = []
        self.out: Path | None = None

    def available(self) -> bool:
        return self.up

    def ensure_image(self) -> str:
        if not self.builds:
            raise ContainerError("no build")
        return "alfabeta-classroom-read:test"

    def memory(self, image: str) -> Memory | None:
        self.probed.append(image)
        return self.memory_read

    def run(
        self, image: str, request: dict[str, Any], profile: Path, out: Path, on_event: Callable[[dict[str, Any]], None]
    ) -> dict[str, Any]:
        self.requests.append(dict(request))
        out.mkdir(parents=True, exist_ok=True)
        if "fetch" in request:
            # The attachments pass: write what it "brings" where read.py would, by the given name.
            if self.fetch_dies:
                raise ContainerError("died")
            for event in self.fetch_events:
                on_event(event)
            if self.plant:
                self.plant(out)
            fetched: list[dict[str, Any]] = [] if self.plant else request["fetch"]
            for d in fetched:
                if d["attachment"] in self.brings:
                    path = out / "inbox" / f"{d['item']}__{d['attachment']}" / d["expected_name"]
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b"%PDF")
            brought = sum(d["attachment"] in self.brings for d in request["fetch"])
            counts = {"brought": brought, "not_brought": len(request["fetch"]) - brought, "refused": 0}
            outcome = "stopped" if self.fetch_reason else "ok"
            return {"event": "end", "outcome": outcome, "reason": self.fetch_reason, "attachments": counts}
        self.out = out
        if self.dies:
            raise ContainerError("died")
        if self.first_ends:
            return self.first_ends.pop(0)
        time.sleep(self.takes)
        for event in self.events:
            on_event(event)
        for i in range(self.end.get("classes", {}).get("read", 0)):
            (out / f"alfabeta-capture-{request['run']}-c{i}-20261118-080000.json").write_text("{}")
        return self.end


class FakeSteps:
    def __init__(
        self, fail: str | None = None, downloads: list[dict[str, Any]] | None = None, full_review: bool = False
    ) -> None:
        self.calls: list[tuple[list[str], str]] = []
        self.fail = fail
        self.downloads = downloads or []
        self.full_review = full_review

    def __call__(self, args: list[str], run: str) -> dict[str, Any]:
        self.calls.append((args, run))
        if self.fail == args[1]:
            return {"ok": False, "reason": "drive_not_mounted"}
        if args[:2] == ["download", "collect"]:
            return {"collected": [], "pending": [], "classes": ["c0"]}
        if args[:2] == ["classroom", "plan"]:
            return {
                "classes": ["c0"],
                "pending_decisions": [{"type": "class_link"}],
                "downloads": self.downloads,
                "full_review": self.full_review,
            }
        if args[:2] == ["classroom", "apply"]:
            return {"result": "ok", "added": 2, "changed": 0}
        return {}


OK = {"event": "end", "outcome": "ok", "reason": None, "classes": {"read": 1, "failed": 0}, "blocked": {"presses": 1}}


def _cfg(tmp_path: Path, profile_read: bool = True) -> refresh.RefreshConfig:
    return refresh.RefreshConfig(
        student=STUDENT,
        account=ACCOUNT,
        profile_read=profile_read,
        data_dir=tmp_path / "home" / STUDENT / "data",
        downloads=tmp_path / "downloads",
        idle_minutes=5,
        times=TIMES,
        wait_minutes=60,
    )


def _deps(
    container: FakeContainer,
    store: FakeStore | None = None,
    inside: bool = False,
    started_by: str = "command",
    steps: FakeSteps | None = None,
    now: dt.datetime = NOW,
    pauses: list[float] | None = None,
) -> tuple[refresh.Deps, FakeNotifier, FakeSteps]:
    notifier, steps = FakeNotifier(), steps or FakeSteps()
    waited = pauses if pauses is not None else []
    deps = refresh.Deps(
        container=container,
        store=store or FakeStore(),
        notifier=notifier,
        steps=steps,
        today=TODAY,
        inside_claude=inside,
        started_by=started_by,
        now=now,
        pause=waited.append,
    )
    return deps, notifier, steps


def _go(tmp_path: Path, container: FakeContainer, **kw: Any) -> tuple[dict[str, Any], FakeNotifier, FakeSteps, Path]:
    cfg = _cfg(tmp_path, kw.pop("profile_read", True))
    deps, notifier, steps = _deps(container, **kw)
    lock = state.Lock(tmp_path / "home", cfg.data_dir)
    result = refresh.refresh(cfg, lock, deps, None)
    assert not lock.held()
    return result, notifier, steps, cfg.data_dir


def _log(data: Path) -> list[dict[str, Any]]:
    path = data / "log.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def test_switched_off_is_disabled_and_starts_nothing(tmp_path: Path) -> None:
    container = FakeContainer(OK)
    result, notifier, _, _ = _go(tmp_path, container, profile_read=False)
    assert result["reason"] == "disabled" and container.requests == [] and notifier.texts == []


def test_a_full_read_collects_plans_and_applies_once(tmp_path: Path) -> None:
    container = FakeContainer(OK)
    result, notifier, steps, data = _go(tmp_path, container, started_by="schedule")
    assert result["ok"] and result["outcome"] == "ok" and result["started_by"] == "schedule"
    assert result["apply"] == {"added": 2, "changed": 0, "pending_decisions": 1}
    assert result["capture"]["collected"] == 1
    assert [c[0][:2] for c in steps.calls] == [["download", "collect"], ["classroom", "plan"], ["classroom", "apply"]]
    run = container.requests[0]["run"]
    assert {c[1] for c in steps.calls} == {run}
    assert sorted(p.name for p in (tmp_path / "downloads").iterdir()) == [
        f"alfabeta-capture-{run}-c0-20261118-080000.json"
    ]
    assert not (data / f"classroom-out-{run}").exists()
    assert notifier.texts == []
    line = _log(data)[-1]
    assert (
        line["type"] == "classroom_refresh" and line["started_by"] == "schedule" and line["blocked"] == {"presses": 1}
    )


def test_the_password_goes_on_stdin_only_with_the_sign_in_allowed(tmp_path: Path) -> None:
    container = FakeContainer(OK)
    _go(tmp_path, container)
    assert container.requests == [
        {"run": container.requests[0]["run"], "account": ACCOUNT, "password": PASSWORD, "signin": True}
    ]


def test_inside_claude_code_no_password_and_no_notification(tmp_path: Path) -> None:
    container = FakeContainer(
        {"event": "end", "outcome": "stopped", "reason": "session_expired", "classes": {"read": 0, "failed": 0}}
    )
    result, notifier, steps, _ = _go(tmp_path, container, inside=True)
    assert container.requests[0]["password"] is None and container.requests[0]["signin"] is False
    assert result["reason"] == "session_expired" and notifier.texts == [] and steps.calls == []


def test_the_mark_forbids_the_sign_in(tmp_path: Path) -> None:
    data = _cfg(tmp_path).data_dir
    data.mkdir(parents=True)
    (data / MARK).write_text("2026-11-17\n")
    container = FakeContainer(
        {"event": "end", "outcome": "stopped", "reason": "wrong_password", "classes": {"read": 0, "failed": 0}}
    )
    _go(tmp_path, container)
    assert container.requests[0]["signin"] is False and container.requests[0]["password"] is None


def test_no_stored_password_sends_null(tmp_path: Path) -> None:
    container = FakeContainer(
        {"event": "end", "outcome": "stopped", "reason": "no_password", "classes": {"read": 0, "failed": 0}}
    )
    result, notifier, _, _ = _go(tmp_path, container, store=FakeStore(None))
    assert container.requests[0]["password"] is None and container.requests[0]["signin"] is True
    assert result["reason"] == "no_password" and "classroom password set" in notifier.texts[0]


def test_a_wrong_password_sets_the_mark_and_tells_the_family(tmp_path: Path) -> None:
    container = FakeContainer(
        {"event": "end", "outcome": "stopped", "reason": "wrong_password", "classes": {"read": 0, "failed": 0}}
    )
    result, notifier, steps, data = _go(tmp_path, container)
    assert result["reason"] == "wrong_password" and (data / MARK).read_text() == "2026-11-18\n"
    assert steps.calls == [] and len(notifier.texts) == 1
    text = notifier.texts[0]
    assert "wrong_password" in text and STUDENT in text and ACCOUNT not in text and PASSWORD not in text


def test_a_sign_in_stop_writes_nothing_to_the_students_folder(tmp_path: Path) -> None:
    for code in ("challenge", "rejected", "second_factor", "other_sign_in", "unreachable"):
        container = FakeContainer(
            {"event": "end", "outcome": "stopped", "reason": code, "classes": {"read": 0, "failed": 0}}
        )
        result, notifier, steps, _ = _go(tmp_path / code, container)
        assert result["reason"] == code and steps.calls == [] and code in notifier.texts[0]
        assert not (tmp_path / code / "downloads").exists()
        assert container.out is not None and not container.out.exists()  # the out folder is dropped


def test_docker_down_or_no_image_is_docker_unavailable(tmp_path: Path) -> None:
    for name, container in (("down", FakeContainer(OK, up=False)), ("build", FakeContainer(OK, builds=False))):
        result, notifier, _, _ = _go(tmp_path / name, container)
        assert result["reason"] == "docker_unavailable" and container.requests == []
        assert "Docker Desktop" in notifier.texts[0]


def test_a_partial_read_still_applies_what_was_read(tmp_path: Path) -> None:
    end = {"event": "end", "outcome": "partial", "reason": "session_expired", "classes": {"read": 1, "failed": 2}}
    result, _, steps, _ = _go(tmp_path, FakeContainer(end))
    assert result["outcome"] == "partial" and len(steps.calls) == 3


def test_a_held_lock_is_lock_busy(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    lock = state.Lock(tmp_path / "home", cfg.data_dir)
    run = lock.take(RunMode.INTERACTIVE, 5)
    try:
        container = FakeContainer(OK)
        deps, _, _ = _deps(container)
        result = refresh.refresh(cfg, lock, deps, None)
        assert result["reason"] == "lock_busy" and container.requests == []
    finally:
        lock.release(run)


def test_neither_account_nor_password_in_the_log_or_result(tmp_path: Path) -> None:
    result, _, _, data = _go(tmp_path, FakeContainer(OK))
    text = json.dumps(result, ensure_ascii=False) + (data / "log.jsonl").read_text()
    assert ACCOUNT not in text and PASSWORD not in text


SESSION_EXPIRED = {
    "event": "end",
    "outcome": "stopped",
    "reason": "session_expired",
    "classes": {"read": 0, "failed": 0},
}


def test_with_the_mark_a_dead_session_is_still_wrong_password(tmp_path: Path) -> None:
    # The real container answers `session_expired` when it may not sign in (read.py); the notice
    # must keep asking for the new password, not send the family to sync by hand.
    data = _cfg(tmp_path).data_dir
    data.mkdir(parents=True)
    (data / MARK).write_text("2026-11-17\n")
    result, notifier, _, _ = _go(tmp_path, FakeContainer(SESSION_EXPIRED))
    assert result["reason"] == "wrong_password" and "classroom password set" in notifier.texts[0]
    assert (data / MARK).read_text() == "2026-11-17\n"  # the mark keeps the day the password failed


def test_with_the_mark_another_account_stays_session_expired(tmp_path: Path) -> None:
    data = _cfg(tmp_path).data_dir
    data.mkdir(parents=True)
    (data / MARK).write_text("2026-11-17\n")
    other = FakeContainer(SESSION_EXPIRED, events=[{"event": "account", "result": "other_account"}])
    result, _, _, _ = _go(tmp_path, other)
    assert result["reason"] == "session_expired"


def test_inside_claude_code_a_dead_session_stays_session_expired_even_with_the_mark(tmp_path: Path) -> None:
    data = _cfg(tmp_path).data_dir
    data.mkdir(parents=True)
    (data / MARK).write_text("2026-11-17\n")
    result, notifier, _, _ = _go(tmp_path, FakeContainer(SESSION_EXPIRED), inside=True)
    assert result["reason"] == "session_expired" and notifier.texts == []


def test_a_keychain_that_does_not_answer_is_no_password(tmp_path: Path) -> None:
    container = FakeContainer(OK)
    result, notifier, _, _ = _go(tmp_path, container, store=FakeStore(locked=True))
    assert result["reason"] == "no_password" and container.requests == [] and notifier.texts


def test_a_container_that_dies_at_start_is_docker_unavailable(tmp_path: Path) -> None:
    container = FakeContainer(OK, dies=True)
    result, notifier, steps, _ = _go(tmp_path, container)
    assert result["reason"] == "docker_unavailable" and steps.calls == [] and notifier.texts
    assert container.out is not None and not container.out.exists()


@pytest.mark.parametrize(("fail", "ran"), [("collect", 1), ("plan", 2), ("apply", 3)])
def test_a_failed_step_stops_the_run_and_tells_the_family(tmp_path: Path, fail: str, ran: int) -> None:
    steps = FakeSteps(fail=fail)
    result, notifier, _, _ = _go(tmp_path, FakeContainer(OK), steps=steps)
    assert result["ok"] is False and result["outcome"] == "stopped" and result["reason"] == "drive_not_mounted"
    assert len(steps.calls) == ran and "drive_not_mounted" in notifier.texts[0]


def test_an_ok_read_of_no_class_still_plans_and_applies(tmp_path: Path) -> None:
    end = {"event": "end", "outcome": "ok", "reason": None, "classes": {"read": 0, "failed": 0}}
    result, notifier, steps, _ = _go(tmp_path, FakeContainer(end))
    assert result["outcome"] == "ok" and len(steps.calls) == 3 and notifier.texts == []


def test_the_log_line_carries_how_long_the_read_took(tmp_path: Path) -> None:
    _, _, _, data = _go(tmp_path, FakeContainer(OK | {"seconds": 860}))
    assert _log(data)[-1]["seconds"] == 860


def test_inside_a_run_it_neither_takes_nor_releases_the_lock(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    lock = state.Lock(tmp_path / "home", cfg.data_dir)
    run = lock.take(RunMode.INTERACTIVE, 5)
    try:
        container = FakeContainer(OK)
        deps, _, steps = _deps(container)
        result = refresh.refresh(cfg, lock, deps, run)
        assert result["outcome"] == "ok" and container.requests[0]["run"] == run
        assert {c[1] for c in steps.calls} == {run}
        assert lock.held() and (lock.lease() or {}).get("run") == run
    finally:
        lock.release(run)


def test_the_lock_is_renewed_while_the_container_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(refresh, "RENEW_SECONDS", 0.02)
    cfg = _cfg(tmp_path)
    lock = state.Lock(tmp_path / "home", cfg.data_dir)
    renewed: list[str | None] = []
    original = state.Lock.renew

    def renew(self: state.Lock, run: str | None) -> dict[str, Any]:
        renewed.append(run)
        return original(self, run)

    monkeypatch.setattr(state.Lock, "renew", renew)
    deps, _, _ = _deps(FakeContainer(OK, takes=0.3))
    refresh.refresh(cfg, lock, deps, None)
    assert len(renewed) >= 3 and not lock.held()


@pytest.mark.parametrize(
    ("end", "code"),
    [
        (OK, 0),
        ({"event": "end", "outcome": "partial", "reason": "session_expired", "classes": {"read": 1, "failed": 1}}, 3),
        (SESSION_EXPIRED, 1),
    ],
)
def test_the_exit_code_follows_the_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], end: dict[str, Any], code: int
) -> None:
    monkeypatch.delenv(state.RUN_ENV, raising=False)
    cfg = _cfg(tmp_path)
    deps, _, _ = _deps(FakeContainer(end), inside=True)
    assert cli.cmd_refresh(cfg, state.Lock(tmp_path / "home", cfg.data_dir), deps) == code
    printed = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert printed["outcome"] in ("ok", "partial", "stopped") and ACCOUNT not in json.dumps(printed)


@pytest.mark.parametrize(
    ("ran", "answer"),
    [
        (subprocess.CompletedProcess([], 1, "", "Traceback"), {"ok": False, "reason": "unexpected_ui"}),
        (
            subprocess.CompletedProcess([], 1, '{"collected": [], "pending": ["a.pdf"]}\n', ""),
            {"collected": [], "pending": ["a.pdf"]},
        ),
        (
            subprocess.CompletedProcess([], 1, '{"ok": false, "reason": "drive_not_mounted"}\n', ""),
            {"ok": False, "reason": "drive_not_mounted"},
        ),
        (subprocess.TimeoutExpired([], 1), {"ok": False, "reason": "timeout"}),
    ],
)
def test_a_step_answers_its_json_or_a_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ran: Any, answer: dict[str, Any]
) -> None:
    seen: list[dict[str, Any]] = []

    def run(argv: list[str], **kw: Any) -> Any:
        seen.append({"argv": argv, "env": kw["env"]})
        if isinstance(ran, BaseException):
            raise ran
        return ran

    monkeypatch.setattr(cli.subprocess, "run", run)
    assert cli.run_step(tmp_path, STUDENT)(["download", "collect"], "run1") == answer
    assert seen[0]["env"][state.RUN_ENV] == "run1" and seen[0]["argv"][-2:] == ["--student", STUDENT]


def _download(item: str, attachment: str, name: str) -> dict[str, Any]:
    url = f"https://drive.usercontent.google.com/download?id={attachment}&export=download&authuser=5"
    return {"item": item, "attachment": attachment, "url": url, "expected_name": name, "batch": 0, "why": "new"}


def test_the_plans_downloads_are_fetched_and_placed_before_apply(tmp_path: Path) -> None:
    steps = FakeSteps(downloads=[_download("i1", "f1", "Tema 3.pdf"), _download("i2", "f2", "b.pdf")])
    container = FakeContainer(OK, brings=frozenset({"f1"}))
    result, _, _, data = _go(tmp_path, container, steps=steps)
    assert result["capture"]["attachments"] == {"brought": 1, "not_brought": 1, "refused": 0}
    assert (data / "inbox" / "i1__f1" / "Tema 3.pdf").read_bytes() == b"%PDF"
    assert not (data / "inbox" / "i2__f2").exists()
    second = container.requests[1]
    assert second["signin"] is False and second["password"] is None and second["run"] == container.requests[0]["run"]
    assert [d["attachment"] for d in second["fetch"]] == ["f1", "f2"] and "batch" not in second["fetch"][0]
    assert [c[0][1] for c in steps.calls] == ["collect", "plan", "apply"]
    assert not list(data.glob("classroom-out-*"))


def _review(item: str, attachment: str, name: str) -> dict[str, Any]:
    return _download(item, attachment, name) | {"why": "review"}


@pytest.mark.parametrize(
    ("first", "fetch_reason", "fetch_dies", "incomplete"),
    [
        (OK, None, False, False),  # the pass got to the end of its list: the review is done
        (OK, "session_expired", False, True),  # 2026-11-20: cut after 5 of 146 (#290)
        (OK, None, True, True),  # the pass's container died
        (  # the first pass found the session gone: the second never ran
            {"event": "end", "outcome": "partial", "reason": "session_expired", "classes": {"read": 1, "failed": 1}},
            None,
            False,
            True,
        ),
    ],
)
def test_a_review_the_pass_did_not_get_through_is_applied_as_incomplete(
    tmp_path: Path, first: dict[str, Any], fetch_reason: str | None, fetch_dies: bool, incomplete: bool
) -> None:
    steps = FakeSteps(downloads=[_download("i1", "f1", "a.pdf"), _review("i2", "f2", "b.pdf")], full_review=True)
    container = FakeContainer(first, fetch_reason=fetch_reason, fetch_dies=fetch_dies)
    _go(tmp_path, container, steps=steps)
    apply_args = next(c[0] for c in steps.calls if c[0][1] == "apply")
    assert ("--review-incomplete" in apply_args) is incomplete


def test_a_cut_pass_with_no_review_to_do_marks_nothing(tmp_path: Path) -> None:
    # A full-review run whose plan holds only new files: a cut loses them, but no review was asked for.
    steps = FakeSteps(downloads=[_download("i1", "f1", "a.pdf")], full_review=True)
    _go(tmp_path, FakeContainer(OK, fetch_reason="session_expired"), steps=steps)
    assert "--review-incomplete" not in next(c[0] for c in steps.calls if c[0][1] == "apply")


def test_nothing_to_fetch_starts_no_second_pass(tmp_path: Path) -> None:
    container = FakeContainer(OK)
    result, _, _, _ = _go(tmp_path, container)
    assert len(container.requests) == 1 and result["capture"]["attachments"]["not_brought"] == 0


def test_a_session_gone_in_the_first_pass_skips_the_second(tmp_path: Path) -> None:
    end = {"event": "end", "outcome": "partial", "reason": "session_expired", "classes": {"read": 1, "failed": 1}}
    steps = FakeSteps(downloads=[_download("i1", "f1", "a.pdf")])
    container = FakeContainer(end, brings=frozenset({"f1"}))
    result, _, steps, _ = _go(tmp_path, container, steps=steps)
    assert len(container.requests) == 1 and result["capture"]["attachments"]["not_brought"] == 1
    assert [c[0][1] for c in steps.calls] == ["collect", "plan", "apply"]


def test_a_name_with_a_way_out_is_never_moved(tmp_path: Path) -> None:
    # The fake writes it at out/inbox/fuera.pdf; a host that trusted the name would move it to data/inbox/.
    steps = FakeSteps(downloads=[_download("i1", "f1", "../fuera.pdf")])
    container = FakeContainer(OK, brings=frozenset({"f1"}))
    result, _, _, data = _go(tmp_path, container, steps=steps)
    assert result["capture"]["attachments"]["brought"] == 0
    assert not list(data.rglob("fuera.pdf")) and not (data / "inbox").exists()


@pytest.mark.parametrize(
    "end",
    [
        {"event": "end", "outcome": "partial", "reason": "challenge", "classes": {"read": 1, "failed": 1}},
        {
            "event": "end",
            "outcome": "ok",
            "reason": None,
            "classes": {"read": 1, "failed": 0},
            "blocked": {"redirects": 1},
        },
    ],
)
def test_a_challenge_or_a_breach_skips_the_second_pass(tmp_path: Path, end: dict[str, Any]) -> None:
    steps = FakeSteps(downloads=[_download("i1", "f1", "a.pdf")])
    container = FakeContainer(end, brings=frozenset({"f1"}))
    _go(tmp_path, container, steps=steps)
    assert len(container.requests) == 1


def test_a_second_pass_that_dies_still_applies(tmp_path: Path) -> None:
    steps = FakeSteps(downloads=[_download("i1", "f1", "a.pdf")])
    result, _, steps, _ = _go(tmp_path, FakeContainer(OK, fetch_dies=True), steps=steps)
    assert result["outcome"] == "ok" and result["capture"]["attachments"]["not_brought"] == 1
    assert [c[0][1] for c in steps.calls] == ["collect", "plan", "apply"]


def test_the_refused_hosts_reach_the_log(tmp_path: Path) -> None:
    refused = {"event": "attachment", "result": "refused", "why": "host", "host": "doc-0s.googleusercontent.com"}
    steps = FakeSteps(downloads=[_download("i1", "f1", "a.pdf")])
    _, _, _, data = _go(tmp_path, FakeContainer(OK, fetch_events=[refused]), steps=steps)
    assert _log(data)[-1]["refused_hosts"] == ["doc-0s.googleusercontent.com"]


def test_a_symlinked_folder_in_out_moves_nothing(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "a.pdf").write_bytes(b"not the container's")

    def plant(out: Path) -> None:
        (out / "inbox").mkdir(parents=True)
        (out / "inbox" / "i1__f1").symlink_to(elsewhere)

    steps = FakeSteps(downloads=[_download("i1", "f1", "a.pdf")])
    result, _, _, data = _go(tmp_path, FakeContainer(OK, plant=plant), steps=steps)
    assert result["capture"]["attachments"]["brought"] == 0
    assert (elsewhere / "a.pdf").exists() and not (data / "inbox").exists()


def test_a_symlink_loop_in_out_is_not_brought_and_apply_runs(tmp_path: Path) -> None:
    def plant(out: Path) -> None:
        (out / "inbox").mkdir(parents=True)
        (out / "inbox" / "i1__f1").symlink_to(out / "inbox" / "i1__f1")

    steps = FakeSteps(downloads=[_download("i1", "f1", "a.pdf")])
    result, _, steps, data = _go(tmp_path, FakeContainer(OK, plant=plant), steps=steps)
    assert result["outcome"] == "ok" and result["capture"]["attachments"]["brought"] == 0
    assert [c[0][1] for c in steps.calls] == ["collect", "plan", "apply"]
    assert not list(data.glob("classroom-out-*"))


@pytest.mark.parametrize(
    ("now", "ran"),
    [
        (dt.datetime(2026, 11, 18, 8, 0), True),  # at the time
        (dt.datetime(2026, 11, 18, 9, 0), True),  # wait_minutes later, still in
        (dt.datetime(2026, 11, 18, 9, 1), False),  # a Mac that slept through it wakes later
        (dt.datetime(2026, 11, 18, 7, 59), False),
        (dt.datetime(2026, 11, 21, 8, 10), False),  # Saturday: no time that day
    ],
)
def test_the_schedule_does_not_make_up_a_missed_time(tmp_path: Path, now: dt.datetime, ran: bool) -> None:
    container = FakeContainer(OK)
    result, notifier, _, data = _go(tmp_path, container, started_by="schedule", now=now)
    assert bool(container.requests) is ran
    if not ran:
        assert result == {"ok": True, "started_by": "schedule", "outcome": "skipped", "reason": "outside_hours"}
        assert _log(data)[-1]["reason"] == "outside_hours" and notifier.texts == []
        assert not state.Lock(tmp_path / "home", data).held()


def test_by_hand_the_hours_do_not_apply(tmp_path: Path) -> None:
    container = FakeContainer(OK)
    _go(tmp_path, container, now=dt.datetime(2026, 11, 21, 23, 0))
    assert container.requests


def test_skipped_exits_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(state.RUN_ENV, raising=False)
    cfg = _cfg(tmp_path)
    deps, _, _ = _deps(FakeContainer(OK), started_by="schedule", now=dt.datetime(2026, 11, 21, 8, 10))
    assert cli.cmd_refresh(cfg, state.Lock(tmp_path / "home", cfg.data_dir), deps) == 0


@pytest.mark.parametrize(
    ("times", "wait", "now", "inside"),
    [
        ({"wednesday": "08:00"}, 0, dt.datetime(2026, 11, 18, 8, 0, 3), True),  # launchd starts a few seconds late
        ({"wednesday": "08:00"}, 0, dt.datetime(2026, 11, 18, 8, 10, 30), False),  # past the grace
        ({"wednesday": "23:50"}, 60, dt.datetime(2026, 11, 19, 0, 10), True),  # Thursday, Wednesday's window
        ({"wednesday": "23:50"}, 60, dt.datetime(2026, 11, 19, 0, 51), False),
        ({"thursday": "00:05"}, 60, dt.datetime(2026, 11, 18, 23, 59), False),  # not before its time
    ],
)
def test_the_hours_window(times: dict[str, str], wait: int, now: dt.datetime, inside: bool) -> None:
    assert refresh.in_hours(times, wait, now) is inside


def test_the_first_pass_sign_in_and_redirects_reach_the_log(tmp_path: Path) -> None:
    end = {"event": "end", "outcome": "stopped", "reason": "unexpected_ui", "classes": {"read": 0, "failed": 0}}
    events = [
        {"event": "signin_page", "host": "accounts.google.com", "path": "/v3/signin/identifier"},
        {
            "event": "signin_load",
            "host": "accounts.google.es",
            "path": "/accounts/SetSID",
            "main_frame": True,
            "via": "redirect",
            "allowed": True,
        },
        {"event": "signin", "result": "signed_in"},
        {"event": "redirect", "to": "other", "path": "", "main_frame": True, "host": "accounts.google.de"},
        {"event": "typed", "field": "password"},
    ]
    _, _, _, data = _go(tmp_path, FakeContainer(end, events=events))
    line = _log(data)[-1]
    assert line["signin"] == "signed_in"
    assert line["signin_pages"] == [{"host": "accounts.google.com", "path": "/v3/signin/identifier"}]
    loads = [
        {
            "host": "accounts.google.es",
            "path": "/accounts/SetSID",
            "main_frame": True,
            "via": "redirect",
            "allowed": True,
        }
    ]
    assert line["signin_loads"] == loads
    assert line["redirects"] == [{"to": "other", "host": "accounts.google.de", "path": "", "main_frame": True}]
    assert "first_pass" not in line and "typed" not in json.dumps(line)


class _DyingAfterEvents(FakeContainer):
    def run(
        self, image: str, request: dict[str, Any], profile: Path, out: Path, on_event: Callable[[dict[str, Any]], None]
    ) -> dict[str, Any]:
        self.out = out
        out.mkdir(parents=True, exist_ok=True)
        on_event({"event": "signin", "result": "signed_in"})
        raise ContainerError("died")


def test_a_first_pass_that_dies_still_logs_what_it_said(tmp_path: Path) -> None:
    result, _, _, data = _go(tmp_path, _DyingAfterEvents(OK))
    assert result["reason"] == "docker_unavailable" and _log(data)[-1]["signin"] == "signed_in"


def test_the_family_sees_one_line_per_step(tmp_path: Path) -> None:
    events = [
        {"event": "browser", "timezone": "Europe/Madrid"},
        {"event": "home", "state": "expired"},
        {"event": "signin_start"},
        {"event": "signin_page", "host": "accounts.google.com", "path": "/v3/signin/identifier"},
        {"event": "typed", "field": "password"},
        {"event": "signin", "result": "signed_in"},
        {"event": "home", "state": "alive"},
        {"event": "account", "result": "ok"},
        {"event": "classes", "listed": 12, "to_read": 2},
        {"event": "class_start", "index": 1, "total": 2},
        {"event": "class", "id": "c1", "type": "class", "complete": True},
        {"event": "class_start", "index": 2, "total": 2},
        {"event": "class", "id": "c2", "type": "class", "complete": False},
    ]
    steps = FakeSteps(downloads=[_download("i1", "f1", "a.pdf")])
    container = FakeContainer(OK, events=events, brings=frozenset({"f1"}))
    cfg = _cfg(tmp_path)
    lines: list[str] = []
    deps, _, _ = _deps(container, steps=steps)
    deps = dataclasses.replace(deps, say=lines.append)
    refresh.refresh(cfg, state.Lock(tmp_path / "home", cfg.data_dir), deps, None)
    assert lines == [
        "preparing the container …",
        "opening Classroom …",
        "the session has expired",
        "signing in with the stored password …",
        "✓ signed in",
        "✓ Classroom session open",
        "✓ school account checked",
        "✓ 2 classes to read",
        "✓ class 1/2",
        "✓ class 2/2 (incomplete: read again next time)",
        "collecting the captures and planning …",
        "fetching 1 attachment …",
        "✓ attachments: 1 brought, 0 not brought, 0 refused",
        "placing in Drive …",
    ]
    assert not any(ACCOUNT in line or PASSWORD in line for line in lines)


def test_a_stop_says_where(tmp_path: Path) -> None:
    events = [{"event": "home", "state": "alive"}, {"event": "account", "result": "none"}]
    end = {"event": "end", "outcome": "stopped", "reason": "unexpected_ui", "step": "account"}
    cfg = _cfg(tmp_path)
    lines: list[str] = []
    deps, _, _ = _deps(FakeContainer(end | {"classes": {"read": 0, "failed": 0}}, events=events))
    refresh.refresh(cfg, state.Lock(tmp_path / "home", cfg.data_dir), dataclasses.replace(deps, say=lines.append), None)
    assert lines[-1] == "✗ the page names no account"
    assert _log(cfg.data_dir)[-1]["step"] == "account"


def test_the_command_ends_with_a_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv(state.RUN_ENV, raising=False)
    cfg = _cfg(tmp_path)
    deps, _, _ = _deps(FakeContainer(OK))
    assert cli.cmd_refresh(cfg, state.Lock(tmp_path / "home", cfg.data_dir), deps) == 0
    err = capsys.readouterr().err
    # One line per message, the local time after the program's name (constitution 2.12.0, Language).
    assert re.search(
        r"^alfabeta: \d{4}-\d\d-\d\dT\d\d:\d\d:\d\d ✓ read finished: 1 class read, 2 added, 0 changed, "
        r"1 pending decisions$",
        err,
        re.MULTILINE,
    )


def test_too_little_docker_memory_stops_before_the_keychain_and_the_container(tmp_path: Path) -> None:
    container, store = FakeContainer(OK, memory=SHORT), FakeStore()
    result, notifier, steps, data = _go(tmp_path, container, store=store)
    assert result["outcome"] == "stopped" and result["reason"] == "docker_low_memory" and not result["ok"]
    assert container.probed == ["alfabeta-classroom-read:test"]
    assert store.asked == 0 and container.requests == [] and steps.calls == []
    assert notifier.texts == [
        "alfabeta (s9): la lectura de Classroom se ha parado (docker_low_memory). Para seguir, "
        "cierra otros contenedores o sube la memoria de Docker Desktop."
    ]
    line = _log(data)[-1]
    assert line["reason"] == "docker_low_memory" and line["memory"] == {"total_mb": 7835, "available_mb": 1213}
    assert not (data / MARK).exists()


def test_the_floor_is_above_the_failing_reading_and_a_read_at_it_goes_on(tmp_path: Path) -> None:
    assert refresh.READ_FLOOR_MB > SHORT.available_mb
    at = FakeContainer(OK, memory=Memory(7835, refresh.READ_FLOOR_MB))
    under = FakeContainer(OK, memory=Memory(7835, refresh.READ_FLOOR_MB - 1))
    assert _go(tmp_path / "at", at)[0]["outcome"] == "ok" and len(at.requests) == 1
    assert _go(tmp_path / "under", under)[0]["reason"] == "docker_low_memory" and under.requests == []


def test_the_spec_and_the_quickstart_name_the_floor_and_the_command_the_code_uses() -> None:
    spec = ROOT / "specs" / "006-classroom-from-the-phone"
    for name in ("spec.md", "quickstart.md"):
        assert f"{refresh.READ_FLOOR_MB} MB" in (spec / name).read_text(), name
    command = " ".join(memory_argv("<image>"))
    assert command in " ".join((spec / "quickstart.md").read_text().split())


def test_memory_that_cannot_be_read_does_not_stop_the_read_and_the_log_says_so(tmp_path: Path) -> None:
    container = FakeContainer(OK, memory=None)
    cfg = _cfg(tmp_path)
    lines: list[str] = []
    deps, notifier, _ = _deps(container)
    result = refresh.refresh(
        cfg, state.Lock(tmp_path / "home", cfg.data_dir), dataclasses.replace(deps, say=lines.append), None
    )
    assert result["outcome"] == "ok" and len(container.requests) == 1 and notifier.texts == []
    line = _log(cfg.data_dir)[-1]
    assert "memory" in line and line["memory"] is None  # asked and not read: neither a number nor a missing key
    assert "⚠ Docker's available memory could not be read" in lines


def test_every_read_logs_dockers_memory_and_a_run_that_never_asked_has_no_such_key(tmp_path: Path) -> None:
    _, _, _, data = _go(tmp_path / "ok", FakeContainer(OK))
    assert _log(data)[-1]["memory"] == {"total_mb": 7835, "available_mb": 5725}
    _, _, _, data = _go(tmp_path / "down", FakeContainer(OK, up=False))
    assert "memory" not in _log(data)[-1]


def test_low_memory_says_what_was_measured(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    lines: list[str] = []
    deps, _, _ = _deps(FakeContainer(OK, memory=SHORT))
    refresh.refresh(cfg, state.Lock(tmp_path / "home", cfg.data_dir), dataclasses.replace(deps, say=lines.append), None)
    assert lines == [
        "preparing the container …",
        f"✗ Docker has 1213 MB of memory available; the floor for a read is {refresh.READ_FLOOR_MB} MB",
    ]


def test_a_crashed_browser_is_notified_by_its_own_code_with_where_to_look(tmp_path: Path) -> None:
    end = {"event": "end", "outcome": "stopped", "reason": "browser_crashed", "step": "classes"}
    container = FakeContainer(end | {"classes": {"read": 0, "failed": 1}})
    result, notifier, steps, data = _go(tmp_path, container)
    assert result["outcome"] == "stopped" and result["reason"] == "browser_crashed" and steps.calls == []
    assert notifier.texts == [
        "alfabeta (s9): la lectura de Classroom se ha parado (browser_crashed). Para seguir, "
        "mira la memoria de Docker: cierra otros contenedores o súbela en Docker Desktop."
    ]
    assert _log(data)[-1]["reason"] == "browser_crashed" and not (data / MARK).exists()


def test_a_browser_that_crashed_midway_keeps_what_was_read_and_starts_no_second_browser(tmp_path: Path) -> None:
    end = {"event": "end", "outcome": "partial", "reason": "browser_crashed", "classes": {"read": 1, "failed": 1}}
    container = FakeContainer(end, brings=frozenset({"f1"}))
    steps = FakeSteps(downloads=[_download("i1", "f1", "a.pdf")])
    result, notifier, steps, data = _go(tmp_path, container, steps=steps)
    assert result["ok"] and result["outcome"] == "partial" and result["reason"] == "browser_crashed"
    assert len(steps.calls) == 3 and notifier.texts == []
    # The plan asked for an attachment; no attachments pass ran, and apply notes it «no traído».
    assert [r for r in container.requests if "fetch" in r] == []
    assert result["capture"]["attachments"] == {"brought": 0, "not_brought": 1, "refused": 0}
    assert _log(data)[-1]["reason"] == "browser_crashed"


UNREACHABLE_HOME = {
    "event": "end",
    "outcome": "stopped",
    "reason": "unreachable",
    "step": "home",
    "classes": {"read": 0, "failed": 0},
}


def test_a_home_that_did_not_load_is_tried_once_more_after_a_pause(tmp_path: Path) -> None:
    # 2026-11-25 15:15: Classroom's home did not load in 3 s and the day's read was lost.
    pauses: list[float] = []
    container = FakeContainer(OK, first_ends=[UNREACHABLE_HOME])
    result, notifier, _, data = _go(tmp_path, container, started_by="schedule", pauses=pauses)
    assert result["ok"] and result["outcome"] == "ok", result
    assert pauses == [refresh.RETRY_PAUSE_SECONDS]
    assert len([r for r in container.requests if "fetch" not in r]) == 2
    assert notifier.texts == []
    (line,) = [entry for entry in _log(data) if entry.get("type") == "classroom_refresh"]
    assert line["retried"] is True and line["outcome"] == "ok"


def test_a_home_that_does_not_load_twice_stops_unreachable_once(tmp_path: Path) -> None:
    pauses: list[float] = []
    container = FakeContainer(UNREACHABLE_HOME, first_ends=[UNREACHABLE_HOME])
    result, notifier, _, _ = _go(tmp_path, container, started_by="schedule", pauses=pauses)
    assert result["outcome"] == "stopped" and result["reason"] == "unreachable"
    assert pauses == [refresh.RETRY_PAUSE_SECONDS] and len(container.requests) == 2
    assert len(notifier.texts) == 1


@pytest.mark.parametrize(
    "end",
    [
        UNREACHABLE_HOME | {"step": "signin"},  # after the sign-in began: never a second sign-in
        UNREACHABLE_HOME | {"classes": {"read": 3, "failed": 0}},  # classes were read
        UNREACHABLE_HOME | {"reason": "session_expired"},
    ],
)
def test_no_second_try_after_a_sign_in_a_read_or_another_stop(tmp_path: Path, end: dict[str, Any]) -> None:
    pauses: list[float] = []
    container = FakeContainer(OK, first_ends=[end])
    _go(tmp_path, container, pauses=pauses)
    assert pauses == [] and len([r for r in container.requests if "fetch" not in r]) == 1
