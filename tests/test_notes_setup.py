"""`notebook setup` with a fake notebook (spec 005 T016, T017). Every value is invented."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pytest

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
        return list(self.sources)


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


def test_a_recorded_living_file_that_was_deleted_is_reported_not_recreated():
    drive, nb = drive_with_photo(), FakeNotebook()
    setup(drive, nb, [["foto-1"]])
    del drive.files[drive.named("Apuntes · Tema 01 - Materia inventada.pdf")[0]]
    out = setup(drive, nb)
    assert out["notes_source"] == "missing"
    assert not drive.named("Apuntes · Tema 01 - Materia inventada.pdf")


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
