"""The family's report of a run (spec 005 T035, FR-013, FR-015, research R8). Every value is invented."""

from __future__ import annotations

import datetime as dt
import io
import json
import re
from dataclasses import replace
from typing import Any

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate

from alfabeta import guardrail
from alfabeta.decisions import Subtopic
from alfabeta.google.drive import DriveError
from alfabeta.notes import report
from alfabeta.notes.model import PhotoState, Usage
from alfabeta.notes.run import run_notes
from alfabeta.notes.state import DriveNotesStateStore
from alfabeta.notes.transcribe import Transcription
from tests.notes_fakes import (
    NOTES,
    TOPIC,
    FixedClock,
    MemoryDrive,
    ScriptedAnswerer,
    ScriptedFeed,
    ScriptedTranscriber,
    deps,
)
from tests.test_notes_run import set_up, state_of

PACK = "Tema 01 para imprimir · Materia inventada.pdf"
GUIDE_TEXT = "La materia se clasifica en sustancias puras y mezclas ZORONGO-GUIA"
QUIZ_TEXT = "Pregunta 1: qué es una disolución ZORONGO-TEST"
PLAN = "0 · Guía de estudio · Empieza aquí"
PLAN_TEXT = "Bloque A, los vídeos: 45 minutos; descanso de 15 minutos ZORONGO-PLAN"
SUMMARY = "Resumen de tus apuntes · Materia inventada"
SUMMARY_TEXT = "Sustancias puras (substantzia puruak): un solo componente ZORONGO-RESUMEN"


def pdf(*pages: list[str]) -> bytes:
    """A PDF with one page per list of paragraphs, as `print_pack.py` prints a pack."""
    out = io.BytesIO()
    style = getSampleStyleSheet()["Normal"]
    story: list[Any] = []
    for i, lines in enumerate(pages):
        if i:
            story.append(PageBreak())
        story += [Paragraph(line, style) for line in lines]
    SimpleDocTemplate(out, pagesize=A4).build(story)
    return out.getvalue()


def pack() -> bytes:
    return pdf(
        ["Tema 01 - Materia inventada", "✎ 3 · Guía de estudio · Materia | en este documento", "▶ 1 · Vídeo"],
        ["1 / 3", "3 · Guía de estudio · Materia inventada", GUIDE_TEXT],
        ["4 · Test 10 preguntas · Materia inventada", QUIZ_TEXT],
    )


def plan_pack(*theory: list[str], plan: tuple[list[str], ...] = ()) -> bytes:
    """A pack printed after #128: the index, the plan «0 · …» (spec 002 FR-015), then the other pieces."""
    return pdf(
        ["Tema 01 - Materia inventada", f"✎ {PLAN} | en este documento", "▶ 1 · Vídeo · Bloque A"],
        ["1 / 7", PLAN, "Nº Pieza Para qué", f"3 · {SUMMARY}", PLAN_TEXT],
        *plan,
        ["2 / 7", "2 · Mapa mental · Materia inventada", "materia - sustancias puras - mezclas"],
        *theory,
        ["3 / 7", f"3 · {SUMMARY}", SUMMARY_TEXT],
        ["4 / 7", "4 · Test 10 preguntas · Materia inventada", QUIZ_TEXT],
    )


def reports(drive: MemoryDrive) -> list[str]:
    """The reports in `reports/`, by name, each decoded."""
    (folder,) = drive.named("reports") or [""]
    return [drive.bodies[f.id].decode() for f in drive.children(folder)] if folder else []


def clean(text: str) -> None:
    """The guardrail's detectors over the report's lines, as SC-008 asks."""
    assert guardrail.scan_lines("Informe.md", report.scan_text(text), []) == []


def test_an_idle_run_writes_no_report():
    drive = MemoryDrive.topic()
    set_up(drive)
    run_notes(deps(drive, ScriptedFeed(drive, [[]]), ScriptedTranscriber()))
    assert reports(drive) == [] and "reported" not in state_of(drive)


