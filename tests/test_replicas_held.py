"""A copy keeps its name until the bytes under a new one arrive (spec 001 FR-026, #299), placed directly."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Any

from alfabeta.model import Attachment, AttachmentKind, AttachmentRole, Item, ItemType, Subject
from alfabeta.placement import Placer
from alfabeta.replicas import Applier

if TYPE_CHECKING:
    from pathlib import Path

GENERIC = "Archivo de Drive"
SUBJECT = Subject("Fis", "synth-c1")
FOLDER = "2026-2027/Fis/20261001 - Tema inventado/classroom/20261001 - Apuntes inventados"


class NoDecisions:
    def decisions(self) -> list[Any]:
        return []


def _item(*attachments: tuple[str, AttachmentKind, str]) -> Item:
    return Item(
        "synth-i1",
        "synth-c1",
        "synth-t1",
        ItemType.MATERIAL,
        "Apuntes inventados",
        dt.date(2026, 10, 1),
        description="inventada",
        attachments=tuple(Attachment(i, k, n, AttachmentRole.MATERIAL) for i, k, n in attachments),
    )


def _record(path: str, name: str, kind: str = "file") -> dict[str, Any]:
    return {"role": "material", "path": f"{FOLDER}/{path}", "hash": "h", "version": 1, "name": name, "kind": kind}


def _applier(tmp_path: Path, records: dict[str, Any], files: dict[str, bytes], **kw: Any) -> Applier:
    base, data = tmp_path / "base", tmp_path / "data"
    for name, content in files.items():
        (base / FOLDER).mkdir(parents=True, exist_ok=True)
        (base / FOLDER / name).write_bytes(content)
    data.mkdir()
    state = {"replicas": {f"classroom|synth-i1|{k}": v for k, v in records.items()}, "items": {}}
    return Applier(base, data, "2026-2027", [SUBJECT], NoDecisions(), state, dt.date(2026, 11, 27), **kw)  # pyright: ignore[reportArgumentType]


def _files(applier: Applier) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in (applier.base / FOLDER).iterdir() if p.is_file() and p.suffix != ".md"}


def test_a_repair_never_moves_a_copy_over_another_file(tmp_path: Path) -> None:
    # Before #299, A's copy took the generic title and B, of the same name, took the freed one: sending
    # A back to it would overwrite B. Both copies stay, each record on its own bytes.
    item = _item(("A", AttachmentKind.FILE, GENERIC), ("B", AttachmentKind.FILE, "x.pdf"))
    records = {"A": _record(GENERIC, "x.pdf"), "B": _record("x.pdf", "x.pdf")}
    applier = _applier(tmp_path, records, {GENERIC: b"AAA", "x.pdf": b"BBB"})
    applier.place_item(Placer("2026-2027", SUBJECT, [], []), item, "Tema inventado")
    replicas = applier.state["replicas"]
    held = {k.rsplit("|", 1)[1]: (applier.base / v["path"]).read_bytes() for k, v in replicas.items() if "#" not in k}
    assert held == {"A": b"AAA", "B": b"BBB"}
    assert sorted(_files(applier).values()) == [b"AAA", b"BBB"]


def test_a_kind_shown_otherwise_keeps_the_copy_s_extension(tmp_path: Path) -> None:
    # A Google document no longer shared may show as a plain file under the generic title.
    item = _item(("G", AttachmentKind.FILE, GENERIC))
    applier = _applier(tmp_path, {"G": _record("Ficha 3.pdf", "Ficha 3", "google_doc")}, {"Ficha 3.pdf": b"DOC"})
    applier.place_item(Placer("2026-2027", SUBJECT, [], []), item, "Tema inventado")
    assert _files(applier).get("Ficha 3.pdf") == b"DOC"
    assert applier.state["replicas"]["classroom|synth-i1|G"]["path"].endswith("/Ficha 3.pdf")


def test_a_move_from_the_state_keeps_the_held_name_even_with_bytes_collected(tmp_path: Path) -> None:
    # The class is not applied in this run, though its download came: the move from the state places no
    # bytes, so it never takes the state's generic name.
    item = _item(("A", AttachmentKind.FILE, GENERIC))
    downloads = [{"item": "synth-i1", "attachment": "A", "expected_name": GENERIC}]
    applier = _applier(tmp_path, {"A": _record("x.pdf", "x.pdf")}, {"x.pdf": b"OLD"}, downloads=downloads)
    collected = applier.data_dir / "inbox" / "synth-i1__A" / GENERIC
    collected.parent.mkdir(parents=True)
    collected.write_bytes(b"NEW")
    applier._replace(Placer("2026-2027", SUBJECT, [], []), item, "Tema inventado")
    assert _files(applier) == {"x.pdf": b"OLD"}
