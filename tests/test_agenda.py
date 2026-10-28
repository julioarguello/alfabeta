"""The agenda (spec 001 T045, FR-020…FR-020c, FR-021, FR-025, SC-004a): its lists, labels, links and files."""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest
from jsonschema import Draft202012Validator

from alfabeta import __main__ as cli_main
from alfabeta import decisions as decisions_module
from alfabeta.agenda import AgendaBuilder
from alfabeta.classification import Classifier, text_hash
from alfabeta.dates import MADRID
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
    Subject,
)
from alfabeta.notes.refresh import AGENDA_LINE
from alfabeta.replicas import item_from_json, item_to_json
from tests.test_incremental import first_run, next_run
from tests.test_plan_apply_us1 import Box, cli

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

SCHEMA = Path(__file__).resolve().parents[1] / "specs" / "001-classroom-sync" / "contracts" / "agenda.schema.json"
CLASS = "synth-c1"
SUBJECT = Subject("FyQ", "Física inventada")
BEFORE = dt.datetime(2026, 10, 27, 16, 22, tzinfo=MADRID)
LATER = dt.datetime(2026, 12, 1, 16, 22, tzinfo=MADRID)
DAY = dt.date(2026, 10, 27)
FORM = Attachment("synth-f", AttachmentKind.FORM, "Formulario inventado", AttachmentRole.STATEMENT)


def it(
    id: str,
    kind: ItemType,
    title: str,
    *,
    posted: dt.date = dt.date(2026, 10, 1),
    due: dt.datetime | dt.date | None = None,
    status: ItemStatus | None = None,
    attachments: tuple[Attachment, ...] = (),
    description: str = "",
) -> Item:
    return Item(
        id,
        CLASS,
        None,
        kind,
        title,
        posted,
        due_at=due,
        status=status,
        attachments=attachments,
        description=description,
    )


ON_ITS_TEXT = "on its text"


def exam(
    origin: str, date: str = "2026-11-05", state: DecisionState = DecisionState.PROPOSED, origin_hash: str = ON_ITS_TEXT
) -> Decision:
    return Decision(
        DecisionType.DETECTED_EXAM,
        origin,
        {"date": date, "reason": "inventado"},
        "inventado",
        state,
        DAY,
        origin_hash=origin_hash,
    )


def correction(origin: str, **target: str) -> Decision:
    return Decision(DecisionType.EXAM_CORRECTION, origin, target, "inventado", DecisionState.CONFIRMED, DAY)


def builder(
    items: Iterable[Item],
    decisions: Iterable[Decision] = (),
    *,
    captured: dt.datetime = BEFORE,
    replicas: dict[str, Any] | None = None,
    withdrawn: Iterable[str] = (),
) -> AgendaBuilder:
    gone = set(withdrawn)
    items = list(items)
    # A detected exam the test does not say otherwise of was proposed on its source's current text.
    texts = {i.id: text_hash(i) for i in items}
    decisions = [
        replace(d, origin_hash=texts.get(d.origin.split("#exam-", 1)[0], d.origin_hash))
        if d.type == DecisionType.DETECTED_EXAM and d.origin_hash == ON_ITS_TEXT
        else d
        for d in decisions
    ]
    state = {
        "items": {
            i.id: item_to_json(i, None) | ({"withdrawn_at": "2026-10-20"} if i.id in gone else {}) for i in items
        },
        "replicas": replicas or {},
    }
    return AgendaBuilder(
        school_year="2026-2027",
        links={CLASS: SUBJECT},
        classifier=Classifier(("es", "en")),
        decisions=list(decisions),
        state=state,
        captured={CLASS: captured},
    )


def entries(b: AgendaBuilder) -> dict[str, AgendaEntry]:
    return {e.item: e for e in b.entries()}


def homework(id: str = "synth-a1", **kw: Any) -> Item:
    return it(id, ItemType.ASSIGNMENT, "Ficha inventada", **kw)


