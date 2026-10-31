"""Proposals and decisions (spec 001 T038, contracts/cli.md `decisions *`). Every id is invented."""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from typing import TYPE_CHECKING, Any

import pytest

from alfabeta.decisions import DecisionError, DecisionStore, Proposal, Subtopic, subtopics
from alfabeta.model import DecisionState, DecisionType

if TYPE_CHECKING:
    from pathlib import Path

D1, D2, D3 = dt.date(2026, 10, 20), dt.date(2026, 10, 22), dt.date(2026, 10, 25)


def raw(kind: str = "topic_match", origin: str = "synth-t1", **extra: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "type": kind,
        "origin": origin,
        "target": {"topic": "Tema 02 - Los gases"},
        "reason": "same number and title",
        "confidence": "high",
    }
    base.update(extra)
    return base


def proposal(on: dt.date = D1, **kwargs: Any) -> Proposal:
    return Proposal.parse(raw(**kwargs), on)


@pytest.fixture
def store(tmp_path: Path) -> DecisionStore:
    return DecisionStore.open(tmp_path)


def state_of(store: DecisionStore, kind: str = "topic_match", origin: str = "synth-t1") -> DecisionState | None:
    record = store.in_force(DecisionType(kind), origin)
    return record.decision.state if record else None


def test_a_key_in_force_is_not_proposed_again(store: DecisionStore):
    assert len(store.propose([proposal()], D1)[0]) == 1
    recorded, ignored = store.propose([proposal(D2, target={"topic": "Tema 03 - Otro"})], D2)
    assert recorded == [] and len(ignored) == 1
    store.confirm(DecisionType.TOPIC_MATCH, "synth-t1", D2)
    assert store.propose([proposal(D3)], D3)[0] == []


def test_an_identical_proposal_does_not_write(store: DecisionStore):
    store.propose([proposal()], D1)
    assert store.save() is True
    store = DecisionStore.open(store.path.parent)
    store.propose([proposal(D2)], D2)
    assert store.save() is False


@pytest.mark.parametrize(
    ("extra", "reopens"),
    [
        ({}, False),
        ({"origin_modified": "2026-10-21"}, False),  # modified before the rejection
        ({"origin_modified": "2026-10-23"}, True),
        ({"origin_title": "2. Gases (nuevo título)"}, True),
        ({"book_topics": ["Tema 02 - Los gases", "Tema 05 - Nuevo"]}, True),
        ({"book_topics": ["Tema 02 - Los gases"]}, False),
    ],
)
def test_a_rejected_one_reopens_only_when_its_origin_changed(
    store: DecisionStore, extra: dict[str, Any], reopens: bool
):
    store.propose([proposal(origin_title="2. Gases", book_topics=["Tema 02 - Los gases"])], D1)
    store.confirm(DecisionType.TOPIC_MATCH, "synth-t1", D2, reject=True)
    now: dict[str, Any] = {"origin_title": "2. Gases", "book_topics": ["Tema 02 - Los gases"]} | extra
    recorded, _ = store.propose([proposal(D3, **now)], D3)
    assert bool(recorded) is reopens
    assert state_of(store) == (DecisionState.PROPOSED if reopens else DecisionState.REJECTED)


def test_title_and_book_topics_reopen_only_topic_matches(store: DecisionStore):
    store.propose([proposal(kind="class_link", target={"subject": "FyQ"}, origin_title="Física")], D1)
    store.confirm(DecisionType.CLASS_LINK, "synth-t1", D2, reject=True)
    again = proposal(D3, kind="class_link", target={"subject": "FyQ"}, origin_title="Física 3ºA")
    assert store.propose([again], D3)[0] == []


def test_a_detected_exam_is_not_rejected(store: DecisionStore):
    exam = proposal(kind="detected_exam", origin="synth-i1#exam-1", target={"date": "2026-11-05"}, origin_hash="h1")
    store.propose([exam], D1)
    with pytest.raises(DecisionError, match="discard"):
        store.confirm(DecisionType.DETECTED_EXAM, "synth-i1#exam-1", D2, reject=True)
    assert store.correct("synth-i1#exam-1", {"discarded": "true"}, D2).state == DecisionState.CONFIRMED


@pytest.mark.parametrize(
    ("target", "fits"),
    [
        ({"date": "2026-11-05"}, True),
        ({"date": "2026-11-05T09:30"}, True),
        ({"date": ""}, True),
        ({"date": "2026-11-05", "category": "quiz"}, True),
        ({"date": "20261105"}, False),  # Python reads it as midnight
        ({"date": "2026-02-30"}, False),
        ({"date": "el jueves"}, False),
        ({"date": "2026-11-05", "category": "examen"}, False),  # the Spanish label, not the value
    ],
)
def test_a_detected_exam_carries_a_date_and_category_the_agenda_reads(target: dict[str, str], fits: bool):
    raw_exam = raw("detected_exam", "synth-i1#exam-1", target=target, origin_hash="h1")
    if fits:
        assert Proposal.parse(raw_exam, D1).decision.target == target
    else:
        with pytest.raises(DecisionError, match="detected exam's"):
            Proposal.parse(raw_exam, D1)


