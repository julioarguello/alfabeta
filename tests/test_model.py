"""Invariants of the domain (spec 001 T021, data-model.md). Every value is invented."""

from __future__ import annotations

import datetime as dt

import pytest

from alfabeta.model import (
    AgendaCategory,
    AgendaEntry,
    AgendaList,
    Attachment,
    AttachmentKind,
    AttachmentRole,
    Decision,
    DecisionState,
    DecisionType,
    Item,
    ItemStatus,
    ItemType,
    Replica,
    ReplicaRole,
    Run,
    RunMode,
    RunResult,
    StopReason,
    Student,
    Subject,
)

DAY = dt.date(2026, 10, 27)


def decision(kind: DecisionType, state: DecisionState = DecisionState.PROPOSED) -> Decision:
    return Decision(kind, "synth-1", {"subject": "Mates"}, "invented", state, DAY)


def test_decision_transitions():
    proposed = decision(DecisionType.TOPIC_MATCH)
    confirmed = proposed.moved_to(DecisionState.CONFIRMED, DAY)
    assert confirmed.state == DecisionState.CONFIRMED and confirmed.key == proposed.key
    assert confirmed.moved_to(DecisionState.SUPERSEDED, DAY).state == DecisionState.SUPERSEDED
    assert proposed.moved_to(DecisionState.REJECTED, DAY).moved_to(DecisionState.SUPERSEDED, DAY)
    for illegal in (DecisionState.SUPERSEDED, DecisionState.PROPOSED):
        with pytest.raises(ValueError, match="cannot go"):
            proposed.moved_to(illegal, DAY)
    with pytest.raises(ValueError, match="cannot go"):
        confirmed.moved_to(DecisionState.REJECTED, DAY)


def test_a_detected_exam_is_discarded_not_rejected():
    with pytest.raises(ValueError, match="not rejected"):
        decision(DecisionType.DETECTED_EXAM).moved_to(DecisionState.REJECTED, DAY)


@pytest.mark.parametrize(
    ("kind", "state", "counts"),
    [
        (DecisionType.TOPIC_MATCH, DecisionState.PROPOSED, False),
        (DecisionType.TOPIC_MATCH, DecisionState.CONFIRMED, True),
        (DecisionType.DETECTED_EXAM, DecisionState.PROPOSED, True),
        (DecisionType.DISMISSED_CANDIDATE, DecisionState.PROPOSED, True),
        (DecisionType.DISMISSED_CANDIDATE, DecisionState.REJECTED, False),
        (DecisionType.CLASS_LINK, DecisionState.SUPERSEDED, False),
    ],
)
def test_what_counts(kind: DecisionType, state: DecisionState, counts: bool):
    assert decision(kind, state).counts is counts


def test_category_precedence():
    assert AgendaCategory.pick([AgendaCategory.ANNOUNCEMENT, AgendaCategory.QUIZ]) == AgendaCategory.QUIZ
    assert AgendaCategory.pick([AgendaCategory.ASSIGNMENT, AgendaCategory.EXAM]) == AgendaCategory.EXAM
    with pytest.raises(ValueError, match="at least one"):
        AgendaCategory.pick([])


def test_only_files_and_docs_are_downloaded():
    downloaded = {k for k in AttachmentKind if Attachment("synth-2", k, "x", AttachmentRole.MATERIAL).downloaded}
    assert downloaded == {AttachmentKind.FILE, AttachmentKind.GOOGLE_DOC}


def test_only_assignments_and_questions_have_a_status():
    Item("synth-3", "synth-4", None, ItemType.QUESTION, "t", DAY, status=ItemStatus.PENDING)
    with pytest.raises(ValueError, match="status"):
        Item("synth-3", "synth-4", None, ItemType.MATERIAL, "t", DAY, status=ItemStatus.PENDING)


def test_replica_path_and_version():
    Replica("classroom", "synth-5", "synth-6", ReplicaRole.STATEMENT, "2026-2027/Mates/x.pdf", "h")
    with pytest.raises(ValueError, match="255"):
        Replica("classroom", "synth-5", "synth-6", ReplicaRole.STATEMENT, "a/" + "ñ" * 128, "h")
    with pytest.raises(ValueError, match="version"):
        Replica("classroom", "synth-5", "synth-6", ReplicaRole.STATEMENT, "a", "h", version=0)


def entry(**changes: object) -> AgendaEntry:
    base: dict[str, object] = {
        "item": "synth-7",
        "subject": "Mates",
        "list": AgendaList.PENDING,
        "date_only": True,
        "category": AgendaCategory.ASSIGNMENT,
        "title": "t",
        "date": DAY,
        "classroom_link": "https://classroom.google.com/c/synth-8/a/synth-7/details",
    }
    base.update(changes)
    return AgendaEntry(**base)  # type: ignore[arg-type]


def test_agenda_entry_invariants():
    entry()
    entry(detected=True, origin="synth-7", item="synth-7#exam-1", category=AgendaCategory.EXAM)
    with pytest.raises(ValueError, match="origin"):
        entry(detected=True)
    with pytest.raises(ValueError, match="posted"):
        entry(category=AgendaCategory.MATERIAL)
    with pytest.raises(ValueError, match="account index"):
        entry(classroom_link="https://classroom.google.com/u/5/c/synth-8")


def test_run_reason_goes_with_its_result():
    start = dt.datetime(2026, 10, 27, 16, 15, tzinfo=dt.UTC)
    Run("r1", start, start, RunMode.SCHEDULED, RunResult.OK)
    Run("r1", start, start, RunMode.SCHEDULED, RunResult.STOPPED, StopReason.LOCK_BUSY)
    with pytest.raises(ValueError, match="reason"):
        Run("r1", start, start, RunMode.SCHEDULED, RunResult.PARTIAL)
    with pytest.raises(ValueError, match="reason"):
        Run("r1", start, start, RunMode.SCHEDULED, RunResult.OK, StopReason.IDLE)


def test_student_invariants():
    subject = Subject("Mates", "Matemáticas inventadas")
    Student("s9", "Alumna", "2026-2027", "3º ESO", ("es",), (subject,))
    for bad in ({"id": "S9"}, {"school_year": "2026-2028"}, {"subjects": ()}):
        args: dict[str, object] = {
            "id": "s9",
            "display_name": "Alumna",
            "school_year": "2026-2027",
            "grade_level": "3º ESO",
            "languages": ("es",),
            "subjects": (subject,),
        }
        args.update(bad)
        with pytest.raises(ValueError):
            Student(**args)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="together"):
        Subject("FiQui", "x", book="sciencebits")
