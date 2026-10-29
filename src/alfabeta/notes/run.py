"""One pass of the notes: new photos become pages, changed living files are rebuilt (spec 005 R2, R4 to R6).

The pass reads the records and the run log, reads the change feed from the cursor, records what
arrived, transcribes the pending photos, writes each page's Markdown and PDF next to its photo, checks
every recorded Classroom item against this run's listing, and rebuilds the living files of every
topic that changed. It never creates a living file: only `notebook setup` does (research R6). It
writes `state.json` only when a record changed, and the run log always. A run that changed
something leaves the family's report in `reports/` (report.py). It calls no study-pack generation
(FR-012).
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, field, replace
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any, Protocol, cast

from alfabeta.google.drive import DriveError, OutsideFolderError
from alfabeta.notes.changes import LIVING_FOLDERS, Known
from alfabeta.notes.model import (
    OFFICE_TYPES,
    Arrival,
    ClassroomEntry,
    ClassroomItem,
    ItemState,
    Kind,
    LivingFile,
    LivingKind,
    NotesPage,
    PageSource,
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
    addresses,
    is_announcement,
    is_part,
    part_kind,
    posted_title,
)
from alfabeta.notes.pdf import RenderedPart
from alfabeta.notes.report import baseline, write_report
from alfabeta.placement import NO_TOPIC

if TYPE_CHECKING:
    from alfabeta.google.drive import DriveFile
    from alfabeta.notes.changes import ChangeFeed
    from alfabeta.notes.model import Clock
    from alfabeta.notes.pdf import PdfBuilder
    from alfabeta.notes.state import NotesStateStore
    from alfabeta.notes.transcribe import Answerer, Transcriber

FOR = "alfabeta_for"
ROLE = "alfabeta_role"
VERSION = "alfabeta_version"
PDF = "application/pdf"
MARKDOWN = "text/markdown"
_DATED = re.compile(r"^\d{8} - (.+)$")
CONVERSIONS = "conversions"  # in `.alfabeta/`: an Office file's Google copy while it is exported
# What spec 001 writes in an item's folder for its cover: a material's description, an assignment's
# statement (placement.py), and the links it did not download.
_DESCRIPTIONS = frozenset({"descripcion.md", "enunciado.md"})
_LINKS = "enlaces.md"
# An item whose entry is in its living file or due to be; `failed_final` waits until it changes.
_FILED = frozenset({ItemState.SEEN, ItemState.IN_LIVING_FILE, ItemState.FAILED})
_DUE = frozenset({ItemState.SEEN, ItemState.FAILED})
_HEADING = re.compile(r"^#{1,6} ", re.MULTILINE)
# What a report counts per topic (contracts/cli.md); a topic is an opaque index, never a name or id.
COUNTS = (
    "pages_added",
    "items_added",
    "duplicates",
    "unsupported",
    "unreadable",
    "gone",
    "marks",
    "unexpected",
    "waiting_setup",
    "missing_living_files",
    "over_page_count",
    "links_only",
    "failed",
)


def topic_name(folder_name: str) -> str:
    """The topic folder's name after its date: what living files and notebooks are named by."""
    dated = _DATED.match(folder_name)
    return dated.group(1) if dated else folder_name


def adopted_section(markdown: str, photo_name: str) -> str | None:
    """The section of a Markdown that embeds the photo by name, Tema 01's form (FR-004)."""
    starts = [m.start() for m in _HEADING.finditer(markdown)]
    for begin, end in zip(starts, [*starts[1:], len(markdown)], strict=True):
        section = markdown[begin:end]
        if f"]({photo_name})" in section or f"]({photo_name.replace(' ', '%20')})" in section:
            return section.strip() + "\n"
    return None


class Listing(Protocol):
    """What looking up an item in this run's listing needs of spec 004's `ScopedDrive`."""

    def listed(self, item_id: str) -> DriveFile:
        """The item as the run's listing holds it."""
        ...

    def contains(self, item_id: str) -> bool:
        """Whether the item is under the root, as listed this run."""
        ...


