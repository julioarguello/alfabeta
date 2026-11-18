"""`classroom refresh`, the container read (spec 006 FR-022, FR-027, FR-028, FR-032; plan, run flow).

One run under the student's and the browser lock: Docker, the image, the container (which signs in
when it must and may, and captures every class), then spec 001's own steps — `download collect`,
`classroom plan`, `classroom apply` — as the classroom-sync skill runs them, with `ALFABETA_RUN`.
Between plan and apply, the attachments the plan asks for (spec 001 research R4's rule: new,
modified, renamed or the periodic review, out of this run's captures) are fetched by a second pass
of the container in the same session, which never signs in; each file lands at its exact
`data/inbox/<item>__<attachment>/<name>`, where `classroom apply` takes it. The pass is skipped
when the plan asks for nothing or the first pass found the session gone; what is not brought,
apply notes «no traído».

- Inside Claude Code (`CLAUDECODE` set) the container gets the account and `signin: false`, never
  the password, and no notification is shown (FR-027): Claude never starts the scripted sign-in.
- With the `wrong_password` mark the container gets `signin: false` too; a `wrong_password` stop
  sets the mark (FR-027, FR-031).
- With the mark, a read that finds the session gone stops with `wrong_password`, not
  `session_expired`: the notice must keep asking for `classroom password set` (FR-027).
- A stop before anything was read writes nothing to the student's folder, shows the macOS
  notification in Spanish naming the code (FR-032) and leaves one log line.
- A step of spec 001 that fails (its JSON says `ok: false`, it leaves no JSON and a non-zero exit,
  or it runs out of time) stops the run with that step's reason and the same notification.
"""

from __future__ import annotations

import contextlib
import re
import shutil
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

from alfabeta import state
from alfabeta.classroom.container import ContainerError
from alfabeta.classroom.password import PasswordStore
from alfabeta.downloads import inbox_path
from alfabeta.google.keychain import KeychainError
from alfabeta.model import RunMode, StopReason

if TYPE_CHECKING:
    import datetime as dt
    from pathlib import Path

    from alfabeta.classroom.container import ReadContainer
    from alfabeta.google.keychain import TokenStore
    from alfabeta.google.notify import Notifier

RENEW_SECONDS = 60
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,200}$")
# A first pass that ended so says the session is gone or the read was breached: no second pass.
NO_SESSION = ("session_expired", "challenge")
STARTED_BY = ("schedule", "command")
# What the notification tells the family to do, by stop code (FR-032).
ADVICE = {
    "wrong_password": "guarda la contraseña nueva con `classroom password set`",
    "no_password": "guarda la contraseña con `classroom password set`",
    "docker_unavailable": "abre Docker Desktop",
}


class Steps(Protocol):
    """Runs one of spec 001's commands inside the run (`download collect`, `classroom plan|apply`)."""

    def __call__(self, args: list[str], run: str) -> dict[str, Any]:
        """Its JSON result."""
        ...


@dataclass(frozen=True)
class RefreshConfig:
    """What the read needs from the student's configuration."""

    student: str
    account: str
    profile_read: bool
    data_dir: Path
    downloads: Path
    idle_minutes: int


@dataclass(frozen=True)
class Deps:
    """The seams: the container, the keychain, the notifier, spec 001's steps, the clock, the environment."""

    container: ReadContainer
    store: TokenStore
    notifier: Notifier
    steps: Steps
    today: dt.date
    inside_claude: bool
    started_by: str


def notification(student: str, code: str) -> str:
    """The Spanish notice of a stop: the student by id, the code, what to do."""
    text = f"alfabeta ({student}): la lectura de Classroom se ha parado ({code})."
    advice = ADVICE.get(code)
    if advice:
        text += f" Para seguir, {advice}."
    else:
        text += " Hoy, sincroniza como siempre con Claude."
    return text


class _Renewer:
    """Renews the run's lock every minute while the container runs."""

    def __init__(self, lock: state.Lock, run: str) -> None:
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, args=(lock, run), daemon=True)

    def _loop(self, lock: state.Lock, run: str) -> None:
        while not self._stop.wait(RENEW_SECONDS):
            with contextlib.suppress(state.LockError):
                lock.renew(run)

    def __enter__(self) -> _Renewer:
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        self._thread.join(timeout=5)


