"""US3 with the student `sample` (spec 001 T051, T054): a later run writes only what changed.

SC-002 (a second run without changes writes nothing in the student's folder), SC-003 (a later
«Última modificación» leaves the previous version beside the new one), FR-025…FR-029.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from typing import TYPE_CHECKING, Any, cast

import pytest

from alfabeta import plan
from alfabeta.dates import MADRID
from tests.test_plan_apply_us1 import BOOK, FYQ, TOPIC, Box, cli

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

NOTES = f"{TOPIC}/20261001 - Apuntes inventados"
OTHER_BOOK_TOPIC = "Tema 02 - Otra materia inventada"
OTHER_BOOK = f"{FYQ}/20260920 - {OTHER_BOOK_TOPIC}/classroom"


@pytest.fixture
def box(tmp_path: Path) -> Iterator[Box]:
    b = Box(tmp_path / "box")
    assert cli(b.home, "sandbox", "prepare").returncode == 0
    b.take()
    yield b
    b.release()


def first_run(box: Box) -> None:
    box.collect_and_plan(drop_stop=True)
    box.apply()


def next_run(box: Box) -> dict[str, Any]:
    """A later run: a new lock, the sandbox's captures again, plan, download and collect."""
    box.release()
    box.take()
    return box.collect_and_plan(drop_stop=True)


def snapshot(box: Box) -> dict[str, tuple[int, str]]:
    """Every folder and file of the student's folder, the state and the decisions, with mtime and hash."""
    found: dict[str, tuple[int, str]] = {}
    for path in [*box.base.rglob("*"), box.data / "state.json", box.data / "decisions.json"]:
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
        found[str(path)] = (path.stat().st_mtime_ns, digest)
    return found


def item(capture: dict[str, Any], item_id: str) -> dict[str, Any]:
    return next(i for i in cast("list[dict[str, Any]]", capture["items"]) if i["id"] == item_id)


def later_capture(box: Box, change: Callable[[dict[str, Any]], None]) -> None:
    """What the next capture of the physics class shows: `change` applied, one day later."""
    path = box.home / "sandbox-captures" / "class-synth-1.json"
    data = cast("dict[str, Any]", json.loads(path.read_text()))
    change(data)
    data["captured_at"] = (dt.datetime.fromisoformat(data["captured_at"]) + dt.timedelta(days=1)).isoformat()
    path.write_text(json.dumps(data, ensure_ascii=False))


def last_line(box: Box) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads((box.data / "log.jsonl").read_text().splitlines()[-1]))


def why(planned: dict[str, Any]) -> list[tuple[str, str]]:
    return sorted((d["attachment"], d["why"]) for d in cast("list[dict[str, str]]", planned["downloads"]))


def state(box: Box) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads((box.data / "state.json").read_text()))


def test_a_second_run_without_changes_writes_nothing(box: Box):
    first_run(box)
    before = snapshot(box)
    planned = next_run(box)
    assert planned["downloads"] == [] and planned["full_review"] is False
    result, _ = box.apply()
    assert (result["added"], result["changed"], result["withdrawn"]) == (0, 0, 0)
    assert snapshot(box) == before  # SC-002: not one write, not even the same bytes again


def test_a_later_modification_keeps_the_previous_version(box: Box):
    first_run(box)
    old = (box.base / NOTES / "apuntes-inventados.pdf").read_bytes()
    new = b"%PDF-1.4\n% the teacher's second version\n"
    later_capture(box, lambda c: item(c, "synth-23")["detail"].update(modified_text="Última modificación: 20 oct"))
    (box.home / "sandbox-attachments" / "apuntes-inventados.pdf").write_bytes(new)
    # Both files of the modified item are asked for again; only one of them changed.
    assert why(next_run(box)) == [("synth-45", "modified"), ("synth-47", "modified")]
    result, _ = box.apply()
    today = dt.datetime.now(MADRID).date().isoformat()
    folder = box.base / NOTES
    assert result["changed"] == 1
    assert (folder / "apuntes-inventados.pdf").read_bytes() == new
    assert (folder / f"apuntes-inventados (anterior {today}).pdf").read_bytes() == old  # SC-003
    assert not [p.name for p in folder.iterdir() if p.name.startswith("Presentación inventada (anterior")]
    # The modification was seen: neither file is asked for again, the identical one included.
    assert next_run(box)["downloads"] == []