def test_a_correction_adds_to_the_one_before(store: DecisionStore):
    origin = "synth-i1#exam-1"
    store.propose([proposal(kind="detected_exam", origin=origin, target={"date": "2026-11-05"}, origin_hash="h1")], D1)
    store.correct(origin, {"date": "2026-11-12"}, D2)
    assert store.correct(origin, {"category": "assignment"}, D2).target == {
        "date": "2026-11-12",
        "category": "assignment",
    }
    assert store.correct(origin, {"discarded": "true"}, D2).target["discarded"] == "true"
    assert "discarded" not in store.correct(origin, {"date": "2026-11-13"}, D2).target  # an exam after all


@pytest.mark.parametrize("reject", [False, True])
def test_change_supersedes_a_confirmed_or_rejected_one(store: DecisionStore, reject: bool):
    store.propose([proposal()], D1)
    store.confirm(DecisionType.TOPIC_MATCH, "synth-t1", D2, reject=reject)
    changed = store.change(DecisionType.TOPIC_MATCH, "synth-t1", {"topic": "Tema 03 - Otro"}, D3)
    assert changed.state == DecisionState.CONFIRMED and changed.target == {"topic": "Tema 03 - Otro"}
    states = [r.decision.state for r in store.records]
    assert states == [DecisionState.SUPERSEDED, DecisionState.CONFIRMED]
    with pytest.raises(DecisionError):
        DecisionStore(store.path).change(DecisionType.TOPIC_MATCH, "synth-t1", {"topic": "x"}, D3)


def test_the_type_disambiguates_one_origin(store: DecisionStore):
    store.propose([proposal(kind="class_link", target={"subject": "FyQ"}), proposal()], D1)
    store.confirm(DecisionType.CLASS_LINK, "synth-t1", D2)
    assert state_of(store, "class_link") == DecisionState.CONFIRMED
    assert state_of(store, "topic_match") == DecisionState.PROPOSED


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"confidence": None}, "confidence"),
        ({"confidence": "absolute"}, "confidence"),
        ({"reason": "  "}, "reason"),
        ({"type": "exam_correction"}, "only the family"),
        ({"type": "detected_exam"}, "hash"),
        ({"target": "Tema 02"}, "target"),
    ],
)
def test_a_proposal_must_fit_the_contract(change: dict[str, Any], message: str):
    bad = raw()
    for key, value in change.items():
        if value is None:
            del bad[key]
        else:
            bad[key] = value
    with pytest.raises(DecisionError, match=message):
        Proposal.parse(bad, D1)


def test_a_dismissed_candidate_counts_when_proposed_and_returns_when_rejected(store: DecisionStore):
    store.propose([proposal(kind="dismissed_candidate", origin="synth-i2", target={}, origin_hash="h1")], D1)
    record = store.in_force(DecisionType.DISMISSED_CANDIDATE, "synth-i2")
    assert record is not None and record.decision.counts
    rejected = store.confirm(DecisionType.DISMISSED_CANDIDATE, "synth-i2", D2, reject=True)
    assert not rejected.counts


@pytest.mark.parametrize("kind", ["detected_exam", "dismissed_candidate"])
def test_a_changed_text_supersedes_unless_the_family_corrected(store: DecisionStore, kind: str):
    origin = "synth-i3#exam-1"
    store.propose([proposal(kind=kind, origin=origin, target={}, origin_hash="h1")], D1)
    recorded, _ = store.propose([proposal(D2, kind=kind, origin=origin, target={}, origin_hash="h2")], D2)
    assert len(recorded) == 1
    assert [r.decision.state for r in store.records] == [DecisionState.SUPERSEDED, DecisionState.PROPOSED]
    if kind == "detected_exam":
        store.correct(origin, {"date": "2026-11-06"}, D2)
        recorded, _ = store.propose([proposal(D3, kind=kind, origin=origin, target={}, origin_hash="h3")], D3)
        assert recorded == []


def test_the_store_round_trips(store: DecisionStore):
    store.propose([proposal(origin_title="2. Gases", book_topics=["Tema 02 - Los gases"])], D1)
    store.save()
    again = DecisionStore.open(store.path.parent)
    assert again.records == store.records


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


def test_the_commands_need_the_lock_and_renew_it(tmp_path: Path):
    (tmp_path / "s9").mkdir()
    (tmp_path / "s9" / "config.toml").write_text(
        "[sync]\nfull_review_days = 7\nlock_idle_minutes = 30\nkept_captures = 10\n"
    )
    file = tmp_path / "p.json"
    file.write_text(json.dumps([raw()]))
    assert cli(tmp_path, "decisions", "propose", "--student", "s9", "--file", str(file)).returncode == 1
    run = json.loads(cli(tmp_path, "lock", "take", "--student", "s9", "--mode", "interactive").stdout)["run"]
    try:
        done = cli(tmp_path, "decisions", "propose", "--student", "s9", "--file", str(file), run=run)
        assert done.returncode == 0, done.stderr
        assert json.loads(done.stdout)["recorded"] == [{"type": "topic_match", "origin": "synth-t1"}]
        args = ("decisions", "confirm", "--student", "s9", "--type", "topic_match", "--origin", "synth-t1")
        assert cli(tmp_path, *args, run=run).returncode == 0
        exam = ("decisions", "confirm", "--student", "s9", "--type", "detected_exam", "--origin", "x", "--reject")
        assert cli(tmp_path, *exam, run=run).returncode == 1
        assert cli(tmp_path, *args, run="otro-run").returncode == 1
    finally:
        cli(tmp_path, "lock", "release", "--student", "s9", run=run)


