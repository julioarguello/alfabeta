"""Fixtures against the contracts, and the copies of the contracts (spec 001 T029)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from alfabeta import config

REPO = Path(__file__).resolve().parents[1]
CONTRACTS = REPO / "specs" / "001-classroom-sync" / "contracts"
FIXTURES = REPO / "tests" / "fixtures" / "classroom"
SCHEMAS = REPO / "src" / "alfabeta" / "schemas"
CAPTURES = sorted(FIXTURES.glob("*.json"))


def test_there_are_captures_to_check():
    assert len(CAPTURES) >= 4


@pytest.mark.parametrize("capture", CAPTURES, ids=lambda p: p.name)
def test_capture_fixtures_follow_the_schema(capture: Path):
    schema = json.loads((CONTRACTS / "capture.schema.json").read_text())
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    instance = json.loads(capture.read_text())
    errors = [f"{list(e.path)}: {e.message}" for e in validator.iter_errors(instance)]  # pyright: ignore[reportUnknownMemberType]
    assert errors == []


def test_the_fixtures_cover_what_the_task_lists():
    captures = [json.loads(p.read_text()) for p in CAPTURES]
    classes = [c for c in captures if c["type"] == "class"]
    items = [i for c in classes for i in c["items"]]
    details = [i["detail"] for i in items if i["detail"]]
    attachments = [a for d in details for a in d["attachments"] + d["submission"]]
    attachments += [a for c in classes for s in c["stream"] for a in s.get("attachments", [])]
    assert {c["type"] for c in captures} == {"classes", "class", "stop"} and len(classes) == 2
    assert {i["type"] for i in items} == {"assignment", "material", "question"}
    assert {a["kind"] for a in attachments} == {"file", "google_doc", "video", "link", "form"}
    statuses = {d["status_text"] for d in details}
    assert {"Entregado", "Calificado"} <= statuses
    assert any(d["status_notice_text"] for d in details) and any(d["modified_text"] for d in details)
    announcements = [s["text"] for c in classes for s in c["stream"]]
    assert any("examen" in t.lower() for t in announcements) and any("test" in t.lower() for t in announcements)
    assert {c["run"] for c in captures} == {"run-sintetico"}


@pytest.mark.parametrize("name", ["capture.schema.json", "agenda.schema.json"])
def test_packaged_schemas_are_the_contracts(name: str):
    assert (SCHEMAS / name).read_bytes() == (CONTRACTS / name).read_bytes()


def test_the_template_is_the_contract():
    assert config.TEMPLATE.read_bytes() == (CONTRACTS / "config-template.toml").read_bytes()
