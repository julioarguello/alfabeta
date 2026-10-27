"""The student's private configuration, `<home>/<student>/config.toml`.

Only the keys spec 004's commands read. Spec 001 (T019) replaces this with the loader that validates
every key against `config/template.toml`.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from pathlib import Path


class ConfigError(Exception):
    """The configuration is missing or a key this command needs is absent or invalid."""


@dataclass(frozen=True)
class AccountConfig:
    """One Google account linked to alfabeta's app (spec 004 data model, LinkedAccount)."""

    alias: str
    role: str
    address: str
    scopes: tuple[str, ...]


@dataclass(frozen=True)
class StudentConfig:
    """The keys spec 004 reads, resolved once per command."""

    student: str
    root: Path
    school_account: str
    calendar_id: str
    accounts: dict[str, AccountConfig]

    @property
    def data_dir(self) -> Path:
        """The student's data folder."""
        return self.root / "data"

    def account(self, alias: str) -> AccountConfig:
        """The linked account with that alias."""
        try:
            return self.accounts[alias]
        except KeyError:
            raise ConfigError(f"no [google.accounts.{alias}] in the configuration") from None


def _table(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ConfigError(f"missing table [{key}]")
    return cast("dict[str, Any]", value)


def _text(table: dict[str, Any], key: str, where: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value or "changeme" in value:
        raise ConfigError(f"missing or unset key {where}.{key}")
    return value


def load(home: Path, student: str) -> StudentConfig:
    """Load the student's configuration from `<home>/<student>/config.toml`."""
    root = home / student
    path = root / "config.toml"
    if not path.is_file():
        raise ConfigError(f"no configuration for student {student!r}")
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    classroom = _table(data, "classroom")
    calendar = _table(data, "calendar")
    google = _table(data, "google")
    raw_accounts = google.get("accounts")
    if not isinstance(raw_accounts, dict) or not raw_accounts:
        raise ConfigError("missing table [google.accounts.<alias>]")
    accounts: dict[str, AccountConfig] = {}
    for alias, raw in cast("dict[str, Any]", raw_accounts).items():
        if not isinstance(raw, dict):
            raise ConfigError(f"[google.accounts.{alias}] must be a table")
        table = cast("dict[str, Any]", raw)
        where = f"google.accounts.{alias}"
        scopes = table.get("scopes")
        if not isinstance(scopes, list) or not scopes or not all(isinstance(s, str) for s in cast("list[Any]", scopes)):
            raise ConfigError(f"missing or invalid key {where}.scopes")
        accounts[alias] = AccountConfig(
            alias=alias,
            role=_text(table, "role", where),
            address=_text(table, "address", where),
            scopes=tuple(cast("list[str]", scopes)),
        )
    return StudentConfig(
        student=student,
        root=root,
        school_account=_text(classroom, "account", "classroom"),
        calendar_id=_text(calendar, "id", "calendar"),
        accounts=accounts,
    )