def test_a_renamed_attachment_moves_and_is_not_fetched_again(box: Box):
    first_run(box)
    attachments = box.home / "sandbox-attachments"
    (attachments / "apuntes-v2.pdf").write_bytes((attachments / "apuntes-inventados.pdf").read_bytes())

    def rename(capture: dict[str, Any]) -> None:
        item(capture, "synth-23")["detail"]["attachments"][0]["name"] = "apuntes-v2.pdf"

    later_capture(box, rename)
    assert why(next_run(box)) == [("synth-45", "renamed")]
    box.apply()
    names = sorted(p.name for p in (box.base / NOTES).iterdir())
    assert "apuntes-v2.pdf" in names and "apuntes-inventados.pdf" not in names
    assert not [n for n in names if "(anterior" in n]  # same bytes: a move, not a version
    assert next_run(box)["downloads"] == []


def age_full_reviews(box: Box, days: int) -> None:
    """Move every logged full review `days` back, as if the last one had run that long ago."""
    log = box.data / "log.jsonl"
    lines: list[str] = []
    for raw in log.read_text().splitlines():
        entry = cast("dict[str, Any]", json.loads(raw))
        if entry.get("full_review"):
            ended = dt.datetime.fromisoformat(str(entry["ended_at"])) - dt.timedelta(days=days)
            entry["ended_at"] = ended.isoformat()
        lines.append(json.dumps(entry, ensure_ascii=False))
    log.write_text("\n".join(lines) + "\n")


def test_an_unchanged_attachment_waits_for_the_full_review(box: Box):
    first_run(box)  # the first sync counts as a full review
    assert last_line(box)["full_review"] is True
    assert next_run(box)["downloads"] == []
    box.apply()
    age_full_reviews(box, days=8)
    before = snapshot(box)
    planned = next_run(box)
    assert planned["full_review"] is True and planned["downloads"]
    assert {d["why"] for d in planned["downloads"]} == {"review"}
    result, _ = box.apply()
    assert (result["added"], result["changed"]) == (0, 0)
    assert snapshot(box) == before  # the same bytes: nothing written outside the run's own records
    assert last_line(box)["full_review"] is True
    assert next_run(box)["full_review"] is False  # counted from the review just logged


@pytest.mark.parametrize("complete", [True, False])
def test_an_item_gone_from_classroom_is_kept_and_marked_only_after_a_complete_capture(box: Box, complete: bool):
    first_run(box)
    before = box.files()

    def withdraw(capture: dict[str, Any]) -> None:
        capture["items"] = [i for i in capture["items"] if i["id"] != "synth-23"]
        capture["complete"] = complete

    later_capture(box, withdraw)
    next_run(box)
    result, summary = box.apply()
    assert box.files() == before  # FR-027: nothing is deleted from the student's folder
    replicas = cast("dict[str, dict[str, Any]]", state(box)["replicas"])
    marked = sorted(k for k, r in replicas.items() if r.get("withdrawn_at"))
    if complete:
        assert marked == sorted(k for k in replicas if k.startswith("classroom|synth-23|")) and marked
        assert result["withdrawn"] == last_line(box)["withdrawn"] == 1
        assert "retirado de Classroom: Apuntes inventados" in summary
    else:  # a cut-short capture withdraws nothing
        assert marked == [] and result["withdrawn"] == last_line(box)["withdrawn"] == 0


def test_an_item_that_comes_back_is_no_longer_withdrawn(box: Box):
    first_run(box)
    path = box.home / "sandbox-captures" / "class-synth-1.json"
    full = json.loads(path.read_text())
    later_capture(box, lambda c: c.update(items=[i for i in c["items"] if i["id"] != "synth-23"]))
    next_run(box)
    assert box.apply()[0]["withdrawn"] == 1
    later_capture(box, lambda c: c.update(items=full["items"]))
    next_run(box)
    result, _ = box.apply()
    assert result["withdrawn"] == 0
    assert not [k for k, r in state(box)["replicas"].items() if r.get("withdrawn_at")]
    assert not state(box)["items"]["synth-23"].get("withdrawn_at")


def test_an_item_the_capture_cannot_read_is_not_withdrawn(box: Box):
    first_run(box)
    later_capture(box, lambda c: item(c, "synth-23")["detail"].pop("posted_text"))
    next_run(box)
    result, _ = box.apply()
    assert result["withdrawn"] == 0
    assert not [k for k, r in state(box)["replicas"].items() if r.get("withdrawn_at")]


def test_a_run_cut_before_apply_is_finished_without_downloading_twice(box: Box, tmp_path: Path):
    box.collect_and_plan(drop_stop=True)  # the attachments reach data/, then the run dies before apply
    collected = {p.name for p in (box.data / "inbox").iterdir()}
    planned = next_run(box)
    asked = {f"{d['item']}__{d['attachment']}" for d in planned["downloads"]}
    kept = {f"{d['item']}__{d['attachment']}" for d in planned["already_collected"]}
    assert collected and kept == collected and not asked & collected
    assert sorted(p.name for p in (box.home / "downloads").iterdir()) == []  # nothing left behind
    box.apply()
    clean = Box(tmp_path / "clean")
    assert cli(clean.home, "sandbox", "prepare").returncode == 0
    clean.take()
    first_run(clean)
    clean.release()
    assert box.files() == clean.files()  # FR-029: as if it had never been cut


