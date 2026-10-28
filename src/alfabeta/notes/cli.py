"""`notes run`, `notebook setup`, `notebook refresh` and `claude key set` (spec 005 contracts/cli.md).

JSON on stdout, one line for people on stderr; no output names an address, a key, a Drive id, a
source id, a checksum or a path. Exit codes: 0 ok · 1 usage or validation (`no_nlm` too) · 2 a Google
link is not usable · 3 partial failure · 5 `nlm` not signed in; the highest wins. A spent budget is not
a failure (exit 0), and a missing Claude key exits 0 on the Mac, transcription skipped and reported.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from alfabeta.google import accounts
from alfabeta.google.drive import DriveError, ScopedDrive, cache_path
from alfabeta.google.notify import MacNotifier
from alfabeta.google.transport import TransportError, UrllibTransport
from alfabeta.notes.changes import DriveChangeFeed
from alfabeta.notes.model import RanOn
from alfabeta.notes.pdf import ReportlabPdfBuilder
from alfabeta.notes.refresh import LocalRefreshStore, RefreshDeps, refresh_sources
from alfabeta.notes.run import NotesDeps, run_notes
from alfabeta.notes.setup import Setting, SetupError, setup_topic
from alfabeta.notes.sources import NlmMissingError, NlmSources, SourcesError, run_bounded
from alfabeta.notes.state import ConcurrentWriteError, DriveNotesStateStore, retry_once
from alfabeta.notes.transcribe import TIMEOUT_SECONDS, ClaudeTranscriber, claude_key_name

if TYPE_CHECKING:
    from collections.abc import Callable

    from alfabeta.config import StudentConfig
    from alfabeta.google.keychain import TokenStore

EXIT_OK, EXIT_INVALID, EXIT_LINK, EXIT_PARTIAL, EXIT_SIGNED_OUT = 0, 1, 2, 3, 5
MADRID = ZoneInfo("Europe/Madrid")


class SystemClock:
    """The instant now, in the family's zone."""

    def now(self) -> dt.datetime:
        """Now."""
        return dt.datetime.now(MADRID)


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def _fail(reason: str, code: int, message: str) -> int:
    print(f"alfabeta: {message}", file=sys.stderr)
    _emit({"ok": False, "reason": reason})
    return code


def _student_alias(cfg: StudentConfig) -> str:
    for alias, account in sorted(cfg.accounts.items()):
        if account.role == "student":
            return alias
    raise accounts.LinkError("no_student_account")


def notes_deps(cfg: StudentConfig, store: TokenStore, ran_on: RanOn) -> tuple[NotesDeps, ScopedDrive]:
    """The pass's real ports: the student's Drive, the place's Claude key, the PDF builder."""
    transport = UrllibTransport()
    token = accounts.access_token(cfg, _student_alias(cfg), store, transport)
    drive = ScopedDrive.open(transport, token, cfg.drive_root, cache_path(cfg))
    transcriber = ClaudeTranscriber.from_store(
        UrllibTransport(timeout=TIMEOUT_SECONDS), store, cfg.student, cfg.notes_model
    )
    deps = NotesDeps(
        drive=drive,
        store=DriveNotesStateStore(drive),
        feed=DriveChangeFeed(drive),
        pdf=ReportlabPdfBuilder(),
        transcriber=transcriber,
        clock=SystemClock(),
        model=cfg.notes_model,
        prices=cfg.notes_prices,
        warn_pages=cfg.notes_warn_pages,
        ran_on=ran_on,
    )
    return deps, drive


def cmd_notes_run(
    cfg: StudentConfig,
    store: TokenStore,
    ran_on: RanOn = RanOn.MAC,
    factory: Callable[[StudentConfig, TokenStore, RanOn], tuple[NotesDeps, Any]] = notes_deps,
) -> int:
    """`notes run`: one pass."""
    try:
        deps, _ = factory(cfg, store, ran_on)
        report = retry_once(lambda: run_notes(deps))
    except accounts.LinkError as err:
        return _fail(err.reason, EXIT_LINK, "the student's Google link is not usable: run `google check`")
    except (DriveError, TransportError):
        return _fail(
            "drive_failed", EXIT_PARTIAL, "Drive refused or did not answer; the next run reads the same changes"
        )
    except ConcurrentWriteError:
        return _fail("state_changed", EXIT_PARTIAL, "another run wrote the records twice meanwhile; nothing written")
    if report["no_key"]:
        where = "the cloud has" if ran_on == RanOn.CLOUD else "this Mac has"
        print(f"alfabeta: {where} no Claude key; photos wait (`claude key set`).", file=sys.stderr)
    _emit(report)
    if not report["ok"] or (report["no_key"] and ran_on == RanOn.CLOUD):
        return EXIT_PARTIAL
    return EXIT_OK


