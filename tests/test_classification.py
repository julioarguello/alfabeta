"""The closed category of each item and the exam candidates (spec 001 T044, FR-020a, FR-020b, FR-021b, SC-004a)."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from alfabeta import capture
from alfabeta.classification import CANDIDATE, Classifier, candidate_text, text_hash
from alfabeta.model import (
    AgendaCategory,
    Attachment,
    AttachmentKind,
    AttachmentRole,
    Decision,
    DecisionState,
    DecisionType,
    Item,
    ItemType,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "classroom"
ES_EN = Classifier(("es", "en"))
DAY = dt.date(2026, 10, 27)
FORM = Attachment("synth-f", AttachmentKind.FORM, "Formulario inventado", AttachmentRole.STATEMENT)
FILE = Attachment("synth-a", AttachmentKind.FILE, "ficha-inventada.pdf", AttachmentRole.STATEMENT)


def item(
    kind: ItemType, title: str, *, description: str = "", attachments: tuple[Attachment, ...] = (), id: str = "synth-i"
) -> Item:
    return Item(
        id, "synth-c", None, kind, title, dt.date(2026, 10, 20), description=description, attachments=attachments
    )


@pytest.mark.parametrize(
    ("kind", "title", "attachments", "category"),
    [
        (ItemType.QUESTION, "Examen inventado del tema 2", (), AgendaCategory.EXAM),  # a question that is an exam
        (ItemType.ASSIGNMENT, "Examen inventado del tema 2", (FILE,), AgendaCategory.EXAM),
        (ItemType.ASSIGNMENT, "Invented unit test", (), AgendaCategory.EXAM),  # the student's other language
        (ItemType.ASSIGNMENT, "Control inventado de formulación", (FILE,), AgendaCategory.EXAM),
        (ItemType.ASSIGNMENT, "Prueba inventada", (FORM,), AgendaCategory.EXAM),  # exam beats quiz
        (ItemType.QUESTION, "¿Pregunta inventada?", (), AgendaCategory.QUIZ),
        (ItemType.ASSIGNMENT, "Cuestionario inventado", (FORM,), AgendaCategory.QUIZ),
        (ItemType.ASSIGNMENT, "Ficha inventada", (FORM, FILE), AgendaCategory.ASSIGNMENT),
        (ItemType.ASSIGNMENT, "Ficha inventada", (FILE,), AgendaCategory.ASSIGNMENT),
        (ItemType.ASSIGNMENT, "Ficha inventada", (), AgendaCategory.ASSIGNMENT),
        (ItemType.MATERIAL, "Apuntes inventados", (FILE,), AgendaCategory.MATERIAL),
        # The source keeps its own category; the exam it announces is an entry of its own (FR-020b).
        (ItemType.MATERIAL, "Examen inventado del curso pasado", (FILE,), AgendaCategory.MATERIAL),
        (ItemType.ANNOUNCEMENT, "Recordad traer la bata inventada", (), AgendaCategory.ANNOUNCEMENT),
        (ItemType.ANNOUNCEMENT, "El examen inventado será el lunes", (), AgendaCategory.ANNOUNCEMENT),
    ],
)
def test_every_item_gets_exactly_one_category(
    kind: ItemType, title: str, attachments: tuple[Attachment, ...], category: AgendaCategory
):
    assert ES_EN.category(item(kind, title, attachments=attachments)) == category


@pytest.mark.parametrize(
    ("title", "category"),
    [
        ("EXÁMENES inventados", AgendaCategory.EXAM),  # neither case nor accents matter
        ("Examenes inventados", AgendaCategory.EXAM),
        ("Contestad la ficha inventada", AgendaCategory.ASSIGNMENT),  # «test» inside a word is not a hint
        ("The latest invented worksheet", AgendaCategory.ASSIGNMENT),
        ("Ficha inventada (control)", AgendaCategory.EXAM),
    ],
)
def test_a_hint_is_a_whole_word_whatever_its_case_or_accents(title: str, category: AgendaCategory):
    assert ES_EN.category(item(ItemType.ASSIGNMENT, title)) == category


def test_only_the_students_languages_give_hints():
    spanish = item(ItemType.ASSIGNMENT, "Examen inventado")
    english = item(ItemType.ASSIGNMENT, "Invented exam")
    assert Classifier(("es",)).category(spanish) == AgendaCategory.EXAM
    assert Classifier(("en",)).category(spanish) == AgendaCategory.ASSIGNMENT
    assert Classifier(("en",)).category(english) == AgendaCategory.EXAM
    assert Classifier(("es",)).category(english) == AgendaCategory.ASSIGNMENT


@pytest.mark.parametrize(
    ("title", "category"),
    [
        ("Azterketa asmatua", AgendaCategory.EXAM),
        ("Gai asmatuaren AZTERKETARAKO fitxa", AgendaCategory.EXAM),  # a stem takes the case Basque adds
        ("Kontrola ostiralean", AgendaCategory.EXAM),
        ("Probabilitate asmatua", AgendaCategory.ASSIGNMENT),  # not a stem: «proba» is left out
        ("Ariketa asmatuak", AgendaCategory.ASSIGNMENT),
        ("Irakurri testua eta erantzun", AgendaCategory.ASSIGNMENT),  # «testua» is a text, not a test
        ("Kontrolatu zure lana", AgendaCategory.ASSIGNMENT),  # the verb, not the test
        ("Kontrolerako ariketak", AgendaCategory.EXAM),
        ("Test asmatua", AgendaCategory.EXAM),
    ],
)
def test_basque_hints_match_their_stem_with_any_ending(title: str, category: AgendaCategory):
    assert Classifier(("eu",)).category(item(ItemType.ASSIGNMENT, title)) == category
    if not title.startswith("Test "):  # «test» is English and Spanish too
        assert ES_EN.category(item(ItemType.ASSIGNMENT, title)) == AgendaCategory.ASSIGNMENT


def fixture_items() -> list[Item]:
    found: list[Item] = []
    for name in ("class-synth-1.json", "class-synth-2.json"):
        found += capture.normalize_class(json.loads((FIXTURES / name).read_text()), "2026-2027").items
    return found


def test_every_invented_exam_announcement_is_a_candidate():
    # SC-004a: the Spanish and the English announcement of T029, and nothing else of the fixtures.
    candidates = ES_EN.candidates(fixture_items(), [])
    assert sorted(c["origin"] for c in candidates) == ["synth-30", "synth-32"]
    assert {c["type"] for c in candidates} == {CANDIDATE}


def test_a_candidate_carries_what_claude_needs_to_propose():
    exam = next(i for i in fixture_items() if i.id == "synth-30")
    [candidate] = ES_EN.candidates([exam], [])
    assert candidate == {
        "type": CANDIDATE,
        "origin": "synth-30",
        "title": exam.title,
        "text": exam.description,
        "posted_at": "2026-10-23",
        "origin_hash": text_hash(exam),
    }
    assert candidate_text(exam) == exam.description


def test_a_material_title_or_description_gives_a_candidate():
    by_title = item(ItemType.MATERIAL, "Examen inventado del curso pasado", id="synth-m1")
    by_text = item(
        ItemType.MATERIAL, "Apuntes inventados", description="El control inventado será el lunes.", id="synth-m2"
    )
    plain = item(ItemType.MATERIAL, "Apuntes inventados", description="Leed los apuntes inventados.", id="synth-m3")
    assert [c["origin"] for c in ES_EN.candidates([by_title, by_text, plain], [])] == ["synth-m1", "synth-m2"]
    assert text_hash(by_title) != text_hash(
        item(ItemType.MATERIAL, "Examen inventado del curso pasado", description="x")
    )


def test_an_assignment_or_question_is_never_a_candidate():
    # FR-020b infers exams from announcements and materials; an assignment's exam is its own category.
    graded = item(ItemType.ASSIGNMENT, "Examen inventado", id="synth-e1")
    worksheet = item(ItemType.ASSIGNMENT, "Ficha inventada", description="Para el examen inventado.", id="synth-e2")
    question = item(ItemType.QUESTION, "¿Entra el examen inventado?", id="synth-e3")
    assert ES_EN.candidates([graded, worksheet, question], []) == []


ANNOUNCEMENT = item(ItemType.ANNOUNCEMENT, "El examen inventado", description="El examen inventado será el lunes.")
HASH = text_hash(ANNOUNCEMENT)


def decision(
    kind: DecisionType, origin: str, digest: str | None, state: DecisionState = DecisionState.PROPOSED
) -> Decision:
    target = {"discarded": "true"} if kind == DecisionType.EXAM_CORRECTION else {"date": "2026-11-02"}
    return Decision(kind, origin, target, "inventado", state, DAY, origin_hash=digest)


@pytest.mark.parametrize(
    ("decisions", "pending"),
    [
        ([], True),
        ([decision(DecisionType.DETECTED_EXAM, "synth-i#exam-1", HASH)], False),
        ([decision(DecisionType.DETECTED_EXAM, "synth-i#exam-2", HASH)], False),
        ([decision(DecisionType.DETECTED_EXAM, "synth-i#exam-1", HASH, DecisionState.CONFIRMED)], False),
        ([decision(DecisionType.DISMISSED_CANDIDATE, "synth-i", HASH)], False),
        # A rejected dismissal does not count: the candidate comes back.
        ([decision(DecisionType.DISMISSED_CANDIDATE, "synth-i", HASH, DecisionState.REJECTED)], True),
        # The text changed since it was judged.
        ([decision(DecisionType.DETECTED_EXAM, "synth-i#exam-1", "other")], True),
        ([decision(DecisionType.DISMISSED_CANDIDATE, "synth-i", "other")], True),
        # ... unless the family corrected that exam.
        (
            [
                decision(DecisionType.DETECTED_EXAM, "synth-i#exam-1", "other"),
                decision(DecisionType.EXAM_CORRECTION, "synth-i#exam-1", None, DecisionState.CONFIRMED),
            ],
            False,
        ),
        ([decision(DecisionType.DETECTED_EXAM, "synth-i#exam-1", HASH, DecisionState.SUPERSEDED)], True),
        # Another item whose id starts with this one's.
        ([decision(DecisionType.DETECTED_EXAM, "synth-ii#exam-1", HASH)], True),
    ],
)
def test_a_candidate_is_pending_until_a_decision_on_its_text(decisions: list[Decision], pending: bool):
    assert bool(ES_EN.candidates([ANNOUNCEMENT], decisions)) == pending
