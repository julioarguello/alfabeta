"""No Drive call leaves the alfabeta folder (spec 004 FR-009a, T023). Every id is invented."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from alfabeta.google.drive import FOLDER, DriveError, OutsideFolderError, ScopedDrive
from tests.conftest import FakeTransport, json_response

if TYPE_CHECKING:
    from collections.abc import Callable

    from alfabeta.google.transport import Response

OUTSIDE = "fuera-1"


def folder(item_id: str, parent: str, name: str = "carpeta") -> dict[str, Any]:
    return {"id": item_id, "name": name, "mimeType": FOLDER, "parents": [parent]}


def file(item_id: str, parent: str, name: str = "ficha.pdf") -> dict[str, Any]:
    return {"id": item_id, "name": name, "mimeType": "application/pdf", "parents": [parent], "size": "3"}


def listing(*items: dict[str, Any]) -> Response:
    return json_response(200, {"files": list(items)})


def tree_responses() -> list[Response]:
    """Resolve «alfabeta», then list it (a topic and a file), then list the topic (one file)."""
    return [
        listing(folder("raiz", "root", "alfabeta")),
        listing(folder("tema-1", "raiz", "Tema 01"), file("ficha-0", "raiz")),
        listing(file("ficha-1", "tema-1")),
    ]


def opened(tmp_path: Path) -> tuple[ScopedDrive, FakeTransport]:
    t = FakeTransport(tree_responses())
    drive = ScopedDrive.open(t, "acceso", "alfabeta", tmp_path / "drive.json")
    assert not t.responses
    return drive, t


# Each public method, called with an id outside the tree. A new public method must be added here.
CALLS: dict[str, Callable[[ScopedDrive], object]] = {
    "children": lambda d: d.children(OUTSIDE),
    "get": lambda d: d.get(OUTSIDE),
    "create_folder": lambda d: d.create_folder(OUTSIDE, "nueva"),
    "upload": lambda d: d.upload(OUTSIDE, "a.pdf", b"abc", "application/pdf"),
    "update": lambda d: d.update(OUTSIDE, b"abc", "application/pdf"),
}


def test_every_public_method_is_in_the_table():
    public = {
        name
        for name, _ in inspect.getmembers(ScopedDrive, inspect.isfunction)
        if not name.startswith("_") and name != "contains"  # contains answers, it never calls Drive
    }
    assert len(public) >= 5, "the sweep found too few methods to mean anything"
    assert public == set(CALLS)


@pytest.mark.parametrize("name", sorted(CALLS))
def test_an_outside_id_is_refused_before_any_request(tmp_path: Path, name: str):
    drive, t = opened(tmp_path)
    before = len(t.calls)
    with pytest.raises(OutsideFolderError):
        CALLS[name](drive)
    assert len(t.calls) == before


def test_positive_control_inside_ids_are_accepted(tmp_path: Path):
    drive, t = opened(tmp_path)
    assert [f.id for f in drive.children("raiz")] == ["tema-1", "ficha-0"]  # by name: «Tema 01» < «ficha.pdf»
    assert len(t.calls) == 3  # children() reads this run's listing, it sends nothing
    assert drive.contains("ficha-1")
    assert not drive.contains(OUTSIDE)
    t.responses.append(json_response(200, file("ficha-1", "tema-1")))
    assert drive.get("ficha-1").id == "ficha-1"


def test_the_allowlist_is_rebuilt_on_every_run(tmp_path: Path):
    first, _ = opened(tmp_path)
    assert json.loads((tmp_path / "drive.json").read_text()) == {"root_id": "raiz"}
    # The next run reads the cached root and lists again; a file added in between is now inside.
    t = FakeTransport(
        [
            json_response(200, folder("raiz", "root", "alfabeta")),
            listing(folder("tema-1", "raiz", "Tema 01")),
            listing(file("ficha-1", "tema-1"), file("ficha-2", "tema-1")),
        ]
    )
    second = ScopedDrive.open(t, "acceso", "alfabeta", tmp_path / "drive.json")
    assert t.calls[0][0] == "GET" and "/files/raiz?" in t.calls[0][1]
    assert second.contains("ficha-2") and not first.contains("ficha-2")
    assert not second.contains("ficha-0")  # gone from Drive, gone from the allowlist


def test_a_trashed_root_fails_the_run(tmp_path: Path):
    (tmp_path / "drive.json").write_text(json.dumps({"root_id": "raiz"}))
    t = FakeTransport([json_response(200, {**folder("raiz", "root", "alfabeta"), "trashed": True})])
    with pytest.raises(DriveError, match="trash"):
        ScopedDrive.open(t, "acceso", "alfabeta", tmp_path / "drive.json")


@pytest.mark.parametrize("found", [0, 2])
def test_the_root_must_resolve_to_exactly_one_folder(tmp_path: Path, found: int):
    items = [folder(f"raiz-{n}", "root", "alfabeta") for n in range(found)]
    with pytest.raises(DriveError, match=f"found {found}"):
        ScopedDrive.open(FakeTransport([listing(*items)]), "acceso", "alfabeta", tmp_path / "drive.json")
    assert not (tmp_path / "drive.json").exists()


def test_a_nested_root_walks_its_path_and_quotes_names(tmp_path: Path):
    t = FakeTransport(
        [
            listing(folder("familia", "root", "Familia d'Ana")),
            listing(folder("raiz", "familia", "alfabeta")),
            listing(),
        ]
    )
    drive = ScopedDrive.open(t, "acceso", "Familia d'Ana/alfabeta", tmp_path / "drive.json")
    assert drive.root.id == "raiz"
    assert "d%5C%27Ana" in t.calls[0][1]  # the quote is escaped inside the query
