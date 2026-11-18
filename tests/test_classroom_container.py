"""`DockerReadContainer` with a fake process runner (spec 006 T009; FR-028, SC-009)."""

from __future__ import annotations

import io
import json
import subprocess
from typing import TYPE_CHECKING, Any

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