@pytest.mark.parametrize(
    ("status", "listed"),
    [
        (ItemStatus.PENDING, AgendaList.PENDING),
        (ItemStatus.OVERDUE, AgendaList.PENDING),
        (ItemStatus.MISSING_PER_TEACHER, AgendaList.PENDING),
        (ItemStatus.TURNED_IN, AgendaList.DONE),
        (ItemStatus.TURNED_IN_LATE, AgendaList.DONE),
        (ItemStatus.RETURNED, AgendaList.DONE),
        (None, AgendaList.PENDING),  # an unknown status text, or nothing to turn in
    ],
)
def test_each_status_has_its_list(status: ItemStatus | None, listed: AgendaList):
    due = dt.date(2026, 10, 20)
    found = entries(
        builder(
            [
                homework(due=due, status=status),
                it("synth-q1", ItemType.QUESTION, "¿Pregunta inventada?", due=due, status=status),
                it(
                    "synth-q2",
                    ItemType.ASSIGNMENT,
                    "Cuestionario inventado",
                    due=due,
                    status=status,
                    attachments=(FORM,),
                ),
            ],
            captured=LATER,  # a later capture moves no assignment nor quiz to «Hecho»
        )
    )
    assert {k: (e.category, e.list, e.status) for k, e in found.items()} == {
        "synth-a1": (AgendaCategory.ASSIGNMENT, listed, status),
        "synth-q1": (AgendaCategory.QUIZ, listed, status),
        "synth-q2": (AgendaCategory.QUIZ, listed, status),
    }


@pytest.mark.parametrize(
    ("status", "captured", "listed"),
    [
        (ItemStatus.OVERDUE, LATER, AgendaList.DONE),  # the exam took place: it wins over «overdue»
        (ItemStatus.PENDING, LATER, AgendaList.DONE),
        (None, LATER, AgendaList.DONE),
        (ItemStatus.MISSING_PER_TEACHER, LATER, AgendaList.PENDING),  # the teacher says it is missing
        (ItemStatus.OVERDUE, BEFORE, AgendaList.PENDING),
        (ItemStatus.PENDING, BEFORE, AgendaList.PENDING),
        (ItemStatus.RETURNED, BEFORE, AgendaList.DONE),
    ],
)
def test_an_exam_that_is_an_assignment(status: ItemStatus | None, captured: dt.datetime, listed: AgendaList):
    test = it("synth-x1", ItemType.ASSIGNMENT, "Examen inventado", due=dt.date(2026, 11, 2), status=status)
    [entry] = builder([test], captured=captured).entries()
    assert (entry.category, entry.list, entry.detected) == (AgendaCategory.EXAM, listed, False)


@pytest.mark.parametrize(
    ("captured", "listed"),
    [
        (dt.datetime(2026, 11, 5, 23, 59, tzinfo=MADRID), AgendaList.PENDING),
        (dt.datetime(2026, 11, 6, 0, 0, 1, tzinfo=MADRID), AgendaList.DONE),
        # The end of that day in Madrid, not in UTC: 23:30 UTC on the 5th is already the 6th in Madrid.
        (dt.datetime(2026, 11, 5, 23, 30, tzinfo=dt.UTC), AgendaList.DONE),
        (dt.datetime(2026, 11, 5, 22, 30, tzinfo=dt.UTC), AgendaList.PENDING),
    ],
)
def test_later_than_a_date_is_after_the_end_of_that_day_in_madrid(captured: dt.datetime, listed: AgendaList):
    post = it("synth-n1", ItemType.ANNOUNCEMENT, "Aviso inventado", description="El examen inventado.")
    found = entries(builder([post], [exam("synth-n1#exam-1", "2026-11-05")], captured=captured))
    assert found["synth-n1#exam-1"].list == listed


@pytest.mark.parametrize(
    ("captured", "listed"),
    [
        (dt.datetime(2026, 11, 5, 8, 59, tzinfo=MADRID), AgendaList.PENDING),
        (dt.datetime(2026, 11, 5, 9, 1, tzinfo=MADRID), AgendaList.DONE),
    ],
)
def test_later_than_an_instant_is_after_that_instant(captured: dt.datetime, listed: AgendaList):
    test = it("synth-x1", ItemType.QUESTION, "Examen inventado", due=dt.datetime(2026, 11, 5, 9, 0, tzinfo=MADRID))
    [entry] = builder([test], captured=captured).entries()
    assert (entry.date_only, entry.list) == (False, listed)


