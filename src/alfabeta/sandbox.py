"""An invented student to try a whole run without Classroom (spec 001 T030, contracts/cli.md).

`sandbox prepare` builds, inside a `--home` the operator names explicitly, the student `sample`: a
valid configuration, a base folder with one book topic, an empty downloads folder and the invented
captures of `tests/fixtures/classroom/` in `sandbox-captures/`. `sandbox download --captures` copies
them to the downloads folder with the current run, as the extractor would leave them. Attachments
and decisions arrive with T039.
"""

from __future__ import annotations

import json
from pathlib import Path

from alfabeta import config
from alfabeta.state import RUN_ENV

DEFAULT_STUDENT = "sample"
FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "classroom"
SCHOOL_YEAR = "2026-2027"
BOOK_TOPIC = "20260915 - Tema 01 - Materia inventada"


class SandboxError(Exception):
    """The sandbox cannot do this here."""


def _config(home: Path) -> str:
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
base = {q(str(home / "drive"))}

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

[[subjects]]
folder = "Ingles"
classroom_class = "English Synthetic 3A"
book = ""
book_class = ""
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
    (root / "config.toml").write_text(_config(home))
    (home / "drive" / SCHOOL_YEAR / "FyQ" / BOOK_TOPIC / "sciencebits").mkdir(parents=True)
    (home / "downloads").mkdir(exist_ok=True)
    (home / "tools").mkdir(exist_ok=True)
    captures = home / "sandbox-captures"
    captures.mkdir(exist_ok=True)
    for fixture in sorted(FIXTURES.glob("*.json")):
        (captures / fixture.name).write_bytes(fixture.read_bytes())
    return root


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
