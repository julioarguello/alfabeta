"""The container read's commands (spec 006 contracts/cli.md, amendment of 2026-11-17)."""

from __future__ import annotations

import contextlib
import json
import os
import sys
from typing import TYPE_CHECKING, Any

from alfabeta import state
from alfabeta.classroom.password import PasswordError, PasswordStore, Prompt
from alfabeta.google.keychain import KeychainError, TokenStore
from alfabeta.model import RunMode, StopReason

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

EXIT_OK = 0
EXIT_INVALID = 1
# A password command touches no profile and writes for a moment: it holds the lock only while it
# writes, never while the family types (`set` asks first).
_IDLE_MINUTES = 5


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def _say(message: str) -> None:
    print(f"alfabeta: {message}", file=sys.stderr)


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
                _say("contraseña guardada en el llavero")
                _emit({"ok": True, "stored": True})
            else:
                removed = passwords.delete()
                _emit({"ok": True, "removed": removed})
        except KeychainError as err:
            return _fail(str(StopReason.INVALID_CONFIG), str(err))
        return EXIT_OK

    return _locked(lock, body)
