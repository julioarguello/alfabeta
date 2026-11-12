"""`notebook prepare` with a fake notebook (spec 005 T016, T017, T028). Every value is invented."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pytest

from alfabeta.notes.changes import DriveChangeFeed
from alfabeta.notes.run import run_notes
from alfabeta.notes.setup import Setting, SetupError, setup_topic
from alfabeta.notes.sources import Source, SourcesError
from alfabeta.notes.state import STATE
from tests.notes_fakes import NOTES, TOPIC, MemoryDrive, ScriptedFeed, ScriptedTranscriber, deps

OWNER = "propietario.inventado@example.com"
TITLE = "3º ESO. FyQ. Tema 01 - Materia inventada"
SETTING = Setting("FyQ/20260915 - Tema 01 - Materia inventada", "{grade}. {subject}. {topic}", "3º ESO", OWNER)


@dataclass
class FakeNotebook:
    """A notebook with Tema 01's two plain sources from before living files."""

    notebooks: dict[str, str] = field(default_factory=lambda: {TITLE: "nb-1"})
    sources: list[Source] = field(
        default_factory=lambda: [Source("viejo-1", "Apuntes · Tema 01 (copia a mano)"), Source("libro", "libro.pdf")]
    )
    added: list[tuple[str, str]] = field(default_factory=lambda: [])
    fail_on_add: int = 0  # the nth add fails once, as nlm can
    unlisted: set[str] = field(default_factory=lambda: set[str]())  # held, but dropped by a short listing
    failing_reads: set[str] = field(default_factory=lambda: set[str]())  # reads that fail without saying why
    reads: list[str] = field(default_factory=lambda: [])

    def find_notebook(self, title: str) -> str | None:
        return self.notebooks.get(title)

    def add_drive_source(self, notebook: str, file_id: str, title: str) -> str:
        if self.fail_on_add and len(self.added) + 1 == self.fail_on_add:
            self.fail_on_add = 0
            raise SourcesError(signed_out=False)
        self.added.append((file_id, title))
        source = f"src-{len(self.added)}"  # like nlm: a new id on every add
        # Like NotebookLM, measured 2026-10-27: the title is the Drive file's name, `.pdf` included.
        self.sources.append(Source(source, f"{title}.pdf"))
        return source

    def list_sources(self, notebook: str) -> list[Source]:
        return [s for s in self.sources if s.id not in self.unlisted]

    def read_source(self, source_id: str) -> None:
        self.reads.append(source_id)
        if source_id in self.failing_reads:
            raise SourcesError(signed_out=False)
        if all(s.id != source_id for s in self.sources):
            raise SourcesError(signed_out=False, not_found=True)  # measured 2026-11-12 for a deleted source

    def session_ok(self) -> bool:
        raise AssertionError("setup never checks the session")

    def renew_session(self, browser: bool) -> bool:
        raise AssertionError("setup never renews the session")


class SetupDriveFake(MemoryDrive):
    def items(self):
        return list(self.files.values())


def drive_with_photo() -> SetupDriveFake:
    drive = SetupDriveFake()
    base = MemoryDrive.topic()
    drive.files.update(base.files)
    drive.put("foto-1", "IMG_0001.jpg", "image/jpeg", b"foto uno")
    return drive


def setup(drive: SetupDriveFake, nb: FakeNotebook, batches: list[list[str]] | None = None) -> dict[str, Any]:
    return setup_topic(deps(drive, ScriptedFeed(drive, batches or []), ScriptedTranscriber()), drive, nb, SETTING)


def test_a_first_setup_creates_shares_and_adds_exactly_two_files():
    drive, nb = drive_with_photo(), FakeNotebook()
    out = setup(drive, nb, [["foto-1"]])
    assert out == {"ok": True, "notes_source": "created", "classroom_source": "created", "plain_sources_to_remove": 1}
    notes = drive.named("Apuntes · Tema 01 - Materia inventada.pdf")
    classroom = drive.named("Classroom · Tema 01 - Materia inventada.pdf")
    assert len(notes) == len(classroom) == 1
    # Each in its folder of the topic: notes/ was there, classroom/ is made (constitution 2.2.0).
    assert drive.files[notes[0]].parents == (NOTES,)
    (made,) = drive.files[classroom[0]].parents
    assert (drive.files[made].name, drive.files[made].parents) == ("classroom", (TOPIC,))
    assert sorted(drive.shared) == sorted([(notes[0], OWNER), (classroom[0], OWNER)])
    assert [t for _, t in nb.added] == [
        "Apuntes · Tema 01 - Materia inventada",
        "Classroom · Tema 01 - Materia inventada",
    ]
    assert drive.bodies[notes[0]].endswith(b"foto-1/automatic")  # the recording pass ran first
    state = json.loads(drive.bodies[drive.named(STATE)[0]])
    assert state["files"]["foto-1"]["state"] == "in_living_file"


