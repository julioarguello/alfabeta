"""The topic's notebook and its sources, through `nlm` (spec 005 research R9). Mac only.

`nlm` (notebooklm-mcp-cli) talks to the notebook's internal API with the operator's own sign-in; the
cloud image does not include it (constitution IV: optional, may break). Output shapes read from its
source, version 0.15.8, on 2026-10-27: `notebook list --json` is a list of `{id, title, ...}`, `source
list --json` a list of `{id, title, ...}`, `source add --json` one `{source_type, source_id, title}`,
and any error with `--json` is `{status: "error", error, hint?}` with exit 1; not signed in carries the
hint "Run 'nlm login' to authenticate."
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

from alfabeta.google.keychain import run_command

if TYPE_CHECKING:
    from alfabeta.google.keychain import Runner


class SourcesError(Exception):
    """`nlm` failed; `signed_out` when the operator must sign in again (exit 5)."""

    def __init__(self, signed_out: bool) -> None:
        super().__init__("nlm is not signed in" if signed_out else "nlm failed")
        self.signed_out = signed_out


@dataclass(frozen=True)
class Source:
    """One source of a notebook."""

    id: str
    title: str


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


class NlmSources:
    """`NotebookSources` over the `nlm` command, with one profile."""

    def __init__(self, profile: str, runner: Runner = run_command) -> None:
        self._profile = profile
        self._run = runner

    def _json(self, *args: str) -> Any:
        done = self._run(["nlm", *args, "--json", "--profile", self._profile], None)
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
        return [Source(str(s.get("id", "")), str(s.get("title", ""))) for s in listed]
