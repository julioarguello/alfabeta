"""`classroom refresh`, the container read (spec 006 T008; FR-019, FR-020, FR-022, FR-024a, FR-027, FR-028, FR-032)."""

from __future__ import annotations

import datetime as dt
import json
from typing import TYPE_CHECKING, Any

from alfabeta import state
from alfabeta.classroom import refresh
from alfabeta.classroom.container import ContainerError
from alfabeta.classroom.password import MARK
from alfabeta.model import RunMode

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

STUDENT = "s9"
ACCOUNT = "alumno@example.test"
PASSWORD = "contraseña-inventada-123"
TODAY = dt.date(2026, 11, 18)


class FakeStore:
    def __init__(self, password: str | None = PASSWORD) -> None:
        self.secrets: dict[str, str] = {STUDENT: password} if password else {}

    def get(self, account: str) -> str | None:
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


class FakeContainer:
    """Answers with a scripted end event, writing the captures a read would leave."""

    def __init__(self, end: dict[str, Any], up: bool = True, builds: bool = True) -> None:
        self.end = end
        self.up = up
        self.builds = builds
        self.requests: list[dict[str, Any]] = []

    def available(self) -> bool:
        return self.up

    def ensure_image(self) -> str:
        if not self.builds:
            raise ContainerError("no build")
        return "alfabeta-classroom-read:test"

    def run(
        self, image: str, request: dict[str, Any], profile: Path, out: Path, on_event: Callable[[dict[str, Any]], None]
    ) -> dict[str, Any]:
        self.requests.append(dict(request))
        out.mkdir(parents=True, exist_ok=True)
        for i in range(self.end.get("classes", {}).get("read", 0)):
            (out / f"alfabeta-capture-{request['run']}-c{i}-20261118-080000.json").write_text("{}")
        return self.end


class FakeSteps:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], str]] = []

    def __call__(self, args: list[str], run: str) -> dict[str, Any]:
        self.calls.append((args, run))
        if args[:2] == ["download", "collect"]:
            return {"classes": ["c0"]}
        if args[:2] == ["classroom", "apply"]:
            return {"added": 2, "changed": 0, "pending_decisions": 0}
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
    )


def _deps(container: FakeContainer, store: FakeStore | None = None, inside: bool = False, started_by: str = "command"):
    notifier, steps = FakeNotifier(), FakeSteps()
    deps = refresh.Deps(
        container=container,
        store=store or FakeStore(),
        notifier=notifier,
        steps=steps,
        today=TODAY,
        inside_claude=inside,
        started_by=started_by,
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
