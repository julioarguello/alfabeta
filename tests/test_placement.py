"""Where each item goes (spec 001 T027, FR-012…FR-015c). Every name and id is invented."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

import pytest

from alfabeta.model import (
    Attachment,
    AttachmentKind,
    AttachmentRole,
    Decision,
    DecisionState,
    DecisionType,
    Grading,
    GradingState,
    Item,
    ItemType,
    ReplicaRole,
    Subject,
)
from alfabeta.placement import Placer, Target, book_topics, summary

if TYPE_CHECKING:
    from pathlib import Path

WITH_BOOK = Subject("FiQui", "Física inventada", "sciencebits", "Fisika eta Kimika")
NO_BOOK = Subject("Lengua", "Lengua inventada")
OCT = dt.date(2026, 10, 14)
BOOK = "Tema 02 - Los gases"
ROOT = "2026-2027/FiQui"


def file(name: str, ident: str = "synth-f1", role: AttachmentRole = AttachmentRole.MATERIAL) -> Attachment:
    return Attachment(ident, AttachmentKind.FILE, name, role)


def link(name: str = "Vídeo", ident: str = "synth-l1") -> Attachment:
    return Attachment(ident, AttachmentKind.VIDEO, name, AttachmentRole.MATERIAL)


def item(
    kind: ItemType = ItemType.MATERIAL,
    *,
    ident: str = "synth-i1",
    topic: str | None = "synth-t1",
    posted: dt.date = OCT,
    title: str = "Ficha de gases",
    attachments: tuple[Attachment, ...] = (),
    description: str = "",
    submission: tuple[Attachment, ...] = (),
    grading: Grading | None = None,
) -> Item:
    return Item(
        ident,
        "synth-c1",
        topic,
        kind,
        title,
        posted,
        attachments=attachments,
        description=description,
        submission=submission,
        grading=grading,
    )


def match(kind: DecisionType, origin: str, state: DecisionState, topic: str = BOOK) -> Decision:
    return Decision(kind, origin, {"topic": topic}, "invented", state, OCT)


def paths(targets: list[Target]) -> list[str]:
    return [t.path for t in targets]


def test_confirmed_match_goes_to_the_book_topic_dated_by_its_first_item():
    placer = Placer(
        "2026-2027", WITH_BOOK, decisions=[match(DecisionType.TOPIC_MATCH, "synth-t1", DecisionState.CONFIRMED)]
    )
    one = file("Ficha.pdf")
    assert paths(placer.place(item(attachments=(one,)), "Gasak")) == [
        f"{ROOT}/20261014 - {BOOK}/classroom/20261014 - Ficha de gases.pdf"
    ]


def test_an_existing_folder_is_reused_whatever_its_date_and_keeps_it():
    placer = Placer(
        "2026-2027",
        WITH_BOOK,
        existing_folders=[f"20261001 - {BOOK}"],
        decisions=[match(DecisionType.TOPIC_MATCH, "synth-t1", DecisionState.CONFIRMED)],
    )
    later = placer.place(item(posted=OCT, ident="synth-i1"), "Gasak")
    earlier = placer.place(item(posted=dt.date(2026, 9, 20), ident="synth-i2", title="Otra"), "Gasak")
    assert all(p.startswith(f"{ROOT}/20261001 - {BOOK}/") for p in paths(later) + paths(earlier))


def test_a_new_folder_keeps_the_date_of_the_first_item_placed():
    placer = Placer("2026-2027", NO_BOOK)
    first = placer.place(item(posted=OCT, ident="synth-i1"), "Comentario de texto")
    second = placer.place(item(posted=dt.date(2026, 10, 2), ident="synth-i2", title="Otra"), "Comentario de texto")
    assert {p.split("/")[2] for p in paths(first) + paths(second)} == {"20261014 - Comentario de texto"}


def test_teacher_topic_without_book_has_no_tema():
    [target] = Placer("2026-2027", NO_BOOK).place(item(), "Repaso: la oración")
    assert target.path.startswith("2026-2027/Lengua/20261014 - Repaso- la oración/classroom/")
    assert "Tema" not in target.path


@pytest.mark.parametrize("state", [None, DecisionState.PROPOSED, DecisionState.REJECTED])
def test_unconfirmed_or_rejected_match_keeps_the_teacher_folder(state: DecisionState | None):
    decisions = [] if state is None else [match(DecisionType.TOPIC_MATCH, "synth-t1", state)]
    [target] = Placer("2026-2027", WITH_BOOK, decisions=decisions).place(item(), "Gasak")
    assert target.path.startswith(f"{ROOT}/20261014 - Gasak/classroom/")


def test_confirming_the_match_moves_the_replicas():
    before = Placer(
        "2026-2027", WITH_BOOK, decisions=[match(DecisionType.TOPIC_MATCH, "synth-t1", DecisionState.PROPOSED)]
    )
    after = Placer(
        "2026-2027", WITH_BOOK, decisions=[match(DecisionType.TOPIC_MATCH, "synth-t1", DecisionState.CONFIRMED)]
    )
    one = item()
    assert paths(before.place(one, "Gasak")) != paths(after.place(one, "Gasak"))
    assert BOOK in paths(after.place(one, "Gasak"))[0]


def test_item_match_wins_over_its_topic():
    decisions = [
        match(DecisionType.TOPIC_MATCH, "synth-t1", DecisionState.CONFIRMED),
        match(DecisionType.ITEM_MATCH, "synth-i1", DecisionState.CONFIRMED, topic="Tema 03 - Disoluciones"),
    ]
    [target] = Placer("2026-2027", WITH_BOOK, decisions=decisions).place(item(), "Gasak")
    assert "/20261014 - Tema 03 - Disoluciones/" in target.path


def test_no_topic_goes_to_sin_tema_one_per_subject_and_never_a_month_folder():
    placer = Placer("2026-2027", NO_BOOK)
    a = placer.place(item(topic=None, ident="synth-i1"))
    b = placer.place(item(topic=None, ident="synth-i2", title="Otra", posted=dt.date(2026, 11, 3)))
    folders = {p.split("/")[2] for p in paths(a) + paths(b)}
    assert folders == {"20261014 - Sin tema"}
    assert not any(
        part[:7].count("-") == 1 and part[:4].isdigit() and len(part) == 7
        for p in paths(a + b)
        for part in p.split("/")
    )


def test_material_forms():
    placer = Placer("2026-2027", NO_BOOK)
    single = placer.place(item(ident="synth-a", attachments=(file("Apuntes.pdf"),)), "T")
    assert paths(single) == ["2026-2027/Lengua/20261014 - T/classroom/20261014 - Ficha de gases.pdf"]
    several = placer.place(
        item(ident="synth-b", title="Vídeos y apuntes", attachments=(file("Apuntes.pdf"), link()), description="Leed"),
        "T",
    )
    folder = "2026-2027/Lengua/20261014 - T/classroom/20261014 - Vídeos y apuntes"
    assert sorted(paths(several)) == sorted(
        [f"{folder}/Apuntes.pdf", f"{folder}/enlaces.md", f"{folder}/descripcion.md"]
    )
    text_only = placer.place(item(ident="synth-c", title="Aviso de lectura", description="Leed el tema"), "T")
    assert paths(text_only) == ["2026-2027/Lengua/20261014 - T/classroom/20261014 - Aviso de lectura.md"]
    only_links = placer.place(item(ident="synth-d", title="Enlaces", attachments=(link(),), description="Mirad"), "T")
    folder = "2026-2027/Lengua/20261014 - T/classroom/20261014 - Enlaces"
    assert sorted(paths(only_links)) == [f"{folder}/descripcion.md", f"{folder}/enlaces.md"]


def test_assignment_is_always_a_folder_with_prefixed_files_and_the_submission_in_entrega():
    statement = file("Problemas.pdf", "synth-s1", AttachmentRole.STATEMENT)
    handed = file("Respuestas.pdf", "synth-s2", AttachmentRole.SUBMISSION)
    one = item(
        ItemType.ASSIGNMENT,
        title="Problemas tema 2",
        attachments=(statement,),
        description="Haced los ejercicios",
        submission=(handed,),
        grading=Grading(GradingState.RETURNED, grade="8"),
    )
    targets = Placer("2026-2027", NO_BOOK).place(one, "T")
    folder = "2026-2027/Lengua/20261014 - T/classroom/20261014 - Problemas tema 2"
    assert {(t.role, t.path) for t in targets} == {
        (ReplicaRole.STATEMENT, f"{folder}/enunciado - Problemas.pdf"),
        (ReplicaRole.DESCRIPTION, f"{folder}/enunciado.md"),
        (ReplicaRole.SUBMISSION, f"{folder}/entrega/Respuestas.pdf"),
        (ReplicaRole.GRADING, f"{folder}/correccion.md"),
    }
    question = Placer("2026-2027", NO_BOOK).place(
        item(ItemType.QUESTION, title="¿Qué es un gas?", description="Responde"), "T"
    )
    assert paths(question) == ["2026-2027/Lengua/20261014 - T/classroom/20261014 - ¿Qué es un gas?/enunciado.md"]


def test_announcement_note_or_folder_in_sin_tema():
    text = "Cambio de fecha del examen: será el jueves 22 en la segunda hora, traed calculadora"
    placer = Placer("2026-2027", NO_BOOK)
    [note] = placer.place(item(ItemType.ANNOUNCEMENT, ident="synth-n1", topic="synth-t1", description=text))
    expected = "20261014 - aviso - " + summary(text)
    assert note.path == f"2026-2027/Lengua/20261014 - Sin tema/classroom/{expected}.md"
    assert len(summary(text)) <= 60 and not summary(text).endswith(" ")
    with_file = placer.place(
        item(ItemType.ANNOUNCEMENT, ident="synth-n2", description="Horario", attachments=(file("Horario.pdf"),))
    )
    folder = "2026-2027/Lengua/20261014 - Sin tema/classroom/20261014 - aviso - Horario"
    assert sorted(paths(with_file)) == [f"{folder}/20261014 - aviso - Horario.md", f"{folder}/Horario.pdf"]


def test_names_are_valid_short_and_unique():
    placer = Placer("2026-2027", NO_BOOK)
    long_title = "Ejercicio " + "ñ" * 200 + ": parte 1/2"
    [target] = placer.place(item(title=long_title, attachments=(file("x.pdf"),)), "T")
    name = target.path.rsplit("/", 1)[1]
    assert len(name.encode()) <= 255 and name.endswith(".pdf") and "/" not in name and ":" not in name
    a = placer.place(item(ident="synth-u1", title="Repetido", description="uno"), "T")
    b = placer.place(item(ident="synth-u2", title="Repetido", description="dos"), "T")
    again = placer.place(item(ident="synth-u1", title="Repetido", description="uno"), "T")
    assert paths(a) != paths(b) and paths(again) == paths(a)
    assert paths(b)[0].endswith("20261014 - Repetido (2).md")


def test_book_topics_are_folders_holding_the_book_subfolder(tmp_path: Path):
    for name, has_book in [
        ("20261001 - Tema 01 - Mezclas", True),
        ("Tema 02 - Gases", True),
        ("20261005 - Tema 03 - Sin libro", False),
        ("20261006 - Repaso", True),
    ]:
        (tmp_path / name).mkdir()
        if has_book:
            (tmp_path / name / "sciencebits").mkdir()
    assert book_topics(tmp_path, "sciencebits") == ["Tema 01 - Mezclas", "Tema 02 - Gases"]
    assert book_topics(tmp_path, "") == []


def test_two_files_of_one_assignment_with_one_name_are_numbered():
    # Measured 2026-10-28: one submission held four photos with the same name (FR-015c).
    photos = tuple(file("foto.jpg", f"synth-p{i}", AttachmentRole.SUBMISSION) for i in range(1, 4))
    sheets = tuple(file("ficha.pdf", f"synth-e{i}", AttachmentRole.STATEMENT) for i in range(1, 3))
    one = item(ItemType.ASSIGNMENT, title="Fotos", attachments=sheets, submission=photos)
    folder = "2026-2027/Lengua/20261014 - T/classroom/20261014 - Fotos"
    expected = [
        f"{folder}/enunciado - ficha.pdf",
        f"{folder}/enunciado - ficha (2).pdf",
        f"{folder}/entrega/foto.jpg",
        f"{folder}/entrega/foto (2).jpg",
        f"{folder}/entrega/foto (3).jpg",
    ]
    assert paths(Placer("2026-2027", NO_BOOK).place(one, "T")) == expected
    assert paths(Placer("2026-2027", NO_BOOK).place(one, "T")) == expected  # the same on every run
