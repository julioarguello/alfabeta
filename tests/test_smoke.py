import subprocess
import sys
from pathlib import Path


def test_version_runs():
    done = subprocess.run([sys.executable, "-m", "alfabeta", "--version"], capture_output=True, text=True, check=False)
    assert done.returncode == 0
    assert done.stdout.startswith("alfabeta ")


def test_missing_home_is_refused(tmp_path: Path):
    done = subprocess.run(
        [sys.executable, "-m", "alfabeta", "--home", str(tmp_path / "nope"), "google", "check", "--student", "s9"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 1
    assert '"no_home"' in done.stdout
