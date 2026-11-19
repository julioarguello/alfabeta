"""`make format-check` also reads the tracked files a git ignore file hides (#276).

ruff skips what a git ignore file hides, tracked or not, and a clone's own `.git/info/exclude` is one.
A clone that hides `.claude/` skipped the tracked rules there, which CI, with no such line, checks: an
edit could pass the local gate and fail CI's. A second run in the recipe reads the tracked files such
a file hides, asked of git.

CI's checkout hides nothing today and would never notice that run going, so each test builds a
repository that does, and runs the recipe itself there through make. `uv run --locked` is stood in for
by the environment that runs the tests, and every call to it is noted. The control runs ruff with no
path: it must miss the hidden files and find them once nothing hides them, or the repository proves
nothing.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTED = re.compile(r"^\s*--> (.+):\d+:\d+$", re.MULTILINE)
RECIPE = re.compile(r"^format-check:\n((?:\t.*\n)+)", re.MULTILINE)
READ_BY_RUFF = re.compile(r"^file_resolver\.include = \[\n((?:\t.*\n)+?)\]", re.MULTILINE)
SUFFIX = re.compile(r"""["']\*(\.\w+)["']""")
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
# A directory pyproject.toml keeps ruff out of: a tracked file there stays unread even when named.
KEPT_OUT: str = PYPROJECT["tool"]["ruff"]["extend-exclude"][0]

TREE = "tree.py"
OURS = ".claude/rules/ours.md"  # tracked, hidden by the clone's exclude file: the file of the issue
SCRIPT = "data/hidden.py"  # tracked, hidden by the clone's exclude file
ACCENTED = "data/añadir.py"  # the same, with a name git would print quoted and escaped
IGNORED = "ignored/tracked.py"  # tracked, hidden by the repository's own .gitignore
EXPORTED = ".claude/rules/exported.md"  # hidden and not tracked: another project's, not ours to check
VENDORED = f"{KEPT_OUT}/vendored.py"  # tracked, hidden, and kept out by pyproject.toml
DATA = "data/hidden.json"  # tracked, hidden, and not a kind ruff reads
HIDDEN = sorted([OURS, SCRIPT, ACCENTED, IGNORED])
NOT_OURS = [EXPORTED, VENDORED, DATA]
TRACKED = (TREE, *HIDDEN, VENDORED, DATA, "pyproject.toml")
EXCLUDE = f"/.claude/*\n/{KEPT_OUT}/\n/data/\n"
GITIGNORE = "/ignored/\n"

UNFORMATTED = {".py": "x=1\n", ".md": "# A rule\n\n```python\nx=1\n```\n", ".json": '{"a":1}\n'}
FORMATTED = {".py": "x = 1\n", ".md": "# A rule\n\n```python\nx = 1\n```\n", ".json": '{"a": 1}\n'}
STAND_IN = """#!/bin/sh
# The recipe's `uv run --locked <tool> ...`, in the environment that runs the tests; each call is noted.
[ "$1" = run ] && [ "$2" = --locked ] || { echo "not the recipe's call: uv $*" >&2; exit 64; }
shift 2
echo "$*" >> "$UV_CALLS"
exec %s -m "$@"
"""


def environment(tmp_path: Path) -> dict[str, str]:
    """Nothing of the caller's but PATH: no outer make's flags, no git state, no ignore file, no colour."""
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    stand_in = tmp_path / "bin" / "uv"
    stand_in.parent.mkdir(exist_ok=True)
    stand_in.write_text(STAND_IN % shlex.quote(sys.executable), encoding="utf-8")
    stand_in.chmod(0o755)
    return {
        "PATH": f"{stand_in.parent}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "NO_COLOR": "1",
        "PYTHONUTF8": "1",
        "UV_CALLS": str(tmp_path / "uv-calls"),
    }


def repository(tmp_path: Path, name: str, *, unformatted: list[str], hiding: bool = True) -> Path:
    """A repository with the project's ruff settings where the files of `unformatted` need reformatting."""
    repo = tmp_path / name
    env = environment(tmp_path)
    subprocess.run(["git", "init", "-q", str(repo)], env=env, capture_output=True, text=True, check=True)
    (repo / "pyproject.toml").write_text((ROOT / "pyproject.toml").read_text(encoding="utf-8"), encoding="utf-8")
    for file in (TREE, *HIDDEN, *NOT_OURS):
        content = UNFORMATTED if file in unformatted else FORMATTED
        (repo / file).parent.mkdir(parents=True, exist_ok=True)
        (repo / file).write_text(content[Path(file).suffix], encoding="utf-8")
    subprocess.run(["git", "add", "-f", *TRACKED], cwd=repo, env=env, capture_output=True, text=True, check=True)
    if hiding:
        (repo / ".git" / "info").mkdir(exist_ok=True)
        (repo / ".git" / "info" / "exclude").write_text(EXCLUDE, encoding="utf-8")
        (repo / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    return repo


def reported(done: subprocess.CompletedProcess[str]) -> list[str]:
    """The files ruff's report points at, one entry for each time it does."""
    return sorted(REPORTED.findall(done.stdout + done.stderr))


def format_check(repo: Path) -> tuple[int, list[str], list[list[str]]]:
    """make's exit code for the Makefile's `format-check` in `repo`, what ruff reported, and the paths of each run."""
    env = environment(repo.parent)
    done = subprocess.run(
        ["make", "-f", str(ROOT / "Makefile"), "format-check"],
        cwd=repo,
        env=env,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    noted = Path(env["UV_CALLS"])
    calls = noted.read_text(encoding="utf-8").splitlines() if noted.exists() else []
    return done.returncode, reported(done), [[word for word in call.split()[2:] if word[0] != "-"] for call in calls]


def ruff_with_no_path(repo: Path) -> list[str]:
    """What a ruff that is given no path reports in `repo`: the recipe as it was."""
    command = [sys.executable, "-m", "ruff", "format", "--check", "--no-cache"]
    done = subprocess.run(command, cwd=repo, env=environment(repo.parent), capture_output=True, encoding="utf-8")
    return reported(done)


def test_format_check_reads_the_tracked_files_a_git_ignore_file_hides_each_once(tmp_path: Path):
    code, found, runs = format_check(repository(tmp_path, "clone", unformatted=[*HIDDEN, *NOT_OURS]))
    assert found == HIDDEN
    assert code != 0
    assert len(runs) == 2, "both runs go through uv run --locked"
    assert sorted(runs[1]) == sorted([*HIDDEN, VENDORED]), "the second run is given what git names, nothing else"


def test_format_check_still_reads_the_tree_whatever_the_checkout_is_called(tmp_path: Path):
    # venv is one of ruff's own exclusions: a ruff told to force them on the tree would read nothing here.
    code, found, _ = format_check(repository(tmp_path, "venv", unformatted=[TREE]))
    assert found == [TREE]
    assert code != 0


def test_format_check_leaves_alone_what_is_not_the_projects_to_format(tmp_path: Path):
    code, found, runs = format_check(repository(tmp_path, "clone", unformatted=NOT_OURS))
    assert (code, found, len(runs)) == (0, [], 2)


def test_format_check_runs_once_where_nothing_is_hidden(tmp_path: Path):
    code, found, runs = format_check(repository(tmp_path, "clone", unformatted=[], hiding=False))
    assert (code, found, len(runs)) == (0, [], 1)


def test_format_check_stops_when_git_cannot_say_what_is_hidden(tmp_path: Path):
    repo = repository(tmp_path, "clone", unformatted=HIDDEN)
    (repo / ".git" / "index").write_bytes(b"not an index")
    code, found, runs = format_check(repo)
    assert code != 0
    assert (found, len(runs)) == ([], 1)


def test_control_with_no_path_ruff_misses_what_the_ignore_files_hide(tmp_path: Path):
    hidden = ruff_with_no_path(repository(tmp_path, "hidden", unformatted=[TREE, *HIDDEN]))
    seen = ruff_with_no_path(repository(tmp_path, "seen", unformatted=[TREE, *HIDDEN], hiding=False))
    assert hidden == [TREE], "ruff read a tracked file an ignore file hides"
    assert seen == sorted([TREE, *HIDDEN]), "ruff found nothing to reformat in the hidden files"


def test_the_recipe_asks_git_for_the_kinds_of_file_ruff_reads():
    recipe = RECIPE.findall((ROOT / "Makefile").read_text(encoding="utf-8"))
    assert len(recipe) == 1, "the Makefile has one format-check recipe"
    settings = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--show-settings", "--no-cache", __file__],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    read = READ_BY_RUFF.findall(settings)
    assert len(read) == 1, "ruff prints the list of what it reads once"
    assert set(SUFFIX.findall(recipe[0])) == set(SUFFIX.findall(read[0])) != set()
