"""One pass of the notes, every port faked (spec 005 T018, T019, T029). Every value is invented."""

from __future__ import annotations

import ast
import datetime as dt
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from alfabeta.notes.changes import DriveChangeFeed
from alfabeta.notes.model import PhotoState, Usage
from alfabeta.notes.run import COUNTS, adopted_section, run_notes, topic_name
from alfabeta.notes.state import STATE, ConcurrentWriteError, DriveNotesStateStore
from alfabeta.notes.transcribe import Transcription
from tests.notes_fakes import (
    CLASSROOM,
    CLASSROOM_0,
    CLASSROOM_2,
    NO_TOPIC,
    NOTES,
    TOPIC,
    TOPIC_2,
    FixedClock,
    MemoryDrive,
    ScriptedFeed,
    ScriptedTranscriber,
    deps,
)

ROOT = Path(__file__).resolve().parents[1]


def state_of(drive: MemoryDrive) -> dict[str, Any]:
    (fid,) = drive.named(STATE)
    return json.loads(drive.bodies[fid])


def set_up(drive: MemoryDrive) -> str:
    """What `notebook setup` leaves: a notes living file in the topic's `notes/`, recorded."""
    living = drive.put("vivo-1", "Apuntes · Tema 01 - Materia inventada.pdf", "application/pdf", b"vacio")
    store = DriveNotesStateStore(drive)
    state = store.load()
    state.setdefault("topics", {})[TOPIC] = {
        "name": "Tema 01 - Materia inventada",
        "living": {"notes": {"file_id": living.id, "source_id": "fuente-1", "built_md5": None, "pages": 0}},
    }
    store.save(state)
    return living.id


def test_one_photo_becomes_one_page_next_to_it():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "IMG_0001.jpg", "image/jpeg", b"foto uno")
    living = set_up(drive)
    tr = ScriptedTranscriber()
    report = run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), tr))
    assert report["topics"] == [{"topic": 0, **dict.fromkeys(COUNTS, 0), "pages_added": 1}]
    assert tr.calls == 1
    (md,) = drive.named("IMG_0001.jpg · transcripción.md")
    assert len(drive.named("IMG_0001.jpg · transcripción.pdf")) == 1
    assert drive.files[md].parents == ("ap1",) and drive.files[md].prop("alfabeta_for") == "foto-1"
    assert drive.bodies[md].decode().startswith("## Página")
    assert drive.bodies[living] == b"notes:Tema 01 - Materia inventada:foto-1/automatic"
    state = state_of(drive)
    assert state["files"]["foto-1"]["state"] == "in_living_file"
    assert state["pages"]["foto-1"]["order"] == 1
    assert state["spend"] == {"2026-10": {"in": 3000, "out": 800}}
    assert report["spend"] == pytest.approx(0.014)


def test_a_second_pass_with_nothing_new_writes_only_the_run_log():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "IMG_0001.jpg", "image/jpeg", b"foto uno")
    set_up(drive)
    feed = ScriptedFeed(drive, [["foto-1"]])
    run_notes(deps(drive, feed, ScriptedTranscriber()))
    writes = list(drive.updates)
    report = run_notes(deps(drive, feed, ScriptedTranscriber()))
    assert drive.updates[len(writes) :] == ["last-run.json"]  # SC-004: state.json untouched
    assert feed.cursors == [None, "c1"]
    assert report["topics"] == []


def test_the_same_photo_twice_is_one_page_and_a_duplicate():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "IMG_0001.jpg", "image/jpeg", b"misma foto")
    drive.put("foto-2", "IMG_0001 copia.jpg", "image/jpeg", b"misma foto")
    tr = ScriptedTranscriber()
    report = run_notes(deps(drive, ScriptedFeed(drive, [["foto-1", "foto-2"]]), tr))
    assert (tr.calls, report["topics"][0]["pages_added"], report["topics"][0]["duplicates"]) == (1, 1, 1)
    assert state_of(drive)["files"]["foto-2"]["state"] == "duplicate"


