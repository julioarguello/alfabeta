"""The launchd agent of `classroom refresh`, with a fake `launchctl` (spec 006 T014; FR-015, research R11).

Every plist is written under `tmp_path`; no test writes to `~/Library`, runs `launchctl` or finds the
real `uv` and `docker`.
"""

from __future__ import annotations

import hashlib
import json
import plistlib
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import pytest

from alfabeta import __main__, config
from alfabeta.classroom import agent, cli
from alfabeta.classroom.agent import ClassroomAgent, ClassroomAgentSpec
from tests.conftest import CONFIG

STUDENT = "s9"
TIMES = {
    "monday": "16:15",
    "tuesday": "16:15",
    "wednesday": "15:15",
    "thursday": "",
    "friday": "16:15",
    "saturday": "",
    "sunday": "10:05",
}


@dataclass
class FakeLaunchctl:
    calls: list[tuple[str, str]] = field(default_factory=lambda: [])
    refuse: bool = False

    def bootstrap(self, plist: Path) -> bool:
        self.calls.append(("bootstrap", plist.name))
        return not self.refuse

    def bootout(self, job: str) -> bool:
        self.calls.append(("bootout", job))
        return True


def _bench(tmp_path: Path, tools: tuple[str, ...] = ("uv", "docker"), refuse: bool = False) -> ClassroomAgent:
    found = {"uv": "/opt/homebrew/bin/uv", "docker": "/usr/local/bin/docker"}
    return ClassroomAgent(
        tmp_path / "LaunchAgents",
        FakeLaunchctl(refuse=refuse),
        which=lambda name: found[name] if name in tools else None,
    )


def _spec(tmp_path: Path, times: dict[str, str] | None = None) -> ClassroomAgentSpec:
    repository = tmp_path / "alfabeta"
    repository.mkdir(exist_ok=True)
    return ClassroomAgentSpec(STUDENT, tmp_path / "home", repository, tmp_path / "data", times or TIMES)


def _plist(made: ClassroomAgent) -> dict[str, Any]:
    (path,) = list(made.agents_dir.glob("*.plist"))
    return plistlib.loads(path.read_bytes())


def test_the_plist_runs_refresh_at_each_schedule_time(tmp_path: Path) -> None:
    made = _bench(tmp_path)
    out = made.install(_spec(tmp_path))
    assert out == {"ok": True, "agent": "installed", "label": agent.label(STUDENT), "times": 5}
    job = _plist(made)
    assert job["ProgramArguments"][-4:] == ["classroom", "refresh", "--student", STUDENT]
    assert job["ProgramArguments"][:4] == ["/opt/homebrew/bin/uv", "run", "--project", str(tmp_path / "alfabeta")]
    assert job["EnvironmentVariables"]["ALFABETA_STARTED_BY"] == "schedule"
    assert job["EnvironmentVariables"]["PATH"].split(":")[:2] == ["/opt/homebrew/bin", "/usr/local/bin"]
    assert job["StartCalendarInterval"] == [
        {"Weekday": 1, "Hour": 16, "Minute": 15},
        {"Weekday": 2, "Hour": 16, "Minute": 15},
        {"Weekday": 3, "Hour": 15, "Minute": 15},
        {"Weekday": 5, "Hour": 16, "Minute": 15},
        {"Weekday": 0, "Hour": 10, "Minute": 5},
    ]
    assert "RunAtLoad" not in job  # a session that starts is not a scheduled time
    assert job["StandardOutPath"] == str(tmp_path / "data" / agent.LOG)
    assert cast("FakeLaunchctl", made.launchctl).calls == [("bootstrap", f"{agent.label(STUDENT)}.plist")]


def test_the_label_names_no_student() -> None:
    assert agent.label(STUDENT) == agent.LABEL_PREFIX + hashlib.sha256(STUDENT.encode()).hexdigest()[:12]
    assert STUDENT not in agent.label(STUDENT).removeprefix(agent.LABEL_PREFIX)


def test_an_unchanged_install_touches_nothing_and_a_change_reloads(tmp_path: Path) -> None:
    made = _bench(tmp_path)
    made.install(_spec(tmp_path))
    assert made.install(_spec(tmp_path))["agent"] == "unchanged"
    calls = cast("FakeLaunchctl", made.launchctl).calls
    assert len(calls) == 1
    made.install(_spec(tmp_path, TIMES | {"thursday": "17:00"}))
    assert [c[0] for c in calls] == ["bootstrap", "bootout", "bootstrap"]
    assert len(_plist(made)["StartCalendarInterval"]) == 6


def test_uninstall_removes_it_and_again_changes_nothing(tmp_path: Path) -> None:
    made = _bench(tmp_path)
    made.install(_spec(tmp_path))
    assert made.remove(STUDENT)["agent"] == "removed" and not list(made.agents_dir.glob("*.plist"))
    assert made.remove(STUDENT) == {"ok": True, "agent": "unchanged", "label": agent.label(STUDENT), "removed": False}


@pytest.mark.parametrize(
    ("bench", "times", "reason"),
    [
        ({}, dict.fromkeys(TIMES, ""), "invalid_config"),
        ({"tools": ("docker",)}, TIMES, "no_uv"),
        ({"tools": ("uv",)}, TIMES, "docker_unavailable"),
        ({"refuse": True}, TIMES, "launchctl_failed"),
    ],
)
def test_a_refused_install_leaves_nothing(
    tmp_path: Path, bench: dict[str, Any], times: dict[str, str], reason: str
) -> None:
    made = _bench(tmp_path, **bench)
    with pytest.raises(agent.AgentError) as raised:
        made.install(_spec(tmp_path, times))
    assert raised.value.reason == reason
    assert not made.agents_dir.exists() or not list(made.agents_dir.glob("*.plist"))


