"""The launchd agent of the owner's refresh, with a fake `launchctl` (spec 005 T046, research R14).

Every plist is written under `tmp_path`; no test writes to `~/Library`, runs `launchctl` or finds the real
`uv` and `nlm`.
"""

from __future__ import annotations

import hashlib
import json
import plistlib
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from alfabeta import __main__, config
from alfabeta.notes import cli
from alfabeta.notes.agent import (
    LABEL_PREFIX,
    LOG,
    SYSTEM_PATH,
    AgentError,
    AgentSpec,
    LaunchdAgent,
    SystemLaunchctl,
    label,
    schedule,
)
from tests.conftest import CONFIG
from tests.test_notes_cli import NOTES_TABLES


@dataclass
class FakeLaunchctl:
    """Records what would be loaded and unloaded; `refuse` makes bootstrap fail."""

    calls: list[tuple[str, str]] = field(default_factory=lambda: [])
    refuse: bool = False

    def bootstrap(self, plist: Path) -> bool:
        self.calls.append(("bootstrap", plist.name))
        return not self.refuse

    def bootout(self, job: str) -> bool:
        self.calls.append(("bootout", job))
        return True


@dataclass
class Bench:
    """A Mac in `tmp_path`: tools found where the bench puts them, and the agents folder it names."""

    root: Path
    launchctl: FakeLaunchctl = field(default_factory=FakeLaunchctl)
    tools: dict[str, str] = field(default_factory=lambda: {})

    def __post_init__(self) -> None:
        for name, where in (("uv", "bin"), ("nlm", "tools/bin")):
            path = self.root / where / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("")
            self.tools[name] = str(path)
        (self.root / "repo").mkdir(exist_ok=True)

    @property
    def agents(self) -> Path:
        return self.root / "LaunchAgents"

    def agent(self) -> LaunchdAgent:
        return LaunchdAgent(self.agents, self.launchctl, self.tools.get)

    def spec(self, minutes: int = 15) -> AgentSpec:
        return AgentSpec("s9", self.root / "home", self.root / "repo", self.root / "home" / "s9" / "data", minutes)

    def plist(self) -> dict[str, Any]:
        [path] = self.agents.iterdir()
        return plistlib.loads(path.read_bytes())


@pytest.fixture
def bench(tmp_path: Path) -> Bench:
    return Bench(tmp_path)


def test_the_label_carries_neither_the_id_nor_a_name():
    made = label("s9")
    assert made == LABEL_PREFIX + hashlib.sha256(b"s9").hexdigest()[:12]
    assert made.removeprefix(LABEL_PREFIX) != "s9" and len(made.removeprefix(LABEL_PREFIX)) == 12


def test_the_plist_runs_the_refresh_through_uv_with_what_install_resolved(bench: Bench):
    bench.agent().install(bench.spec())
    plist = bench.plist()
    root = bench.root
    assert plist["Label"] == label("s9")
    assert plist["ProgramArguments"] == [
        bench.tools["uv"],
        "run",
        "--project",
        str(root / "repo"),
        "python",
        "-m",
        "alfabeta",
        "--home",
        str(root / "home"),
        "notebook",
        "refresh",
        "--student",
        "s9",
    ]
    assert "--browser" not in plist["ProgramArguments"]  # unattended: never the renewal through a browser
    path = plist["EnvironmentVariables"]["PATH"].split(":")
    assert path == [str(root / "bin"), str(root / "tools" / "bin"), *SYSTEM_PATH]
    assert plist["RunAtLoad"] is True
    assert plist["StandardOutPath"] == plist["StandardErrorPath"] == str(root / "home" / "s9" / "data" / LOG)
    assert plist["StartCalendarInterval"] == [{"Minute": 0}, {"Minute": 15}, {"Minute": 30}, {"Minute": 45}]


def test_one_directory_holding_uv_and_nlm_is_on_the_path_once(bench: Bench):
    bench.tools["nlm"] = str(bench.root / "bin" / "nlm")
    bench.agent().install(bench.spec())
    assert bench.plist()["EnvironmentVariables"]["PATH"].split(":") == [str(bench.root / "bin"), *SYSTEM_PATH]


@pytest.mark.parametrize(("minutes", "entries"), [(60, [0]), (30, [0, 30]), (20, [0, 20, 40]), (1, list(range(60)))])
def test_one_entry_every_refresh_minutes(minutes: int, entries: list[int]):
    assert schedule(minutes) == [{"Minute": m} for m in entries]


@pytest.mark.parametrize("minutes", [0, -15, 7, 45, 90, 120])
def test_a_value_that_does_not_divide_60_is_refused(bench: Bench, minutes: int):
    with pytest.raises(AgentError) as err:
        bench.agent().install(bench.spec(minutes))
    assert err.value.reason == "invalid_refresh_minutes"
    assert not bench.agents.exists() and bench.launchctl.calls == []


@pytest.mark.parametrize(("tool", "reason"), [("nlm", "no_nlm"), ("uv", "no_uv")])
def test_a_tool_not_found_refuses_to_install(bench: Bench, tool: str, reason: str):
    del bench.tools[tool]
    with pytest.raises(AgentError) as err:
        bench.agent().install(bench.spec())
    assert err.value.reason == reason
    assert not bench.agents.exists() and bench.launchctl.calls == []


def test_a_repository_that_is_not_there_refuses_to_install(bench: Bench):
    (bench.root / "repo").rmdir()
    with pytest.raises(AgentError) as err:
        bench.agent().install(bench.spec())
    assert err.value.reason == "no_repository"