def test_tema_01_form_is_adopted_with_no_claude_call():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "pagina1.jpg", "image/jpeg", b"uno")
    drive.put("foto-2", "pagina 2.jpg", "image/jpeg", b"dos")
    text = "# Apuntes\n\n## Página 1\n\n![](pagina1.jpg)\n\nTexto PRIMERO\n\n## Página 2\n\n![foto](pagina%202.jpg)\n\nTexto SEGUNDO\n"
    drive.put("md-1", "apuntes.md", "text/markdown", text.encode())
    tr = ScriptedTranscriber()
    report = run_notes(deps(drive, ScriptedFeed(drive, [["md-1", "foto-1", "foto-2"]]), tr))
    assert tr.calls == 0
    assert report["topics"][0]["pages_added"] == 2
    pages = state_of(drive)["pages"]
    assert "PRIMERO" in pages["foto-1"]["markdown"] and "SEGUNDO" not in pages["foto-1"]["markdown"]
    assert pages["foto-2"]["source"] == "adopted"


def test_a_crash_after_the_upload_is_recovered_without_a_second_call_or_file():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "IMG_0001.jpg", "image/jpeg", b"foto uno")
    tr = ScriptedTranscriber()
    crashing = deps(drive, ScriptedFeed(drive, [["foto-1"]]), tr)

    def crash(state: object) -> bool:
        raise RuntimeError("the container stopped")

    crashing.store.save = crash  # type: ignore[method-assign]
    with pytest.raises(RuntimeError):
        run_notes(crashing)
    assert tr.calls == 1 and not drive.named(STATE)
    report = run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), tr))  # the same changes again
    assert tr.calls == 1
    assert len(drive.named("IMG_0001.jpg · transcripción.md")) == 1
    assert report["topics"][0]["pages_added"] == 1


def test_two_overlapping_passes_leave_one_transcription_per_photo():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "IMG_0001.jpg", "image/jpeg", b"foto uno")
    tr = ScriptedTranscriber()
    late = deps(drive, ScriptedFeed(drive, [["foto-1"]]), tr)
    late.store.load()  # it read the records before the other pass wrote them
    run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), tr))
    stale = late.store

    def stale_load() -> dict[str, Any]:
        return {}

    stale.load = stale_load  # type: ignore[method-assign]
    with pytest.raises(ConcurrentWriteError):
        run_notes(late)
    assert tr.calls == 1
    assert len(drive.named("IMG_0001.jpg · transcripción.md")) == 1
    assert len(drive.named("IMG_0001.jpg · transcripción.pdf")) == 1


def test_a_topic_waiting_for_setup_gets_no_living_file():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "IMG_0001.jpg", "image/jpeg", b"foto uno")
    report = run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), ScriptedTranscriber()))
    assert report["topics"][0]["waiting_setup"] == 1
    assert not [n for n in drive.uploads if n.startswith(("Apuntes ·", "Classroom ·"))]
    assert state_of(drive)["files"]["foto-1"]["state"] == "transcribed"


def test_a_living_file_over_the_warning_is_reported():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    drive.put("foto-2", "b.jpg", "image/jpeg", b"b")
    set_up(drive)
    report = run_notes(deps(drive, ScriptedFeed(drive, [["foto-1", "foto-2"]]), ScriptedTranscriber(), warn_pages=4))
    assert report["topics"][0]["over_page_count"] == 1  # 1 + 2 x 2 = 5 pages


def test_a_missing_living_file_is_reported_never_recreated():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    living = set_up(drive)
    del drive.files[living]
    report = run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), ScriptedTranscriber()))
    assert report["topics"][0]["missing_living_files"] == 1
    assert not drive.named("Apuntes · Tema 01 - Materia inventada.pdf")


def test_a_living_file_at_the_topics_root_is_reported_and_left_alone():
    # Where living files sat until 2026-10-28 (#110); only the family moves one into notes/.
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    living = set_up(drive)
    drive.files[living] = replace(drive.files[living], parents=(TOPIC,))
    report = run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), ScriptedTranscriber()))
    assert report["topics"][0]["missing_living_files"] == 1
    assert drive.bodies[living] == b"vacio" and drive.named("Apuntes · Tema 01 - Materia inventada.pdf") == [living]
    assert state_of(drive)["topics"][TOPIC]["living"]["notes"]["health"] == "missing"
    # Moved into notes/ by the family: found again, healthy, and still the only one.
    drive.files[living] = replace(drive.files[living], parents=(NOTES,))
    assert run_notes(deps(drive, ScriptedFeed(drive, [[]]), ScriptedTranscriber()))["topics"] == []
    state = state_of(drive)
    assert state["topics"][TOPIC]["living"]["notes"]["health"] == "ok"
    # The page transcribed while it was missing is in it now.
    assert drive.bodies[living] == b"notes:Tema 01 - Materia inventada:foto-1/automatic"
    assert state["files"]["foto-1"]["state"] == "in_living_file"


