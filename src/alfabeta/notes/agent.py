"""The launchd agent that runs `notebook refresh` with no app open (spec 005 FR-018, research R14, T046). Mac only.

A LaunchAgent of the family's user session: `StartCalendarInterval` entries every `[notebook]
refresh_minutes`, so a Mac that slept runs one pass when it wakes (`man launchd.plist`, read
2026-10-28), and `RunAtLoad`, so one runs when the session starts. launchd's `PATH` is only the
system's, so `uv` and `nlm` are found at install and their folders written into the agent's own.

The label is `io.alfabeta.notebook-refresh.` and the first 12 hex digits of the SHA-256 of the student
id: it carries neither the id nor a name. The job's arguments and log path, which `launchctl print`
shows, carry the id, never a name. The agent never passes `--browser`: unattended, the refresh renews
the owner's session only through `nlm auth refresh --http-only`.

`LaunchdAgent` writes only into the folder it is given and loads only through the `Launchctl` it is
given; `system_agent` is the family's `~/Library/LaunchAgents` and the real `launchctl`.
"""

from __future__ import annotations

import hashlib
import os
import plistlib
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from alfabeta.google.keychain import run_command
from alfabeta.state import write_atomic

if TYPE_CHECKING:
    from collections.abc import Callable

    from alfabeta.google.keychain import Runner

LABEL_PREFIX = "io.alfabeta.notebook-refresh."
LOG = "notebook-agent.log"
SYSTEM_PATH = ("/usr/bin", "/bin", "/usr/sbin", "/sbin")  # launchd's own, after the tools' folders
_HOUR = 60


class AgentError(Exception):
    """The agent is not installed; `reason` is the CLI's code (all exit 1)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class Launchctl(Protocol):
    """Loading and unloading a job in the user's GUI domain."""

    def bootstrap(self, plist: Path) -> bool:
        """Load the job; True if launchd took it."""
        ...

    def bootout(self, job: str) -> bool:
        """Unload the job by label; False also when it was not loaded."""
        ...


@dataclass(frozen=True)
class SystemLaunchctl:
    """`Launchctl` over `launchctl bootstrap|bootout gui/<uid>`."""

    run: Runner = run_command
    uid: int = field(default_factory=os.getuid)

    def bootstrap(self, plist: Path) -> bool:
        """`launchctl bootstrap gui/<uid> <plist>`."""
        return self.run(["launchctl", "bootstrap", f"gui/{self.uid}", str(plist)], None).returncode == 0

    def bootout(self, job: str) -> bool:
        """`launchctl bootout gui/<uid>/<label>`."""
        return self.run(["launchctl", "bootout", f"gui/{self.uid}/{job}"], None).returncode == 0


@dataclass(frozen=True)
class AgentSpec:
    """What one student's agent runs, and where it logs."""

    student: str
    home: Path  # the `--home` the pass runs with
    repository: Path  # `[tools] repository`, the clone `uv run --project` runs
    data_dir: Path  # the student's data folder: the log goes there
    refresh_minutes: int


def label(student: str) -> str:
    """The job's label: no id, no name."""
    return LABEL_PREFIX + hashlib.sha256(student.encode()).hexdigest()[:12]


def schedule(minutes: int) -> list[dict[str, int]]:
    """One `StartCalendarInterval` entry every `minutes`, which must divide an hour."""
    if not 0 < minutes <= _HOUR or _HOUR % minutes:
        raise AgentError("invalid_refresh_minutes")
    return [{"Minute": minute} for minute in range(0, _HOUR, minutes)]


def render(spec: AgentSpec, uv: Path, nlm: Path) -> str:
    """The plist, as XML."""
    folders = list(dict.fromkeys(str(tool.parent) for tool in (uv, nlm)))
    log = str(spec.data_dir / LOG)
    job: dict[str, Any] = {
        "Label": label(spec.student),
        "ProgramArguments": [
            str(uv),
            "run",
            "--project",
            str(spec.repository),
            "python",
            "-m",
            "alfabeta",
            "--home",
            str(spec.home),
            "notebook",
            "refresh",
            "--student",
            spec.student,
        ],
        "EnvironmentVariables": {"PATH": ":".join([*folders, *SYSTEM_PATH])},
        "StartCalendarInterval": schedule(spec.refresh_minutes),
        "RunAtLoad": True,
        "StandardOutPath": log,
        "StandardErrorPath": log,
    }
    return plistlib.dumps(job, sort_keys=True).decode()


@dataclass(frozen=True)
class LaunchdAgent:
    """Install and remove one student's agent, in `agents_dir` only."""

    agents_dir: Path
    launchctl: Launchctl
    which: Callable[[str], str | None] = shutil.which

    def _plist(self, student: str) -> Path:
        return self.agents_dir / f"{label(student)}.plist"

    def _tool(self, name: str, reason: str) -> Path:
        found = self.which(name)
        if not found:
            raise AgentError(reason)
        return Path(found).absolute()  # not resolved: a symlink of a package manager survives its upgrades

    def install(self, spec: AgentSpec) -> dict[str, Any]:
        """Write the plist and load it; rewrite only when it changes (contracts/cli.md)."""
        schedule(spec.refresh_minutes)
        nlm = self._tool("nlm", "no_nlm")
        uv = self._tool("uv", "no_uv")
        if not spec.repository.is_dir():
            raise AgentError("no_repository")
        path, text = self._plist(spec.student), render(spec, uv, nlm)
        job = label(spec.student)
        if path.is_file() and path.read_text() == text:
            return {"ok": True, "agent": "unchanged", "label": job}
        if path.is_file():
            self.launchctl.bootout(job)  # not loaded is fine: the new one replaces it
        spec.data_dir.mkdir(parents=True, exist_ok=True)  # launchd appends the log, it makes no folder
        write_atomic(path, text)
        if not self.launchctl.bootstrap(path):
            path.unlink()
            raise AgentError("launchctl_failed")
        return {"ok": True, "agent": "installed", "label": job}

    def remove(self, student: str) -> dict[str, Any]:
        """Unload and delete the plist; with none there, nothing changes."""
        path, job = self._plist(student), label(student)
        if not path.is_file():
            return {"ok": True, "agent": "unchanged", "label": job}
        self.launchctl.bootout(job)
        path.unlink()
        return {"ok": True, "agent": "removed", "label": job}


def system_agent() -> LaunchdAgent:
    """The family's own: `~/Library/LaunchAgents` and the real `launchctl`. Only the CLI builds it."""
    return LaunchdAgent(Path.home() / "Library" / "LaunchAgents", SystemLaunchctl())