class NotesDrive(Protocol):
    """What the pass needs of spec 004's `ScopedDrive`."""

    def listed(self, item_id: str) -> DriveFile:
        """The item as the run's listing holds it."""
        ...

    def contains(self, item_id: str) -> bool:
        """Whether the item is under the root, as listed this run."""
        ...

    def content(self, file_id: str) -> bytes:
        """The file's bytes."""
        ...

    def made_for(self, folder_id: str, properties: dict[str, str]) -> DriveFile | None:
        """The file carrying these public properties, asked of Drive now."""
        ...

    @property
    def root(self) -> DriveFile:
        """The alfabeta folder, where `reports/` sits."""
        ...

    def lookup(self, folder_id: str, name: str) -> DriveFile | None:
        """The item with that name in the folder, asked of Drive now."""
        ...

    def create_folder(self, parent_id: str, name: str) -> DriveFile:
        """A new folder."""
        ...

    def upload(
        self, parent_id: str, name: str, content: bytes, mime_type: str, properties: dict[str, str] | None = None
    ) -> DriveFile:
        """A new file, confirmed."""
        ...

    def update(
        self, file_id: str, content: bytes, mime_type: str, properties: dict[str, str] | None = None
    ) -> DriveFile:
        """New content on the same id, confirmed."""
        ...

    def children(self, folder_id: str) -> list[DriveFile]:
        """What this run's listing found directly inside the folder, sorted by name."""
        ...

    def export(self, file_id: str, mime_type: str = PDF) -> bytes:
        """A Google-native file converted by Drive."""
        ...

    def convert(self, file_id: str, folder_id: str, google_type: str, properties: dict[str, str]) -> bytes:
        """An Office file as PDF, through a Google copy in `folder_id` that goes to the trash at once."""
        ...


@dataclass
class NotesDeps:
    """The ports and settings of one pass."""

    drive: NotesDrive
    store: NotesStateStore
    feed: ChangeFeed
    pdf: PdfBuilder
    transcriber: Transcriber | None  # None: this place holds no Claude key
    clock: Clock
    model: str
    prices: tuple[float, float]
    warn_pages: int
    ran_on: RanOn
    answerer: Answerer | None = None  # the report's "what it adds" (research R8); None: no key here


@dataclass
class Pass:
    """The working state of one pass."""

    state: dict[str, Any]
    today: str
    counts: dict[str, Counter[str]] = field(default_factory=lambda: {})
    dirty: set[str] = field(default_factory=lambda: set())
    classroom_dirty: set[str] = field(default_factory=lambda: set())  # topics whose Classroom file changes
    budget_wait: int = 0
    budget_refused: bool = False  # once refused, this pass makes no other call (research R5)
    no_key: bool = False
    write_failed: bool = False
    claude_answered: bool = False  # a Claude call answered this pass: the budget is not spent
    spent_before: dict[str, Any] = field(default_factory=lambda: {})  # the ledger as the run found it

    def count(self, topic: str, what: str, n: int = 1) -> None:
        """Add to one of the topic's report counts."""
        self.counts.setdefault(topic, Counter())[what] += n

    @property
    def files(self) -> dict[str, dict[str, Any]]:
        """Every recorded file, by Drive id."""
        return cast("dict[str, dict[str, Any]]", self.state.setdefault("files", {}))

    @property
    def pages(self) -> dict[str, dict[str, Any]]:
        """Every page, by its photo's Drive id."""
        return cast("dict[str, dict[str, Any]]", self.state.setdefault("pages", {}))

    @property
    def topics(self) -> dict[str, dict[str, Any]]:
        """Every topic seen, by folder id: its name and living files."""
        return cast("dict[str, dict[str, Any]]", self.state.setdefault("topics", {}))


# --- records ----------------------------------------------------------------------------------------


def page_of(photo_id: str, record: dict[str, Any]) -> NotesPage:
    """A page from its record."""
    usage = Usage(record["in"], record["out"]) if "in" in record else None
    return NotesPage(
        photo_id=photo_id,
        photo_version=record["photo_version"],
        markdown=record["markdown"],
        order=record["order"],
        review=Review(record.get("review", Review.AUTOMATIC)),
        source=PageSource(record.get("source", PageSource.CLAUDE)),
        pdf_id=record.get("pdf_id"),
        markdown_id=record.get("markdown_id"),
        markdown_version=record.get("markdown_version"),
        model=record.get("model"),
        usage=usage,
    )


