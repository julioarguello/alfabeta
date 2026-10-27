"""The `python -m alfabeta` command (spec 001 contracts/cli.md; spec 004 contracts/cli.md).

JSON for machines on stdout, messages for people on stderr. No output names an address, a token or
an absolute path; accounts are named by alias.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import webbrowser
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from alfabeta import __version__, config, guardrail
from alfabeta.google import accounts, calendar
from alfabeta.google.keychain import KeychainStore
from alfabeta.google.transport import UrllibTransport

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
    parser.add_argument("--home", default="~/.alfabeta", help="folder of student configurations")
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

    guard = groups.add_parser("guardrail", help="look for personal data before it is published")
    scope = guard.add_mutually_exclusive_group()
    scope.add_argument("--staged", dest="scope", action="store_const", const="staged", help="the staged change")
    scope.add_argument("--all", dest="scope", action="store_const", const="all", help="every tracked file")
    scope.add_argument("--history", dest="scope", action="store_const", const="history", help="every published commit")
    guard.set_defaults(scope="staged")

    cfg_group = groups.add_parser("config", help="the student's configuration").add_subparsers(
        dest="verb", required=True
    )
    cfg_check = cfg_group.add_parser("check", help="compare the configuration with the template")

    cal = groups.add_parser("calendar", help="the family calendar").add_subparsers(dest="verb", required=True)
    probe = cal.add_parser("probe", help="a test event with one reminder at its start")
    probe.add_argument("--minutes", type=int, default=10)
    clean = cal.add_parser("probe-clean", help="delete a probe event")
    clean.add_argument("--event", required=True)

    for sub in (setter, link, google.choices["check"], unlink, probe, clean, cfg_check):
        sub.add_argument("--student", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the command."""
    args = build_parser().parse_args(argv)
    home = Path(args.home).expanduser()
    if args.group == "guardrail":
        # No configuration folder (CI, another contributor) only means no named detectors.
        return guardrail.run(Path.cwd(), home, args.scope)
    if not home.is_dir():
        return _fail("no_home", EXIT_INVALID, "the configuration folder does not exist")
    store = KeychainStore()
    try:
        if args.group == "google" and args.verb == "client":
            return _cmd_client_set(args, store)
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