def test_a_spent_budget_waits_until_the_next_day():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    tr = ScriptedTranscriber([Transcription(PhotoState.BUDGET_WAIT)])
    clock = FixedClock()
    report = run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), tr, clock))
    assert (report["budget_wait"], state_of(drive)["files"]["foto-1"]["state"]) == (1, "budget_wait")
    clock.when += dt.timedelta(hours=2)
    run_notes(deps(drive, ScriptedFeed(drive, []), tr, clock))
    assert tr.calls == 1  # the same day: not retried
    clock.when += dt.timedelta(days=1)
    run_notes(deps(drive, ScriptedFeed(drive, []), tr, clock))
    assert tr.calls == 2 and state_of(drive)["files"]["foto-1"]["state"] == "transcribed"


def test_a_failure_is_retried_three_times_then_final():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    tr = ScriptedTranscriber([Transcription(PhotoState.FAILED, usage=Usage(10, 0))] * 4)
    feed = ScriptedFeed(drive, [["foto-1"]])
    report: dict[str, Any] = {}
    for _ in range(5):
        report = run_notes(deps(drive, feed, tr))
    assert tr.calls == 4
    assert state_of(drive)["files"]["foto-1"]["state"] == "failed_final"
    assert report["ok"]


def test_no_key_leaves_the_photo_waiting():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    report = run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), None))
    assert report["no_key"] and state_of(drive)["files"]["foto-1"]["state"] == "seen"


def test_a_failed_write_keeps_the_cursor():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    run_notes(deps(drive, ScriptedFeed(drive, []), ScriptedTranscriber()))  # a first run: cursor c1
    drive.put("foto-2", "b.jpg", "image/jpeg", b"b")
    failing = deps(drive, ScriptedFeed(drive, [["foto-2"]]), ScriptedTranscriber())
    upload = drive.upload

    def refuse(*args: object, **kwargs: object):
        if str(args[1]).endswith("transcripción.md"):
            from alfabeta.google.drive import DriveError

            raise DriveError("Drive API returned 500", 500)
        return upload(*args, **kwargs)  # type: ignore[arg-type]

    drive.upload = refuse  # type: ignore[method-assign]
    report = run_notes(failing)
    assert not report["ok"]
    (log,) = drive.named("last-run.json")
    assert json.loads(drive.bodies[log])["page_token"] == "c1"


def test_the_pass_calls_no_study_pack_generation():
    tree = ast.parse((ROOT / "src" / "alfabeta" / "notes" / "run.py").read_text())
    imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert imported, "the sweep found no imports to mean anything"
    assert not {m for m in imported if "study" in m or "sources" in m or "nlm" in m}


def test_helpers():
    assert topic_name("20260915 - Tema 01 - Materia") == "Tema 01 - Materia"
    assert topic_name("No topic") == "No topic"
    assert adopted_section("## A\n\n![](x.jpg)\n", "y.jpg") is None


def test_a_failed_photo_whose_copy_got_a_page_becomes_a_duplicate_not_a_crash():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"misma")
    tr = ScriptedTranscriber([Transcription(PhotoState.FAILED)] * 2)
    run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), tr))  # foto-1 fails
    drive.put("foto-2", "a copia.jpg", "image/jpeg", b"misma")
    run_notes(deps(drive, ScriptedFeed(drive, [["foto-2"]]), tr))  # foto-1 fails again; its copy gets the page
    report = run_notes(deps(drive, ScriptedFeed(drive, []), tr))  # foto-1, still failed, meets its copy
    files = state_of(drive)["files"]
    assert report["ok"]
    assert (files["foto-1"]["state"], files["foto-2"]["state"]) == ("duplicate", "transcribed")


def test_one_budget_refusal_holds_every_other_photo_without_a_call():
    drive = MemoryDrive.topic()
    for n in (1, 2, 3):
        drive.put(f"foto-{n}", f"{n}.jpg", "image/jpeg", str(n).encode())
    tr = ScriptedTranscriber([Transcription(PhotoState.BUDGET_WAIT)])
    report = run_notes(deps(drive, ScriptedFeed(drive, [["foto-1", "foto-2", "foto-3"]]), tr))
    assert (tr.calls, report["budget_wait"]) == (1, 3)


