"""Constitution 2.12.0 (Technical constraints > Language): every command prints English, each line with the time.

The gates python-cli-output §1 and §6 promise for the whole program (#261):

- no string literal in `src/` holds Spanish, but for the family-facing writers and the readers of
  Classroom's Spanish page, excluded by name with the reason;
- no module but `alfabeta.output` writes to stderr, and every module's helper (`_say`, `_fail`)
  prints `alfabeta: <YYYY-MM-DDTHH:MM:SS> <message>`.
"""

from __future__ import annotations

import ast
import datetime as dt
import importlib
import inspect
import re
import subprocess
from pathlib import Path

import pytest

from alfabeta import output

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

# Accented letters and ¿¡ are Spanish in this repository (English carries none); the words are
# Spanish words no English line uses. «» are not on the list: English lines quote names with them.
_SPANISH = re.compile(
    r"[áéíóúñÁÉÍÓÚÑ¿¡]"
    r"|(?<![\w-])(?:sin|con|por|para|los|las|una|del|que|nuevos|cambiados|colocados|compartid[ao]s?|carpeta"
    r"|actualizada|escrita|fallidas|guardadas|cuadernos|cuentas?|clases?|temas|prueba|ignorar|informes?|examen|apuntes)(?![\w-])"
)

# Where Spanish belongs (constitution, Technical constraints > Language), by module or by
# `module.name` (a module-level constant, a function or a class), each with its reason.
FAMILY_FACING: dict[str, str] = {
    # Whole modules: they write only for the family, or only read Classroom's Spanish page.
    "alfabeta.agenda": "the family's agenda",
    "alfabeta.anonymize": "reads Classroom's Spanish page",
    "alfabeta.dates": "reads Classroom's Spanish dates",
    "alfabeta.exam.prompts": "the notebook's prompts for the family's material",
    "alfabeta.notes.report": "the family's notes report",
    "alfabeta.notes.statements": "the problems' statements in the family's notes",
    # One name each, in modules that also print to the terminal or raise into `_fail`.
    "alfabeta.capture._MODIFIED": "reads Classroom's Spanish page",
    "alfabeta.capture._NO_DUE": "reads Classroom's Spanish page",
    "alfabeta.capture._TURNED_IN_LATE": "reads Classroom's Spanish page",
    "alfabeta.capture._WAITING": "reads Classroom's Spanish page",
    "alfabeta.classification.EXAM_HINTS": "reads the teacher's Spanish words for an exam",
    "alfabeta.classroom.refresh.ADVICE": "the Mac notification of a stopped read",
    "alfabeta.classroom.refresh.notification": "the Mac notification of a stopped read",
    "alfabeta.exam.cli._part": "a prompt to the notebook",
    "alfabeta.exam.cli._open_part": "a prompt to the notebook",
    "alfabeta.exam.cli._sheets": "the names of the printed sheets",
    "alfabeta.exam.prep.CORRECTIONS_HEADING": "a heading of the family's bloques.md",
    "alfabeta.exam.prep.QUESTIONS_HEADING": "a heading of the family's bloques.md",
    "alfabeta.exam.prep.START_TITLE": "the title of the pack's start note",
    "alfabeta.exam.prep._GUIDE": "reads the name of the pack's study guide",
    "alfabeta.google.notify._REASONS": "the Mac notification",
    "alfabeta.google.notify.link_failed": "the Mac notification",
    "alfabeta.google.notify.signin_needed": "the Mac notification",
    "alfabeta.google.oauth._CallbackHandler": "the browser page the family sees after linking an account",
    "alfabeta.notes.changes.TRANSCRIPT_MARK": "names of the files alfabeta writes for the family",
    "alfabeta.notes.model.NotesPage": "the transcription's states, written in the family's folder",
    "alfabeta.notes.pdf.ReportlabPdfBuilder": "the family's printed transcription",
    "alfabeta.notes.refresh.AGENDA_LINE": "the agenda's warning",
    "alfabeta.notes.refresh.GONE_AGENDA_LINE": "the agenda's warning",
    "alfabeta.notes.refresh.NOTICE": "the Mac notification",
    "alfabeta.notes.refresh.GONE_NOTICE": "the Mac notification",
    "alfabeta.notes.refresh.gone_notice": "the Mac notification",
    "alfabeta.notes.watch.REPORT_LABEL": "the agenda's label for a notes report",
    "alfabeta.notes.run._correct": "names of the files alfabeta writes for the family",
    "alfabeta.notes.run._photo": "names of the files alfabeta writes for the family",
    "alfabeta.notes.run._write_lines": "names of the files alfabeta writes for the family",
    "alfabeta.notes.transcribe.INSTRUCTIONS": "the transcription written for the family",
    "alfabeta.notes.transcribe.UNREADABLE": "the transcription written for the family",
    "alfabeta.placement.Placer": "names of the files alfabeta writes for the family",
    "alfabeta.replicas.NOT_ARRIVED": "«no traído» in the family's enlaces.md",
    "alfabeta.replicas._GRADING_STATES": "the correction note in the family's folder",
    "alfabeta.replicas._grading_note": "the correction note in the family's folder",
    "alfabeta.replicas._links_note": "the family's enlaces.md",
    "alfabeta.sandbox._config": "a sample student's configuration (the family's own words)",
    "alfabeta.__main__.PROBE_SUMMARY": "a calendar event the family sees",
    "alfabeta.__main__._cmd_probe": "a calendar event the family sees",
}


