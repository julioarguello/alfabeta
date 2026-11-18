"""The read container (spec 006 FR-028, data-model «Read container»): Docker, behind a port.

`DockerReadContainer` builds the image from the repository root when its inputs change (the tag is
their hash), and runs it with `docker run --rm -i`: the read profile and an out folder mounted, the
request written once on stdin and closed. The account and the password never appear in an argument,
an environment variable, the image or a file; stdout is read line by line as JSON events. The
container is named after the run, so a watchdog can `docker kill` it when the read outlives
RUN_TIMEOUT_SECONDS (killing the docker client alone would leave the container running).
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import subprocess
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable

REPO = Path(__file__).resolve().parents[3]
DOCKERFILE = REPO / "docker" / "classroom" / "Dockerfile"
INPUTS = (
    DOCKERFILE,
    REPO / "docker" / "classroom" / "Dockerfile.dockerignore",
    REPO / "docker" / "classroom" / "read.py",
    REPO / "skills" / "classroom-sync" / "scripts" / "extract.js",
)
IMAGE = "alfabeta-classroom-read"
PLATFORM = "linux/amd64"
# A whole read took 14 min 20 s under emulation (research S14); a build of the image a few minutes.
RUN_TIMEOUT_SECONDS = 45 * 60
BUILD_TIMEOUT_SECONDS = 30 * 60
INFO_TIMEOUT_SECONDS = 20


class ContainerError(Exception):
    """Docker is not running, or the image cannot be built (`docker_unavailable`)."""


class ReadContainer(Protocol):
    """What `classroom refresh` needs from the container."""

    def available(self) -> bool:
        """Whether Docker answers."""
        ...

    def ensure_image(self) -> str:
        """The image to run, built if its inputs changed; ContainerError if it cannot be."""
        ...

    def run(
        self, image: str, request: dict[str, Any], profile: Path, out: Path, on_event: Callable[[dict[str, Any]], None]
    ) -> dict[str, Any]:
        """Run one read; returns its `end` event."""
        ...


class Process(Protocol):
    """Runs one command to completion; the seam the tests replace."""

    def __call__(self, argv: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        """Run it."""
        ...


class Streaming(Protocol):
    """Starts a command with a pipe on stdin and stdout; the seam the tests replace."""

    def __call__(self, argv: list[str]) -> subprocess.Popen[str]:
        """Start it."""
        ...


def run_process(argv: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    """Run a command and capture its output."""
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)


def start_process(argv: list[str]) -> subprocess.Popen[str]:
    """Start a command with stdin and stdout piped, stderr discarded (it is Chrome's chatter)."""
    return subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)


def inputs_hash(paths: tuple[Path, ...] = INPUTS) -> str:
    """The image's tag: a hash of the files it is built from."""
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()[:16]


def container_name(run: str) -> str:
    """The container's name: the run id, which is no secret."""
    return f"{IMAGE}-{run}"


def run_argv(image: str, profile: Path, out: Path, name: str) -> list[str]:
    """`docker run` for one read: no `-e`, no secret; the profile and out folder mounted."""
    return [
        "docker",
        "run",
        "--rm",
        "-i",
        "--name",
        name,
        "--platform",
        PLATFORM,
        "-v",
        f"{profile}:/profile",
        "-v",
        f"{out}:/out",
        image,
    ]


class DockerReadContainer:
    """`ReadContainer` over the Docker command line."""

    def __init__(self, process: Process = run_process, streaming: Streaming = start_process) -> None:
        self._process = process
        self._streaming = streaming

    def available(self) -> bool:
        """`docker info` answers."""
        try:
            return (
                self._process(["docker", "info", "--format", "{{.ServerVersion}}"], INFO_TIMEOUT_SECONDS).returncode
                == 0
            )
        except (OSError, subprocess.TimeoutExpired):
            return False

    def ensure_image(self) -> str:
        """Build the image under its inputs' hash unless it is there already."""
        image = f"{IMAGE}:{inputs_hash()}"
        try:
            if self._process(["docker", "image", "inspect", image], INFO_TIMEOUT_SECONDS).returncode == 0:
                return image
            built = self._process(
                ["docker", "build", "--platform", PLATFORM, "-f", str(DOCKERFILE), "-t", image, str(REPO)],
                BUILD_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired) as err:
            raise ContainerError("the read's image could not be built") from err
        if built.returncode != 0:
            raise ContainerError("the read's image could not be built")
        return image

    def run(
        self, image: str, request: dict[str, Any], profile: Path, out: Path, on_event: Callable[[dict[str, Any]], None]
    ) -> dict[str, Any]:
        """Start the container, write the request on stdin once, read the events until `end`.

        ContainerError when the container cannot take the request (it died at start).
        """
        profile.mkdir(mode=0o700, parents=True, exist_ok=True)
        out.mkdir(mode=0o700, parents=True, exist_ok=True)
        name = container_name(str(request["run"]))
        proc = self._streaming(run_argv(image, profile, out, name))
        assert proc.stdin is not None and proc.stdout is not None
        expired = threading.Event()

        def kill() -> None:
            expired.set()
            with contextlib.suppress(OSError, subprocess.TimeoutExpired):
                self._process(["docker", "kill", name], INFO_TIMEOUT_SECONDS)
            with contextlib.suppress(OSError):
                proc.kill()

        watchdog = threading.Timer(RUN_TIMEOUT_SECONDS, kill)
        watchdog.daemon = True
        watchdog.start()
        try:
            try:
                proc.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
                proc.stdin.close()
            except OSError as err:
                kill()
                raise ContainerError("the read's container did not take the request") from err
            end: dict[str, Any] = {
                "event": "end",
                "outcome": "stopped",
                "reason": "unexpected_ui",
                "classes": {"read": 0, "failed": 0},
            }
            for line in proc.stdout:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get("event") == "end":
                    end = event
                else:
                    on_event(event)
            with contextlib.suppress(subprocess.TimeoutExpired):
                proc.wait(timeout=INFO_TIMEOUT_SECONDS)
        finally:
            watchdog.cancel()
        if expired.is_set() and end.get("outcome") != "ok":
            end = end | {"outcome": "partial" if end.get("classes", {}).get("read") else "stopped", "reason": "timeout"}
        return end
