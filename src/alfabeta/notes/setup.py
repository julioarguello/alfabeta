"""`notebook setup`: a topic gets its two living files and they become its notebook's sources (R9).

Only this command creates living files (research R6). It runs on the Mac, where `nlm` is signed in.
It first runs the recording pass, so an adopted Markdown is in the first build; then, for each
living file not yet recorded, it builds it, shares it read-only with the notebook's owner (and
nothing else in the folder), adds it as a Drive source and records both ids. A recorded file that
is gone is reported, never recreated. Old plain sources of the notes or the Classroom material are
listed for the family to remove; nothing is removed (FR-011).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

from alfabeta.notes.model import Kind, LivingKind, PhotoState, Topic
from alfabeta.notes.run import FOR, PDF, ROLE, NotesDeps, living_of, living_record, page_of, run_notes, topic_name

if TYPE_CHECKING:
    from alfabeta.google.drive import DriveFile
    from alfabeta.notes.sources import NotebookSources

LIVING_TITLES = ("Apuntes ·", "Classroom ·")


class SetupError(Exception):
    """Setup stopped; `reason` is the CLI's code."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class SetupDrive(Protocol):
    """What setup needs of `ScopedDrive` beyond the pass."""

    def items(self) -> list[DriveFile]:
        """Everything listed under the root this run."""
        ...

    def listed(self, item_id: str) -> DriveFile:
        """The item as listed this run."""
        ...

    def contains(self, item_id: str) -> bool:
        """Whether the item is under the root."""
        ...

    def share_reader(self, file_id: str, address: str) -> None:
        """Let one account read one file, without mailing it."""
        ...


@dataclass(frozen=True)
class Setting:
    """What a setup needs besides the pass's ports."""

    topic: str  # `<subject>/<topic folder>`
    title_pattern: str
    grade: str
    owner: str  # never printed, logged or reported


def _topic_folder(drive: SetupDrive, topic: str) -> DriveFile:
    subject, _, folder = topic.partition("/")
    found = [
        f
        for f in drive.items()
        if f.is_folder
        and f.name == folder
        and any(drive.contains(p) and drive.listed(p).name == subject and drive.listed(p).is_folder for p in f.parents)
    ]
    if len(found) != 1:
        raise SetupError("no_topic")
    return found[0]


def setup_topic(deps: NotesDeps, drive: SetupDrive, sources: NotebookSources, setting: Setting) -> dict[str, Any]:
    """The JSON of contracts/cli.md: `{ok, notes_source, classroom_source, plain_sources_to_remove}`."""
    folder = _topic_folder(drive, setting.topic)
    name = topic_name(folder.name)
    subject = setting.topic.partition("/")[0]
    title = setting.title_pattern.format(grade=setting.grade, subject=subject, topic=name)
    notebook = sources.find_notebook(title)
    if notebook is None:
        raise SetupError("no_notebook")
    run_notes(deps)  # the recording pass first: an adopted Markdown is in the first build
    state = deps.store.load()
    topics = cast("dict[str, dict[str, Any]]", state.setdefault("topics", {}))
    record = topics.setdefault(folder.id, {"name": name})
    living = cast("dict[str, Any]", record.setdefault("living", {}))
    outcome: dict[str, str] = {}
    present = sources.list_sources(notebook)
    for kind in (LivingKind.NOTES, LivingKind.CLASSROOM):
        current = living_of(folder.id, kind, living.get(kind))
        if not current.waiting_setup:
            assert current.file_id is not None
            found = drive.listed(current.file_id) if drive.contains(current.file_id) else None
            there = found is not None and not found.trashed and folder.id in found.parents
            outcome[kind] = "unchanged" if there else "missing"
            if not there:
                living[kind] = {**living_record(current), "health": "missing"}
            continue
        data, pages = _build(deps, state, folder.id, name, kind)
        file = _living_file(deps, folder.id, Topic(folder.id, name).living_file_name(kind), data, kind)
        drive.share_reader(file.id, setting.owner)
        title = file.name.removesuffix(".pdf")
        # A setup stopped after adding the source (nlm failed on the next one, or another writer
        # changed state.json) runs again: the source is found, never added twice (FR-009).
        # Measured 2026-10-27: a Drive source's `url` is empty and its title is the Drive file's name,
        # `.pdf` included, whatever `--title` said; so the name is what finds it.
        again = next((s for s in present if s.title in (file.name, title)), None)
        source = again.id if again else sources.add_drive_source(notebook, file.id, title)
        built, _ = current.set_up(file.id, source).built(hashlib.md5(data).hexdigest(), pages)
        living[kind] = living_record(built)
        files = cast("dict[str, dict[str, Any]]", state.setdefault("files", {}))
        files[file.id] = {"kind": str(Kind.LIVING_FILE), "topic": folder.id, "version": file.version, "own": True}
        outcome[kind] = "created"
    deps.store.save(state)
    recorded = {living_of(folder.id, k, living.get(k)).source_id for k in LivingKind}
    plain = [s for s in present if s.title.startswith(LIVING_TITLES) and s.id not in recorded]
    return {
        "ok": True,
        "notes_source": outcome[LivingKind.NOTES],
        "classroom_source": outcome[LivingKind.CLASSROOM],
        "plain_sources_to_remove": len(plain),
    }


def _build(deps: NotesDeps, state: dict[str, Any], topic: str, name: str, kind: LivingKind) -> tuple[bytes, int]:
    """From what is recorded; a cover page when nothing is. Classroom items arrive with phase 5."""
    if kind == LivingKind.CLASSROOM:
        return deps.pdf.classroom(Topic(topic, name), [])
    files = cast("dict[str, dict[str, Any]]", state.get("files", {}))
    pages = sorted(
        (
            page_of(f, p)
            for f, p in cast("dict[str, dict[str, Any]]", state.get("pages", {})).items()
            if files[f]["topic"] == topic
        ),
        key=lambda p: p.order,
    )
    for p in pages:
        files[p.photo_id]["state"] = str(PhotoState.IN_LIVING_FILE)
    return deps.pdf.notes(Topic(topic, name), [(p, deps.drive.content(p.photo_id)) for p in pages])


def _living_file(deps: NotesDeps, folder: str, name: str, data: bytes, kind: LivingKind) -> DriveFile:
    """Look up before create: a setup that stopped after the upload leaves one file."""
    properties = {FOR: folder, ROLE: str(kind)}
    found = deps.drive.made_for(folder, properties)
    if found is not None:
        return deps.drive.update(found.id, data, PDF, properties)
    return deps.drive.upload(folder, name, data, PDF, properties)
