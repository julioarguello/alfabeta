"""The Science Bits skill's build names no topic of its own (spec 001 T057, constitution I).

`build.py` stops, naming the key, without `--config` or without one of its keys; it reads them with
the standard library only, so this runs where the PDF and HTML libraries are not installed. The
renderer's `L10N` keeps only interface texts. The build also runs for real here, with the fonts and
libraries the repository declares, as on the family's Mac. Every topic text here is invented.
"""

from __future__ import annotations

import ast
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest
from PIL import Image
from pypdf import PdfReader

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


STUB_RENDER = """
import json, pathlib
L10N = {"en": {"toc": "Contents"}, "es": {"toc": "Índice"}}
def build(raw, out, lang, prefix):
    pathlib.Path(out).mkdir(exist_ok=True)
    (pathlib.Path(out) / f"{prefix}_{lang.upper()}.json").write_text(json.dumps([raw, L10N[lang]]))
"""


def test_the_build_hands_each_language_its_texts_and_the_prefix(tmp_path: Path):
    """The glue to render.py, with a stand-in renderer that can say what it was handed."""
    scripts = tmp_path / "tools"
    scripts.mkdir()
    shutil.copyfile(SCRIPTS / "build.py", scripts / "build.py")
    (scripts / "render.py").write_text(STUB_RENDER)
    argv = ["raw", str(tmp_path / "out"), "--config", unit_file(tmp_path, UNIT), "es", "en"]
    done = subprocess.run(
        [sys.executable, str(scripts / "build.py"), *argv],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert done.returncode == 0, done.stderr
    for lang in ("es", "en"):
        raw, texts = json.loads((tmp_path / "out" / f"Tema04_{lang.upper()}.json").read_text())
        assert raw == "raw" and texts == {"toc": {"es": "Índice", "en": "Contents"}[lang]} | LANGS[lang]


def test_a_language_the_renderer_has_no_texts_for_is_refused(tmp_path: Path):
    """Not drawn with another language's labels: the provider's languages are render.py's L10N."""
    scripts = tmp_path / "tools"
    scripts.mkdir()
    shutil.copyfile(SCRIPTS / "build.py", scripts / "build.py")
    (scripts / "render.py").write_text(STUB_RENDER)
    unit = UNIT | {"langs": LANGS | {"fr": {"unit": "Unité 4 · inventée", "course": "Matière inventée"}}}
    argv = ["raw", str(tmp_path / "out"), "--config", unit_file(tmp_path, unit), "es", "fr"]
    done = subprocess.run(
        [sys.executable, str(scripts / "build.py"), *argv], capture_output=True, text=True, check=False, cwd=tmp_path
    )
    assert done.returncode == 1 and "no interface texts for fr" in done.stderr
    assert not (tmp_path / "out").exists()


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


def capture_zip(raw: Path, tag: str, items: list[dict[str, str]] | None = None) -> Path:
    """A capture as the orchestrator downloads it, with one invented screen and a real image."""
    image = io.BytesIO()
    Image.new("RGB", (64, 40), "white").save(image, "JPEG")
    screen = {
        "file": "001.jpg",
        "page": "p1",
        "label": "base",
        "text": "Agua H2O",
        "html": "<p>Agua H<sub>2</sub>O y CO<sub>2</sub>, <b>en negrita</b> e <i>inclinada</i>.</p>",
    }
    meta = {
        "tag": tag,
        "title": "Lección inventada",
        "menu": ["Empezamos Inicio 1"],
        "items": [screen] if items is None else items,
    }
    raw.mkdir(exist_ok=True)
    path = raw / f"sb_{tag}.zip"
    with zipfile.ZipFile(path, "w") as capture:
        capture.writestr("001.jpg", image.getvalue())
        capture.writestr("meta.json", json.dumps(meta))
    return path


def test_the_real_build_draws_a_navigable_pdf_with_its_own_fonts(tmp_path: Path):
    """What ran on the Mac only from a patched copy: the repository's own render.py, bs4 and DejaVu."""
    capture_zip(tmp_path / "raw", "es_L1")
    unit = UNIT | {"langs": {"es": ES}}
    argv = [str(tmp_path / "raw"), str(tmp_path / "out"), "--config", unit_file(tmp_path, unit), "es"]
    done = subprocess.run(
        [sys.executable, str(SCRIPTS / "build.py"), *argv], capture_output=True, text=True, check=False, cwd=tmp_path
    )
    assert done.returncode == 0, done.stderr
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["Tema04_ES.md", "Tema04_ES.pdf"]
    assert "H₂O" in (tmp_path / "out" / "Tema04_ES.md").read_text()
    pdf = PdfReader(tmp_path / "out" / "Tema04_ES.pdf")
    assert pdf.outline
    text = " ".join(page.extract_text() for page in pdf.pages)
    assert "Materia inventada" in text and "H₂O" in text
    fonts = {
        str(font.get_object()["/BaseFont"])
        for page in pdf.pages
        for font in cast("Any", page["/Resources"]["/Font"]).values()  # pyright: ignore[reportIndexIssue]
    }
    assert any("DejaVu" in name for name in fonts) and any("Bold" in name for name in fonts)


def watch_module() -> Any:
    spec = importlib.util.spec_from_file_location("sciencebits_watch", SCRIPTS / "watch.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


NOW = 1_800_000_000.0


def downloaded(path: Path, at: float) -> Path:
    os.utime(path, (at, at))
    return path


def test_the_collector_leaves_what_an_earlier_capture_downloaded(tmp_path: Path):
    """Measured 2026-11-05: an old zip landed in the new topic. Its tag says nothing: only its age does."""
    downloads, raw = tmp_path / "downloads", tmp_path / "raw"
    downloaded(capture_zip(downloads, "es_L1"), NOW - 3600)
    raw.mkdir()
    assert watch_module().collect(str(raw), str(downloads), NOW, {}) == []
    assert list(raw.iterdir()) == []


def test_the_collector_files_a_new_capture_by_its_own_tag_whatever_chrome_named_it(tmp_path: Path):
    downloads, raw = tmp_path / "downloads", tmp_path / "raw"
    fresh = capture_zip(downloads, "es_L1")
    renamed = downloaded(fresh.rename(downloads / "sb_es_L1 (1).zip"), NOW + 1)
    raw.mkdir()
    collect = watch_module().collect
    seen: dict[str, int] = {}
    assert collect(str(raw), str(downloads), NOW, seen) == [("es_L1", 1)]
    assert (raw / "sb_es_L1.zip").read_bytes() == renamed.read_bytes()
    assert collect(str(raw), str(downloads), NOW, seen) == []  # once


def test_the_collector_survives_a_zip_of_ours_by_name_only(tmp_path: Path):
    downloads, raw = tmp_path / "downloads", tmp_path / "raw"
    raw.mkdir()
    downloads.mkdir()
    with zipfile.ZipFile(downloads / "sb_other.zip", "w") as other:
        other.writestr("meta.json", "[1, 2]")
    downloaded(downloads / "sb_other.zip", NOW + 1)
    assert watch_module().collect(str(raw), str(downloads), NOW, {}) == []


def test_the_collector_waits_for_a_zip_still_being_written_and_skips_an_empty_capture(tmp_path: Path):
    downloads, raw = tmp_path / "downloads", tmp_path / "raw"
    raw.mkdir()
    downloads.mkdir()
    downloaded(capture_zip(downloads, "es_L2", items=[]), NOW + 1)
    cut = downloads / "sb_es_L3.zip"
    downloaded(capture_zip(downloads, "es_L3"), NOW + 1)
    whole = cut.read_bytes()
    downloaded(cut, NOW + 1).write_bytes(whole[:20])
    os.utime(cut, (NOW + 1, NOW + 1))
    collect = watch_module().collect
    seen: dict[str, int] = {}
    assert collect(str(raw), str(downloads), NOW, seen) == []
    assert list(raw.iterdir()) == []
    downloaded(cut, NOW + 2).write_bytes(whole)
    os.utime(cut, (NOW + 2, NOW + 2))
    assert collect(str(raw), str(downloads), NOW, seen) == [("es_L3", 1)]


def test_the_fonts_travel_with_the_renderer():
    assert "/usr/share/fonts" not in (SCRIPTS / "render.py").read_text()
    assert {p.name for p in (SCRIPTS / "fonts").iterdir()} >= {
        "DejaVuSans.ttf",
        "DejaVuSans-Bold.ttf",
        "DejaVuSans-Oblique.ttf",
        "DejaVuSans-BoldOblique.ttf",
        "LICENSE",
    }


def test_the_skill_names_only_what_the_mac_has_and_only_scripts_that_exist():
    """Measured 2026-11-05: none of these tools is available in a run on the family's Mac."""
    skill = (SCRIPTS.parent / "SKILL.md").read_text()
    for gone in ("device_bash", "Desktop Commander", "start_process", "preview_start", "request_access", "sleep 170"):
        assert gone not in skill
    assert "NOT_AVAILABLE" not in skill and "NOT_AVAILABLE" not in (SCRIPTS / "orchestrator.js").read_text()
    for script in re.findall(r"`?\$H/(\w+\.py)", skill) + re.findall(r"`(\w+\.(?:py|js))`", skill):
        assert (SCRIPTS / script).is_file() or script == "print_pack.py", script