def test_a_page_is_reported_in_spanish_under_the_runs_name():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "IMG_0001.jpg", "image/jpeg", b"foto uno")
    set_up(drive)
    run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), ScriptedTranscriber()))
    (folder,) = drive.named("reports")
    [written] = drive.children(folder)
    assert written.name == "Informe 20261027-0900.md"
    text = drive.bodies[written.id].decode()
    assert text.startswith("# Informe de apuntes · 27/10/2026 09:00\n\nEjecución en la nube.\n")
    assert "## Tema 01 - Materia inventada" in text
    assert "- 1 página nueva en el archivo vivo." in text
    assert report.NO_PACK in text  # no printable pack in notebook/: no comparison, said in one line
    assert "- Esta ejecución: 3.000 tokens de entrada y 800 de salida." in text
    assert "- Mes 2026-10: 0,01 USD" in text
    assert "foto-1" not in text and "ap1" not in text and "raiz" not in text  # counts and names, never an id
    clean(text)


def test_the_second_run_with_nothing_new_writes_no_report_and_leaves_the_state_alone():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    set_up(drive)
    feed = ScriptedFeed(drive, [["foto-1"]])
    run_notes(deps(drive, feed, ScriptedTranscriber()))
    before = state_of(drive)
    writes = list(drive.updates) + list(drive.uploads)
    run_notes(deps(drive, feed, ScriptedTranscriber()))
    assert len(reports(drive)) == 1
    assert state_of(drive) == before and (drive.updates + drive.uploads)[len(writes) :] == ["last-run.json"]


def test_a_repeating_failure_is_reported_once_and_its_clearing_once():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    set_up(drive)
    tr = ScriptedTranscriber([Transcription(PhotoState.FAILED, usage=Usage(10, 0))] * 3)
    feed = ScriptedFeed(drive, [["foto-1"]])
    clock = FixedClock()
    run_notes(deps(drive, feed, tr, clock))
    assert len(reports(drive)) == 1 and "1 foto que falló al transcribirse (se reintenta)." in reports(drive)[0]
    for _ in range(2):  # still failing: the records do not change, so no report
        clock.when += dt.timedelta(hours=1)
        run_notes(deps(drive, feed, tr, clock))
    assert len(reports(drive)) == 1
    clock.when += dt.timedelta(hours=1)
    run_notes(deps(drive, feed, tr, clock))  # the fourth call succeeds: the page clears the failure
    assert len(reports(drive)) == 2
    assert "1 página nueva en el archivo vivo." in reports(drive)[1] and "falló" not in reports(drive)[1]


def test_a_spent_budget_is_reported_when_it_starts_and_when_it_clears():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    set_up(drive)
    tr = ScriptedTranscriber([Transcription(PhotoState.BUDGET_WAIT)])
    feed = ScriptedFeed(drive, [["foto-1"]])
    clock = FixedClock()
    run_notes(deps(drive, feed, tr, clock))
    [first] = reports(drive)
    assert f"- Comienza: {report._CONDITIONS['budget']}." in first and "## Avisos" in first
    clock.when += dt.timedelta(hours=2)
    run_notes(deps(drive, feed, tr, clock))  # the same day: nothing retried, nothing reported
    assert len(reports(drive)) == 1
    clock.when += dt.timedelta(days=1)
    run_notes(deps(drive, feed, tr, clock))
    assert len(reports(drive)) == 2
    assert f"- Resuelto: {report._CONDITIONS['budget']}." in reports(drive)[1]
    for text in reports(drive):
        clean(text)


