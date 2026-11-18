"""The launchd agent that runs `classroom refresh` at the `[schedule]` times (spec 006 FR-015, R11). Mac only.

A LaunchAgent of the family's user session, as spec 005's `notebook agent` (`notes/agent.py`, whose
`Launchctl` port it reuses): one `StartCalendarInterval` entry per weekday time of `[schedule]`. A
Mac asleep at a time runs that entry when it wakes (`man launchd.plist`); `classroom refresh`, told
by `ALFABETA_STARTED_BY=schedule` that the agent started it, ends `skipped`/`outside_hours` when
that is more than `[schedule] wait_minutes` after the time (FR-015: a missed time is not made up).
No `RunAtLoad`: a session that starts is not a scheduled time. launchd's `PATH` is only the
system's, so `uv` and `docker` are found at install and their folders written into the agent's own.

The label is `io.alfabeta.classroom-refresh.` and the first 12 hex digits of the SHA-256 of the
student id: it carries neither the id nor a name. The job's arguments and log path carry the id,
never a name, an account or a password. The launcher of FR-016 is not built (amendment of
2026-11-17): the family starts a read by hand with `classroom refresh`.
"""

from __future__ import annotations

import hashlib
import plistlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from alfabeta.notes.agent import SYSTEM_PATH, AgentError, Launchctl, SystemLaunchctl
from alfabeta.state import write_atomic

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

LABEL_PREFIX = "io.alfabeta.classroom-refresh."
LOG = "classroom-agent.log"
STARTED_BY = "schedule"
# `[schedule]`'s days and launchd's `Weekday` (0 and 7 are Sunday).
WEEKDAYS = {
    "monday": 1,
    "tuesday": 2,
    "wednesday": 3,
    "thursday": 4,
    "friday": 5,
    "saturday": 6,
    "sunday": 0,
}


@dataclass(frozen=True)
class ClassroomAgentSpec:
    """What one student's agent runs, when, and where it logs."""

    student: str
    home: Path  # the `--home` the read runs with
    repository: Path  # `[tools] repository`, the clone `uv run --project` runs
    data_dir: Path  # the student's data folder: the log goes there
    times: Mapping[str, str]  # `[schedule]`: day → "HH:MM", or "" for none that day


def label(student: str) -> str:
    """The job's label: no id, no name."""
    return LABEL_PREFIX + hashlib.sha256(student.encode()).hexdigest()[:12]


def calendar(times: Mapping[str, str]) -> list[dict[str, int]]:
    """One `StartCalendarInterval` entry per weekday time; none at all is `invalid_config`."""
    entries: list[dict[str, int]] = []
    for day, weekday in WEEKDAYS.items():
        value = times.get(day, "")
        if value:
            hour, minute = value.split(":")
            entries.append({"Weekday": weekday, "Hour": int(hour), "Minute": int(minute)})
    if not entries:
        raise AgentError("invalid_config")
    return entries


def render(spec: ClassroomAgentSpec, uv: Path, docker: Path) -> str:
    """The plist, as XML."""
    folders = list(dict.fromkeys(str(tool.parent) for tool in (uv, docker)))
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
            "classroom",
            "refresh",
            "--student",
            spec.student,
        ],
        "EnvironmentVariables": {"PATH": ":".join([*folders, *SYSTEM_PATH]), "ALFABETA_STARTED_BY": STARTED_BY},
        "StartCalendarInterval": calendar(spec.times),
        "StandardOutPath": log,
        "StandardErrorPath": log,
    }
    return plistlib.dumps(job, sort_keys=True).decode()


@dataclass(frozen=True)
class ClassroomAgent:
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

    def install(self, spec: ClassroomAgentSpec) -> dict[str, Any]:
        """Write the plist and load it; rewrite only when it changes."""
        times = len(calendar(spec.times))
        uv = self._tool("uv", "no_uv")
        docker = self._tool("docker", "docker_unavailable")
        if not spec.repository.is_dir():
            raise AgentError("no_repository")
        path, text = self._plist(spec.student), render(spec, uv, docker)
        job = label(spec.student)
        if path.is_file() and path.read_text() == text:
            return {"ok": True, "agent": "unchanged", "label": job, "times": times}
        if path.is_file():
            self.launchctl.bootout(job)  # not loaded is fine: the new one replaces it
        spec.data_dir.mkdir(parents=True, exist_ok=True)  # launchd appends the log, it makes no folder
        write_atomic(path, text)
        if not self.launchctl.bootstrap(path):
            path.unlink()
            raise AgentError("launchctl_failed")
        return {"ok": True, "agent": "installed", "label": job, "times": times}

    def remove(self, student: str) -> dict[str, Any]:
        """Unload and delete the plist; with none there, nothing changes."""
        path, job = self._plist(student), label(student)
        if not path.is_file():
            return {"ok": True, "agent": "unchanged", "label": job, "removed": False}
        self.launchctl.bootout(job)
        path.unlink()
        return {"ok": True, "agent": "removed", "label": job, "removed": True}


def system_agent() -> ClassroomAgent:
    """The family's own: `~/Library/LaunchAgents` and the real `launchctl`. Only the CLI builds it."""
    return ClassroomAgent(Path.home() / "Library" / "LaunchAgents", SystemLaunchctl())
