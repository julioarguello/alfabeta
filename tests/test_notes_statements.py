"""A problem solved in the notes is matched to its statement (spec 005 T048, FR-016d, SC-009). All invented."""

from __future__ import annotations

import datetime as dt
import itertools
import json
from typing import Any

import pytest

from alfabeta import guardrail
from alfabeta.google.drive import DriveFile
from alfabeta.notes import report, statements
from alfabeta.notes.changes import WRITTEN, DriveChangeFeed
from alfabeta.notes.model import PhotoState, Usage
from alfabeta.notes.run import known, run_notes
from alfabeta.notes.state import DriveNotesStateStore
from alfabeta.notes.transcribe import Transcription
from tests.notes_fakes import (
    CLASSROOM,
    MADRID,
    NOTES,
    TOPIC,
    FixedClock,
    MemoryDrive,
    ScriptedAnswerer,
    ScriptedFeed,
    ScriptedTranscriber,
    deps,
)
from tests.test_notes_report import reports
from tests.test_notes_run import set_up, state_of

PHOTO = "foto-1"
PAGE = "## Ejercicios\n\n3) m = 2 kg, a = 5 m/s²\nF = m·a = 10 N\n\nFin de la clase\n"
ANCHOR = "3) m = 2 kg, a = 5 m/s²"
STATEMENT = "Calcula la fuerza que actúa sobre un cuerpo de dos kilos que acelera a cinco metros"
BOOK_ES = f"# Tema 1\n\n## Lección 1: Fuerzas\n\nEjercicio 3. {STATEMENT} por segundo.\n"
BOOK_EU = "# 1. gaia\n\n## Ikasgaia 1: Indarrak\n\n3. ariketa. Kalkulatu bi kiloko gorputz baten indarra.\n"
PROBLEM = {"number": "3", "data": "m = 2 kg, a = 5 m/s²", "result": "10 N", "anchor": ANCHOR}
QUOTE = "Calcula la fuerza que actúa sobre un cuerpo"
EARLY = dt.datetime(2026, 10, 27, 9, 0, tzinfo=MADRID)
_MINUTES = itertools.count(1)  # each later run writes its own report, the same day


def later() -> FixedClock:
    return FixedClock(EARLY + dt.timedelta(minutes=next(_MINUTES)))


def listed(*problems: dict[str, Any]) -> Transcription:
    """What the listing call answers."""
    return Transcription(PhotoState.TRANSCRIBED, json.dumps({"problems": list(problems)}), Usage(2000, 100))


def found(*entries: dict[str, Any]) -> Transcription:
    """What the search call answers, fenced as Claude may."""
    body = json.dumps({"problems": list(entries)}, ensure_ascii=False)
    return Transcription(PhotoState.TRANSCRIBED, f"```json\n{body}\n```", Usage(40000, 300))


def candidate(source: str = "S1", exercise: str = "Ejercicio 3", quote: str = QUOTE) -> dict[str, str]:
    return {"source": source, "exercise": exercise, "quote": quote, "why": "el número y el resultado coinciden"}


def with_book(drive: MemoryDrive, *, languages: bool = True) -> None:
    drive.folder("sb", "sciencebits", TOPIC)
    drive.put("libro-es", "Tema01_ES.md", "text/markdown", BOOK_ES.encode(), parent="sb")
    drive.put("libro-pdf", "Tema01_ES.pdf", "application/pdf", b"%PDF", parent="sb")
    if languages:
        drive.put("libro-eu", "Tema01_EU.md", "text/markdown", BOOK_EU.encode(), parent="sb")


def page_drive() -> MemoryDrive:
    drive = MemoryDrive.topic()
    drive.put(PHOTO, "a.jpg", "image/jpeg", b"a")
    set_up(drive)
    return drive


def transcriber() -> ScriptedTranscriber:
    return ScriptedTranscriber([Transcription(PhotoState.TRANSCRIBED, PAGE, Usage(3000, 800))])


def first_run(drive: MemoryDrive, *script: Transcription) -> ScriptedAnswerer:
    answerer = ScriptedAnswerer(statements=list(script))
    run_notes(deps(drive, ScriptedFeed(drive, [[PHOTO]]), transcriber(), answerer=answerer))
    return answerer