def test_a_missing_living_file_is_said_once_and_its_return_once():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    living = set_up(drive)
    drive.files[living] = replace(drive.files[living], parents=(TOPIC,))  # at the topic's root (#110)
    feed = ScriptedFeed(drive, [["foto-1"]])
    clock = FixedClock()
    run_notes(deps(drive, feed, ScriptedTranscriber(), clock))
    [first] = reports(drive)
    assert "- Comienza: el archivo vivo «Apuntes · Tema 01 - Materia inventada.pdf» no está donde se creó" in first
    assert "1 página transcrita que espera su archivo vivo." in first
    clock.when += dt.timedelta(hours=1)
    run_notes(deps(drive, feed, ScriptedTranscriber(), clock))
    assert len(reports(drive)) == 1
    drive.files[living] = replace(drive.files[living], parents=(NOTES,))  # the family moved it back
    clock.when += dt.timedelta(hours=1)
    run_notes(deps(drive, feed, ScriptedTranscriber(), clock))
    assert len(reports(drive)) == 2
    assert (
        "- Resuelto: el archivo vivo «Apuntes · Tema 01 - Materia inventada.pdf» no está donde se creó"
        in reports(drive)[1]
    )
    assert "1 página nueva en el archivo vivo." in reports(drive)[1]


def test_what_it_adds_compares_the_new_pages_with_the_guide_only_and_pays_into_the_ledger():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    set_up(drive)
    drive.folder("nb1", "notebook", TOPIC)
    drive.put("pack-1", PACK, "application/pdf", pack(), parent="nb1")
    answerer = ScriptedAnswerer()
    run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), ScriptedTranscriber(), answerer=answerer))
    [text] = reports(drive)
    [prompt] = answerer.prompts
    assert (
        "Texto de a" in prompt
        and GUIDE_TEXT in prompt
        and QUIZ_TEXT not in prompt
        and "en este documento" not in prompt
    )
    assert "### Qué aportan los apuntes nuevos" in text
    assert f"Comparadas 1 página nueva con «Guía de estudio · Materia inventada» de «{PACK}»." in text
    assert "- La guía no cubre los métodos de separación de mezclas." in text
    assert report.DECISION in text and "es decisión de la familia" in text
    assert state_of(drive)["spend"] == {"2026-10": {"in": 8000, "out": 1000}}  # 3000+5000, 800+200
    assert "- Esta ejecución: 8.000 tokens de entrada y 1.000 de salida." in text
    clean(text)


def test_what_it_adds_compares_a_post_128_pack_with_its_summary_never_its_plan():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    set_up(drive)
    drive.folder("nb1", "notebook", TOPIC)
    drive.put("pack-1", PACK, "application/pdf", plan_pack(), parent="nb1")
    answerer = ScriptedAnswerer()
    run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), ScriptedTranscriber(), answerer=answerer))
    [prompt] = answerer.prompts
    assert SUMMARY_TEXT in prompt and "ZORONGO-PLAN" not in prompt
    [text] = reports(drive)
    assert f"Comparadas 1 página nueva con «{SUMMARY}» de «{PACK}»." in text
    clean(text)


def test_a_pack_without_a_guide_or_a_refused_budget_skips_the_call_with_a_line():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    set_up(drive)
    drive.folder("nb1", "notebook", TOPIC)
    drive.put("pack-1", PACK, "application/pdf", pdf(["Índice"], ["4 · Test · Materia", QUIZ_TEXT]), parent="nb1")
    answerer = ScriptedAnswerer()
    run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), ScriptedTranscriber(), answerer=answerer))
    assert answerer.prompts == [] and report.NO_GUIDE in reports(drive)[0]

    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    set_up(drive)
    drive.folder("nb1", "notebook", TOPIC)
    drive.put("pack-1", PACK, "application/pdf", pack(), parent="nb1")
    answerer = ScriptedAnswerer([Transcription(PhotoState.BUDGET_WAIT)])
    run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), ScriptedTranscriber(), answerer=answerer))
    [text] = reports(drive)
    assert report.NO_BUDGET in text and f"- Comienza: {report._CONDITIONS['budget']}." in text
    assert state_of(drive)["reported"]["conditions"]["budget"] is True


def test_no_key_is_one_line_and_one_condition():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    set_up(drive)
    run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), None))
    [text] = reports(drive)
    assert f"- Comienza: {report._CONDITIONS['no_key']}." in text and "página nueva" not in text


