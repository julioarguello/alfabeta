"""`classroom refresh`, the container read (spec 006 FR-022, FR-027, FR-028, FR-032; plan, run flow).

One run under the student's and the browser lock: Docker, the image, Docker's available memory
(under READ_FLOOR_MB the read stops with `docker_low_memory` before the keychain is read or anything
signs in; a reading that fails stops nothing; either way the log line keeps it as `memory`), the
container (which signs in when it must and may, and captures every class; a page that dies ends the
read there with `browser_crashed`), then spec 001's own steps — `download collect`,
`classroom plan`, `classroom apply` — as the classroom-sync skill runs them, with `ALFABETA_RUN`.
Between plan and apply, the attachments the plan asks for (spec 001 research R4's rule: new,
modified, renamed or the periodic review, out of this run's captures) are fetched by a second pass
of the container in the same session, which never signs in; each file lands at its exact
`data/inbox/<item>__<attachment>/<name>`, where `classroom apply` takes it. The pass is skipped
when the plan asks for nothing, the first pass found the session gone, or its page died
(`browser_crashed`); what is not brought, apply notes «no traído».

- Inside Claude Code (`CLAUDECODE` set) the container gets the account and `signin: false`, never
  the password, and no notification is shown (FR-027): Claude never starts the scripted sign-in.
- With the `wrong_password` mark the container gets `signin: false` too; a `wrong_password` stop
  sets the mark (FR-027, FR-031).
- With the mark, a read that finds the session gone stops with `wrong_password`, not
  `session_expired`: the notice must keep asking for `classroom password set` (FR-027).
- Started by the launchd agent, the read first finds the Mac staying awake (`_await_awake`, FR-015),
  without the lock, or stops `mac_asleep` when the window closes first; from then on it holds
  `caffeinate` (`Deps.keep_awake`). A Mac that slept before the password, or through the try that
  ended `unreachable`, stops the read `mac_asleep` (`awake.SleepMeter`); the log keeps `mac`.
- Started by the launchd agent (`started_by: schedule`) more than `[schedule] wait_minutes` (at
  least GRACE_MINUTES) after its day's time, or on a day with none (a Mac that slept through it,
  FR-015), the read is not made up: `outcome: skipped`, `reason: outside_hours`, one log line, no
  lock, no notice. A window that crosses midnight belongs to the day it started.
- A stop before anything was read writes nothing to the student's folder, shows the macOS
  notification in Spanish naming the code (FR-032) and leaves one log line.
- Progress: one short English line per step on stderr (`Deps.say`; the CLI adds the local time),
  built from the container's events — where the read is, never an address, a name or a password
  (rule python-cli-output §1, §4, §6; constitution 2.12.0, Language). The log line names the `step` the first pass stopped in.
- A step of spec 001 that fails (its JSON says `ok: false`, it leaves no JSON and a non-zero exit,
  or it runs out of time) stops the run with that step's reason and the same notification.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import re
import shutil
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, cast

from alfabeta import state
from alfabeta.classroom import awake
from alfabeta.classroom.container import ContainerError
from alfabeta.classroom.password import PasswordStore
from alfabeta.downloads import inbox_path
from alfabeta.google.keychain import KeychainError
from alfabeta.model import RunMode, StopReason

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from contextlib import AbstractContextManager
    from pathlib import Path

    from alfabeta.classroom.container import ReadContainer
    from alfabeta.google.keychain import TokenStore
    from alfabeta.google.notify import Notifier

RENEW_SECONDS = 60
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,200}$")
# A first pass that ended so says the session is gone or the read was breached: no second pass.
NO_SESSION = ("session_expired", "challenge")
# Nor after a page that died: a second browser in the Docker that just lost one would only repeat it.
NO_SECOND_PASS = (*NO_SESSION, "browser_crashed")
STARTED_BY = ("schedule", "command")
# What the notification tells the family to do, by stop code (FR-032).
ADVICE = {
    "wrong_password": "guarda la contraseña nueva con `classroom password set`",
    "no_password": "guarda la contraseña con `classroom password set`",
    "docker_unavailable": "abre Docker Desktop",
    "docker_low_memory": "cierra otros contenedores o sube la memoria de Docker Desktop",
    # The code states what was seen (the page died); memory is where to look, not a proven cause.
    "browser_crashed": "mira la memoria de Docker: cierra otros contenedores o súbela en Docker Desktop",
    # A closed lid sleeps the Mac with no external display, on power too; no assertion keeps it awake.
    "mac_asleep": "deja el Mac abierto y encendido mientras dura la lectura",
}
# Below this much available memory in Docker the read is not started (FR-028). Measured 2026-11-19
# (#268, research S16): with 1213 MB available — read as here, by a short container of the image
# with no read running — the load of one class took its container to about 1.2 GB and the page
# died. The floor sits above that one failing reading; no read has been measured to succeed at it,
# and the `memory` each read logs is what can move it.
READ_FLOOR_MB = 1536


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
    times: Mapping[str, str] = field(default_factory=lambda: {})  # `[schedule]`: day → "HH:MM" or ""
    wait_minutes: int = 0


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
    now: dt.datetime | None = None  # the Mac's local time; None = now (the tests fix it)
    say: Callable[[str], None] | None = None  # one progress line for people (stderr); None = quiet
    pause: Callable[[float], None] | None = None  # waits that many seconds; None = time.sleep (the tests skip it)
    clocks: Callable[[], tuple[float, float]] | None = None  # wall and awake seconds; None = awake.clocks
    keep_awake: Callable[[], AbstractContextManager[None]] | None = None  # None = no assertion (the tests)


# How long a read waits before its one more try when Classroom's home did not load (a network that
# was not there yet); within FR-015's window and the lock's lease, which the renewer keeps.
RETRY_PAUSE_SECONDS = 120
# A scheduled read starts only on a Mac that stays awake (FR-015): a stretch of AWAKE_PROBE_SECONDS
# in which it slept less than SLEPT_SECONDS. A maintenance wake lasts about 5 s (2026-11-26), so the
# stretch outlasts it; the margin leaves room for a step of the wall clock. The same margin, slept
# within a read, makes its `unreachable` a `mac_asleep`.
AWAKE_PROBE_SECONDS = 15
SLEPT_SECONDS = 10

OK, FAIL, WARN = "✓", "✗", "⚠"  # python-cli-output §4: done, failed, a run that stays partial


def _counted(n: int, one: str, many: str) -> str:
    """A count with its noun (python-cli-output §9)."""
    return f"{n} {one if n == 1 else many}"


class Progress:
    """The container's events as one English line per step, or None for an event that says nothing new."""

    def __init__(self) -> None:
        self.index, self.total = 0, 0
        self.signed_in = False

    def line(self, event: dict[str, Any]) -> str | None:
        """The line an event earns, if any."""
        kind = event.get("event")
        if kind == "home":
            if event.get("state") == "alive":
                return f"{OK} Classroom session open"
            if event.get("state") == "expired":
                return (
                    f"{FAIL} Classroom does not open after signing in" if self.signed_in else "the session has expired"
                )
            return None
        if kind == "signin_start":
            return "signing in with the stored password …"
        if kind == "signin":
            result = event.get("result")
            self.signed_in = result == "signed_in"
            return f"{OK} signed in" if result == "signed_in" else f"{FAIL} sign-in stopped: {result}"
        if kind == "account":
            return {
                "ok": f"{OK} school account checked",
                "other_account": f"{FAIL} another account is signed in to the profile",
                "none": f"{FAIL} the page names no account",
            }.get(str(event.get("result")))
        if kind == "classes":
            if "stop" in event:
                return f"{FAIL} the class list could not be read: {event['stop']}"
            return f"{OK} {_counted(int(event.get('to_read', 0)), 'class', 'classes')} to read"
        if kind == "class_start":
            self.index, self.total = int(event.get("index", 0)), int(event.get("total", 0))
            return None
        if kind == "class":
            where = f"class {self.index}/{self.total}"
            if event.get("type") == "class":
                return f"{OK} {where}" + ("" if event.get("complete") else " (incomplete: read again next time)")
            return f"{FAIL} {where}: {event.get('reason')}"
        return None