def test_a_second_setup_creates_adds_and_lists_nothing_new():
    drive, nb = drive_with_photo(), FakeNotebook()
    setup(drive, nb, [["foto-1"]])
    uploads, added = list(drive.uploads), list(nb.added)
    out = setup(drive, nb)
    assert out["notes_source"] == out["classroom_source"] == "unchanged"
    assert out["plain_sources_to_remove"] == 1  # its own living sources are not listed
    assert (drive.uploads, nb.added) == (uploads, added)
    assert nb.reads == []  # a source that is listed is not read: neither run asked the owner for one


def test_a_recorded_living_file_that_was_deleted_is_reported_not_recreated():
    drive, nb = drive_with_photo(), FakeNotebook()
    setup(drive, nb, [["foto-1"]])
    del drive.files[drive.named("Apuntes · Tema 01 - Materia inventada.pdf")[0]]
    out = setup(drive, nb)
    assert out["notes_source"] == "missing"
    assert not drive.named("Apuntes · Tema 01 - Materia inventada.pdf")


NOTES_TITLE = "Apuntes · Tema 01 - Materia inventada"


def recorded(drive: SetupDriveFake, kind: str = "notes") -> dict[str, Any]:
    return json.loads(drive.bodies[drive.named(STATE)[0]])["topics"][TOPIC]["living"][kind]


def test_a_source_deleted_from_the_notebook_is_added_again_once_from_the_same_file():
    # The student's accounts edit the notebook (spec 001 FR-011b), so a source can be deleted there (#235).
    drive, nb = drive_with_photo(), FakeNotebook()
    setup(drive, nb, [["foto-1"]])
    before = recorded(drive)
    nb.sources = [s for s in nb.sources if s.id != before["source_id"]]
    uploads, updates, shared = list(drive.uploads), list(drive.updates), list(drive.shared)
    out = setup(drive, nb)
    assert out == {
        "ok": True,
        "notes_source": "restored",
        "classroom_source": "unchanged",
        "plain_sources_to_remove": 1,
    }
    assert nb.added[2:] == [(before["file_id"], NOTES_TITLE)]  # the same Drive file, not a new one
    assert nb.reads == [before["source_id"]]  # asked for once, and it answered "not found"
    after = recorded(drive)
    assert after == before | {"source_id": "src-3"}  # only the source changes: same file, same build
    assert (drive.uploads, drive.shared) == (uploads, shared)  # no file is made and none is shared again
    assert [name for name in drive.updates[len(updates) :] if name.endswith(".pdf")] == []
    assert len(drive.named(f"{NOTES_TITLE}.pdf")) == 1
    again = setup(drive, nb)  # a third run finds the new source listed
    assert again["notes_source"] == "unchanged" and len(nb.added) == 3
    assert recorded(drive) == after


def test_a_source_put_back_but_not_recorded_is_taken_never_added_twice():
    # A repair that added the source and then lost its save (another writer, or nlm failing on the other
    # kind) runs again. Measured 2026-11-12: the notebook takes the same Drive file twice, so the title
    # is what keeps it to one (FR-009).
    drive, nb = drive_with_photo(), FakeNotebook()
    setup(drive, nb, [["foto-1"]])
    gone = recorded(drive)["source_id"]
    nb.sources = [s for s in nb.sources if s.id != gone] + [Source("puesta-otra-vez", f"{NOTES_TITLE}.pdf")]
    out = setup(drive, nb)
    assert (out["notes_source"], out["plain_sources_to_remove"]) == ("restored", 1)
    assert len(nb.added) == 2  # nothing was added
    assert recorded(drive)["source_id"] == "puesta-otra-vez"