def test_the_guide_section_is_the_guides_pages_only():
    section = text_of(report.guide_section(pack()))
    assert GUIDE_TEXT in section and QUIZ_TEXT not in section
    assert "en este documento" not in section  # the index's row names the guide but is not it
    assert report.guide_section(pdf(["Índice", "3 · Guía de estudio · X"], ["4 · Test", QUIZ_TEXT])) is None


def text_of(section: tuple[str, str] | None) -> str:
    assert section is not None
    return section[1]


def test_the_plan_is_never_the_section_and_the_summary_stands_in_for_a_missing_guide():
    # Spec 002 FR-015: piece 0 says «Guía de estudio» but holds no theory; the theory is the summary.
    title, text = report.guide_section(plan_pack()) or ("", "")
    assert title == SUMMARY and SUMMARY_TEXT in text
    assert "ZORONGO-PLAN" not in text and QUIZ_TEXT not in text


def test_a_theory_guide_wins_over_the_summary():
    guide = ["2 / 7", "2 · Guía de estudio · Materia inventada", GUIDE_TEXT]
    text = text_of(report.guide_section(plan_pack(guide)))
    assert GUIDE_TEXT in text and SUMMARY_TEXT not in text and "ZORONGO-PLAN" not in text


def test_a_plan_page_whose_table_row_names_a_piece_is_not_that_piece():
    # The plan's table lists every piece by its title: a page of the plan may start with one.
    more = ["2 / 7", f"3 · {SUMMARY} | Para estudiar", "Bloque B, comprobar: 30 minutos ZORONGO-PLAN"]
    text = text_of(report.guide_section(plan_pack(plan=(more,))))
    assert SUMMARY_TEXT in text and "ZORONGO-PLAN" not in text


def test_a_pack_with_only_the_plan_has_no_section():
    assert report.guide_section(pdf(["Índice"], ["1 / 2", PLAN, PLAN_TEXT], ["4 · Test", QUIZ_TEXT])) is None


def test_the_report_name_and_the_pack_name_pass_the_guardrail():
    text = report.report_name(dt.datetime(2026, 10, 28, 16, 5))
    assert text == "Informe 20261028-1605.md"
    assert guardrail.scan_lines("x.md", [(1, text), (2, PACK)], []) == []
    assert re.fullmatch(r"Informe \d{8}-\d{4}\.md", text)


# --- what the independent review of #70 found ------------------------------------------------------


def with_pack(body: bytes | None = None) -> MemoryDrive:
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    set_up(drive)
    drive.folder("nb1", "notebook", TOPIC)
    drive.put("pack-1", PACK, "application/pdf", pack() if body is None else body, parent="nb1")
    return drive


def test_a_damaged_pack_is_one_line_and_the_run_keeps_its_records():
    drive = with_pack(b"%PDF-1.4 roto")
    answerer = ScriptedAnswerer()
    result = run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), ScriptedTranscriber(), answerer=answerer))
    assert result["ok"] and answerer.prompts == []
    assert report.NO_PDF in reports(drive)[0]
    assert state_of(drive)["spend"] == {"2026-10": {"in": 3000, "out": 800}}  # the transcription is kept


def test_a_refused_comparison_holds_the_budget_until_a_call_is_answered_and_then_compares():
    drive = with_pack()
    answerer = ScriptedAnswerer([Transcription(PhotoState.BUDGET_WAIT)])
    clock = FixedClock()
    run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), ScriptedTranscriber(), clock, answerer=answerer))
    [first] = reports(drive)
    assert report.NO_BUDGET in first and f"- Comienza: {report._CONDITIONS['budget']}." in first
    # A change that no Claude call answers (a format Claude does not take): the budget is not said to clear.
    drive.put("foto-3", "c.heic", "image/heic", b"c")
    clock.when += dt.timedelta(hours=1)
    unsupported = ScriptedTranscriber([Transcription(PhotoState.UNSUPPORTED)])
    run_notes(deps(drive, ScriptedFeed(drive, [["foto-3"]]), unsupported, clock, answerer=answerer))
    assert len(reports(drive)) == 2 and "1 foto en un formato no admitido." in reports(drive)[1]
    assert all("Resuelto" not in text for text in reports(drive))
    assert len(answerer.prompts) == 1  # the waiting comparison waits for an answered call
    # The next photo is answered: the budget clears once and the waiting page is compared with the new one.
    drive.put("foto-2", "b.jpg", "image/jpeg", b"b")
    clock.when += dt.timedelta(days=1)
    run_notes(deps(drive, ScriptedFeed(drive, [["foto-2"]]), ScriptedTranscriber(), clock, answerer=answerer))
    last = reports(drive)[-1]
    assert f"- Resuelto: {report._CONDITIONS['budget']}." in last
    assert "Comparadas 2 páginas nuevas" in last and "Texto de a" in answerer.prompts[-1]
    assert "compare" in state_of(drive)["reported"] and state_of(drive)["reported"]["compare"] == {}