def later_run(drive: MemoryDrive, *script: Transcription, when: dt.datetime | None = None) -> ScriptedAnswerer:
    answerer = ScriptedAnswerer(statements=list(script))
    clock = FixedClock(when) if when else later()
    run_notes(deps(drive, ScriptedFeed(drive, [[]]), ScriptedTranscriber(), answerer=answerer, clock=clock))
    return answerer


def markdown_of(drive: MemoryDrive) -> str:
    return drive.bodies[state_of(drive)["pages"][PHOTO]["markdown_id"]].decode()


def block_of(drive: MemoryDrive) -> dict[str, Any]:
    return state_of(drive)["pages"][PHOTO]["statements"]


def section_of(text: str) -> str:
    """The report's lines about the statements."""
    return text.split(statements.HEADING, 1)[1].split("\n## ", 1)[0] if statements.HEADING in text else ""


# --- a match, beside its problem ------------------------------------------------------------------------


def test_a_match_is_written_beside_its_problem_with_its_source_and_evidence():
    drive = page_drive()
    with_book(drive)
    first_run(drive, listed(PROBLEM), found({"problem": "P1", "candidates": [candidate()]}))
    lines = markdown_of(drive).splitlines()
    beside = lines[lines.index(ANCHOR) + 1]
    assert beside.startswith("[enunciado del problema 3: «Tema01_ES.md», Ejercicio 3")
    assert QUOTE in beside and "el número y el resultado coinciden" in beside
    # The transcription's own text is all still there, in its order.
    assert statements.strip_statements(markdown_of(drive)) == PAGE
    block = block_of(drive)
    assert block["state"] == statements.SETTLED
    assert block["problems"][0]["status"] == statements.MATCHED
    assert block["problems"][0]["number"] == "3" and block["problems"][0]["result"] == "10 N"


def test_the_living_file_and_the_pages_pdf_built_in_that_pass_hold_the_match():
    drive = page_drive()
    with_book(drive)
    first_run(drive, listed(PROBLEM), found({"problem": "P1", "candidates": [candidate()]}))
    pdf_id = state_of(drive)["pages"][PHOTO]["pdf_id"]
    assert b"[enunciado del problema 3" in drive.bodies[pdf_id]
    # The living notes file is rebuilt in the same pass, from the record that holds the line.
    assert state_of(drive)["files"][PHOTO]["state"] == PhotoState.IN_LIVING_FILE
    assert "[enunciado del problema 3" in state_of(drive)["pages"][PHOTO]["markdown"]


def test_the_report_says_what_matched_and_on_what_evidence():
    drive = page_drive()
    with_book(drive)
    first_run(drive, listed(PROBLEM), found({"problem": "P1", "candidates": [candidate()]}))
    [text] = reports(drive)
    said = section_of(text)
    assert "«a.jpg», problema 3" in said and "«Tema01_ES.md», Ejercicio 3" in said
    assert "el número y el resultado coinciden" in said
    assert guardrail.scan_lines("Informe.md", report.scan_text(text), []) == []


def test_every_language_captured_and_the_classroom_material_are_searched_but_never_the_students_work():
    drive = page_drive()
    with_book(drive)
    drive.folder(CLASSROOM, "classroom", TOPIC)
    drive.folder("item", "20261001 - Ficha de fuerzas", CLASSROOM)
    drive.put("ficha", "enunciado.md", "text/markdown", b"Ficha ZORONGO-FICHA: problema 3", parent="item")
    drive.put("mia", "entrega - resuelto.md", "text/markdown", b"ZORONGO-ENTREGA", parent="item")
    drive.put("nota", "correccion.md", "text/markdown", b"ZORONGO-NOTA", parent="item")
    answerer = ScriptedAnswerer(statements=[listed(PROBLEM), found({"problem": "P1", "candidates": []})])
    feed = ScriptedFeed(drive, [[PHOTO]])
    state = DriveNotesStateStore(drive)
    loaded = state.load()
    loaded["files"] = {"item": {"kind": "classroom_item", "topic": TOPIC, "version": "v", "state": "seen"}}
    state.save(loaded)
    run_notes(deps(drive, feed, transcriber(), answerer=answerer))
    listing, search = answerer.statement_prompts
    assert STATEMENT not in listing and "ZORONGO-FICHA" not in listing  # the list costs a page, no source
    assert "Tema01_ES.md" in search and "Tema01_EU.md" in search and "Ikasgaia 1" in search
    assert "ZORONGO-FICHA" in search and "2026-10-01" in search
    assert "ZORONGO-ENTREGA" not in search and "ZORONGO-NOTA" not in search
    assert search.index("Tema01_ES.md") < search.index("ZORONGO-FICHA")  # the textbook first


