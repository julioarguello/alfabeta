"""The plan (spec 001 T039): the sandbox run through the command, and its rules one by one."""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from typing import TYPE_CHECKING, Any

import pytest

from alfabeta import plan
from alfabeta.classification import Classifier
from alfabeta.decisions import DecisionStore, Proposal
from alfabeta.model import Attachment, AttachmentKind, AttachmentRole, DecisionType, Item, ItemType, Subject

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


def cli(home: Path, *args: str, run: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "ALFABETA_RUN"}
    if run:
        env["ALFABETA_RUN"] = run
    return subprocess.run(
        [sys.executable, "-m", "alfabeta", "--home", str(home), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


@pytest.fixture
def sandbox(tmp_path: Path) -> Iterator[tuple[Path, str]]:
    home = tmp_path / "box"
    assert cli(home, "sandbox", "prepare").returncode == 0
    run = json.loads(cli(home, "lock", "take", "--student", "sample", "--mode", "interactive").stdout)["run"]
    yield home, run
    cli(home, "lock", "release", "--student", "sample", run=run)


def collect_captures(home: Path, run: str) -> None:
    assert cli(home, "sandbox", "download", "--student", "sample", "--captures", run=run).returncode == 0
    done = cli(home, "downloads", "collect", "--student", "sample", run=run)
    assert json.loads(done.stdout)["classes"] == ["synth-1", "synth-2"]


def test_the_sandbox_run_plans_downloads_places_and_asks(sandbox: tuple[Path, str]):
    home, run = sandbox
    collect_captures(home, run)
    done = cli(home, "plan", "--student", "sample", run=run)
    assert done.returncode == 0, done.stderr
    result = json.loads(done.stdout)
    names = sorted(d["expected_name"] for d in result["downloads"])
    assert names == [
        "Plantilla inventada.pdf",
        "Presentación inventada.pdf",
        "apuntes-inventados.pdf",
        "ficha-inventada.pdf",
        "informe-inventado.pdf",
        "normas-inventadas.pdf",
        "respuestas-inventadas.pdf",
    ]  # the student's submissions too (US6), no video, link or form
    by_name = {d["expected_name"]: d for d in result["downloads"]}
    assert by_name["ficha-inventada.pdf"]["url"].startswith(
        "https://drive.usercontent.google.com/download?id=synth-40&"
    )
    assert "/presentation/d/synth-47/export/pdf" in by_name["Presentación inventada.pdf"]["url"]
    assert {d["batch"] for d in result["downloads"]} == {0} and {d["why"] for d in result["downloads"]} == {"new"}
    paths = [c["path"] for c in result["changes"]]
    assert any(p.startswith("2026-2027/FyQ/") and p.endswith("/enunciado - ficha-inventada.pdf") for p in paths)
    assert any(" - No topic/" in p for p in paths)
    assert any(p.endswith("/20261006 - Ficha inventada de mezclas/submission/respuestas-inventadas.pdf") for p in paths)
    pending = {(p["type"], p["origin"]) for p in result["pending_decisions"]}
    # The Spanish exam announcement has the sandbox's proposal; the English one waits for Claude (T048).
    assert pending == {
        ("class_link", "synth-3"),
        ("topic_match", "synth-10"),
        ("topic_match", "synth-11"),
        ("exam_candidate", "synth-32"),
    }
    english = next(p for p in result["pending_decisions"] if p["origin"] == "synth-32")
    assert english["language"] == "en" and english["posted_at"] == "2026-10-24" and english["origin_hash"]
    topic = next(p for p in result["pending_decisions"] if p["origin"] == "synth-10")
    assert topic["book_topics"] == ["Tema 01 - Materia inventada"]

    assert cli(home, "sandbox", "download", "--student", "sample", "--batch", "0", run=run).returncode == 0
    collected = json.loads(cli(home, "downloads", "collect", "--student", "sample", run=run).stdout)
    assert sorted(collected["collected"]) == names and collected["pending"] == []


def test_subject_limits_the_scope(sandbox: tuple[Path, str]):
    home, run = sandbox
    collect_captures(home, run)
    result = json.loads(cli(home, "plan", "--student", "sample", "--subject", "Ingles", run=run).stdout)
    assert result["downloads"] == [] and all(c["path"].startswith("2026-2027/Ingles/") for c in result["changes"])


def test_a_capture_outside_the_school_year_stops_the_run(sandbox: tuple[Path, str]):
    home, run = sandbox
    collect_captures(home, run)
    captured = next((home / "sample" / "data" / "captures").glob(f"alfabeta-capture-{run}-synth-1-*.json"))
    data = json.loads(captured.read_text())
    data["captured_at"] = "2025-10-27T16:22:00+01:00"
    captured.write_text(json.dumps(data))
    done = cli(home, "plan", "--student", "sample", run=run)
    assert done.returncode == 1 and '"invalid_config"' in done.stdout
    last = json.loads((home / "sample" / "data" / "log.jsonl").read_text().splitlines()[-1])
    assert (last["result"], last["reason"], last["run"]) == ("stopped", "invalid_config", run)
    assert cli(home, "lock", "renew", "--student", "sample", run=run).returncode == 1  # released


def test_plan_needs_the_lock(tmp_path: Path):
    home = tmp_path / "box"
    cli(home, "sandbox", "prepare")
    done = cli(home, "plan", "--student", "sample")
    assert done.returncode == 1 and '"lock_not_held"' in done.stdout


TODAY = dt.date(2026, 10, 27)
SUBJECT = Subject("FyQ", "Física", "sciencebits", "Física inventada")


def planner(tmp_path: Path, state: dict[str, Any] | None = None, last_review: dt.date | None = TODAY) -> plan.Planner:
    return plan.Planner(
        school_year="2026-2027",
        subjects=[SUBJECT],
        base=tmp_path,
        decisions=DecisionStore.open(tmp_path),
        state=state or {},
        full_review_days=7,
        today=TODAY,
        classifier=Classifier(("es",)),
        last_review=last_review,
    )


ITEM = Item("synth-i", "synth-c", None, ItemType.MATERIAL, "x", dt.date(2026, 10, 1), modified_at=dt.date(2026, 10, 8))
FILE = {"id": "synth-a", "kind": "file", "name": "ficha.pdf"}


@pytest.mark.parametrize(
    ("replica", "last_review", "why"),
    [
        (None, TODAY, "new"),
        ({"name": "ficha.pdf", "kind": "file", "modified_seen": "2026-10-08"}, TODAY, None),
        ({"name": "ficha.pdf", "kind": "file", "modified_seen": "2026-10-01"}, TODAY, "modified"),
        ({"name": "otra.pdf", "kind": "file", "modified_seen": "2026-10-08"}, TODAY, "renamed"),
        ({"name": "ficha.pdf", "kind": "file", "modified_seen": "2026-10-08"}, dt.date(2026, 10, 20), "review"),
        ({"name": "ficha.pdf", "kind": "file", "modified_seen": "2026-10-08"}, None, "review"),
    ],
)
def test_only_what_changed_is_downloaded(
    tmp_path: Path, replica: dict[str, Any] | None, last_review: dt.date | None, why: str | None
):
    state = {"replicas": {"classroom|synth-i|synth-a": replica}} if replica else {}
    assert planner(tmp_path, state, last_review)._why(ITEM, FILE) == why  # pyright: ignore[reportPrivateUsage]


def test_a_rejected_topic_returns_only_when_its_title_or_the_book_changed(tmp_path: Path):
    p = planner(tmp_path)
    proposal = Proposal.parse(
        {
            "type": "topic_match",
            "origin": "synth-10",
            "target": {"topic": "Tema 01 - X"},
            "reason": "r",
            "confidence": "low",
            "origin_title": "1. Materia inventada",
            "book_topics": ["Tema 01 - Materia inventada"],
        },
        TODAY,
    )
    p.decisions.propose([proposal], TODAY)
    p.decisions.confirm(DecisionType.TOPIC_MATCH, "synth-10", TODAY, reject=True)

    class Captured:
        topics = {"synth-10": "1. Materia inventada"}

    pending = p._pending_topics  # pyright: ignore[reportPrivateUsage]
    assert pending(Captured(), SUBJECT, ["Tema 01 - Materia inventada"]) == []  # type: ignore[arg-type]
    assert len(pending(Captured(), SUBJECT, ["Tema 01 - Materia inventada", "Tema 02 - Nuevo"])) == 1  # type: ignore[arg-type]
    Captured.topics = {"synth-10": "1. Título cambiado"}
    assert len(pending(Captured(), SUBJECT, ["Tema 01 - Materia inventada"])) == 1  # type: ignore[arg-type]


def test_expected_names_and_urls():
    assert plan.expected_name("Plantilla", AttachmentKind.GOOGLE_DOC) == "Plantilla.pdf"
    assert plan.expected_name("ficha.pdf", AttachmentKind.FILE) == "ficha.pdf"
    assert plan.download_url({"id": "x", "kind": "video", "name": "v"}, 5) is None
    sheet = plan.download_url({"id": "x", "kind": "google_doc", "google_type": "spreadsheet", "name": "s"}, 5)
    assert sheet == "https://docs.google.com/spreadsheets/d/x/export?format=pdf&authuser=5"
    assert Attachment("a", AttachmentKind.FILE, "n", AttachmentRole.MATERIAL).downloaded