def test_a_page_waiting_for_setup_is_compared_once_not_again_when_it_reaches_its_file():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    drive.folder("nb1", "notebook", TOPIC)
    drive.put("pack-1", PACK, "application/pdf", pack(), parent="nb1")
    answerer = ScriptedAnswerer()
    clock = FixedClock()
    run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), ScriptedTranscriber(), clock, answerer=answerer))
    [first] = reports(drive)
    assert first.count("el tema espera a que se cree su cuaderno") == 1  # once per topic, not per file
    set_up(drive)
    clock.when += dt.timedelta(hours=1)
    run_notes(deps(drive, ScriptedFeed(drive, [[]]), ScriptedTranscriber(), clock, answerer=answerer))
    second = reports(drive)[-1]
    assert "1 página nueva en el archivo vivo." in second
    assert second.count("Resuelto: el tema espera") == 1
    assert len(answerer.prompts) == 1  # the page was compared when it was transcribed, never again


def test_a_drive_write_failure_is_reported_once_and_its_clearing_once():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    set_up(drive)
    clock = FixedClock()
    run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), ScriptedTranscriber(), clock))
    drive.put("foto-2", "b.jpg", "image/jpeg", b"b")
    upload = drive.upload

    def refuse(*args: Any, **kwargs: Any) -> Any:
        if str(args[1]).endswith("transcripción.md"):
            raise DriveError("Drive API returned 500", 500)
        return upload(*args, **kwargs)

    drive.upload = refuse  # type: ignore[method-assign]
    for _ in range(2):
        clock.when += dt.timedelta(hours=1)
        run_notes(deps(drive, ScriptedFeed(drive, [["foto-2"]]), ScriptedTranscriber(), clock))
    assert len(reports(drive)) == 2 and f"- Comienza: {report._CONDITIONS['drive_write']}." in reports(drive)[1]
    drive.upload = upload  # type: ignore[method-assign]
    clock.when += dt.timedelta(hours=1)
    run_notes(deps(drive, ScriptedFeed(drive, [["foto-2"]]), ScriptedTranscriber(), clock))
    assert len(reports(drive)) == 3 and f"- Resuelto: {report._CONDITIONS['drive_write']}." in reports(drive)[2]


def test_records_older_than_the_report_are_its_baseline_not_news():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    set_up(drive)
    clock = FixedClock()
    run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), ScriptedTranscriber(), clock))
    store = DriveNotesStateStore(drive)
    state = store.load()
    del state["reported"]  # what a state.json written before this module looks like
    store.save(state)
    drive.put("foto-2", "b.jpg", "image/jpeg", b"b")
    drive.folder("nb1", "notebook", TOPIC)
    drive.put("pack-1", PACK, "application/pdf", pack(), parent="nb1")
    answerer = ScriptedAnswerer()
    clock.when += dt.timedelta(hours=1)
    run_notes(deps(drive, ScriptedFeed(drive, [["foto-2"]]), ScriptedTranscriber(), clock, answerer=answerer))
    last = reports(drive)[-1]
    assert "- 1 página nueva en el archivo vivo." in last  # foto-2 only
    assert "Texto de b" in answerer.prompts[0] and "Texto de a" not in answerer.prompts[0]


# --- what the re-review of #70 found ---------------------------------------------------------------