# --- a doubtful match -----------------------------------------------------------------------------------


def test_two_exercises_that_fit_equally_are_both_named_as_doubtful():
    drive = page_drive()
    with_book(drive)
    other = candidate("S1", "Ejercicio 9", "Ejercicio 3")
    first_run(drive, listed(PROBLEM), found({"problem": "P1", "candidates": [candidate(), other]}))
    line = next(x for x in markdown_of(drive).splitlines() if x.startswith("[enunciado"))
    assert line.startswith("[enunciado dudoso del problema 3:")
    assert "Ejercicio 3" in line and "Ejercicio 9" in line
    assert block_of(drive)["problems"][0]["status"] == statements.DOUBTFUL
    said = section_of(reports(drive)[0])
    assert "Ejercicio 3" in said and "Ejercicio 9" in said and "dudoso" in said


# --- a statement no source holds ------------------------------------------------------------------------


def test_a_statement_no_source_holds_is_missing_and_names_what_was_searched():
    drive = page_drive()
    with_book(drive)
    first_run(drive, listed(PROBLEM), found({"problem": "P1", "candidates": []}))
    block = block_of(drive)
    assert block["problems"][0]["status"] == statements.MISSING and block["problems"][0]["candidates"] == []
    said = section_of(reports(drive)[0])
    assert "«a.jpg», problema 3" in said and "m = 2 kg" in said and "10 N" in said
    assert "Tema01_ES.md" in said and "Tema01_EU.md" in said
    assert "no se escribe" in said.lower()


def test_a_quote_the_source_does_not_hold_cannot_reach_the_transcription():
    """What makes SC-009 mechanical: a statement rebuilt from the working has no source to be found in."""
    drive = page_drive()
    with_book(drive)
    invented = candidate(quote="Un cuerpo de dos kilos acelera, halla la fuerza resultante aplicada")
    first_run(drive, listed(PROBLEM), found({"problem": "P1", "candidates": [invented]}))
    assert block_of(drive)["problems"][0]["status"] == statements.MISSING
    assert "halla la fuerza" not in markdown_of(drive) and "halla la fuerza" not in reports(drive)[0]


@pytest.mark.parametrize(
    "bad",
    [
        {"source": "S9", "exercise": "Ejercicio 3", "quote": QUOTE, "why": "x"},  # no such source
        {"source": "S1", "exercise": "Ejercicio 3", "quote": "3", "why": "x"},  # too short to prove anything
        {"source": "S1", "quote": QUOTE, "why": "x"},  # names no exercise
        "Ejercicio 3",  # not an object
    ],
)
def test_a_candidate_that_proves_nothing_is_dropped(bad: Any):
    drive = page_drive()
    with_book(drive)
    first_run(drive, listed(PROBLEM), found({"problem": "P1", "candidates": [bad]}))
    assert block_of(drive)["problems"][0]["status"] == statements.MISSING


def test_a_problem_the_search_answer_leaves_out_is_missing_not_lost():
    drive = page_drive()
    with_book(drive)
    second = {**PROBLEM, "number": "4", "anchor": "Fin de la clase"}
    first_run(drive, listed(PROBLEM, second), found({"problem": "P2", "candidates": [candidate()]}))
    by_number = {p["number"]: p["status"] for p in block_of(drive)["problems"]}
    assert by_number == {"3": statements.MISSING, "4": statements.MATCHED}


def test_a_quote_survives_the_line_breaks_and_hyphens_of_an_extracted_pdf():
    assert statements.holds("Calcula la fuer-\nza que actúa\n  sobre un cuerpo", "Calcula la fuerza que actúa sobre")