def _modules() -> list[tuple[str, Path]]:
    tracked = subprocess.run(
        ["git", "ls-files", "src/alfabeta/**.py"], cwd=ROOT, capture_output=True, text=True, check=True, timeout=30
    ).stdout.split()
    found: list[tuple[str, Path]] = []
    for name in tracked:
        path = ROOT / name
        parts = path.relative_to(SRC).with_suffix("").parts
        found.append((".".join(parts[:-1] if parts[-1] == "__init__" else parts), path))
    return found


def _docstrings(tree: ast.AST) -> set[int]:
    owners = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    return {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(node, owners)
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    }


def _spanish_literals(module: str, tree: ast.Module) -> list[tuple[str, int, str]]:
    """Every non-docstring string literal that reads Spanish, with the top-level name that holds it."""
    docs = _docstrings(tree)
    hits: list[tuple[str, int, str]] = []
    for top in tree.body:
        if isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            owner = top.name
        elif isinstance(top, (ast.Assign, ast.AnnAssign)):
            targets = top.targets if isinstance(top, ast.Assign) else [top.target]
            owner = next((t.id for t in targets if isinstance(t, ast.Name)), "")
        else:
            owner = ""
        for node in ast.walk(top):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in docs
                and _SPANISH.search(node.value)
            ):
                hits.append((f"{module}.{owner}" if owner else module, node.lineno, node.value))
    return hits


def _excluded(where: str) -> bool:
    return any(where == name or where.startswith(name + ".") for name in FAMILY_FACING)


def test_no_command_prints_spanish() -> None:
    found: list[str] = []
    for module, path in _modules():
        for where, line, text in _spanish_literals(module, ast.parse(path.read_text())):
            if not _excluded(where):
                found.append(f"{path.relative_to(ROOT)}:{line} ({where}): {text[:80]!r}")
    assert not found, "a terminal line in Spanish (constitution 2.12.0):\n" + "\n".join(found)


def test_every_family_facing_exclusion_covers_spanish() -> None:
    """An exclusion that covers nothing would hide the next Spanish line put under that name."""
    covered: set[str] = set()
    for module, path in _modules():
        for where, _, _ in _spanish_literals(module, ast.parse(path.read_text())):
            covered |= {name for name in FAMILY_FACING if where == name or where.startswith(name + ".")}
    assert sorted(set(FAMILY_FACING) - covered) == []


def test_the_spanish_detector_sees_the_lines_it_replaced() -> None:
    """The detector is not blind: the summaries #261 moved to English read as Spanish to it."""
    for text in ("sin cambios", "carpeta del curso compartida con 1 cuenta(s)", "agenda actualizada", "1 sin traer"):
        assert _SPANISH.search(text), text
    for text in ("no changes", "agenda: 2 in «Pendiente»", "school-year folder shared with 1 account(s)", "en"):
        assert not _SPANISH.search(text), text


_LINE = re.compile(r"^alfabeta: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2} \S")


def _writes_stderr(tree: ast.AST) -> list[int]:
    """Lines that reach `sys.stderr` by hand: `print(..., file=sys.stderr)`, `sys.stderr.write(...)`."""
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and node.attr == "stderr"
        and isinstance(node.value, ast.Name)
        and node.value.id == "sys"
    ]


def test_only_the_output_module_writes_to_stderr() -> None:
    found = [
        f"{path.relative_to(ROOT)}:{line}"
        for module, path in _modules()
        if module != output.__name__
        for line in _writes_stderr(ast.parse(path.read_text()))
    ]
    assert not found, "a line for people that bypasses alfabeta.output (no time on it):\n" + "\n".join(found)


def test_a_line_carries_the_madrid_time() -> None:
    noon_utc = dt.datetime(2026, 11, 18, 16, 5, 3, tzinfo=dt.UTC)
    assert output.line("✓ signed in", now=noon_utc) == "alfabeta: 2026-11-18T17:05:03 ✓ signed in"


_ARGS = {"reason": "probe", "code": 1, "message": "probe"}


def _helpers() -> list[tuple[str, str]]:
    """Each module's stderr helper: every module-level `_say` or `_fail`, derived from the source.

    A `_say` that takes more than a message (`classroom.refresh._say(deps, line)`) hands its line
    to an injected writer, the command module's own helper, which is gated here.
    """
    found: list[tuple[str, str]] = []
    for module, path in _modules():
        tree = ast.parse(path.read_text())
        defined = {
            n.name for n in tree.body if isinstance(n, ast.FunctionDef) and {a.arg for a in n.args.args} <= set(_ARGS)
        }
        imported = {a.asname or a.name for n in tree.body if isinstance(n, ast.ImportFrom) for a in n.names}
        found += [(module, name) for name in ("_say", "_fail") if name in defined | imported]
    return found


@pytest.mark.parametrize(("module", "helper"), _helpers())
def test_every_line_for_people_carries_the_time(module: str, helper: str, capsys: pytest.CaptureFixture[str]) -> None:
    fn = getattr(importlib.import_module(module), helper)
    params = inspect.signature(fn).parameters
    fn(**{name: _ARGS[name] for name in params})
    err = capsys.readouterr().err.splitlines()
    assert err and all(_LINE.match(line) for line in err), err


def test_the_helpers_are_found() -> None:
    """The parametrized gate above is not empty: the command modules' helpers are there."""
    modules = {module for module, _ in _helpers()}
    assert {"alfabeta.__main__", "alfabeta.notes.cli", "alfabeta.exam.cli", "alfabeta.classroom.cli"} <= modules