def test_a_waiting_comparison_of_a_topic_that_left_drive_is_dropped_not_a_crash():
    drive = with_pack()
    drive.folder("ap2", "notes", "t9")
    drive.folder("t9", "20261101 - Tema 09 - Otro", "fyq")
    answerer = ScriptedAnswerer([Transcription(PhotoState.BUDGET_WAIT)])
    clock = FixedClock()
    run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), ScriptedTranscriber(), clock, answerer=answerer))
    assert state_of(drive)["reported"]["compare"] == {TOPIC: ["foto-1"]}
    for fid in [f for f, item in drive.files.items() if TOPIC in item.parents or f == TOPIC]:
        del drive.files[fid]  # the topic folder and everything under it moved out of alfabeta/
    drive.put("foto-2", "b.jpg", "image/jpeg", b"b", parent="ap2")
    clock.when += dt.timedelta(days=1)
    feed = ScriptedFeed(drive, [["foto-2"]])
    result = run_notes(deps(drive, feed, ScriptedTranscriber(), clock, answerer=answerer))
    assert result["ok"] and state_of(drive)["reported"]["compare"] == {}


def test_the_budget_does_not_flap_while_a_refused_photo_still_waits():
    drive = MemoryDrive.topic()
    for n in (1, 2):
        drive.put(f"foto-{n}", f"{n}.jpg", "image/jpeg", str(n).encode())
    set_up(drive)
    clock = FixedClock()
    refused = ScriptedTranscriber([Transcription(PhotoState.BUDGET_WAIT)])
    run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), refused, clock))
    assert f"- Comienza: {report._CONDITIONS['budget']}." in reports(drive)[0]
    clock.when += dt.timedelta(hours=1)  # the limit is raised: the same day, another photo is answered
    run_notes(deps(drive, ScriptedFeed(drive, [["foto-2"]]), ScriptedTranscriber(), clock))
    clock.when += dt.timedelta(hours=1)
    run_notes(deps(drive, ScriptedFeed(drive, [[]]), ScriptedTranscriber(), clock))
    said = "".join(reports(drive))
    assert said.count(f"Comienza: {report._CONDITIONS['budget']}") == 1
    assert said.count(f"Resuelto: {report._CONDITIONS['budget']}") == 0  # foto-1 still waits for its day


@pytest.mark.parametrize("error", [NotImplementedError("filtro"), KeyError("/Root"), RecursionError()])
def test_any_error_of_the_pdf_parser_is_one_line(monkeypatch: pytest.MonkeyPatch, error: BaseException):
    def broken(pdf: bytes) -> str | None:
        raise error

    monkeypatch.setattr(report, "guide_section", broken)
    drive = with_pack()
    result = run_notes(
        deps(drive, ScriptedFeed(drive, [["foto-1"]]), ScriptedTranscriber(), answerer=ScriptedAnswerer())
    )
    assert result["ok"] and report.NO_PDF in reports(drive)[0]


def test_a_subtopic_s_printable_pack_is_found_by_its_name():
    names = (
        "Tema 02B para imprimir · Lección inventada.pdf",
        "Tema 02 para imprimir · x.pdf",
        "Tema 02b para imprimir · x.pdf",
    )
    assert [bool(report._PRINTABLE.match(n)) for n in names] == [True, True, False]  # pyright: ignore[reportPrivateUsage]


# --- each new page's lesson, and what the textbook states otherwise (spec 005 FR-020) ---------------------

BOOK_MD = "# Tema 1\n\n## Lección 1: Materia\n\nTexto.\n\n## Lección 2: Mezclas\n\nLas mezclas se separan.\n\n## Lección 3: Gases\n"


def with_book(drive: MemoryDrive) -> None:
    drive.folder("sb", "sciencebits", TOPIC)
    drive.put("libro-md", "Tema01_ES.md", "text/markdown", BOOK_MD.encode(), parent="sb")
    drive.put("libro-pdf", "Tema01_ES.pdf", "application/pdf", b"%PDF", parent="sb")


