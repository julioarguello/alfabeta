"""The cloud run's records in the student's Drive (spec 005 research R2, R4; data-model.md).

`.alfabeta/state.json` holds the records and is written only when one changed (SC-004);
`.alfabeta/last-run.json` is the run's own log, with the change cursor, written every run;
`.alfabeta/conversions/` holds an Office file's Google copy for the moment it is exported. Three
writers share them (the cloud run, `notebook setup` and `notes run` on the Mac), so a write first
checks that nobody wrote since the read.
"""

from __future__ import annotations

import datetime as dt
import json
from typing import TYPE_CHECKING, Any, Protocol, cast

from alfabeta.notes.model import RanOn, RunLog, RunResult

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from alfabeta.google.drive import DriveFile

FOLDER_NAME = ".alfabeta"
STATE = "state.json"
RUN_LOG = "last-run.json"
JSON = "application/json"


class ConcurrentWriteError(Exception):
    """Another writer changed `state.json` since this run read it (research R4)."""

    def __init__(self) -> None:
        super().__init__("state.json changed since it was read; nothing written")


class DriveFiles(Protocol):
    """What the store needs of spec 004's `ScopedDrive`."""

    @property
    def root(self) -> DriveFile:
        """The alfabeta folder."""
        ...

    def lookup(self, folder_id: str, name: str) -> DriveFile | None:
        """The item with that name in the folder, asked of Drive now."""
        ...

    def create_folder(self, parent_id: str, name: str) -> DriveFile:
        """A new folder."""
        ...

    def upload(self, parent_id: str, name: str, content: bytes, mime_type: str) -> DriveFile:
        """A new file, confirmed."""
        ...

    def update(self, file_id: str, content: bytes, mime_type: str) -> DriveFile:
        """New content on the same id, confirmed."""
        ...

    def content(self, file_id: str) -> bytes:
        """The file's bytes."""
        ...

    def head_revision(self, file_id: str) -> str | None:
        """The file's head revision, read now."""
        ...


class NotesStateStore(Protocol):
    """The records and the run log of one student's cloud run."""

    def load(self) -> dict[str, Any]:
        """The records, `{}` before the first write."""
        ...

    def save(self, state: Mapping[str, Any]) -> bool:
        """Write the records if they changed; False when nothing was written."""
        ...

    def load_run_log(self) -> RunLog | None:
        """The previous run's log, None before the first run."""
        ...

    def save_run_log(self, log: RunLog) -> None:
        """Write this run's log; every run does."""
        ...

    def own_ids(self) -> frozenset[str]:
        """The ids of every file the store wrote: their changes are echoes."""
        ...

    def work_folder(self, name: str) -> str:
        """The id of a folder inside `.alfabeta/`, made when missing."""
        ...


def _dumps(data: Mapping[str, Any]) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n").encode()


def run_log_json(log: RunLog) -> dict[str, Any]:
    """A run log as JSON."""

    def iso(value: dt.datetime | None) -> str | None:
        return value.isoformat() if value else None

    return {
        "started": iso(log.started),
        "ended": iso(log.ended),
        "result": str(log.result),
        "ran_on": str(log.ran_on),
        "last_ok_ended": iso(log.last_ok_ended),
        "page_token": log.page_token,
    }


def run_log_of(data: Mapping[str, Any]) -> RunLog:
    """A run log from its JSON."""

    def when(value: object) -> dt.datetime | None:
        return dt.datetime.fromisoformat(str(value)) if value else None

    started, ended = when(data["started"]), when(data["ended"])
    assert started is not None and ended is not None
    return RunLog(
        started=started,
        ended=ended,
        result=RunResult(data["result"]),
        ran_on=RanOn(data["ran_on"]),
        last_ok_ended=when(data.get("last_ok_ended")),
        page_token=cast("str | None", data.get("page_token")),
    )


class DriveNotesStateStore:
    """`NotesStateStore` in `.alfabeta/` at the root of the alfabeta folder."""

    def __init__(self, drive: DriveFiles) -> None:
        self._drive = drive
        self._folder: DriveFile | None = None
        self._read: bytes | None = None  # state.json as read, None before load
        self._revision: str | None = None
        self._own: set[str] = set()
        self._work: dict[str, str] = {}

    def _file(self, name: str) -> DriveFile | None:
        """Asked of Drive every time: another writer may have created it since this run started."""
        folder = self._state_folder(create=False)
        if folder is None:
            return None
        found = self._drive.lookup(folder.id, name)
        return found if found is not None and not found.is_folder else None

    def _state_folder(self, *, create: bool) -> DriveFile | None:
        if self._folder is None:
            root = self._drive.root.id
            found = self._drive.lookup(root, FOLDER_NAME)
            if found is None and create:
                found = self._drive.create_folder(root, FOLDER_NAME)
            self._folder = found
        if self._folder is not None:
            self._own.add(self._folder.id)
        return self._folder

    def load(self) -> dict[str, Any]:
        """The records; remembers the revision they were read at."""
        found = self._file(STATE)
        if found is None:
            self._read, self._revision = b"", None
            return {}
        self._own.add(found.id)
        self._revision = self._drive.head_revision(found.id)
        self._read = self._drive.content(found.id)
        return cast("dict[str, Any]", json.loads(self._read))

    def save(self, state: Mapping[str, Any]) -> bool:
        """Write only a change, and only if nobody wrote since `load` (research R4)."""
        if self._read is None:
            raise RuntimeError("save before load")
        body = _dumps(state)
        if body == self._read or (not state and not self._read):
            return False
        found = self._file(STATE)
        current = self._drive.head_revision(found.id) if found else None
        if current != self._revision:
            raise ConcurrentWriteError
        folder = self._state_folder(create=True)
        assert folder is not None
        written = (
            self._drive.update(found.id, body, JSON) if found else self._drive.upload(folder.id, STATE, body, JSON)
        )
        self._own.add(written.id)
        self._read, self._revision = body, self._drive.head_revision(written.id)
        return True

    def load_run_log(self) -> RunLog | None:
        """The previous run's log."""
        found = self._file(RUN_LOG)
        if found is None:
            return None
        self._own.add(found.id)
        return run_log_of(json.loads(self._drive.content(found.id)))

    def save_run_log(self, log: RunLog) -> None:
        """This run's log, written every run: the one write an idle run makes."""
        body = _dumps(run_log_json(log))
        found = self._file(RUN_LOG)
        folder = self._state_folder(create=True)
        assert folder is not None
        written = (
            self._drive.update(found.id, body, JSON) if found else self._drive.upload(folder.id, RUN_LOG, body, JSON)
        )
        self._own.add(written.id)

    def own_ids(self) -> frozenset[str]:
        """The `.alfabeta` folder and the files this store read or wrote."""
        return frozenset(self._own)

    def work_folder(self, name: str) -> str:
        """The id of a folder inside `.alfabeta/`, such as `conversions/` for Office copies (research R6)."""
        if name not in self._work:
            folder = self._state_folder(create=True)
            assert folder is not None
            found = self._drive.lookup(folder.id, name)
            self._work[name] = (found if found is not None else self._drive.create_folder(folder.id, name)).id
        return self._work[name]


def retry_once[T](run: Callable[[], T]) -> T:
    """Run again from the start once if another writer got there first; a second clash propagates."""
    try:
        return run()
    except ConcurrentWriteError:
        return run()