def page_record(page: NotesPage) -> dict[str, Any]:
    """A page's record."""
    record: dict[str, Any] = {
        "photo_version": page.photo_version,
        "markdown": page.markdown,
        "order": page.order,
        "review": str(page.review),
        "source": str(page.source),
        "pdf_id": page.pdf_id,
        "markdown_id": page.markdown_id,
        "markdown_version": page.markdown_version,
        "model": page.model,
    }
    if page.usage:
        record |= {"in": page.usage.tokens_in, "out": page.usage.tokens_out}
    return record


def living_of(topic: str, kind: LivingKind, record: dict[str, Any] | None) -> LivingFile:
    """A living file from its record."""
    record = record or {}
    return LivingFile(
        topic,
        kind,
        record.get("file_id"),
        record.get("source_id"),
        record.get("built_md5"),
        record.get("pages", 0),
    )


def in_place(drive: Listing, file: DriveFile, topic: str, kind: LivingKind) -> bool:
    """Whether a living file sits where setup put it: its topic's `notes/` or `classroom/` (FR-011)."""
    folder = LIVING_FOLDERS[kind]
    return not file.trashed and any(
        drive.contains(p) and drive.listed(p).name == folder and topic in drive.listed(p).parents for p in file.parents
    )


def living_record(living: LivingFile) -> dict[str, Any]:
    """A living file's record."""
    return {
        "file_id": living.file_id,
        "source_id": living.source_id,
        "built_md5": living.built_md5,
        "pages": living.pages,
        "health": str(living.health),
    }


def known(state: dict[str, Any]) -> dict[str, Known]:
    """What the feed needs of the records."""
    files = cast("dict[str, dict[str, Any]]", state.get("files", {}))
    return {
        fid: Known(Kind(r["kind"]), r.get("version", ""), r.get("own", False), r.get("name"), r.get("topic"))
        for fid, r in files.items()
    }


def spend(state: dict[str, Any]) -> SpendLedger:
    """The month-by-month ledger of every Claude call."""
    months = cast("dict[str, dict[str, int]]", state.get("spend", {}))
    return SpendLedger({m: Usage(u["in"], u["out"]) for m, u in months.items()})


# --- the pass -----------------------------------------------------------------------------------------


def run_notes(deps: NotesDeps) -> dict[str, Any]:
    """One pass; the report of contracts/cli.md, without the exit code."""
    started = deps.clock.now()
    state = deps.store.load()
    previous = deps.store.load_run_log()
    work = Pass(state, started.date().isoformat(), spent_before=copy.deepcopy(state.get("spend", {})))
    baseline(state, Pass(state, work.today), deps.warn_pages)  # once, for records older than the report
    result = deps.feed.read(previous.page_token if previous else None, known(state))
    for gone in result.gone:
        _gone(work, gone)
    for arrival in result.arrivals:
        _record(deps, work, arrival)
    for photo_id in _pending(work):
        try:
            _photo(deps, work, photo_id)
        except DriveError:
            work.write_failed = True
            work.count(work.files[photo_id]["topic"], "failed")
    _items(deps, work)
    for topic in sorted(work.topics):
        for rebuild in (_rebuild, _rebuild_classroom):
            try:
                rebuild(deps, work, topic)
            except DriveError:
                work.write_failed = True
    try:
        write_report(deps, work, started)  # before the save: its calls' usage and its snapshot go with it
    except DriveError:
        work.write_failed = True
    deps.store.save(state)
    failed = work.write_failed or any(c["failed"] for c in work.counts.values())
    run_result = RunResult.PARTIAL if failed else RunResult.OK
    ended = deps.clock.now()
    log = (
        previous.next(started, ended, run_result, deps.ran_on, result.cursor, writes_ok=not work.write_failed)
        if previous
        else RunLog(
            started,
            ended,
            run_result,
            deps.ran_on,
            ended if deps.ran_on == RanOn.CLOUD else None,
            None if work.write_failed else result.cursor,
        )
    )
    deps.store.save_run_log(log)
    month = started.strftime("%Y-%m")
    return {
        "ok": not failed,
        "topics": [
            {"topic": i, **{k: work.counts.get(t, Counter())[k] for k in COUNTS}}
            for i, t in enumerate(sorted(work.counts))
        ],
        "budget_wait": work.budget_wait,
        "no_key": work.no_key,
        "spend": round(spend(state).cost(month, deps.prices), 4),
    }


