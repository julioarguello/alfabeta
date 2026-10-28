"""From the change feed to arrivals, marks, corrections and gone files (spec 005 T009, T010).

The tree and the feed pages are in `tests/fixtures/notes/`, with invented ids and names.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from alfabeta.google.drive import DriveFile, ScopedDrive
from alfabeta.google.transport import Response
from alfabeta.notes.changes import DriveChangeFeed, Known
from alfabeta.notes.model import Kind
from tests.conftest import FakeTransport, json_response

FIXTURES = Path(__file__).parent / "fixtures" / "notes"


def fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())


def drive(*responses: dict[str, Any], extra: tuple[DriveFile, ...] = ()) -> tuple[ScopedDrive, FakeTransport]:
    """A ScopedDrive whose listing is the fixture tree (plus `extra`); the transport serves the given pages."""
    tree = {f["id"]: DriveFile.of(f) for f in fixture("tree.json")["files"]} | {f.id: f for f in extra}
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


@dataclass
class TreeTransport:
    """Answers listings from a tree it holds, so a test can change Drive between two requests."""

    files: list[dict[str, Any]]
    token: str = "300"
    calls: list[str] = field(default_factory=lambda: [])

    def request(
        self, method: str, url: str, *, headers: dict[str, str] | None = None, body: bytes | None = None
    ) -> Response:
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        if url.endswith("/changes/startPageToken"):
            self.calls.append("token")
            return json_response(200, {"startPageToken": self.token})
        parent = re.match(r"'([^']+)' in parents", query["q"][0])
        assert parent is not None
        self.calls.append("list")
        name = re.search(r"name = '([^']+)'", query["q"][0])
        found = [f for f in self.files if parent.group(1) in f["parents"] and (not name or f["name"] == name.group(1))]
        return json_response(200, {"files": found})


def test_the_first_run_takes_the_cursor_first_then_the_whole_tree(tmp_path: Path):
    files = fixture("tree.json")["files"]
    t = TreeTransport([f for f in files if f["id"] != "raiz"] + [files[0]])
    d = ScopedDrive.open(t, "acceso", "alfabeta", tmp_path / "drive.json")
    # Uploaded after the run listed the tree but before it took its cursor: in neither, unless the
    # run lists again after the cursor (research R2).
    t.files.append(
        {"id": "tarde", "name": "IMG_0002.jpg", "mimeType": "image/jpeg", "parents": ["ap"], "md5Checksum": "a010"}
    )
    t.calls.clear()
    result = DriveChangeFeed(d).read(None, {})
    assert t.calls[0] == "token" and set(t.calls[1:]) == {"list"}
    assert result.cursor == "300"
    assert {(a.file_id, a.topic, a.kind) for a in result.arrivals} == {
        ("f1", "t1", Kind.NOTES_PHOTO),
        ("tarde", "t1", Kind.NOTES_PHOTO),
        ("tp1", "t1", Kind.NOTES_TRANSCRIPT),
        ("tm1", "t1", Kind.NOTES_TEXT),
        ("u1", "t1", Kind.UNEXPECTED),
        ("it1", "t1", Kind.CLASSROOM_ITEM),  # the item folder and its file: one item
        ("it2", "t1", Kind.CLASSROOM_ITEM),
        ("lf1", "t1", Kind.LIVING_FILE),  # in notes/
        ("lf2", "t1", Kind.LIVING_FILE),  # in classroom/, never an item of itself
        ("lf0", "t1", Kind.UNEXPECTED),  # a living file's name at the topic's root: nothing belongs there
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


def test_a_transcription_named_like_a_living_file_stays_a_transcription():
    photo = "Apuntes · pizarra.jpg · transcripción.pdf"  # the photo's own name starts like a living file
    new = {"name": photo, "mimeType": "application/pdf", "parents": ["ap"], "md5Checksum": "c001"}  # in notes/
    d, _ = drive({"changes": [{"fileId": "tx", "removed": False, "file": new}], "newStartPageToken": "9"})
    assert [(a.file_id, a.kind) for a in DriveChangeFeed(d).read("8", {}).arrivals] == [("tx", Kind.NOTES_TRANSCRIPT)]


def test_a_trashed_recorded_file_is_gone():
    tree = {f["id"]: f for f in fixture("tree.json")["files"]}
    trashed = {**{k: v for k, v in tree["it2"].items() if k != "id"}, "trashed": True}
    d, _ = drive({"changes": [{"fileId": "it2", "removed": False, "file": trashed}], "newStartPageToken": "9"})
    result = DriveChangeFeed(d).read("8", {"it2": Known(Kind.CLASSROOM_ITEM, "a006")})
    assert (result.gone, result.arrivals) == (["it2"], [])


def test_a_deep_path_under_reports_is_never_read_as_a_topic(tmp_path: Path):
    folder = "application/vnd.google-apps.folder"
    # reports/<a>/<b>/notes/ has a topic's shape one level down: only the skip keeps it out.
    deep = [("i1", "2026-2027", "inf"), ("i2", "FyQ", "i1"), ("i4", "notes", "i2")]
    files = fixture("tree.json")["files"]
    files += [{"id": i, "name": n, "mimeType": folder, "parents": [p]} for i, n, p in deep]
    files.append({"id": "img", "name": "foto.jpg", "mimeType": "image/jpeg", "parents": ["i4"], "md5Checksum": "z1"})
    t = TreeTransport(files)
    d = ScopedDrive.open(t, "acceso", "alfabeta", tmp_path / "drive.json")
    assert d.contains("img")
    assert "img" not in {a.file_id for a in DriveChangeFeed(d).read(None, {}).arrivals}


def test_a_recorded_file_moved_to_another_topic_arrives_there():
    folder = "application/vnd.google-apps.folder"
    other = (
        DriveFile("t2", "20261020 - Tema 02 - Otra", folder, ("fyq",)),
        DriveFile("ap2", "notes", folder, ("t2",)),
    )
    tree = {f["id"]: f for f in fixture("tree.json")["files"]}
    moved = {**{k: v for k, v in tree["f1"].items() if k != "id"}, "parents": ["ap2"]}
    d, _ = drive(
        {"changes": [{"fileId": "f1", "removed": False, "file": moved}], "newStartPageToken": "9"}, extra=other
    )
    result = DriveChangeFeed(d).read("8", {"f1": Known(Kind.NOTES_PHOTO, "a001", topic="t1")})
    assert [(a.file_id, a.topic) for a in result.arrivals] == [("f1", "t2")]
