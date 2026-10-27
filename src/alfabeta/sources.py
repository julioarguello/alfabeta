"""Where items come from (spec 001 data-model, Source).

A source has a `name`, which is also its subfolder inside each topic folder (`classroom`, or the
book provider's name such as `sciencebits`), and yields normalized items. `ClassroomSource` reads
the extractor's captures (US1) and `BookSource` a book provider's result (US4); both are filled in
with their stories, and this module fixes the shape the placer and `apply` rely on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

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

    @property
    def name(self) -> str:
        """`classroom`."""
        return CLASSROOM

    def items(self) -> Iterator[Item]:
        """The items in capture order."""
        yield from self.items_seen


@dataclass(frozen=True)
class BookSource:
    """A book provider's result for one subject; its name is the provider's (`sciencebits`)."""

    provider: str
    items_seen: tuple[Item, ...] = ()

    @property
    def name(self) -> str:
        """The provider's name, which is also its subfolder."""
        return self.provider

    def items(self) -> Iterator[Item]:
        """The book's items."""
        yield from self.items_seen