def _gone(work: Pass, file_id: str) -> None:
    record = work.files.get(file_id)
    if record is None or record.get("state") == str(PhotoState.GONE):
        return
    if record["kind"] == Kind.NOTES_PHOTO:
        record["state"] = str(PhotoState.GONE)  # its page stays (constitution V)
        work.count(record["topic"], "gone")
    elif record["kind"] == Kind.CLASSROOM_ITEM:
        _item_gone(work, file_id, record)


def _record(deps: NotesDeps, work: Pass, arrival: Arrival) -> None:
    """FR-003: Drive id, version, kind, topic folder, state."""
    if arrival.topic not in work.topics:
        work.topics[arrival.topic] = {"name": topic_name(deps.drive.listed(arrival.topic).name)}
    record = work.files.setdefault(arrival.file_id, {})
    before, was = record.get("topic"), record.get("kind")
    if was == Kind.CLASSROOM_ITEM and arrival.kind != Kind.CLASSROOM_ITEM and record.get("state") != ItemState.GONE:
        _item_gone(work, arrival.file_id, record)  # out of `classroom/`, into another part of a topic
    record |= {"kind": str(arrival.kind), "topic": arrival.topic, "version": arrival.version, "own": False}
    if arrival.kind == Kind.NOTES_PHOTO:
        record |= {"name": deps.drive.listed(arrival.file_id).name, "state": str(PhotoState.SEEN), "retries": 0}
        record.setdefault("seq", _next(work.state, "seq"))
    elif arrival.kind == Kind.NOTES_TEXT:
        record["name"] = deps.drive.listed(arrival.file_id).name
    elif arrival.kind == Kind.CLASSROOM_ITEM:
        if before not in (None, arrival.topic):
            _touch(work, record)  # moved: it leaves the first file, and `_item` files it in the second
            record.pop("living", None)
        if was != Kind.CLASSROOM_ITEM or record.get("state") == ItemState.GONE:
            # New, back, or a file of `notes/` moved here: its entry is built again, from `seen`.
            record |= {"state": str(ItemState.SEEN), "retries": 0}
            record.pop("item_version", None)
    elif arrival.kind == Kind.UNEXPECTED:
        work.count(arrival.topic, "unexpected")


def _next(state: dict[str, Any], key: str) -> int:
    state[key] = int(state.get(key, 0)) + 1
    return int(state[key])


def _pending(work: Pass) -> list[str]:
    """Photos to transcribe now: new, failed under the cap, or waiting for the budget since another day."""
    due: list[tuple[int, str]] = []
    for fid, r in work.files.items():
        if r["kind"] != Kind.NOTES_PHOTO:
            continue
        waiting = r["state"] == PhotoState.BUDGET_WAIT and r.get("tried_on") != work.today
        if r["state"] in (PhotoState.SEEN, PhotoState.FAILED) or waiting:
            due.append((int(r.get("seq", 0)), fid))
    return [fid for _, fid in sorted(due)]


