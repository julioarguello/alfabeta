"""In-memory doubles of the notes ports. Every id, name and value is invented."""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from alfabeta.google.drive import FOLDER, Change, DriveError, DriveFile, OutsideFolderError
from alfabeta.notes.changes import FeedResult, Known
from alfabeta.notes.model import Arrival, Kind, PartKind, PhotoState, RanOn
from alfabeta.notes.run import NotesDeps
from alfabeta.notes.sources import NlmMissingError, Source, SourcesError
from alfabeta.notes.state import DriveNotesStateStore
from alfabeta.notes.transcribe import Transcription

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from alfabeta.config import StudentConfig
    from alfabeta.google.keychain import TokenStore
    from alfabeta.notes.changes import ChangeFeed
    from alfabeta.notes.model import ClassroomEntry, NotesPage, Topic
    from alfabeta.notes.pdf import RenderedPart

MADRID = ZoneInfo("Europe/Madrid")
TOPIC = "t1"
NOTES = "ap1"
# The Classroom tree of `MemoryDrive.subject()`: each topic's `classroom/`.
CLASSROOM = "cl1"
TOPIC_2, CLASSROOM_2 = "t2", "cl2"
NO_TOPIC, CLASSROOM_0 = "t0", "cl0"


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
    exports: list[str] = field(default_factory=lambda: [])
    conversions: list[str] = field(default_factory=lambda: [])
    unreadable: set[str] = field(default_factory=lambda: set())  # reading these fails, as Drive can
    changed: list[str] = field(default_factory=lambda: [])  # what the feed reports on its next page
    tokens: int = 0

    @classmethod
    def topic(cls) -> MemoryDrive:
        """alfabeta/2026-2027/FyQ/20260915 - Tema 01 - Materia inventada/notes/"""
        drive = cls()
        for fid, name, parent in (
            ("anio", "2026-2027", "raiz"),
            ("fyq", "FyQ", "anio"),
            (TOPIC, "20260915 - Tema 01 - Materia inventada", "fyq"),
            (NOTES, "notes", TOPIC),
        ):
            drive.files[fid] = DriveFile(fid, name, FOLDER, (parent,))
        return drive

    @classmethod
    def subject(cls) -> MemoryDrive:
        """alfabeta/2026-2027/FyQ/ with Tema 01 (notes/ and classroom/), Tema 02, later, and No topic."""
        drive = cls.topic()
        for fid, name, parent in (
            (CLASSROOM, "classroom", TOPIC),
            (TOPIC_2, "20261020 - Tema 02 - Otra materia", "fyq"),
            (CLASSROOM_2, "classroom", TOPIC_2),
            (NO_TOPIC, "20260910 - No topic", "fyq"),
            (CLASSROOM_0, "classroom", NO_TOPIC),
        ):
            drive.files[fid] = DriveFile(fid, name, FOLDER, (parent,))
        return drive

    def folder(self, fid: str, name: str, parent: str) -> DriveFile:
        self.files[fid] = DriveFile(fid, name, FOLDER, (parent,))
        return self.files[fid]

    def touch(self, *fids: str) -> None:
        """What the feed's next page reports as changed."""
        self.changed += fids

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
        self._readable(file_id)
        return self.bodies[file_id]

    def _readable(self, file_id: str) -> None:
        if file_id in self.unreadable:
            raise DriveError("Drive API returned 500", 500)

    def children(self, folder_id: str) -> list[DriveFile]:
        if not self.contains(folder_id):
            raise OutsideFolderError  # as ScopedDrive: an id outside the listing is refused
        found = (f for f in self.files.values() if folder_id in f.parents and not f.trashed)
        return sorted(found, key=lambda f: (f.name, f.id))

    def listing(self, folder_id: str) -> list[DriveFile]:
        return self.children(folder_id)

    def export(self, file_id: str, mime_type: str = "application/pdf") -> bytes:
        self.exports.append(file_id)
        self._readable(file_id)
        return f"export:{file_id}".encode()

    def convert(self, file_id: str, folder_id: str, google_type: str, properties: dict[str, str]) -> bytes:
        """Like Drive's: a leftover copy is trashed, the new copy is exported and trashed at once."""
        for left in self.children(folder_id):
            if all(left.prop(k) == v for k, v in properties.items()):
                self.files[left.id] = replace(left, trashed=True)
        self._readable(file_id)
        fid = self._new_id()
        self.files[fid] = DriveFile(
            fid, self.files[file_id].name, google_type, (folder_id,), properties=tuple(sorted(properties.items()))
        )
        self.conversions.append(file_id)
        self.files[fid] = replace(self.files[fid], trashed=True)
        return f"office:{file_id}".encode()

    # FeedSource: the first read lists the tree, a later one reports what `touch` named ------------

    def items(self) -> list[DriveFile]:
        return [f for f in self.files.values() if not f.trashed]

    def relist(self) -> None:
        pass

    def ancestors(self, item_id: str) -> list[DriveFile]:
        chain: list[DriveFile] = []
        parents = self.files[item_id].parents
        while parents and parents[0] in self.files:
            chain.append(self.files[parents[0]])
            parents = self.files[parents[0]].parents
        return chain[::-1]

    def start_page_token(self) -> str:
        self.tokens += 1
        return f"c{self.tokens}"

    def changes(self, page_token: str, known_ids: frozenset[str]) -> tuple[list[Change], str]:
        kept: list[Change] = []
        for fid in self.changed:
            if fid in self.files and not self.files[fid].trashed:
                kept.append(Change(fid, left=False, file=self.files[fid]))
            elif fid in known_ids:
                kept.append(Change(fid, left=True))
        self.changed = []
        return kept, self.start_page_token()

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
        """`classroom:<topic>:` then per entry, in posting order, `<id>[title|description|addresses|parts]`,
        each part as `<name>/<kind>=<its bytes>`."""
        shown = [
            f"{e.item_id}[{e.title}|{e.description}|{','.join(e.addresses)}|"
            + ",".join(f"{r.part.name}/{r.part.kind}={r.content.decode()}" for r in parts)
            + "]"
            for e, parts in sorted(entries, key=lambda e: (e[0].posted, e[0].title))
        ]
        pages = 1 + sum(1 + sum(r.part.kind != PartKind.NAMED for r in parts) for _, parts in entries)
        return f"classroom:{topic.name}:{';'.join(shown)}".encode(), pages

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
class ScriptedAnswerer:
    """The report's "what it adds": answers in order; with nothing scripted, a fixed Spanish bullet."""

    answers: list[Transcription] = field(default_factory=lambda: [])
    prompts: list[str] = field(default_factory=lambda: [])

    def answer(self, prompt: str) -> Transcription:
        self.prompts.append(prompt)
        if self.answers:
            return self.answers.pop(0)
        from alfabeta.notes.model import Usage

        return Transcription(
            PhotoState.TRANSCRIBED, "- La guía no cubre los métodos de separación de mezclas.\n", Usage(5000, 200)
        )