def test_a_topic_with_no_source_lists_its_problems_and_says_so_without_a_search():
    drive = page_drive()
    answerer = first_run(drive, listed(PROBLEM))
    assert len(answerer.statement_prompts) == 1
    assert block_of(drive)["problems"][0]["status"] == statements.MISSING
    assert statements.NO_SOURCES in section_of(reports(drive)[0])


def test_material_that_cannot_be_read_is_named_never_claimed_as_searched():
    drive = page_drive()
    with_book(drive)
    drive.folder(CLASSROOM, "classroom", TOPIC)
    drive.put("hoja", "20261001 - hoja.jpg", "image/jpeg", b"foto", parent=CLASSROOM)
    state = DriveNotesStateStore(drive)
    loaded = state.load()
    loaded["files"] = {"hoja": {"kind": "classroom_item", "topic": TOPIC, "version": "v", "state": "seen"}}
    state.save(loaded)
    answerer = first_run(drive, listed(PROBLEM), found({"problem": "P1", "candidates": []}))
    assert "hoja.jpg" not in answerer.statement_prompts[1]
    said = section_of(reports(drive)[0])
    assert "Sin poder leer" in said and "hoja.jpg" in said
    assert block_of(drive)["searched"]["hoja"]["unread"]


def test_a_source_beyond_the_size_a_call_takes_is_named_as_cut():
    long_book = "Ejercicio 3. " + STATEMENT + " " + "relleno " * 20000
    drive = page_drive()
    drive.folder("sb", "sciencebits", TOPIC)
    drive.put("libro-es", "Tema01_ES.md", "text/markdown", long_book.encode(), parent="sb")
    answerer = first_run(drive, listed(PROBLEM), found({"problem": "P1", "candidates": []}))
    assert len(answerer.statement_prompts[1]) < statements.MAX_SEARCH_CHARS + 10_000
    assert block_of(drive)["searched"]["libro-es"]["unread"] == statements.CUT
    assert statements.CUT in section_of(reports(drive)[0])


def test_a_page_of_theory_pays_for_the_listing_and_never_for_the_sources():
    drive = page_drive()
    with_book(drive)
    answerer = first_run(drive, listed())
    assert len(answerer.statement_prompts) == 1
    assert block_of(drive)["state"] == statements.SETTLED and block_of(drive)["problems"] == []
    assert markdown_of(drive) == PAGE
    assert section_of(reports(drive)[0]) == ""


# --- what a later run does ------------------------------------------------------------------------------


def test_a_second_run_with_nothing_new_calls_reads_and_writes_nothing():
    drive = page_drive()
    with_book(drive)
    first_run(drive, listed(PROBLEM), found({"problem": "P1", "candidates": []}))
    before = (dict(drive.revisions), len(reports(drive)))
    drive.downloads.clear()
    answerer = later_run(drive)
    assert answerer.statement_prompts == []
    assert "libro-es" not in drive.downloads
    changed = {f for f, n in drive.revisions.items() if before[0].get(f) != n}
    assert changed <= set(drive.named("last-run.json"))  # the run's own log, as SC-004 allows
    assert len(reports(drive)) == before[1]


def test_a_statement_that_arrives_later_is_searched_for_once_in_that_source_only():
    drive = page_drive()
    with_book(drive)
    first_run(drive, listed(PROBLEM), found({"problem": "P1", "candidates": []}))
    drive.put(
        "hoja", "Tema01_EN.md", "text/markdown", b"Exercise 3. Find the force on a body of two kilos.", parent="sb"
    )
    answerer = later_run(
        drive, found({"problem": "P1", "candidates": [candidate(quote="Find the force on a body of two")]})
    )
    [search] = answerer.statement_prompts
    assert "Tema01_EN.md" in search and "Tema01_ES.md" not in search  # what was searched is not paid twice
    assert block_of(drive)["problems"][0]["status"] == statements.MATCHED
    line = next(x for x in markdown_of(drive).splitlines() if x.startswith("[enunciado"))
    assert "Tema01_EN.md" in line
    assert "Tema01_EN.md" in section_of(reports(drive)[-1])
    # The match is settled: the same source, or another one, is not asked again.
    drive.put("mas", "Tema01_FR.md", "text/markdown", b"Exercice 3.", parent="sb")
    assert later_run(drive).statement_prompts == []