def _photo(deps: NotesDeps, work: Pass, photo_id: str) -> None:
    record = work.files[photo_id]
    topic = record["topic"]
    try:
        item = deps.drive.listed(photo_id)
    except OutsideFolderError:
        return  # not in this run's listing: its change will arrive
    folder = item.parents[0]
    photo = Photo(
        Arrival(photo_id, topic, Kind.NOTES_PHOTO, record["version"]),
        PhotoState(record["state"]),
        int(record.get("retries", 0)),
    )
    same = [
        f
        for f, r in work.files.items()
        if f != photo_id and r["kind"] == Kind.NOTES_PHOTO and r.get("version") == record["version"] and f in work.pages
    ]
    if same:
        record["state"] = str(photo.moved_to(PhotoState.DUPLICATE).state)
        work.count(topic, "duplicates")
        return
    markdown, source, usage = _adopted(deps, work, topic, folder, item.name), PageSource.ADOPTED, None
    if markdown is None:
        source = PageSource.CLAUDE
        recovered = deps.drive.made_for(folder, {FOR: photo_id, ROLE: "markdown"})
        if recovered is not None and recovered.prop(VERSION) == record["version"]:
            markdown = deps.drive.content(recovered.id).decode()  # a crashed pass already paid for it
        elif deps.transcriber is None:
            work.no_key = True  # nothing downloaded: the photo waits for a key
            return
        elif work.budget_refused:
            moved = photo.moved_to(PhotoState.BUDGET_WAIT)
            record |= {"state": str(moved.state), "tried_on": work.today}
            work.budget_wait += 1
            return
        else:
            record["tried_on"] = work.today
            done = deps.transcriber.transcribe(deps.drive.content(photo_id), item.mime_type)
            work.claude_answered = work.claude_answered or done.usage is not None
            if done.usage is not None:
                ledger = spend(work.state).add(work.today[:7], done.usage)
                work.state["spend"] = {m: {"in": u.tokens_in, "out": u.tokens_out} for m, u in ledger.months.items()}
            if done.state != PhotoState.TRANSCRIBED:
                moved = photo.moved_to(done.state)
                record |= {"state": str(moved.state), "retries": moved.retries}
                if moved.state == PhotoState.BUDGET_WAIT:
                    work.budget_wait += 1
                    work.budget_refused = True
                else:
                    work.count(
                        topic, {"unsupported": "unsupported", "unreadable": "unreadable"}.get(moved.state, "failed")
                    )
                return
            markdown, usage = done.markdown, done.usage
    image = deps.drive.content(photo_id)
    if photo_id in work.pages:
        order = int(work.pages[photo_id]["order"])  # a new version keeps the page's place (research R7)
    else:
        order = max((p["order"] for f, p in work.pages.items() if work.files[f]["topic"] == topic), default=0) + 1
    page = NotesPage(
        photo_id, record["version"], markdown, order, source=source, model=deps.model if usage else None, usage=usage
    )
    md_file = _write(
        deps,
        folder,
        f"{item.name} · transcripción.md",
        markdown.encode(),
        MARKDOWN,
        photo_id,
        record["version"],
        "markdown",
    )
    pdf_file = _write(
        deps,
        folder,
        f"{item.name} · transcripción.pdf",
        deps.pdf.page(page, image),
        PDF,
        photo_id,
        record["version"],
        "pdf",
    )
    page = replace(page, pdf_id=pdf_file.id, markdown_id=md_file.id, markdown_version=md_file.version)
    work.pages[photo_id] = page_record(page)
    work.files[md_file.id] = {
        "kind": str(Kind.NOTES_TEXT),
        "topic": topic,
        "version": md_file.version,
        "own": True,
        "for": photo_id,
    }
    work.files[pdf_file.id] = {
        "kind": str(Kind.NOTES_TRANSCRIPT),
        "topic": topic,
        "version": pdf_file.version,
        "own": True,
        "name": pdf_file.name,
        "for": photo_id,
    }
    record |= {"state": str(photo.moved_to(PhotoState.TRANSCRIBED).state), "retries": 0}
    work.dirty.add(topic)
    work.count(topic, "pages_added")


def _adopted(deps: NotesDeps, work: Pass, topic: str, folder: str, photo_name: str) -> str | None:
    """A transcription the family already wrote, in a Markdown of the same `notes/`: no Claude call."""
    for fid, r in sorted(work.files.items()):
        if r["kind"] != Kind.NOTES_TEXT or r.get("own") or r.get("topic") != topic or not deps.drive.contains(fid):
            continue
        if folder not in deps.drive.listed(fid).parents:
            continue
        section = adopted_section(deps.drive.content(fid).decode(), photo_name)
        if section is not None:
            return section
    return None


def _write(
    deps: NotesDeps, folder: str, name: str, content: bytes, mime: str, made_for: str, version: str, role: str
) -> DriveFile:
    """Look up before create (research R4): a crashed or overlapping pass leaves one file, updated."""
    found = deps.drive.made_for(folder, {FOR: made_for, ROLE: role})
    properties = {FOR: made_for, ROLE: role, VERSION: version}
    if found is not None:
        return deps.drive.update(found.id, content, mime, properties)
    return deps.drive.upload(folder, name, content, mime, properties)