def test_a_detected_exam_is_an_entry_of_its_own_from_the_moment_it_is_proposed():
    post = it("synth-n1", ItemType.ANNOUNCEMENT, "Aviso inventado", description="El examen inventado será el jueves.")
    found = entries(builder([post], [exam("synth-n1#exam-1")]))
    detected = found["synth-n1#exam-1"]
    assert (detected.category, detected.list, detected.detected, detected.origin) == (
        AgendaCategory.EXAM,
        AgendaList.PENDING,
        True,
        "synth-n1",
    )
    assert (detected.date, detected.date_only, detected.status, detected.corrected) == (
        dt.date(2026, 11, 5),
        True,
        None,
        False,
    )
    assert detected.classroom_link == found["synth-n1"].classroom_link  # the link to the item it comes from
    source = found["synth-n1"]  # the announcement keeps its own entry and its category
    assert (source.category, source.list, source.detected) == (AgendaCategory.ANNOUNCEMENT, AgendaList.POSTED, False)


def test_an_item_that_announces_two_exams_gives_two_entries():
    post = it("synth-m1", ItemType.MATERIAL, "Calendario inventado de exámenes")
    found = entries(builder([post], [exam("synth-m1#exam-1", "2026-11-05"), exam("synth-m1#exam-2", "2026-11-12")]))
    assert sorted(found) == ["synth-m1", "synth-m1#exam-1", "synth-m1#exam-2"]
    assert found["synth-m1"].category == AgendaCategory.MATERIAL


def test_a_detected_exam_without_a_date_stays_pending_until_the_family_corrects_it():
    post = it("synth-n1", ItemType.ANNOUNCEMENT, "Aviso inventado", description="Habrá examen inventado.")
    undated = exam("synth-n1#exam-1", "")
    [entry] = [e for e in builder([post], [undated], captured=LATER).entries() if e.detected]
    assert (entry.date, entry.list) == (None, AgendaList.PENDING)
    dated = builder([post], [undated, correction("synth-n1#exam-1", date="2026-11-05")], captured=LATER)
    [entry] = [e for e in dated.entries() if e.detected]
    assert (entry.date, entry.list, entry.corrected) == (dt.date(2026, 11, 5), AgendaList.DONE, True)


def test_a_dismissed_exam_leaves_the_agenda():
    post = it("synth-n1", ItemType.ANNOUNCEMENT, "Aviso inventado", description="Habrá examen inventado.")
    found = entries(builder([post], [exam("synth-n1#exam-1"), correction("synth-n1#exam-1", discarded="true")]))
    assert sorted(found) == ["synth-n1"]


def test_the_familys_correction_prevails():
    post = it("synth-n1", ItemType.ANNOUNCEMENT, "Aviso inventado", description="El examen inventado.")
    found = entries(builder([post], [exam("synth-n1#exam-1"), correction("synth-n1#exam-1", date="2026-11-20")]))
    assert (found["synth-n1#exam-1"].date, found["synth-n1#exam-1"].corrected) == (dt.date(2026, 11, 20), True)
    as_quiz = entries(builder([post], [exam("synth-n1#exam-1"), correction("synth-n1#exam-1", category="quiz")]))
    entry = as_quiz["synth-n1#exam-1"]
    assert (entry.category, entry.list, entry.date) == (AgendaCategory.QUIZ, AgendaList.PENDING, dt.date(2026, 11, 5))
    as_material = entries(
        builder([post], [exam("synth-n1#exam-1"), correction("synth-n1#exam-1", category="material")])
    )
    assert (as_material["synth-n1#exam-1"].category, as_material["synth-n1#exam-1"].list) == (
        AgendaCategory.MATERIAL,
        AgendaList.POSTED,
    )


def test_an_exam_detected_on_a_text_the_teacher_changed_leaves_unless_the_family_corrected_it():
    post = it("synth-n1", ItemType.ANNOUNCEMENT, "Aviso inventado", description="Se anula el control inventado.")
    old = text_hash(
        it("synth-n1", ItemType.ANNOUNCEMENT, "Aviso inventado", description="Examen y control inventados.")
    )
    stale = [exam("synth-n1#exam-1", origin_hash=old), exam("synth-n1#exam-2", "2026-11-12", origin_hash=old)]
    assert sorted(entries(builder([post], stale))) == ["synth-n1"]  # the announcement alone
    # On the new text Claude proposes one exam: the second, of the old text only, does not stay.
    again = entries(builder([post], [exam("synth-n1#exam-1"), stale[1]]))
    assert sorted(again) == ["synth-n1", "synth-n1#exam-1"]
    corrected = entries(builder([post], [stale[0], correction("synth-n1#exam-1", date="2026-11-20")]))
    assert corrected["synth-n1#exam-1"].date == dt.date(2026, 11, 20)  # the family's word stays


