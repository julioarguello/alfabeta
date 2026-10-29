"""Where items come from (spec 001 data-model, Source).

A source has a `name`, which is also its subfolder inside each topic folder (`classroom`, or the
book provider's name such as `sciencebits`). `ClassroomSource` yields the normalized items of the
extractor's captures (US1); `BookSource` is the directory where a book provider left what it built
for one topic (US4), whose `files()` `book place` copies as they are.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from pathlib import Path

    from alfabeta.capture import ClassCapture
    from alfabeta.model import Item

CLASSROOM = "classroom"


class Source(Protocol):
    """A source of items for one subject."""

    @property
    def name(self) -> str:
        """The subfolder this source writes in each topic folder."""
        ...

    def items(self) -> Iterator[Item]:
        """The source's items, normalized."""
        ...


@dataclass(frozen=True)
class ClassroomSource:
    """Items of one Classroom class, from its captures; the teacher's topics by id."""

    items_seen: tuple[Item, ...] = ()
    topics: Mapping[str, str] = field(default_factory=dict[str, str])

    @classmethod
    def from_capture(cls, capture: ClassCapture) -> ClassroomSource:
        """The source of a normalized class capture."""
        return cls(capture.items, dict(capture.topics))

    @property
    def name(self) -> str:
        """`classroom`."""
        return CLASSROOM

    def items(self) -> Iterator[Item]:
        """The items in capture order."""
        yield from self.items_seen


@dataclass(frozen=True)
class BookSource:
    """A book provider's result for one topic, in `origin`; its name is the provider's (`sciencebits`)."""

    provider: str
    items_seen: tuple[Item, ...] = ()
    origin: Path | None = None

    @property
    def name(self) -> str:
        """The provider's name, which is also its subfolder."""
        return self.provider

    def items(self) -> Iterator[Item]:
        """The book's items."""
        yield from self.items_seen

    def files(self) -> list[Path]:
        """The files the provider built: the regular files at the top of `origin`, by name; hidden ones are not its."""
        if self.origin is None or not self.origin.is_dir():
            return []
        return sorted(p for p in self.origin.iterdir() if p.is_file() and not p.name.startswith("."))
