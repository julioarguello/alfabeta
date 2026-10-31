"""The study pack's printer takes its `nlm` profile from the student's configuration."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from alfabeta import sandbox

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "study-pack" / "scripts"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("print_pack", SCRIPTS / "print_pack.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def home(tmp_path: Path) -> Path:
    sandbox.prepare(tmp_path, "sample")
    return tmp_path


def test_the_profile_is_the_students_notebook_profile(home: Path):
    args = load_script().parse(["topic", "nb-1", "out.pdf", "--student", "sample", "--home", str(home)])
    assert args.profile == "prueba"


def test_a_named_profile_needs_no_configuration(tmp_path: Path):
    args = load_script().parse(["report", "nb-1", "art-1", "out.pdf", "--profile", "otro", "--home", str(tmp_path)])
    assert args.profile == "otro"


def test_an_invalid_configuration_stops_and_names_the_key(home: Path):
    path = home / "sample" / "config.toml"
    path.write_text(path.read_text().replace('nlm_profile = "prueba"\n', ""))
    with pytest.raises(SystemExit, match=r"notebook\.nlm_profile \(missing\)"):
        load_script().parse(["topic", "nb-1", "out.pdf", "--student", "sample", "--home", str(home)])


@pytest.mark.parametrize("who", [[], ["--student", "sample", "--profile", "otro"]])
def test_exactly_one_of_student_and_profile(home: Path, who: list[str]):
    done = subprocess.run(
        [sys.executable, str(SCRIPTS / "print_pack.py"), "topic", "nb-1", "out.pdf", "--home", str(home), *who],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 2 and "--student" in done.stderr


class FakeRun:
    """Records each `nlm` call and answers `config get` with a default profile."""

    def __init__(self, default: str) -> None:
        self.default = default
        self.calls: list[list[str]] = []

    def __call__(self, cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        self.calls.append(cmd)
        out = f"{self.default}\n" if cmd[1:3] == ["config", "get"] else "{}"
        return subprocess.CompletedProcess(cmd, 0, out, "")


def test_every_nlm_command_but_download_and_config_gets_the_profile(monkeypatch: pytest.MonkeyPatch):
    script = load_script()
    fake = FakeRun("familia")
    monkeypatch.setattr(script.subprocess, "run", fake)
    script.nlm("familia", "studio", "status", "nb-1", "--full", "--json")
    script.nlm("familia", "download", "report", "nb-1", "--id", "art-1", "-o", "x.md")
    script.require_default("familia")
    assert fake.calls == [
        ["nlm", "studio", "status", "nb-1", "--full", "--json", "--profile", "familia"],
        ["nlm", "download", "report", "nb-1", "--id", "art-1", "-o", "x.md"],
        ["nlm", "config", "get", "auth.default_profile"],
    ]


def test_a_default_profile_other_than_the_students_stops_before_any_download(monkeypatch: pytest.MonkeyPatch):
    script = load_script()
    monkeypatch.setattr(script.subprocess, "run", FakeRun("default"))
    with pytest.raises(SystemExit, match=r"nlm config set auth\.default_profile <profile>") as stop:
        script.require_default("familia")
    assert "familia" not in str(stop.value)  # the key, never the value


def test_the_run_checks_the_default_before_it_downloads(home: Path, monkeypatch: pytest.MonkeyPatch):
    script = load_script()
    fake = FakeRun("default")
    monkeypatch.setattr(script.subprocess, "run", fake)
    monkeypatch.setattr(
        sys, "argv", ["print_pack.py", "topic", "nb-1", "out.pdf", "--student", "sample", "--home", str(home)]
    )
    with pytest.raises(SystemExit):
        script.main()
    assert [call[1] for call in fake.calls] == ["config"]


def test_a_pdf_for_a_folder_the_topic_lacks_makes_the_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    script = load_script()
    fake = FakeRun("familia")
    monkeypatch.setattr(script.subprocess, "run", fake)
    out = tmp_path / "20261001 - Tema 01 - Inventado" / "notebook" / "Guía · T01.pdf"
    work = tmp_path / "work"
    work.mkdir()
    script.render("# Guía\n", out, work)
    assert out.parent.is_dir()
    assert f"--print-to-pdf={out}" in fake.calls[-1]


PROBLEMS = """# FyQ · Examen del jueves 5 de noviembre — Problemas tipo

## 4. El más difícil de cada patrón

Enunciado.

## 5. Soluciones

Solución.

## Soluciones impresas que no cuadran