def test_an_item_withdrawn_from_classroom_and_what_it_announced_are_out():
    post = it("synth-m1", ItemType.MATERIAL, "Calendario inventado", description="Examen inventado el jueves.")
    kept = homework(due=dt.date(2026, 11, 2), status=ItemStatus.PENDING)
    gone = homework("synth-a2", due=dt.date(2026, 11, 3), status=ItemStatus.PENDING)
    found = entries(builder([post, kept, gone], [exam("synth-m1#exam-1")], withdrawn=["synth-a2", "synth-m1"]))
    assert sorted(found) == ["synth-a1"]


def test_an_item_of_a_class_that_is_not_linked_is_out():
    other = Item("synth-z1", "synth-c9", None, ItemType.ASSIGNMENT, "Ficha inventada", dt.date(2026, 10, 1))
    assert entries(builder([homework(), other])).keys() == {"synth-a1"}


def test_pending_nearest_first_and_undated_last_then_done_newest_first_then_posted():
    items = [
        homework("synth-a1", due=dt.date(2026, 11, 3), status=ItemStatus.PENDING),
        homework("synth-a2", status=ItemStatus.PENDING),  # no date
        homework("synth-a3", due=dt.datetime(2026, 11, 2, 8, 0, tzinfo=MADRID), status=ItemStatus.OVERDUE),
        homework("synth-a4", due=dt.date(2026, 11, 2), status=ItemStatus.PENDING),  # date only: the end of the day
        homework("synth-d1", due=dt.date(2026, 10, 10), status=ItemStatus.RETURNED),
        homework("synth-d2", status=ItemStatus.TURNED_IN),  # no date
        homework("synth-d3", due=dt.date(2026, 10, 20), status=ItemStatus.TURNED_IN_LATE),
        it("synth-p1", ItemType.MATERIAL, "Apuntes inventados", posted=dt.date(2026, 10, 2)),
        it("synth-p2", ItemType.ANNOUNCEMENT, "Aviso inventado", posted=dt.date(2026, 10, 9), description="Aviso."),
    ]
    order = [(e.list, e.item) for e in builder(items).entries()]
    assert order == [
        (AgendaList.PENDING, "synth-a3"),
        (AgendaList.PENDING, "synth-a4"),
        (AgendaList.PENDING, "synth-a1"),
        (AgendaList.PENDING, "synth-a2"),
        (AgendaList.DONE, "synth-d3"),
        (AgendaList.DONE, "synth-d1"),
        (AgendaList.DONE, "synth-d2"),
        (AgendaList.POSTED, "synth-p2"),
        (AgendaList.POSTED, "synth-p1"),
    ]
    md = builder(items).to_markdown()
    assert md.index("## Pendiente") < md.index("## Hecho") < md.index("## Publicado")


def test_dates_are_the_due_exam_or_posting_date():
    found = entries(
        builder(
            [
                homework(due=dt.datetime(2026, 11, 2, 8, 0, tzinfo=MADRID), status=ItemStatus.PENDING),
                it("synth-p1", ItemType.MATERIAL, "Apuntes inventados", posted=dt.date(2026, 10, 2)),
            ]
        )
    )
    assert (found["synth-a1"].date, found["synth-a1"].date_only) == (
        dt.datetime(2026, 11, 2, 8, 0, tzinfo=MADRID),
        False,
    )
    assert (found["synth-p1"].date, found["synth-p1"].date_only, found["synth-p1"].status) == (
        dt.date(2026, 10, 2),
        True,
        None,
    )


