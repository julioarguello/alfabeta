"""Captures → items (spec 001 T034): the fixtures of T029 and every row of the status table."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import pytest

from alfabeta import capture
from alfabeta.dates import MADRID
from alfabeta.model import AttachmentKind, AttachmentRole, GradingState, ItemStatus, ItemType
from alfabeta.sources import ClassroomSource

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "classroom"
NOW = dt.datetime(2026, 10, 27, 16, 0, tzinfo=MADRID)
FUTURE, PAST = dt.date(2026, 10, 30), dt.date(2026, 10, 20)


def load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())


@pytest.mark.parametrize(
    ("status_text", "notice", "due", "expected"),
    [
        ("Asignado", None, FUTURE, ItemStatus.PENDING),
        ("Asignado", None, None, ItemStatus.PENDING),
        ("Falta", None, FUTURE, ItemStatus.PENDING),
        ("Asignado", None, PAST, ItemStatus.OVERDUE),
        ("Falta", None, PAST, ItemStatus.OVERDUE),
        ("Sin entregar", None, FUTURE, ItemStatus.PENDING),
        ("Sin entregar", None, None, ItemStatus.PENDING),
        ("Sin entregar", None, PAST, ItemStatus.OVERDUE),
        ("Asignado", None, dt.date(2026, 10, 27), ItemStatus.PENDING),  # due today is not past
        ("Asignado", None, dt.datetime(2026, 10, 27, 8, 0, tzinfo=MADRID), ItemStatus.OVERDUE),
        ("Entregado", None, PAST, ItemStatus.TURNED_IN),
        ("Entregado con retraso", None, PAST, ItemStatus.TURNED_IN_LATE),
        ("Calificado", None, PAST, ItemStatus.RETURNED),
        ("Devuelto", None, PAST, ItemStatus.RETURNED),
        ("Calificado", "El profesor ha indicado que falta esto", PAST, ItemStatus.MISSING_PER_TEACHER),
        ("Entregado", "El profesor ha indicado que falta esto", None, ItemStatus.MISSING_PER_TEACHER),
        ("Algo nuevo", None, FUTURE, None),
    ],
)
def test_status_table(
    status_text: str, notice: str | None, due: dt.date | dt.datetime | None, expected: ItemStatus | None
):
    detail = {"status_text": status_text, "status_notice_text": notice}
    assert capture.status_of(detail, due, NOW) == expected


def test_the_class_fixture_normalizes():
    physics = capture.normalize_class(load("class-synth-1.json"), "2026-2027")
    assert physics.class_id == "synth-1" and physics.complete and physics.unreadable == ()
    by_id = {item.id: item for item in physics.items}
    assert physics.topics == {"synth-10": "1. Materia inventada", "synth-11": "2. Repaso inventado"}

    turned_in = by_id["synth-20"]
    assert turned_in.status == ItemStatus.TURNED_IN and turned_in.posted_at == dt.date(2026, 10, 6)
    assert turned_in.due_at == dt.datetime(2026, 10, 13, 8, 0, tzinfo=MADRID)
    assert [a.role for a in turned_in.attachments] == [AttachmentRole.STATEMENT]
    assert [a.role for a in turned_in.submission] == [AttachmentRole.SUBMISSION]

    returned = by_id["synth-21"]
    assert returned.status == ItemStatus.RETURNED and returned.grading is not None
    assert returned.grading.grading_state == GradingState.GRADED and returned.grading.grade == "8/10"
    assert returned.grading.returned_at == dt.date(2026, 10, 24)
    assert returned.attachments[0].kind == AttachmentKind.GOOGLE_DOC

    assert by_id["synth-22"].status == ItemStatus.MISSING_PER_TEACHER
    edited = by_id["synth-23"]
    assert edited.type == ItemType.MATERIAL and edited.status is None
    assert edited.posted_at == dt.date(2026, 10, 1) and edited.modified_at == dt.date(2026, 10, 8)
    assert {a.kind for a in edited.attachments} == {
        AttachmentKind.FILE,
        AttachmentKind.VIDEO,
        AttachmentKind.GOOGLE_DOC,
    }
    assert by_id["synth-24"].type == ItemType.QUESTION and by_id["synth-24"].status == ItemStatus.PENDING
    assert by_id["synth-25"].topic_id is None

    exam = by_id["synth-30"]
    assert exam.type == ItemType.ANNOUNCEMENT and exam.topic_id is None and exam.posted_at == dt.date(2026, 10, 23)
    assert "examen" in exam.description.lower()
    assert len(by_id["synth-31"].attachments) == 1


def test_the_english_class_and_the_source():
    english = capture.normalize_class(load("class-synth-2.json"), "2026-2027")
    source = ClassroomSource.from_capture(english)
    assert source.name == "classroom" and source.topics == {"synth-12": "Module 1 - Invented games"}
    assert {i.type for i in source.items()} == {ItemType.ASSIGNMENT, ItemType.ANNOUNCEMENT}


def test_the_status_comes_from_the_detail_not_the_listing():
    data = load("class-synth-1.json")
    data["items"][2]["listing_date_text"] = "Completada"
    by_id = {i.id: i for i in capture.normalize_class(data, "2026-2027").items}
    assert by_id["synth-22"].status == ItemStatus.MISSING_PER_TEACHER


def test_an_unknown_status_is_left_empty_and_reported():
    data = load("class-synth-1.json")
    data["items"][0]["detail"]["status_text"] = "Texto que no conocemos"
    normalized = capture.normalize_class(data, "2026-2027")
    assert normalized.unknown_statuses == ("synth-20",)
    assert next(i for i in normalized.items if i.id == "synth-20").status is None


def test_an_unreadable_item_is_listed_not_guessed():
    data = load("class-synth-1.json")
    data["items"][1]["detail"]["posted_text"] = "pronto"
    data["items"][3]["detail"] = None
    normalized = capture.normalize_class(data, "2026-2027")
    assert normalized.unreadable == ("synth-21", "synth-23")
    assert {i.id for i in normalized.items}.isdisjoint({"synth-21", "synth-23"})


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("run", None, "'run'"),
        ("items", None, "'items'"),
        ("version", 2, "version"),
        ("captured_at", "2026-10-27T16:22:00", "time zone"),
    ],
)
def test_essential_keys_are_checked_by_hand(key: str, value: object, message: str):
    data = load("class-synth-1.json")
    if value is None:
        del data[key]
    else:
        data[key] = value
    with pytest.raises(capture.CaptureError, match=message):
        capture.normalize_class(data, "2026-2027")


def test_read_checks_the_file(tmp_path: Path):
    bad = tmp_path / "x.json"
    bad.write_text("{not json")
    with pytest.raises(capture.CaptureError, match="readable"):
        capture.read(bad)
    assert capture.read(FIXTURES / "stop.json")["reason"] == "session_expired"
