"""`exam prep --student <id> --subject <folder> [--exam] [--slot] [--topic]...` (spec 002 contracts/cli.md).

JSON on stdout, messages for people on stderr; no message names an address, a Drive id, a notebook
id or an absolute path. Exit codes: 0 ok · 1 usage or validation, and the refusals `notebook_disabled`,
`no_exam`, `no_announcement`, `no_notebook`, `subtopics_unnamed` · 3 a step from 5 on failed · 5 `nlm` is not usable.
Steps 1 to 4 refuse before the notebook is asked for anything, and then nothing is printed.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
import time
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from alfabeta import config, decisions
from alfabeta.exam import prompts
from alfabeta.exam.drive import DriveLivingNotes
from alfabeta.exam.nlm import NlmError, NlmNotebook
from alfabeta.exam.prep import (
    EXIT_INVALID,
    EXIT_NLM,
    EXIT_OK,
    EXIT_PARTIAL,
    SOLUTIONS,
    Exam,
    ExamDeps,
    ExamPrep,
    Refusal,
    Sheet,
    Slot,
    find_exam,
    topic_folders,
)
from alfabeta.exam.printing import PrintPack, refresh_mirrors
from alfabeta.notes.run import topic_name

if TYPE_CHECKING:
    import argparse
    from collections.abc import Callable
    from pathlib import Path

    from alfabeta.google.keychain import TokenStore

MADRID = ZoneInfo("Europe/Madrid")
NLM_MESSAGES = {
    "no_nlm": "nlm cannot be run here: install it, then sign in with `nlm login --profile <profile>`",
    "nlm_signed_out": "nlm is not signed in for notebook.nlm_profile: run `nlm login --profile <profile>`",
    "nlm_failed": "nlm failed while checking its session; nothing was asked or printed",
}


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def _fail(reason: str, code: int, message: str) -> int:
    print(f"alfabeta: {message}", file=sys.stderr)
    _emit({"ok": False, "reason": reason})
    return code


def exam_deps(cfg: config.StudentConfig, store: TokenStore) -> ExamDeps:
    """The real ports: `nlm`, the student's Drive, `print_pack.py`, rsync, the clock."""
    return ExamDeps(
        notebook=NlmNotebook(cfg.nlm_profile),
        living=DriveLivingNotes(cfg, store),
        printer=PrintPack(cfg.nlm_profile),
        mirrors=lambda: refresh_mirrors(cfg.base, cfg.mirrors),
        sleep=time.sleep,
        now=lambda: dt.datetime.now(MADRID),
    )


def _sheets(cfg: config.StudentConfig, subject: str, language: str, exam: Exam, slot: Slot) -> tuple[Sheet, Sheet]:
    values = {
        "grade": cfg.grade_level,
        "language": language,
        "subject": subject,
        "exam_day": prompts.exam_day(exam.day),
        "scope": exam.announcement,
        "scope_date": prompts.day_month(exam.announced),
        "slot": slot.words,
        "pages": str(slot.pages),
    }
    return (
        Sheet("theory", "Teoría para el examen", prompts.fill(prompts.template(prompts.THEORY), values)),
        Sheet("problems", "Problemas tipo", prompts.fill(prompts.template(prompts.PROBLEMS), values), SOLUTIONS),
    )