def test_with_no_key_no_photo_is_downloaded():
    drive = MemoryDrive.topic()
    drive.put("foto-1", "a.jpg", "image/jpeg", b"a")
    run_notes(deps(drive, ScriptedFeed(drive, [["foto-1"]]), None))
    assert "foto-1" not in drive.downloads


# --- Classroom items (spec 005 T028, T029) ---------------------------------------------------------
# The real change feed over the fake Drive: a first run lists the whole tree, a later one reads what
# the test `touch`es. Every name, id and text is invented.

PDF_MIME = "application/pdf"
WORD = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
SLIDES = "application/vnd.google-apps.presentation"
TEMA_01, TEMA_02 = "Tema 01 - Materia inventada", "Tema 02 - Otra materia"


def classroom_set_up(drive: MemoryDrive, topic: str = TOPIC, folder: str = CLASSROOM, name: str = TEMA_01) -> str:
    """What `notebook setup` leaves: the topic's Classroom living file in its `classroom/`, recorded."""
    living = drive.put(f"vivo-{topic}", f"Classroom · {name}.pdf", PDF_MIME, b"vacio", parent=folder)
    store = DriveNotesStateStore(drive)
    state = store.load()
    state.setdefault("topics", {})[topic] = {
        "name": name,
        "living": {"classroom": {"file_id": living.id, "source_id": f"fuente-{topic}", "built_md5": None, "pages": 0}},
    }
    state.setdefault("files", {})[living.id] = {"kind": "living_file", "topic": topic, "version": "", "own": True}
    store.save(state)
    return living.id


def run(drive: MemoryDrive) -> dict[str, Any]:
    return run_notes(deps(drive, DriveChangeFeed(drive), None))


def nonzero(report: dict[str, Any]) -> list[dict[str, int]]:
    """Each reported topic's counts that are not zero, in the report's order."""
    return [{k: v for k, v in t.items() if k != "topic" and v} for t in report["topics"]]


def body(drive: MemoryDrive, living: str) -> str:
    return drive.bodies[living].decode()


def test_one_file_item_is_added_once_and_a_second_run_writes_only_the_run_log():
    drive = MemoryDrive.subject()
    living = classroom_set_up(drive)
    drive.put("ficha", "20261001 - Ficha de repaso.pdf", PDF_MIME, b"%PDF ficha", parent=CLASSROOM)
    report = run(drive)
    assert (
        body(drive, living)
        == f"classroom:{TEMA_01}:ficha[Ficha de repaso|||20261001 - Ficha de repaso.pdf/pdf=%PDF ficha]"
    )
    assert nonzero(report) == [{"items_added": 1}]
    assert state_of(drive)["files"]["ficha"]["state"] == "in_living_file"
    writes = list(drive.updates)
    report = run(drive)
    assert drive.updates[len(writes) :] == ["last-run.json"]  # SC-004
    assert report["topics"] == []


def test_a_folder_with_a_pdf_a_word_file_and_its_description_is_one_entry():
    drive = MemoryDrive.subject()
    living = classroom_set_up(drive)
    drive.folder("lab", "20261005 - Práctica de laboratorio", CLASSROOM)
    drive.put("guion", "guion.pdf", PDF_MIME, b"%PDF guion", parent="lab")
    drive.put("plantilla", "plantilla.docx", WORD, b"docx", parent="lab")
    drive.put("diapos", "Presentación", SLIDES, b"", parent="lab")
    drive.put("desc", "descripcion.md", "text/markdown", b"Traed la bata.\n", parent="lab")
    report = run(drive)
    parts = "Presentación/export=export:diapos,guion.pdf/pdf=%PDF guion,plantilla.docx/office=office:plantilla"
    assert body(drive, living) == f"classroom:{TEMA_01}:lab[Práctica de laboratorio|Traed la bata.||{parts}]"
    assert nonzero(report) == [{"items_added": 1}]
    assert (drive.exports, drive.conversions) == (["diapos"], ["plantilla"])
    # The Word file's Google copy was made in .alfabeta/conversions/ and is in the trash already.
    (conversions,) = [f for f in drive.files.values() if f.name == "conversions"]
    assert drive.files[conversions.parents[0]].name == ".alfabeta"
    copies = [f for f in drive.files.values() if conversions.id in f.parents]
    assert len(copies) == 1 and copies[0].trashed and copies[0].prop("alfabeta_for") == "plantilla"