def test_both_sources_deleted_are_both_added_again():
    drive, nb = drive_with_photo(), FakeNotebook()
    setup(drive, nb, [["foto-1"]])
    nb.sources = [s for s in nb.sources if not s.id.startswith("src-")]
    out = setup(drive, nb)
    assert out["notes_source"] == out["classroom_source"] == "restored"
    assert [t for _, t in nb.added[2:]] == [NOTES_TITLE, "Classroom · Tema 01 - Materia inventada"]
    assert (recorded(drive)["source_id"], recorded(drive, "classroom")["source_id"]) == ("src-3", "src-4")


def test_a_missing_living_file_gets_no_source_even_when_its_source_is_gone_too():
    from dataclasses import replace

    drive, nb = drive_with_photo(), FakeNotebook()
    setup(drive, nb, [["foto-1"]])
    before = recorded(drive)
    nb.sources = [s for s in nb.sources if s.id != before["source_id"]]
    notes = before["file_id"]
    drive.files[notes] = replace(drive.files[notes], parents=(TOPIC,))  # still in Drive, out of its folder
    out = setup(drive, nb)
    assert out["notes_source"] == "missing" and len(nb.added) == 2  # reported; nothing is added for it (FR-011)
    assert recorded(drive) == before | {"health": "missing"} and nb.reads == []
    drive.files[notes] = replace(drive.files[notes], parents=(NOTES,))  # put back: now it is repaired
    assert setup(drive, nb)["notes_source"] == "restored" and len(nb.added) == 3
    del drive.files[notes]  # deleted outright, with its new source gone as well
    nb.sources = [s for s in nb.sources if s.id != "src-3"]
    assert setup(drive, nb)["notes_source"] == "missing" and len(nb.added) == 3


def test_a_listing_that_comes_back_short_adds_nothing():
    # One listing is not proof of a deletion: the recorded source still answers, so it is left alone.
    drive, nb = drive_with_photo(), FakeNotebook()
    setup(drive, nb, [["foto-1"]])
    before = (recorded(drive), recorded(drive, "classroom"))
    nb.unlisted = {"src-1", "src-2"}
    out = setup(drive, nb)
    assert out["notes_source"] == out["classroom_source"] == "unchanged"
    assert len(nb.added) == 2 and nb.reads == ["src-1", "src-2"]
    assert (recorded(drive), recorded(drive, "classroom")) == before


def test_a_recorded_source_whose_read_fails_without_saying_why_stops_the_setup_and_adds_nothing():
    drive, nb = drive_with_photo(), FakeNotebook()
    setup(drive, nb, [["foto-1"]])
    before = recorded(drive)
    nb.unlisted, nb.failing_reads = {"src-1"}, {"src-1"}
    with pytest.raises(SourcesError):
        setup(drive, nb)
    assert len(nb.added) == 2 and recorded(drive) == before


def test_a_repair_stopped_after_one_source_adds_each_once_when_run_again():
    drive, nb = drive_with_photo(), FakeNotebook()
    setup(drive, nb, [["foto-1"]])
    nb.sources = [s for s in nb.sources if not s.id.startswith("src-")]
    nb.fail_on_add = 4  # the notes source is added again; nlm fails on the Classroom one
    with pytest.raises(SourcesError):
        setup(drive, nb)
    assert recorded(drive)["source_id"] == "src-1"  # nothing was recorded: the run stopped before its save
    out = setup(drive, nb)
    assert out["notes_source"] == out["classroom_source"] == "restored"
    assert [t for _, t in nb.added[2:]] == [NOTES_TITLE, "Classroom · Tema 01 - Materia inventada"]  # once each
    assert (recorded(drive)["source_id"], recorded(drive, "classroom")["source_id"]) == ("src-3", "src-4")
    assert sorted(s.title for s in nb.sources if s.id.startswith("src-")) == [
        f"{NOTES_TITLE}.pdf",
        "Classroom · Tema 01 - Materia inventada.pdf",
    ]


def test_a_living_file_at_the_topics_root_is_missing_until_it_is_back_in_its_folder():
    from dataclasses import replace

    drive, nb = drive_with_photo(), FakeNotebook()
    setup(drive, nb, [["foto-1"]])
    (notes,) = drive.named("Apuntes · Tema 01 - Materia inventada.pdf")
    drive.files[notes] = replace(drive.files[notes], parents=(TOPIC,))  # where it sat until #110
    assert setup(drive, nb)["notes_source"] == "missing"
    assert drive.named("Apuntes · Tema 01 - Materia inventada.pdf") == [notes]  # never a second one
    drive.files[notes] = replace(drive.files[notes], parents=(NOTES,))
    assert setup(drive, nb)["notes_source"] == "unchanged"
    state = json.loads(drive.bodies[drive.named(STATE)[0]])
    assert state["topics"][TOPIC]["living"]["notes"]["health"] == "ok"


