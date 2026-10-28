"""The topic's notebook and its sources, through `nlm` (spec 005 research R9). Mac only.

`nlm` (notebooklm-mcp-cli) talks to the notebook's internal API with the operator's own sign-in; the
cloud image does not include it (constitution IV: optional, may break). Output shapes read from its
source, version 0.15.8, on 2026-10-27: `notebook list --json` is a list of `{id, title, ...}`, `source
list --json` a list of `{id, title, ...}`, `source add --json` one `{source_type, source_id, title}`,
and any error with `--json` is `{status: "error", error, hint?}` with exit 1; not signed in carries the
hint "Run 'nlm login' to authenticate."

The owner's refresh (research R14, T043) adds three reads that never change a notebook: `source content`,
whose output is discarded and never logged; `login --check`, which exits 0 when the profile's session
works and 2 when it does not (read from `nlm`'s source, 0.15.8, 2026-10-28, as `exam prep` uses it); and
`auth refresh`, `--http-only` unless a person at the Mac asked for the renewal through `nlm`'s own
browser profile. Each gets an empty, closed standard input, so a prompt fails instead of waiting.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

from alfabeta.google.keychain import run_command

if TYPE_CHECKING:
    from alfabeta.google.keychain import Runner

SIGNED_OUT_CHECK = 2  # `nlm login --check` on a session that does not work
# A command of the unattended refresh that runs longer than this fails, so a hang cannot hold the
# launchd job (which never starts a second copy) until the session ends. Not measured: a bound.
NLM_TIMEOUT_SECONDS = 300
TIMED_OUT = 124  # what `timeout(1)` exits with


class SourcesError(Exception):
    """`nlm` failed; `signed_out` when the operator must sign in again (exit 5)."""

    def __init__(self, signed_out: bool, message: str = "") -> None:
        super().__init__(message or ("nlm is not signed in" if signed_out else "nlm failed"))
        self.signed_out = signed_out


class NlmMissingError(SourcesError):
    """`nlm` cannot be run at all: not installed, or not on this process's `PATH` (`no_nlm`, never 5)."""

    def __init__(self) -> None:
        super().__init__(signed_out=False, message="nlm cannot be run")


def run_bounded(argv: list[str], stdin: str | None) -> subprocess.CompletedProcess[str]:
    """Like `run_command`, but a command still running after `NLM_TIMEOUT_SECONDS` fails."""
    try:
        return subprocess.run(
            argv, input=stdin, capture_output=True, text=True, check=False, timeout=NLM_TIMEOUT_SECONDS
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(argv, TIMED_OUT, "", "timed out")


@dataclass(frozen=True)
class Source:
    """One source of a notebook."""

    id: str
    title: str
    url: str = ""  # empty for a Drive source (measured 2026-10-27)


class NotebookSources(Protocol):
    """A notebook and its sources."""

    def find_notebook(self, title: str) -> str | None:
        """The id of the notebook with exactly that title, or None."""
        ...

    def add_drive_source(self, notebook: str, file_id: str, title: str) -> str:
        """Add a Drive PDF as a source; its source id."""
        ...

    def list_sources(self, notebook: str) -> list[Source]:
        """The notebook's sources."""
        ...

    def read_source(self, source_id: str) -> None:
        """Read a source once as the owner, which makes the notebook take its file's latest revision."""
        ...

    def session_ok(self) -> bool:
        """Whether the owner's session works now."""
        ...

    def renew_session(self, browser: bool) -> bool:
        """Try to renew the owner's session; `browser` only with a person at the Mac. True if it ran."""
        ...


class NlmSources:
    """`NotebookSources` over the `nlm` command, with one profile."""

    def __init__(self, profile: str, runner: Runner = run_command) -> None:
        self._profile = profile
        self._run = runner

    def _call(self, argv: list[str], stdin: str | None) -> subprocess.CompletedProcess[str]:
        try:
            return self._run(argv, stdin)
        except OSError:  # not installed, not on PATH, not executable
            raise NlmMissingError from None

    def _json(self, *args: str, stdin: str | None = None) -> Any:
        done = self._call(["nlm", *args, "--json", "--profile", self._profile], stdin)
        try:
            parsed: object = json.loads(done.stdout) if done.stdout.strip() else None
        except json.JSONDecodeError:
            parsed = None
        error = cast("dict[str, Any]", parsed) if isinstance(parsed, dict) else {}
        if done.returncode != 0 or error.get("status") == "error":
            raise SourcesError(signed_out="nlm login" in str(error.get("hint", "")) or "nlm login" in done.stderr)
        return cast("Any", parsed)

    def find_notebook(self, title: str) -> str | None:
        """By exact title; two notebooks with one title is an error, never a guess."""
        found = [nb for nb in cast("list[dict[str, Any]]", self._json("notebook", "list")) if nb.get("title") == title]
        if len(found) > 1:
            raise SourcesError(signed_out=False)
        return str(found[0]["id"]) if found else None

    def add_drive_source(self, notebook: str, file_id: str, title: str) -> str:
        """`--wait`: the source is processed before the id is recorded."""
        args = ("source", "add", notebook, "--drive", file_id, "--type", "pdf", "--title", title, "--wait")
        result = cast("dict[str, Any]", self._json(*args))
        return str(result["source_id"])

    def list_sources(self, notebook: str) -> list[Source]:
        """Every source, in the order `nlm` lists them."""
        listed = cast("list[dict[str, Any]]", self._json("source", "list", notebook))
        return [Source(str(s.get("id", "")), str(s.get("title", "")), str(s.get("url") or "")) for s in listed]

    def read_source(self, source_id: str) -> None:
        """`nlm source content`; the content is not kept, printed or logged (research R14)."""
        self._json("source", "content", source_id, stdin="")

    def session_ok(self) -> bool:
        """`nlm login --check`: 0 works, 2 does not; anything else says nothing about the session."""
        done = self._call(["nlm", "login", "--check", "--profile", self._profile], "")
        if done.returncode == 0:
            return True
        if done.returncode == SIGNED_OUT_CHECK and "Usage:" not in done.stderr:  # click's usage errors exit 2 too
            return False
        raise SourcesError(signed_out=False)

    def renew_session(self, browser: bool) -> bool:
        """`nlm auth refresh --http-only`, which needs no browser; without it only when `browser` is true."""
        mode = () if browser else ("--http-only",)
        return self._call(["nlm", "auth", "refresh", *mode, "--profile", self._profile], "").returncode == 0
