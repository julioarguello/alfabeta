"""`classroom refresh`, the container read (spec 006 FR-022, FR-027, FR-028, FR-032; plan, run flow).

One run under the student's and the browser lock: Docker, the image, the container (which signs in
when it must and may, and captures every class), then spec 001's own steps — `download collect`,
`classroom plan`, `classroom apply` — as the classroom-sync skill runs them, with `ALFABETA_RUN`.

- Inside Claude Code (`CLAUDECODE` set) the container gets the account and `signin: false`, never
  the password, and no notification is shown (FR-027): Claude never starts the scripted sign-in.
- With the `wrong_password` mark the container gets `signin: false` too; a `wrong_password` stop
  sets the mark (FR-027, FR-031).
- A stop before anything was read writes nothing to the student's folder, shows the macOS
  notification in Spanish naming the code (FR-032) and leaves one log line.
"""

from __future__ import annotations

import contextlib
import shutil
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from alfabeta import state
from alfabeta.classroom.container import ContainerError
from alfabeta.classroom.password import PasswordStore
from alfabeta.model import RunMode, StopReason

if TYPE_CHECKING:
    import datetime as dt
    from pathlib import Path

    from alfabeta.classroom.container import ReadContainer
    from alfabeta.google.keychain import TokenStore
    from alfabeta.google.notify import Notifier

RENEW_SECONDS = 60
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
    try:
        result |= _read(cfg, lock, deps, run, store)
    finally:
        store.log(
            {"type": "classroom_refresh", "run": run, "started_by": started_by}
            | {k: result.get(k) for k in ("outcome", "reason", "capture", "blocked")}
        )
        if not own:
            with contextlib.suppress(state.LockError):
                lock.release(run)
    return result


def _stop(cfg: RefreshConfig, deps: Deps, code: str) -> dict[str, Any]:
    if not deps.inside_claude:
        deps.notifier.notify(notification(cfg.student, code))
    return {"outcome": "stopped", "reason": code}


def _read(cfg: RefreshConfig, lock: state.Lock, deps: Deps, run: str, store: state.StateStore) -> dict[str, Any]:
    if not deps.container.available():
        return _stop(cfg, deps, str(StopReason.DOCKER_UNAVAILABLE))
    try:
        image = deps.container.ensure_image()
    except ContainerError:
        return _stop(cfg, deps, str(StopReason.DOCKER_UNAVAILABLE))
    passwords = PasswordStore(deps.store, cfg.data_dir, cfg.student)
    signin = not deps.inside_claude and not passwords.marked()
    request: dict[str, Any] = {
        "run": run,
        "account": cfg.account,
        "password": passwords.get() if signin else None,
        "signin": signin,
    }
    profile = cfg.data_dir / "classroom-profile"
    out = cfg.data_dir / f"classroom-out-{run}"
    try:
        with _Renewer(lock, run):
            end = deps.container.run(image, request, profile, out, lambda event: None)
    finally:
        request.clear()
    capture = end.get("classes", {"read": 0, "failed": 0})
    blocked = end.get("blocked", {})
    reason = end.get("reason")
    if not capture.get("read"):
        if reason == "wrong_password":
            passwords.mark(deps.today)
        shutil.rmtree(out, ignore_errors=True)
        return _stop(cfg, deps, str(reason or StopReason.UNEXPECTED_UI)) | {"capture": capture, "blocked": blocked}
    _hand_over(out, cfg.downloads, run)
    collected = deps.steps(["download", "collect", "--wait", "10"], run)
    deps.steps(["classroom", "plan"], run)
    applied = deps.steps(["classroom", "apply"], run)
    outcome = "ok" if end.get("outcome") == "ok" else "partial"
    return {
        "ok": True,
        "outcome": outcome,
        "reason": reason,
        "capture": capture | {"collected": len(collected.get("classes", []))},
        "apply": {k: applied.get(k) for k in ("added", "changed", "pending_decisions") if k in applied},
        "blocked": blocked,
    }


def _hand_over(out: Path, downloads: Path, run: str) -> None:
    """Move this run's captures where `download collect` looks for them; drop the out folder."""
    downloads.mkdir(parents=True, exist_ok=True)
    for path in sorted(out.glob(f"alfabeta-capture-{run}-*.json")):
        shutil.move(str(path), downloads / path.name)
    shutil.rmtree(out, ignore_errors=True)
