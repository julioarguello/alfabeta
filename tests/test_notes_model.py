"""Invariants of spec 005's domain (T005, data-model.md). Every value is invented."""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from alfabeta.notes.model import (
    MAX_RETRIES,
    Arrival,
    ClassroomEntry,
    ClassroomItem,
    ItemState,
    Kind,
    LivingFile,
    LivingKind,
    NotesPage,
    Part,
    PartKind,
    Photo,
    PhotoState,
    RanOn,
    Review,
    RunLog,
    RunResult,
    SpendLedger,
    Topic,
    Usage,
    is_announcement,
    is_part,
    reportable,
)

MADRID = ZoneInfo("Europe/Madrid")
T0 = dt.datetime(2026, 10, 27, 9, 0, tzinfo=MADRID)


def photo(state: PhotoState = PhotoState.SEEN) -> Photo:
    return Photo(Arrival("foto-1", "tema-1", Kind.NOTES_PHOTO, "md5-a"), state)


def test_a_photo_goes_seen_transcribed_in_living_file():
    done = photo().moved_to(PhotoState.TRANSCRIBED).moved_to(PhotoState.IN_LIVING_FILE)
    assert done.state == PhotoState.IN_LIVING_FILE


def test_a_photo_cannot_skip_the_transcription():
    with pytest.raises(ValueError, match="cannot go from seen to in_living_file"):
        photo().moved_to(PhotoState.IN_LIVING_FILE)


def test_failures_are_capped_then_final():
    p = photo()
    for _ in range(MAX_RETRIES):
        p = p.moved_to(PhotoState.FAILED)
        assert p.state == PhotoState.FAILED
    assert p.moved_to(PhotoState.FAILED).state == PhotoState.FAILED_FINAL


def test_a_new_version_starts_again_and_clears_the_retries():
    p = photo()
    for _ in range(MAX_RETRIES + 1):
        p = p.moved_to(PhotoState.FAILED)
    again = p.moved_to(PhotoState.SEEN)
    assert (again.state, again.retries) == (PhotoState.SEEN, 0)


def test_a_photo_can_be_gone_from_any_state():
    assert photo(PhotoState.IN_LIVING_FILE).moved_to(PhotoState.GONE).state == PhotoState.GONE


def test_budget_wait_is_retried():
    assert photo(PhotoState.BUDGET_WAIT).moved_to(PhotoState.TRANSCRIBED).state == PhotoState.TRANSCRIBED


def test_a_classroom_item_goes_in_once():
    item = ClassroomItem(Arrival("item-1", "tema-1", Kind.CLASSROOM_ITEM, "md5-b"))
    assert item.moved_to(ItemState.IN_LIVING_FILE).state == ItemState.IN_LIVING_FILE
    with pytest.raises(ValueError):
        item.moved_to(ItemState.IN_LIVING_FILE).moved_to(ItemState.FAILED)


def test_a_persisting_state_is_not_reported_again():
    assert reportable(None, "failed")
    assert not reportable("failed", "failed")
    assert reportable("failed", "transcribed")


def test_living_file_names_are_spanish_and_keyed_by_folder():
    topic = Topic("carpeta-1", "Tema 01 - Sustancias inventadas")
    assert topic.living_file_name(LivingKind.NOTES) == "Apuntes · Tema 01 - Sustancias inventadas.pdf"
    assert topic.living_file_name(LivingKind.CLASSROOM) == "Classroom · Tema 01 - Sustancias inventadas.pdf"
    assert Topic("a", "Sin tema") != Topic("b", "Sin tema")


def test_only_setup_sets_a_living_file_and_its_id_never_changes():
    living = LivingFile("tema-1", LivingKind.NOTES)
    assert living.waiting_setup
    set_up = living.set_up("fichero-1", "fuente-1")
    assert not set_up.waiting_setup
    assert set_up.set_up("fichero-1", "fuente-1") == set_up
    with pytest.raises(ValueError, match="never changes"):
        set_up.set_up("fichero-2", "fuente-1")


