"""Shared fakes. Every value here is invented; no test calls Google or the real keychain."""

from __future__ import annotations

import base64
import json
import subprocess
import urllib.parse
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from alfabeta.google.transport import Response

STUDENT_ADDRESS = "estudiante.inventado@example.com"
SCHOOL_ADDRESS = "alumno.inventado@colegio.example.org"
CALENDAR_ID = "familia-inventada@calendar.example.org"

CONFIG = f"""
[classroom]
account = "{SCHOOL_ADDRESS}"

[calendar]
id = "{CALENDAR_ID}"

[google]
project_label = "alfabeta (prueba)"

[google.accounts.student]
role = "student"
address = "{STUDENT_ADDRESS}"
scopes = ["https://www.googleapis.com/auth/calendar.events", "https://www.googleapis.com/auth/drive", "openid", "email"]
"""

GRANTED = (
    "https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/drive "
    "openid https://www.googleapis.com/auth/userinfo.email"
)


def id_token(email: str) -> str:
    def seg(obj: dict[str, object]) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")

    return f"{seg({'alg': 'RS256'})}.{seg({'email': email, 'sub': '123'})}.firma"


@dataclass
class FakeTransport:
    """Serves queued responses in order and records every request; fails on an unexpected one."""

    responses: list[Response] = field(default_factory=lambda: [])
    calls: list[tuple[str, str, dict[str, str], bytes | None]] = field(default_factory=lambda: [])

    def request(
        self, method: str, url: str, *, headers: dict[str, str] | None = None, body: bytes | None = None
    ) -> Response:
        self.calls.append((method, url, dict(headers or {}), body))
        if not self.responses:
            raise AssertionError(f"unexpected request {method} {urllib.parse.urlparse(url).path}")
        return self.responses.pop(0)


def json_response(status: int, data: Mapping[str, object]) -> Response:
    return Response(status, json.dumps(data).encode())


class MemoryStore:
    """`TokenStore` in memory."""

    def __init__(self) -> None:
        self.items: dict[str, str] = {}

    def get(self, account: str) -> str | None:
        return self.items.get(account)

    def set(self, account: str, secret: str) -> None:
        self.items[account] = secret

    def delete(self, account: str) -> None:
        self.items.pop(account, None)


@pytest.fixture
def home(tmp_path: Path) -> Path:
    (tmp_path / "s9").mkdir()
    (tmp_path / "s9" / "config.toml").write_text(CONFIG)
    return tmp_path


@pytest.fixture
def store() -> MemoryStore:
    s = MemoryStore()
    s.set("s9/client", json.dumps({"client_id": "id-inventado", "client_secret": "secreto-inventado"}))
    return s


RunnerFn = Callable[[list[str], str | None], subprocess.CompletedProcess[str]]
