"""US1 end to end with the student `sample` (spec 001 T035): collect, plan, download, collect, apply."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from alfabeta import sandbox

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

FYQ = "2026-2027/FyQ"
TOPIC = f"{FYQ}/20261001 - 1. Materia inventada/classroom"
BOOK = f"{FYQ}/20260915 - Tema 01 - Materia inventada/classroom"


def cli(home: Path, *args: str, run: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "ALFABETA_RUN"}
    if run:
        env["ALFABETA_RUN"] = run
    return subprocess.run(
        [sys.executable, "-m", "alfabeta", "--home", str(home), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


class Box:
    def __init__(self, home: Path) -> None:
        self.home = home
        self.run = ""

    def __call__(self, *args: str) -> subprocess.CompletedProcess[str]:
        return cli(self.home, *args, run=self.run)

    def take(self) -> None:
        self.run = json.loads(cli(self.home, "lock", "take", "--student", "sample", "--mode", "interactive").stdout)[
            "run"
        ]

    def release(self) -> None:
        self("lock", "release", "--student", "sample")

    @property
    def data(self) -> Path:
        return self.home / "sample" / "data"

    @property
    def base(self) -> Path:
        return sandbox.base_folder(self.home, "sample")

    def files(self) -> list[str]:
        return sorted(str(p.relative_to(self.base)) for p in self.base.rglob("*") if p.is_file())

    def collect_and_plan(self, *, drop_stop: bool = False, skip: str | None = None) -> dict[str, object]:
        assert self("sandbox", "download", "--student", "sample", "--captures").returncode == 0
        assert self("downloads", "collect", "--student", "sample").returncode == 0
        if drop_stop:
            for stop in self.data.glob(f"captures/alfabeta-capture-{self.run}-stop-*.json"):
                stop.unlink()
        planned = self("plan", "--student", "sample")
        assert planned.returncode == 0, planned.stderr
        assert self("sandbox", "download", "--student", "sample", "--batch", "0").returncode == 0
        if skip:
            (self.home / "downloads" / skip).unlink()
        self("downloads", "collect", "--student", "sample")
        return json.loads(planned.stdout)

    def apply(self, *extra: str) -> tuple[dict[str, object], str]:
        done = self("apply", "--student", "sample", *extra)
        assert done.returncode == 0, done.stderr
        return json.loads(done.stdout), done.stderr


@pytest.fixture
def box(tmp_path: Path) -> Iterator[Box]:
    b = Box(tmp_path / "box")
    assert cli(b.home, "sandbox", "prepare").returncode == 0
    b.take()
    yield b
    b.release()


def test_the_run_places_every_item_or_notes_it(box: Box):
    box.collect_and_plan()
    result, summary = box.apply()
    files = box.files()
    for expected in (
        f"{TOPIC}/20261006 - Ficha inventada de mezclas/enunciado - ficha-inventada.pdf",
        f"{TOPIC}/20261006 - Ficha inventada de mezclas/enunciado.md",
        f"{TOPIC}/20261009 - Informe inventado de laboratorio/enunciado - Plantilla inventada.pdf",
        f"{TOPIC}/20261001 - Apuntes inventados/apuntes-inventados.pdf",
        f"{TOPIC}/20261001 - Apuntes inventados/Presentación inventada.pdf",
        f"{TOPIC}/20261001 - Apuntes inventados/descripcion.md",
        f"{TOPIC}/20261010 - Cuestionario inventado/enlaces.md",
        f"{TOPIC}/20261006 - Ficha inventada de mezclas/entrega/respuestas-inventadas.pdf",
        f"{TOPIC}/20261009 - Informe inventado de laboratorio/entrega/informe-inventado.pdf",
    ):
        assert expected in files
    video = (box.base / TOPIC / "20261001 - Apuntes inventados" / "enlaces.md").read_text()
    assert "[Vídeo inventado](https://www.youtube.com/watch?v=synth-46)" in video
    # The sandbox's stop capture names the English class: it is left unapplied and the run is partial.
    assert (result["result"], result["reason"]) == ("partial", "session_expired")
    assert not any(f.startswith("2026-2027/Ingles/") for f in files)
    assert "clase sin aplicar" in summary and "temas por confirmar: 2" in summary
    assert str(box.base) not in summary  # never an absolute path (FR-031)
    assert list((box.data / "inbox").rglob("*.pdf")) == []  # placed, so gone from data/
    again, _ = box.apply()
    assert (again["added"], again["changed"]) == (0, 0) and box.files() == files


def test_an_attachment_that_does_not_arrive_is_noted(box: Box):
    box.collect_and_plan(skip="ficha-inventada.pdf")
    result, summary = box.apply()
    assert result["not_fetched"] == 1 and "1 sin traer" in summary
    note = (box.base / TOPIC / "20261006 - Ficha inventada de mezclas" / "enlaces.md").read_text()
    assert "no traído" in note and "https://drive.google.com/file/d/synth-40/view" in note


def test_a_submission_that_does_not_arrive_is_noted(box: Box):
    box.collect_and_plan(skip="respuestas-inventadas.pdf")
    result, _ = box.apply()
    folder = box.base / TOPIC / "20261006 - Ficha inventada de mezclas"
    assert result["not_fetched"] == 1 and not (folder / "entrega").exists()
    note = (folder / "enlaces.md").read_text()
    assert "respuestas-inventadas.pdf" in note and "no traído" in note


def test_an_unreadable_class_does_not_stop_the_other(box: Box):
    box.collect_and_plan(drop_stop=True)
    physics = next(box.data.glob(f"captures/alfabeta-capture-{box.run}-synth-1-*.json"))
    broken = json.loads(physics.read_text())
    broken["items"] = "not a list"
    physics.write_text(json.dumps(broken))
    result, summary = box.apply()
    assert result["result"] == "ok" and "capturas ilegibles: 1" in summary
    assert any(f.startswith("2026-2027/Ingles/") for f in box.files())
    assert not any(f.startswith(f"{FYQ}/") for f in box.files())


def test_subject_limits_what_is_applied(box: Box):
    box.collect_and_plan(drop_stop=True)
    box.apply("--subject", "Ingles")
    assert box.files() and all(f.startswith("2026-2027/Ingles/") for f in box.files())


def test_apply_needs_the_lock(box: Box):
    done = cli(box.home, "apply", "--student", "sample")
    assert done.returncode == 1 and '"lock_not_held"' in done.stdout


def test_a_match_confirmed_later_moves_the_replicas_without_copies(box: Box):
    box.collect_and_plan()
    box.apply()
    before = box.files()
    box.release()
    box.take()  # a new run with no new capture: its scope is empty
    proposal = box.home / "p.json"
    proposal.write_text(
        json.dumps(
            {
                "type": "topic_match",
                "origin": "synth-10",
                "target": {"topic": "Tema 01 - Materia inventada"},
                "reason": "same number and title",
                "confidence": "high",
            }
        )
    )
    assert box("decisions", "propose", "--student", "sample", "--file", str(proposal)).returncode == 0
    args = ("decisions", "confirm", "--student", "sample", "--type", "topic_match", "--origin", "synth-10")
    assert box(*args).returncode == 0
    result, _ = box.apply()
    after = box.files()
    assert len(after) == len(before) and int(str(result["changed"])) > 0
    assert not any(f.startswith(TOPIC) for f in after)
    assert f"{BOOK}/20261006 - Ficha inventada de mezclas/enunciado - ficha-inventada.pdf" in after


def test_a_capture_of_another_run_is_not_collected(box: Box):
    other = box.home / "downloads" / "alfabeta-capture-otro-synth-1-20261027-162200.json"
    other.write_text(
        (box.home / "sandbox-captures" / "class-synth-1.json").read_text().replace("run-sintetico", "otro")
    )
    box("downloads", "collect", "--student", "sample")
    assert other.exists()


def test_without_a_base_folder_nothing_is_written(box: Box):
    box.collect_and_plan()
    box.base.rename(box.home / "elsewhere")
    done = box("apply", "--student", "sample")
    assert done.returncode == 1 and '"drive_not_mounted"' in done.stdout
    assert not box.base.exists()
    box.run = ""  # the failed apply released the lock
