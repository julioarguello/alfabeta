"""The invented student of the sandbox (spec 001 T030)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import TYPE_CHECKING

from alfabeta import config, placement, sandbox
from alfabeta.decisions import DecisionStore
from alfabeta.model import DecisionType

if TYPE_CHECKING:
    from pathlib import Path


def cli(*args: str, run: str | None = None, home_env: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "ALFABETA_RUN"}
    if run:
        env["ALFABETA_RUN"] = run
    if home_env:
        env["HOME"] = str(home_env)
    return subprocess.run(
        [sys.executable, "-m", "alfabeta", *args], capture_output=True, text=True, check=False, env=env
    )


def test_prepare_builds_a_student_whose_configuration_is_valid(tmp_path: Path):
    home = tmp_path / "box"
    assert cli("--home", str(home), "sandbox", "prepare").returncode == 0
    assert config.check(home, "sample") == ([], [])
    assert sorted(p.name for p in (home / "sandbox-captures").iterdir()) == sorted(
        p.name for p in sandbox.FIXTURES.glob("*.json")
    )
    assert list((home / "downloads").iterdir()) == []
    subject = home / "drive" / sandbox.SCHOOL_YEAR / "FyQ"
    assert placement.book_topics(subject, "sciencebits") == ["Tema 01 - Materia inventada"]
    again = cli("--home", str(home), "sandbox", "prepare")
    assert again.returncode == 1 and "already exists" in again.stderr


def test_the_sandbox_needs_an_explicit_home_and_never_the_real_one(tmp_path: Path):
    assert cli("sandbox", "prepare", home_env=tmp_path).returncode == 1
    real = cli("--home", str(tmp_path / ".alfabeta"), "sandbox", "prepare", home_env=tmp_path)
    assert real.returncode == 1 and "never uses ~/.alfabeta" in real.stderr
    assert not (tmp_path / ".alfabeta").exists()


def test_download_carries_the_run_in_name_and_field(tmp_path: Path):
    home = tmp_path / "box"
    cli("--home", str(home), "sandbox", "prepare")
    without = cli("--home", str(home), "sandbox", "download", "--student", "sample", "--captures")
    assert without.returncode == 1 and "ALFABETA_RUN" in without.stderr
    done = cli("--home", str(home), "sandbox", "download", "--student", "sample", "--captures", run="r42")
    assert done.returncode == 0, done.stderr
    written = json.loads(done.stdout)["written"]
    assert len(written) == len(list(sandbox.FIXTURES.glob("*.json")))
    for name in written:
        assert name.startswith("alfabeta-capture-r42-")
        assert json.loads((home / "downloads" / name).read_text())["run"] == "r42"
    assert "alfabeta-capture-r42-synth-1-20261027-162200.json" in written


def test_prepare_leaves_attachments_and_decisions(tmp_path: Path):
    home = tmp_path / "box"
    cli("--home", str(home), "sandbox", "prepare")
    names = sorted(p.name for p in (home / "sandbox-attachments").iterdir())
    assert "ficha-inventada.pdf" in names and "Plantilla inventada.pdf" in names
    assert not any(n.startswith("Vídeo") or n.startswith("Página") for n in names)  # never downloaded
    store = DecisionStore.open(home / "sample" / "data")
    assert {d.origin for d in store.decisions() if d.type == DecisionType.CLASS_LINK and d.counts} == {
        "synth-1",
        "synth-2",
    }
    exam = store.in_force(DecisionType.DETECTED_EXAM, "synth-30#exam-1")
    assert exam is not None and exam.decision.counts


def test_download_batch_needs_a_plan(tmp_path: Path):
    home = tmp_path / "box"
    cli("--home", str(home), "sandbox", "prepare")
    done = cli("--home", str(home), "sandbox", "download", "--student", "sample", "--batch", "0", run="r42")
    assert done.returncode == 1 and "no plan" in done.stderr
