"""The topic's notebook and its sources, through `nlm` (spec 005 research R9). Mac only.

`nlm` (notebooklm-mcp-cli) talks to the notebook's internal API with the operator's own sign-in; the
cloud image does not include it (constitution IV: optional, may break). Output shapes read from its
source, version 0.15.8, on 2026-10-27: `notebook list --json` is a list of `{id, title, ...}`, `source
list --json` a list of `{id, title, ...}`, `source add --json` one `{source_type, source_id, title}`,
and any error with `--json` is `{status: "error", error, hint?}` with exit 1; not signed in carries the
hint "Run 'nlm login' to authenticate."

The owner's refresh (research R14, T043) adds three reads that never change a notebook: `source content`,
whose output is discarded and never logged; `login --check`, which exits 0 when the profile's session
works and 2 when it does not (read from `nlm`'s source, 0.15.8, 2026-10-28, as `exam build` uses it); and
`auth refresh`, `--http-only` unless a person at the Mac asked for the renewal through `nlm`'s own
browser profile. Each gets an empty, closed standard input, so a prompt fails instead of waiting.

A source or a notebook that is not there answers `{status: "error", error: "API error (code 5):
NOT_FOUND"}` with exit 1 and no hint, the same for an id deleted a moment ago and for one that never
existed (measured 2026-11-12 with 0.15.8 on a throwaway notebook, julioarguello/alfabeta#235).
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
NOT_FOUND = "NOT_FOUND"  # in the `error` of what was asked for and is not there (measured 2026-11-12)


class SourcesError(Exception):
    """`nlm` failed; `signed_out` when the operator must sign in again (exit 5).

    `not_found` when `nlm` said that what was asked for is not there: a source someone deleted from
    its notebook answers so (measured 2026-11-12).
    """

    def __init__(self, signed_out: bool, message: str = "", *, not_found: bool = False) -> None:
        super().__init__(message or ("nlm is not signed in" if signed_out else "nlm failed"))
        self.signed_out = signed_out
        self.not_found = not_found


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
            signed_out = "nlm login" in str(error.get("hint", "")) or "nlm login" in done.stderr
            raise SourcesError(signed_out, not_found=not signed_out and NOT_FOUND in str(error.get("error", "")))
        return cast("Any", parsed)

    def find_notebook(self, title: str) -> str | None:
        """By exact title; two notebooks with one title is an error, never a guess."""
        found = [nb for nb in cast("list[dict[str, Any]]", self._json("notebook", "list")) if nb.get("title") == title]
        if len(found) > 1:
            raise SourcesError(signed_out=False)
        return str(found[0]["id"]) if found else None

    def notebooks(self) -> list[tuple[str, str]]:
        """The id and the title of every notebook of the profile, as `nlm notebook list` gives them."""
        listed: object = self._json("notebook", "list", stdin="")
        if not isinstance(listed, list):  # an answer that is not the list read in nlm's source
            raise SourcesError(signed_out=False)
        rows = [cast("dict[str, Any]", nb) for nb in cast("list[object]", listed) if isinstance(nb, dict)]
        return [(str(nb.get("id", "")), str(nb.get("title", ""))) for nb in rows]

    def collaborators(self, notebook: str) -> dict[str, str]:
        """The role of each address `nlm share status` lists; never printed or logged (FR-031).

        Its shape, read on 2026-11-12 (nlm 0.15.8): `{is_public, access_level, public_link, collaborators:
        [{email, role, is_pending, display_name}]}`; only the address and the role are read, so a
        pending editor is an editor.
        """
        status: object = self._json("share", "status", notebook, stdin="")
        listed: object = cast("dict[str, Any]", status).get("collaborators") if isinstance(status, dict) else None
        if not isinstance(listed, list):
            raise SourcesError(signed_out=False)
        rows = [cast("dict[str, Any]", c) for c in cast("list[object]", listed) if isinstance(c, dict)]
        return {str(c.get("email", "")): str(c.get("role", "")) for c in rows}

    def invite_editor(self, notebook: str, address: str) -> None:
        """`nlm share invite --role editor`, which also raises a viewer (measured 2026-11-12); it takes no `--json`."""
        argv = ["nlm", "share", "invite", notebook, address, "--role", "editor", "--profile", self._profile]
        done = self._call(argv, "")
        if done.returncode != 0:
            raise SourcesError(signed_out="nlm login" in done.stdout + done.stderr)

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