# --- the subtopics of a split textbook topic (spec 002 FR-043) -----------------------------------------


def sub(letter: str, lessons: str, title: str = "Lección inventada", on: dt.date = D1) -> Proposal:
    return proposal(on, kind="subtopic", origin=f"Bio/Tema 02{letter}", target={"title": title, "lessons": lessons})


def test_a_split_is_one_subtopic_decision_each_and_only_confirmed_ones_count(store: DecisionStore):
    store.propose([sub("A", "1,2,3,4,5", "Nutrientes y digestión"), sub("B", "6"), sub("C", "7")], D1)
    assert subtopics(store.decisions(), "Bio", "Tema 02") == []
    for letter in "AB":
        store.confirm(DecisionType.SUBTOPIC, f"Bio/Tema 02{letter}", D2)
    store.confirm(DecisionType.SUBTOPIC, "Bio/Tema 02C", D2, reject=True)
    assert subtopics(store.decisions(), "Bio", "Tema 02") == [
        Subtopic("A", "Nutrientes y digestión", (1, 2, 3, 4, 5)),
        Subtopic("B", "Lección inventada", (6,)),
    ]
    assert subtopics(store.decisions(), "Bio", "Tema 03") == [] and subtopics(store.decisions(), "FyQ", "Tema 02") == []


@pytest.mark.parametrize(
    ("origin", "target"),
    [
        ("Bio/Tema 02", {"title": "x", "lessons": "1"}),
        ("Tema 02B", {"title": "x", "lessons": "1"}),
        ("Bio/Tema 02b", {"title": "x", "lessons": "1"}),
        ("Bio/Tema 02B", {"title": " ", "lessons": "1"}),
        ("Bio/Tema 02B", {"title": "x", "lessons": ""}),
        ("Bio/Tema 02B", {"title": "x", "lessons": "6,5"}),
        ("Bio/Tema 02B", {"title": "x", "lessons": "6,6"}),
        ("Bio/Tema 02B", {"title": "x", "lessons": "0"}),
        ("Bio/Tema 02B", {"title": "x", "lessons": "6-7"}),
    ],
)
def test_a_subtopic_that_does_not_fit_is_refused(origin: str, target: dict[str, str]):
    with pytest.raises(DecisionError):
        proposal(kind="subtopic", origin=origin, target=target)


def test_a_lesson_in_two_subtopics_writes_nothing(store: DecisionStore):
    store.propose([sub("A", "1,2,3,4,5")], D1)
    store.confirm(DecisionType.SUBTOPIC, "Bio/Tema 02A", D1)
    with pytest.raises(DecisionError, match="lesson 5 of Bio/Tema 02 is in two subtopics"):
        store.propose([sub("B", "5,6", on=D2)], D2)
    with pytest.raises(DecisionError, match="lesson 7"):
        store.propose([sub("B", "6,7", on=D2), sub("C", "7", on=D2)], D2)
    assert [r.decision.origin for r in store.records] == ["Bio/Tema 02A"]
    # A rejected subtopic holds no lesson.
    store.propose([sub("B", "6", on=D2)], D2)
    store.confirm(DecisionType.SUBTOPIC, "Bio/Tema 02B", D2, reject=True)
    assert len(store.propose([sub("C", "6", on=D3)], D3)[0]) == 1


def test_a_confirmed_subtopic_never_changes(store: DecisionStore):
    store.propose([sub("A", "1,2,3,4,5")], D1)
    store.confirm(DecisionType.SUBTOPIC, "Bio/Tema 02A", D1)
    assert store.propose([sub("A", "1,2,3", on=D2)], D2) == ([], [sub("A", "1,2,3", on=D2).decision])
    with pytest.raises(DecisionError, match="never changes"):
        store.change(DecisionType.SUBTOPIC, "Bio/Tema 02A", {"topic": "x"}, D2)


def test_a_rejected_split_is_proposed_again_only_with_new_material(store: DecisionStore):
    store.propose([sub("B", "6")], D1)
    store.confirm(DecisionType.SUBTOPIC, "Bio/Tema 02B", D1, reject=True)
    assert store.propose([sub("B", "6", on=D2)], D2)[0] == []
    again = Proposal.parse(
        raw(
            kind="subtopic",
            origin="Bio/Tema 02B",
            target={"title": "x", "lessons": "6"},
            origin_modified=D3.isoformat(),
        ),
        D3,
    )
    assert len(store.propose([again], D3)[0]) == 1