def cmd_exam_prep(
    home: Path,
    args: argparse.Namespace,
    store: TokenStore,
    factory: Callable[[config.StudentConfig, TokenStore], ExamDeps] | None = None,
    today: Callable[[], dt.date] = decisions.today,
) -> int:
    """`exam prep`: steps 1 to 4 here, 5 to 9 in `ExamPrep`."""
    # 1. The configuration, as `config check` reads it; notebooks may be switched off.
    problems, warnings = config.check(home, args.student)
    for warning in warnings:
        print(f"alfabeta: warning: {warning.key}: {warning.reason}", file=sys.stderr)
    for problem in problems:
        print(f"alfabeta: {problem.key}: {problem.reason}", file=sys.stderr)
    if problems:
        return _fail("invalid_config", EXIT_INVALID, "the configuration is not valid; nothing was asked or printed")
    cfg = config.load_all(home, args.student)
    if not cfg.notebook_enabled:
        return _fail(
            "notebook_disabled",
            EXIT_INVALID,
            "notebooks are switched off (notebook.enabled); nothing was asked or printed",
        )
    subject = next((s for s in cfg.subjects if s.folder == args.subject), None)
    if subject is None:
        return _fail("no_subject", EXIT_INVALID, "--subject is not the folder of a configured subject")
    try:
        slot = Slot.parse(args.slot)
        language = prompts.language_words(subject.language)
    except Refusal as refusal:
        return _fail(refusal.reason, EXIT_INVALID, str(refusal))
    except prompts.PromptError as err:
        return _fail("unknown_language", EXIT_INVALID, f"the subject's language: {err}")
    deps = (factory or exam_deps)(cfg, store)

    # 2. `nlm` signed in for the profile, and that profile is the one `nlm download` reads.
    try:
        deps.notebook.check_session()
        if deps.notebook.default_profile() != cfg.nlm_profile:
            return _fail(
                "nlm_not_default",
                EXIT_NLM,
                "nlm download reads nlm's default profile, which is not notebook.nlm_profile:"
                " run `nlm config set auth.default_profile <profile>`",
            )
    except NlmError as err:
        return _fail(err.reason, EXIT_NLM, NLM_MESSAGES.get(err.reason, NLM_MESSAGES["nlm_failed"]))

    # 3 and 4. The exam and its announcement; each topic and its notebook, before any is asked.
    year = cfg.base / cfg.school_year
    try:
        exam = find_exam(
            year / "agenda.json", cfg.data_dir / "state.json", cfg.base, subject.folder, args.exam, today()
        )
        folders = topic_folders(year / subject.folder, args.topic)
    except Refusal as refusal:
        return _fail(refusal.reason, EXIT_INVALID, str(refusal))
    if not args.topic:
        print(f"alfabeta: the exam's topic is the subject's most recent one: {folders[0].name}", file=sys.stderr)
    notebooks: list[str] = []
    for folder in folders:
        title = cfg.notebook_title_pattern.format(
            grade=cfg.grade_level, subject=subject.folder, topic=topic_name(folder.name)
        )
        try:
            notebook = deps.notebook.find_notebook(title)
        except NlmError as err:
            return _fail(err.reason, EXIT_NLM, NLM_MESSAGES.get(err.reason, NLM_MESSAGES["nlm_failed"]))
        if notebook is None:
            return _fail(
                "no_notebook", EXIT_INVALID, f"{folder.name} has no notebook titled as notebook.title_pattern names it"
            )
        notebooks.append(notebook)
    try:
        start = prompts.template(prompts.START_NOTE)
        # The slot is shared in equal parts among the subtopics, in their order (FR-045).
        parts = [(part, _sheets(cfg, subject.folder, language, exam, part)) for part in slot.share(len(folders))]
    except prompts.PromptError as err:
        return _fail("invalid_prompt", EXIT_INVALID, f"prompts.md: {err}")

    listed = sorted(p.name for p in folders[0].parent.iterdir() if p.is_dir())
    topics: list[dict[str, Any]] = []
    partial = False
    for folder, notebook, (part, sheets) in zip(folders, notebooks, parts, strict=True):
        prep = ExamPrep(
            deps=deps,
            data_dir=cfg.data_dir,
            base=cfg.base,
            subject=subject.folder,
            folder=folder,
            notebook=notebook,
            exam=exam,
            slot=part,
            sheets=sheets,
            start_note=lambda theory, part=part: prompts.fill(
                start, {"exam_day": prompts.exam_day(exam.day), "theory": theory, "slot": part.words}
            ),
        )
        outcome = prep.run()
        outcome.pop("exam_date")
        topics.append({"topic": listed.index(folder.name), **outcome})
        partial = partial or prep.partial
    _emit({"ok": not partial, "exam_date": exam.day.isoformat(), "topics": topics})
    return EXIT_PARTIAL if partial else EXIT_OK
