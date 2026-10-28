"""The student's private configuration, `<home>/<student>/config.toml` (spec 001 FR-001…FR-004).

The repository's `config/template.toml` is the contract: a key that is missing, extra, changes type
or contains `changeme` is a problem named by its key, never by its value (FR-003). `config check`
compares the whole file; a command loads only the tables it reads, so a run is not stopped by a
table it never touches (spec 001 T024).

Every read goes through a reader (`READERS`) with the key's dotted path as a string literal, so
`tests/test_template_covers_reads.py` can check that the template declares every key read.
"""

from __future__ import annotations

import math
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from alfabeta.model import Subject

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

TEMPLATE = Path(__file__).resolve().parents[2] / "config" / "template.toml"
# A template table whose only child is this table holds one table per name the operator chooses.
DYNAMIC = "changeme"
READERS = frozenset({"_str", "_strs", "_int", "_float", "_names", "_count"})

_NAME = re.compile(r"[a-z][a-z0-9_-]*")
# Google Drive for desktop mounts every account under this folder (spec 004 R7).
_DRIVE_MOUNTS = Path("Library") / "CloudStorage"
_MY_DRIVE = frozenset({"mi unidad", "my drive"})


class ConfigError(Exception):
    """The configuration is missing or a key this command needs is absent or invalid."""


@dataclass(frozen=True)
class Problem:
    """A key and what is wrong with it; never its value."""

    key: str
    reason: str

    def as_json(self) -> dict[str, str]:
        """The `{key, reason}` shape of `config check`."""
        return {"key": self.key, "reason": self.reason}


@dataclass(frozen=True)
class AccountConfig:
    """One Google account linked to alfabeta's app (spec 004 data model, LinkedAccount)."""

    alias: str
    role: str
    address: str
    scopes: tuple[str, ...]


def _at(data: Mapping[str, Any], path: str, names: tuple[str, ...]) -> Any:
    node: Any = data
    pending = list(names)
    for part in path.split("."):
        step = pending.pop(0) if part == "*" else part
        if isinstance(node, list) and step.isdigit() and int(step) < len(cast("list[Any]", node)):
            node = cast("list[Any]", node)[int(step)]
            continue
        if not isinstance(node, dict) or step not in node:
            raise ConfigError(f"key {path} was not loaded")
        node = cast("dict[str, Any]", node)[step]
    return node


def _str(data: Mapping[str, Any], path: str, *names: str, allow_empty: bool = False) -> str:
    value = _at(data, path, names)
    if not isinstance(value, str) or (not value and not allow_empty):
        raise ConfigError(f"key {path} is empty")
    return value


def _strs(data: Mapping[str, Any], path: str, *names: str, allow_empty: bool = False) -> tuple[str, ...]:
    value = _at(data, path, names)
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ConfigError(f"key {path} is empty")
    return tuple(cast("list[str]", value))


def _int(data: Mapping[str, Any], path: str, *names: str) -> int:
    value = _at(data, path, names)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ConfigError(f"key {path} must be a whole number of at least 1")
    return value


def _count(data: Mapping[str, Any], path: str, *names: str) -> int:
    value = _at(data, path, names)
    if not isinstance(value, list):
        raise ConfigError(f"key {path} is not a list")
    return len(cast("list[Any]", value))


def _float(data: Mapping[str, Any], path: str, *names: str) -> float:
    value = _at(data, path, names)
    if not isinstance(value, float) or not math.isfinite(value) or value <= 0:
        raise ConfigError(f"key {path} must be a number above 0")
    return value


def _names(data: Mapping[str, Any], path: str, *names: str) -> tuple[str, ...]:
    value = _at(data, path, names)
    if not isinstance(value, dict):
        raise ConfigError(f"key {path} is not a table")
    return tuple(sorted(cast("dict[str, Any]", value)))


