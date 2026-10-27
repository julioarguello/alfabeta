"""The notebook through `nlm`, with its runner replaced: no test shells out (spec 005 T015)."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from typing import Any

import pytest

from alfabeta.notes.sources import NlmSources, Source, SourcesError


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