def test_a_links_only_folder_is_its_cover_with_the_addresses():
    drive = MemoryDrive.subject()
    living = classroom_set_up(drive)
    drive.folder("videos", "20261006 - Vídeos del tema", CLASSROOM)
    drive.put("desc", "descripcion.md", "text/markdown", b"Mirad los dos.", parent="videos")
    links = b"# Enlaces\n\n- [Uno](https://example.org/uno) \xc2\xb7 06/10/2026\n- [Dos](https://example.org/dos) \xc2\xb7 06/10/2026\n"
    drive.put("enl", "enlaces.md", "text/markdown", links, parent="videos")
    report = run(drive)
    shown = "Uno: https://example.org/uno · 06/10/2026,Dos: https://example.org/dos · 06/10/2026"
    assert body(drive, living) == f"classroom:{TEMA_01}:videos[Vídeos del tema|Mirad los dos.|{shown}|]"
    assert nonzero(report) == [{"items_added": 1, "links_only": 1}]


def test_an_assignment_enters_with_its_statement_only_never_the_students_work_or_its_grading():
    drive = MemoryDrive.subject()
    living = classroom_set_up(drive)
    drive.folder("tarea", "20261007 - Tarea 1", CLASSROOM)
    drive.put("enun", "enunciado - Tarea 1.pdf", PDF_MIME, b"%PDF enunciado", parent="tarea")
    drive.put("enun-md", "enunciado.md", "text/markdown", b"Resolved los cinco ejercicios.", parent="tarea")
    drive.folder("sub", "submission", "tarea")
    drive.put("hecho", "Tarea 1.pdf", PDF_MIME, b"%PDF lo del alumno", parent="sub")
    drive.put("nota", "correccion.md", "text/markdown", b"# Correccion\n\n- Nota: 9", parent="tarea")
    drive.put("nota-0", "correccion (anterior 2026-10-01).md", "text/markdown", b"- Nota: 7", parent="tarea")
    drive.put("borrador", "entrega - borrador.pdf", PDF_MIME, b"%PDF borrador", parent="tarea")
    drive.folder("legado", "entrega", "tarea")  # the submission's folder until 2026-10-28 (#110)
    drive.put("viejo", "Tarea 1 viejo.pdf", PDF_MIME, b"%PDF viejo", parent="legado")
    run(drive)
    statement = "tarea[Tarea 1|Resolved los cinco ejercicios.||enunciado - Tarea 1.pdf/pdf=%PDF enunciado]"
    assert body(drive, living) == f"classroom:{TEMA_01}:{statement}"
    student = {"hecho", "nota", "nota-0", "borrador", "viejo"}
    # Never read, so never in a living file: the student's bytes did not leave Drive (constitution III).
    assert not student & {*drive.downloads, *drive.exports, *drive.conversions}
    assert not student & set(state_of(drive)["files"])


def test_an_edited_file_with_its_previous_version_beside_it_is_in_once():
    drive = MemoryDrive.subject()
    living = classroom_set_up(drive)
    drive.put("ficha", "20261001 - Ficha de repaso.pdf", PDF_MIME, b"%PDF v1", parent=CLASSROOM)
    run(drive)
    # classroom-sync keeps the old file beside the new one under its previous-version name (spec 001
    # FR-015b): renamed in place, same content, so the feed reports no new version of it.
    drive.files["ficha"] = replace(drive.files["ficha"], name="20261001 - Ficha de repaso (anterior 2026-10-12).pdf")
    drive.put("ficha-2", "20261001 - Ficha de repaso.pdf", PDF_MIME, b"%PDF v2", parent=CLASSROOM)
    drive.touch("ficha", "ficha-2")
    run(drive)
    assert (
        body(drive, living)
        == f"classroom:{TEMA_01}:ficha-2[Ficha de repaso|||20261001 - Ficha de repaso.pdf/pdf=%PDF v2]"
    )
    assert state_of(drive)["files"]["ficha"]["state"] == "left_out"