def test_plain_sources_are_listed_never_removed():
    drive, nb = drive_with_photo(), FakeNotebook()
    setup(drive, nb, [["foto-1"]])
    assert Source("viejo-1", "Apuntes · Tema 01 (copia a mano)") in nb.sources


def test_no_notebook_stops_before_anything_is_written():
    drive, nb = drive_with_photo(), FakeNotebook(notebooks={})
    with pytest.raises(SetupError, match="no_notebook"):
        setup(drive, nb, [["foto-1"]])
    assert drive.uploads == []


def test_the_owner_address_is_in_no_output():
    drive, nb = drive_with_photo(), FakeNotebook()
    out = setup(drive, nb, [["foto-1"]])
    assert OWNER not in json.dumps(out)
    assert all(OWNER.encode() not in body for body in drive.bodies.values())


def test_a_setup_stopped_after_one_source_adds_each_source_once_when_run_again():
    drive, nb = drive_with_photo(), FakeNotebook(fail_on_add=2)
    with pytest.raises(SourcesError):
        setup(drive, nb, [["foto-1"]])
    out = setup(drive, nb)
    assert [t for _, t in nb.added] == [
        "Apuntes · Tema 01 - Materia inventada",
        "Classroom · Tema 01 - Materia inventada",
    ]
    assert out["plain_sources_to_remove"] == 1
    assert len(drive.named("Apuntes · Tema 01 - Materia inventada.pdf")) == 1
    assert len(drive.named("classroom")) == len(drive.named("Classroom · Tema 01 - Materia inventada.pdf")) == 1


def test_a_setup_whose_save_lost_a_race_adds_nothing_when_run_again():
    from alfabeta.notes.state import ConcurrentWriteError

    drive, nb = drive_with_photo(), FakeNotebook()
    made = deps(drive, ScriptedFeed(drive, [["foto-1"]]), ScriptedTranscriber())
    save = made.store.save
    calls: list[int] = []

    def lose_the_second(state: dict[str, Any]) -> bool:
        calls.append(1)
        if len(calls) == 2:  # the pass saved; setup's own save meets another writer
            raise ConcurrentWriteError
        return save(state)

    made.store.save = lose_the_second  # type: ignore[method-assign]
    with pytest.raises(ConcurrentWriteError):
        setup_topic(made, drive, nb, SETTING)
    setup(drive, nb)
    assert len(nb.added) == 2


def test_setup_builds_the_classroom_file_with_the_items_already_in_classroom():
    drive, nb = drive_with_photo(), FakeNotebook()
    drive.folder("cl", "classroom", TOPIC)
    drive.put("ficha", "20261001 - Ficha.pdf", "application/pdf", b"%PDF ficha", parent="cl")
    feed = DriveChangeFeed(drive)
    setup_topic(deps(drive, feed, ScriptedTranscriber()), drive, nb, SETTING)
    (classroom,) = drive.named("Classroom · Tema 01 - Materia inventada.pdf")
    assert drive.files[classroom].parents == ("cl",)
    expected = b"classroom:Tema 01 - Materia inventada:ficha[Ficha|||20261001 - Ficha.pdf/pdf=%PDF ficha]"
    assert drive.bodies[classroom] == expected
    state = json.loads(drive.bodies[drive.named(STATE)[0]])
    assert state["files"]["ficha"]["state"] == "in_living_file"
    writes = list(drive.updates)
    run_notes(deps(drive, feed, ScriptedTranscriber()))  # the next run finds it built already…
    # …and reports to the family that the topic's files are built (US4): the report, its snapshot, the log.
    assert drive.updates[len(writes) :] == ["Informe 20261027-0900.md", "state.json", "last-run.json"]
    writes = list(drive.updates)
    run_notes(deps(drive, feed, ScriptedTranscriber()))  # then nothing changes: only the run log
    assert drive.updates[len(writes) :] == ["last-run.json"]