def test_install_needs_the_switch_on_and_uninstall_does_not(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    made = _bench(tmp_path)
    assert cli.cmd_agent("install", _spec(tmp_path), profile_read=False, agent=made) == 1
    assert json.loads(capsys.readouterr().out)["reason"] == "disabled"
    assert cli.cmd_agent("install", _spec(tmp_path), profile_read=True, agent=made) == 0
    capsys.readouterr()
    assert cli.cmd_agent("uninstall", _spec(tmp_path), profile_read=False, agent=made) == 0
    assert json.loads(capsys.readouterr().out)["removed"] is True


def _configured(tmp_path: Path, switch: str = "true", monday: str = "16:15") -> Path:
    home = tmp_path / "home"
    (home / STUDENT).mkdir(parents=True)
    (tmp_path / "repo").mkdir()
    schedule = "\n".join(f'{day} = "{monday if day == "monday" else ""}"' for day in TIMES)
    tables = f'\n[tools]\nfolder = "{tmp_path / "tools"}"\nrepository = "{tmp_path / "repo"}"\n'
    tables += f"\n[schedule]\n{schedule}\nwait_minutes = 60\n"
    tables += f'\n[downloads]\nfolder = "{tmp_path / "downloads"}"\n'
    tables += "\n[sync]\nfull_review_days = 7\nlock_idle_minutes = 30\nkept_captures = 10\n"
    text = CONFIG.replace("profile_read = false", f"profile_read = {switch}") + tables
    (home / STUDENT / "config.toml").write_text(text)
    return home


def test_the_cli_reads_the_schedule_and_never_touches_the_real_agents_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = _configured(tmp_path)
    made = _bench(tmp_path)
    monkeypatch.setattr(cli, "system_agent", lambda: made)
    argv = ["--home", str(home), "classroom", "agent"]
    assert __main__.main([*argv, "install", "--student", STUDENT]) == 0, capsys.readouterr()
    job = _plist(made)
    assert job["ProgramArguments"][-4:] == ["classroom", "refresh", "--student", STUDENT]
    assert job["StartCalendarInterval"] == [{"Weekday": 1, "Hour": 16, "Minute": 15}]
    assert __main__.main([*argv, "uninstall", "--student", STUDENT]) == 0
    assert not list(made.agents_dir.glob("*.plist"))


def test_uninstall_works_whatever_the_configuration_says(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = _configured(tmp_path)
    made = _bench(tmp_path)
    monkeypatch.setattr(cli, "system_agent", lambda: made)
    argv = ["--home", str(home), "classroom", "agent"]
    assert __main__.main([*argv, "install", "--student", STUDENT]) == 0
    config_file = home / STUDENT / "config.toml"
    config_file.write_text(config_file.read_text().replace('monday = "16:15"', 'monday = "25:00"'))
    assert __main__.main([*argv, "install", "--student", STUDENT]) == 1  # install refuses it now
    assert list(made.agents_dir.glob("*.plist"))
    shutil.rmtree(home / STUDENT)  # even with the student's folder gone
    assert __main__.main([*argv, "uninstall", "--student", STUDENT]) == 0
    assert not list(made.agents_dir.glob("*.plist"))


def test_every_day_maps_to_its_launchd_weekday() -> None:
    every = {day: f"0{i}:3{i}" for i, day in enumerate(agent.WEEKDAYS)}
    entries = agent.calendar(every)
    assert [(e["Weekday"], e["Hour"], e["Minute"]) for e in entries] == [
        (1, 0, 30),
        (2, 1, 31),
        (3, 2, 32),
        (4, 3, 33),
        (5, 4, 34),
        (6, 5, 35),
        (0, 6, 36),
    ]


def test_no_repository_is_refused(tmp_path: Path) -> None:
    spec = ClassroomAgentSpec(STUDENT, tmp_path / "home", tmp_path / "missing", tmp_path / "data", TIMES)
    with pytest.raises(agent.AgentError) as raised:
        _bench(tmp_path).install(spec)
    assert raised.value.reason == "no_repository"


def test_refresh_reads_the_schedule_only_when_the_agent_started_it(tmp_path: Path) -> None:
    home = _configured(tmp_path)
    scheduled = __main__._refresh_config(home, STUDENT, "schedule")
    assert scheduled.times["monday"] == "16:15" and scheduled.wait_minutes == 60
    config_file = home / STUDENT / "config.toml"
    config_file.write_text(config_file.read_text().replace('monday = "16:15"', 'monday = "changeme"'))
    by_hand = __main__._refresh_config(home, STUDENT, "command")  # a template value left: no invalid_config
    assert by_hand.times == {} and by_hand.wait_minutes == 0
    with pytest.raises(config.ConfigError):
        __main__._refresh_config(home, STUDENT, "schedule")


def test_a_schedule_time_that_is_not_hh_mm_is_named(tmp_path: Path) -> None:
    home = _configured(tmp_path, monday="25:00")
    with pytest.raises(config.ConfigError, match=r"schedule\.monday"):
        _ = config.load(home, STUDENT, ("schedule",)).schedule_times
