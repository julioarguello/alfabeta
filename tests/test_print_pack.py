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
