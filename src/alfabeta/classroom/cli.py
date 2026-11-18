"""The container read's commands (spec 006 contracts/cli.md, amendment of 2026-11-17)."""

from __future__ import annotations

import contextlib
import datetime as dt
import json
import os
import subprocess
import sys
from typing import TYPE_CHECKING, Any, cast

from alfabeta import state
from alfabeta.classroom import refresh
from alfabeta.classroom.agent import ClassroomAgent, ClassroomAgentSpec, system_agent
from alfabeta.classroom.password import PasswordError, PasswordStore, Prompt
from alfabeta.google.keychain import KeychainError, TokenStore
from alfabeta.model import RunMode, StopReason
from alfabeta.notes.agent import AgentError

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_PARTIAL = 3
STEP_TIMEOUT_SECONDS = 15 * 60
# A password command touches no profile and writes for a moment: it holds the lock only while it
# writes, never while the family types (`set` asks first).
_IDLE_MINUTES = 5


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def _say(message: str) -> None:
    """One line for people on stderr: English, with the local time (constitution 2.12.0, Language)."""
    print(f"alfabeta: {dt.datetime.now():%Y-%m-%dT%H:%M:%S} {message}", file=sys.stderr)


def say(message: str) -> None:
    """One progress line for people, on stderr (python-cli-output §1)."""
    _say(message)


def _fail(reason: str, message: str) -> int:
    _say(message)
    _emit({"ok": False, "reason": reason})
    return EXIT_INVALID


def _locked(lock: state.Lock, body: Callable[[], int]) -> int:
    """Run `body` under the student's and the browser lock (FR-024a), or inside the run that holds them."""
    run = os.environ.get(state.RUN_ENV)
    lease = lock.lease()
    if run and lease is not None and lease.get("run") == run and lock.held():
        return body()
    try:
        taken = lock.take(RunMode.INTERACTIVE, _IDLE_MINUTES)
    except state.LockError as err:
        return _fail(str(err.reason), str(err))
    try:
        return body()
    finally:
        with contextlib.suppress(state.LockError):  # a watcher that idled out has released it already
            lock.release(taken)


def run_step(home: Path, student: str) -> refresh.Steps:
    """Spec 001's own commands inside the run, as the classroom-sync skill runs them.

    A step that runs out of time, or exits non-zero with no JSON, answers `{"ok": false, "reason"}`;
    `download collect`'s own exit 1 (an attachment still missing) carries its JSON and is no failure.
    """

    def step(args: list[str], run: str) -> dict[str, Any]:
        env = os.environ | {state.RUN_ENV: run}
        try:
            done = subprocess.run(
                [sys.executable, "-m", "alfabeta", "--home", str(home), *args, "--student", student],
                capture_output=True,
                text=True,
                env=env,
                timeout=STEP_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "reason": str(StopReason.TIMEOUT)}
        lines = [line for line in done.stdout.splitlines() if line.startswith("{")]
        try:
            result = cast("dict[str, Any]", json.loads(lines[-1])) if lines else {}
        except ValueError:
            result = {}
        if not result and done.returncode != 0:
            # No JSON and a failed exit: a crash, not one of the step's own answers.
            return {"ok": False, "reason": str(StopReason.UNEXPECTED_UI)}
        return result

    return step


def cmd_refresh(cfg: refresh.RefreshConfig, lock: state.Lock, deps: refresh.Deps) -> int:
    """`classroom refresh`, the container read (contracts/cli.md, amendment of 2026-11-17)."""
    result = refresh.refresh(cfg, lock, deps, os.environ.get(state.RUN_ENV))
    _emit(result)
    if result["outcome"] == "skipped":
        _say("outside the reading hours: nothing read now")
        return EXIT_OK
    if result["outcome"] in ("ok", "partial"):
        capture, applied = result.get("capture", {}), result.get("apply", {})
        read = int(capture.get("read", 0))
        summary = (
            f"{read} {'class' if read == 1 else 'classes'} read, {applied.get('added', 0)} added, "
            f"{applied.get('changed', 0)} changed, {applied.get('pending_decisions', 0)} pending decisions"
        )
        if result["outcome"] == "ok":
            _say(f"{refresh.OK} read finished: {summary}")
            return EXIT_OK
        _say(f"{refresh.WARN} partial read ({result['reason']}): {summary}")
        return EXIT_PARTIAL
    _say(f"{refresh.FAIL} the read stopped: {result['reason']}")
    return EXIT_INVALID


def cmd_password(
    action: str,
    student: str,
    data_dir: Path,
    lock: state.Lock,
    store: TokenStore,
    prompt: Prompt,
    is_tty: bool,
) -> int:
    """`classroom password set|delete` (FR-031). Never prints the password."""
    passwords = PasswordStore(store, data_dir, student)
    answer = ""
    if action == "set":
        try:
            answer = passwords.ask(prompt, is_tty)
        except PasswordError as err:
            return _fail(err.reason, str(err))

    def body() -> int:
        try:
            if action == "set":
                passwords.store_password(answer)
                _say("password stored in the keychain")
                _emit({"ok": True, "stored": True})
            else:
                removed = passwords.delete()
                _emit({"ok": True, "removed": removed})
        except KeychainError as err:
            return _fail(str(StopReason.INVALID_CONFIG), str(err))
        return EXIT_OK

    return _locked(lock, body)


_AGENT_REFUSALS = {
    "invalid_config": "[schedule] sets no time on any day: nothing to run",
    "disabled": "[classroom] profile_read is false: switch it on before installing the agent",
    "no_uv": "uv was not found on this PATH: install it, then install the agent again",
    "docker_unavailable": "docker was not found on this PATH: install Docker Desktop, then install the agent again",
    "no_repository": "[tools] repository is not a folder on this Mac",
    "launchctl_failed": "launchd did not load the agent; nothing was left installed",
}


def cmd_agent(action: str, spec: ClassroomAgentSpec, profile_read: bool, agent: ClassroomAgent | None = None) -> int:
    """`classroom agent install|uninstall` (FR-015, research R11). Uninstall works whatever the switch."""
    made = agent or system_agent()
    try:
        if action == "install":
            if not profile_read:
                raise AgentError("disabled")
            out = made.install(spec)
        else:
            out = made.remove(spec.student)
    except AgentError as err:
        return _fail(err.reason, _AGENT_REFUSALS[err.reason])
    _say(f"classroom agent {out['agent']}")
    _emit(out)
    return EXIT_OK