def test_an_unchanged_rebuild_is_not_uploaded_and_size_warns():
    living = LivingFile("tema-1", LivingKind.NOTES, "fichero-1", "fuente-1")
    built, upload = living.built("md5-x", 12)
    assert upload
    _, again = built.built("md5-x", 12)
    assert not again
    assert built.built("md5-y", 101)[0].over(100)
    assert not built.over(100)


def test_a_page_keeps_its_place_through_marks_and_corrections():
    page = NotesPage("foto-1", "md5-a", "texto", order=3)
    assert page.heading == "Transcripción automática"
    wrong = page.marked(Review.WRONG)
    assert wrong.heading == "En corrección"
    fixed = wrong.corrected("foto-2", "md5-c", "texto corregido")
    assert (fixed.order, fixed.review, fixed.photo_id) == (3, Review.AUTOMATIC, "foto-2")
    assert page.marked(Review.CHECKED).heading == "Revisada por el alumno"


@pytest.mark.parametrize(
    "name",
    [
        "entrega - Ejercicios.pdf",
        "Entrega - ejercicios.pdf",
        "correccion.md",
        "correccion (anterior 2026-10-01).md",
        "Ficha 2 (anterior 2026-10-01).pdf",
        "enunciado - Ficha (anterior 2026-09-30)",
    ],
)
def test_student_work_grading_and_previous_versions_are_never_parts(name: str):
    assert not is_part(name)
    with pytest.raises(ValueError, match="never parts"):
        ClassroomEntry("item-1", "v1", "Ficha", dt.date(2026, 10, 1), parts=(Part("f", name, PartKind.PDF),))


@pytest.mark.parametrize("name", ["enunciado - Ficha 2.pdf", "Apuntes del tema.pdf", "descripcion.md", "Mapa (2).png"])
def test_material_is_a_part(name: str):
    assert is_part(name)


def test_announcements_are_not_material():
    assert is_announcement("20261020 - aviso - Mañana no hay clase.md")
    assert not is_announcement("20261020 - Ficha de repaso.pdf")


def test_a_links_only_entry_is_its_cover():
    links = ClassroomEntry("item-1", "v1", "Vídeo", dt.date(2026, 10, 2), parts=(Part("f", "enlace", PartKind.NAMED),))
    assert links.links_only
    pdf = ClassroomEntry("item-2", "v1", "Ficha", dt.date(2026, 10, 2), parts=(Part("g", "ficha.pdf", PartKind.PDF),))
    assert not pdf.links_only


def test_a_failed_run_keeps_the_cursor_and_the_last_cloud_success():
    first = RunLog(T0, T0, RunResult.OK, RanOn.CLOUD, last_ok_ended=T0, page_token="100")
    later = T0 + dt.timedelta(minutes=15)
    failed = first.next(later, later, RunResult.FAILED, RanOn.CLOUD, page_token="120")
    assert (failed.page_token, failed.last_ok_ended) == ("100", T0)
    ok = failed.next(later, later, RunResult.PARTIAL, RanOn.CLOUD, page_token="120")
    assert (ok.page_token, ok.last_ok_ended) == ("120", later)


def test_a_mac_run_does_not_count_as_the_clouds():
    first = RunLog(T0, T0, RunResult.OK, RanOn.CLOUD, last_ok_ended=T0, page_token="100")
    later = T0 + dt.timedelta(hours=3)
    mac = first.next(later, later, RunResult.OK, RanOn.MAC, page_token="130")
    assert (mac.last_ok_ended, mac.page_token) == (T0, "130")


def test_the_ledger_sums_every_call_by_month():
    ledger = SpendLedger().add("2026-10", Usage(3_000, 1_000)).add("2026-10", Usage(1_000, 500))
    ledger = ledger.add("2026-11", Usage(10, 10))
    assert ledger.months["2026-10"] == Usage(4_000, 1_500)
    assert ledger.cost("2026-10", (2.0, 10.0)) == pytest.approx(0.023)
    assert ledger.cost("2026-12", (2.0, 10.0)) == 0