| Problema | Impreso | Calculado | Qué pasa |
"""


def test_the_page_breaks_before_the_solutions_heading_and_not_before_the_table():
    out = load_script().break_before(PROBLEMS, "Soluciones")
    before, _, after = out.partition('<div class="newpage"></div>\n\n')
    assert before.endswith("Enunciado.\n\n") and after.startswith("## 5. Soluciones\n")
    assert out.count("newpage") == 1


def test_a_sheet_without_that_heading_prints_unchanged_and_says_so(capsys: pytest.CaptureFixture[str]):
    md = "# Hoja\n\nSin soluciones aparte.\n"
    assert load_script().break_before(md, "Soluciones") == md
    assert "no heading «Soluciones»" in capsys.readouterr().err


def test_the_report_takes_a_heading_to_break_before(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    script = load_script()
    args = script.parse(["report", "nb-1", "art-1", "out.pdf", "--profile", "p", "--break-before", "Soluciones"])
    assert args.break_before == "Soluciones"
    report = tmp_path / "r.md"
    report.write_text(PROBLEMS)
    rendered: list[str] = []

    def download(*_: object) -> Path:
        return report

    def render(md: str, out: Path, work: Path) -> None:
        rendered.append(md)

    monkeypatch.setattr(script, "download", download)
    monkeypatch.setattr(script, "render", render)
    script.report(args, tmp_path)
    assert '<div class="newpage"></div>\n\n## 5. Soluciones' in rendered[0]
    assert script.parse(["report", "nb-1", "art-1", "out.pdf", "--profile", "p"]).break_before is None


@pytest.mark.parametrize("heading", ["## Soluciones", "### 5) Soluciones:", "## **5. Soluciones**", "## «Soluciones»"])
def test_the_solutions_heading_is_found_however_it_is_written(heading: str):
    md = f"# Hoja\n\nEnunciado.\n\n{heading}\n\nSolución.\n"
    assert f'<div class="newpage"></div>\n\n{heading}\n' in load_script().break_before(md, "Soluciones")


class Notebook(FakeRun):
    """Answers `notebook get` with a notebook, and every other command as FakeRun does."""

    def __init__(self, default: str, got: dict[str, str]) -> None:
        super().__init__(default)
        self.got = got

    def __call__(self, cmd: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
        if cmd[1:3] == ["notebook", "get"]:
            self.calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, json.dumps(self.got), "")
        if cmd[1:3] == ["studio", "status"] or cmd[1:3] == ["note", "list"]:
            self.calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, "[]" if cmd[1] == "studio" else '{"notes": []}', "")
        return super().__call__(cmd, **kw)


NB = {"title": "3º ESO. Inventada. Tema 01 - Prueba", "url": "https://notebook.google.com/notebook/nb-1"}


def capture(script: ModuleType, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Each rendered page's markdown; its path goes to `rendered_to`."""
    rendered: list[str] = []
    rendered_to.clear()

    def render(md: str, out: Path, work: Path) -> None:
        rendered.append(md)
        rendered_to.append(out)

    monkeypatch.setattr(script, "render", render)
    return rendered


rendered_to: list[Path] = []


def test_the_link_page_carries_the_notebooks_title_and_the_link_nlm_returns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    script = load_script()
    monkeypatch.setattr(script.subprocess, "run", Notebook("familia", NB))
    rendered = capture(script, monkeypatch)
    out = tmp_path / "notebook" / "Abrir el cuaderno.pdf"
    script.link(script.parse(["link", "nb-1", str(out), "--profile", "familia"]), tmp_path)
    assert rendered_to == [out]
    assert rendered[0].startswith(f"# {NB['title']}\n")
    assert f"]({NB['url']})" in rendered[0] and f"\n{NB['url']}\n" in rendered[0]


def test_the_link_page_needs_no_default_profile(home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    script = load_script()
    fake = Notebook("default", NB)
    monkeypatch.setattr(script.subprocess, "run", fake)
    capture(script, monkeypatch)
    out = tmp_path / "Abrir el cuaderno.pdf"
    monkeypatch.setattr(
        sys, "argv", ["print_pack.py", "link", "nb-1", str(out), "--student", "sample", "--home", str(home)]
    )
    script.main()
    assert [call[1:3] for call in fake.calls] == [["notebook", "get"]]


def test_a_notebook_without_a_link_stops_and_nothing_is_printed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    script = load_script()
    monkeypatch.setattr(script.subprocess, "run", Notebook("familia", {"title": NB["title"]}))
    rendered = capture(script, monkeypatch)
    with pytest.raises(SystemExit, match="no url"):
        script.link(script.parse(["link", "nb-1", str(tmp_path / "out.pdf"), "--profile", "familia"]), tmp_path)
    assert rendered == []


def test_the_printed_topic_carries_the_link_under_its_title(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    script = load_script()
    monkeypatch.setattr(script.subprocess, "run", Notebook("familia", NB))
    rendered = capture(script, monkeypatch)
    script.topic(script.parse(["topic", "nb-1", "out.pdf", "--profile", "familia"]), tmp_path)
    head = rendered[0].split("| | Pieza |")[0]
    assert head == f"# {NB['title']}\n\nTu cuaderno: [{NB['url']}]({NB['url']})\n\n"


@pytest.mark.parametrize(("held", "written"), [(None, True), (NB["url"], False), (NB["url"] + "-otro", True)])
def test_the_link_page_is_written_only_when_absent_or_carrying_another_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, held: str | None, written: bool
):
    script = load_script()
    monkeypatch.setattr(script.subprocess, "run", Notebook("familia", NB))
    rendered = capture(script, monkeypatch)
    out = tmp_path / "Abrir el cuaderno.pdf"
    if held is not None:
        out.write_bytes(f"%PDF-1.4 << /URI ({held}) >>".encode())
    script.link(script.parse(["link", "nb-1", str(out), "--profile", "familia"]), tmp_path)
    assert bool(rendered) is written


def test_a_relative_link_path_stops_before_asking_nlm(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    script = load_script()
    fake = Notebook("familia", NB)
    monkeypatch.setattr(script.subprocess, "run", fake)
    rendered = capture(script, monkeypatch)
    with pytest.raises(SystemExit, match="absolute path"):
        script.link(script.parse(["link", "nb-1", "2026-2027/Bio/notebook/x.pdf", "--profile", "familia"]), tmp_path)
    assert rendered == [] and fake.calls == []