def _speaker(deps: Deps, events: list[dict[str, Any]]) -> Callable[[dict[str, Any]], None]:
    """Keep each event, and say its line."""
    progress = Progress()

    def on_event(event: dict[str, Any]) -> None:
        events.append(event)
        line = progress.line(event)
        if line:
            _say(deps, line)

    return on_event


def _say(deps: Deps, line: str) -> None:
    if deps.say is not None:
        deps.say(line)


DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
# The agent starts `uv run` a few seconds after its minute: `wait_minutes = 0` must not skip every run.
GRACE_MINUTES = 10


def in_hours(times: Mapping[str, str], wait_minutes: int, now: dt.datetime) -> bool:
    """Whether `now` is within the window after its day's `[schedule]` time (FR-015).

    The window is `wait_minutes`, at least GRACE_MINUTES; yesterday's time counts too, so a window
    that crosses midnight is kept.
    """
    window = dt.timedelta(minutes=max(wait_minutes, GRACE_MINUTES))
    for back in (0, 1):
        day = now - dt.timedelta(days=back)
        value = times.get(DAYS[day.weekday()], "")
        if not value:
            continue
        hour, minute = (int(part) for part in value.split(":"))
        start = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if start <= now <= start + window:
            return True
    return False


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
    if started_by == "schedule" and not in_hours(cfg.times, cfg.wait_minutes, deps.now or dt.datetime.now()):
        state.StateStore(cfg.data_dir).log(
            {"type": "classroom_refresh", "run": None, "started_by": started_by, "outcome": "skipped"}
            | {"reason": "outside_hours"}
        )
        return result | {"ok": True, "outcome": "skipped", "reason": "outside_hours"}
    clocks = deps.clocks or awake.clocks
    run_meter = awake.SleepMeter(clocks)
    mac: dict[str, int] = {}
    if started_by == "schedule":
        # Before the lock: a wait of up to the window must not hold the student's lock (FR-015).
        # Before the assertion too: held in a maintenance wake, it could keep that wake going and the
        # probe would measure its own assertion.
        stayed, waited = _await_awake(cfg, deps, clocks)
        mac["waited_s"] = round(waited)
        if not stayed:
            mac["slept_s"] = round(run_meter.slept())
            state.StateStore(cfg.data_dir).log(
                {"type": "classroom_refresh", "run": None, "started_by": started_by}
                | {"outcome": "stopped", "reason": str(StopReason.MAC_ASLEEP), "mac": mac}
            )
            return result | _stop(cfg, deps, str(StopReason.MAC_ASLEEP))
    since_gate = awake.SleepMeter(clocks)
    with (deps.keep_awake or contextlib.nullcontext)():
        return _locked(cfg, lock, deps, run_env, result, since_gate, run_meter, mac)


