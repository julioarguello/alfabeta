"""The topic's notebook as `exam prep` uses it, through `nlm` (spec 002 contracts/cli.md). Mac only.

Output shapes read from `nlm`'s source, version 0.15.8, on 2026-10-28: `login --check` exits 0 when
the profile's session works and 2 when it does not; `config get auth.default_profile` prints the name;
`studio status <nb> --full --json` is a list of `{id, type, title, status, created_at, ...}` with
`created_at` as `YYYY-MM-DDTHH:MM:SSZ`; `report create --json` is one `{artifact_id, status, ...}`;
`note list --json` is `{notes:[{id, title, ...}], count}`; `studio rename`, `studio delete`,
`note create` and `note update` print text. Every command takes `--profile` but `config`, which reads
nlm's own settings.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

from alfabeta.google.keychain import run_command
from alfabeta.notes.sources import NlmSources, SourcesError

if TYPE_CHECKING:
    from alfabeta.google.keychain import Runner

SIGNED_OUT_CHECK = 2  # `nlm login --check` on a session that does not work


class NlmError(Exception):
    """`nlm` cannot be run, is signed out, or a command failed; `reason` is the CLI's code."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Artifact:
    """One Studio artifact."""

    id: str
    type: str
    title: str
    status: str
    created_at: dt.datetime | None = None


@dataclass(frozen=True)
class Note:
    """One note of the notebook."""

    id: str
    title: str


class Notebook(Protocol):
    """What `exam prep` asks of the notebook tool."""

    def check_session(self) -> None:
        """Raise unless the profile's session works."""
        ...

    def default_profile(self) -> str:
        """The default profile of nlm, the one `nlm download` reads."""
        ...

    def find_notebook(self, title: str) -> str | None:
        """The id of the notebook with exactly that title, or None."""
        ...

    def artifacts(self, notebook: str) -> list[Artifact]:
        """Every Studio artifact."""
        ...

    def create_report(self, notebook: str, report_format: str, language: str, prompt: str = "") -> str:
        """Start a report; its artifact id."""
        ...

    def rename(self, artifact: str, title: str) -> None:
        """Retitle an artifact."""
        ...

    def delete(self, notebook: str, artifact: str) -> None:
        """Delete an artifact."""
        ...

    def notes(self, notebook: str) -> list[Note]:
        """The notebook's notes."""
        ...

    def write_note(self, notebook: str, note: str | None, title: str, content: str) -> None:
        """Rewrite a note, or create it when `note` is None."""
        ...

    def read_source(self, source: str) -> None:
        """Read a source once, which makes the notebook take its file's latest content (spec 005 R14)."""
        ...


def _instant(value: object) -> dt.datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return dt.datetime.fromisoformat(value)
    except ValueError:
        return None


class NlmNotebook:
    """`Notebook` over the `nlm` command, with one profile."""

    def __init__(self, profile: str, runner: Runner = run_command) -> None:
        self._profile = profile
        self._run = runner

    def _call(self, *args: str, profiled: bool = True) -> str:
        argv = ["nlm", *args, *(("--profile", self._profile) if profiled else ())]
        try:
            done = self._run(argv, None)
        except FileNotFoundError:
            raise NlmError("no_nlm") from None
        if done.returncode != 0:
            signed_out = "nlm login" in done.stdout or "nlm login" in done.stderr
            raise NlmError("nlm_signed_out" if signed_out else "nlm_failed")
        return done.stdout

    def _json(self, *args: str) -> Any:
        try:
            return json.loads(self._call(*args, "--json"))
        except json.JSONDecodeError:
            raise NlmError("nlm_failed") from None

    def check_session(self) -> None:
        """`nlm login --check`: exit 2 is a session that does not work."""
        argv = ["nlm", "login", "--check", "--profile", self._profile]
        try:
            done = self._run(argv, None)
        except FileNotFoundError:
            raise NlmError("no_nlm") from None
        if done.returncode == SIGNED_OUT_CHECK and "Usage:" not in done.stderr:  # click's usage errors exit 2 too
            raise NlmError("nlm_signed_out")
        if done.returncode != 0:
            raise NlmError("nlm_failed")

    def default_profile(self) -> str:
        """`nlm config get auth.default_profile`."""
        return self._call("config", "get", "auth.default_profile", profiled=False).strip()

    def find_notebook(self, title: str) -> str | None:
        """By exact title, as `notebook setup` finds it."""
        try:
            return NlmSources(self._profile, self._run).find_notebook(title)
        except SourcesError as err:
            raise NlmError("nlm_signed_out" if err.signed_out else "nlm_failed") from None

    def artifacts(self, notebook: str) -> list[Artifact]:
        """`nlm studio status --full --json`."""
        listed = cast("list[dict[str, Any]]", self._json("studio", "status", notebook, "--full"))
        return [
            Artifact(
                str(a.get("id") or a.get("artifact_id") or ""),
                str(a.get("type") or ""),
                str(a.get("title") or ""),
                str(a.get("status") or ""),
                _instant(a.get("created_at")),
            )
            for a in listed
        ]

    def create_report(self, notebook: str, report_format: str, language: str, prompt: str = "") -> str:
        """`nlm report create … -y --json`, with the report's own `--language`."""
        args = ["report", "create", notebook, "--format", report_format, "--language", language]
        if prompt:
            args += ["--prompt", prompt]
        made = cast("dict[str, Any]", self._json(*args, "-y"))
        if not made.get("artifact_id"):
            raise NlmError("nlm_failed")
        return str(made["artifact_id"])

    def rename(self, artifact: str, title: str) -> None:
        """`nlm studio rename`."""
        self._call("studio", "rename", artifact, title)

    def delete(self, notebook: str, artifact: str) -> None:
        """`nlm studio delete … --confirm`."""
        self._call("studio", "delete", notebook, artifact, "--confirm")

    def notes(self, notebook: str) -> list[Note]:
        """`nlm note list --json`."""
        listed = cast("dict[str, Any]", self._json("note", "list", notebook))
        return [Note(str(n.get("id", "")), str(n.get("title", ""))) for n in listed.get("notes", [])]

    def write_note(self, notebook: str, note: str | None, title: str, content: str) -> None:
        """`nlm note update`, or `nlm note create` for a note not there yet."""
        if note is None:
            self._call("note", "create", notebook, "--title", title, "--content", content)
        else:
            self._call("note", "update", notebook, note, "--title", title, "--content", content)

    def read_source(self, source: str) -> None:
        """`nlm source content --json`; the content itself is not kept."""
        self._json("source", "content", source)