def refresh(cfg: RefreshConfig, lock: state.Lock, deps: Deps, run_env: str | None) -> dict[str, Any]:
    """The whole container read; returns the command's JSON result (`ok`, `outcome`, `reason`, …)."""
    started_by = deps.started_by if deps.started_by in STARTED_BY else "command"
    result: dict[str, Any] = {"ok": False, "started_by": started_by, "outcome": "stopped", "reason": None}
    if not cfg.profile_read:
        return result | {"reason": str(StopReason.DISABLED)}
    lease = lock.lease()
    own = bool(run_env and lease is not None and lease.get("run") == run_env and lock.held())
    if own:
        run = str(run_env)
    else:
        try:
            run = lock.take(RunMode.SCHEDULED if started_by == "schedule" else RunMode.INTERACTIVE, cfg.idle_minutes)
        except state.LockError as err:
            return result | {"reason": str(err.reason)}
    store = state.StateStore(cfg.data_dir)
    logged: dict[str, Any] = {}  # what the passes add to the log line
    try:
        result |= _read(cfg, lock, deps, run, logged)
    finally:
        store.log(
            {"type": "classroom_refresh", "run": run, "started_by": started_by}
            | {k: result.get(k) for k in ("outcome", "reason", "capture", "blocked")}
            | {"seconds": logged.get("seconds")}
            | {k: logged[k] for k in ("refused_hosts", "attachments_pass") if k in logged}
        )
        if not own:
            with contextlib.suppress(state.LockError):
                lock.release(run)
    return result


def _stop(cfg: RefreshConfig, deps: Deps, code: str) -> dict[str, Any]:
    if not deps.inside_claude:
        deps.notifier.notify(notification(cfg.student, code))
    return {"outcome": "stopped", "reason": code}


def _failed(step: dict[str, Any]) -> bool:
    return step.get("ok") is False


def _read(cfg: RefreshConfig, lock: state.Lock, deps: Deps, run: str, logged: dict[str, Any]) -> dict[str, Any]:
    if not deps.container.available():
        return _stop(cfg, deps, str(StopReason.DOCKER_UNAVAILABLE))
    try:
        image = deps.container.ensure_image()
    except ContainerError:
        return _stop(cfg, deps, str(StopReason.DOCKER_UNAVAILABLE))
    passwords = PasswordStore(deps.store, cfg.data_dir, cfg.student)
    marked = passwords.marked()
    signin = not deps.inside_claude and not marked
    try:
        password = passwords.get() if signin else None
    except KeychainError:
        # The keychain did not answer (locked, or refused under launchd): the read cannot sign in.
        return _stop(cfg, deps, str(StopReason.NO_PASSWORD))
    request: dict[str, Any] = {"run": run, "account": cfg.account, "password": password, "signin": signin}
    del password
    events: list[dict[str, Any]] = []
    profile = cfg.data_dir / "classroom-profile"
    out = cfg.data_dir / f"classroom-out-{run}"
    try:
        with _Renewer(lock, run):
            end = deps.container.run(image, request, profile, out, events.append)
    except ContainerError:
        shutil.rmtree(out, ignore_errors=True)
        return _stop(cfg, deps, str(StopReason.DOCKER_UNAVAILABLE))
    finally:
        request.clear()
    logged["seconds"] = end.get("seconds")
    capture = end.get("classes", {"read": 0, "failed": 0})
    blocked = end.get("blocked", {})
    reason = end.get("reason")
    if not capture.get("read") and end.get("outcome") != "ok":
        other_account = {"event": "account", "result": "other_account"} in events
        if marked and not deps.inside_claude and reason == StopReason.SESSION_EXPIRED and not other_account:
            reason = str(StopReason.WRONG_PASSWORD)
        if reason == StopReason.WRONG_PASSWORD and not marked:
            passwords.mark(deps.today)
        shutil.rmtree(out, ignore_errors=True)
        return _stop(cfg, deps, str(reason or StopReason.UNEXPECTED_UI)) | {"capture": capture, "blocked": blocked}
    _hand_over(out, cfg.downloads, run)
    collected = deps.steps(["download", "collect", "--wait", "10"], run)
    planned = {} if _failed(collected) else deps.steps(["classroom", "plan"], run)
    attachments: dict[str, int] = {"brought": 0, "not_brought": 0, "refused": 0}
    if not _failed(collected) and not _failed(planned):
        session = reason not in NO_SESSION and not blocked.get("redirects")
        attachments = _attachments(cfg, lock, deps, run, image, planned, session, logged)
    applied = {} if _failed(collected) or _failed(planned) else deps.steps(["classroom", "apply"], run)
    failed = next((step for step in (collected, planned, applied) if _failed(step)), None)
    if failed is not None:
        code = str(failed.get("reason") or StopReason.UNEXPECTED_UI)
        return _stop(cfg, deps, code) | {"capture": capture, "blocked": blocked}
    outcome = "ok" if end.get("outcome") == "ok" else "partial"
    return {
        "ok": True,
        "outcome": outcome,
        "reason": reason,
        "capture": capture | {"collected": len(collected.get("classes", [])), "attachments": attachments},
        "apply": {k: applied.get(k) for k in ("added", "changed") if k in applied}
        | {"pending_decisions": len(planned.get("pending_decisions", []))},
        "blocked": blocked,
    }