def _await_awake(cfg: RefreshConfig, deps: Deps, clocks: Callable[[], tuple[float, float]]) -> tuple[bool, float]:
    """Whether the Mac stays awake before the window closes, and the wall seconds it took (FR-015).

    Probes of AWAKE_PROBE_SECONDS until one finds the Mac slept less than SLEPT_SECONDS in it; a
    Mac in its maintenance wakes sleeps through each probe, until the family opens it or the window
    closes. Never longer than the window itself, whatever `[schedule]` says: a `wait_minutes` of a
    day would keep every day's window open.
    """
    waiting = awake.SleepMeter(clocks)
    begun = deps.now or dt.datetime.now()
    longest = 60 * max(cfg.wait_minutes, GRACE_MINUTES)
    said = False
    while True:
        probe = awake.SleepMeter(clocks)
        (deps.pause or time.sleep)(AWAKE_PROBE_SECONDS)
        if probe.slept() < SLEPT_SECONDS:
            return True, waiting.wall()
        now = begun + dt.timedelta(seconds=waiting.wall())
        if waiting.wall() >= longest or not in_hours(cfg.times, cfg.wait_minutes, now):
            return False, waiting.wall()
        if not said:
            _say(deps, f"{WARN} the Mac is asleep; the read waits for it to wake while the window lasts")
            said = True


def _locked(
    cfg: RefreshConfig,
    lock: state.Lock,
    deps: Deps,
    run_env: str | None,
    result: dict[str, Any],
    since_gate: awake.SleepMeter,
    run_meter: awake.SleepMeter,
    mac: dict[str, int],
) -> dict[str, Any]:
    """The read under the student's lock, and its log line."""
    started_by = result["started_by"]
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
        result |= _read(cfg, lock, deps, run, logged, since_gate)
    finally:
        store.log(
            {"type": "classroom_refresh", "run": run, "started_by": started_by}
            | {k: result.get(k) for k in ("outcome", "reason", "capture", "blocked")}
            | {"seconds": logged.get("seconds")}
            | {k: logged[k] for k in ("refused_hosts", "attachments_pass", "step", "memory", "retried") if k in logged}
            | {"mac": mac | {"slept_s": round(run_meter.slept())}}
            | _first_pass(logged.get("first_pass", []))
        )
        if not own:
            with contextlib.suppress(state.LockError):
                lock.release(run)
    return result


def _stop(cfg: RefreshConfig, deps: Deps, code: str) -> dict[str, Any]:
    if not deps.inside_claude:
        deps.notifier.notify(notification(cfg.student, code))
    return {"outcome": "stopped", "reason": code}