def lessons_answer(pages: list[dict[str, Any]], facts: list[dict[str, Any]] | None = None) -> Transcription:
    body = json.dumps({"pages": pages, "facts": facts or []}, ensure_ascii=False)
    return Transcription(PhotoState.TRANSCRIBED, f"```json\n{body}\n```", Usage(1000, 100))


def lessons_run(drive: MemoryDrive, answer: Transcription, split: list[Subtopic] | None = None) -> tuple[str, str]:
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    set_up(drive)
    with_book(drive)
    answerer = ScriptedAnswerer([answer])

    def held(subject: str, number: str) -> list[Subtopic]:
        return (split or []) if (subject, number) == ("FyQ", "Tema 01") else []

    made = replace(
        deps(drive, ScriptedFeed(drive, [["foto-1"]]), ScriptedTranscriber(), answerer=answerer), subtopics=held
    )
    run_notes(made)
    [text] = reports(drive)
    [prompt] = answerer.prompts  # no pack: the lessons call is the only one
    return text, prompt


def test_each_new_page_gets_its_textbook_lesson():
    text, prompt = lessons_run(MemoryDrive.topic(), lessons_answer([{"page": "a.jpg", "lesson": 2}]))
    assert "1: Materia\n2: Mezclas\n3: Gases" in prompt and "Las mezclas se separan." in prompt
    assert '<page name="a.jpg">' in prompt and "Texto de a" in prompt
    assert "### Lección de cada página" in text and "- «a.jpg»: lección 2, «Mezclas»." in text
    assert "### Lo que el libro dice de otra forma" not in text
    clean(text)


@pytest.mark.parametrize(
    ("lesson", "said"),
    [
        (
            2,
            "- «a.jpg»: lección 2, «Mezclas»; es del subtema Tema 01B, no de esta carpeta: moverla es decisión de la familia.",
        ),
        (3, "- «a.jpg»: lección 3, «Gases»; ningún subtema la tiene: se propone uno (spec 002 FR-044)."),
        (1, "- «a.jpg»: lección 1, «Materia»."),
        (None, "- «a.jpg»: ninguna lección del libro la trata."),
    ],
)
def test_a_page_of_a_split_topic_says_which_subtopic_its_lesson_is_in(lesson: int | None, said: str):
    split = [Subtopic("A", "Materia", (1,)), Subtopic("B", "Mezclas", (2,))]
    drive = MemoryDrive.topic()
    drive.files[TOPIC] = replace(drive.files[TOPIC], name="20260915 - Tema 01A - Materia")
    text, _ = lessons_run(drive, lessons_answer([{"page": "a.jpg", "lesson": lesson}]), split)
    assert said in text


def test_a_fact_the_textbook_states_otherwise_is_a_correction_or_a_question():
    facts = [
        {"page": "a.jpg", "notes": "las mezclas no se separan", "book": "Las mezclas se separan.", "insists": False},
        {"page": "a.jpg", "notes": "el gas pesa nada", "book": "Los gases tienen masa.", "insists": True},
    ]
    text, _ = lessons_run(MemoryDrive.topic(), lessons_answer([{"page": "a.jpg", "lesson": 2}], facts))
    assert "### Lo que el libro dice de otra forma" in text
    assert (
        "- «a.jpg»: los apuntes dicen «las mezclas no se separan»; el libro, «Las mezclas se separan.». El material"
        in text
    )
    assert "- Pregunta: «a.jpg»: los apuntes dicen «el gas pesa nada»" in text and "¿se corrige?" in text


def test_an_answer_that_is_not_json_says_so_in_one_line():
    text, _ = lessons_run(MemoryDrive.topic(), Transcription(PhotoState.TRANSCRIBED, "no sé", Usage(10, 1)))
    assert report.NO_LESSONS in text


def test_a_topic_without_a_textbook_has_no_lessons_section():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    set_up(drive)
    answerer = ScriptedAnswerer()
    run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), ScriptedTranscriber(), answerer=answerer))
    [text] = reports(drive)
    assert "Lección de cada página" not in text and answerer.prompts == []