@pytest.mark.parametrize("due", [dt.datetime(2026, 11, 2, 8, 0, tzinfo=MADRID), dt.date(2026, 11, 2), None])
def test_the_state_keeps_the_due_date_the_agenda_reads(due: dt.datetime | dt.date | None):
    kept = homework(due=due, status=ItemStatus.PENDING)
    back, _ = item_from_json(item_to_json(kept, None))
    assert back == kept and type(back.due_at) is type(kept.due_at)
    older = {k: v for k, v in item_to_json(kept, None).items() if k != "due_at"}  # a state from before #8
    assert item_from_json(older)[0].due_at is None


def test_classroom_links_carry_no_account_index():
    found = entries(
        builder(
            [
                homework(),
                it("synth-q1", ItemType.QUESTION, "¿Pregunta inventada?"),
                it("synth-p1", ItemType.MATERIAL, "Apuntes inventados"),
                it("synth-n1", ItemType.ANNOUNCEMENT, "Aviso inventado", description="Aviso."),
            ]
        )
    )
    assert {k: e.classroom_link for k, e in found.items()} == {
        "synth-a1": f"https://classroom.google.com/c/{CLASS}/a/synth-a1/details",
        "synth-q1": f"https://classroom.google.com/c/{CLASS}/mc/synth-q1/details",
        "synth-p1": f"https://classroom.google.com/c/{CLASS}/m/synth-p1/details",
        "synth-n1": f"https://classroom.google.com/c/{CLASS}",  # the stream: no post link was measured
    }
    assert "/u/" not in builder([homework()]).to_json()


TOPIC = "2026-2027/FyQ/20261001 - 1. Materia inventada/classroom"


def test_the_folder_is_the_one_holding_the_items_replica():
    replicas = {
        "classroom|synth-a1|synth-s1": {"role": "statement", "path": f"{TOPIC}/20261006 - Ficha/enunciado - f.pdf"},
        "classroom|synth-a1|synth-s2": {"role": "submission", "path": f"{TOPIC}/20261006 - Ficha/submission/r.pdf"},
        "classroom|synth-a1|#description": {"role": "description", "path": f"{TOPIC}/20261006 - Ficha/enunciado.md"},
        "classroom|synth-a2|synth-s3": {"role": "submission", "path": f"{TOPIC}/20261007 - Otra/submission/r.pdf"},
        "classroom|synth-p1|synth-s4": {"role": "material", "path": f"{TOPIC}/20261002 - Apuntes inventados.pdf"},
    }
    post = it("synth-n1", ItemType.ANNOUNCEMENT, "Aviso inventado", description="El examen inventado.")
    found = entries(
        builder(
            [homework(), homework("synth-a2"), it("synth-p1", ItemType.MATERIAL, "Apuntes inventados"), post],
            [exam("synth-n1#exam-1")],
            replicas=replicas,
        )
    )
    assert found["synth-a1"].folder == f"{TOPIC}/20261006 - Ficha"
    assert found["synth-a2"].folder == f"{TOPIC}/20261007 - Otra"  # only the student's files: still its folder
    assert found["synth-p1"].folder == TOPIC  # a one-file material is the file itself
    assert found["synth-n1"].folder == "" and found["synth-n1#exam-1"].folder == ""  # no replica
    by_item = {e["item"]: e for e in json.loads(builder([post]).to_json())["entries"]}
    assert by_item["synth-n1"]["folder"] is None


def every_case() -> AgendaBuilder:
    items = [
        homework("synth-a1", due=dt.date(2026, 11, 3), status=ItemStatus.PENDING),
        homework("synth-a2", due=dt.date(2026, 10, 3), status=ItemStatus.OVERDUE),
        homework("synth-a3", due=dt.date(2026, 10, 4), status=ItemStatus.MISSING_PER_TEACHER),
        homework("synth-a4", status=ItemStatus.TURNED_IN),
        homework("synth-a5", status=ItemStatus.TURNED_IN_LATE),
        homework("synth-a6", status=ItemStatus.RETURNED),
        it("synth-q1", ItemType.QUESTION, "¿Pregunta inventada?", status=ItemStatus.PENDING),
        it("synth-x1", ItemType.ASSIGNMENT, "Examen inventado", due=dt.date(2026, 11, 9)),
        it("synth-p1", ItemType.MATERIAL, "Apuntes inventados"),
        it("synth-n1", ItemType.ANNOUNCEMENT, "Aviso inventado", description="Habrá examen inventado."),
    ]
    decisions = [exam("synth-n1#exam-1", ""), exam("synth-n1#exam-2"), correction("synth-n1#exam-2", date="2026-11-06")]
    return builder(items, decisions)


