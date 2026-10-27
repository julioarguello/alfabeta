"""The cloud run's records in Drive (spec 005 T007, T008). Every id and value is invented."""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

import pytest

from alfabeta.google.drive import FOLDER, DriveFile
from alfabeta.notes.model import RanOn, RunLog, RunResult
from alfabeta.notes.state import (
    RUN_LOG,
    STATE,
    ConcurrentWriteError,
    DriveNotesStateStore,
    retry_once,
    run_log_json,
    run_log_of,
)

T0 = dt.datetime(2026, 10, 27, 9, 0, tzinfo=ZoneInfo("Europe/Madrid"))


@dataclass
class MemoryDrive:
    """`DriveFiles` in memory; counts writes and lets a test play the other writer."""

    root: DriveFile = field(default_factory=lambda: DriveFile("raiz", "alfabeta", FOLDER))
    files: dict[str, DriveFile] = field(default_factory=lambda: {})
    bodies: dict[str, bytes] = field(default_factory=lambda: {})
    revisions: dict[str, int] = field(default_factory=lambda: {})
    writes: list[str] = field(default_factory=lambda: [])

    def lookup(self, folder_id: str, name: str) -> DriveFile | None:
        return next((f for f in self.files.values() if folder_id in f.parents and f.name == name), None)

    def create_folder(self, parent_id: str, name: str) -> DriveFile:
        made = DriveFile(f"id-{len(self.files)}", name, FOLDER, (parent_id,))
        self.files[made.id] = made
        self.writes.append(name)
        return made

    def upload(self, parent_id: str, name: str, content: bytes, mime_type: str) -> DriveFile:
        made = DriveFile(f"id-{len(self.files)}", name, mime_type, (parent_id,))
        self.files[made.id] = made
        return self.update(made.id, content, mime_type)

    def update(self, file_id: str, content: bytes, mime_type: str) -> DriveFile:
        self.bodies[file_id] = content
        self.revisions[file_id] = self.revisions.get(file_id, 0) + 1
        self.writes.append(self.files[file_id].name)
        return self.files[file_id]

    def content(self, file_id: str) -> bytes:
        return self.bodies[file_id]

    def head_revision(self, file_id: str) -> str | None:
        return f"r{self.revisions[file_id]}" if file_id in self.revisions else None

    def named(self, name: str) -> str:
        return next(f.id for f in self.files.values() if f.name == name)


def test_records_round_trip_and_only_a_change_is_written():
    drive = MemoryDrive()
    store = DriveNotesStateStore(drive)
    assert store.load() == {}
    assert not store.save({})  # nothing read, nothing to write
    assert store.save({"files": {"foto-1": {"state": "seen"}}})
    assert not store.save({"files": {"foto-1": {"state": "seen"}}})
    again = DriveNotesStateStore(drive)
    assert again.load() == {"files": {"foto-1": {"state": "seen"}}}
    assert not again.save({"files": {"foto-1": {"state": "seen"}}})
    assert drive.writes.count(STATE) == 1


def test_a_write_by_another_run_since_the_read_stops_the_save():
    drive = MemoryDrive()
    DriveNotesStateStore(drive).load()
    first = DriveNotesStateStore(drive)
    first.load()
    first.save({"n": 1})
    mine = DriveNotesStateStore(drive)
    mine.load()
    drive.update(drive.named(STATE), b'{"n": 2}\n', "application/json")  # the Mac wrote meanwhile
    with pytest.raises(ConcurrentWriteError):
        mine.save({"n": 3})
    assert json.loads(drive.bodies[drive.named(STATE)]) == {"n": 2}


def test_a_state_created_by_another_run_since_an_empty_read_stops_the_save():
    drive = MemoryDrive()
    mine = DriveNotesStateStore(drive)
    assert mine.load() == {}
    other = DriveNotesStateStore(drive)
    other.load()
    other.save({"n": 1})
    with pytest.raises(ConcurrentWriteError):
        mine.save({"n": 2})


def test_retry_once_runs_again_from_the_start_then_gives_up():
    attempts: list[int] = []

    def clashes_once() -> str:
        attempts.append(1)
        if len(attempts) == 1:
            raise ConcurrentWriteError
        return "hecho"

    assert retry_once(clashes_once) == "hecho"
    assert len(attempts) == 2

    def always() -> str:
        raise ConcurrentWriteError

    with pytest.raises(ConcurrentWriteError):
        retry_once(always)


def test_the_run_log_is_written_every_run_and_read_back():
    drive = MemoryDrive()
    store = DriveNotesStateStore(drive)
    assert store.load_run_log() is None
    log = RunLog(T0, T0, RunResult.OK, RanOn.CLOUD, last_ok_ended=T0, page_token="100")
    store.save_run_log(log)
    store.save_run_log(log)
    assert drive.writes.count(RUN_LOG) == 2
    assert DriveNotesStateStore(drive).load_run_log() == log


def test_every_file_the_store_touches_is_its_own():
    drive = MemoryDrive()
    store = DriveNotesStateStore(drive)
    store.load()
    store.save({"n": 1})
    store.save_run_log(RunLog(T0, T0, RunResult.OK, RanOn.MAC))
    assert store.own_ids() == {drive.named(".alfabeta"), drive.named(STATE), drive.named(RUN_LOG)}


def test_run_log_json_keeps_every_field():
    log = RunLog(T0, T0 + dt.timedelta(minutes=2), RunResult.PARTIAL, RanOn.CLOUD, None, "7")
    assert run_log_of(run_log_json(log)) == log
    assert run_log_json(log)["last_ok_ended"] is None
