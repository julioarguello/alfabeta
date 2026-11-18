"""`classroom password set|delete` (spec 006 FR-031, T002): the keychain, the mark, the lock."""

from __future__ import annotations

import datetime as dt
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from alfabeta import state
from alfabeta.__main__ import main as alfabeta_main
from alfabeta.classroom import cli
from alfabeta.classroom.password import MARK, SERVICE, PasswordStore, Prompt
from alfabeta.google.keychain import SERVICE as GOOGLE_SERVICE
from alfabeta.google.keychain import KeychainStore
from alfabeta.model import RunMode

STUDENT = "s9"
INVENTED = "contraseña-inventada-123"


class FakeStore:
    """A TokenStore in memory, one per keychain service."""

    def __init__(self) -> None:
        self.secrets: dict[str, str] = {}

    def get(self, account: str) -> str | None:
        return self.secrets.get(account)

    def set(self, account: str, secret: str) -> None:
        self.secrets[account] = secret

    def delete(self, account: str) -> None:
        self.secrets.pop(account, None)


def _prompt(answer: str) -> tuple[Prompt, list[str]]:
    asked: list[str] = []

    def ask(prompt: str) -> str:
        asked.append(prompt)
        return answer

    return ask, asked


def _run(tmp_path: Path, action: str, store: FakeStore, answer: str = INVENTED, tty: bool = True) -> tuple[int, Path]:
    home = tmp_path / "home"
    data = home / STUDENT / "data"
    data.mkdir(parents=True, exist_ok=True)
    prompt, _ = _prompt(answer)
    code = cli.cmd_password(action, STUDENT, data, state.Lock(home, data), store, prompt, tty)
    return code, data