def test_a_repeated_search_that_finds_nothing_writes_nothing_and_reports_nothing():
    drive = page_drive()
    with_book(drive)
    first_run(drive, listed(PROBLEM), found({"problem": "P1", "candidates": []}))
    written = drive.revisions[state_of(drive)["pages"][PHOTO]["markdown_id"]]
    count = len(reports(drive))
    drive.put("hoja", "Tema01_EN.md", "text/markdown", b"Nothing to see.", parent="sb")
    answerer = later_run(drive, found({"problem": "P1", "candidates": []}))
    assert len(answerer.statement_prompts) == 1
    assert drive.revisions[state_of(drive)["pages"][PHOTO]["markdown_id"]] == written
    assert len(reports(drive)) == count
    assert "hoja" in block_of(drive)["searched"]
    assert later_run(drive).statement_prompts == []  # recorded: not paid for again


def test_a_changed_source_is_searched_again():
    drive = page_drive()
    with_book(drive)
    first_run(drive, listed(PROBLEM), found({"problem": "P1", "candidates": []}))
    drive.put("libro-eu", "Tema01_EU.md", "text/markdown", b"3. ariketa berria", parent="sb")
    [search] = later_run(drive, found({"problem": "P1", "candidates": []})).statement_prompts
    assert "Tema01_EU.md" in search and "Tema01_ES.md" not in search


def test_a_doubtful_match_is_not_searched_again():
    drive = page_drive()
    with_book(drive)
    both = [candidate(), candidate("S1", "Ejercicio 9", "Ejercicio 3")]
    first_run(drive, listed(PROBLEM), found({"problem": "P1", "candidates": both}))
    drive.put("hoja", "Tema01_EN.md", "text/markdown", b"Exercise 3.", parent="sb")
    assert later_run(drive).statement_prompts == []


def test_a_page_recorded_before_this_was_built_is_not_searched_on_its_own():
    drive = page_drive()
    with_book(drive)
    first_run(drive, listed())
    store = DriveNotesStateStore(drive)
    loaded = store.load()
    del loaded["pages"][PHOTO]["statements"]
    store.save(loaded)
    assert later_run(drive).statement_prompts == []


def test_a_new_version_of_the_photo_starts_again():
    drive = page_drive()
    with_book(drive)
    first_run(drive, listed(PROBLEM), found({"problem": "P1", "candidates": [candidate()]}))
    drive.put(PHOTO, "a.jpg", "image/jpeg", b"a2")
    answerer = ScriptedAnswerer(statements=[listed()])
    run_notes(deps(drive, ScriptedFeed(drive, [[PHOTO]]), transcriber(), answerer=answerer))
    assert len(answerer.statement_prompts) == 1
    assert block_of(drive)["problems"] == []
    assert "[enunciado" not in state_of(drive)["pages"][PHOTO]["markdown"]


def test_a_stopped_passs_markdown_is_recovered_without_its_lines():
    """A pass that wrote the page and stopped: the next one pays for no transcription, and searches anew."""
    drive = page_drive()
    with_book(drive)
    version = drive.files[PHOTO].version
    written = f"{PAGE}[enunciado del problema 3: «Viejo.md», Ejercicio 1]\n"
    drive.put("md-viejo", "a.jpg · transcripción.md", "text/markdown", written.encode())
    drive.files["md-viejo"] = DriveFile(
        "md-viejo",
        "a.jpg · transcripción.md",
        "text/markdown",
        (NOTES,),
        md5=drive.files["md-viejo"].md5,
        properties=(("alfabeta_for", PHOTO), ("alfabeta_role", "markdown"), ("alfabeta_version", version)),
    )
    made = ScriptedTranscriber()
    answerer = ScriptedAnswerer(statements=[listed()])
    run_notes(deps(drive, ScriptedFeed(drive, [[PHOTO]]), made, answerer=answerer))
    assert made.calls == 0
    assert "[enunciado" not in state_of(drive)["pages"][PHOTO]["markdown"]


# --- the student's mark ---------------------------------------------------------------------------------