def _rebuild(deps: NotesDeps, work: Pass, topic: str) -> None:
    """The topic's notes living file: checked where it was set up, rebuilt when its pages changed."""
    pages = sorted(
        (page_of(f, p) for f, p in work.pages.items() if work.files[f]["topic"] == topic), key=lambda p: p.order
    )
    living_records = cast("dict[str, Any]", work.topics[topic].setdefault("living", {}))
    living = living_of(topic, LivingKind.NOTES, living_records.get(LivingKind.NOTES))
    if living.waiting_setup:
        if pages:
            work.count(topic, "waiting_setup")
        return
    assert living.file_id is not None
    found = deps.drive.listed(living.file_id) if deps.drive.contains(living.file_id) else None
    if found is None or not in_place(deps.drive, found, topic, LivingKind.NOTES):
        living_records[LivingKind.NOTES] = {**living_record(living), "health": "missing"}
        work.count(topic, "missing_living_files")  # reported, never recreated (FR-014)
        return
    living_records[LivingKind.NOTES] = living_record(living)  # in place again after a move: healthy
    # A page transcribed while the file was missing reaches it on the first pass that finds it again.
    waiting = any(work.files[p.photo_id]["state"] == PhotoState.TRANSCRIBED for p in pages)
    if topic not in work.dirty and not waiting:
        return
    data, count = deps.pdf.notes(
        Topic(topic, work.topics[topic]["name"]), [(p, deps.drive.content(p.photo_id)) for p in pages]
    )
    built, upload = living.built(hashlib.md5(data).hexdigest(), count)
    if upload:
        deps.drive.update(living.file_id, data, PDF)
    for p in pages:
        if work.files[p.photo_id]["state"] == PhotoState.TRANSCRIBED:
            work.files[p.photo_id]["state"] = str(PhotoState.IN_LIVING_FILE)
    living_records[LivingKind.NOTES] = living_record(built)
    if built.over(deps.warn_pages):
        work.count(topic, "over_page_count")


# --- Classroom items (research R6; data-model.md, ClassroomEntry) -------------------------------------


@dataclass(frozen=True)
class ClassroomBuild:
    """A Classroom living file built from its entries, and the items it held or could not read."""

    data: bytes
    pages: int
    built: tuple[str, ...]
    failed: tuple[str, ...]
    links_only: frozenset[str] = frozenset()  # built entries that are only their cover


def _touch(work: Pass, record: dict[str, Any]) -> None:
    """The item's living Classroom file is rebuilt this run."""
    living = record.get("living")
    if living is not None:
        work.classroom_dirty.add(living)


def _settle(item_id: str, record: dict[str, Any], state: ItemState) -> None:
    """Move an item's record to `state` through the model's transitions; staying where it is is no move."""
    current = ItemState(record.get("state", ItemState.SEEN))
    if current == state and state != ItemState.FAILED:
        return
    item = ClassroomItem(
        Arrival(item_id, record["topic"], Kind.CLASSROOM_ITEM, record.get("version", "")),
        current,
        int(record.get("retries", 0)),
    ).moved_to(state)
    record |= {"state": str(item.state), "retries": item.retries}


def _item_gone(work: Pass, item_id: str, record: dict[str, Any]) -> None:
    """Removed, trashed or moved out of its topic: its entry leaves the file, which cannot read it again."""
    _settle(item_id, record, ItemState.GONE)
    work.count(record.get("living") or record["topic"], "gone")
    _touch(work, record)


def _items(deps: NotesDeps, work: Pass) -> None:
    """Every recorded Classroom item against this run's listing, which `ScopedDrive.open` makes afresh.

    The feed only says which item changed; the listing says what it is now, so a renamed item, a file
    removed from an item's folder or an item moved out of the topics is seen with no change of its own.
    """
    for item_id, record in sorted(work.files.items()):
        if record["kind"] == Kind.CLASSROOM_ITEM and record.get("state") != ItemState.GONE:
            _item(deps, work, item_id, record)


def _item(deps: NotesDeps, work: Pass, item_id: str, record: dict[str, Any]) -> None:
    """What the item is now (T028): left out, waiting for a topic, unchanged, or a new version of its entry."""
    found = deps.drive.listed(item_id) if deps.drive.contains(item_id) else None
    if found is None or not in_place(deps.drive, found, record["topic"], LivingKind.CLASSROOM):
        _item_gone(work, item_id, record)
        return
    named = posted_title(found.name, folder=found.is_folder)
    if named is None or is_announcement(found.name) or not is_part(found.name):
        # Not material: an announcement, a previous version, or a name spec 001 never writes.
        if record.get("state") != ItemState.LEFT_OUT:
            if named is None:
                work.count(record.get("living") or record["topic"], "unexpected")
            _touch(work, record)  # an entry it had leaves the file
        _settle(item_id, record, ItemState.LEFT_OUT)
        record.pop("item_version", None)
        return
    if "living" not in record:
        living = _route(deps, work, record["topic"])
        if living is None:
            return  # a `No topic` material of a subject with no topic yet: routed once one exists
        record["living"] = living
        work.classroom_dirty.add(living)
    kept = _kept(deps.drive, found)
    version = _version(found.name, kept)
    if version == record.get("item_version"):
        return
    record["item_version"] = version
    _settle(item_id, record, ItemState.SEEN)
    work.classroom_dirty.add(record["living"])