def _first_pass(events: list[dict[str, Any]]) -> dict[str, Any]:
    """What the log keeps of the first pass's events: the sign-in's result, its pages, the redirects.

    The sign-in's pages (host and path, never a query) and every document it loaded, redirects and
    frames included, with whether the guard let it through, are what narrowing its guard needs (T017).
    """
    signin = next((e.get("result") for e in events if e.get("event") == "signin"), None)
    keys = ("to", "host", "path", "main_frame")
    redirects = [{k: e[k] for k in keys if k in e} for e in events if e.get("event") == "redirect"]
    pages = [{k: e[k] for k in ("host", "path") if k in e} for e in events if e.get("event") == "signin_page"]
    load_keys = ("host", "path", "main_frame", "via", "allowed")
    loads = [{k: e[k] for k in load_keys if k in e} for e in events if e.get("event") == "signin_load"]
    return {"signin": signin, "signin_pages": pages, "signin_loads": loads, "redirects": redirects}


def _failed(step: dict[str, Any]) -> bool:
    return step.get("ok") is False


def _home_unreachable(end: dict[str, Any], events: list[dict[str, Any]]) -> bool:
    """Whether the read stopped because Classroom's home did not load, before any sign-in or class.

    The events say it too, not the step alone: read.py checks the home again after a sign-in, and a
    second try must never follow one (a run signs in once at most).
    """
    capture: dict[str, Any] = end.get("classes") or {}
    signing = any(e.get("event") in ("signin_start", "signin", "typed") for e in events)
    return (
        not signing
        and end.get("outcome") != "ok"
        and end.get("reason") == StopReason.UNREACHABLE
        and end.get("step") == "home"
        and not capture.get("read")
        and not capture.get("failed")
    )


def _read(
    cfg: RefreshConfig, lock: state.Lock, deps: Deps, run: str, logged: dict[str, Any], since_gate: awake.SleepMeter
) -> dict[str, Any]:
    if not deps.container.available():
        return _stop(cfg, deps, str(StopReason.DOCKER_UNAVAILABLE))
    try:
        _say(deps, "preparing the container …")
        image = deps.container.ensure_image()
    except ContainerError:
        return _stop(cfg, deps, str(StopReason.DOCKER_UNAVAILABLE))
    # Before the keychain and the sign-in: a read that cannot finish must not sign in (FR-028).
    memory = deps.container.memory(image)
    logged["memory"] = None if memory is None else {"total_mb": memory.total_mb, "available_mb": memory.available_mb}
    if memory is None:
        _say(deps, f"{WARN} Docker's available memory could not be read")
    elif memory.available_mb < READ_FLOOR_MB:
        _say(
            deps,
            f"{FAIL} Docker has {memory.available_mb} MB of memory available; the floor for a read is {READ_FLOOR_MB} MB",
        )
        return _stop(cfg, deps, str(StopReason.DOCKER_LOW_MEMORY))
    # Nor on a Mac that slept since it was found awake: a sign-in cut by a sleep is worse than none.
    if since_gate.slept() >= SLEPT_SECONDS:
        _say(deps, f"{FAIL} the Mac slept before the sign-in")
        return _stop(cfg, deps, str(StopReason.MAC_ASLEEP))
    passwords = PasswordStore(deps.store, cfg.data_dir, cfg.student)
    marked = passwords.marked()
    signin = not deps.inside_claude and not marked
    try:
        password = passwords.get() if signin else None
    except KeychainError:
        # The keychain did not answer (locked, or refused under launchd): the read cannot sign in.
        return _stop(cfg, deps, str(StopReason.NO_PASSWORD))
    if since_gate.slept() >= SLEPT_SECONDS:  # the keychain can take its time under launchd
        _say(deps, f"{FAIL} the Mac slept before the sign-in")
        return _stop(cfg, deps, str(StopReason.MAC_ASLEEP))
    request: dict[str, Any] = {"run": run, "account": cfg.account, "password": password, "signin": signin}
    del password
    events: list[dict[str, Any]] = []
    profile = cfg.data_dir / "classroom-profile"
    logged["first_pass"] = events  # the sign-in's result and any redirect, by host and path (no query)
    out = cfg.data_dir / f"classroom-out-{run}"
    container_meter = awake.SleepMeter(deps.clocks or awake.clocks)
    retry_slept = False  # the one more try was not made because the Mac slept
    try:
        with _Renewer(lock, run):
            _say(deps, "opening Classroom …")
            end = deps.container.run(image, request, profile, out, _speaker(deps, events))
            if _home_unreachable(end, events):
                # A network that was not there yet (2026-11-25 15:15: Classroom's home did not load
                # in 3 s, and loaded the next morning): one more try, before anything signed in.
                _say(deps, f"{WARN} Classroom did not load; trying again in {RETRY_PAUSE_SECONDS} s")
                (deps.pause or time.sleep)(RETRY_PAUSE_SECONDS)
                # The second try carries the password too: never on a Mac that slept since the probe
                # (the first try and the pause are this meter's, and make the stop `mac_asleep`).
                retry_slept = since_gate.slept() >= SLEPT_SECONDS
                if not retry_slept:
                    shutil.rmtree(out, ignore_errors=True)
                    events.clear()
                    logged["retried"] = True
                    _say(deps, "opening Classroom …")
                    end = deps.container.run(image, request, profile, out, _speaker(deps, events))
    except ContainerError:
        shutil.rmtree(out, ignore_errors=True)
        return _stop(cfg, deps, str(StopReason.DOCKER_UNAVAILABLE))
    finally:
        request.clear()
    logged["seconds"] = end.get("seconds")
    logged["step"] = end.get("step")
    capture = end.get("classes", {"read": 0, "failed": 0})
    blocked = end.get("blocked", {})
    reason = end.get("reason")
    if reason == StopReason.UNREACHABLE and (retry_slept or container_meter.slept() >= SLEPT_SECONDS):
        # Classroom did not load because the Mac slept, not because the network was away (2026-11-26).
        reason = str(StopReason.MAC_ASLEEP)
    if not capture.get("read") and end.get("outcome") != "ok":
        other_account = {"event": "account", "result": "other_account"} in events
        if marked and not deps.inside_claude and reason == StopReason.SESSION_EXPIRED and not other_account:
            reason = str(StopReason.WRONG_PASSWORD)
        if reason == StopReason.WRONG_PASSWORD and not marked:
            passwords.mark(deps.today)
        shutil.rmtree(out, ignore_errors=True)
        return _stop(cfg, deps, str(reason or StopReason.UNEXPECTED_UI)) | {"capture": capture, "blocked": blocked}
    _hand_over(out, cfg.downloads, run)
    _say(deps, "collecting the captures and planning …")
    collected = deps.steps(["download", "collect", "--wait", "10"], run)
    planned = {} if _failed(collected) else deps.steps(["classroom", "plan"], run)
    attachments: dict[str, int] = {"brought": 0, "not_brought": 0, "refused": 0}
    if not _failed(collected) and not _failed(planned):
        session = reason not in NO_SECOND_PASS and not blocked.get("redirects")
        attachments = _attachments(cfg, lock, deps, run, image, planned, session, logged)
    if not _failed(collected) and not _failed(planned):
        _say(deps, "placing in Drive …")
    apply_args = ["classroom", "apply"]
    if _review_incomplete(planned, logged):
        apply_args.append("--review-incomplete")
    applied = {} if _failed(collected) or _failed(planned) else deps.steps(apply_args, run)
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