def test_agenda_md_speaks_spanish_and_never_the_technical_values():
    md = every_case().to_markdown()
    for label in (
        "## Pendiente",
        "## Hecho",
        "## Publicado",
        "· examen ·",
        "· entrega ·",
        "· cuestionario ·",
        "· material ·",
        "· aviso ·",
        "· pendiente ·",
        "· vencida ·",
        "· falta según el profesor ·",
        "· entregada ·",
        "· entregada tarde ·",
        "· devuelta ·",
        "· detectado ·",
        "· corregido ·",
        "sin fecha ·",
        "- [ ] ",
        "- [x] ",
    ):
        assert label in md, label
    readable = re.sub(r"\]\([^)]*\)", "]", md)  # the link targets are URLs and paths, not words
    for value in (
        *(str(s) for s in ItemStatus),
        *(str(c) for c in AgendaCategory if c != AgendaCategory.MATERIAL),  # «material» is Spanish too
        *(str(x) for x in AgendaList),
        "detected",
        "corrected",
        "null",
        "None",
    ):
        assert not re.search(rf"\b{re.escape(value)}\b", readable), value


def test_agenda_md_says_to_open_the_links_with_the_school_account():
    assert "cuenta del colegio" in every_case().to_markdown()


def test_dates_are_shown_as_classroom_shows_them():
    md = builder(
        [
            homework("synth-a1", due=dt.datetime(2026, 11, 2, 8, 0, tzinfo=MADRID), status=ItemStatus.PENDING),
            homework("synth-a2", due=dt.date(2026, 9, 14), status=ItemStatus.RETURNED),
        ]
    ).to_markdown()
    assert "- [ ] 2 nov, 8:00 · FyQ · entrega ·" in md
    assert "- [x] 14 sept · FyQ · entrega ·" in md


def test_agenda_json_follows_the_contract_and_carries_no_timestamp():
    schema = json.loads(SCHEMA.read_text())
    document = json.loads(every_case().to_json())
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    found = validator.iter_errors(document)  # pyright: ignore[reportUnknownMemberType]
    assert [f"{list(e.path)}: {e.message}" for e in found] == []
    assert sorted(document) == sorted(schema["required"])  # every key, and nothing else: no timestamp
    entry_keys = sorted(cast("list[str]", schema["properties"]["entries"]["items"]["required"]))
    assert all(sorted(e) == entry_keys for e in document["entries"]) and document["entries"]
    assert document["school_year"] == "2026-2027" and document["version"] == 1


def test_a_notice_goes_at_the_top_of_agenda_md_and_never_into_agenda_json():
    plain = every_case()
    noticed = replace(plain, notices=("**Aviso**: un aviso inventado.",))
    md = noticed.to_markdown()
    assert md.splitlines()[:4] == ["# Agenda 2026-2027", "", "**Aviso**: un aviso inventado.", ""]
    assert md.replace("**Aviso**: un aviso inventado.\n\n", "", 1) == plain.to_markdown()
    assert noticed.to_json() == plain.to_json()  # agenda.json is the reminders epic's input: entries only


def test_the_same_inputs_give_the_same_bytes(tmp_path: Path):
    base = tmp_path / "base"
    base.mkdir()
    assert every_case().write(base) == ["2026-2027/agenda.json", "2026-2027/agenda.md"]
    stamps = [p.stat().st_mtime_ns for p in sorted((base / "2026-2027").iterdir())]
    assert every_case().write(base) == []  # FR-025: rewritten only if its content changes
    assert [p.stat().st_mtime_ns for p in sorted((base / "2026-2027").iterdir())] == stamps


# --- the sandbox run, through the command ---


@pytest.fixture
def box(tmp_path: Path) -> Iterator[Box]:
    b = Box(tmp_path / "box")
    assert cli(b.home, "sandbox", "prepare").returncode == 0
    b.take()
    yield b
    b.release()


def agenda(box: Box) -> dict[str, dict[str, Any]]:
    document = json.loads((box.base / "2026-2027" / "agenda.json").read_text())
    return {e["item"]: e for e in cast("list[dict[str, Any]]", document["entries"])}


