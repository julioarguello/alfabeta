"""Configuration against the template (spec 001 T018). Every value is invented."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from alfabeta import config

SECRET_VALUE = "valor-que-no-debe-salir"


def _full(base: Path, tools: Path, mirror: Path) -> str:
    return f"""
[student]
display_name = "Alumna Inventada"
school_year = "2026-2027"
grade_level = "3º ESO"
languages = ["es", "en"]

[classroom]
account = "alumna@colegio.example"

[storage]
base = "{base}"

[drive]
root = "alfabeta"
mirrors = ["{mirror}"]

[calendar]
id = "familia@calendar.example.org"
shared_with = []

[downloads]
folder = "~/Downloads"

[sync]
full_review_days = 7
lock_idle_minutes = 30
kept_captures = 10

[tools]
folder = "{tools}"
repository = "~/opt/alfabeta"

[sciencebits]
url = ""
languages = []

[notebook]
enabled = false
share_with = []
title_pattern = "{{grade}}. {{subject}}. {{topic}}"
nlm_profile = "prueba"
owner = "familia@example.com"
refresh_minutes = 15

[notes]
model = "claude-sonnet-5-5"
price_in = 2.0
price_out = 10.0
warn_pages = 100
cloud_stale_hours = 2

[schedule]
monday = "16:15"
tuesday = "16:15"
wednesday = "15:15"
thursday = "15:15"
friday = "16:15"
saturday = ""
sunday = ""

[google]
project_label = "alfabeta (prueba)"

[google.accounts.student]
role = "student"
address = "alumna@example.com"
scopes = ["openid", "email"]