def _wanted(planned: dict[str, Any]) -> list[dict[str, Any]]:
    """The plan's downloads as the attachments pass takes them: item, attachment, R4 address, name."""
    keys = ("item", "attachment", "url", "expected_name")
    listed = planned.get("downloads", [])
    entries: list[Any] = cast("list[Any]", listed) if isinstance(listed, list) else []
    downloads = [cast("dict[str, Any]", d) for d in entries if isinstance(d, dict)]
    return [{k: d[k] for k in keys} for d in downloads if all(isinstance(d.get(k), str) for k in keys)]


def _safe(download: dict[str, Any]) -> bool:
    """Ids and name as single path components (they come from the page): no way out of the inbox."""
    name = download["expected_name"]
    return bool(
        SAFE_ID.match(download["item"])
        and SAFE_ID.match(download["attachment"])
        and 0 < len(name) <= 255
        and name not in (".", "..")
        and not any(c in name for c in ("/", "\\", "\0"))
    )


def _attachments(
    cfg: RefreshConfig,
    lock: state.Lock,
    deps: Deps,
    run: str,
    image: str,
    planned: dict[str, Any],
    session: bool,
    logged: dict[str, Any],
) -> dict[str, int]:
    """The second pass: fetch what the plan asks for, place each file at its exact inbox path.

    Its refused hosts, blocks and stop code go to the run's log line through `logged`.
    """
    wanted = _wanted(planned)
    counts = {"brought": 0, "not_brought": len(wanted), "refused": 0}
    if not wanted or not session:
        return counts
    request: dict[str, Any] = {"run": run, "account": cfg.account, "password": None, "signin": False, "fetch": wanted}
    out = cfg.data_dir / f"classroom-out-{run}-attachments"
    events: list[dict[str, Any]] = []
    try:
        with _Renewer(lock, run):
            end = deps.container.run(image, request, cfg.data_dir / "classroom-profile", out, events.append)
    except ContainerError:
        shutil.rmtree(out, ignore_errors=True)
        return counts
    finally:
        request.clear()
        hosts = {str(e.get("host")) for e in events if e.get("event") == "attachment" and e.get("host")}
        logged["refused_hosts"] = sorted(hosts)
    logged["attachments_pass"] = {"reason": end.get("reason"), "blocked": end.get("blocked", {})}
    placed = 0
    root = out.resolve()
    for download in wanted:
        if not _safe(download):
            continue
        source = out / "inbox" / f"{download['item']}__{download['attachment']}" / download["expected_name"]
        # Every part must be a real folder of `out`: a symlinked file or folder would move another file.
        try:
            inside = source.resolve().parent == root / "inbox" / source.parent.name
        except (OSError, RuntimeError):  # a symlink loop (RuntimeError on Python 3.12): not brought
            continue
        if inside and source.is_file() and not source.is_symlink():
            destination = inbox_path(cfg.data_dir, download)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), destination)
            placed += 1
    shutil.rmtree(out, ignore_errors=True)
    refused = int(end.get("attachments", {}).get("refused", 0))
    return {"brought": placed, "not_brought": len(wanted) - placed - refused, "refused": refused}


def _hand_over(out: Path, downloads: Path, run: str) -> None:
    """Move this run's captures where `download collect` looks for them; drop the out folder."""
    downloads.mkdir(parents=True, exist_ok=True)
    for path in sorted(out.glob(f"alfabeta-capture-{run}-*.json")):
        shutil.move(str(path), downloads / path.name)
    shutil.rmtree(out, ignore_errors=True)
