"""The Science Bits skill's build names no topic of its own (spec 001 T057, constitution I).

`build.py` stops, naming the key, without `--config` or without one of its keys; it reads them with
the standard library only, so this runs where the PDF and HTML libraries are not installed. The
renderer's `L10N` keeps only interface texts. Every topic text here is invented.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "sciencebits-a-notebooklm" / "scripts"
ES = {"unit": "Tema 4 · Materia inventada", "course": "Asignatura inventada · curso inventado"}
LANGS = {"es": ES, "en": {"unit": "Unit 4 · Invented matter", "course": "Invented subject · invented year"}}
UNIT: dict[str, Any] = {"prefix": "Tema04", "langs": LANGS}


def build(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPTS / "build.py"), *args], capture_output=True, text=True, check=False
    )


def read_config() -> Callable[[list[str]], tuple[str, str, str, dict[str, dict[str, str]]]]:
    spec = importlib.util.spec_from_file_location("sciencebits_build", SCRIPTS / "build.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast("Callable[[list[str]], tuple[str, str, str, dict[str, dict[str, str]]]]", module.read_config)


def unit_file(tmp_path: Path, unit: dict[str, Any]) -> str:
    path = tmp_path / "unit.json"
    path.write_text(json.dumps(unit, ensure_ascii=False))
    return str(path)


def test_without_config_the_build_stops_naming_it(tmp_path: Path):
    done = build(str(tmp_path / "raw"), str(tmp_path / "out"), "es")
    assert done.returncode == 1 and "missing --config" in done.stderr
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    ("unit", "key"),
    [
        ({"langs": LANGS}, "prefix"),
        (UNIT | {"prefix": "Tema1"}, "prefix"),
        ({"prefix": "Tema04"}, "langs.es.unit"),
        (UNIT | {"langs": {"es": {"unit": "Tema 4 · Materia inventada"}}}, "langs.es.course"),
        (UNIT | {"langs": {"es": ES}}, "langs.en.unit"),
        (UNIT | {"langs": {"es": ES, "en": {"unit": " ", "course": "x"}}}, "langs.en.unit"),
    ],
)
def test_a_config_without_a_key_stops_naming_that_key(tmp_path: Path, unit: dict[str, Any], key: str):
    done = build(str(tmp_path / "raw"), str(tmp_path / "out"), "--config", unit_file(tmp_path, unit), "es", "en")
    assert done.returncode == 1 and f"missing {key}" in done.stderr
    assert not (tmp_path / "out").exists()


def test_a_complete_config_gives_each_language_its_own_texts(tmp_path: Path):
    """The control: with every key, nothing is missing and the texts are the configuration's."""
    path = unit_file(tmp_path, UNIT)
    raw, out, prefix, texts = read_config()(["raw", "out", "--config", path, "es", "en"])
    assert (raw, out, prefix) == ("raw", "out", "Tema04")
    assert texts == LANGS


def test_the_renderer_names_no_topic_course_or_grade():
    tree = ast.parse((SCRIPTS / "render.py").read_text())
    tables = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "L10N" for t in node.targets)
    ]
    [l10n] = tables
    assert isinstance(l10n, ast.Dict) and l10n.keys
    for language in l10n.values:
        assert isinstance(language, ast.Call)
        assert not {k.arg for k in language.keywords} & {"unit", "course"}
    [render] = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "build"]
    assert render.args.defaults == []  # no default topic prefix
