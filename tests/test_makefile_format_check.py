"""`make format-check` reads every tracked file ruff formats, whatever an ignore file hides (#276).

ruff skips what an ignore file hides, tracked or not, and a clone's own `.git/info/exclude` is one. A
clone that hides `.claude/` skipped the tracked rules there, which CI, with no such line, checks: an
edit could pass the local gate and fail CI's. The recipe also names the tracked files an ignore file
hides, asked of git.

CI's checkout hides nothing and would never notice the names going, so each test builds a repository
that does, and runs the recipe itself there through make. `uv run --locked` is stood in for by the
environment that runs the tests. The control runs the recipe without its arguments: it must miss the
hidden rule and find it once nothing hides it, or the repository proves nothing.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path

from tests.test_makefile_serial import INHERITED

ROOT = Path(__file__).resolve().parents[1]
RECIPE = re.compile(r"^(format-check:\n\t.*\bruff format --check)(.*)$", re.MULTILINE)
REPORTED = re.compile(r"^\s*--> (.+):\d+:\d+$", re.MULTILINE)
# A directory pyproject.toml keeps ruff out of: a tracked file there stays unread even when named.
KEPT_OUT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["ruff"]["extend-exclude"][0]

TREE = "tree.py"
OURS = ".claude/rules/ours.md"  # tracked, hidden: the file of the issue
EXPORTED = ".claude/rules/exported.md"  # hidden and not tracked: another project's, not ours to check
VENDORED = f"{KEPT_OUT}/vendored.py"  # tracked, hidden, and kept out by pyproject.toml
DATA = "data/hidden.json"  # tracked, hidden, and not a kind ruff formats
TRACKED = (TREE, OURS, VENDORED, DATA, "pyproject.toml")
HIDES = f"/.claude/*\n/{KEPT_OUT}/\n/data/\n"

UNFORMATTED = {".py": "x=1\n", ".md": "# A rule\n\n```python\nx=1\n```\n", ".json": '{"a":1}\n'}
FORMATTED = {".py": "x = 1\n", ".md": "# A rule\n\n```python\nx = 1\n```\n", ".json": '{"a": 1}\n'}
STAND_IN = """#!/bin/sh
# The recipe's `uv run --locked <tool> ...`, in the environment that runs the tests.
[ "$1" = run ] && [ "$2" = --locked ] || { echo "not the recipe's call: uv $*" >&2; exit 64; }
shift 2
exec %s -m "$@"
"""


def environment(tmp_path: Path) -> dict[str, str]:
    """No flags from an outer make, no git state or ignore file of the person's, and the stand-in first."""
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    stand_in = tmp_path / "bin" / "uv"
    stand_in.parent.mkdir(exist_ok=True)
    stand_in.write_text(STAND_IN % shlex.quote(sys.executable), encoding="utf-8")
    stand_in.chmod(0o755)
    kept = {name: value for name, value in os.environ.items() if name not in INHERITED and not name.startswith("GIT_")}
    path = f"{stand_in.parent}{os.pathsep}{kept['PATH']}"
    return kept | {"PATH": path, "HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config")}


def repository(tmp_path: Path, name: str, *, hides: str, unformatted: set[str]) -> Path:
    """A repository with the project's ruff settings where the files of `unformatted` need reformatting."""
    repo = tmp_path / name
    env = environment(tmp_path)
    subprocess.run(["git", "init", "-q", str(repo)], env=env, capture_output=True, text=True, check=True)
    (repo / "pyproject.toml").write_text((ROOT / "pyproject.toml").read_text(encoding="utf-8"), encoding="utf-8")
    for file in (TREE, OURS, EXPORTED, VENDORED, DATA):
        content = UNFORMATTED if file in unformatted else FORMATTED
        (repo / file).parent.mkdir(parents=True, exist_ok=True)
        (repo / file).write_text(content[Path(file).suffix], encoding="utf-8")
    subprocess.run(["git", "add", "-f", *TRACKED], cwd=repo, env=env, capture_output=True, text=True, check=True)
    (repo / ".git" / "info").mkdir(exist_ok=True)
    (repo / ".git" / "info" / "exclude").write_text(hides, encoding="utf-8")
    return repo


def format_check(makefile: str, repo: Path) -> tuple[int, set[str]]:
    """make's exit code for `format-check` in `repo`, and the files ruff said it would reformat."""
    under_test = repo.parent / "Makefile.under-test"
    under_test.write_text(makefile, encoding="utf-8")
    done = subprocess.run(
        ["make", "-f", str(under_test), "format-check"],
        cwd=repo,
        env=environment(repo.parent),
        capture_output=True,
        text=True,
        check=False,
    )
    return done.returncode, set(REPORTED.findall(done.stdout + done.stderr))


def makefile() -> str:
    return (ROOT / "Makefile").read_text(encoding="utf-8")


def test_format_check_reads_the_tree_and_the_tracked_files_an_ignore_file_hides(tmp_path: Path):
    everything = {TREE, OURS, EXPORTED, VENDORED, DATA}
    code, reported = format_check(makefile(), repository(tmp_path, "clone", hides=HIDES, unformatted=everything))
    assert reported == {TREE, OURS}
    assert code != 0


def test_format_check_leaves_alone_what_is_not_the_projects_to_format(tmp_path: Path):
    not_ours = {EXPORTED, VENDORED, DATA}
    code, reported = format_check(makefile(), repository(tmp_path, "clone", hides=HIDES, unformatted=not_ours))
    assert (code, reported) == (0, set())


def test_control_without_its_arguments_the_recipe_misses_the_hidden_rule(tmp_path: Path):
    bare, replaced = RECIPE.subn(r"\1", makefile())
    assert replaced == 1, "the Makefile has one format-check recipe, and it runs ruff format --check"
    _, hidden = format_check(bare, repository(tmp_path, "hidden", hides=HIDES, unformatted={TREE, OURS}))
    _, seen = format_check(bare, repository(tmp_path, "seen", hides="", unformatted={TREE, OURS}))
    assert hidden == {TREE}, "ruff read a rule the exclude file hides"
    assert seen == {TREE, OURS}, "ruff found nothing to reformat in the rule"