[[subjects]]
folder = "Mates"
classroom_class = "Matemáticas 3º"
book = ""
book_class = ""
language = "es"
"""


@pytest.fixture
def home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    (home / "s9").mkdir(parents=True)
    (tmp_path / "base").mkdir()
    (tmp_path / "mirror").mkdir()
    write(home, _full(tmp_path / "base", tmp_path / "tools", tmp_path / "mirror"))
    return home


def write(home: Path, text: str) -> None:
    (home / "s9" / "config.toml").write_text(text)


def text(home: Path) -> str:
    return (home / "s9" / "config.toml").read_text()


def keys(problems: list[config.Problem]) -> list[tuple[str, str]]:
    return [(p.key, p.reason) for p in problems]


def test_the_full_invented_configuration_is_valid(home: Path):
    assert config.check(home, "s9") == ([], [])


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        ('grade_level = "3º ESO"\n', "", ("student.grade_level", "missing")),
        ("kept_captures = 10\n", f'kept_captures = 10\nnickname = "{SECRET_VALUE}"\n', ("sync.nickname", "extra")),
        ("kept_captures = 10", f'kept_captures = "{SECRET_VALUE}"', ("sync.kept_captures", "type")),
        ("enabled = false", "enabled = 0", ("notebook.enabled", "type")),
        ('grade_level = "3º ESO"', f'grade_level = "{SECRET_VALUE} CHANGEME"', ("student.grade_level", "unset")),
        ('languages = ["es", "en"]', 'languages = ["es", "changeme"]', ("student.languages", "unset")),
        ('languages = ["es", "en"]', "languages = [1]", ("student.languages", "type")),
        ('book = ""\n', f'book = ""\nshelf = "{SECRET_VALUE}"\n', ("subjects[0].shelf", "extra")),
        ('language = "es"\n', "", ("subjects[0].language", "missing")),
        ('role = "student"\n', "", ("google.accounts.student.role", "missing")),
        ("[google.accounts.student]", '[google.accounts."Nombre Real"]', ("google.accounts.<name>", "invalid_name")),
    ],
)
def test_each_problem_names_the_key_never_the_value(home: Path, old: str, new: str, expected: tuple[str, str]):
    assert old in text(home)
    write(home, text(home).replace(old, new, 1))
    problems, _ = config.check(home, "s9")
    assert keys(problems) == [expected]
    shown = " ".join(f"{p.key} {p.reason}" for p in problems)
    assert SECRET_VALUE not in shown and "Nombre Real" not in shown


def test_a_command_validates_only_the_tables_it_reads(home: Path):
    write(home, text(home).replace("kept_captures = 10\n", ""))
    cfg = config.load(home, "s9", ("classroom", "calendar", "google"))
    assert cfg.calendar_id == "familia@calendar.example.org"
    assert cfg.account("student").scopes == ("openid", "email")
    with pytest.raises(config.ConfigError, match=r"sync\.kept_captures \(missing\)"):
        config.load(home, "s9", ("sync",))
    with pytest.raises(config.ConfigError, match="was not loaded"):
        _ = config.load(home, "s9", ("classroom",)).calendar_id


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        ('root = "alfabeta"', 'root = ""', ("drive.root", "is_my_drive")),
        ('root = "alfabeta"', 'root = "/Mi unidad/"', ("drive.root", "is_my_drive")),
        (
            'root = "alfabeta"',
            'root = "~/Library/CloudStorage/GoogleDrive-x/Mi unidad/alfabeta"',
            ("drive.root", "local_path"),
        ),
    ],
)
def test_drive_root_is_a_folder_inside_my_drive(home: Path, old: str, new: str, expected: tuple[str, str]):
    write(home, text(home).replace(old, new, 1))
    assert keys(config.check(home, "s9")[0]) == [expected]


def test_base_folder_must_exist_and_stay_out_of_the_drive_mount(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    base = str(tmp_path / "base")
    write(home, text(home).replace(base, str(tmp_path / "nowhere")))
    problems, _ = config.check(home, "s9")
    assert keys(problems) == [("storage.base", "not_found")]
    assert str(tmp_path) not in " ".join(p.key + p.reason for p in problems)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    mounted = tmp_path / "Library" / "CloudStorage" / "GoogleDrive-alguien" / "Mi unidad" / "alfabeta"
    mounted.mkdir(parents=True)
    write(home, text(home).replace(str(tmp_path / "nowhere"), str(mounted)))
    assert keys(config.check(home, "s9")[0]) == [("storage.base", "inside_drive_mount")]


def test_data_and_tools_folders_stay_out_of_the_base_folder(home: Path, tmp_path: Path):
    write(home, text(home).replace(str(tmp_path / "base"), str(home)).replace(str(tmp_path / "tools"), str(home / "t")))
    assert keys(config.check(home, "s9")[0]) == [
        ("storage.base", "contains_data_folder"),
        ("tools.folder", "inside_base"),
    ]


def test_mirrors_never_overlap_the_base_and_unmounted_is_a_warning(home: Path, tmp_path: Path):
    mirror = str(tmp_path / "mirror")
    write(home, text(home).replace(mirror, str(tmp_path / "base" / "sub")))
    assert keys(config.check(home, "s9")[0]) == [("drive.mirrors[0]", "overlaps_base")]
    write(home, text(home).replace(str(tmp_path / "base" / "sub"), str(tmp_path / "gone")))
    assert config.check(home, "s9") == ([], [config.Problem("drive.mirrors[0]", "not_mounted")])


def test_student_id_is_lowercase_ascii(home: Path):
    with pytest.raises(config.ConfigError, match="lowercase ASCII"):
        config.check(home, "S9")


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-m", "alfabeta", *args], capture_output=True, text=True, check=False)


def test_config_check_command(home: Path):
    done = _cli("--home", str(home), "config", "check", "--student", "s9")
    assert done.returncode == 0, done.stderr
    assert '"ok": true' in done.stdout
    write(home, text(home).replace("kept_captures = 10", f'kept_captures = "{SECRET_VALUE}"'))
    done = _cli("--home", str(home), "config", "check", "--student", "s9")
    assert done.returncode == 1
    assert "sync.kept_captures" in done.stdout and SECRET_VALUE not in done.stdout + done.stderr


def test_missing_home_is_not_created(tmp_path: Path):
    done = _cli("--home", str(tmp_path / "nope"), "config", "check", "--student", "s9")
    assert done.returncode == 1 and '"no_home"' in done.stdout
    assert not (tmp_path / "nope").exists()


def test_drive_root_is_read_for_scoped_drive(home: Path):
    assert config.load(home, "s9", ("drive",)).drive_root == "alfabeta"  # spec 004 R6


def test_notes_and_notebook_keys_of_spec_005(home: Path):
    cfg = config.load(home, "s9", ("notes", "notebook"))
    assert cfg.notes_model == "claude-sonnet-5-5"
    assert cfg.notes_prices == (2.0, 10.0)
    assert (cfg.notes_warn_pages, cfg.cloud_stale_hours) == (100, 2)
    assert cfg.notebook_title_pattern == "{grade}. {subject}. {topic}"
    assert cfg.nlm_profile == "prueba"
    assert cfg.notebook_owner == "familia@example.com"


def test_each_subject_carries_its_language(home: Path):  # spec 002 FR-005
    assert [s.language for s in config.load(home, "s9", ("subjects",)).subjects] == ["es"]
    write(home, text(home).replace('language = "es"', 'language = ""'))
    with pytest.raises(config.ConfigError, match=r"subjects\.\*\.language is empty"):
        _ = config.load(home, "s9", ("subjects",)).subjects


@pytest.mark.parametrize("bad", ["price_in = 0.0", "price_in = -1.0", "price_in = nan", "price_in = inf"])
def test_a_price_of_zero_or_less_is_refused(home: Path, bad: str):
    write(home, text(home).replace("price_in = 2.0", bad, 1))
    with pytest.raises(config.ConfigError, match=r"notes\.price_in must be a number above 0"):
        _ = config.load(home, "s9", ("notes",)).notes_prices


def test_an_integer_price_is_a_type_problem(home: Path):
    write(home, text(home).replace("price_in = 2.0", "price_in = 2", 1))
    assert ("notes.price_in", "type") in keys(config.check(home, "s9")[0])
