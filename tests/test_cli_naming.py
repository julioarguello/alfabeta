"""The CLI's naming convention, gated (`.claude/rules/cli-naming.md`, `.claude/rules/python-cli.md`).

Two walks over the real parser, never over the AST:

- the command tree: every command is `<group> [<subgroup>] <verb>`, each name from the closed
  vocabulary below, in kebab-case, with no short letters, no secret on a flag, and `--student`
  wherever a student is meant;
- the documentation: every command written in a skill, a spec, a doc or a message, as
  `python -m alfabeta …`, «alfabeta …» or a code span starting with a group, exists on the parser,
  with every `--flag` written beside it.

The vocabulary lives here and nowhere else: a rule or a doc that needs it points at this file.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path
from typing import cast

import pytest

from alfabeta.__main__ import build_parser

ROOT = Path(__file__).resolve().parents[1]

# Groups and subgroups: singular nouns of the domain. Its one meaning beside each.
GROUPS = {
    "agenda": "the student's agenda of assignments and exams",
    "book": "a textbook provider's result",
    "calendar": "the family calendar",
    "claude": "this place's Claude API key",
    "classroom": "the Classroom sync",
    "config": "the student's configuration",
    "decision": "Claude's proposals and the family's decisions",
    "download": "a file in the browser's downloads folder",
    "drive": "the student's Drive: alfabeta's own connection, and the mirrors of the master folder",
    "exam": "an exam the family declares, and the sheets for the day before one",
    "google": "alfabeta's own Google connection",
    "guardrail": "the personal-data guardrail",
    "lock": "a run's lock",
    "log": "the run log",
    "note": "a photo of the student's class notes",
    "notebook": "a topic's notebook",
    "notice": "a notification to the family",
    "page": "a saved Classroom page",
    "sandbox": "an invented student to try a run",
}
SUBGROUPS = {
    "account": "a linked Google account",
    "agent": "a launchd agent that runs a command with no app open (`notebook refresh`, `classroom refresh`)",
    "probe": "a test calendar event",
}
# Verbs: one meaning each, CLI-wide. A leaf is a verb, or `<verb>-<object>` when the group has
# only that one action on the object (`google set-client`, as `google.setClient()`).
VERBS = {
    "anonymize": "replace a saved page's personal data with invented data",
    "apply": "write what a plan computed",
    "build": "generate files derived from the state",
    "capture": "read a platform into a capture, guarded, without changing it",
    "check": "verify and report; changes nothing the family owns",
    "collect": "move a run's expected files into its data folder",
    "confirm": "accept or reject a proposal",
    "create": "make one object",
    "delete": "remove objects",
    "install": "add a system agent",
    "link": "connect an account",
    "migrate": "adopt, once, what an earlier layout left behind",
    "place": "put what a provider built in its topic folder",
    "plan": "compute what a run will do, writing only the plan",
    "prepare": "make something ready for use, once",
    "propose": "record proposals",
    "pull": "bring an outside store's new files into the local copy (spec 004)",
    "push": "send the local copy's new files to an outside store (spec 004)",
    "refresh": "re-read sources so a copy that depends on them is current",
    "release": "give up a run's lock",
    "renew": "extend a run's lock",
    "replay": "simulate past days without writing anything",
    "send": "send a notice",
    "set": "store a value or a secret",
    "sign-in": "open a window for the family to sign in by hand; types nothing",
    "stage": "copy files to where a later step expects them",
    "sync": "write the state out to an outside copy (the calendar, the mirrors)",
    "take": "acquire a run's lock",
    "transcribe": "turn photos into text pages",
    "uninstall": "remove a system agent",
    "unlink": "revoke an account's link",
    "update": "change a recorded decision",
    "write": "write a line of the run log",
}
# A leaf that is not a verb: an aggregate view drops the verb (python-cli.md §6).
AGGREGATES = {"status": "a status view"}
# Words the vocabulary rejects, and what says it instead.
REJECTED = {
    "run": "name the action (`note transcribe`)",
    "do": "name the action",
    "execute": "name the action",
    "setup": "`prepare`",
    "prep": "`build` or `prepare`",
    "remove": "`uninstall` or `delete`",
    "change": "`update`",
    "correct": "`update`",
    "validate": "`check`",
    "signin": "`sign-in`",
}
# A command with no student: it reads the repository or two files, never a configuration.
NO_STUDENT = {("page", "anonymize"), ("guardrail", "check")}
# Commands a spec designs and no code builds yet: (path, the spec that designs it).
PLANNED: dict[tuple[str, ...], str] = {
    ("calendar", "sync"): "spec 003 contracts/cli.md",
    ("calendar", "replay"): "spec 003 contracts/cli.md",
    ("calendar", "set-delivery"): "spec 003 contracts/cli.md",
    ("calendar", "set-sharing"): "spec 003 contracts/cli.md",
    ("calendar", "delete-legacy"): "spec 003 contracts/cli.md",
    ("drive", "migrate"): "spec 004 contracts/cli.md",
    ("drive", "push"): "spec 004 contracts/cli.md",
    ("drive", "pull"): "spec 004 contracts/cli.md",
    ("classroom", "sign-in"): "spec 006 FR-021",
    ("classroom", "refresh"): "spec 006 FR-022",
    ("classroom", "capture"): "spec 006 FR-023",
    ("classroom", "status"): "spec 006 FR-024",
    ("classroom", "agent", "install"): "spec 006 FR-015, plan",
    ("classroom", "agent", "uninstall"): "spec 006 FR-015, plan",
    ("exam", "create"): "spec 007 FR-001",
}
# Options a spec designs on a built command and no code adds yet.
PLANNED_OPTIONS: dict[tuple[str, ...], set[str]] = {
    ("google", "account", "link"): {"--client-file", "--print-token", "--scopes"},  # spec 005 T025
    ("exam", "build"): {"--undated"},  # spec 007 FR-025
}
SECRET_FLAG = re.compile(r"^--(token|password|secret|api-key|client-secret|key|refresh-token)$")
KEBAB = re.compile(r"^[a-z]+(-[a-z]+)*$")
LONG_FLAG = re.compile(r"^--[a-z]+(-[a-z]+)*$")


def _children(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:  # argparse exposes no public walk
        if isinstance(action, argparse._SubParsersAction):
            subparsers = cast("argparse._SubParsersAction[argparse.ArgumentParser]", action)
            return dict(subparsers.choices)
    return {}


def _leaves() -> list[tuple[tuple[str, ...], argparse.ArgumentParser]]:
    found: list[tuple[tuple[str, ...], argparse.ArgumentParser]] = []

    def walk(parser: argparse.ArgumentParser, path: tuple[str, ...]) -> None:
        children = _children(parser)
        if not children:
            found.append((path, parser))
        for name, child in children.items():
            walk(child, (*path, name))

    walk(build_parser(), ())
    return found


def _options(parser: argparse.ArgumentParser) -> set[str]:
    return {o for a in parser._actions for o in a.option_strings}


def _verb(leaf: str) -> str:
    """A leaf's verb: the whole leaf when it is a verb (`sign-in`), else the part before `-<object>`."""
    return leaf if leaf in VERBS else leaf.split("-", 1)[0]