def checked_page(drive: MemoryDrive) -> str:
    """A page the student marked: its record says so and its PDF carries the name."""
    with_book(drive)
    first_run(drive, listed(PROBLEM), found({"problem": "P1", "candidates": []}))
    store = DriveNotesStateStore(drive)
    loaded = store.load()
    loaded["pages"][PHOTO]["review"] = "checked"
    store.save(loaded)
    pdf_id = loaded["pages"][PHOTO]["pdf_id"]
    drive.files[pdf_id] = _renamed(drive.files[pdf_id], "a.jpg · transcripción (revisada).pdf")
    return pdf_id


def _renamed(file: DriveFile, name: str) -> DriveFile:
    return DriveFile(
        file.id, name, file.mime_type, file.parents, file.size, file.md5, file.modified, False, file.properties
    )


def test_writing_a_match_keeps_the_students_mark_and_its_pdfs_name():
    drive = page_drive()
    pdf_id = checked_page(drive)
    drive.put("hoja", "Tema01_EN.md", "text/markdown", b"Exercise 3. Find the force on a body of two.", parent="sb")
    later_run(drive, found({"problem": "P1", "candidates": [candidate(quote="Find the force on a body of two")]}))
    record = state_of(drive)["pages"][PHOTO]
    assert "[enunciado del problema 3" in record["markdown"]
    assert record["review"] == "checked"
    assert drive.files[pdf_id].name == "a.jpg · transcripción (revisada).pdf"
    assert b"[enunciado del problema 3" in drive.bodies[pdf_id]
    # A mark the feed has not delivered yet is still seen: the recorded name is the one before it.
    assert state_of(drive)["files"][pdf_id]["name"] == "a.jpg · transcripción.pdf"


def test_the_feed_reads_alfabetas_write_as_an_echo_never_as_a_correction():
    drive = page_drive()
    with_book(drive)
    first_run(drive, listed(PROBLEM), found({"problem": "P1", "candidates": [candidate()]}))
    record = state_of(drive)
    md_id = record["pages"][PHOTO]["markdown_id"]
    assert record["files"][md_id]["version"] == drive.files[md_id].version
    assert record["pages"][PHOTO]["markdown_version"] == drive.files[md_id].version
    drive.touch(md_id)
    result = DriveChangeFeed(drive).read("c0", known(record))
    assert result.corrections == []


def test_a_write_the_pass_could_not_record_is_still_an_echo():
    """The pass stopped between the write and the save: `alfabeta_written` recognises it."""
    drive = page_drive()
    with_book(drive)
    first_run(drive, listed(PROBLEM), found({"problem": "P1", "candidates": [candidate()]}))
    record = state_of(drive)
    md_id = record["pages"][PHOTO]["markdown_id"]
    assert drive.files[md_id].prop(WRITTEN) == drive.files[md_id].version
    record["files"][md_id]["version"] = "lo-de-antes"
    drive.touch(md_id)
    assert DriveChangeFeed(drive).read("c0", known(record)).corrections == []


def test_a_write_drive_refused_is_done_by_the_next_run_and_paid_for_once():
    drive = page_drive()
    with_book(drive)
    first_run(drive, listed(PROBLEM), found({"problem": "P1", "candidates": []}))
    md_id = state_of(drive)["pages"][PHOTO]["markdown_id"]
    drive.put("hoja", "Tema01_EN.md", "text/markdown", b"Exercise 3. Find the force on a body of two.", parent="sb")
    drive.unreadable.add(PHOTO)  # the PDF cannot be drawn: neither file is written
    later_run(drive, found({"problem": "P1", "candidates": [candidate(quote="Find the force on a body of two")]}))
    assert "Tema01_EN.md" not in drive.bodies[md_id].decode()
    assert block_of(drive)[statements.UNWRITTEN] is True
    drive.unreadable.clear()
    assert later_run(drive).statement_prompts == []
    assert "Tema01_EN.md" in drive.bodies[md_id].decode()
    assert statements.UNWRITTEN not in block_of(drive)


