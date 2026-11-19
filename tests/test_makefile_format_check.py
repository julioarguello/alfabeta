"""`make format-check` reads the rules under `.claude/` whatever the clone's exclude file says (#276).

ruff skips what `.git/info/exclude` hides, tracked or not. A clone whose exclude file hides `.claude/`
skipped the tracked rules there, which CI, with no such line, checks: an edit could pass the local
gate and fail CI's. The recipe names the directory, and a directory named on the command line is read
all the same.

CI would never notice the path going, so the test builds a repository that has the line and a rule
with an unformatted block, and hands ruff the recipe's own arguments. The control hands it none: the
block must go unseen under the line and be seen without it, or the repository proves nothing.
"""

from __future__ import annotations

import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECIPE = re.compile(r"^format-check:\n\t.*\bruff format --check(.*)$", re.MULTILINE)
EXCLUDE = "/.claude/*\n"
RULE = "# A rule\n\n```python\nx=1\n```\n"


def recipe_arguments() -> list[str]:
    """What the Makefile's recipe gives `ruff format --check` after the flag."""
    found = RECIPE.findall((ROOT / "Makefile").read_text(encoding="utf-8"))
    assert len(found) == 1, "the Makefile has one format-check recipe, and it runs ruff format --check"
    return shlex.split(found[0])


def repository(path: Path, *, exclude: str) -> Path:
    """A repository with the project's ruff settings, a formatted file, a rule to reformat and `exclude`."""
    subprocess.run(["git", "init", "-q", str(path)], capture_output=True, text=True, check=True)
    info = path / ".git" / "info"
    info.mkdir(exist_ok=True)
    (info / "exclude").write_text(exclude, encoding="utf-8")
    (path / "pyproject.toml").write_text((ROOT / "pyproject.toml").read_text(encoding="utf-8"), encoding="utf-8")
    (path / "formatted.py").write_text("x = 1\n", encoding="utf-8")
    rules = path / ".claude" / "rules"
    rules.mkdir(parents=True)
    (rules / "rule.md").write_text(RULE, encoding="utf-8")
    return path


def check(arguments: list[str], repo: Path) -> subprocess.CompletedProcess[str]:
    """ruff's verdict on `repo`: the ruff of the environment that runs the tests, the locked one."""
    return subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", "--no-cache", *arguments],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def test_format_check_reads_a_rule_the_clones_exclude_file_hides(tmp_path: Path):
    done = check(recipe_arguments(), repository(tmp_path / "clone", exclude=EXCLUDE))
    assert done.returncode == 1, done.stdout + done.stderr
    assert ".claude/rules/rule.md" in done.stdout


def test_control_with_no_path_the_exclude_line_hides_the_rule(tmp_path: Path):
    hidden = check([], repository(tmp_path / "hidden", exclude=EXCLUDE))
    seen = check([], repository(tmp_path / "seen", exclude=""))
    assert hidden.returncode == 0, f"ruff read a rule the exclude line hides: {hidden.stdout}"
    assert seen.returncode == 1, f"ruff found nothing to reformat in the rule: {seen.stdout}{seen.stderr}"
