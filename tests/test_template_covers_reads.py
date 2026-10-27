"""Every key alfabeta reads is declared in the template (spec 001 T020).

The walk finds each call to a reader of `config.READERS` and takes its path argument, which must be
a string literal: a path built at run time is reported, because the walk cannot see it.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, cast

from alfabeta import config

SRC = Path(config.__file__).resolve().parent
NOT_A_LITERAL = "<not a literal>"


def reads(source: str) -> list[str]:
    """The key paths read in one module's source."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
        if name not in config.READERS:
            continue
        path = node.args[1] if len(node.args) > 1 else None
        literal = isinstance(path, ast.Constant) and isinstance(path.value, str)
        found.append(cast("str", path.value) if literal else NOT_A_LITERAL)  # type: ignore[union-attr]
    return found


def declared(template: dict[str, Any], path: str) -> bool:
    """Whether the template declares `path`; `*` is a name of a dynamic table."""
    node: Any = template
    for part in path.split("."):
        if isinstance(node, list) and node:
            node = cast("list[Any]", node)[0]
            if part == "*":  # the element of an array of tables, such as [[subjects]]
                continue
        if not isinstance(node, dict):
            return False
        step = config.DYNAMIC if part == "*" else part
        if step not in node:
            return False
        node = cast("dict[str, Any]", node)[step]
    return True


def test_every_read_key_is_in_the_template():
    template = config.load_template()
    paths = [p for module in sorted(SRC.rglob("*.py")) for p in reads(module.read_text())]
    assert paths, "the walk found no read at all"
    assert [p for p in paths if not declared(template, p)] == []


CONTROL = """
def f(data, alias):
    a = _str(data, "classroom.account")
    b = cfg._strs(data, "google.accounts.*.scopes", alias)
    c = _names(data, "google.accounts")
    d = other(data, "not.a.reader")
"""


def test_control_finds_the_known_reads_and_rejects_planted_ones():
    template = config.load_template()
    assert reads(CONTROL) == ["classroom.account", "google.accounts.*.scopes", "google.accounts"]
    assert all(declared(template, p) for p in reads(CONTROL))
    planted = CONTROL + '    e = _str(data, "classroom.nickname")\n    g = _str(data, f"x.{alias}")\n'
    assert [p for p in reads(planted) if not declared(template, p)] == ["classroom.nickname", NOT_A_LITERAL]
    assert declared(template, "subjects.folder")