def cmd_notebook_setup(
    cfg: StudentConfig,
    store: TokenStore,
    topic: str,
    factory: Callable[[StudentConfig, TokenStore, RanOn], tuple[NotesDeps, Any]] = notes_deps,
    sources: Callable[[str], Any] = NlmSources,
) -> int:
    """`notebook setup --topic <subject>/<folder>`."""
    setting = Setting(topic, cfg.notebook_title_pattern, cfg.grade_level, cfg.notebook_owner)
    try:
        deps, drive = factory(cfg, store, RanOn.MAC)
        out = setup_topic(deps, drive, sources(cfg.nlm_profile), setting)
    except accounts.LinkError as err:
        return _fail(err.reason, EXIT_LINK, "the student's Google link is not usable: run `google check`")
    except SetupError as err:
        return _fail(err.reason, EXIT_INVALID, f"setup stopped: {err.reason}")
    except SourcesError as err:
        if err.signed_out:
            return _fail("nlm_signed_out", EXIT_SIGNED_OUT, "nlm is not signed in: run `nlm login --profile <profile>`")
        return _fail("nlm_failed", EXIT_PARTIAL, "nlm failed; nothing more was added")
    except (DriveError, TransportError, ConcurrentWriteError):
        return _fail("drive_failed", EXIT_PARTIAL, "Drive refused or did not answer; run setup again")
    _emit(out)
    return EXIT_OK


def refresh_deps(cfg: StudentConfig, store: TokenStore) -> RefreshDeps:
    """The refresh's real ports: Drive opened at the root, the owner's `nlm`, the record, the Mac (R14)."""
    transport = UrllibTransport()
    token = accounts.access_token(cfg, _student_alias(cfg), store, transport)
    drive = ScopedDrive.open_root(transport, token, cfg.drive_root, cache_path(cfg))
    return RefreshDeps(
        state=DriveNotesStateStore(drive),
        sources=NlmSources(cfg.nlm_profile, run_bounded),
        record=LocalRefreshStore(cfg.data_dir),
        notifier=MacNotifier(),
        clock=SystemClock(),
    )


def cmd_notebook_refresh(
    cfg: StudentConfig,
    store: TokenStore,
    *,
    browser: bool = False,
    factory: Callable[[StudentConfig, TokenStore], RefreshDeps] = refresh_deps,
) -> int:
    """`notebook refresh`: one pass of the owner's reads (FR-018); `browser` only with a person at the Mac."""
    try:
        deps = factory(cfg, store)
        report = refresh_sources(deps, browser=browser)
    except accounts.LinkError as err:
        return _fail(err.reason, EXIT_LINK, "the student's Google link is not usable: run `google check`")
    except NlmMissingError:
        return _fail("no_nlm", EXIT_INVALID, "nlm cannot be run: install it, then install the agent again")
    except SourcesError:
        return _fail("nlm_failed", EXIT_PARTIAL, "nlm failed; the next pass reads the same sources")
    except (DriveError, TransportError):
        return _fail("drive_failed", EXIT_PARTIAL, "Drive refused or did not answer; the next pass tries again")
    _emit(report)
    when = deps.clock.now().isoformat(timespec="seconds")  # the agent's log has no time of its own
    counts = f"read {report['read']}, unchanged {report['unchanged']}, missing {report['missing']}"
    print(f"alfabeta: notebook refresh at {when}: {counts}", file=sys.stderr)
    if not report["ok"] and report["session"] == "signed_out":
        print(
            "alfabeta: nlm is not signed in, even after renewing: run `nlm login --profile <profile>`", file=sys.stderr
        )
        return EXIT_SIGNED_OUT
    if not report["ok"]:
        print("alfabeta: a source could not be read; the next pass reads it again", file=sys.stderr)
        return EXIT_PARTIAL
    return EXIT_OK


def cmd_claude_key_set(student: str, store: TokenStore, stdin: str) -> int:
    """`claude key set`: the place's own key of the workspace `alfabeta`, from standard input."""
    key = stdin.strip()
    if not key:
        return _fail("empty_key", EXIT_INVALID, "no key on standard input")
    store.set(claude_key_name(student), key)
    print("alfabeta: Claude key stored in the keychain.", file=sys.stderr)
    _emit({"ok": True})
    return EXIT_OK
