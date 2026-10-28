"""The topic's living notes file as step 5 of `exam prep` reads it: spec 005's records in Drive.

The records are `.alfabeta/state.json` at the root of the alfabeta folder, read through spec 004's
adapter with the student's link; the topic is the Drive folder of that name inside the subject's,
as `notebook setup` finds it. The revision time is the one Drive gives for the file now.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Any, cast

from alfabeta.exam.prep import LivingNotes, LivingNotesError
from alfabeta.google import accounts
from alfabeta.google.drive import DriveError, OutsideFolderError, ScopedDrive, cache_path
from alfabeta.google.keychain import KeychainError
from alfabeta.google.transport import TransportError, UrllibTransport
from alfabeta.notes.model import Health, LivingKind
from alfabeta.notes.state import DriveNotesStateStore

if TYPE_CHECKING:
    from alfabeta.config import StudentConfig
    from alfabeta.google.keychain import TokenStore


def _student_alias(cfg: StudentConfig) -> str:
    for alias, account in sorted(cfg.accounts.items()):
        if account.role == "student":
            return alias
    raise accounts.LinkError("no_student_account")


class DriveLivingNotes:
    """`LivingNotesReader` over the student's Drive, opened only when step 5 asks."""

    def __init__(self, cfg: StudentConfig, store: TokenStore) -> None:
        self._cfg = cfg
        self._store = store

    def living_notes(self, subject: str, folder: str) -> LivingNotes | None:
        """From the topic's record; None when it has no living notes file set up and in place."""
        try:
            return self._read(subject, folder)
        except (accounts.LinkError, DriveError, OutsideFolderError, TransportError, KeychainError) as err:
            raise LivingNotesError(type(err).__name__) from None

    def _read(self, subject: str, folder: str) -> LivingNotes | None:
        transport = UrllibTransport()
        token = accounts.access_token(self._cfg, _student_alias(self._cfg), self._store, transport)
        drive = ScopedDrive.open(transport, token, self._cfg.drive_root, cache_path(self._cfg))
        topics = [
            f
            for f in drive.items()
            if f.is_folder
            and f.name == folder
            and any(drive.contains(p) and drive.listed(p).name == subject for p in f.parents)
        ]
        if len(topics) != 1:
            return None
        state = DriveNotesStateStore(drive).load()
        record = cast("dict[str, dict[str, Any]]", state.get("topics", {})).get(topics[0].id, {})
        living = cast("dict[str, dict[str, Any]]", record.get("living", {}))
        notes = living.get(str(LivingKind.NOTES)) or {}
        file_id, source, built = (str(notes.get(k) or "") for k in ("file_id", "source_id", "built_md5"))
        if not (file_id and source and built) or notes.get("health", str(Health.OK)) != Health.OK:
            return None
        if not drive.contains(file_id):
            return None
        modified = drive.get(file_id).modified
        if not modified:
            return None
        return LivingNotes(source, built, dt.datetime.fromisoformat(modified))