@dataclass
class FixedClock:
    when: dt.datetime = field(default_factory=lambda: dt.datetime(2026, 10, 27, 9, 0, tzinfo=MADRID))

    def now(self) -> dt.datetime:
        return self.when


def deps(
    drive: MemoryDrive,
    feed: ChangeFeed,
    transcriber: ScriptedTranscriber | None,
    clock: FixedClock | None = None,
    warn_pages: int = 100,
    answerer: ScriptedAnswerer | None = None,
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
        answerer=answerer,
    )


def fixed(made: NotesDeps, drive: MemoryDrive) -> Callable[[StudentConfig, TokenStore, RanOn], tuple[NotesDeps, Any]]:
    """A `notes_deps` factory that hands out these fakes."""

    def factory(cfg: StudentConfig, store: TokenStore, ran_on: RanOn) -> tuple[NotesDeps, Any]:
        return made, drive

    return factory


# --- the owner's refresh (spec 005 T045) ---


@dataclass
class FakeOwner:
    """The notebook owner's `nlm`, scripted; records every call in order."""

    sessions: list[bool] = field(default_factory=lambda: [True])  # one per check; the last repeats
    renewals: list[bool] = field(default_factory=lambda: [])  # whether each renewal ran; True when empty
    failing: dict[str, SourcesError] = field(default_factory=lambda: {})  # reads that fail, by source id
    missing: bool = False  # `nlm` cannot be run
    calls: list[str] = field(default_factory=lambda: [])

    def session_ok(self) -> bool:
        self.calls.append("check")
        if self.missing:
            raise NlmMissingError
        return self.sessions.pop(0) if len(self.sessions) > 1 else self.sessions[0]

    def renew_session(self, browser: bool) -> bool:
        self.calls.append("renew browser" if browser else "renew http-only")
        return self.renewals.pop(0) if self.renewals else True

    def read_source(self, source_id: str) -> None:
        self.calls.append(f"read {source_id}")
        if source_id in self.failing:
            raise self.failing[source_id]

    def find_notebook(self, title: str) -> str | None:
        raise AssertionError("the refresh never looks for a notebook")

    def add_drive_source(self, notebook: str, file_id: str, title: str) -> str:
        raise AssertionError("the refresh never adds a source (FR-011)")

    def list_sources(self, notebook: str) -> list[Source]:
        raise AssertionError("the refresh never lists sources")


@dataclass
class FakeState:
    """`state.json` as the refresh reads it."""

    state: dict[str, Any] = field(default_factory=lambda: {})
    loads: int = 0

    def load(self) -> dict[str, Any]:
        self.loads += 1
        return copy.deepcopy(self.state)


@dataclass
class FakeNotifier:
    """The Mac's notifications, recorded."""

    texts: list[str] = field(default_factory=lambda: [])

    def notify(self, text: str) -> None:
        self.texts.append(text)


def living_state(*living: tuple[str, str | None, str | None, str]) -> dict[str, Any]:
    """`state.json` with one topic per (kind, source id, built checksum, health); invented ids."""
    topics: dict[str, Any] = {}
    for n, (kind, source, md5, health) in enumerate(living):
        record = {"file_id": f"vivo-{n}", "source_id": source, "built_md5": md5, "pages": 1, "health": health}
        topics[f"tema-{n}"] = {"name": f"2026091{n} - Tema 0{n} - Materia inventada", "living": {kind: record}}
    return {"topics": topics}