def test_an_edited_part_with_its_previous_version_replaces_the_entry_in_place():
    drive = MemoryDrive.subject()
    living = classroom_set_up(drive)
    drive.put("antes", "20260920 - Primera ficha.pdf", PDF_MIME, b"%PDF primera", parent=CLASSROOM)
    drive.folder("lab", "20261005 - Práctica", CLASSROOM)
    drive.put("guion", "guion.pdf", PDF_MIME, b"%PDF v1", parent="lab")
    drive.put("despues", "20261010 - Última ficha.pdf", PDF_MIME, b"%PDF ultima", parent=CLASSROOM)
    run(drive)
    first = state_of(drive)["files"]["lab"]["item_version"]
    drive.files["guion"] = replace(drive.files["guion"], name="guion (anterior 2026-10-12).pdf")
    drive.put("guion-2", "guion.pdf", PDF_MIME, b"%PDF v2", parent="lab")
    drive.touch("guion", "guion-2")
    report = run(drive)
    entries = body(drive, living).split(":", 2)[2].split(";")
    assert [e.split("[")[0] for e in entries] == ["antes", "lab", "despues"]  # its place, by posting date
    assert entries[1] == "lab[Práctica|||guion.pdf/pdf=%PDF v2]"
    assert state_of(drive)["files"]["lab"]["item_version"] != first
    assert nonzero(report) == [{"items_added": 1}]
    assert "guion" not in drive.downloads[drive.downloads.index("guion-2") :]


def test_a_changed_item_is_replaced_in_place():
    drive = MemoryDrive.subject()
    living = classroom_set_up(drive)
    drive.put("ficha", "20261001 - Ficha.pdf", PDF_MIME, b"%PDF v1", parent=CLASSROOM)
    run(drive)
    drive.put("ficha", "20261001 - Ficha.pdf", PDF_MIME, b"%PDF v2", parent=CLASSROOM)
    drive.touch("ficha")
    report = run(drive)
    assert body(drive, living) == f"classroom:{TEMA_01}:ficha[Ficha|||20261001 - Ficha.pdf/pdf=%PDF v2]"
    assert drive.updates.count(f"Classroom · {TEMA_01}.pdf") == 2
    assert nonzero(report) == [{"items_added": 1}]


def test_an_announcement_is_no_entry():
    drive = MemoryDrive.subject()
    living = classroom_set_up(drive, TOPIC_2, CLASSROOM_2, TEMA_02)
    drive.put("aviso", "20261002 - aviso - Excursión al museo.md", "text/markdown", b"El jueves.", parent=CLASSROOM_0)
    drive.folder("aviso-2", "20261003 - aviso - Material para el viernes", CLASSROOM_0)
    drive.put("adjunto", "lista.pdf", PDF_MIME, b"%PDF lista", parent="aviso-2")
    report = run(drive)
    assert body(drive, living) == "vacio"
    assert {state_of(drive)["files"][i]["state"] for i in ("aviso", "aviso-2")} == {"left_out"}
    assert report["topics"] == [] and "adjunto" not in drive.downloads


def test_a_no_topic_material_goes_to_the_latest_topic_and_stays_there():
    drive = MemoryDrive.subject()
    first = classroom_set_up(drive)
    latest = classroom_set_up(drive, TOPIC_2, CLASSROOM_2, TEMA_02)
    drive.put("normas", "20261003 - Normas del laboratorio.pdf", PDF_MIME, b"%PDF v1", parent=CLASSROOM_0)
    run(drive)
    assert body(drive, first) == "vacio"
    assert body(drive, latest).startswith(f"classroom:{TEMA_02}:normas[Normas del laboratorio|")
    # A newer topic appears; a new version of the material stays where it went first (spec 002 FR-023).
    drive.folder("t3", "20261101 - Tema 03 - Nueva", "fyq")
    drive.folder("cl3", "classroom", "t3")
    drive.put("normas", "20261003 - Normas del laboratorio.pdf", PDF_MIME, b"%PDF v2", parent=CLASSROOM_0)
    drive.touch("t3", "cl3", "normas")
    run(drive)
    assert state_of(drive)["files"]["normas"]["living"] == TOPIC_2
    assert body(drive, latest).count("normas[") == 1


def test_a_no_topic_material_waits_for_a_topic_then_goes_into_it():
    drive = MemoryDrive()
    for fid, name, parent in (
        ("anio", "2026-2027", "raiz"),
        ("fyq", "FyQ", "anio"),
        (NO_TOPIC, "20260910 - No topic", "fyq"),
        (CLASSROOM_0, "classroom", NO_TOPIC),
    ):
        drive.folder(fid, name, parent)
    drive.put("normas", "20260911 - Normas.pdf", PDF_MIME, b"%PDF normas", parent=CLASSROOM_0)
    assert run(drive)["topics"] == []
    assert "living" not in state_of(drive)["files"]["normas"]
    drive.folder(TOPIC, "20260915 - Tema 01 - Materia inventada", "fyq")
    drive.folder(CLASSROOM, "classroom", TOPIC)
    living = classroom_set_up(drive)
    drive.touch(TOPIC, CLASSROOM)
    run(drive)
    assert body(drive, living).startswith(f"classroom:{TEMA_01}:normas[Normas|")


