"""`DockerReadContainer` with a fake process runner (spec 006 T009; FR-028, SC-009)."""

from __future__ import annotations

import io
import json
import subprocess
import threading
from typing import TYPE_CHECKING, Any

import pytest

from alfabeta.classroom import container

if TYPE_CHECKING:
    from pathlib import Path

PASSWORD = "contraseña-inventada-123"
ACCOUNT = "alumno@example.test"


class Ran:
    def __init__(self, codes: dict[str, int]) -> None:
        self.codes = codes
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        self.calls.append(argv)
        return subprocess.CompletedProcess(
            argv, self.codes.get(argv[1] + (" " + argv[2] if argv[1] == "image" else ""), 0), "", ""
        )


class FakePopen:
    def __init__(self, lines: list[dict[str, Any]]) -> None:
        self.stdin = io.StringIO()
        self.stdout = io.StringIO("".join(json.dumps(line) + "\n" for line in lines))
        self.written = ""
        self.closed_stdin = False
        original_close = self.stdin.close

        def close() -> None:
            self.written = self.stdin.getvalue()
            self.closed_stdin = True
            original_close()

        self.stdin.close = close  # type: ignore[method-assign]

    def wait(self, timeout: int) -> int:
        return 0

    def kill(self) -> None:
        pass


def test_run_puts_the_request_on_stdin_once_and_nowhere_else(tmp_path: Path) -> None:
    started: list[list[str]] = []
    popen = FakePopen(
        [
            {"event": "browser"},
            {"event": "class", "id": "x"},
            {"event": "end", "outcome": "ok", "classes": {"read": 1, "failed": 0}},
        ]
    )

    def streaming(argv: list[str]) -> Any:
        started.append(argv)
        return popen

    events: list[dict[str, Any]] = []
    reader = container.DockerReadContainer(process=Ran({}), streaming=streaming)
    request = {"run": "r1", "account": ACCOUNT, "password": PASSWORD, "signin": True}
    end = reader.run("img:tag", request, tmp_path / "profile", tmp_path / "out", events.append)
    assert end["outcome"] == "ok" and [e["event"] for e in events] == ["browser", "class"]
    argv = started[0]
    assert argv[:4] == ["docker", "run", "--rm", "-i"]
    assert argv[argv.index("--name") + 1] == container.container_name("r1")
    assert not any(a in ("-e", "--env", "--env-file") or a.startswith("--env") for a in argv)
    assert all(PASSWORD not in a and ACCOUNT not in a for a in argv)
    assert popen.closed_stdin and json.loads(popen.written) == request and popen.written.count(PASSWORD) == 1
    assert (tmp_path / "profile").stat().st_mode & 0o777 == 0o700 and (tmp_path / "out").stat().st_mode & 0o777 == 0o700


def test_the_image_is_built_only_when_its_hash_is_missing(tmp_path: Path) -> None:
    present = Ran({})
    image = container.DockerReadContainer(process=present).ensure_image()
    assert image == f"{container.IMAGE}:{container.inputs_hash()}"
    assert [c[1] for c in present.calls] == ["image"]
    missing = Ran({"image inspect": 1})
    container.DockerReadContainer(process=missing).ensure_image()
    build = missing.calls[-1]
    assert build[:2] == ["docker", "build"] and "--build-arg" not in build
    assert build[build.index("-t") + 1] == image and build[-1] == str(container.REPO)


def test_a_failed_build_is_a_container_error() -> None:
    failing = Ran({"image inspect": 1, "build": 1})
    try:
        container.DockerReadContainer(process=failing).ensure_image()
    except container.ContainerError:
        return
    raise AssertionError("a failed build must raise ContainerError")


def test_docker_not_answering_is_unavailable() -> None:
    assert container.DockerReadContainer(process=Ran({"info": 1})).available() is False
    assert container.DockerReadContainer(process=Ran({})).available() is True


def test_the_hash_follows_every_input(tmp_path: Path) -> None:
    files: list[Path] = []
    for name in ("Dockerfile", "read.py"):
        path = tmp_path / name
        path.write_text(name)
        files.append(path)
    before = container.inputs_hash(tuple(files))
    files[1].write_text("changed")
    assert container.inputs_hash(tuple(files)) != before


class HungPopen(FakePopen):
    """A container that never ends until it is killed."""

    def __init__(self, before: list[dict[str, Any]] | None = None) -> None:
        super().__init__([])
        self.killed = threading.Event()

        def lines() -> Any:
            yield from (json.dumps(event) + "\n" for event in before or [])
            self.killed.wait(5)

        self.stdout = _Lazy(lines)

    def kill(self) -> None:
        self.killed.set()


class _Lazy:
    def __init__(self, make: Any) -> None:
        self.make = make

    def __iter__(self) -> Any:
        return self.make()


def test_a_hung_read_is_killed_by_name_and_ends_in_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(container, "RUN_TIMEOUT_SECONDS", 0.05)
    process = Ran({})
    popen = HungPopen()
    reader = container.DockerReadContainer(process=process, streaming=lambda argv: popen)  # type: ignore[arg-type,return-value]
    end = reader.run("img:tag", {"run": "r2", "password": PASSWORD}, tmp_path / "p", tmp_path / "o", lambda e: None)
    assert end["reason"] == "timeout" and end["outcome"] == "stopped"
    assert ["docker", "kill", container.container_name("r2")] in process.calls and popen.killed.is_set()


def test_a_container_that_cannot_take_the_request_is_a_container_error(tmp_path: Path) -> None:
    popen = FakePopen([])

    def broken(_: str) -> int:
        raise BrokenPipeError

    popen.stdin.write = broken  # type: ignore[method-assign]
    process = Ran({})
    reader = container.DockerReadContainer(process=process, streaming=lambda argv: popen)  # type: ignore[arg-type,return-value]
    with pytest.raises(container.ContainerError):
        reader.run("img:tag", {"run": "r3", "password": PASSWORD}, tmp_path / "p", tmp_path / "o", lambda e: None)
    assert ["docker", "kill", container.container_name("r3")] in process.calls


def test_a_read_killed_midway_keeps_the_classes_it_had_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(container, "RUN_TIMEOUT_SECONDS", 0.05)
    popen = HungPopen(
        [
            {"event": "class", "id": "a", "type": "class", "complete": True},
            {"event": "class", "id": "b", "type": "class", "complete": True},
            {"event": "class", "id": "c", "type": "stop", "reason": "unexpected_ui"},
        ]
    )
    reader = container.DockerReadContainer(process=Ran({}), streaming=lambda argv: popen)  # type: ignore[arg-type,return-value]
    end = reader.run("img:tag", {"run": "r4"}, tmp_path / "p", tmp_path / "o", lambda e: None)
    assert end == {"event": "end", "outcome": "partial", "reason": "timeout", "classes": {"read": 2, "failed": 1}}


def test_a_genuine_end_is_never_relabelled(tmp_path: Path) -> None:
    stop = {"event": "end", "outcome": "stopped", "reason": "challenge", "classes": {"read": 0, "failed": 0}}
    popen = FakePopen([{"event": "class", "id": "a", "type": "class"}, stop])
    reader = container.DockerReadContainer(process=Ran({}), streaming=lambda argv: popen)  # type: ignore[arg-type,return-value]
    assert reader.run("img:tag", {"run": "r5"}, tmp_path / "p", tmp_path / "o", lambda e: None) == stop
