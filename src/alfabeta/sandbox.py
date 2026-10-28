"""An invented student to try a whole run without Classroom (spec 001 T030, contracts/cli.md).

`sandbox prepare` builds, inside a `--home` the operator names explicitly, the student `sample` (or
another id): a valid configuration, its own base folder `drive/<student>/` with one book topic, the
downloads folder every student of the home shares, as they share the Mac's browser, and the invented
captures of `tests/fixtures/classroom/` in `sandbox-captures/`. `sandbox download --captures` copies
them to the downloads folder with the current run, as the extractor would leave them. Attachments
and decisions arrive with T039.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, cast

from alfabeta import config, decisions, plan
from alfabeta.model import DecisionType
from alfabeta.state import RUN_ENV

DEFAULT_STUDENT = "sample"
FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "classroom"
SCHOOL_YEAR = "2026-2027"
BOOK_TOPIC = "20260915 - Tema 01 - Materia inventada"


class SandboxError(Exception):
    """The sandbox cannot do this here."""


def base_folder(home: Path, student: str) -> Path:
    """The invented student's base folder; each student of the home has its own."""
    return home / "drive" / student


def _config(home: Path, student: str) -> str:
    def q(value: str) -> str:
        return json.dumps(value, ensure_ascii=False)

    return f"""# Invented student of the sandbox. Every value is made up.

[student]
display_name = "Alumna de prueba"
school_year = "{SCHOOL_YEAR}"
grade_level = "3º ESO"
languages = ["es", "en"]

[classroom]
account = "alumna@colegio.example"

[storage]
base = {q(str(base_folder(home, student)))}

[drive]
root = "alfabeta"
mirrors = []

[calendar]
id = "familia@calendar.example.org"
shared_with = []

[downloads]
folder = {q(str(home / "downloads"))}

[sync]
full_review_days = 7
lock_idle_minutes = 30
kept_captures = 10

[tools]
folder = {q(str(home / "tools"))}
repository = {q(str(Path(__file__).resolve().parents[2]))}

[sciencebits]
url = "https://learning-bits.example/intranet/es/myclasses/index"
languages = ["es", "en"]

[notebook]
enabled = false
share_with = []
title_pattern = "{{grade}}. {{subject}}. {{topic}}"
nlm_profile = "prueba"
owner = "familia@example.com"

[notes]
model = "claude-sonnet-5-5"
price_in = 2.0
price_out = 10.0
warn_pages = 100
cloud_stale_hours = 2

[schedule]
monday = ""
tuesday = ""
wednesday = ""
thursday = ""
friday = ""
saturday = ""
sunday = ""

[google]
project_label = "sandbox"

[google.accounts.student]
role = "student"
address = "alumna@example.com"
scopes = ["openid", "email"]

[[subjects]]
folder = "FyQ"
classroom_class = "Física y Química sintética 3ºA"
book = "sciencebits"
book_class = "Física inventada"
exam_language = "es"

[[subjects]]
folder = "Ingles"
classroom_class = "English Synthetic 3A"
book = ""
book_class = ""
exam_language = "en"
"""


def require_explicit_home(given: str | None) -> Path:
    """The `--home` the operator named; never the default, so the real students are never touched."""
    if given is None:
        raise SandboxError("the sandbox needs an explicit --home")
    home = Path(given).expanduser().resolve()
    if home == (Path.home() / ".alfabeta").resolve():
        raise SandboxError("the sandbox never uses ~/.alfabeta")
    return home


def prepare(home: Path, student: str = DEFAULT_STUDENT) -> Path:
    """Create the invented student in `home`; returns its folder."""
    root = home / student
    if (root / "config.toml").exists():
        raise SandboxError(f"student {student!r} already exists in this home")
    root.mkdir(parents=True)
    (root / "config.toml").write_text(_config(home, student))
    (base_folder(home, student) / SCHOOL_YEAR / "FyQ" / BOOK_TOPIC / "sciencebits").mkdir(parents=True)
    (home / "downloads").mkdir(exist_ok=True)
    (home / "tools").mkdir(exist_ok=True)
    captures = home / "sandbox-captures"
    captures.mkdir(exist_ok=True)
    attachments = home / "sandbox-attachments"
    attachments.mkdir(exist_ok=True)
    for fixture in sorted(FIXTURES.glob("*.json")):
        (captures / fixture.name).write_bytes(fixture.read_bytes())
        for name in _downloadable_names(json.loads(fixture.read_text())):
            (attachments / name).write_bytes(b"%PDF-1.4\n% invented attachment of the sandbox\n")
    _decide(root / "data")
    return root