def test_a_moved_item_leaves_the_first_file_and_enters_the_second_once():
    drive = MemoryDrive.subject()
    first = classroom_set_up(drive)
    second = classroom_set_up(drive, TOPIC_2, CLASSROOM_2, TEMA_02)
    drive.folder("lab", "20261005 - Práctica", CLASSROOM)
    drive.put("guion", "guion.pdf", PDF_MIME, b"%PDF guion", parent="lab")
    run(drive)
    assert "lab[" in body(drive, first)
    drive.files["lab"] = replace(drive.files["lab"], parents=(CLASSROOM_2,))  # classroom-sync moved it
    drive.touch("lab")
    run(drive)
    assert body(drive, first) == f"classroom:{TEMA_01}:"
    assert body(drive, second) == f"classroom:{TEMA_02}:lab[Práctica|||guion.pdf/pdf=%PDF guion]"
    assert state_of(drive)["files"]["lab"]["living"] == TOPIC_2


def test_a_gone_item_leaves_the_file_and_is_reported_once():
    drive = MemoryDrive.subject()
    living = classroom_set_up(drive)
    drive.put("ficha", "20261001 - Ficha.pdf", PDF_MIME, b"%PDF ficha", parent=CLASSROOM)
    run(drive)
    del drive.files["ficha"]
    drive.touch("ficha")
    assert nonzero(run(drive)) == [{"gone": 1}]
    assert body(drive, living) == f"classroom:{TEMA_01}:"
    assert state_of(drive)["files"]["ficha"]["state"] == "gone"
    assert run(drive)["topics"] == []


def test_an_item_moved_into_reports_is_gone_though_the_feed_says_nothing():
    drive = MemoryDrive.subject()
    living = classroom_set_up(drive)
    drive.put("ficha", "20261001 - Ficha.pdf", PDF_MIME, b"%PDF ficha", parent=CLASSROOM)
    run(drive)
    drive.folder("informes", "reports", "raiz")
    drive.files["ficha"] = replace(drive.files["ficha"], parents=("informes",))
    drive.touch("ficha")  # the feed drops it: reports/ is never read (research R2)
    assert nonzero(run(drive)) == [{"gone": 1}]
    assert body(drive, living) == f"classroom:{TEMA_01}:"


@pytest.mark.parametrize("into", [TOPIC_2, NOTES])  # another topic's root; this topic's notes/
def test_an_item_moved_out_of_classroom_into_a_topic_leaves_its_file(into: str):
    drive = MemoryDrive.subject()
    living = classroom_set_up(drive)
    drive.put("ficha", "20261001 - Ficha.pdf", PDF_MIME, b"%PDF ficha", parent=CLASSROOM)
    run(drive)
    drive.files["ficha"] = replace(drive.files["ficha"], parents=(into,))
    drive.touch("ficha")
    report = run(drive)
    assert body(drive, living) == f"classroom:{TEMA_01}:"
    assert {"gone": 1} in [{k: v for k, v in t.items() if k == "gone"} for t in nonzero(report)]


def test_a_file_removed_alone_from_an_item_folder_is_seen_with_no_change_reported():
    drive = MemoryDrive.subject()
    living = classroom_set_up(drive)
    drive.folder("lab", "20261005 - Práctica", CLASSROOM)
    drive.put("guion", "guion.pdf", PDF_MIME, b"%PDF guion", parent="lab")
    drive.put("tabla", "tabla.pdf", PDF_MIME, b"%PDF tabla", parent="lab")
    run(drive)
    del drive.files["tabla"]  # the feed reports nothing: the file was never recorded on its own
    run(drive)
    assert body(drive, living) == f"classroom:{TEMA_01}:lab[Práctica|||guion.pdf/pdf=%PDF guion]"