def _route(deps: NotesDeps, work: Pass, topic: str) -> str | None:
    """The topic whose Classroom file an item of `topic` goes into; None while there is none.

    An item's own topic, or for `No topic` the subject's topic folder with the latest date now (spec 002
    FR-023).
    """
    folder = deps.drive.listed(topic)
    if topic_name(folder.name) != NO_TOPIC:
        return topic
    dated = [
        (sibling.name[:8], sibling.name, sibling.id)
        for subject in folder.parents
        if deps.drive.contains(subject)
        for sibling in deps.drive.children(subject)
        if sibling.is_folder and _DATED.match(sibling.name) and topic_name(sibling.name) != NO_TOPIC
    ]
    if not dated:
        return None
    latest = max(dated)[2]
    work.topics.setdefault(latest, {"name": topic_name(deps.drive.listed(latest).name)})
    return latest


def _kept(drive: NotesDrive, item: DriveFile) -> list[tuple[str, DriveFile]]:
    """Each file of the item a living file may show, by its path inside the item, in name order.

    Never the student's work, its grading or a previous version (constitution III, spec 001 FR-015b).
    """
    if not item.is_folder:
        return [(item.name, item)]
    kept: list[tuple[str, DriveFile]] = []
    below = [("", item.id)]
    while below:
        prefix, folder = below.pop()
        for child in drive.children(folder):
            path = prefix + child.name
            if child.is_folder:
                below.append((f"{path}/", child.id))
            elif is_part(path):
                kept.append((path, child))
    return sorted(kept, key=lambda k: (k[0], k[1].id))


def _version(name: str, kept: list[tuple[str, DriveFile]]) -> str:
    """The entry's `item_version`: what it shows, the item's name and each kept file's path and version."""
    shown = json.dumps([name, [[path, f.version] for path, f in kept]], ensure_ascii=False)
    return hashlib.sha256(shown.encode()).hexdigest()[:16]


def _filed(files: dict[str, dict[str, Any]], topic: str) -> list[str]:
    """The items whose entries the topic's Classroom file holds or is due to."""
    return sorted(
        f
        for f, r in files.items()
        if r["kind"] == Kind.CLASSROOM_ITEM and r.get("living") == topic and r.get("state") in _FILED
    )


def _rebuild_classroom(deps: NotesDeps, work: Pass, topic: str) -> None:
    """The topic's Classroom living file: checked where it was set up, rebuilt when an entry changed."""
    filed = _filed(work.files, topic)
    living_records = cast("dict[str, Any]", work.topics[topic].setdefault("living", {}))
    living = living_of(topic, LivingKind.CLASSROOM, living_records.get(LivingKind.CLASSROOM))
    if living.waiting_setup:
        if filed:
            work.count(topic, "waiting_setup")
        return
    assert living.file_id is not None
    found = deps.drive.listed(living.file_id) if deps.drive.contains(living.file_id) else None
    if found is None or not in_place(deps.drive, found, topic, LivingKind.CLASSROOM):
        living_records[LivingKind.CLASSROOM] = {**living_record(living), "health": "missing"}
        work.count(topic, "missing_living_files")  # reported, never recreated (FR-011)
        return
    living_records[LivingKind.CLASSROOM] = living_record(living)
    waiting = any(work.files[i]["state"] in _DUE for i in filed)
    if topic not in work.classroom_dirty and not waiting:
        return
    build = build_classroom(deps, work.files, topic, work.topics[topic]["name"])
    built, upload = living.built(hashlib.md5(build.data).hexdigest(), build.pages)
    if upload:
        deps.drive.update(living.file_id, build.data, PDF)
    reached = [i for i in build.built if work.files[i]["state"] in _DUE]  # new or changed, now in the file
    settle_classroom(work.files, build)
    for item_id in reached:
        work.count(topic, "items_added")  # FR-013: items that reached the living file
        if item_id in build.links_only:
            work.count(topic, "links_only")
    for _ in build.failed:
        work.count(topic, "failed")
    living_records[LivingKind.CLASSROOM] = living_record(built)
    if built.over(deps.warn_pages):
        work.count(topic, "over_page_count")