LEAVES = _leaves()


def test_the_tree_is_not_empty() -> None:
    assert len(LEAVES) >= 30  # a walk that finds nothing is not green


def _name_problems(path: tuple[str, ...]) -> list[str]:
    """What is wrong with a command's name; empty when it follows the grammar."""
    if not 2 <= len(path) <= 3:
        return [f"{' '.join(path)}: a command is <group> [<subgroup>] <verb>"]
    group, *middle, leaf = path
    problems: list[str] = []
    if group not in GROUPS:
        problems.append(f"{group}: not a group of the vocabulary")
    problems += [f"{sub}: not a subgroup of the vocabulary" for sub in middle if sub not in SUBGROUPS]
    problems += [f"{name}: names are kebab-case" for name in path if not KEBAB.match(name)]
    problems += [f"{name}: rejected word, say {REJECTED[name]}" for name in path if name in REJECTED]
    if _verb(leaf) not in VERBS and leaf not in AGGREGATES:
        problems.append(f"{leaf}: its verb {_verb(leaf)!r} is not in the vocabulary")
    if leaf in GROUPS or leaf in SUBGROUPS:
        problems.append(f"{leaf}: a leaf never shares a group's name")
    return problems


@pytest.mark.parametrize(("path", "parser"), LEAVES, ids=[" ".join(p) for p, _ in LEAVES])
def test_every_command_is_group_subgroup_verb(path: tuple[str, ...], parser: argparse.ArgumentParser) -> None:
    assert not _name_problems(path)