def test_a_search_answer_of_another_shape_is_unusable_never_a_missing_statement():
    drive = page_drive()
    with_book(drive)
    first_run(drive, listed(PROBLEM), Transcription(PhotoState.TRANSCRIBED, '{"otra": 1}', Usage(100, 10)))
    assert block_of(drive)["state"] == statements.LISTED and block_of(drive)["tries"] == 1


def test_the_same_exercise_said_twice_is_not_a_doubt():
    drive = page_drive()
    with_book(drive)
    first_run(drive, listed(PROBLEM), found({"problem": "P1", "candidates": [candidate(), candidate()]}))
    assert block_of(drive)["problems"][0]["status"] == statements.MATCHED


def test_the_familys_edit_of_the_markdown_is_never_written_over():
    drive = page_drive()
    with_book(drive)
    first_run(drive, listed(PROBLEM), found({"problem": "P1", "candidates": []}))
    md_id = state_of(drive)["pages"][PHOTO]["markdown_id"]
    properties = drive.files[md_id].properties
    edited = "Texto corregido por la familia\n"
    drive.put(md_id, drive.files[md_id].name, "text/markdown", edited.encode())
    drive.files[md_id] = DriveFile(
        md_id, drive.files[md_id].name, "text/markdown", (NOTES,), md5=drive.files[md_id].md5, properties=properties
    )
    drive.put("hoja", "Tema01_EN.md", "text/markdown", b"Exercise 3. Find the force on a body of two.", parent="sb")
    later_run(drive, found({"problem": "P1", "candidates": [candidate(quote="Find the force on a body of two")]}))
    assert drive.bodies[md_id].decode() == edited
    assert "[enunciado del problema 3" in state_of(drive)["pages"][PHOTO]["markdown"]  # the living file holds it
    assert block_of(drive)["edited"] is True
    assert statements.EDITED in section_of(reports(drive)[-1])
    # The family's edit stays visible to the feed as the correction it is.
    drive.touch(md_id)
    assert [c.file_id for c in DriveChangeFeed(drive).read("c0", known(state_of(drive))).corrections] == [md_id]


# --- what may stop it -----------------------------------------------------------------------------------


def test_with_no_key_the_pages_wait_and_the_report_says_it_once():
    drive = page_drive()
    with_book(drive)
    run_notes(deps(drive, ScriptedFeed(drive, [[PHOTO]]), transcriber()))
    assert block_of(drive)["state"] == statements.PENDING
    assert statements.WAITING in section_of(reports(drive)[0])
    count = len(reports(drive))
    run_notes(deps(drive, ScriptedFeed(drive, [[]]), ScriptedTranscriber(), clock=later()))
    assert len(reports(drive)) == count


def test_a_refused_budget_waits_for_another_day_and_then_finishes():
    drive = page_drive()
    with_book(drive)
    refused = Transcription(PhotoState.BUDGET_WAIT)
    first_run(drive, listed(PROBLEM), refused)
    assert block_of(drive)["state"] == statements.LISTED
    assert state_of(drive)["reported"]["conditions"]["budget"] is True
    assert later_run(drive).statement_prompts == []  # the same day: not asked again
    tomorrow = EARLY + dt.timedelta(days=1)
    later_run(drive, found({"problem": "P1", "candidates": [candidate()]}), when=tomorrow)
    assert block_of(drive)["problems"][0]["status"] == statements.MATCHED


def test_a_refusal_stops_every_other_call_of_the_pass():
    drive = page_drive()
    with_book(drive)
    answerer = ScriptedAnswerer(statements=[Transcription(PhotoState.BUDGET_WAIT)])
    run_notes(deps(drive, ScriptedFeed(drive, [[PHOTO]]), transcriber(), answerer=answerer))
    assert len(answerer.statement_prompts) == 1 and answerer.prompts == []


def test_every_call_goes_into_the_months_ledger():
    drive = page_drive()
    with_book(drive)
    first_run(drive, listed(PROBLEM), found({"problem": "P1", "candidates": []}))
    # The transcription, the listing, the search, and the report's lessons call of the fake's default.
    assert state_of(drive)["spend"]["2026-10"] == {"in": 3000 + 2000 + 40000 + 5000, "out": 800 + 100 + 300 + 200}


