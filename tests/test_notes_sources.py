"""The notebook through `nlm`, with its runner replaced: no test shells out (spec 005 T015)."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pytest

from alfabeta.notes.sources import SIGNED_OUT_CHECK, NlmMissingError, NlmSources, Source, SourcesError, run_bounded

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class FakeNlm:
    """Answers `nlm` commands in order and records them."""

    answers: list[tuple[int, Any]]
    calls: list[list[str]] = field(default_factory=lambda: [])

    def __call__(self, argv: list[str], stdin: str | None) -> subprocess.CompletedProcess[str]:
        self.calls.append(argv)
        code, out = self.answers.pop(0)
        return subprocess.CompletedProcess(argv, code, json.dumps(out), "")


def test_the_notebook_is_found_by_exact_title_with_the_profile():
    nlm = FakeNlm([(0, [{"id": "nb-1", "title": "3º ESO. FyQ. Tema 01 - Materia"}, {"id": "nb-2", "title": "Otro"}])])
    assert NlmSources("prueba", nlm).find_notebook("3º ESO. FyQ. Tema 01 - Materia") == "nb-1"
    assert nlm.calls[0] == ["nlm", "notebook", "list", "--json", "--profile", "prueba"]


def test_no_notebook_and_two_notebooks():
    assert NlmSources("p", FakeNlm([(0, [])])).find_notebook("X") is None
    two = FakeNlm([(0, [{"id": "a", "title": "X"}, {"id": "b", "title": "X"}])])
    with pytest.raises(SourcesError):
        NlmSources("p", two).find_notebook("X")


def test_a_drive_pdf_is_added_and_waited_for():
    nlm = FakeNlm([(0, {"source_type": "drive", "source_id": "src-1", "title": "Apuntes · Tema"})])
    assert NlmSources("p", nlm).add_drive_source("nb-1", "file-1", "Apuntes · Tema") == "src-1"
    argv = nlm.calls[0]
    assert argv[:4] == ["nlm", "source", "add", "nb-1"]
    assert argv[argv.index("--drive") + 1] == "file-1" and argv[argv.index("--type") + 1] == "pdf" and "--wait" in argv


def test_sources_are_listed():
    nlm = FakeNlm([(0, [{"id": "s1", "title": "Apuntes · Tema 01"}, {"id": "s2", "title": "libro.pdf"}])])
    assert NlmSources("p", nlm).list_sources("nb-1") == [Source("s1", "Apuntes · Tema 01"), Source("s2", "libro.pdf")]


def test_signed_out_is_told_apart_from_any_other_failure():
    signed_out = FakeNlm(
        [(1, {"status": "error", "error": "Authentication failed", "hint": "Run 'nlm login' to authenticate."})]
    )
    with pytest.raises(SourcesError) as err:
        NlmSources("p", signed_out).list_sources("nb-1")
    assert err.value.signed_out
    other = FakeNlm([(1, {"status": "error", "error": "Notebook not found"})])
    with pytest.raises(SourcesError) as err:
        NlmSources("p", other).list_sources("nb-1")
    assert not err.value.signed_out


# --- the owner's refresh (spec 005 T043, research R14) ---


@dataclass
class CodedNlm:
    """Answers `nlm` with exit codes and texts, records argv and stdin; raises like a missing binary."""

    answers: list[tuple[int, str, str]]
    calls: list[tuple[list[str], str | None]] = field(default_factory=lambda: [])
    missing: bool = False

    def __call__(self, argv: list[str], stdin: str | None) -> subprocess.CompletedProcess[str]:
        self.calls.append((argv, stdin))
        if self.missing:
            raise FileNotFoundError(argv[0])
        code, out, err = self.answers.pop(0)
        return subprocess.CompletedProcess(argv, code, out, err)


def test_a_source_is_read_as_the_owner_and_its_content_is_discarded():
    nlm = CodedNlm([(0, json.dumps({"content": "texto inventado de la página"}), "")])
    assert NlmSources("prueba", nlm).read_source("src-1") is None
    argv, stdin = nlm.calls[0]
    assert argv[:4] == ["nlm", "source", "content", "src-1"]
    assert argv[argv.index("--profile") + 1] == "prueba"
    assert stdin == ""  # a prompt would read an empty, closed input: never waits for anyone


def test_a_read_that_fails_signed_out_says_so():
    hint = json.dumps({"status": "error", "error": "Authentication failed", "hint": "Run 'nlm login' to authenticate."})
    with pytest.raises(SourcesError) as err:
        NlmSources("p", CodedNlm([(1, hint, "")])).read_source("src-1")
    assert err.value.signed_out


@pytest.mark.parametrize(("code", "stderr", "ok"), [(0, "", True), (2, "", False)])
def test_the_session_check_is_login_check(code: int, stderr: str, ok: bool):
    nlm = CodedNlm([(code, "", stderr)])
    assert NlmSources("prueba", nlm).session_ok() is ok
    assert nlm.calls[0] == (["nlm", "login", "--check", "--profile", "prueba"], "")


@pytest.mark.parametrize(("code", "stderr"), [(2, "Usage: nlm login [OPTIONS]"), (1, "network unreachable")])
def test_a_check_that_answers_nothing_about_the_session_is_a_failure_not_signed_out(code: int, stderr: str):
    with pytest.raises(SourcesError) as err:
        NlmSources("p", CodedNlm([(code, "", stderr)])).session_ok()
    assert not err.value.signed_out


def test_the_unattended_renewal_is_http_only_and_the_browser_one_is_asked_for():
    nlm = CodedNlm([(0, "HTTP-only session refresh validated", ""), (1, "", "failed")])
    sources = NlmSources("prueba", nlm)
    assert sources.renew_session(browser=False) is True
    assert sources.renew_session(browser=True) is False
    (quiet, _), (browser, _) = nlm.calls
    assert quiet == ["nlm", "auth", "refresh", "--http-only", "--profile", "prueba"]
    assert browser == ["nlm", "auth", "refresh", "--profile", "prueba"]
    assert all(stdin == "" for _, stdin in nlm.calls)


# Every call the refresh makes, and one setup makes, with their arguments.
CALLS: list[tuple[str, tuple[object, ...]]] = [
    ("session_ok", ()),
    ("renew_session", (False,)),
    ("read_source", ("src-1",)),
    ("list_sources", ("nb-1",)),
]


@pytest.mark.parametrize(("name", "args"), CALLS)
def test_nlm_that_cannot_be_run_is_its_own_error_never_signed_out(name: str, args: tuple[object, ...]):
    method: Callable[..., object] = getattr(NlmSources("p", CodedNlm([], missing=True)), name)
    with pytest.raises(NlmMissingError) as err:
        method(*args)
    assert not err.value.signed_out


def test_a_bounded_run_turns_a_hang_into_a_failure(monkeypatch: pytest.MonkeyPatch):
    def hang(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired("nlm", 1)

    monkeypatch.setattr(subprocess, "run", hang)
    done = run_bounded(["nlm", "login", "--check"], "")
    assert done.returncode != 0 and done.returncode != SIGNED_OUT_CHECK
