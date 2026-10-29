"""The `python -m alfabeta` command (spec 001 contracts/cli.md; spec 004 contracts/cli.md).

JSON for machines on stdout, messages for people on stderr. No output names an address, a token or
an absolute path; accounts are named by alias.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
import sys
import webbrowser
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo

from alfabeta import (
    __version__,
    agenda,
    anonymize,
    book,
    config,
    decisions,
    downloads,
    guardrail,
    plan,
    replicas,
    sandbox,
    sources,
    state,
)
from alfabeta.classification import CANDIDATE, Classifier
from alfabeta.exam import cli as exam_cli
from alfabeta.google import accounts, calendar
from alfabeta.google.keychain import KeychainStore
from alfabeta.google.notify import MacNotifier
from alfabeta.google.transport import UrllibTransport
from alfabeta.model import AgendaCategory, AgendaList, DecisionType, RunMode, StopReason
from alfabeta.notes import cli as notes_cli
from alfabeta.notes import refresh

MADRID = ZoneInfo("Europe/Madrid")
PROBE_SUMMARY = "Prueba alfabeta · ignorar"

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_LINK = 2


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def _fail(reason: str, code: int, message: str) -> int:
    print(f"alfabeta: {message}", file=sys.stderr)
    _emit({"ok": False, "reason": reason})
    return code


# The configuration tables each command group reads; the others are not validated for it.
TABLES = {
    "google": ("classroom", "google"),
    "calendar": ("classroom", "calendar", "google"),
    "notes": ("google", "drive", "notes"),
    "notebook": ("student", "google", "drive", "notes", "notebook"),
}
# `notebook agent` reads only the clone it runs and the refresh interval (spec 005 T046).
AGENT_TABLES = ("tools", "notebook")


def _cmd_config_check(home: Path, student: str) -> int:
    problems, warnings = config.check(home, student)
    for warning in warnings:
        print(f"alfabeta: warning: {warning.key}: {warning.reason}", file=sys.stderr)
    for problem in problems:
        print(f"alfabeta: {problem.key}: {problem.reason}", file=sys.stderr)
    _emit(
        {
            "ok": not problems,
            "problems": [p.as_json() for p in problems],
            "warnings": [w.as_json() for w in warnings],
        }
    )
    return EXIT_INVALID if problems else EXIT_OK


# Reasons a skill may give `log stop`; `idle` is the watcher's own (contracts/cli.md).
LOG_STOP_REASONS = tuple(r for r in StopReason if r != StopReason.IDLE)


def _lock(home: Path, student: str) -> state.Lock:
    return state.Lock(home, config.student_root(home, student) / "data")


def _cmd_lock(args: argparse.Namespace, home: Path) -> int:
    lock = _lock(home, args.student)
    run = os.environ.get(state.RUN_ENV)
    try:
        if args.verb == "take":
            mode = RunMode(args.mode)
            try:
                idle = config.load(home, args.student, ("sync",)).lock_idle_minutes
            except config.ConfigError as err:
                line = state.stopped_line(None, StopReason.INVALID_CONFIG) | {"mode": str(mode)}
                state.StateStore(lock.data_dir).log(line)
                return _fail(str(StopReason.INVALID_CONFIG), EXIT_INVALID, str(err))
            _emit({"ok": True, "run": lock.take(mode, idle)})
        elif args.verb == "renew":
            lock.renew(run)
            _emit({"ok": True})
        else:
            lock.release(run)
            _emit({"ok": True})
    except state.LockError as err:
        return _fail(str(err.reason), EXIT_INVALID, str(err))
    return EXIT_OK


def _cmd_log_stop(args: argparse.Namespace, home: Path) -> int:
    if args.reason not in LOG_STOP_REASONS:
        return _fail("invalid_reason", EXIT_INVALID, f"--reason must be one of: {', '.join(LOG_STOP_REASONS)}")
    lock = _lock(home, args.student)
    run = os.environ.get(state.RUN_ENV)
    lease = lock.lease()
    state.StateStore(lock.data_dir).log(state.stopped_line(run, StopReason(args.reason), lease))
    if run and lease is not None and lease.get("run") == run:
        # The watcher may already have let go; the line is written either way.
        with contextlib.suppress(state.LockError):
            lock.release(run)
    _emit({"ok": True})
    return EXIT_OK


def _cmd_log_notebook(args: argparse.Namespace, home: Path) -> int:
    lock = _lock(home, args.student)
    run = os.environ.get(state.RUN_ENV)
    try:
        line = book.notebook_line(
            run, dt.datetime.now(MADRID).isoformat(), args.topic, args.result, args.reason, args.shares
        )
        lock.renew(run)
    except book.BookError as err:
        return _fail(err.reason, EXIT_INVALID, str(err))
    except state.LockError as err:
        return _fail(str(err.reason), EXIT_INVALID, str(err))
    config.load_all(home, args.student)
    state.StateStore(lock.data_dir).log(line)
    _emit({"ok": True})
    return EXIT_OK


def _cmd_book_place(args: argparse.Namespace, home: Path) -> int:
    lock = _lock(home, args.student)
    run = os.environ.get(state.RUN_ENV)
    try:
        lock.renew(run)
    except state.LockError as err:
        return _fail(str(err.reason), EXIT_INVALID, str(err))
    cfg = config.load_all(home, args.student)
    if not cfg.base.is_dir():
        return _fail(
            str(StopReason.DRIVE_NOT_MOUNTED), EXIT_INVALID, "the base folder is not there; nothing was written"
        )
    store = state.StateStore(lock.data_dir)
    current = store.load()
    try:
        subject = book.book_subject(cfg.subjects, args.subject)
        topic, number = book.book_topic(args.topic)
        origin = Path(args.origin).expanduser()
        if not origin.is_dir():
            raise book.BookError("no_origin", "the origin folder is not there")
    except book.BookError as err:
        return _fail(err.reason, EXIT_INVALID, str(err))
    placer = book.BookPlacer(cfg.base, cfg.school_year, subject, json.loads(json.dumps(current)), decisions.today())
    line: dict[str, Any] = {
        "type": "book",
        "at": dt.datetime.now(MADRID).isoformat(),
        "run": run,
        "source": subject.book,
        "subject": subject.folder,
        "topic": topic,
    }
    try:
        folder = placer.place(sources.BookSource(subject.book, origin=origin), topic, number)
    except book.BookError as err:
        return _fail(err.reason, EXIT_INVALID, str(err))
    except OSError:
        # What was copied before the failure is recorded, so the next run finds it (constitution VII).
        if placer.state != current:
            store.save(placer.state)
        store.log(line | {"result": "failed", "reason": "write_failed", "placed": len(placer.placed)})
        return _fail("write_failed", EXIT_INVALID, "a file could not be written in the base folder; run it again")
    if placer.state != current:
        store.save(placer.state)
    mirrors = book.refresh(cfg.base, cfg.mirrors)
    result = "placed" if placer.placed else "unchanged"
    store.log(line | {"result": result, "mirrors": mirrors})
    print(
        f"alfabeta: libro en {folder}: {len(placer.placed)} colocados, {len(placer.unchanged)} sin cambios",
        file=sys.stderr,
    )
    if placer.previous:
        print(f"alfabeta: versiones anteriores guardadas: {len(placer.previous)}", file=sys.stderr)
    if cfg.mirrors:
        print(f"alfabeta: espejos al día: {mirrors['up_to_date']}, fallidos: {mirrors['failed']}", file=sys.stderr)
    _emit(
        {
            "ok": True,
            "result": result,
            "folder": folder,
            "placed": placer.placed,
            "unchanged": placer.unchanged,
            "previous": placer.previous,
            "mirrors": mirrors,
        }
    )
    return EXIT_OK


def _cmd_decisions(args: argparse.Namespace, home: Path) -> int:
    lock = _lock(home, args.student)
    on = decisions.today()
    try:
        lock.renew(os.environ.get(state.RUN_ENV))
        store = decisions.DecisionStore.open(lock.data_dir)
        if args.verb == "propose":
            try:
                raw = json.loads(Path(args.file).read_text())
            except (OSError, ValueError):
                return _fail("invalid_proposal", EXIT_INVALID, "the proposals file is not readable JSON")
            items: list[object] = cast("list[object]", raw) if isinstance(raw, list) else [raw]
            proposals = [decisions.Proposal.parse(p, on) for p in items]
            recorded, ignored = store.propose(proposals, on)
            store.save()
            _emit(
                {
                    "ok": True,
                    "recorded": [{"type": str(d.type), "origin": d.origin} for d in recorded],
                    "ignored": [{"type": str(d.type), "origin": d.origin} for d in ignored],
                }
            )
            return EXIT_OK
        kind = DecisionType(args.type) if getattr(args, "type", None) else DecisionType.DETECTED_EXAM
        if args.verb == "confirm":
            decision = store.confirm(kind, args.origin, on, reject=args.reject)
        elif args.verb == "correct":
            target = (
                {"date": args.date}
                if args.date
                else {"category": args.category}
                if args.category
                else {"discarded": "true"}
            )
            decision = store.correct(args.origin, target, on)
        else:
            key = "subject" if kind == DecisionType.CLASS_LINK else "topic"
            decision = store.change(kind, args.origin, {key: args.target}, on)
        store.save()
        _emit({"ok": True, "type": str(decision.type), "origin": decision.origin, "state": str(decision.state)})
    except state.LockError as err:
        return _fail(str(err.reason), EXIT_INVALID, str(err))
    except decisions.DecisionError as err:
        return _fail("invalid_decision", EXIT_INVALID, str(err))
    return EXIT_OK


def _cmd_plan(args: argparse.Namespace, home: Path) -> int:
    lock = _lock(home, args.student)
    run = os.environ.get(state.RUN_ENV)
    try:
        lease = lock.renew(run)
    except state.LockError as err:
        return _fail(str(err.reason), EXIT_INVALID, str(err))
    cfg = config.load_all(home, args.student)
    store = decisions.DecisionStore.open(lock.data_dir)
    planner = plan.Planner(
        school_year=cfg.school_year,
        subjects=cfg.subjects,
        base=cfg.base,
        decisions=store,
        state=state.StateStore(lock.data_dir).load(),
        full_review_days=cfg.full_review_days,
        today=decisions.today(),
        classifier=Classifier(cfg.languages),
        last_review=plan.last_full_review(lock.data_dir / "log.jsonl"),
        data_dir=lock.data_dir,
    )
    if args.subject:
        wanted = set(args.subject)
        scope = [c for c, s in planner.linked_classes().items() if s.folder in wanted]
    else:
        scope = list(lease.get("classes", []))
    try:
        result = planner.plan(plan.latest_captures(lock.data_dir / "captures"), scope, str(run))
    except plan.PlanError as err:
        state.StateStore(lock.data_dir).log(state.stopped_line(run, StopReason(err.reason), lease))
        with contextlib.suppress(state.LockError):
            lock.release(run)
        return _fail(err.reason, EXIT_INVALID, str(err))
    plan.write(result, lock.data_dir)
    _emit(result)
    return EXIT_OK


def _summary(
    applier: replicas.Applier, pending: list[dict[str, Any]], stopped: dict[str, str], agenda_written: list[str]
) -> list[str]:
    """What the family reads after a sync, in Spanish (T043, FR-008).

    An agenda rewritten because an entry changed list is a change too (FR-025), never «sin cambios».
    """
    if not (
        applier.added
        or applier.changed
        or applier.not_fetched
        or applier.withdrawn
        or pending
        or stopped
        or applier.unknown_statuses
        or agenda_written
    ):
        return ["sin cambios"]
    lines = [f"{applier.added} nuevos, {applier.changed} cambiados, {len(applier.not_fetched)} sin traer"]
    lines += [f"retirado de Classroom: {title}" for title in applier.withdrawn]
    unlinked = [p for p in pending if p["type"] == "class_link" and p.get("visibility") == "visible"]
    hidden = [p for p in pending if p["type"] == "class_link" and p.get("visibility") != "visible"]
    matches = [p for p in pending if p["type"] == "topic_match"]
    exams = [p for p in pending if p["type"] == CANDIDATE]
    if unlinked:
        lines.append("clases sin vincular: " + ", ".join(str(p["title"]) for p in unlinked))
    if hidden:
        lines.append(f"clases ocultas o archivadas: {len(hidden)}")
    if matches:
        lines.append(f"temas por confirmar: {len(matches)}")
    if exams:
        lines.append(f"posibles exámenes por revisar: {len(exams)}")
    if agenda_written:
        lines.append("agenda actualizada")
    if applier.unknown_statuses:
        lines.append(f"estados desconocidos: {applier.unknown_statuses}")
    if applier.unreadable:
        lines.append(f"capturas ilegibles: {len(applier.unreadable)}")
    lines += [f"clase sin aplicar: {reason}" for reason in stopped.values()]
    return lines


def _cmd_apply(args: argparse.Namespace, home: Path) -> int:
    lock = _lock(home, args.student)
    run = os.environ.get(state.RUN_ENV)
    try:
        lease = lock.renew(run)
    except state.LockError as err:
        return _fail(str(err.reason), EXIT_INVALID, str(err))
    cfg = config.load_all(home, args.student)
    store_log = state.StateStore(lock.data_dir)
    if not cfg.base.is_dir():
        store_log.log(state.stopped_line(run, StopReason.DRIVE_NOT_MOUNTED, lease))
        with contextlib.suppress(state.LockError):
            lock.release(run)
        return _fail(
            str(StopReason.DRIVE_NOT_MOUNTED), EXIT_INVALID, "the base folder is not there; nothing was written"
        )
    store = decisions.DecisionStore.open(lock.data_dir)
    links = plan.linked_classes(store, cfg.subjects)
    plan_path = lock.data_dir / "plan.json"
    planned: dict[str, Any] = json.loads(plan_path.read_text()) if plan_path.is_file() else {}
    if planned.get("applied_at"):  # applying again is not a new plan: no downloads, no full review
        planned = {"pending_decisions": planned.get("pending_decisions", [])}
    current = store_log.load()
    applier = replicas.Applier(
        base=cfg.base,
        data_dir=lock.data_dir,
        school_year=cfg.school_year,
        subjects=list(cfg.subjects),
        decisions=store,
        state=json.loads(json.dumps(current)),
        today=decisions.today(),
        downloads=[*planned.get("downloads", []), *planned.get("already_collected", [])],
    )
    if args.subject:
        scope = [c for c, s in links.items() if s.folder in set(args.subject)]
    else:
        scope = list(lease.get("classes", []))
    stopped = plan.run_stops(lock.data_dir / "captures", str(run))
    captures = plan.latest_captures(lock.data_dir / "captures")
    applied = applier.apply(captures, [c for c in scope if c not in stopped], links)
    if applier.state != current:
        store_log.save(applier.state)
    if "created_at" in planned and set(planned.get("classes", [])) <= set(applied) | set(stopped):
        # Every class it planned is placed: the next run's first collect must not wait for any of it.
        plan.write(planned | {"applied_at": dt.datetime.now(MADRID).isoformat()}, lock.data_dir)
    plan.prune_captures(lock.data_dir / "captures", cfg.kept_captures)
    # Whatever the scope, the school year's agenda from the state just saved (contracts/cli.md, apply).
    agenda_written = _agenda_builder(cfg, lock.data_dir, applier.state).write(cfg.base)
    partial = bool(stopped)
    line = {
        "run": run,
        "started_at": lease.get("started_at"),
        "ended_at": dt.datetime.now(MADRID).isoformat(),
        "mode": lease.get("mode"),
        "result": "partial" if partial else "ok",
        "reason": next(iter(stopped.values())) if partial else None,
        "account_index": captures["classes"]["account_index"] if "classes" in captures else None,
        "classes": applied,
        "added": applier.added,
        "changed": applier.changed,
        "withdrawn": len(applier.withdrawn),
        "not_fetched": applier.not_fetched,
        "unknown_statuses": applier.unknown_statuses,
        "pending_decisions": len(planned.get("pending_decisions", [])),
        "full_review": bool(planned.get("full_review")),
    }
    store_log.log(line)
    for text in _summary(applier, list(planned.get("pending_decisions", [])), stopped, agenda_written):
        print(f"alfabeta: {text}", file=sys.stderr)
    _emit(
        {k: line[k] for k in ("result", "reason", "added", "changed", "withdrawn", "unknown_statuses")}
        | {"not_fetched": len(applier.not_fetched)}
    )
    return EXIT_OK


def _agenda_builder(cfg: config.StudentConfig, data_dir: Path, current: dict[str, Any]) -> agenda.AgendaBuilder:
    """The agenda of `current` (the state), with the decisions in force and the newest captures."""
    store = decisions.DecisionStore.open(data_dir)
    return agenda.AgendaBuilder(
        school_year=cfg.school_year,
        links=plan.linked_classes(store, cfg.subjects),
        classifier=Classifier(cfg.languages),
        decisions=store.decisions(),
        state=current,
        captured=agenda.capture_instants(plan.latest_captures(data_dir / "captures")),
        notices=refresh.agenda_notices(data_dir),  # spec 005 FR-019, while the owner's session fails
    )


def _cmd_agenda(args: argparse.Namespace, home: Path) -> int:
    lock = _lock(home, args.student)
    try:
        lock.renew(os.environ.get(state.RUN_ENV))
    except state.LockError as err:
        return _fail(str(err.reason), EXIT_INVALID, str(err))
    cfg = config.load_all(home, args.student)
    if not cfg.base.is_dir():
        return _fail(
            str(StopReason.DRIVE_NOT_MOUNTED), EXIT_INVALID, "the base folder is not there; nothing was written"
        )
    builder = _agenda_builder(cfg, lock.data_dir, state.StateStore(lock.data_dir).load())
    written = builder.write(cfg.base)
    counts = builder.counts()
    print(
        f"alfabeta: agenda: {counts[AgendaList.PENDING]} en «Pendiente», {counts[AgendaList.DONE]} en «Hecho», "
        f"{counts[AgendaList.POSTED]} en «Publicado»",
        file=sys.stderr,
    )
    print(f"alfabeta: {'escrita: ' + ', '.join(written) if written else 'sin cambios'}", file=sys.stderr)
    _emit({"written": written})
    return EXIT_OK


def _cmd_collect(args: argparse.Namespace, home: Path) -> int:
    lock = _lock(home, args.student)
    run = os.environ.get(state.RUN_ENV)
    try:
        lock.renew(run)
        cfg = config.load(home, args.student, ("downloads",))
        inbox = downloads.DownloadsInbox(Path(cfg.downloads_folder).expanduser(), lock.data_dir)
        result = downloads.collect(inbox, str(run), args.wait)
        lock.record_classes(run, result["classes"])
    except state.LockError as err:
        return _fail(str(err.reason), EXIT_INVALID, str(err))
    _emit({"collected": result["collected"], "pending": result["pending"], "classes": result["classes"]})
    return EXIT_INVALID if result["pending"] else EXIT_OK


def _cmd_sandbox(args: argparse.Namespace) -> int:
    try:
        home = sandbox.require_explicit_home(args.home)
        if args.verb == "prepare":
            home.mkdir(parents=True, exist_ok=True)
            sandbox.prepare(home, args.student)
            _emit({"ok": True, "student": args.student})
        elif args.captures:
            _emit({"ok": True, "written": sandbox.download_captures(home, args.student, os.environ.get(state.RUN_ENV))})
        else:
            _emit({"ok": True, "written": sandbox.download_batch(home, args.student, args.batch)})
    except (sandbox.SandboxError, config.ConfigError) as err:
        return _fail("invalid_sandbox", EXIT_INVALID, str(err))
    return EXIT_OK


def _student_account(cfg: config.StudentConfig) -> str:
    for alias, account in sorted(cfg.accounts.items()):
        if account.role == "student":
            return alias
    raise config.ConfigError("no linked account with role 'student'")


def _cmd_client_set(args: argparse.Namespace, store: KeychainStore) -> int:
    try:
        accounts.set_client(store, args.student, Path(args.from_file).expanduser())
    except accounts.LinkError as err:
        return _fail(err.reason, EXIT_INVALID, "the file is not a Desktop client downloaded from Google")
    print("alfabeta: client stored in the keychain; delete the downloaded file now.", file=sys.stderr)
    _emit({"ok": True})
    return EXIT_OK


def _cmd_link(args: argparse.Namespace, cfg: config.StudentConfig, store: KeychainStore) -> int:
    print(f"alfabeta: opening Google's sign-in for account '{args.account}'…", file=sys.stderr)
    try:
        scopes = accounts.link_account(cfg, args.account, store, UrllibTransport(), webbrowser.open, dt.date.today())
    except accounts.LinkError as err:
        return _fail(err.reason, EXIT_INVALID, f"linking '{args.account}' failed: {err.reason}; nothing was stored")
    _emit({"ok": True, "alias": args.account, "scopes": list(scopes)})
    return EXIT_OK


def _cmd_check(cfg: config.StudentConfig, store: KeychainStore) -> int:
    statuses = accounts.check_accounts(cfg, store, UrllibTransport(), dt.date.today(), MacNotifier())
    for status in statuses:
        hint = " (the app may still be in Testing: publish it)" if status.testing_suspected else ""
        print(f"alfabeta: {status.alias}: {status.status}{hint}", file=sys.stderr)
    all_ok = all(s.status == "ok" for s in statuses)
    _emit({"ok": all_ok, "accounts": [{"alias": s.alias, "status": s.status} for s in statuses]})
    return EXIT_OK if all_ok else EXIT_LINK


def _cmd_unlink(args: argparse.Namespace, cfg: config.StudentConfig, store: KeychainStore) -> int:
    accounts.unlink_account(cfg, args.account, store, UrllibTransport())
    _emit({"ok": True})
    return EXIT_OK


def _calendar_client(cfg: config.StudentConfig, store: KeychainStore) -> calendar.CalendarClient:
    transport = UrllibTransport()
    token = accounts.access_token(cfg, _student_account(cfg), store, transport)
    return calendar.CalendarClient(transport, token, cfg.calendar_id)


def _cmd_probe(args: argparse.Namespace, cfg: config.StudentConfig, store: KeychainStore) -> int:
    try:
        client = _calendar_client(cfg, store)
    except accounts.LinkError as err:
        return _fail(err.reason, EXIT_LINK, f"the student's link is not usable: {err.reason}")
    now = dt.datetime.now(MADRID).replace(second=0, microsecond=0)
    start = now + dt.timedelta(minutes=args.minutes)
    spec = calendar.EventSpec(
        summary=PROBE_SUMMARY,
        start=start.strftime("%Y-%m-%dT%H:%M:%S"),
        end=(start + dt.timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%S"),
        reminder_minutes=(0,),
        description="Prueba de notificaciones de alfabeta. Se borra después.",
    )
    eid = calendar.event_id(f"probe-{now.isoformat()}")
    client.insert(eid, spec)
    readback = client.get(eid) or {}
    _emit({"ok": True, "event": eid, "start": spec.start, "reminders": readback.get("reminders")})
    return EXIT_OK


def _cmd_probe_clean(args: argparse.Namespace, cfg: config.StudentConfig, store: KeychainStore) -> int:
    try:
        client = _calendar_client(cfg, store)
    except accounts.LinkError as err:
        return _fail(err.reason, EXIT_LINK, f"the student's link is not usable: {err.reason}")
    client.delete(args.event)
    _emit({"ok": True})
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    """The command's arguments."""
    parser = argparse.ArgumentParser(prog="alfabeta")
    parser.add_argument("--version", action="version", version=f"alfabeta {__version__}")
    parser.add_argument("--home", help="folder of student configurations (default ~/.alfabeta)")
    groups = parser.add_subparsers(dest="group", required=True)

    google = groups.add_parser("google", help="alfabeta's own Google connection").add_subparsers(
        dest="verb", required=True
    )
    client_set = google.add_parser("client", help="the app's OAuth client").add_subparsers(dest="action", required=True)
    setter = client_set.add_parser("set", help="store the Desktop client JSON in the keychain")
    setter.add_argument("--from", dest="from_file", required=True)
    link = google.add_parser("link", help="link an account through Google's sign-in")
    link.add_argument("--account", required=True)
    google.add_parser("check", help="refresh and report every linked account")
    unlink = google.add_parser("unlink", help="revoke an account's link")
    unlink.add_argument("--account", required=True)

    plan_cmd = groups.add_parser("plan", help="what this run downloads, places and asks")
    plan_cmd.add_argument("--subject", action="append", default=[])
    apply_cmd = groups.add_parser("apply", help="place what this run collected in the student's base folder")
    apply_cmd.add_argument("--subject", action="append", default=[])
    agenda_cmd = groups.add_parser("agenda", help="regenerate agenda.json and agenda.md, only if they change")
    dl = groups.add_parser("downloads", help="the browser's downloads folder").add_subparsers(
        dest="verb", required=True
    )
    collect = dl.add_parser("collect", help="move this run's captures and the planned attachments to data/")
    collect.add_argument("--wait", type=int, default=0)

    dec = groups.add_parser("decisions", help="Claude's proposals and the family's decisions").add_subparsers(
        dest="verb", required=True
    )
    propose = dec.add_parser("propose", help="record Claude's proposals from a JSON file")
    propose.add_argument("--file", required=True)
    confirm = dec.add_parser("confirm", help="confirm or reject a proposal")
    confirm.add_argument("--type", required=True, choices=[str(t) for t in decisions.PROPOSABLE])
    confirm.add_argument("--origin", required=True)
    confirm.add_argument("--reject", action="store_true")
    correct = dec.add_parser("correct", help="correct a detected exam")
    correct.add_argument("--origin", required=True)
    fix = correct.add_mutually_exclusive_group(required=True)
    fix.add_argument("--date", type=lambda v: dt.date.fromisoformat(v).isoformat())
    fix.add_argument("--category", choices=[str(c) for c in AgendaCategory])
    fix.add_argument("--discard", action="store_true")
    change = dec.add_parser("change", help="change a confirmed or rejected match")
    change.add_argument("--type", required=True, choices=[str(t) for t in decisions.PROPOSABLE])
    change.add_argument("--origin", required=True)
    change.add_argument("--target", required=True)

    box = groups.add_parser("sandbox", help="an invented student to try a run").add_subparsers(
        dest="verb", required=True
    )
    box_prepare = box.add_parser("prepare", help="create the invented student in an explicit --home")
    box_prepare.add_argument("--student", default=sandbox.DEFAULT_STUDENT)
    box_download = box.add_parser("download", help="copy the sandbox captures to the downloads folder")
    box_download.add_argument("--student", required=True)
    what = box_download.add_mutually_exclusive_group()
    what.add_argument("--captures", action="store_true")
    what.add_argument("--batch", type=int, default=0)

    anon = groups.add_parser("anonymize", help="a synthetic page from a saved Classroom page")
    anon.add_argument("input")
    anon.add_argument("output")

    guard = groups.add_parser("guardrail", help="look for personal data before it is published")
    scope = guard.add_mutually_exclusive_group()
    scope.add_argument("--staged", dest="scope", action="store_const", const="staged", help="the staged change")
    scope.add_argument("--all", dest="scope", action="store_const", const="all", help="every tracked file")
    scope.add_argument("--history", dest="scope", action="store_const", const="history", help="every published commit")
    guard.set_defaults(scope="staged")

    lock = groups.add_parser("lock", help="the run's lock").add_subparsers(dest="verb", required=True)
    take = lock.add_parser("take", help="start a run and hold the student's and the browser's lock")
    take.add_argument("--mode", required=True, choices=[str(m) for m in RunMode])
    renew = lock.add_parser("renew", help="renew the lock of the run in ALFABETA_RUN")
    release = lock.add_parser("release", help="release the lock of the run in ALFABETA_RUN")
    log = groups.add_parser("log", help="the run log").add_subparsers(dest="verb", required=True)
    stop = log.add_parser("stop", help="write the stopped line of a run halted before apply")
    stop.add_argument("--reason", required=True)
    log_notebook = log.add_parser("notebook", help="write the line of a book topic's notebook step")
    log_notebook.add_argument("--topic", required=True, help="Tema NN - <title>")
    log_notebook.add_argument("--result", required=True, help=", ".join(book.NOTEBOOK_RESULTS))
    log_notebook.add_argument("--reason", help="short, without student data; required with failed")
    log_notebook.add_argument("--shares", help="<invited>,<already>,<failed>: counts over [notebook] share_with")
    book_group = groups.add_parser("book", help="a book provider's result (spec 001 US4)").add_subparsers(
        dest="verb", required=True
    )
    book_place = book_group.add_parser("place", help="place what a book provider built in its topic's folder")
    book_place.add_argument("--subject", required=True, help="the subject's [[subjects]] folder")
    book_place.add_argument("--topic", required=True, help="Tema NN - <title>")
    book_place.add_argument("--origin", required=True, help="the folder where the provider left its files")

    cfg_group = groups.add_parser("config", help="the student's configuration").add_subparsers(
        dest="verb", required=True
    )
    cfg_check = cfg_group.add_parser("check", help="compare the configuration with the template")

    notes = groups.add_parser("notes", help="class notes into the topic's notebook (spec 005)").add_subparsers(
        dest="verb", required=True
    )
    notes_run = notes.add_parser("run", help="one pass: new photos become pages of the living file")
    notebook = groups.add_parser("notebook", help="the topic's notebook (spec 005)").add_subparsers(
        dest="verb", required=True
    )
    notebook_setup = notebook.add_parser("setup", help="the topic's two living files, added as sources")
    notebook_setup.add_argument("--topic", required=True, help="<subject>/<topic folder>")
    notebook_refresh = notebook.add_parser("refresh", help="the owner reads each changed living file's source")
    notebook_refresh.add_argument(
        "--browser",
        action="store_true",
        help="also renew the owner's session through nlm's own browser profile; only with someone at the Mac",
    )
    agent = notebook.add_parser("agent", help="the launchd agent that runs `notebook refresh`").add_subparsers(
        dest="action", required=True
    )
    agent_install = agent.add_parser("install", help="write the agent in ~/Library/LaunchAgents and load it")
    agent_remove = agent.add_parser("remove", help="unload the agent and delete it")
    exam = groups.add_parser("exam", help="the sheets for the day before an exam (spec 002)").add_subparsers(
        dest="verb", required=True
    )
    exam_prep = exam.add_parser("prep", help="the topic's notebook writes a theory and a problems sheet; both print")
    exam_prep.add_argument("--subject", required=True, help="the subject's [[subjects]] folder")
    exam_prep.add_argument("--exam", type=dt.date.fromisoformat, help="the exam's date (default: the next one)")
    exam_prep.add_argument("--slot", help="the study slot, HH:MM-HH:MM (default: 90 minutes)")
    exam_prep.add_argument("--topic", help="the exam's topic folder (default: the subject's most recent)")
    claude = groups.add_parser("claude", help="this place's Claude API key").add_subparsers(dest="verb", required=True)
    claude_key = claude.add_parser("key", help="the key of the workspace alfabeta").add_subparsers(
        dest="action", required=True
    )
    claude_set = claude_key.add_parser("set", help="store the key read from standard input in the keychain")

    cal = groups.add_parser("calendar", help="the family calendar").add_subparsers(dest="verb", required=True)
    probe = cal.add_parser("probe", help="a test event with one reminder at its start")
    probe.add_argument("--minutes", type=int, default=10)
    clean = cal.add_parser("probe-clean", help="delete a probe event")
    clean.add_argument("--event", required=True)

    for sub in (
        setter,
        link,
        google.choices["check"],
        unlink,
        probe,
        clean,
        cfg_check,
        take,
        renew,
        release,
        stop,
        log_notebook,
        book_place,
        propose,
        confirm,
        correct,
        change,
        plan_cmd,
        apply_cmd,
        agenda_cmd,
        collect,
        notes_run,
        notebook_setup,
        notebook_refresh,
        agent_install,
        agent_remove,
        exam_prep,
        claude_set,
    ):
        sub.add_argument("--student", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the command."""
    args = build_parser().parse_args(argv)
    home = Path(args.home or "~/.alfabeta").expanduser()
    if args.group == "sandbox":
        return _cmd_sandbox(args)
    if args.group == "anonymize":
        try:
            _emit({"ok": True, "written": anonymize.run(Path(args.input), Path(args.output), home)})
        except anonymize.AnonymizeError as err:
            return _fail("would_leak", EXIT_INVALID, str(err))
        return EXIT_OK
    if args.group == "guardrail":
        # No configuration folder (CI, another contributor) only means no named detectors.
        return guardrail.run(Path.cwd(), home, args.scope)
    if not home.is_dir():
        return _fail("no_home", EXIT_INVALID, "the configuration folder does not exist")
    store = KeychainStore()
    try:
        if args.group == "google" and args.verb == "client":
            return _cmd_client_set(args, store)
        if args.group == "claude":
            return notes_cli.cmd_claude_key_set(args.student, store, sys.stdin.read())
        if args.group == "lock":
            return _cmd_lock(args, home)
        if args.group == "log":
            return _cmd_log_stop(args, home) if args.verb == "stop" else _cmd_log_notebook(args, home)
        if args.group == "book":
            return _cmd_book_place(args, home)
        if args.group == "decisions":
            return _cmd_decisions(args, home)
        if args.group == "plan":
            return _cmd_plan(args, home)
        if args.group == "apply":
            return _cmd_apply(args, home)
        if args.group == "agenda":
            return _cmd_agenda(args, home)
        if args.group == "downloads":
            return _cmd_collect(args, home)
        if args.group == "config":
            return _cmd_config_check(home, args.student)
        if args.group == "exam":
            return exam_cli.cmd_exam_prep(home, args, store)
        if args.group == "notebook" and args.verb == "agent":
            agent_cfg = config.load(home, args.student, AGENT_TABLES)
            return notes_cli.cmd_notebook_agent(agent_cfg, home, args.action)
        cfg = config.load(home, args.student, TABLES[args.group])
        if args.group == "notes":
            return notes_cli.cmd_notes_run(cfg, store)
        if args.group == "notebook" and args.verb == "refresh":
            return notes_cli.cmd_notebook_refresh(cfg, store, browser=args.browser)
        if args.group == "notebook":
            return notes_cli.cmd_notebook_setup(cfg, store, args.topic)
        if args.group == "google":
            if args.verb == "link":
                return _cmd_link(args, cfg, store)
            if args.verb == "check":
                return _cmd_check(cfg, store)
            return _cmd_unlink(args, cfg, store)
        if args.verb == "probe":
            return _cmd_probe(args, cfg, store)
        return _cmd_probe_clean(args, cfg, store)
    except config.ConfigError as err:
        return _fail("invalid_config", EXIT_INVALID, str(err))


if __name__ == "__main__":
    sys.exit(main())