@dataclass(frozen=True)
class StudentConfig:
    """The validated tables of one student's configuration, read through the readers."""

    student: str
    root: Path
    data: Mapping[str, Any] = field(repr=False)

    @property
    def data_dir(self) -> Path:
        """The student's data folder."""
        return self.root / "data"

    @property
    def drive_root(self) -> str:
        """The alfabeta folder's path inside the student's My Drive (spec 004 R6)."""
        return _str(self.data, "drive.root")

    @property
    def school_account(self) -> str:
        """The school account's address."""
        return _str(self.data, "classroom.account")

    @property
    def calendar_id(self) -> str:
        """The family calendar alfabeta writes to."""
        return _str(self.data, "calendar.id")

    @property
    def grade_level(self) -> str:
        """The student's grade, as the notebook titles name it (spec 005 `{grade}`)."""
        return _str(self.data, "student.grade_level")

    @property
    def school_year(self) -> str:
        """The school year, `YYYY-YYYY`."""
        return _str(self.data, "student.school_year")

    @property
    def base(self) -> Path:
        """The student's base folder on the Mac."""
        return Path(_str(self.data, "storage.base")).expanduser()

    @property
    def full_review_days(self) -> int:
        """Every how many days every attachment is downloaded again."""
        return _int(self.data, "sync.full_review_days")

    @property
    def kept_captures(self) -> int:
        """How many captures of each class stay in the data folder."""
        return _int(self.data, "sync.kept_captures")

    @property
    def subjects(self) -> tuple[Subject, ...]:
        """The configured subjects, in order."""
        return tuple(
            Subject(
                folder=_str(self.data, "subjects.*.folder", str(i)),
                classroom_class=_str(self.data, "subjects.*.classroom_class", str(i)),
                book=_str(self.data, "subjects.*.book", str(i), allow_empty=True),
                book_class=_str(self.data, "subjects.*.book_class", str(i), allow_empty=True),
                language=_str(self.data, "subjects.*.language", str(i)),
            )
            for i in range(_count(self.data, "subjects"))
        )

    @property
    def downloads_folder(self) -> str:
        """Where the browser leaves its downloads."""
        return _str(self.data, "downloads.folder")

    @property
    def lock_idle_minutes(self) -> int:
        """Minutes without renewal after which a dead run's lock is released."""
        return _int(self.data, "sync.lock_idle_minutes")

    @property
    def notebook_title_pattern(self) -> str:
        """The name of each topic's notebook, with `{grade}`, `{subject}` and `{topic}`."""
        return _str(self.data, "notebook.title_pattern")

    @property
    def nlm_profile(self) -> str:
        """The `nlm` profile of the account that owns the notebooks."""
        return _str(self.data, "notebook.nlm_profile")

    @property
    def notebook_owner(self) -> str:
        """The address each living file is shared with, as reader; never shown."""
        return _str(self.data, "notebook.owner")

    @property
    def notes_model(self) -> str:
        """The Claude model that transcribes the student's notes."""
        return _str(self.data, "notes.model")

    @property
    def notes_prices(self) -> tuple[float, float]:
        """The model's price in USD per million tokens, in and out."""
        return _float(self.data, "notes.price_in"), _float(self.data, "notes.price_out")

    @property
    def notes_warn_pages(self) -> int:
        """Pages a living file may hold before the family is warned."""
        return _int(self.data, "notes.warn_pages")

    @property
    def cloud_stale_hours(self) -> int:
        """Hours without a successful cloud run after which the Mac warns."""
        return _int(self.data, "notes.cloud_stale_hours")

    @property
    def accounts(self) -> dict[str, AccountConfig]:
        """The linked Google accounts by alias."""
        return {
            alias: AccountConfig(
                alias=alias,
                role=_str(self.data, "google.accounts.*.role", alias),
                address=_str(self.data, "google.accounts.*.address", alias),
                scopes=_strs(self.data, "google.accounts.*.scopes", alias),
            )
            for alias in _names(self.data, "google.accounts")
        }

    def account(self, alias: str) -> AccountConfig:
        """The linked account with that alias."""
        try:
            return self.accounts[alias]
        except KeyError:
            raise ConfigError(f"no [google.accounts.{alias}] in the configuration") from None


def load_template(path: Path = TEMPLATE) -> dict[str, Any]:
    """The repository's template."""
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _is_dynamic(example: dict[str, Any]) -> bool:
    return list(example) == [DYNAMIC] and isinstance(example[DYNAMIC], dict)


def _join(key: str, child: str) -> str:
    return f"{key}.{child}" if key else child


def _compare(value: Any, example: Any, key: str, problems: list[Problem]) -> None:
    if isinstance(example, dict):
        if not isinstance(value, dict):
            problems.append(Problem(key, "type"))
            return
        table = cast("dict[str, Any]", value)
        template = cast("dict[str, Any]", example)
        if _is_dynamic(template):
            if not table:
                problems.append(Problem(f"{key}.<name>", "missing"))
            for name, child in table.items():
                if _NAME.fullmatch(name):
                    _compare(child, template[DYNAMIC], f"{key}.{name}", problems)
                else:
                    problems.append(Problem(f"{key}.<name>", "invalid_name"))
            return
        problems.extend(Problem(_join(key, k), "missing") for k in template if k not in table)
        problems.extend(Problem(_join(key, k), "extra") for k in table if k not in template)
        for k in template:
            if k in table:
                _compare(table[k], template[k], _join(key, k), problems)
    elif isinstance(example, list):
        if not isinstance(value, list):
            problems.append(Problem(key, "type"))
            return
        items = cast("list[Any]", value)
        element = cast("list[Any]", example)[0]
        for index, item in enumerate(items):
            where = f"{key}[{index}]" if isinstance(element, dict) else key
            _compare(item, element, where, problems)
    elif type(value) is not type(example):  # bool is an int to isinstance
        problems.append(Problem(key, "type"))
    elif isinstance(value, str) and "changeme" in value.lower():
        problems.append(Problem(key, "unset"))


