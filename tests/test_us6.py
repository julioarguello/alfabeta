"""US6 (spec 001 T060): announcements and the grading, placed by `apply` in the sandbox."""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from alfabeta import replicas
from alfabeta.model import Grading, GradingState
from tests.test_plan_apply_us1 import FYQ, TOPIC, Box, cli

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

GRADED = f"{TOPIC}/20261009 - Informe inventado de laboratorio"
TURNED_IN = f"{TOPIC}/20261006 - Ficha inventada de mezclas"
# Another item without a topic, posted 2026-10-22, dates the folder.
NO_TOPIC = f"{FYQ}/20261022 - Sin tema/classroom"


@pytest.fixture
def box(tmp_path: Path) -> Iterator[Box]:
    b = Box(tmp_path / "box")
    assert cli(b.home, "sandbox", "prepare").returncode == 0
    b.take()
    yield b
    b.release()


def test_a_graded_assignment_gets_its_correccion(box: Box):
    box.collect_and_plan()
    box.apply()
    note = (box.base / GRADED / "correccion.md").read_text()
    assert note == (
        "# Corrección\n"
        "\n"
        "- Estado: calificada\n"
        "- Nota: 8/10\n"
        "- Puntuación máxima: 10 puntos\n"
        "- Fecha de devolución: 24/10/2026\n"
        "\n"
        "## Comentario\n"
        "\n"
        "Comentario inventado.\n"
    )
    # Each role is told apart by its name (SC-008a); an assignment turned in and not graded has none.
    names = sorted(p.name for p in (box.base / GRADED).iterdir())
    assert names == ["correccion.md", "entrega", "enunciado - Plantilla inventada.pdf", "enunciado.md"]
    assert not (box.base / TURNED_IN / "correccion.md").exists()
    again, _ = box.apply()
    assert (again["added"], again["changed"]) == (0, 0)


def test_what_classroom_does_not_show_is_said_never_guessed(box: Box):
    box.collect_and_plan()
    _edit(box, "synth-21", grade_text=None, returned_text=None, teacher_comment=None)
    box.apply()
    note = (box.base / GRADED / "correccion.md").read_text()
    assert "- Nota: Classroom no la muestra\n" in note
    assert "- Fecha de devolución: Classroom no la muestra\n" in note
    assert "Comentario" not in note


@pytest.mark.parametrize("edited", [False, True])
def test_a_grading_withdrawn_takes_its_note_away_unless_edited(box: Box, edited: bool):
    box.collect_and_plan()
    box.apply()
    note = box.base / GRADED / "correccion.md"
    if edited:
        note.write_text(note.read_text() + "Repasar el apartado 3.\n")
    _edit(box, "synth-21", status_text="Entregado")
    box.apply()
    assert note.exists() == edited


def test_announcements_go_to_sin_tema(box: Box):
    box.collect_and_plan()
    box.apply()
    notice = "20261026 - aviso - Recordad traer la bata inventada al laboratorio"
    assert [f for f in box.files() if " - aviso - " in f] == [
        f"{NO_TOPIC}/20261023 - aviso - El examen del tema 1 inventado será el jueves 5 de noviembre.md",
        f"{NO_TOPIC}/{notice}/{notice}.md",
        f"{NO_TOPIC}/{notice}/normas-inventadas.pdf",
    ]
    text = (box.base / NO_TOPIC / notice / f"{notice}.md").read_text()
    assert text == "Recordad traer la bata inventada al laboratorio.\n"


def _edit(box: Box, item: str, **changes: object) -> None:
    """Change one item's detail in the sandbox's class capture, as a later capture would show it."""
    for path in (box.data / "captures").glob("alfabeta-capture-*.json"):
        data = json.loads(path.read_text())
        found = [i for i in data.get("items", []) if i["id"] == item]
        if found:
            found[0]["detail"].update(changes)
            path.write_text(json.dumps(data))
            return
    raise AssertionError(item)


def test_a_state_written_before_the_grading_note_still_reads():
    raw = {
        "id": "synth-21",
        "class_id": "synth-1",
        "topic_id": "synth-10",
        "type": "assignment",
        "title": "Informe inventado de laboratorio",
        "posted_at": "2026-10-09",
        "grading": "graded",
    }
    item, _ = replicas.item_from_json(raw)
    assert item.grading == Grading(GradingState.GRADED)
    graded = replace(item, grading=Grading(GradingState.GRADED, "8/10", "10 puntos", "", dt.date(2026, 10, 24)))
    assert replicas.item_from_json(replicas.item_to_json(graded, None))[0] == graded
