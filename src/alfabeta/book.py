"""A book provider's result in its topic's folder (spec 001 US4, contracts/cli.md `book place`, `log notebook`).

`book place` copies what a provider built for one topic (the Science Bits skill's `TemaNN_<LANG>.pdf`
and `.md`) into `<school-year>/<subject>/<topic>/<book>/`. `<topic>` is the subject's folder whose
name holds `Tema NN - `, whatever its date and title, or a new `<today> - Tema NN - <title>` when
there is none; between two such folders it never guesses. Each file is a replica keyed
`<book>|Tema NN|<file>` with its hash and version: an identical file writes nothing, a changed one
keeps the previous one beside it as «<name> (anterior YYYY-MM-DD)» (FR-015b). The origin is only
read, and nothing is written outside the base folder. `log notebook` writes the line of the book's
notebook step, whatever its result (constitution VII).
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, cast

from alfabeta.exam.printing import refresh_mirrors
from alfabeta.google.keychain import run_command
from alfabeta.model import ReplicaRole
from alfabeta.placement import book_topic_number, clean, fit
from alfabeta.replicas import previous_name, sha256

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Iterable, Sequence
    from pathlib import Path

    from alfabeta.google.keychain import Runner
    from alfabeta.model import Subject

NOTEBOOK_RESULTS = ("created", "unchanged", "failed", "disabled")
SHARES = ("invited", "already", "failed")
# A reason is a short text for the log; a longer one is cut, and never spans lines.
REASON_CHARS = 200


class BookError(Exception):
    """The command refuses; nothing is written. `reason` is what it reports."""

    def __init__(self, reason: str, message: str) -> None:
        """Keep the reason the command reports."""
        super().__init__(message)
        self.reason = reason


class BookFiles(Protocol):
    """What a book provider built for one topic: its name, which is also its subfolder, and its files."""

    @property
    def name(self) -> str:
        """The provider's subfolder in each topic folder."""
        ...

    def files(self) -> list[Path]:
        """The files to place, under the names they keep."""
        ...


def book_subject(subjects: Iterable[Subject], folder: str) -> Subject:
    """The `[[subjects]]` entry of `folder`, if it has a book."""
    for subject in subjects:
        if subject.folder == folder:
            if not subject.book:
                raise BookError("no_book", f"subject {folder} has no book")
            return subject
    raise BookError("no_book", f"no subject {folder} in the configuration")


def book_topic(text: str) -> tuple[str, str]:
    """`text` as a folder name and its `Tema NN`, if it has the form `Tema NN - <title>`."""
    topic = clean(text)
    number = book_topic_number(topic)
    if number is None:
        raise BookError("invalid_topic", "--topic must have the form «Tema NN - <title>», NN with two digits")
    return topic, number


@dataclass
class BookPlacer:
    """Places one topic of a book provider for one subject, and records its replicas in `state`."""

    base: Path
    school_year: str
    subject: Subject
    state: dict[str, Any]
    today: dt.date
    placed: list[str] = field(default_factory=list[str])
    unchanged: list[str] = field(default_factory=list[str])
    previous: list[str] = field(default_factory=list[str])

    @property
    def replicas(self) -> dict[str, Any]:
        """`state.json` «replicas»: `<source>|<item>|<attachment>` → its record."""
        return cast("dict[str, Any]", self.state.setdefault("replicas", {}))

    def topic_folder(self, topic: str, number: str) -> str:
        """The topic's folder relative to the base folder: the one holding `Tema NN - `, or a new one dated today."""
        subject_dir = self.base / self.school_year / self.subject.folder
        found = (
            sorted(p.name for p in subject_dir.iterdir() if p.is_dir() and f"{number} - " in p.name)
            if subject_dir.is_dir()
            else []
        )
        if len(found) > 1:
            raise BookError(
                "ambiguous_topic", f"{len(found)} folders of {self.subject.folder} hold «{number} - »: rename one"
            )
        name = found[0] if found else fit(f"{self.today.strftime('%Y%m%d')} - {topic}")
        return f"{self.school_year}/{self.subject.folder}/{name}"

    def place(self, built: BookFiles, topic: str, number: str) -> str:
        """Every file of `built` in the topic's `<book>/`; that folder, relative to the base folder."""
        files = built.files()
        if not files:
            raise BookError("nothing_to_place", "the origin holds no file to place")
        folder = f"{self.topic_folder(topic, number)}/{built.name}"
        for origin in files:
            name = fit(clean(origin.name))
            relative = f"{folder}/{name}"
            key = f"{built.name}|{number}|{name}"
            record = cast("dict[str, Any] | None", self.replicas.get(key))
            digest = sha256(origin)
            version = int(record["version"]) if record else 0
            if record is None or record.get("hash") != digest:
                version += 1
            destination = self.base / relative
            if destination.is_file() and sha256(destination) == digest:
                self.unchanged.append(name)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    kept = previous_name(destination, self.today)
                    shutil.move(str(destination), kept)
                    self.previous.append(kept.name)
                _copy(origin, destination)
                self.placed.append(name)
            self.replicas[key] = {
                "role": str(ReplicaRole.MATERIAL),
                "path": relative,
                "hash": digest,
                "version": version,
            }
        return folder


def _copy(origin: Path, destination: Path) -> None:
    """Copy through a temporary file and a rename, so a cut copy never stands as the replica."""
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    shutil.copyfile(origin, temporary)
    temporary.replace(destination)


def refresh(base: Path, mirrors: Sequence[Path], runner: Runner = run_command) -> dict[str, int]:
    """Bring every mirror up to date, one way and never deleting (FR-011a); how many are and failed, never which."""
    failed = refresh_mirrors(base, mirrors, runner)
    return {"up_to_date": len(mirrors) - failed, "failed": failed}


def shares(text: str | None) -> dict[str, int]:
    """`--shares <invited>,<already>,<failed>` as counts; none given is none shared."""
    if text is None:
        return dict.fromkeys(SHARES, 0)
    parts = text.split(",")
    if len(parts) != len(SHARES) or not all(p.strip().isdigit() for p in parts):
        raise BookError("invalid_shares", "--shares must be <invited>,<already>,<failed>, three whole numbers")
    return {name: int(part) for name, part in zip(SHARES, parts, strict=True)}


def notebook_line(
    run: str | None, at: str, topic: str, result: str, reason: str | None, shared: str | None
) -> dict[str, Any]:
    """The `log notebook` line; `reason` only, and always, with `failed`."""
    if result not in NOTEBOOK_RESULTS:
        raise BookError("invalid_result", f"--result must be one of: {', '.join(NOTEBOOK_RESULTS)}")
    said = " ".join((reason or "").split())[:REASON_CHARS]
    if result == "failed" and not said:
        raise BookError("missing_reason", "--reason is required with --result failed")
    line: dict[str, Any] = {
        "type": "notebook",
        "at": at,
        "run": run,
        "topic": book_topic(topic)[0],
        "result": result,
        "shares": shares(shared),
    }
    if result == "failed":
        line["reason"] = said
    return line
