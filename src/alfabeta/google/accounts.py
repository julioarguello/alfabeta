"""Linking accounts to alfabeta's app and checking them on every run (spec 004 US1, data model)."""

from __future__ import annotations

import contextlib
import datetime as dt
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from alfabeta.google import oauth
from alfabeta.google.transport import HttpTransport, TransportError

if TYPE_CHECKING:
    from pathlib import Path

    from alfabeta.config import AccountConfig, StudentConfig
    from alfabeta.google.keychain import TokenStore

STATUSES = ("ok", "revoked", "expired", "missing_scope", "no_token", "network")
_TESTING_WINDOW_DAYS = 8


class LinkError(Exception):
    """Linking stopped; `reason` is the CLI's code."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class AccountStatus:
    """One account's state at the start of a run."""

    alias: str
    status: str
    testing_suspected: bool = False


def client_key(student: str) -> str:
    """Keychain account name of the app's client."""
    return f"{student}/client"


def token_key(student: str, alias: str) -> str:
    """Keychain account name of a linked account's refresh token."""
    return f"{student}/{alias}"


def load_client(store: TokenStore, student: str) -> oauth.Client:
    """The app's client from the keychain."""
    raw = store.get(client_key(student))
    if raw is None:
        raise LinkError("no_client")
    data = cast("dict[str, str]", json.loads(raw))
    return oauth.Client(data["client_id"], data["client_secret"])


def set_client(store: TokenStore, student: str, client_file: Path) -> None:
    """Store the Desktop client from the JSON Google offers for download."""
    try:
        data = cast("dict[str, Any]", json.loads(client_file.read_text()))
        installed = cast("dict[str, Any]", data["installed"])
        client = {"client_id": str(installed["client_id"]), "client_secret": str(installed["client_secret"])}
    except (OSError, ValueError, KeyError, TypeError):
        raise LinkError("bad_client_file") from None
    store.set(client_key(student), json.dumps(client))


def _records_path(config: StudentConfig) -> Path:
    return config.data_dir / "google" / "accounts.json"


def _read_records(config: StudentConfig) -> dict[str, dict[str, str]]:
    path = _records_path(config)
    if not path.is_file():
        return {}
    return cast("dict[str, dict[str, str]]", json.loads(path.read_text()))


def _write_record(config: StudentConfig, alias: str, today: dt.date) -> None:
    records = _read_records(config)
    records[alias] = {"linked_on": today.isoformat()}
    path = _records_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)


def _domain(address: str) -> str:
    return address.rsplit("@", 1)[-1].lower()


def validate_grant(account: AccountConfig, grant: oauth.Grant, school_account: str) -> None:
    """The data model's three link checks; raises LinkError, never prints an address."""
    if grant.email is None:
        raise LinkError("wrong_account")
    if _domain(grant.email) == _domain(school_account):
        raise LinkError("school_account")
    if grant.email.lower() != account.address.lower():
        raise LinkError("wrong_account")
    if not oauth.normalise_scopes(account.scopes) <= grant.scopes:
        raise LinkError("missing_scope")


def link_account(
    config: StudentConfig,
    alias: str,
    store: TokenStore,
    transport: HttpTransport,
    open_browser: Any,
    today: dt.date,
) -> tuple[str, ...]:
    """Run the sign-in, validate it, and store the refresh token. Returns the granted scopes."""
    account = config.account(alias)
    client = load_client(store, config.student)
    try:
        code, verifier, redirect_uri = oauth.receive_code(open_browser, client, account.scopes)
        grant = oauth.exchange_code(transport, client, code, verifier, redirect_uri)
    except oauth.OAuthError as err:
        raise LinkError("denied" if err.reason in ("denied", "bad_state") else err.reason) from None
    try:
        validate_grant(account, grant, config.school_account)
    except LinkError:
        oauth.revoke(transport, grant.refresh_token)
        raise
    store.set(token_key(config.student, alias), grant.refresh_token)
    _write_record(config, alias, today)
    return tuple(sorted(grant.scopes))


def access_token(config: StudentConfig, alias: str, store: TokenStore, transport: HttpTransport) -> str:
    """A fresh access token for a linked account, or LinkError with its status."""
    client = load_client(store, config.student)
    refresh = store.get(token_key(config.student, alias))
    if refresh is None:
        raise LinkError("no_token")
    try:
        return oauth.refresh_access_token(transport, client, refresh)
    except oauth.OAuthError as err:
        raise LinkError(err.reason) from None
    except TransportError:
        raise LinkError("network") from None


def check_accounts(
    config: StudentConfig, store: TokenStore, transport: HttpTransport, today: dt.date
) -> list[AccountStatus]:
    """Refresh every linked account's token; refreshing is also what keeps it from going unused."""
    records = _read_records(config)
    statuses: list[AccountStatus] = []
    for alias in sorted(config.accounts):
        try:
            access_token(config, alias, store, transport)
            statuses.append(AccountStatus(alias, "ok"))
        except LinkError as err:
            status = err.reason if err.reason in STATUSES else "network"
            linked_on = records.get(alias, {}).get("linked_on")
            recent = linked_on is not None and (today - dt.date.fromisoformat(linked_on)).days < _TESTING_WINDOW_DAYS
            statuses.append(AccountStatus(alias, status, testing_suspected=status == "expired" and recent))
    return statuses


def unlink_account(config: StudentConfig, alias: str, store: TokenStore, transport: HttpTransport) -> None:
    """Revoke the account's token at Google and remove it from the keychain."""
    key = token_key(config.student, alias)
    refresh = store.get(key)
    if refresh is not None:
        # Offline: the keychain entry still goes; the account owner can revoke from their settings.
        with contextlib.suppress(TransportError):
            oauth.revoke(transport, refresh)
    store.delete(key)