def test_set_stores_under_the_student_and_clears_the_mark(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    store = FakeStore()
    home = tmp_path / "home"
    data = home / STUDENT / "data"
    PasswordStore(store, data, STUDENT).mark(dt.date(2026, 11, 17))
    assert (data / MARK).read_text() == "2026-11-17\n"
    code, _ = _run(tmp_path, "set", store)
    out = capsys.readouterr()
    assert code == 0 and json.loads(out.out) == {"ok": True, "stored": True}
    assert store.secrets == {STUDENT: INVENTED}
    assert not (data / MARK).exists()
    assert INVENTED not in out.out + out.err


def test_delete_removes_the_password_and_the_mark(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    store = FakeStore()
    store.set(STUDENT, INVENTED)
    data = tmp_path / "home" / STUDENT / "data"
    PasswordStore(store, data, STUDENT).mark(dt.date(2026, 11, 17))
    code, _ = _run(tmp_path, "delete", store)
    assert code == 0 and json.loads(capsys.readouterr().out) == {"ok": True, "removed": True}
    assert store.secrets == {} and not (data / MARK).exists()


def test_an_empty_answer_stores_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    store = FakeStore()
    code, _ = _run(tmp_path, "set", store, answer="")
    assert code == 1 and json.loads(capsys.readouterr().out) == {"ok": False, "reason": "invalid_config"}
    assert store.secrets == {}


def test_without_a_terminal_nothing_is_asked_or_stored(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    store = FakeStore()
    home = tmp_path / "home"
    data = home / STUDENT / "data"
    data.mkdir(parents=True)
    prompt, asked = _prompt(INVENTED)
    code = cli.cmd_password("set", STUDENT, data, state.Lock(home, data), store, prompt, False)
    assert code == 1 and asked == [] and store.secrets == {}
    assert json.loads(capsys.readouterr().out)["reason"] == "invalid_config"


def test_a_held_lock_stops_with_lock_busy(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    home = tmp_path / "home"
    data = home / STUDENT / "data"
    lock = state.Lock(home, data)
    run = lock.take(RunMode.INTERACTIVE, 5)
    try:
        store = FakeStore()
        prompt, asked = _prompt(INVENTED)
        code = cli.cmd_password("set", STUDENT, data, lock, store, prompt, True)
        assert code == 1 and json.loads(capsys.readouterr().out)["reason"] == "lock_busy"
        # Asked first (no lock while typing), then refused at the lock: nothing stored.
        assert len(asked) == 1 and store.secrets == {}
    finally:
        lock.release(run)


def test_the_password_has_its_own_keychain_service() -> None:
    class Recorder:
        def __init__(self) -> None:
            self.calls: list[tuple[list[str], str | None]] = []

        def __call__(self, argv: list[str], stdin: str | None) -> subprocess.CompletedProcess[str]:
            self.calls.append((argv, stdin))
            return subprocess.CompletedProcess(argv, 0, "", "")

    rec = Recorder()
    KeychainStore(rec, service=SERVICE).set(STUDENT, INVENTED)
    argv, stdin = rec.calls[0]
    assert SERVICE != GOOGLE_SERVICE
    assert stdin is not None and f"-s {SERVICE} -a {STUDENT}" in stdin
    assert all(INVENTED not in a for a in argv)


def test_the_commands_take_no_password_option_and_ignore_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"
    (home / STUDENT).mkdir(parents=True)
    monkeypatch.setenv("ALFABETA_PASSWORD", INVENTED)
    monkeypatch.setattr(sys, "stdin", io.StringIO(INVENTED + "\n"))  # not a terminal
    base = ["--home", str(home), "classroom", "password", "set", "--student", STUDENT]
    for extra in (["--password", INVENTED], [INVENTED]):
        with pytest.raises(SystemExit) as stop:
            alfabeta_main(base + extra)
        assert stop.value.code == 2  # argparse refuses it: no option or argument carries the password
    capsys.readouterr()
    code = alfabeta_main(base)
    out = capsys.readouterr()
    # No terminal: refused before asking; neither stdin nor the environment's planted value is used.
    assert code == 1 and json.loads(out.out)["reason"] == "invalid_config"
    assert INVENTED not in out.out + out.err


def test_the_service_literal_is_its_own() -> None:
    assert SERVICE == "alfabeta.classroom" and GOOGLE_SERVICE == "alfabeta.google"


def test_main_stores_in_the_classroom_service(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import alfabeta.__main__ as entry

    services: list[str] = []

    class Recording(FakeStore):
        def __init__(self, service: str = GOOGLE_SERVICE) -> None:
            super().__init__()
            services.append(service)

    monkeypatch.setattr(entry, "KeychainStore", Recording)
    home = tmp_path / "home"
    (home / STUDENT).mkdir(parents=True)
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    entry.main(["--home", str(home), "classroom", "password", "delete", "--student", STUDENT])
    assert json.loads(capsys.readouterr().out.splitlines()[-1]) == {"ok": True, "removed": False}
    assert SERVICE in services


def test_the_stored_value_is_the_prompts_never_the_environments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("ALFABETA_PASSWORD", "plantada-en-el-entorno")
    store = FakeStore()
    code, _ = _run(tmp_path, "set", store, answer=INVENTED, tty=True)
    assert code == 0 and store.secrets == {STUDENT: INVENTED}
    capsys.readouterr()


def test_the_lock_is_released_after_each_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    home = tmp_path / "home"
    data = home / STUDENT / "data"
    for action in ("set", "delete"):
        _run(tmp_path, action, FakeStore())
        assert not state.Lock(home, data).held()
    capsys.readouterr()


def test_inside_the_run_that_holds_the_lock_it_goes_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"
    data = home / STUDENT / "data"
    lock = state.Lock(home, data)
    run = lock.take(RunMode.INTERACTIVE, 5)
    try:
        monkeypatch.setenv(state.RUN_ENV, run)
        store = FakeStore()
        prompt, _ = _prompt(INVENTED)
        code = cli.cmd_password("set", STUDENT, data, lock, store, prompt, True)
        assert code == 0 and store.secrets == {STUDENT: INVENTED}
        assert lock.held()  # still the run's: the command neither took nor released it
    finally:
        lock.release(run)
    capsys.readouterr()


def test_the_lock_is_not_held_while_the_family_types(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    home = tmp_path / "home"
    data = home / STUDENT / "data"
    data.mkdir(parents=True)
    lock = state.Lock(home, data)
    seen: list[bool] = []

    def ask(prompt: str) -> str:
        seen.append(lock.held())
        return INVENTED

    assert cli.cmd_password("set", STUDENT, data, lock, FakeStore(), ask, True) == 0
    assert seen == [False]
    capsys.readouterr()


@pytest.mark.parametrize("raised", [EOFError, KeyboardInterrupt])
def test_a_cancelled_prompt_is_invalid_config(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], raised: type[BaseException]
) -> None:
    home = tmp_path / "home"
    data = home / STUDENT / "data"
    data.mkdir(parents=True)

    def ask(prompt: str) -> str:
        raise raised

    store = FakeStore()
    code = cli.cmd_password("set", STUDENT, data, state.Lock(home, data), store, ask, True)
    assert code == 1 and json.loads(capsys.readouterr().out)["reason"] == "invalid_config" and store.secrets == {}
