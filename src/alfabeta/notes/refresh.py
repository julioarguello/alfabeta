"""`notebook refresh`: the owner reads each changed living file's source (spec 005 FR-018, FR-019, R14, T044).

Mac only. The student's own access does not make the notebook take a changed Drive file; a read by its
owner does, within two minutes (measured 2026-10-28). A pass reads `state.json` from a Drive opened at
the root (`ScopedDrive.open_root`, no listing), compares each living file's `built_md5` with the checksum
the owner last read, and reads only the sources that differ or await their confirming read: with
nothing changed it calls no `nlm` and writes nothing. It never adds, removes or renames a source (FR-011).

A source someone deleted from its notebook answers the read with "not found" (measured 2026-11-12,
julioarguello/alfabeta#235). The pass counts it as `gone`, tells the family once, on the Mac, which
living file it was, and the Mac's sync shows an agenda line while it lasts; `notebook prepare` on that
topic adds the file again (FR-009a, FR-018a), and its new source is read on the next pass.

Unattended, a failing session is renewed once, with `nlm auth refresh --http-only`, which needs no
browser. The renewal through `nlm`'s own browser profile runs only when a person at the Mac asks for it
(`browser`), never from the launchd agent: no run may make a browser ask anything mid-run. A session that
still fails stops the pass: FR-019's notice goes out when the record's `session` turns `signed_out`, and
the Mac's sync shows an agenda line while it stays so.

The record, `notebook-refresh.json` in the student's data folder, is readable by its user alone and
written only when it changes. It holds source ids, checksums and the titles of the living files whose
source is gone: nothing here prints or logs it, and only the family's notice and agenda show a title.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

from alfabeta.notes.model import Health, LivingKind, RefreshRecord, Session, SourceRead, Topic
from alfabeta.notes.run import living_of
from alfabeta.notes.sources import NlmMissingError, SourcesError
from alfabeta.state import write_atomic

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from alfabeta.google.notify import Notifier
    from alfabeta.notes.model import Clock
    from alfabeta.notes.sources import NotebookSources

RECORD = "notebook-refresh.json"
# What the family reads (Spanish). Neither names the profile, the account or a notebook.
NOTICE = (
    "alfabeta no puede actualizar los cuadernos: la sesión de nlm de la cuenta propietaria no funciona; "
    "vuelve a iniciarla con «nlm login»"
)
AGENDA_LINE = (
    "**Aviso**: los cuadernos no reciben las páginas nuevas porque la sesión de nlm de la cuenta propietaria "
    "no funciona en el Mac; vuelve a iniciarla con «nlm login --profile <perfil>»."
)
# FR-018a. Each takes the living file's title, «Apuntes · <tema>» or «Classroom · <tema>»: no id, no account.
GONE_NOTICE = (
    "al cuaderno le falta la fuente «{title}», que alguien borró; vuelve a añadirla con «notebook prepare» en ese tema"
)
GONE_AGENDA_LINE = (
    "**Aviso**: el cuaderno ya no tiene la fuente «{title}» (alguien la borró), así que no recibe sus "
    "páginas nuevas; vuelve a añadirla con «python -m alfabeta notebook prepare» en ese tema."
)


class StateReader(Protocol):
    """What the pass needs of `state.json`: to read it (spec 005 `DriveNotesStateStore`)."""

    def load(self) -> dict[str, Any]:
        """The records, `{}` before the first write."""
        ...


class RefreshStore(Protocol):
    """The refresh record of one student."""

    def load(self) -> RefreshRecord:
        """The record, empty before the first write."""
        ...

    def save(self, record: RefreshRecord) -> bool:
        """Write the record if it changed; False when nothing was written."""
        ...


def _when(value: object) -> dt.datetime | None:
    return dt.datetime.fromisoformat(value) if isinstance(value, str) and value else None


def record_of(data: Mapping[str, Any]) -> RefreshRecord:
    """A record from its JSON; `exam build`'s entries may lack `read_at`, and its record `session`."""
    sources = {
        str(source): SourceRead(str(read["read_md5"]), int(read.get("reads", 1)), _when(read.get("read_at")))
        for source, read in cast("dict[str, dict[str, Any]]", data.get("sources", {})).items()
    }
    session = Session(data["session"]) if data.get("session") else None
    gone = {str(source): str(title) for source, title in cast("dict[str, Any]", data.get("gone", {})).items()}
    return RefreshRecord(sources, session, _when(data.get("session_since")), gone)


def record_json(record: RefreshRecord) -> dict[str, Any]:
    """A record as JSON; `session` only once a pass has checked it, `gone` only while a source is."""
    sources: dict[str, Any] = {}
    for source, read in record.sources.items():
        entry: dict[str, Any] = {"read_md5": read.read_md5, "reads": read.reads}
        if read.read_at is not None:
            entry["read_at"] = read.read_at.isoformat()
        sources[source] = entry
    data: dict[str, Any] = {"sources": sources}
    if record.session is not None:
        data["session"] = str(record.session)
        data["session_since"] = record.session_since.isoformat() if record.session_since else None
    if record.gone:
        data["gone"] = dict(record.gone)
    return data


