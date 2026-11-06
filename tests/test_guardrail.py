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
# Inside an HTML tag, which once matched the placeholder pattern and hid its content.
IN_A_TAG = '<span class="' + _at("persona.real", "colegio-real.es") + '">x</span>'

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


def test_a_value_inside_an_html_tag_is_scanned():
    assert [f.detector for f in guardrail.scan_lines("f.html", [(1, IN_A_TAG)], [])] == ["email"]
    assert guardrail.scan_lines("f.md", [(1, "write to <school account> or <YYYYMMDD>")], []) == []


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
        "[storage]\n"
        'base = "~/Drive/Iñigo"\n'
        "[drive]\n"
        'root = "alfabeta"\n'
        "[notebook]\n"
        f'owner = "{_at("familia.y", "correo.example.org")}"\n'
    )
    return home


def test_named_values_come_from_identifying_keys_only(tmp_path: Path):
    named = guardrail.named_values(_home_with_config(tmp_path))
    assert "Iñigo" in named and "estudiante" in named
    assert "2026-2027" not in named
    assert "~/Drive/Iñigo" in named
    assert "alfabeta" not in named  # drive.root names a folder inside My Drive, as the repository does
    assert _at("familia.y", "correo.example.org") in named  # notebook.owner (spec 005)


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


# --- standing rules (spec 009 FR-009) ------------------------------------------------------------------


def _home_with_rule(tmp_path: Path, rule: str) -> Path:
    home = tmp_path / "home"
    (home / "estudiante").mkdir(parents=True, exist_ok=True)
    (home / "estudiante" / "config.toml").write_text(
        f"[student]\nrules_both = '''{rule}'''\n[[subjects]]\nfolder = 'Xy'\nrules_problems = ''\nrules_theory = 'changeme'\n"
    )
    return home


def test_a_multi_line_rule_is_caught_line_by_line(tmp_path: Path):
    first, second = "Clasifica los enunciados inventados", "y después separa cada tipo inventado"
    named = guardrail.named_values(_home_with_rule(tmp_path, f"{first}\n{second}"))
    assert first in named and second in named
    found = guardrail.scan_lines("docs/x.md", [(1, f"nota: {second.upper()}")], named)
    assert [f.detector for f in found] == ["configured-value"]


def test_a_short_line_of_several_names_nothing_but_a_short_rule_does(tmp_path: Path):
    named = guardrail.named_values(_home_with_rule(tmp_path, "Corto\n\nOtra línea breve"))
    assert "Corto" not in named and "Otra línea breve" not in named
    short = guardrail.named_values(_home_with_rule(tmp_path, "Regla inventada."))
    found = guardrail.scan_lines("docs/x.md", [(1, "nota: regla inventada.")], short)
    assert [f.detector for f in found] == ["configured-value"]


def test_an_unset_rule_names_nothing(tmp_path: Path):
    named = guardrail.named_values(_home_with_rule(tmp_path, "changeme con bastantes palabras inventadas"))
    assert not any("changeme" in value for value in named)


def test_a_configuration_that_cannot_be_parsed_makes_the_guardrail_blind(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    home = tmp_path / "home"
    (home / "estudiante").mkdir(parents=True)
    (home / "estudiante" / "config.toml").write_text('[student]\nrules_both = "con "comillas" inventadas"\n')
    assert guardrail.run(_repo(tmp_path), home, "all", _discard) == guardrail.EXIT_BLIND
    err = capsys.readouterr().err
    assert "config check" in err and "estudiante" not in err and "comillas" not in err
