"""The built image, offline (spec 006 T011; FR-028, SC-009).

It needs Docker and builds an amd64 image with Google Chrome (minutes), so it runs where
`ALFABETA_DOCKER_TESTS=1` is set — on the Mac before a pull request that touches the image, whose
description records the result. No network reaches the container (`--network none`), and the
credentials are invented.
"""

from __future__ import annotations

import json
import os
import subprocess

import pytest

from alfabeta.classroom import container

pytestmark = pytest.mark.skipif(
    os.environ.get("ALFABETA_DOCKER_TESTS") != "1",
    reason="builds the read's image; run on the Mac before its pull request",
)
PASSWORD = "contraseña-inventada-123"
ACCOUNT = "alumno@example.test"


def test_the_image_holds_no_secret_and_runs_offline() -> None:
    reader = container.DockerReadContainer()
    assert reader.available()
    image = reader.ensure_image()
    config = json.loads(
        subprocess.run(
            ["docker", "image", "inspect", image], capture_output=True, text=True, timeout=60, check=True
        ).stdout
    )[0]["Config"]
    assert PASSWORD not in json.dumps(config) and ACCOUNT not in json.dumps(config)
    request = json.dumps({"run": "run0000000000001", "account": ACCOUNT, "password": PASSWORD, "signin": True})
    done = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-i",
            "--network",
            "none",
            "--platform",
            container.PLATFORM,
            "--label",
            "alfabeta-test=1",
            image,
        ],
        input=request + "\n",
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    lines = [json.loads(line) for line in done.stdout.splitlines() if line.startswith("{")]
    assert lines[-1]["event"] == "end" and lines[-1]["reason"] == "unreachable"
    assert PASSWORD not in done.stdout + done.stderr and ACCOUNT not in done.stdout + done.stderr
    left = subprocess.run(
        ["docker", "ps", "-aq", "--filter", "label=alfabeta-test=1"],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    assert left.stdout.strip() == ""
