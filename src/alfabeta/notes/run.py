"""One pass of the notes: new photos become pages, changed living files are rebuilt (spec 005 R2, R4 to R6).

The pass reads the records and the run log, reads the change feed from the cursor, records what
arrived, transcribes the pending photos, writes each page's Markdown and PDF next to its photo, and
rebuilds the notes living file of every topic that changed. It never creates a living file: only
`notebook setup` does (research R6). It writes `state.json` only when a record changed, and the run
log always. It calls no study-pack generation (FR-012).
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, Protocol, cast

from alfabeta.google.drive import DriveError, OutsideFolderError
from alfabeta.notes.changes import LIVING_FOLDERS, Known
from alfabeta.notes.model import (
    Arrival,
    Kind,
    LivingFile,
    LivingKind,
    NotesPage,
    PageSource,
    Photo,
    PhotoState,
    RanOn,
    Review,
    RunLog,
    RunResult,
    SpendLedger,
    Topic,
    Usage,
)

if TYPE_CHECKING:
    from alfabeta.google.drive import DriveFile
    from alfabeta.notes.changes import ChangeFeed
    from alfabeta.notes.model import Clock
    from alfabeta.notes.pdf import PdfBuilder
    from alfabeta.notes.state import NotesStateStore
    from alfabeta.notes.transcribe import Transcriber

FOR = "alfabeta_for"
ROLE = "alfabeta_role"
VERSION = "alfabeta_version"
PDF = "application/pdf"
MARKDOWN = "text/markdown"
_DATED = re.compile(r"^\d{8} - (.+)$")
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


@dataclass
class Pass:
    """The working state of one pass."""

    state: dict[str, Any]
    today: str
    counts: dict[str, Counter[str]] = field(default_factory=lambda: {})
    dirty: set[str] = field(default_factory=lambda: set())
    budget_wait: int = 0
    budget_refused: bool = False  # once refused, this pass makes no other call (research R5)
    no_key: bool = False
    write_failed: bool = False

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
    work = Pass(state, started.date().isoformat())
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
    for topic in sorted(work.topics):
        try:
            _rebuild(deps, work, topic)
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
    if record["kind"] in (Kind.NOTES_PHOTO, Kind.CLASSROOM_ITEM):
        record["state"] = str(PhotoState.GONE)  # its page stays (constitution V)
        work.count(record["topic"], "gone")


def _record(deps: NotesDeps, work: Pass, arrival: Arrival) -> None:
    """FR-003: Drive id, version, kind, topic folder, state."""
    if arrival.topic not in work.topics:
        work.topics[arrival.topic] = {"name": topic_name(deps.drive.listed(arrival.topic).name)}
    record = work.files.setdefault(arrival.file_id, {})
    record |= {"kind": str(arrival.kind), "topic": arrival.topic, "version": arrival.version, "own": False}
    if arrival.kind == Kind.NOTES_PHOTO:
        record |= {"name": deps.drive.listed(arrival.file_id).name, "state": str(PhotoState.SEEN), "retries": 0}
        record.setdefault("seq", _next(work.state, "seq"))
    elif arrival.kind == Kind.NOTES_TEXT:
        record["name"] = deps.drive.listed(arrival.file_id).name
    elif arrival.kind == Kind.CLASSROOM_ITEM:
        record.setdefault("state", "seen")  # phase 5 builds them
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