def test_install_writes_only_into_the_folder_it_is_given_and_loads_it(bench: Bench):
    out = bench.agent().install(bench.spec())
    assert out == {"ok": True, "agent": "installed", "label": label("s9")}
    assert [p.name for p in bench.agents.iterdir()] == [f"{label('s9')}.plist"]
    assert bench.launchctl.calls == [("bootstrap", f"{label('s9')}.plist")]
    assert (bench.root / "home" / "s9" / "data").is_dir()  # launchd appends the log there


def test_installing_again_unchanged_touches_nothing(bench: Bench):
    bench.agent().install(bench.spec())
    [path] = bench.agents.iterdir()
    stamp = path.stat().st_mtime_ns
    bench.launchctl.calls.clear()
    assert bench.agent().install(bench.spec())["agent"] == "unchanged"
    assert bench.launchctl.calls == [] and path.stat().st_mtime_ns == stamp


def test_installing_a_changed_agent_unloads_rewrites_and_loads_it(bench: Bench):
    bench.agent().install(bench.spec(15))
    bench.launchctl.calls.clear()
    assert bench.agent().install(bench.spec(30))["agent"] == "installed"
    assert bench.launchctl.calls == [("bootout", label("s9")), ("bootstrap", f"{label('s9')}.plist")]
    assert bench.plist()["StartCalendarInterval"] == [{"Minute": 0}, {"Minute": 30}]


def test_an_agent_launchd_refuses_is_not_left_behind(bench: Bench):
    bench.launchctl.refuse = True
    with pytest.raises(AgentError) as err:
        bench.agent().install(bench.spec())
    assert err.value.reason == "launchctl_failed"
    assert list(bench.agents.iterdir()) == []


def test_remove_unloads_and_deletes_and_a_second_remove_changes_nothing(bench: Bench):
    bench.agent().install(bench.spec())
    bench.launchctl.calls.clear()
    assert bench.agent().remove("s9") == {"ok": True, "agent": "removed", "label": label("s9")}
    assert bench.launchctl.calls == [("bootout", label("s9"))] and list(bench.agents.iterdir()) == []
    bench.launchctl.calls.clear()
    assert bench.agent().remove("s9")["agent"] == "unchanged" and bench.launchctl.calls == []


def test_launchctl_is_asked_in_the_users_gui_domain():
    seen: list[list[str]] = []

    def runner(argv: list[str], stdin: str | None) -> subprocess.CompletedProcess[str]:
        seen.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    ctl = SystemLaunchctl(runner, uid=501)
    assert ctl.bootstrap(Path("/tmp/agente.plist")) and ctl.bootout("io.alfabeta.notebook-refresh.abc")
    assert seen == [
        ["launchctl", "bootstrap", "gui/501", "/tmp/agente.plist"],
        ["launchctl", "bootout", "gui/501/io.alfabeta.notebook-refresh.abc"],
    ]


# --- the command ---------------------------------------------------------------------------------


@pytest.fixture
def home(tmp_path: Path) -> Path:
    (tmp_path / "home" / "s9").mkdir(parents=True)
    (tmp_path / "repo").mkdir(exist_ok=True)  # the bench may have made it
    tools = f'\n[tools]\nfolder = "{tmp_path / "tools"}"\nrepository = "{tmp_path / "repo"}"\n'
    (tmp_path / "home" / "s9" / "config.toml").write_text(CONFIG + NOTES_TABLES + tools)
    return tmp_path / "home"


def printed(capsys: pytest.CaptureFixture[str]) -> tuple[dict[str, Any], str]:
    captured = capsys.readouterr()
    return json.loads(captured.out.strip().splitlines()[-1]), captured.err


def test_the_agent_command_prints_its_state_and_no_path(
    home: Path, bench: Bench, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.setattr(cli, "system_agent", bench.agent)  # never ~/Library, never launchctl
    assert __main__.main(["--home", str(home), "notebook", "agent", "install", "--student", "s9"]) == 0
    out, err = printed(capsys)
    assert out == {"ok": True, "agent": "installed", "label": label("s9")}
    assert str(bench.root) not in json.dumps(out) + err
    plist = bench.plist()
    assert plist["ProgramArguments"][plist["ProgramArguments"].index("--home") + 1] == str(home.resolve())
    assert plist["StandardOutPath"] == str((home / "s9" / "data").resolve() / LOG)
    assert __main__.main(["--home", str(home), "notebook", "agent", "remove", "--student", "s9"]) == 0
    assert printed(capsys)[0]["agent"] == "removed"


def test_the_agent_command_refuses_without_nlm(
    home: Path, bench: Bench, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    del bench.tools["nlm"]
    monkeypatch.setattr(cli, "system_agent", bench.agent)
    assert __main__.main(["--home", str(home), "notebook", "agent", "install", "--student", "s9"]) == 1
    assert printed(capsys)[0] == {"ok": False, "reason": "no_nlm"}


def test_refresh_is_wired_with_its_flag(home: Path, monkeypatch: pytest.MonkeyPatch):
    seen: list[bool] = []

    def fake(cfg: config.StudentConfig, store: object, *, browser: bool = False) -> int:
        seen.append(browser)
        return 0

    monkeypatch.setattr(cli, "cmd_notebook_refresh", fake)
    assert __main__.main(["--home", str(home), "notebook", "refresh", "--student", "s9"]) == 0
    assert __main__.main(["--home", str(home), "notebook", "refresh", "--student", "s9", "--browser"]) == 0
    assert seen == [False, True]


def test_the_agent_reads_refresh_minutes_and_the_repository(home: Path):
    cfg = config.load(home, "s9", __main__.AGENT_TABLES)
    assert cfg.notebook_refresh_minutes == 15
    assert cfg.tools_repository == home.parent / "repo"