@pytest.mark.parametrize(
    "planted",
    [
        ("plan",),  # a verb with no group
        ("notes", "run"),  # a plural group and a vague verb
        ("decisions", "correct"),  # a plural group and a synonym of update
        ("exam", "prep"),  # a rejected abbreviation
        ("notebook", "setup"),  # a rejected word
        ("google", "account", "account"),  # a leaf named as a group
        ("calendar", "probeClean"),  # not kebab-case
        ("agenda", "build", "now", "please"),  # too deep
    ],
)
def test_the_name_check_fires(planted: tuple[str, ...]) -> None:
    assert _name_problems(planted)


@pytest.mark.parametrize(("path", "parser"), LEAVES, ids=[" ".join(p) for p, _ in LEAVES])
def test_every_option_is_long_kebab_and_no_secret(path: tuple[str, ...], parser: argparse.ArgumentParser) -> None:
    for option in _options(parser) - {"-h", "--help"}:
        assert LONG_FLAG.match(option), f"{' '.join(path)} {option}: long, kebab-case, no short letter"
        assert not SECRET_FLAG.match(option), f"{' '.join(path)} {option}: a secret is never a flag"


@pytest.mark.parametrize(("path", "parser"), LEAVES, ids=[" ".join(p) for p, _ in LEAVES])
def test_a_student_command_takes_student(path: tuple[str, ...], parser: argparse.ArgumentParser) -> None:
    if path in NO_STUDENT:
        assert "--student" not in _options(parser)
    else:
        assert "--student" in _options(parser), f"{' '.join(path)}: names its student with --student"


def test_the_vocabulary_has_no_stale_entry() -> None:
    used_groups = {p[0] for p, _ in LEAVES}
    used_subgroups = {s for p, _ in LEAVES for s in p[1:-1]}
    used_verbs = ({_verb(p[-1]) for p, _ in LEAVES} | {_verb(p[-1]) for p in PLANNED}) - set(AGGREGATES)
    assert set(GROUPS) == used_groups | {p[0] for p in PLANNED}
    assert set(SUBGROUPS) == used_subgroups | {s for p in PLANNED for s in p[1:-1]}
    assert set(VERBS) == used_verbs
    assert set(NO_STUDENT) <= {p for p, _ in LEAVES}


def test_planned_options_are_not_built() -> None:
    leaves = dict(LEAVES)
    for path, options in PLANNED_OPTIONS.items():
        assert path in leaves, f"{' '.join(path)}: planned options on a command that does not exist"
        assert not options & _options(leaves[path]), f"{' '.join(path)}: built, drop it from PLANNED_OPTIONS"


def test_planned_commands_follow_the_grammar_and_are_not_built() -> None:
    built = {p for p, _ in LEAVES}
    for path, spec in PLANNED.items():
        assert path not in built, f"{' '.join(path)} is built: drop it from PLANNED ({spec})"
        assert path[0] in GROUPS and all(s in SUBGROUPS for s in path[1:-1])
        assert _verb(path[-1]) in VERBS or path[-1] in AGGREGATES, f"{' '.join(path)}: verb not in the vocabulary"


# --- The documentation -----------------------------------------------------------------------

TREE = build_parser()
_INVOCATION = re.compile(r"(?:python -m alfabeta|[«`]alfabeta)((?: [^\s`»|]+)+)")
_SPAN = re.compile(r"`([a-z][a-z-]* [^`]+)`")
_TEXT = (".md", ".py", ".toml", "Makefile", "pre-commit")
_SKIP = ("tests/test_cli_naming.py", "uv.lock")


def _tracked_text() -> list[Path]:
    names = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    return [ROOT / n for n in names if n.endswith(_TEXT) and n not in _SKIP]


# Group names the vocabulary retired: a doc that still writes one names a command that is gone.
RETIRED_GROUPS = {"notes": "note", "decisions": "decision", "downloads": "download"}
_WORD = re.compile(r"[a-z][a-z-]*")


