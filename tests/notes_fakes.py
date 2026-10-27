"""In-memory doubles of the notes ports. Every id, name and value is invented."""

from __future__ import annotations

import datetime as dt
import hashlib
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from alfabeta.google.drive import FOLDER, DriveError, DriveFile, OutsideFolderError
from alfabeta.notes.changes import FeedResult, Known
from alfabeta.notes.model import Arrival, Kind, PhotoState, RanOn
from alfabeta.notes.run import NotesDeps
from alfabeta.notes.state import DriveNotesStateStore
from alfabeta.notes.transcribe import Transcription

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from alfabeta.config import StudentConfig
    from alfabeta.google.keychain import TokenStore
    from alfabeta.notes.model import ClassroomEntry, NotesPage, Topic
    from alfabeta.notes.pdf import RenderedPart

MADRID = ZoneInfo("Europe/Madrid")
TOPIC = "t1"
NOTES = "ap1"


@dataclass
class MemoryDrive:
    """A Drive tree in memory: what `ScopedDrive` answers, without HTTP."""

    root: DriveFile = field(default_factory=lambda: DriveFile("raiz", "alfabeta", FOLDER))
    files: dict[str, DriveFile] = field(default_factory=lambda: {})
    bodies: dict[str, bytes] = field(default_factory=lambda: {})
    revisions: dict[str, int] = field(default_factory=lambda: {})
    uploads: list[str] = field(default_factory=lambda: [])
    updates: list[str] = field(default_factory=lambda: [])
    shared: list[tuple[str, str]] = field(default_factory=lambda: [])
    fail_writes: bool = False
    made: int = 0
    downloads: list[str] = field(default_factory=lambda: [])

    @classmethod
    def topic(cls) -> MemoryDrive:
        """alfabeta/2026-2027/FyQ/20260915 - Tema 01 - Materia inventada/apuntes/"""
        drive = cls()
        for fid, name, parent in (
            ("anio", "2026-2027", "raiz"),
            ("fyq", "FyQ", "anio"),
            (TOPIC, "20260915 - Tema 01 - Materia inventada", "fyq"),
            (NOTES, "apuntes", TOPIC),
        ):
            drive.files[fid] = DriveFile(fid, name, FOLDER, (parent,))
        return drive

    def put(self, fid: str, name: str, mime: str, body: bytes, parent: str = NOTES) -> DriveFile:
        md5 = hashlib.md5(body).hexdigest()
        self.files[fid] = DriveFile(fid, name, mime, (parent,), len(body), md5)
        self.bodies[fid] = body
        return self.files[fid]

    def _new_id(self) -> str:
        self.made += 1
        return f"nuevo-{self.made}"

    # NotesDrive and DriveFiles ------------------------------------------------------------------

    def listed(self, item_id: str) -> DriveFile:
        if item_id not in self.files and item_id != self.root.id:
            raise OutsideFolderError
        return self.files.get(item_id, self.root)

    def contains(self, item_id: str) -> bool:
        return item_id in self.files or item_id == self.root.id

    def content(self, file_id: str) -> bytes:
        self.downloads.append(file_id)
        return self.bodies[file_id]

    def made_for(self, folder_id: str, properties: dict[str, str]) -> DriveFile | None:
        found = [
            f
            for f in self.files.values()
            if folder_id in f.parents and not f.trashed and all(f.prop(k) == v for k, v in properties.items())
        ]
        return sorted(found, key=lambda f: f.id)[0] if found else None

    def upload(
        self, parent_id: str, name: str, content: bytes, mime_type: str, properties: dict[str, str] | None = None
    ) -> DriveFile:
        if self.fail_writes:
            raise DriveError("Drive API returned 500", 500)
        fid = self._new_id()
        self.files[fid] = DriveFile(
            fid, name, mime_type, (parent_id,), properties=tuple(sorted((properties or {}).items()))
        )
        self.uploads.append(name)
        return self._store(fid, content)

    def update(
        self, file_id: str, content: bytes, mime_type: str, properties: dict[str, str] | None = None
    ) -> DriveFile:
        if self.fail_writes:
            raise DriveError("Drive API returned 500", 500)
        current = self.files[file_id]
        if properties:
            self.files[file_id] = replace(current, properties=tuple(sorted(properties.items())))
        self.updates.append(current.name)
        return self._store(file_id, content)

    def _store(self, fid: str, content: bytes) -> DriveFile:
        md5 = hashlib.md5(content).hexdigest()
        self.files[fid] = replace(self.files[fid], size=len(content), md5=md5)
        self.bodies[fid] = content
        self.revisions[fid] = self.revisions.get(fid, 0) + 1
        return self.files[fid]

    def lookup(self, folder_id: str, name: str) -> DriveFile | None:
        return next((f for f in self.files.values() if folder_id in f.parents and f.name == name), None)

    def create_folder(self, parent_id: str, name: str) -> DriveFile:
        fid = self._new_id()
        self.files[fid] = DriveFile(fid, name, FOLDER, (parent_id,))
        self.uploads.append(name)
        return self.files[fid]

    def head_revision(self, file_id: str) -> str | None:
        return f"r{self.revisions[file_id]}" if file_id in self.revisions else None

    def share_reader(self, file_id: str, address: str) -> None:
        self.shared.append((file_id, address))

    def named(self, name: str) -> list[str]:
        return [f.id for f in self.files.values() if f.name == name]