def build_classroom(deps: NotesDeps, files: dict[str, dict[str, Any]], topic: str, name: str) -> ClassroomBuild:
    """The topic's Classroom living file from its entries, each read from Drive now (research R6).

    A new or changed entry Drive fails to read is left out and retried on the next runs, up to the
    cap; one already in the file stops the build instead, so the file never loses it to a Drive error.
    """
    entries: list[tuple[ClassroomEntry, list[RenderedPart]]] = []
    failed: list[str] = []
    # HACK(tech-debt): every rebuild reads, exports and converts each entry of the topic again.
    # Research R6 rebuilds a living file whole from its records, and state.json keeps no part's bytes;
    # a cache of rendered parts by (file id, version) in `.alfabeta/` would spare the Office copies
    # (origin: #68)
    for item_id in _filed(files, topic):
        try:
            entries.append(_entry(deps, item_id, files[item_id]))
        except DriveError:
            if files[item_id]["state"] == ItemState.IN_LIVING_FILE:
                raise
            # FIXME(tech-debt): a new version Drive fails to read drops the item's old entry too.
            # The old version's files are no longer read (renamed `(anterior …)` or overwritten), so the
            # build cannot keep the entry it replaces; it is back once a retry reads the new one
            # (origin: #68)
            failed.append(item_id)
    data, pages = deps.pdf.classroom(Topic(topic, name), entries)
    links_only = frozenset(e.item_id for e, _ in entries if e.links_only)
    return ClassroomBuild(data, pages, tuple(e.item_id for e, _ in entries), tuple(failed), links_only)


def settle_classroom(files: dict[str, dict[str, Any]], build: ClassroomBuild) -> None:
    """Once the file is written: its entries are in it, and the ones Drive failed to read count a failure."""
    for item_id in build.built:
        _settle(item_id, files[item_id], ItemState.IN_LIVING_FILE)
    for item_id in build.failed:
        _settle(item_id, files[item_id], ItemState.FAILED)


def _entry(deps: NotesDeps, item_id: str, record: dict[str, Any]) -> tuple[ClassroomEntry, list[RenderedPart]]:
    """One entry and its parts' bytes; the student's work and its grading are never downloaded.

    Its cover comes from the item's name, `descripcion.md` or `enunciado.md`, and `enlaces.md`; each
    other kept file is a part.
    """
    item = deps.drive.listed(item_id)
    named = posted_title(item.name, folder=item.is_folder)
    assert named is not None  # `_item` left every other name out
    posted, title = named
    description: list[str] = []
    links: tuple[str, ...] = ()
    rendered: list[RenderedPart] = []
    for path, f in _kept(deps.drive, item):
        if item.is_folder and path in _DESCRIPTIONS:
            description.append(deps.drive.content(f.id).decode(errors="replace").strip())
        elif item.is_folder and path == _LINKS:
            links = addresses(deps.drive.content(f.id).decode(errors="replace"))
        else:
            part = Part(f.id, path, part_kind(f.name, f.mime_type))
            rendered.append(RenderedPart(part, _render(deps, f, part.kind)))
    entry = ClassroomEntry(
        item_id,
        record.get("item_version", ""),
        title,
        posted,
        "\n\n".join(d for d in description if d),
        links,
        tuple(r.part for r in rendered),
    )
    return entry, rendered


def _render(deps: NotesDeps, file: DriveFile, kind: PartKind) -> bytes:
    """A part's bytes as the builder takes them (research R6); a part only named needs none."""
    if kind in (PartKind.PDF, PartKind.TEXT, PartKind.IMAGE):
        return deps.drive.content(file.id)
    if kind == PartKind.EXPORT:
        return deps.drive.export(file.id, PDF)
    if kind == PartKind.OFFICE:
        google = OFFICE_TYPES[PurePosixPath(file.name).suffix.lower()]
        folder = deps.store.work_folder(CONVERSIONS)
        return deps.drive.convert(file.id, folder, google, {FOR: file.id, ROLE: "conversion"})
    return b""