def _review_incomplete(planned: dict[str, Any], logged: dict[str, Any]) -> bool:
    """Whether the plan's review downloads were not all asked for: the pass was cut or never ran (#290).

    A file asked for and not brought (a page, a 404) does not make a review incomplete; a pass that
    stopped before the end of its list, or that was skipped, does.
    """
    listed = planned.get("downloads", [])
    entries: list[Any] = cast("list[Any]", listed) if isinstance(listed, list) else []
    reasons = [cast("dict[str, Any]", d).get("why") for d in entries if isinstance(d, dict)]
    if not planned.get("full_review") or "review" not in reasons:
        return False
    passed = logged.get("attachments_pass")
    return not isinstance(passed, dict) or cast("dict[str, Any]", passed).get("reason") is not None


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
    _say(deps, f"fetching {_counted(len(wanted), 'attachment', 'attachments')} …")
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
    # A file over the read's in-memory cap is never brought until it can be streamed to disk (#300):
    # counted on the log line and in the summary, and apply notes it «no traído» as any file not brought.
    too_large = sum(1 for e in events if e.get("event") == "attachment" and e.get("why") == "too_large")
    logged["attachments_pass"] = {"reason": end.get("reason"), "blocked": end.get("blocked", {}), "too_large": too_large}
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
    counts = {"brought": placed, "not_brought": len(wanted) - placed - refused, "refused": refused}
    _say(deps, f"{OK} attachments: {placed} brought, {counts['not_brought']} not brought, {refused} refused")
    if too_large:
        _say(deps, f"{WARN} attachments: {too_large} too large to bring (#300); each is noted «no traído»")
    return counts


def _hand_over(out: Path, downloads: Path, run: str) -> None:
    """Move this run's captures where `download collect` looks for them; drop the out folder."""
    downloads.mkdir(parents=True, exist_ok=True)
    for path in sorted(out.glob(f"alfabeta-capture-{run}-*.json")):
        shutil.move(str(path), downloads / path.name)
    shutil.rmtree(out, ignore_errors=True)