@dataclass
class ScriptedFeed:
    """Hands out the arrivals a test lists, then nothing; records the cursor it was read from."""

    drive: MemoryDrive
    batches: list[list[str]]
    cursors: list[str | None] = field(default_factory=lambda: [])

    def read(self, cursor: str | None, known: Mapping[str, Known]) -> FeedResult:
        self.cursors.append(cursor)
        ids = self.batches.pop(0) if self.batches else []
        arrivals: list[Arrival] = []
        for fid in ids:
            item = self.drive.files[fid]
            kind = Kind.NOTES_PHOTO if item.mime_type.startswith("image/") else Kind.NOTES_TEXT
            arrivals.append(Arrival(fid, TOPIC, kind, item.version))
        return FeedResult(f"c{len(self.cursors)}", arrivals)


@dataclass
class CountingPdf:
    """A `PdfBuilder` whose bytes name what went in; a notes file has 1 + 2 pages per page."""

    def notes(self, topic: Topic, pages: Sequence[tuple[NotesPage, bytes]]) -> tuple[bytes, int]:
        return (f"notes:{topic.name}:" + ",".join(f"{p.photo_id}/{p.review}" for p, _ in pages)).encode(), 1 + 2 * len(
            pages
        )

    def classroom(
        self, topic: Topic, entries: Sequence[tuple[ClassroomEntry, Sequence[RenderedPart]]]
    ) -> tuple[bytes, int]:
        return f"classroom:{topic.name}:{len(entries)}".encode(), 1 + len(entries)

    def page(self, page: NotesPage, image: bytes) -> bytes:
        return f"page:{page.photo_id}:{page.markdown}".encode()


@dataclass
class ScriptedTranscriber:
    """Answers in order; with nothing scripted, a page naming the photo's bytes."""

    answers: list[Transcription] = field(default_factory=lambda: [])
    calls: int = 0

    def transcribe(self, image: bytes, mime_type: str) -> Transcription:
        self.calls += 1
        if self.answers:
            return self.answers.pop(0)
        from alfabeta.notes.model import Usage

        return Transcription(PhotoState.TRANSCRIBED, f"## Página\n\nTexto de {image.decode()}\n", Usage(3000, 800))


@dataclass
class FixedClock:
    when: dt.datetime = field(default_factory=lambda: dt.datetime(2026, 10, 27, 9, 0, tzinfo=MADRID))

    def now(self) -> dt.datetime:
        return self.when


def deps(
    drive: MemoryDrive,
    feed: ScriptedFeed,
    transcriber: ScriptedTranscriber | None,
    clock: FixedClock | None = None,
    warn_pages: int = 100,
) -> NotesDeps:
    return NotesDeps(
        drive=drive,
        store=DriveNotesStateStore(drive),
        feed=feed,
        pdf=CountingPdf(),
        transcriber=transcriber,
        clock=clock or FixedClock(),
        model="claude-sonnet-5-5",
        prices=(2.0, 10.0),
        warn_pages=warn_pages,
        ran_on=RanOn.CLOUD,
    )


def fixed(made: NotesDeps, drive: MemoryDrive) -> Callable[[StudentConfig, TokenStore, RanOn], tuple[NotesDeps, Any]]:
    """A `notes_deps` factory that hands out these fakes."""

    def factory(cfg: StudentConfig, store: TokenStore, ran_on: RanOn) -> tuple[NotesDeps, Any]:
        return made, drive

    return factory