def test_every_sample_detected_exam_proposal_is_in_the_agenda(box: Box):
    first_run(box)
    proposed = [
        d
        for d in json.loads((box.data / "decisions.json").read_text())["decisions"]
        if d["type"] == "detected_exam" and d["state"] != "superseded"
    ]
    found = agenda(box)
    assert proposed and all(found[d["origin"]]["detected"] for d in proposed)  # SC-004a, unconfirmed
    exam_entry = found["synth-30#exam-1"]
    assert (exam_entry["origin"], exam_entry["date"], exam_entry["list"]) == ("synth-30", "2026-11-05", "pending")
    assert exam_entry["classroom_link"] == "https://classroom.google.com/c/synth-1"
    md = (box.base / "2026-2027" / "agenda.md").read_text()
    assert "· examen · El examen del tema 1 inventado será el jueves 5 de noviembre. · detectado ·" in md


def test_an_announcements_entry_gets_its_folder(box: Box):
    first_run(box)
    found = agenda(box)
    folder = found["synth-31"]["folder"]
    assert folder.startswith("2026-2027/FyQ/") and " - aviso - Recordad traer la bata inventada" in folder
    assert (box.base / folder).is_dir()
    assert found["synth-20"]["folder"].endswith("/classroom/20261006 - Ficha inventada de mezclas")


def test_a_familys_correction_prevails_in_the_next_run(box: Box):
    first_run(box)
    fix = ("decisions", "correct", "--student", "sample", "--origin", "synth-30#exam-1", "--date", "2026-11-10")
    assert box(*fix).returncode == 0
    box.apply()
    assert (agenda(box)["synth-30#exam-1"]["date"], agenda(box)["synth-30#exam-1"]["corrected"]) == ("2026-11-10", True)
    next_run(box)
    box.apply()
    assert agenda(box)["synth-30#exam-1"]["date"] == "2026-11-10"


def test_the_agenda_command_writes_only_what_changed(box: Box):
    first_run(box)
    (box.base / "2026-2027" / "agenda.md").unlink()
    done = box("agenda", "--student", "sample")
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == {"written": ["2026-2027/agenda.md"]}
    assert str(box.base) not in done.stderr and "alfabeta: agenda:" in done.stderr
    again = box("agenda", "--student", "sample")
    assert json.loads(again.stdout) == {"written": []} and "sin cambios" in again.stderr


def test_the_agenda_command_needs_the_lock(box: Box):
    done = cli(box.home, "agenda", "--student", "sample")
    assert done.returncode == 1 and '"lock_not_held"' in done.stdout


def test_another_today_rewrites_nothing(box: Box, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    first_run(box)
    monkeypatch.setenv("ALFABETA_RUN", box.run)
    files = sorted((box.base / "2026-2027").glob("agenda.*"))
    stamps = [p.stat().st_mtime_ns for p in files]
    for day in (dt.date(2026, 11, 20), dt.date(2027, 6, 1)):  # after the exam, and near the end of the year
        monkeypatch.setattr(decisions_module, "today", lambda day=day: day)
        assert cli_main.main(["--home", str(box.home), "agenda", "--student", "sample"]) == 0
        assert json.loads(capsys.readouterr().out) == {"written": []}
    assert [p.stat().st_mtime_ns for p in files] == stamps


def test_the_macs_sync_shows_the_owners_session_line_while_it_is_signed_out(box: Box):
    """Spec 005 FR-019: the agenda line comes from the Mac's sync, read from the refresh record."""
    first_run(box)
    record = box.data / "notebook-refresh.json"
    record.write_text(
        json.dumps({"sources": {}, "session": "signed_out", "session_since": "2026-10-28T10:00:00+01:00"})
    )
    assert box("agenda", "--student", "sample").returncode == 0
    md = (box.base / "2026-2027" / "agenda.md").read_text()
    assert md.splitlines()[2] == AGENDA_LINE
    record.write_text(json.dumps({"sources": {}, "session": "ok", "session_since": "2026-10-28T10:15:00+01:00"}))
    again = box("agenda", "--student", "sample")
    assert json.loads(again.stdout) == {"written": ["2026-2027/agenda.md"]}
    assert AGENDA_LINE not in (box.base / "2026-2027" / "agenda.md").read_text()