def test_a_drive_failure_is_not_a_missing_statement():
    drive = page_drive()
    with_book(drive)
    drive.unreadable.add("libro-es")
    answerer = first_run(drive, listed(PROBLEM))
    assert len(answerer.statement_prompts) == 1  # the listing, and no search over half the sources
    assert block_of(drive)["state"] == statements.LISTED
    said = section_of(reports(drive)[0])
    assert statements.WAITING in said and "problema 3" not in said
    drive.unreadable.clear()
    later_run(drive, found({"problem": "P1", "candidates": [candidate()]}))
    assert block_of(drive)["problems"][0]["status"] == statements.MATCHED


def test_a_listing_claude_cannot_answer_is_given_up_after_three_paid_tries():
    drive = page_drive()
    useless = Transcription(PhotoState.TRANSCRIBED, "no es JSON", Usage(100, 10))
    first_run(drive, useless)
    assert block_of(drive)["state"] == statements.PENDING
    later_run(drive, useless)
    later_run(drive, useless)
    assert block_of(drive)["state"] == statements.GIVEN_UP
    assert statements.GAVE_UP in section_of(reports(drive)[-1])
    assert later_run(drive).statement_prompts == []


def test_a_search_claude_cannot_answer_leaves_its_problems_missing_after_three_paid_tries():
    drive = page_drive()
    with_book(drive)
    useless = Transcription(PhotoState.TRANSCRIBED, "no es JSON", Usage(100, 10))
    first_run(drive, listed(PROBLEM), useless)
    assert block_of(drive)["state"] == statements.LISTED
    later_run(drive, useless)
    later_run(drive, useless)
    block = block_of(drive)
    assert block["state"] == statements.SETTLED and block["problems"][0]["status"] == statements.MISSING
    assert block["searched"]["libro-es"]["unread"] == statements.NO_ANSWER
    assert later_run(drive).statement_prompts == []


def test_an_answer_not_paid_for_is_retried_without_counting():
    drive = page_drive()
    first_run(drive, Transcription(PhotoState.FAILED))
    assert block_of(drive)["tries"] == 0


def test_the_reports_other_calls_read_the_notes_without_the_lines():
    drive = page_drive()
    with_book(drive)
    answerer = first_run(drive, listed(PROBLEM), found({"problem": "P1", "candidates": [candidate()]}))
    [lessons] = answerer.prompts  # no pack: the lessons call
    assert ANCHOR in lessons and "[enunciado" not in lessons


# --- the text --------------------------------------------------------------------------------------------


def test_a_line_whose_anchor_is_gone_goes_at_the_end_of_the_page():
    missing: dict[str, Any] = {"number": "7", "anchor": "no está", "status": statements.MISSING, "candidates": []}
    written = statements.with_statements(PAGE, [missing])
    assert written.startswith(PAGE)
    assert written.splitlines()[-1].startswith("[enunciado del problema 7")
    assert statements.strip_statements(written) == PAGE


def test_an_anchor_prefers_the_whole_line_to_a_line_that_merely_holds_it():
    page = "## Tema 3\n\n3\nx  =  1\n"
    problem: dict[str, Any] = {"number": "3", "anchor": "3", "status": statements.MISSING, "candidates": []}
    assert statements.with_statements(page, [problem]).splitlines()[3].startswith("[enunciado")
    spaced: dict[str, Any] = {"number": "4", "anchor": "x = 1", "status": statements.MISSING, "candidates": []}
    assert statements.with_statements(page, [spaced]).splitlines()[4].startswith("[enunciado")


def test_writing_the_lines_twice_is_writing_them_once():
    problem: dict[str, Any] = {**PROBLEM, "status": statements.MISSING, "candidates": []}
    once = statements.with_statements(PAGE, [problem])
    assert statements.with_statements(once, [problem]) == once


def test_a_problem_not_searched_yet_writes_no_line():
    assert statements.with_statements(PAGE, [PROBLEM]) == PAGE


def test_a_problem_without_a_number_is_said_by_its_data():
    problem: dict[str, Any] = {
        "number": None,
        "data": "x = 1",
        "anchor": "no está",
        "status": statements.MISSING,
        "candidates": [],
    }
    assert "problema sin número" in statements.with_statements(PAGE, [problem])
