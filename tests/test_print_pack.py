"""The study pack's printer takes its `nlm` profile from the student's configuration."""

from __future__ import annotations

import importlib.util
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
    with pytest.raises(SystemExit, match=r"nlm config set auth\.default_profile familia"):
        script.require_default("familia")
