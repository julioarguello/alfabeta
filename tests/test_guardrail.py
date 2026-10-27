"""Guardrail (spec 001 T013). Every personal-looking value is built at run time."""

import base64
import subprocess
from pathlib import Path

import pytest

from alfabeta import guardrail


def _at(local: str, domain: str) -> str:
    return local + "@" + domain


MUST_FIRE = {
    "email": "write to " + _at("persona.real", "colegio-real.es"),
    "user-path": "/" + "Users" + "/maria/Library/x",
    "notebook-id": "nb " + "0123abcd-" + "4567-89ab-cdef-" + "0123456789ab",
    "drive-id": "file/d/" + "1" + "QwErTyUiOpAsDfGhJkLzXcVbNm0987654" + "/view",
    "classroom-id": "/c/" + base64.b64encode(("9123" + "45678901").encode()).decode() + "/a/x",
}

MUST_NOT_FIRE = [
    "contact " + _at("someone", "example.org"),
    "contact " + _at("someone", "mail.example.com"),
    "contact " + _at("alumno", "colegio.example"),
    _at("changeme", "group.calendar.google.com"),
    "https://cdn.jsdelivr.net/npm/" + _at("katex", "0.16.11") + "/dist/",
    "/" + "Users" + "/<someone>/Library",
    "/" + "Users" + "/changeme/x",
    "id synth-12 and synth-3",
    "school_year = 2026-2027; languages = es",
    "snake_case_identifier_that_is_quite_long_indeed and camelCaseIdentifierThatIsLongToo",
    "commit 2cd7506 and sha 6dcaafd01141abcd",
    "version 0.1.0, port 59334, year 2026",
]


@pytest.mark.parametrize(("detector", "line"), MUST_FIRE.items())
def test_detector_fires(detector: str, line: str):
    found = guardrail.scan_lines("f.md", [(1, line)], [])
    assert [f.detector for f in found] == [detector]


@pytest.mark.parametrize("line", MUST_NOT_FIRE)
def test_detector_stays_quiet(line: str):
    assert guardrail.scan_lines("f.md", [(1, line)], []) == []


def test_finding_never_shows_the_value():
    [finding] = guardrail.scan_lines("docs/x.md", [(7, MUST_FIRE["email"])], [])
    assert str(finding) == "docs/x.md:7: email"


def test_self_test_passes_and_catches_a_blind_detector(monkeypatch: pytest.MonkeyPatch):
    assert guardrail.self_test() == []
    monkeypatch.setitem(guardrail.GENERIC, "email", lambda line: False)
    assert guardrail.self_test() == ["email"]


def _home_with_config(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    (home / "estudiante").mkdir(parents=True)
    (home / "estudiante" / "config.toml").write_text(
        "[student]\n"
        'display_name = "Iñigo"\nschool_year = "2026-2027"\n'
        "[classroom]\n"
        f'account = "{_at("inigo.x", "cole.example.org")}"\n'
        "[drive]\n"
        'root = "~/Drive/Iñigo"\n'
    )
    return home


def test_named_values_come_from_identifying_keys_only(tmp_path: Path):
    named = guardrail.named_values(_home_with_config(tmp_path))
    assert "Iñigo" in named and "estudiante" in named
    assert "2026-2027" not in named


def test_named_value_fires_even_where_generic_ones_do_not(tmp_path: Path):
    named = guardrail.named_values(_home_with_config(tmp_path))
    found = guardrail.scan_lines("README.md", [(3, "Hola, iñigo, este es tu tema")], named)
    assert [f.detector for f in found] == ["configured-value"]


def _discard(_line: str) -> None:
    return None


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    for args in (["init", "-q"], ["config", "user.email", _at("t", "example.org")], ["config", "user.name", "t"]):
        subprocess.run(["git", *args], cwd=repo, check=True)
    return repo


def _commit(repo: Path, name: str, text: str) -> None:
    (repo / name).write_text(text)
    subprocess.run(["git", "add", name], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "x"], cwd=repo, check=True)


def test_exit_codes_all_staged_history(tmp_path: Path):
    repo, home = _repo(tmp_path), tmp_path / "no-home"
    out: list[str] = []
    assert guardrail.run(repo, home, "all", out.append) == guardrail.EXIT_NOTHING_CHECKED
    assert guardrail.run(repo, home, "staged", out.append) == guardrail.EXIT_CLEAN
    _commit(repo, "a.md", "clean text\n")
    assert guardrail.run(repo, home, "all", out.append) == guardrail.EXIT_CLEAN
    (repo / "b.md").write_text("line\n" + MUST_FIRE["user-path"] + "\n")
    subprocess.run(["git", "add", "b.md"], cwd=repo, check=True)
    out.clear()
    assert guardrail.run(repo, home, "staged", out.append) == guardrail.EXIT_FINDING
    assert out == ["b.md:2: user-path"]
    subprocess.run(["git", "commit", "-q", "-m", "y"], cwd=repo, check=True)
    _commit(repo, "b.md", "line\n")
    assert guardrail.run(repo, home, "all", out.append) == guardrail.EXIT_CLEAN
    assert guardrail.run(repo, home, "history", out.append) == guardrail.EXIT_FINDING


def test_lock_files_and_allow_file_are_skipped(tmp_path: Path):
    repo, home = _repo(tmp_path), tmp_path / "no-home"
    _commit(repo, "uv.lock", MUST_FIRE["drive-id"] + "\n")
    value = _at("inventado", "calendar.google.com")
    _commit(repo, ".guardrail-allow", value + "  # invented\n")
    _commit(repo, "t.py", f'X = "{value}"\n')
    assert guardrail.run(repo, home, "all", _discard) == guardrail.EXIT_CLEAN


def test_blind_detector_exits_3(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setitem(guardrail.GENERIC, "drive-id", lambda line: False)
    assert guardrail.run(_repo(tmp_path), tmp_path, "all", _discard) == guardrail.EXIT_BLIND
