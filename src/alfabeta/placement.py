"""Where each Classroom item goes in the student's folder (spec 001 FR-012…FR-015c).

`<school-year>/<subject>/<YYYYMMDD> - <Tema NN - title | teacher's title | Sin tema>/classroom/…`

A topic folder is found by the part of its name after the date, whatever that date is, and keeps
the date it was created with: the posting date of the first item placed in it. Items must therefore
be placed in posting order. The placer only computes paths; `apply` writes.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from alfabeta.model import (
    Attachment,
    AttachmentKind,
    Decision,
    DecisionState,
    DecisionType,
    Item,
    ItemType,
    ReplicaRole,
    Subject,
)
from alfabeta.sources import CLASSROOM

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Iterable
    from pathlib import Path

NO_TOPIC = "Sin tema"
# What the student turned in, inside the assignment's folder (FR-015a, amended 2026-10-28).
SUBMISSION_FOLDER = "entrega"
MAX_NAME_BYTES = 255
SUMMARY_CHARS = 60

_DATED = re.compile(r"^(\d{8}) - (.+)$")
_BOOK_TOPIC = re.compile(r"Tema \d{2} - .+")
# "/" separates paths and ":" is shown as "/" by macOS; control characters are invisible in Drive.
_FORBIDDEN = re.compile(r"[/:\x00-\x1f\x7f]")


def clean(text: str) -> str:
    """A name valid in the file system and in Drive, keeping the teacher's accents."""
    name = unicodedata.normalize("NFC", _FORBIDDEN.sub("-", text))
    return re.sub(r"\s+", " ", name).strip().rstrip(".")


def fit(name: str, limit: int = MAX_NAME_BYTES) -> str:
    """`name` cut to `limit` UTF-8 bytes, keeping its extension."""
    if len(name.encode()) <= limit:
        return name
    path = PurePosixPath(name)
    suffix = path.suffix if 0 < len(path.suffix) <= 10 else ""
    stem = name[: len(name) - len(suffix)]
    budget = limit - len(suffix.encode())
    while len(stem.encode()) > budget:
        stem = stem[:-1]
    return stem.rstrip(" .") + suffix


def summary(text: str) -> str:
    """The first words of an announcement, cleaned and cut to 60 characters at a word boundary."""
    words = clean(text)
    if len(words) <= SUMMARY_CHARS:
        return words
    cut = words[:SUMMARY_CHARS]
    if words[SUMMARY_CHARS] != " " and " " in cut:
        cut = cut[: cut.rindex(" ")]
    return cut.rstrip(" .,;-")


def downloaded_name(name: str, kind: str) -> str:
    """The name a file has once downloaded: Google files arrive as PDF (research R3, S1)."""
    if kind == AttachmentKind.GOOGLE_DOC and PurePosixPath(name).suffix.lower() != ".pdf":
        return f"{name}.pdf"
    return name


def _file_name(attachment: Attachment) -> str:
    return clean(downloaded_name(attachment.name, attachment.kind))


def _day(date: dt.date) -> str:
    return date.strftime("%Y%m%d")


def book_topics(subject_dir: Path, book: str) -> list[str]:
    """The book topics of a subject: folders named `… Tema NN - <title>` that hold the book's subfolder.

    Returned without their date, as `Tema NN - <title>`.
    """
    if not book or not subject_dir.is_dir():
        return []
    found: list[str] = []
    for folder in sorted(subject_dir.iterdir()):
        dated = _DATED.match(folder.name)
        rest = dated.group(2) if dated else folder.name
        if _BOOK_TOPIC.fullmatch(rest) and (folder / book).is_dir():
            found.append(rest)
    return found


@dataclass(frozen=True)
class Target:
    """One file an item produces: its role, the attachment it copies ("" for a note) and its path."""

    role: ReplicaRole
    attachment: str
    path: str