def _resolve(tokens: list[str], *, explicit: bool) -> str | None:
    """None when the written command exists with its flags, else why not.

    `explicit`: the text wrote `alfabeta` before it, so its first word must be a group.
    """
    words = list(tokens)
    while words and words[0] in {"--home", "--version"}:
        words = words[2:] if words[0] == "--home" else words[1:]
    if not words:
        return None
    first, rest = words[0], words[1:]
    if first in RETIRED_GROUPS:
        return f"{first}: a retired group, now {RETIRED_GROUPS[first]!r}"
    if first not in _children(TREE):
        if any(p[0] == first for p in PLANNED):
            ok = bool(rest) and (first, rest[0]) in PLANNED
            return None if ok else f"{first}: a planned group, but no planned {' '.join(rest[:1])!r}"
        if first in VERBS and rest and rest[0].startswith(("--", "<")):
            return f"{first}: a verb with no group"
        if explicit and _WORD.fullmatch(first):
            return f"{first}: no group {first!r}"
        return None
    node: argparse.ArgumentParser = TREE
    path: list[str] = []
    while words:
        children = _children(node)
        if not children:
            break
        word = words[0]
        if word in children:
            node, path = children[word], [*path, word]
            words.pop(0)
        elif word.startswith("--") and path:
            return f"{' '.join(path)}: a group needs a verb before {word}"
        elif _WORD.fullmatch(word) and path:
            if (*path, word) in PLANNED:
                return None
            if any(p[: len(path) + 1] == (*path, word) for p in PLANNED):  # a planned subgroup
                after = words[1:2]
                if after and after[0].startswith("--"):
                    return f"{' '.join((*path, word))}: a group needs a verb before {after[0]}"
                if not after or not _WORD.fullmatch(after[0]) or (*path, word, after[0]) in PLANNED:
                    return None
                return f"{' '.join((*path, word))}: a planned subgroup, but no planned {after[0]!r}"
            return f"{' '.join(path)}: no subcommand {word!r}"
        else:
            return None  # a placeholder, a wildcard or prose: not a command
    if _children(node):
        return None  # a group named on its own
    flags = {w.split("=", 1)[0] for w in words if w.startswith("--")}
    known = _options(node) | PLANNED_OPTIONS.get(tuple(path), set())
    unknown = sorted(f for f in flags if re.fullmatch(r"--[a-z][a-z-]*", f) and f not in known)
    return f"{' '.join(path)}: no option {', '.join(unknown)}" if unknown else None


def _line_problems(line: str, *, docs: bool) -> list[str]:
    """Why each command written on the line does not exist; `docs` also reads bare code spans."""
    candidates = [(m.group(1).split(), True) for m in _INVOCATION.finditer(line)]
    if docs:  # a bare code span names alfabeta's command only in its docs
        starts = set(_children(TREE)) | set(RETIRED_GROUPS) | set(VERBS)
        candidates += [(m.group(1).split(), False) for m in _SPAN.finditer(line) if m.group(1).split()[0] in starts]
    found = (_resolve(tokens, explicit=explicit) for tokens, explicit in candidates)
    return [why for why in found if why]


def test_every_written_command_exists() -> None:
    problems: list[str] = []
    for file in _tracked_text():
        for number, line in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
            problems += [
                f"{file.relative_to(ROOT)}:{number}: {why}" for why in _line_problems(line, docs=file.suffix == ".md")
            ]
    assert not problems, "commands written that the parser does not have:\n" + "\n".join(problems)


@pytest.mark.parametrize(
    "line",
    [
        "run `python -m alfabeta google link --student x`",  # an old leaf
        "«alfabeta notes run»",  # a retired group in a message
        "then `notes run --student <id>`",  # a retired group in a bare span
        "`decisions confirm --type x`",  # a retired group
        "`plan --student <id>`",  # a verb with no group
        "`classroom plan --student <id> --bogus`",  # an option the command lacks
        "python -m alfabeta guardrail --all",  # a group that now needs its verb
        "python -m alfabeta exam prep --student x",  # an old verb in an explicit call
        "python -m alfabeta anonymize in out",  # an old top-level command
        "`classroom agent start --student <id>`",  # a planned subgroup, an unplanned verb
        "`classroom robot install --student <id>`",  # neither built nor planned
        "`classroom agent --student <id>`",  # a planned subgroup that needs its verb
    ],
)
def test_the_written_command_check_fires(line: str) -> None:
    assert _line_problems(line, docs=True)


@pytest.mark.parametrize(
    "line",
    [
        "the `plan` and the `apply` steps",  # prose words, no command written
        "`notebook agent` is the launchd agent",  # a group named on its own
        "`decision *` subcommands",  # a wildcard
        "`classroom plan --student <id> [--subject <folder>]…`",  # the real command
        "python -m alfabeta <command>",  # a placeholder
        "`calendar sync --student <id> [--apply]`",  # planned by spec 003
        "`classroom agent install --student <id>`",  # a planned subgroup's planned verb, spec 006
        "`classroom agent install|uninstall`",  # its verbs listed
        "`classroom agent`",  # a planned subgroup named on its own
    ],
)
def test_the_written_command_check_spares(line: str) -> None:
    assert not _line_problems(line, docs=True)