def validate(
    data: Mapping[str, Any], template: Mapping[str, Any], tables: Iterable[str] | None = None
) -> list[Problem]:
    """Problems of `data` against `template`, over every table or only `tables`."""
    problems: list[Problem] = []
    if tables is None:
        _compare(dict(data), dict(template), "", problems)
    else:
        for name in tables:
            if name not in data:
                problems.append(Problem(name, "missing"))
            else:
                _compare(data[name], template[name], name, problems)
    # One problem per key and reason: a list of scalars reports its key once.
    return list(dict.fromkeys(problems))


def student_root(home: Path, student: str) -> Path:
    """The student's folder in `home`, without reading their configuration."""
    if not _NAME.fullmatch(student):
        raise ConfigError("the student id must be lowercase ASCII")
    root = home / student
    if not root.is_dir():
        raise ConfigError(f"no configuration for student {student!r}")
    return root


def _read(home: Path, student: str) -> tuple[Path, dict[str, Any]]:
    root = student_root(home, student)
    path = root / "config.toml"
    if not path.is_file():
        raise ConfigError(f"no configuration for student {student!r}")
    try:
        with path.open("rb") as handle:
            return root, tomllib.load(handle)
    except tomllib.TOMLDecodeError as err:
        raise ConfigError(f"config.toml is not valid TOML ({err})") from None


def load_all(home: Path, student: str, template: Path = TEMPLATE) -> StudentConfig:
    """Load and validate every table of the template (the commands that act on the student's folder)."""
    return load(home, student, tuple(load_template(template)), template)


def load(home: Path, student: str, tables: Iterable[str], template: Path = TEMPLATE) -> StudentConfig:
    """Load the student's configuration, validating the tables this command reads."""
    root, data = _read(home, student)
    wanted = tuple(tables)
    problems = validate(data, load_template(template), wanted)
    if problems:
        listed = ", ".join(f"{p.key} ({p.reason})" for p in problems)
        raise ConfigError(f"invalid configuration: {listed}")
    return StudentConfig(student, root, {name: data[name] for name in wanted})


def _inside(path: Path, folder: Path) -> bool:
    return path == folder or folder in path.parents


def _local(value: str) -> Path:
    return Path(value).expanduser()


def _check_places(cfg: StudentConfig, problems: list[Problem], warnings: list[Problem]) -> None:
    data = cfg.data
    base = _local(_str(data, "storage.base"))
    if not base.is_absolute():
        problems.append(Problem("storage.base", "not_absolute"))
    elif not base.is_dir():
        problems.append(Problem("storage.base", "not_found"))
    mounts = Path.home() / _DRIVE_MOUNTS
    if any(p.parent == mounts and p.name.startswith("GoogleDrive-") for p in (base, *base.parents)):
        problems.append(Problem("storage.base", "inside_drive_mount"))
    if _inside(cfg.data_dir, base):
        problems.append(Problem("storage.base", "contains_data_folder"))
    if _inside(_local(_str(data, "tools.folder")), base):
        problems.append(Problem("tools.folder", "inside_base"))

    root = _str(data, "drive.root", allow_empty=True).strip("/")
    if root.startswith("~") or str(_DRIVE_MOUNTS) in root:
        problems.append(Problem("drive.root", "local_path"))
    elif not root or root.lower() in _MY_DRIVE:
        problems.append(Problem("drive.root", "is_my_drive"))

    for index, value in enumerate(_strs(data, "drive.mirrors", allow_empty=True)):
        key = f"drive.mirrors[{index}]"
        mirror = _local(value)
        if mirror.name.lower() in _MY_DRIVE:
            problems.append(Problem(key, "is_my_drive"))
        elif _inside(mirror, base) or _inside(base, mirror):
            problems.append(Problem(key, "overlaps_base"))
        elif not mirror.is_dir():
            warnings.append(Problem(key, "not_mounted"))


def check(home: Path, student: str, template: Path = TEMPLATE) -> tuple[list[Problem], list[Problem]]:
    """Every problem of the whole file, and the warnings (`config check`)."""
    root, data = _read(home, student)
    problems = validate(data, load_template(template))
    warnings: list[Problem] = []
    if not problems:
        _check_places(StudentConfig(student, root, data), problems, warnings)
    return problems, warnings
