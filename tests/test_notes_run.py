"""One pass of the notes, every port faked (spec 005 T018, T019). Every value is invented."""

from __future__ import annotations

import ast
import datetime as dt
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from alfabeta.notes.model import PhotoState, Usage
from alfabeta.notes.run import COUNTS, adopted_section, run_notes, topic_name
from alfabeta.notes.state import STATE, ConcurrentWriteError, DriveNotesStateStore
from alfabeta.notes.transcribe import Transcription
from tests.notes_fakes import TOPIC, FixedClock, MemoryDrive, ScriptedFeed, ScriptedTranscriber, deps

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