def test_a_changed_match_moves_the_replicas_without_copies(box: Box):
    first_run(box)
    (box.base / OTHER_BOOK).parent.joinpath("sciencebits").mkdir(parents=True)
    proposal = box.home / "p.json"
    proposal.write_text(
        json.dumps(
            {
                "type": "topic_match",
                "origin": "synth-10",
                "target": {"topic": "Tema 01 - Materia inventada"},
                "reason": "same number and title",
                "confidence": "high",
            }
        )
    )
    assert box("decisions", "propose", "--student", "sample", "--file", str(proposal)).returncode == 0
    assert (
        box("decisions", "confirm", "--student", "sample", "--type", "topic_match", "--origin", "synth-10").returncode
        == 0
    )
    box.apply()
    before = box.files()
    assert f"{BOOK}/20261006 - Ficha inventada de mezclas/enunciado - ficha-inventada.pdf" in before
    change = ("decisions", "change", "--student", "sample", "--type", "topic_match", "--origin", "synth-10")
    assert box(*change, "--target", OTHER_BOOK_TOPIC).returncode == 0
    result, _ = box.apply()
    after = box.files()
    assert len(after) == len(before) and int(str(result["changed"])) > 0
    assert not any(f.startswith(BOOK) for f in after)
    assert f"{OTHER_BOOK}/20261006 - Ficha inventada de mezclas/enunciado - ficha-inventada.pdf" in after


def test_apply_keeps_only_the_newest_captures_of_each_class(box: Box):
    config = box.home / "sample" / "config.toml"
    config.write_text(config.read_text().replace("kept_captures = 10", "kept_captures = 1"))
    first_run(box)
    later_capture(box, lambda c: None)
    next_run(box)
    box.apply()
    captures = sorted((box.data / "captures").glob("alfabeta-capture-*.json"))
    physics = [p for p in captures if "-synth-1-" in p.name]
    assert len(physics) == 1 and f"-{box.run}-" in physics[0].name  # the newest one stays
    assert len([p for p in captures if "-synth-2-" in p.name]) == 1


def test_pruning_keeps_what_it_cannot_read(tmp_path: Path):
    unreadable = [tmp_path / f"alfabeta-capture-x-synth-1-2026102{n}-162200.json" for n in (6, 7)]
    for path in unreadable:
        path.write_text("not json")
    # Two of them with room for one: neither is counted as the older of a pair.
    assert plan.prune_captures(tmp_path, 1) == 0
    assert all(path.exists() for path in unreadable)


def test_an_announcement_gone_from_the_stream_is_not_withdrawn(box: Box):
    first_run(box)  # the stream is read from one page: an older post off it is not a removed one
    later_capture(box, lambda c: c.update(stream=[p for p in c["stream"] if p["id"] != "synth-31"]))
    next_run(box)
    result, _ = box.apply()
    assert result["withdrawn"] == 0


def test_a_copy_collected_before_the_teachers_change_is_asked_for_again(box: Box):
    box.collect_and_plan(drop_stop=True)  # cut before apply
    stale = next((box.data / "inbox").glob("synth-23__synth-45/*"))
    stale.write_bytes(b"%PDF-1.4\n% the version before the teacher's change\n")
    os.utime(stale, (stale.stat().st_atime, dt.datetime(2026, 10, 10, tzinfo=MADRID).timestamp()))
    later_capture(box, lambda c: item(c, "synth-23")["detail"].update(modified_text="Última modificación: 20 oct"))
    planned = next_run(box)
    assert "synth-45" in {d["attachment"] for d in planned["downloads"]}
    assert "synth-45" not in {d["attachment"] for d in planned["already_collected"]}
    box.apply()
    new = (box.home / "sandbox-attachments" / "apuntes-inventados.pdf").read_bytes()
    assert (box.base / NOTES / "apuntes-inventados.pdf").read_bytes() == new


def test_a_plan_is_applied_only_once_every_class_it_planned_is(box: Box):
    box.collect_and_plan(drop_stop=True)
    box.apply("--subject", "Ingles")
    assert "applied_at" not in json.loads((box.data / "plan.json").read_text())
    box.apply()
    assert "applied_at" in json.loads((box.data / "plan.json").read_text())
    again, summary = box.apply()
    assert again["added"] == 0 and "temas por confirmar: 2" in summary  # still pending, still said