def _downloadable_names(capture: dict[str, Any]) -> list[str]:
    """The expected names of the files and Google files a fixture capture holds."""
    found: list[dict[str, Any]] = []
    for item in cast("list[dict[str, Any]]", capture.get("items", [])):
        detail = cast("dict[str, Any]", item.get("detail") or {})
        found += cast("list[dict[str, Any]]", detail.get("attachments", []) + detail.get("submission", []))
    for post in cast("list[dict[str, Any]]", capture.get("stream", [])):
        found += cast("list[dict[str, Any]]", post.get("attachments", []))
    return [plan.expected_name(a["name"], a["kind"]) for a in found if plan.download_url(a, 0)]


def _decide(data_dir: Path) -> None:
    """The decisions a sandbox run starts from: both classes linked, and one detected exam proposed."""
    on = dt.date(2026, 10, 27)
    store = decisions.DecisionStore.open(data_dir)
    links = [
        decisions.Proposal.parse(
            {
                "type": "class_link",
                "origin": cls,
                "target": {"subject": folder},
                "reason": "sandbox",
                "confidence": "high",
            },
            on,
        )
        for cls, folder in (("synth-1", "FyQ"), ("synth-2", "Ingles"))
    ]
    exam = decisions.Proposal.parse(
        {
            "type": "detected_exam",
            "origin": "synth-30#exam-1",
            "target": {"date": "2026-11-05", "reason": "the announcement names the exam's day"},
            "reason": "sandbox",
            "confidence": "medium",
            "origin_hash": "sandbox",
        },
        on,
    )
    store.propose([*links, exam], on)
    for cls in ("synth-1", "synth-2"):
        store.confirm(DecisionType.CLASS_LINK, cls, on)
    store.save()


def download_batch(home: Path, student: str, batch: int) -> list[str]:
    """Copy to the downloads folder the attachments batch `batch` of the last plan requests."""
    cfg = config.load(home, student, ("downloads",))
    downloads = Path(cfg.downloads_folder).expanduser()
    plan_path = home / student / "data" / "plan.json"
    if not plan_path.is_file():
        raise SandboxError("there is no plan yet")
    requested = [d for d in json.loads(plan_path.read_text())["downloads"] if int(d["batch"]) == batch]
    written: list[str] = []
    for download in requested:
        source = home / "sandbox-attachments" / download["expected_name"]
        if not source.is_file():
            raise SandboxError("the plan requests an attachment the sandbox does not have")
        target = downloads / source.name
        number = 1
        while target.exists():  # as the browser does: « (1)» before the extension
            target = downloads / f"{source.stem} ({number}){source.suffix}"
            number += 1
        target.write_bytes(source.read_bytes())
        written.append(target.name)
    return written


def download_captures(home: Path, student: str, run: str | None) -> list[str]:
    """Copy the sandbox captures to the downloads folder, carrying `run` in their name and field."""
    if not run:
        raise SandboxError(f"{RUN_ENV} is not set")
    cfg = config.load(home, student, ("downloads",))
    downloads = Path(cfg.downloads_folder).expanduser()
    written: list[str] = []
    for source in sorted((home / "sandbox-captures").glob("*.json")):
        capture = json.loads(source.read_text())
        capture["run"] = run
        owner = capture["class"]["id"] if capture["type"] == "class" else capture["type"]
        stamp = capture["captured_at"][:19].replace("-", "").replace(":", "").replace("T", "-")
        target = downloads / f"alfabeta-capture-{run}-{owner}-{stamp}.json"
        target.write_text(json.dumps(capture, ensure_ascii=False, indent=1) + "\n")
        written.append(target.name)
    return written
