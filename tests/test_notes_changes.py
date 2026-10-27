"""From the change feed to arrivals, marks, corrections and gone files (spec 005 T009, T010).

The tree and the feed pages are in `tests/fixtures/notes/`, with invented ids and names.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from alfabeta.google.drive import DriveFile, ScopedDrive
from alfabeta.notes.changes import DriveChangeFeed, Known
from alfabeta.notes.model import Kind
from tests.conftest import FakeTransport, json_response

FIXTURES = Path(__file__).parent / "fixtures" / "notes"


def fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())


def drive(*responses: dict[str, Any]) -> tuple[ScopedDrive, FakeTransport]:
    """A ScopedDrive whose listing is the fixture tree; the transport serves the given pages."""
    tree = {f["id"]: DriveFile.of(f) for f in fixture("tree.json")["files"]}
    t = FakeTransport([json_response(200, r) for r in responses])
    return ScopedDrive(t, "acceso", tree["raiz"], tree), t


# What a run that already wrote its transcription, living file and state would have recorded.
OWN = {
    "st": Known(Kind.UNEXPECTED, "5555", own=True),
    "lr": Known(Kind.UNEXPECTED, "6666", own=True),
    "tp1": Known(Kind.NOTES_TRANSCRIPT, "a002", own=True, name="IMG_0001.jpg · transcripción.pdf"),
    "tm1": Known(Kind.NOTES_TEXT, "a003", own=True),
    "lf1": Known(Kind.LIVING_FILE, "a007", own=True),
}
SEEN = {"f1": Known(Kind.NOTES_PHOTO, "a001"), "p1": Known(Kind.CLASSROOM_ITEM, "a005")}


def test_the_first_run_takes_the_cursor_first_then_the_whole_tree():
    d, t = drive({"startPageToken": "300"})
    result = DriveChangeFeed(d).read(None, {})
    assert "/changes/startPageToken" in t.calls[0][1]
    assert result.cursor == "300"
    assert {(a.file_id, a.topic, a.kind) for a in result.arrivals} == {
        ("f1", "t1", Kind.NOTES_PHOTO),
        ("tp1", "t1", Kind.NOTES_TRANSCRIPT),
        ("tm1", "t1", Kind.NOTES_TEXT),
        ("u1", "t1", Kind.UNEXPECTED),
        ("it1", "t1", Kind.CLASSROOM_ITEM),  # the item folder and its file: one item
        ("it2", "t1", Kind.CLASSROOM_ITEM),
        ("lf1", "t1", Kind.LIVING_FILE),
        ("u2", "t1", Kind.UNEXPECTED),
    }
    assert {a.version for a in result.arrivals if a.file_id == "f1"} == {"a001"}


def test_echoes_are_consumed_but_the_students_mark_and_correction_arrive():
    d, _ = drive(fixture("changes-echoes.json"))
    result = DriveChangeFeed(d).read("301", {**OWN, **SEEN})
    assert result.cursor == "302"
    assert [(m.file_id, m.name) for m in result.marks] == [("tp1", "IMG_0001.jpg · transcripción (revisada).pdf")]
    assert [(c.file_id, c.version) for c in result.corrections] == [("tm1", "a0b3")]
    # The living file and the state are echoes; the changed file inside an item folder is that item.
    assert [(a.file_id, a.kind, a.version) for a in result.arrivals] == [("it1", Kind.CLASSROOM_ITEM, "a0d5")]
    assert result.gone == ["f1"]


def test_an_idle_page_yields_nothing_but_the_new_cursor():
    d, _ = drive(fixture("changes-idle.json"))
    result = DriveChangeFeed(d).read("302", {**OWN, **SEEN})
    assert (result.cursor, result.arrivals, result.marks, result.corrections, result.gone) == ("303", [], [], [], [])


def test_a_recorded_file_arrives_again_only_with_a_new_version():
    tree = {f["id"]: f for f in fixture("tree.json")["files"]}

    def change(**fields: str) -> dict[str, Any]:
        moved = {k: v for k, v in {**tree["f1"], **fields}.items() if k != "id"}
        return {"changes": [{"fileId": "f1", "removed": False, "file": moved}], "newStartPageToken": "9"}

    d, _ = drive(change(name="IMG_0001 bis.jpg"), change(md5Checksum="b001"))
    feed = DriveChangeFeed(d)
    assert feed.read("8", SEEN).arrivals == []  # renamed, same content
    assert [a.version for a in feed.read("8", SEEN).arrivals] == ["b001"]


def test_an_own_transcript_renamed_to_its_recorded_name_is_an_echo():
    tree = {f["id"]: f for f in fixture("tree.json")["files"]}
    same = {k: v for k, v in tree["tp1"].items() if k != "id"}
    d, _ = drive({"changes": [{"fileId": "tp1", "removed": False, "file": same}], "newStartPageToken": "9"})
    result = DriveChangeFeed(d).read("8", OWN)
    assert (result.marks, result.arrivals) == ([], [])


def test_a_trashed_recorded_file_is_gone():
    tree = {f["id"]: f for f in fixture("tree.json")["files"]}
    trashed = {**{k: v for k, v in tree["it2"].items() if k != "id"}, "trashed": True}
    d, _ = drive({"changes": [{"fileId": "it2", "removed": False, "file": trashed}], "newStartPageToken": "9"})
    result = DriveChangeFeed(d).read("8", {"it2": Known(Kind.CLASSROOM_ITEM, "a006")})
    assert (result.gone, result.arrivals) == (["it2"], [])


def test_a_deep_path_under_informes_is_never_read_as_a_topic():
    folder = "application/vnd.google-apps.folder"
    # Informes/<a>/<b>/apuntes/ has a topic's shape one level down: only the skip keeps it out.
    deep = [("i1", "2026-2027", "inf"), ("i2", "FyQ", "i1"), ("i4", "apuntes", "i2")]
    d, t = drive({"startPageToken": "1"})
    for item_id, name, parent in deep:
        d._tree[item_id] = DriveFile(item_id, name, folder, (parent,))  # noqa: SLF001
    d._tree["img"] = DriveFile("img", "foto.jpg", "image/jpeg", ("i4",), md5="z1")  # noqa: SLF001
    assert "img" not in {a.file_id for a in DriveChangeFeed(d).read(None, {}).arrivals}
    assert t.responses == []
