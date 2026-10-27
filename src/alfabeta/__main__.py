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

from alfabeta import __version__, anonymize, config, decisions, downloads, guardrail, plan, replicas, sandbox, state
from alfabeta.google import accounts, calendar
from alfabeta.google.keychain import KeychainStore
from alfabeta.google.transport import UrllibTransport
from alfabeta.model import AgendaCategory, DecisionType, RunMode, StopReason

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
TABLES = {"google": ("classroom", "google"), "calendar": ("classroom", "calendar", "google")}


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
        last_review=plan.last_full_review(lock.data_dir / "log.jsonl"),
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


def _summary(applier: replicas.Applier, pending: list[dict[str, Any]], stopped: dict[str, str]) -> list[str]:
    """What the family reads after a sync, in Spanish (T043, FR-008)."""
    if not (applier.added or applier.changed or applier.not_fetched or pending or stopped or applier.unknown_statuses):
        return ["sin cambios"]
    lines = [f"{applier.added} nuevos, {applier.changed} cambiados, {len(applier.not_fetched)} sin traer"]
    unlinked = [p for p in pending if p["type"] == "class_link" and p.get("visibility") == "visible"]
    hidden = [p for p in pending if p["type"] == "class_link" and p.get("visibility") != "visible"]
    matches = [p for p in pending if p["type"] == "topic_match"]
    if unlinked:
        lines.append("clases sin vincular: " + ", ".join(str(p["title"]) for p in unlinked))
    if hidden:
        lines.append(f"clases ocultas o archivadas: {len(hidden)}")
    if matches:
        lines.append(f"temas por confirmar: {len(matches)}")
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
    current = store_log.load()
    applier = replicas.Applier(
        base=cfg.base,
        data_dir=lock.data_dir,
        school_year=cfg.school_year,
        subjects=list(cfg.subjects),
        decisions=store,
        state=json.loads(json.dumps(current)),
        today=decisions.today(),
        downloads=list(planned.get("downloads", [])),
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
        "withdrawn": 0,
        "not_fetched": applier.not_fetched,
        "unknown_statuses": applier.unknown_statuses,
        "pending_decisions": len(planned.get("pending_decisions", [])),
        "full_review": bool(planned.get("full_review")),
    }
    store_log.log(line)
    for text in _summary(applier, list(planned.get("pending_decisions", [])), stopped):
        print(f"alfabeta: {text}", file=sys.stderr)
    _emit(
        {k: line[k] for k in ("result", "reason", "added", "changed", "unknown_statuses")}
        | {"not_fetched": len(applier.not_fetched)}
    )
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
        elif args.batch is not None:
            _emit({"ok": True, "written": sandbox.download_batch(home, args.student, args.batch)})
        else:
            _emit({"ok": True, "written": sandbox.download_captures(home, args.student, os.environ.get(state.RUN_ENV))})
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
    statuses = accounts.check_accounts(cfg, store, UrllibTransport(), dt.date.today())
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
    what = box_download.add_mutually_exclusive_group(required=True)
    what.add_argument("--captures", action="store_true")
    what.add_argument("--batch", type=int)

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

    cfg_group = groups.add_parser("config", help="the student's configuration").add_subparsers(
        dest="verb", required=True
    )
    cfg_check = cfg_group.add_parser("check", help="compare the configuration with the template")

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
        propose,
        confirm,
        correct,
        change,
        plan_cmd,
        apply_cmd,
        collect,
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
        if args.group == "lock":
            return _cmd_lock(args, home)
        if args.group == "log":
            return _cmd_log_stop(args, home)
        if args.group == "decisions":
            return _cmd_decisions(args, home)
        if args.group == "plan":
            return _cmd_plan(args, home)
        if args.group == "apply":
            return _cmd_apply(args, home)
        if args.group == "downloads":
            return _cmd_collect(args, home)
        if args.group == "config":
            return _cmd_config_check(home, args.student)
        cfg = config.load(home, args.student, TABLES[args.group])
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