@dataclass(frozen=True)
class LocalRefreshStore:
    """`RefreshStore` in the student's data folder: on the Mac only, never in Drive (research R14)."""

    data_dir: Path

    @property
    def path(self) -> Path:
        """`notebook-refresh.json`."""
        return self.data_dir / RECORD

    def load(self) -> RefreshRecord:
        """The record; empty when there is none."""
        if not self.path.is_file():
            return RefreshRecord()
        return record_of(cast("dict[str, Any]", json.loads(self.path.read_text())))

    def save(self, record: RefreshRecord) -> bool:
        """Write it only when its bytes change, readable by its user alone (T044)."""
        text = json.dumps(record_json(record), ensure_ascii=False, indent=1, sort_keys=True) + "\n"
        written = write_atomic(self.path, text)
        if written:
            self.path.chmod(0o600)
        return written


@dataclass(frozen=True)
class RefreshDeps:
    """The pass's ports."""

    state: StateReader
    sources: NotebookSources
    record: RefreshStore
    notifier: Notifier
    clock: Clock


@dataclass(frozen=True)
class _Built:
    source_id: str
    built_md5: str
    title: str  # the living file's, for the family's notice when its source is gone (FR-018a)


def _living(state: Mapping[str, Any]) -> tuple[list[_Built], int]:
    """The living files bound to a source: those healthy and built, and how many are missing."""
    built: dict[str, _Built] = {}
    missing = 0
    for topic, data in cast("dict[str, dict[str, Any]]", state.get("topics", {})).items():
        records = cast("dict[str, dict[str, Any]]", data.get("living", {}))
        for kind in LivingKind:
            record = records.get(str(kind))
            living = living_of(topic, kind, record)
            if record is None or living.source_id is None:
                continue  # waiting for `notebook prepare`: no source to read
            if Health(record.get("health", Health.OK)) != Health.OK:
                missing += 1  # not read; FR-011's report covers it
            elif living.built_md5 is not None and living.source_id not in built:
                title = Topic(topic, str(data.get("name", ""))).living_file_name(kind).removesuffix(".pdf")
                built[living.source_id] = _Built(living.source_id, living.built_md5, title)
    return list(built.values()), missing


def _session(sources: NotebookSources, *, browser: bool) -> tuple[bool, bool]:
    """Whether the session works, after the renewals allowed here, and whether any renewal ran."""
    if sources.session_ok():
        return True, False
    for with_browser in (False, True) if browser else (False,):
        if sources.renew_session(with_browser) and sources.session_ok():
            return True, True
    return False, True


def _signed_out(deps: RefreshDeps, record: RefreshRecord, report: dict[str, Any], now: dt.datetime) -> dict[str, Any]:
    """Stop: record `signed_out`, and tell the family only if that is a change (FR-019)."""
    record, turned = record.with_session(Session.SIGNED_OUT, now)
    deps.record.save(record)
    if turned:
        deps.notifier.notify(NOTICE)
    return report | {"ok": False, "session": str(Session.SIGNED_OUT)}


def refresh_sources(deps: RefreshDeps, *, browser: bool = False) -> dict[str, Any]:
    """One pass: `{ok, read, unchanged, missing, gone, renewed, session}` (contracts/cli.md).

    `session` is the last one a pass measured, None before any did: an idle pass does not check it.
    `NlmMissingError` propagates: `nlm` that cannot be run is `no_nlm`, never a signed-out owner.
    `gone` counts the sources this pass asked for and their notebook no longer holds (FR-018a): each is
    asked for again on every pass, since its record does not move, until `notebook prepare` records the
    new source in its place.
    """
    living, missing = _living(deps.state.load())
    record = deps.record.load()
    due = [built for built in living if record.due(built.source_id, built.built_md5)]
    report: dict[str, Any] = {
        "ok": True,
        "read": 0,
        "unchanged": len(living) - len(due),
        "missing": missing,
        "gone": 0,
        "renewed": False,
        "session": str(record.session) if record.session else None,
    }
    if not due:
        return report
    now = deps.clock.now()
    works, report["renewed"] = _session(deps.sources, browser=browser)
    if not works:
        return _signed_out(deps, record, report, now)
    record, _ = record.with_session(Session.OK, now)
    report["session"] = str(Session.OK)
    gone: dict[str, str] = {}
    for built in due:
        try:
            deps.sources.read_source(built.source_id)
        except NlmMissingError:
            raise
        except SourcesError as err:
            if err.signed_out:
                return _signed_out(deps, record, report, now)
            report["ok"] = False  # read again on the next pass: its record did not move
            # A read that fails otherwise says nothing: a source known gone stays so, and is not told again.
            if err.not_found or built.source_id in record.gone:
                gone[built.source_id] = built.title
            continue
        record = record.after_read(built.source_id, built.built_md5, now)
        report["read"] += 1
    # A gone source stays due, so this pass asked for each one the state still names: `gone` is the
    # whole list, and a source the setup replaced drops out of it.
    report["gone"] = len(gone)
    record, new = record.with_gone(gone)
    deps.record.save(record)
    for title in new:  # once per source: a pass that finds it gone again says nothing
        deps.notifier.notify(GONE_NOTICE.format(title=title))
    return report


def agenda_notices(data_dir: Path) -> tuple[str, ...]:
    """The agenda's lines: FR-019's while the session is `signed_out`, FR-018a's per source that is gone."""
    record = LocalRefreshStore(data_dir).load()
    session = (AGENDA_LINE,) if record.session == Session.SIGNED_OUT else ()
    return session + tuple(GONE_AGENDA_LINE.format(title=title) for title in sorted(record.gone.values()))
