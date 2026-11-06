"""Configuration against the template (spec 001 T018). Every value is invented."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from alfabeta import config, sandbox

SECRET_VALUE = "valor-que-no-debe-salir"


def _full(base: Path, tools: Path, mirror: Path) -> str:
    return f"""
[student]
display_name = "Alumna Inventada"
school_year = "2026-2027"
grade_level = "3º ESO"
languages = ["es", "en"]
rules_both = ""
rules_problems = ""
rules_theory = ""

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
wait_minutes = 60

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
rules_both = ""
rules_problems = ""
rules_theory = ""
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


@pytest.mark.parametrize(
    ("where", "reason"),
    [
        ("base", "overlaps_base"),
        ("base/sub", "overlaps_base"),
        ("", "overlaps_base"),
        ("drive/Mi unidad", "is_my_drive"),
    ],
    ids=["the-base", "inside-the-base", "contains-the-base", "my-drive"],
)
def test_a_mirror_that_is_the_base_holds_it_or_is_my_drive_is_refused(
    home: Path, tmp_path: Path, where: str, reason: str
):
    (tmp_path / where).mkdir(parents=True, exist_ok=True)
    write(home, text(home).replace(str(tmp_path / "mirror"), str(tmp_path / where).rstrip("/")))
    assert keys(config.check(home, "s9")[0]) == [("drive.mirrors[0]", reason)]


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


@pytest.mark.parametrize(("value", "ok"), [("0", True), ("60", True), ("-1", False), ("true", False), ('"60"', False)])
def test_the_sign_in_wait_takes_a_whole_number_of_minutes_from_zero(tmp_path: Path, value: str, ok: bool):
    sandbox.prepare(tmp_path, "sample")
    path = tmp_path / "sample" / "config.toml"
    path.write_text(path.read_text().replace("wait_minutes = 60\n", f"wait_minutes = {value}\n"))
    if ok:
        assert config.load(tmp_path, "sample", ("schedule",)).schedule_wait_minutes == int(value)
    else:
        with pytest.raises(config.ConfigError, match="schedule.wait_minutes"):
            _ = config.load(tmp_path, "sample", ("schedule",)).schedule_wait_minutes


# --- standing rules (spec 009) -------------------------------------------------------------------------


RULE_KEYS = ("rules_both", "rules_problems", "rules_theory")


def _with_rules(base: str, *, student: dict[str, str] | None = None, subject: dict[str, str] | None = None) -> str:
    """`base` with its empty rule keys given literal strings, as the template says to write them."""
    head, tail = base.split("[[subjects]]")
    for key, value in (student or {}).items():
        head = head.replace(f'{key} = ""', f"{key} = '''{value}'''")
    for key, value in (subject or {}).items():
        tail = tail.replace(f'{key} = ""', f"{key} = '''{value}'''")
    return f"{head}[[subjects]]{tail}"


def test_empty_rule_keys_are_valid_and_mean_no_rule(home: Path):
    rules = config.load_all(home, "s9").rules("Mates")
    assert rules.parts("problems") == [] and rules.parts("theory") == []


@pytest.mark.parametrize("key", RULE_KEYS)
@pytest.mark.parametrize("table", ["student", "subjects[0]"])
def test_a_missing_rule_key_is_named(home: Path, key: str, table: str):
    head, tail = text(home).split("[[subjects]]")
    line = f'{key} = ""\n'
    write(
        home,
        f"{head.replace(line, '')}[[subjects]]{tail}"
        if table == "student"
        else f"{head}[[subjects]]{tail.replace(line, '')}",
    )
    assert (f"{table}.{key}", "missing") in keys(config.check(home, "s9")[0])


def test_an_unset_or_mistyped_rule_key_is_named_and_never_shown(home: Path):
    secret = "PALABRAPLANTADA"
    written = _with_rules(text(home), student={"rules_both": f"changeme {secret}"})
    write(home, written.replace('rules_theory = ""', "rules_teoria = ''", 1))
    problems = config.check(home, "s9")[0]
    assert ("student.rules_both", "unset") in keys(problems)
    assert ("student.rules_teoria", "extra") in keys(problems)
    assert secret not in str(problems)


def test_a_rule_key_that_is_not_text_is_named(home: Path):
    write(home, text(home).replace('rules_both = ""', "rules_both = 5", 1))
    assert ("student.rules_both", "type") in keys(config.check(home, "s9")[0])


def test_rules_come_stripped_from_the_student_and_that_subject_alone(home: Path):
    head, first = _with_rules(text(home), student={"rules_both": "  del alumno \n", "rules_theory": "   "}).split(
        "[[subjects]]"
    )
    other = first.replace('folder = "Mates"', 'folder = "Otra"').replace(
        'rules_problems = ""', "rules_problems = 'de la otra'"
    )
    mates = first.replace('rules_problems = ""', "rules_problems = 'de mates'")
    write(home, f"{head}[[subjects]]{mates}[[subjects]]{other}")
    rules = config.load_all(home, "s9").rules("Mates")
    assert rules.parts("problems") == [("student.both", "del alumno"), ("subject.problems", "de mates")]
    assert rules.parts("theory") == [("student.both", "del alumno")]  # spaces only count as empty


def test_a_literal_string_keeps_quotes_backslashes_and_line_breaks(home: Path):
    rule = 'Di "raíz" y usa \\frac{a}{b}\ny \\sqrt{x}'
    write(home, _with_rules(text(home), subject={"rules_both": rule}))
    assert config.load_all(home, "s9").rules("Mates").parts("theory") == [("subject.both", rule)]


def test_a_subject_that_is_not_configured_has_no_rules_to_read(home: Path):
    with pytest.raises(config.ConfigError):
        config.load_all(home, "s9").rules("Otra")


def test_the_repr_of_the_rules_holds_no_rule(home: Path):
    write(home, _with_rules(text(home), student={"rules_both": "PALABRAPLANTADA"}))
    assert "PALABRAPLANTADA" not in repr(config.load_all(home, "s9").rules("Mates"))


def test_only_exam_build_reads_the_rules():
    # FR-013: `config check` validates them and the guardrail compares them; nothing else uses them.
    src = Path(config.__file__).parent
    readers = {str(p.relative_to(src)) for p in src.rglob("*.py") if ".rules(" in p.read_text()}
    assert readers == {"exam/cli.py"}