def test_a_renamed_item_folder_is_its_entry_with_the_new_title_in_place():
    drive = MemoryDrive.subject()
    living = classroom_set_up(drive)
    drive.folder("lab", "20261005 - Práctica", CLASSROOM)
    drive.put("guion", "guion.pdf", PDF_MIME, b"%PDF guion", parent="lab")
    run(drive)
    drive.files["lab"] = replace(drive.files["lab"], name="20261005 - Práctica de densidad")
    drive.touch("lab")
    run(drive)
    assert body(drive, living) == f"classroom:{TEMA_01}:lab[Práctica de densidad|||guion.pdf/pdf=%PDF guion]"


def test_an_undated_file_in_classroom_is_unexpected_and_no_entry():
    drive = MemoryDrive.subject()
    living = classroom_set_up(drive)
    drive.put("suelto", "apuntes extra.pdf", PDF_MIME, b"%PDF suelto", parent=CLASSROOM)
    assert nonzero(run(drive)) == [{"unexpected": 1}]
    assert body(drive, living) == "vacio" and "suelto" not in drive.downloads
    drive.touch("suelto")
    assert run(drive)["topics"] == []  # reported once


def test_an_item_drive_cannot_read_is_left_out_retried_then_in():
    drive = MemoryDrive.subject()
    living = classroom_set_up(drive)
    drive.put("ficha", "20261001 - Ficha.pdf", PDF_MIME, b"%PDF ficha", parent=CLASSROOM)
    drive.folder("lab", "20261005 - Práctica", CLASSROOM)
    drive.put("plantilla", "plantilla.docx", WORD, b"docx", parent="lab")
    drive.unreadable.add("plantilla")
    report = run(drive)
    assert body(drive, living) == f"classroom:{TEMA_01}:ficha[Ficha|||20261001 - Ficha.pdf/pdf=%PDF ficha]"
    assert nonzero(report) == [{"items_added": 2, "failed": 1}]
    assert state_of(drive)["files"]["lab"]["state"] == "failed"
    drive.unreadable.clear()
    run(drive)  # nothing changed in Drive: a failed item is retried
    assert "lab[Práctica|||plantilla.docx/office=office:plantilla]" in body(drive, living)
    assert state_of(drive)["files"]["lab"]["state"] == "in_living_file"


def test_an_item_that_keeps_failing_is_left_until_it_changes():
    drive = MemoryDrive.subject()
    classroom_set_up(drive)
    drive.put("ficha", "20261001 - Ficha.pdf", PDF_MIME, b"%PDF v1", parent=CLASSROOM)
    drive.unreadable.add("ficha")
    for _ in range(5):
        run(drive)
    assert drive.downloads.count("ficha") == 4  # the first try and three retries (MAX_RETRIES)
    assert state_of(drive)["files"]["ficha"]["state"] == "failed_final"
    drive.unreadable.clear()
    drive.put("ficha", "20261001 - Ficha.pdf", PDF_MIME, b"%PDF v2", parent=CLASSROOM)
    drive.touch("ficha")
    run(drive)
    assert state_of(drive)["files"]["ficha"]["state"] == "in_living_file"


def test_a_drive_error_on_an_entry_already_in_the_file_keeps_the_file_and_the_cursor():
    drive = MemoryDrive.subject()
    living = classroom_set_up(drive)
    drive.put("ficha", "20261001 - Ficha.pdf", PDF_MIME, b"%PDF ficha", parent=CLASSROOM)
    run(drive)
    before = body(drive, living)
    (log,) = drive.named("last-run.json")
    cursor = json.loads(drive.bodies[log])["page_token"]
    drive.unreadable.add("ficha")
    drive.put("nueva", "20261002 - Nueva.pdf", PDF_MIME, b"%PDF nueva", parent=CLASSROOM)
    drive.touch("nueva")
    report = run(drive)
    assert not report["ok"] and body(drive, living) == before
    assert json.loads(drive.bodies[log])["page_token"] == cursor  # the next run reads the same changes
    drive.unreadable.clear()
    drive.touch("nueva")
    run(drive)
    assert "nueva[" in body(drive, living) and "ficha[" in body(drive, living)


def test_a_topic_waiting_for_setup_gets_no_classroom_file():
    drive = MemoryDrive.subject()
    drive.put("ficha", "20261001 - Ficha.pdf", PDF_MIME, b"%PDF ficha", parent=CLASSROOM)
    report = run(drive)
    assert nonzero(report) == [{"items_added": 1, "waiting_setup": 1}]
    assert not [n for n in drive.uploads if n.startswith("Classroom ·")] and "ficha" not in drive.downloads
    assert state_of(drive)["files"]["ficha"]["state"] == "seen"