@dataclass
class Placer:
    """Paths for the items of one subject, given the folders already there and the decisions."""

    school_year: str
    subject: Subject
    existing_folders: Iterable[str] = ()
    decisions: Iterable[Decision] = ()
    _topic_folders: dict[str, str] = field(init=False, default_factory=dict[str, str])
    _matches: dict[tuple[DecisionType, str], str] = field(
        init=False, default_factory=dict[tuple[DecisionType, str], str]
    )
    _taken: dict[str, str] = field(init=False, default_factory=dict[str, str])

    def __post_init__(self) -> None:
        """Index the existing topic folders by name after the date, and the confirmed matches."""
        for name in self.existing_folders:
            dated = _DATED.match(name)
            if dated:
                self._topic_folders.setdefault(dated.group(2), name)
        for decision in self.decisions:
            topic = decision.target.get("topic", "")
            if decision.state == DecisionState.CONFIRMED and topic:
                self._matches[(decision.type, decision.origin)] = topic

    @property
    def _subject_dir(self) -> str:
        return f"{self.school_year}/{self.subject.folder}"

    def topic_name(self, item: Item, teacher_title: str | None) -> str:
        """The topic folder's name without its date, for an item and its teacher's topic title."""
        if item.type == ItemType.ANNOUNCEMENT or item.topic_id is None:
            return NO_TOPIC
        by_item = self._matches.get((DecisionType.ITEM_MATCH, item.id))
        if by_item:
            return by_item
        if self.subject.book:
            by_topic = self._matches.get((DecisionType.TOPIC_MATCH, item.topic_id))
            if by_topic:
                return by_topic
        return clean(teacher_title or "") or NO_TOPIC

    def topic_folder(self, name: str, first_posted: dt.date) -> str:
        """The dated folder for `name`: the existing one whatever its date, else a new one dated now."""
        if name not in self._topic_folders:
            self._topic_folders[name] = fit(f"{_day(first_posted)} - {name}")
        return self._topic_folders[name]

    def _unique(self, folder: str, name: str, item: str, *, is_folder: bool = False) -> str:
        """`name` in `folder`, numbered « (2)», « (3)»… if another item already took it there."""
        suffix = "" if is_folder else PurePosixPath(name).suffix
        stem = name[: len(name) - len(suffix)]
        candidate, number = name, 1
        while self._taken.get(f"{folder}/{candidate}", item) != item:
            number += 1
            candidate = fit(f"{stem} ({number}){suffix}")
        self._taken[f"{folder}/{candidate}"] = item
        return candidate

    def place(self, item: Item, teacher_title: str | None = None) -> list[Target]:
        """Every file `item` produces, with paths relative to the student's base folder."""
        topic = self.topic_folder(self.topic_name(item, teacher_title), item.posted_at)
        where = f"{self._subject_dir}/{topic}/{CLASSROOM}"
        files = [a for a in item.attachments if a.downloaded]
        links = [a for a in item.attachments if not a.downloaded]
        day = _day(item.posted_at)

        if item.type == ItemType.ANNOUNCEMENT:
            note = fit(f"{day} - aviso - {summary(item.description or item.title)}", MAX_NAME_BYTES - 3)
            if not item.attachments:
                return [Target(ReplicaRole.ANNOUNCEMENT, "", f"{where}/{self._unique(where, note + '.md', item.id)}")]
            folder = f"{where}/{self._unique(where, note, item.id, is_folder=True)}"
            return [Target(ReplicaRole.ANNOUNCEMENT, "", f"{folder}/{note}.md"), *self._inside(folder, files, links)]

        title = clean(item.title) or "sin título"
        if item.type in (ItemType.ASSIGNMENT, ItemType.QUESTION):
            folder = f"{where}/{self._unique(where, fit(f'{day} - {title}'), item.id, is_folder=True)}"
            # Two files of one item may share a name: each attachment owns its numbered name (FR-015c).
            targets = [
                Target(
                    ReplicaRole.STATEMENT,
                    a.id,
                    f"{folder}/{self._unique(folder, fit('enunciado - ' + _file_name(a)), a.id)}",
                )
                for a in files
            ]
            if item.description:
                targets.append(Target(ReplicaRole.DESCRIPTION, "", f"{folder}/enunciado.md"))
            handed = f"{folder}/{SUBMISSION_FOLDER}"
            targets += [
                Target(ReplicaRole.SUBMISSION, a.id, f"{handed}/{self._unique(handed, fit(_file_name(a)), a.id)}")
                for a in item.submission
                if a.downloaded
            ]
            if item.grading is not None:
                targets.append(Target(ReplicaRole.GRADING, "", f"{folder}/correccion.md"))
            if links:
                targets.append(Target(ReplicaRole.LINKS, "", f"{folder}/enlaces.md"))
            return targets

        # Material.
        if not files and not links:
            name = fit(f"{day} - {title}", MAX_NAME_BYTES - 3) + ".md"
            return [Target(ReplicaRole.DESCRIPTION, "", f"{where}/{self._unique(where, name, item.id)}")]
        if len(files) == 1 and not links and not item.description:
            [only] = files
            name = fit(f"{day} - {title}{PurePosixPath(_file_name(only)).suffix}")
            return [Target(ReplicaRole.MATERIAL, only.id, f"{where}/{self._unique(where, name, item.id)}")]
        folder = f"{where}/{self._unique(where, fit(f'{day} - {title}'), item.id, is_folder=True)}"
        targets = self._inside(folder, files, links)
        if item.description:
            targets.append(Target(ReplicaRole.DESCRIPTION, "", f"{folder}/descripcion.md"))
        return targets

    def _inside(self, folder: str, files: list[Attachment], links: list[Attachment]) -> list[Target]:
        """The files of a material or announcement folder under their own names, and `enlaces.md`."""
        targets: list[Target] = []
        for attachment in files:
            name = self._unique(folder, fit(_file_name(attachment) or attachment.id), attachment.id)
            targets.append(Target(ReplicaRole.MATERIAL, attachment.id, f"{folder}/{name}"))
        if links:
            targets.append(Target(ReplicaRole.LINKS, "", f"{folder}/enlaces.md"))
        return targets
