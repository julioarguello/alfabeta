"""Secrets in the macOS keychain through the `security` tool (spec 004 research R3).

A secret is written by sending the command on `security -i`'s standard input, so it never appears
in a process's arguments. It is stored base64url-encoded, which keeps the command free of quotes
and makes `find-generic-password -w` print exactly what was stored.
"""

from __future__ import annotations

import base64
import subprocess
from typing import Protocol

SERVICE = "alfabeta.google"
_NOT_FOUND = 44


class KeychainError(Exception):
    """The keychain refused an operation."""


class TokenStore(Protocol):
    """Where linked accounts' refresh tokens and the app's client live."""

    def get(self, account: str) -> str | None:
        """The secret stored for that account, or None."""
        ...

    def set(self, account: str, secret: str) -> None:
        """Store the secret, replacing any earlier one."""
        ...

    def delete(self, account: str) -> None:
        """Remove the secret if present."""
        ...


class Runner(Protocol):
    """Runs one command; the seam the tests replace."""

    def __call__(self, argv: list[str], stdin: str | None) -> subprocess.CompletedProcess[str]:
        """Run it."""
        ...


def run_command(argv: list[str], stdin: str | None) -> subprocess.CompletedProcess[str]:
    """Run a command and capture its output."""
    return subprocess.run(argv, input=stdin, capture_output=True, text=True, check=False)


class KeychainStore:
    """`TokenStore` over the login keychain."""

    def __init__(self, runner: Runner = run_command) -> None:
        self._run = runner

    def get(self, account: str) -> str | None:
        """Read a secret; None when there is none."""
        done = self._run(["security", "find-generic-password", "-s", SERVICE, "-a", account, "-w"], None)
        if done.returncode == _NOT_FOUND:
            return None
        if done.returncode != 0:
            raise KeychainError(f"find-generic-password exited {done.returncode}")
        return base64.urlsafe_b64decode(done.stdout.strip().encode()).decode()

    def set(self, account: str, secret: str) -> None:
        """Write a secret through `security -i`, never through argv."""
        encoded = base64.urlsafe_b64encode(secret.encode()).decode()
        command = f"add-generic-password -U -s {SERVICE} -a {account} -w {encoded}\n"
        done = self._run(["security", "-i"], command)
        if done.returncode != 0 or "error" in done.stderr.lower():
            raise KeychainError("add-generic-password failed")

    def delete(self, account: str) -> None:
        """Remove a secret; absent is fine."""
        done = self._run(["security", "delete-generic-password", "-s", SERVICE, "-a", account], None)
        if done.returncode not in (0, _NOT_FOUND):
            raise KeychainError(f"delete-generic-password exited {done.returncode}")
