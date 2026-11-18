#!/usr/bin/env python3
"""The container read (spec 006, amendment of 2026-11-17): sign in if needed, then capture Classroom.

Runs inside the image of `docker/classroom/Dockerfile`; imports nothing from `alfabeta`. It reads one
JSON line on stdin — `{"run", "account", "password", "signin"}`, plus `fetch` on the attachments
pass — and writes one JSON line per event on stdout, the last one `{"event": "end", ...}` with its
outcome and stop code. No line carries the account or the password.

- **Sign-in** (FR-027): only when the profile has no live session and `signin` is true. It clears
  the profile's cookies, opens Google's sign-in, types the account and the password, presses only
  Enter in those two fields, and waits for Classroom. Any other page stops it with a code; nothing is
  typed past a check (constitution IV).
- **Account check** (FR-006): the signed-in account must be the one given, read from the page's
  `aria-label`s and compared in memory; another account is `session_expired`.
- **Read** (FR-030): alfabeta's own extractor, unchanged, injected into Classroom's home page; the
  skill's calls, class by class; each capture returned through the page and written to the out
  folder under the extractor's own file name.
- **Guard** (FR-030, FR-027): presses and form submits cancelled on Classroom pages; main-frame and
  frame document loads only on the pages the phase allows; form, quiz and download hosts refused.
  Every block is counted.
- **Browser zone and locale** (FR-029): `Europe/Madrid`, `es-ES`.
- **Attachments** (FR-030's exception, the run's second pass): with `fetch` — the attachments the
  host's `classroom plan` asked for out of this run's captures — the read never signs in; after the
  account check it fetches each one through the page's request context (the session's cookies),
  only by spec 001 research R4's routes and only for the attachment id it is listed under, into
  `out/inbox/<item>__<attachment>/<name>`. The request context does not go through the guard's
  route, so each hop is checked here: redirects are followed by hand within the R4 hosts; a hop to
  Google's sign-in is the expired session (the rest is not brought); any other host is refused and
  logged by host only. An HTML page, a wrong length or an oversized body is not a file: not brought.

The tests run this module directly with Playwright's Chromium against a local fake, setting the
host constants below in the module object; nothing here reads them from the environment.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urljoin, urlsplit

CLASSROOM_HOME = "https://classroom.google.com/u/0/h"
SIGN_IN_URL = "https://accounts.google.com/ServiceLogin?service=classroom&continue=" + CLASSROOM_HOME
ACCOUNT_HOSTS = frozenset({"accounts.google.com"})
# Pages Google's sign-in redirects through to set its cookies (research S14's guard).
REDIRECT_HOSTS = frozenset({"accounts.youtube.com", "www.google.com", "www.google.es"})
CLASSROOM_HOSTS = frozenset({"classroom.google.com"})
FORM_HOSTS = frozenset({"forms.gle", "forms.google.com"})
DOWNLOAD_HOSTS = frozenset({"drive.usercontent.google.com"})
# Spec 001 research R4's routes, by origin, for the attachments pass (plan.py builds the addresses).
DRIVE_DOWNLOAD = "https://drive.usercontent.google.com/download"
DOCS_ORIGIN = "https://docs.google.com"
DOCS_EXPORT = re.compile(r"^/(document|spreadsheets|presentation)/d/([A-Za-z0-9_-]+)/export(/pdf)?$")
# Hosts a fetch may be redirected to besides R4's own: none measured yet. Each refused host reaches
# the run's log line (`refused_hosts`), and only a measured one is added here.
FETCH_REDIRECT_NETLOCS: frozenset[str] = frozenset()
FETCH_MAX_HOPS = 5
FETCH_MAX_BYTES = 200 * 1024 * 1024
FETCH_TIMEOUT_MS = 120_000
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,200}$")
# Spec 001 FR-007's pages: home, classwork, stream, item details.
CLASSROOM_PAGES = re.compile(r"^/u/\d+/(h(/[^/]*)?|w/[^/]+/t/all|c/[^/]+(/(a|m|mc)/[^/]+/details)?)$")
EXTRACTOR = Path("/app/extract.js")
PROFILE = Path("/profile")
OUT = Path("/out")
TIMEZONE = "Europe/Madrid"
LOCALE = "es-ES"
CHANNEL: str | None = "chrome"
# Playwright's defaults that keep cookies out of a keychain; removed as in research S7 so a profile
# is read back the same way. The tests keep them (a mock keychain), so no test touches a real one.
IGNORE_DEFAULT_ARGS: list[str] = ["--use-mock-keychain", "--password-store=basic"]
# The extractor's own pause between pages is multiplied by this; the tests set it to 0.
PACE = 1.0
# Class ids to capture; empty = every class (the tests name one or two to stay fast).
ONLY: frozenset[str] = frozenset()

EMAIL_FIELD = "#identifierId, input[name=identifier], input[type=email]"
PASSWORD_FIELD = "input[name=Passwd], input[type=password]"
CAPTCHA_MARKS = (
    "escribe el texto que escuches o veas",
    "type the text you hear or see",
    "demuestra que eres",
    "verifica que eres",
    "verify it's you",
    "tráfico inusual",
    "unusual traffic",
    "captcha",
)
WRONG_PASSWORD_MARKS = ("contraseña incorrecta", "wrong password")
SECOND_FACTOR_PATHS = ("/totp", "/ipp", "/sk", "/az", "/dp", "/iap", "/selection", "/ootp")

GUARD_JS = """
(() => {
  if (!window.__abClassroom) return;
  const count = (k) => { try { window.__abCount(k); } catch (_) {} };
  for (const type of ["click", "submit", "keydown", "pointerdown", "mousedown"]) {
    window.addEventListener(type, (e) => { e.preventDefault(); e.stopImmediatePropagation(); count("presses"); }, true);
  }
  const block = function () { count("form_submits"); };
  HTMLFormElement.prototype.submit = block;
  HTMLFormElement.prototype.requestSubmit = block;
})();
"""

BROWSER_CHECK_JS = """
() => {
  const f = (iso) => new Intl.DateTimeFormat(navigator.language, { hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
  return {
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    locale: navigator.language,
    winter: f("2026-01-15T07:00:00Z"),
    summer: f("2026-07-15T06:00:00Z"),
  };
}
"""

ACCOUNTS_JS = """
() => {
  const found = new Set();
  for (const e of document.querySelectorAll('[aria-label]')) {
    for (const m of (e.getAttribute('aria-label').match(/[\\w.+-]+@[\\w-]+(\\.[\\w-]+)+/g) || [])) found.add(m.toLowerCase());
  }
  return [...found];
}
"""

CLASSES_JS = """
({ run }) => {
  const X = window.alfabetaExtract;
  const capture = X.captureClasses({ run, doc: document, path: location.pathname, now: () => new Date() });
  return { name: X.fileName(capture), capture };
}
"""

CLASS_JS = """
async ({ run, classId, title, account, pace }) => {
  const X = window.alfabetaExtract;
  const capture = await X.captureClass({
    run, classId, title, account,
    load: X.iframeLoader(window),
    sleep: (ms) => new Promise((r) => setTimeout(r, ms * pace)),
    now: () => new Date(),
    random: Math.random,
  });
  return { name: X.fileName(capture), capture };
}
"""


def emit(event: dict[str, Any]) -> None:
    """One JSON line on stdout; the host reads them as they come."""
    print(json.dumps(event, ensure_ascii=False), flush=True)


class Guard:
    """Request routing by phase (`signin` or `read`), with its counts."""

    def __init__(self) -> None:
        self.phase = "read"
        self.blocked: dict[str, int] = {}
        self.breached = False

    def _count(self, kind: str) -> None:
        self.blocked[kind] = self.blocked.get(kind, 0) + 1

    def allows_document(self, url: str, main_frame: bool) -> bool:
        """Whether a document load may go on in the current phase."""
        parts = urlsplit(url)
        host = parts.hostname or ""
        if host in CLASSROOM_HOSTS and (host not in ACCOUNT_HOSTS or parts.path.startswith("/u/")):
            # Classroom's pages keep their own rule in every phase; only the sign-in's landing (a
            # main frame) may be any Classroom page.
            return bool(CLASSROOM_PAGES.match(parts.path) or (self.phase == "signin" and main_frame))
        if self.phase == "signin" and main_frame and (host in ACCOUNT_HOSTS or host in REDIRECT_HOSTS):
            return True
        return bool(self.phase == "signin" and not main_frame and host in ACCOUNT_HOSTS | REDIRECT_HOSTS)

    def route(self, route: Any, request: Any) -> None:
        """Playwright's route handler: abort and count what the guard refuses."""
        parts = urlsplit(request.url)
        host = parts.hostname or ""
        if host in FORM_HOSTS or (host == "docs.google.com" and parts.path.startswith("/forms")):
            self._count("form_hosts")
            route.abort()
            return
        if host in DOWNLOAD_HOSTS or parts.path.endswith("/export"):
            self._count("downloads")
            route.abort()
            return
        if request.resource_type == "document":
            main_frame = request.frame.parent_frame is None
            if not self.allows_document(request.url, main_frame):
                self._count("pages" if main_frame else "frames")
                route.abort()
                return
        route.continue_()

    def watch(self, request: Any) -> None:
        """Every request, redirects included: Playwright routes only the first URL of a redirect chain.

        A document a server redirected outside what the phase allows has already been fetched when
        it is seen; it is counted and breaks the read, which stops at the next step (FR-030: a
        server-chosen redirect from an allowed GET is the guard's weaker guarantee, never silent).
        Google's own sign-in host in the read phase is the expired session's signal, not a breach.
        """
        if request.redirected_from is None or request.resource_type != "document":
            return
        main_frame = request.frame.parent_frame is None
        if self.allows_document(request.url, main_frame) or kind(request.url).startswith("accounts:"):
            return
        self._count("redirects")
        self.breached = True
        target = kind(request.url)
        # Where it went, by category; a Classroom or Google path holds no account and no query.
        path = urlsplit(request.url).path if target.startswith(("accounts:", "classroom", "redirect")) else ""
        emit({"event": "redirect", "to": target.split(":")[0], "path": path, "main_frame": main_frame})

    def bump(self, kind: str) -> None:
        """A count from the page's guard script (presses, form submits), whatever document or frame."""
        self._count(str(kind))


def kind(url: str) -> str:
    """A page as a category; Google's sign-in pages by path (which holds no account), others never by address."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    if host in CLASSROOM_HOSTS and (host not in ACCOUNT_HOSTS or parts.path.startswith("/u/")):
        return "classroom"
    if host in ACCOUNT_HOSTS:
        return "accounts:" + parts.path
    if host in REDIRECT_HOSTS:
        return "redirect"
    if parts.scheme in ("chrome-error", "about", "chrome"):
        return "internal"
    return "other"


def body_text(page: Any) -> str:
    """The page's visible text in lower case, or empty while it changes."""
    try:
        return (page.inner_text("body", timeout=3000) or "").lower()
    except Exception:
        return ""


def stop_code(category: str, body: str) -> str | None:
    """Why the sign-in must stop on this page, or None while it may go on."""
    if any(mark in body for mark in WRONG_PASSWORD_MARKS):
        return "wrong_password"
    if any(mark in body for mark in CAPTCHA_MARKS):
        return "challenge"
    if category.startswith("accounts:"):
        path = category.removeprefix("accounts:")
        if "/rejected" in path or "deniedsigninrejected" in path:
            return "rejected"
        if "/challenge/" in path and not path.endswith("/challenge/pwd"):
            if path.endswith("/recaptcha"):
                return "challenge"
            if any(path.endswith(p) for p in SECOND_FACTOR_PATHS):
                return "second_factor"
            return "challenge"
        if "/speedbump" in path:
            return "challenge"
        if "/chooser" in path or "/accountchooser" in path:
            return "other_sign_in"
    if category in ("other", "internal"):
        return "other_sign_in"
    return None


def field(page: Any, selector: str) -> Any:
    """The first visible element of `selector`: Google's pages keep hidden inputs beside the real one."""
    return page.locator(selector).filter(visible=True).first


def wait_for(page: Any, selector: str, seconds: float) -> str:
    """`field`, `classroom` or `stop:<code>`; logs each sign-in page by host and path, never a query."""
    end = time.monotonic() + seconds
    last = None
    while time.monotonic() < end:
        category = kind(page.url)
        if category != last:
            parts = urlsplit(page.url)
            host = parts.hostname if category.startswith(("accounts:", "redirect", "classroom")) else "other"
            path = parts.path if category.startswith(("accounts:", "redirect", "classroom")) else ""
            emit({"event": "signin_page", "host": host, "path": path})
            last = category
        if category == "classroom":
            return "classroom"
        code = stop_code(category, body_text(page))
        if code:
            return "stop:" + code
        try:
            if field(page, selector).count():
                return "field"
        except Exception:
            pass
        time.sleep(0.5)
    return "stop:challenge"


def _type(page: Any, selector: str, value: str) -> bool:
    """Fill one field and press Enter; False if the page moved on.

    Playwright's error for a failed fill quotes the value in its call log, so the exception is
    dropped here, never printed or chained (constitution III; FR-031).
    """
    try:
        field(page, selector).fill(value, timeout=10000)
        page.keyboard.press("Enter")
    except Exception:
        return False
    return True


def sign_in(ctx: Any, page: Any, guard: Guard, account: str, password: str | None) -> str | None:
    """None when Classroom is reached, else the stop code."""
    if password is None:
        return "no_password"
    guard.phase = "signin"
    ctx.clear_cookies()  # from a clean start: the account page, never an account chooser (FR-027)
    try:
        page.goto(SIGN_IN_URL, wait_until="domcontentloaded", timeout=45000)
    except Exception:
        return "unreachable"
    step = wait_for(page, EMAIL_FIELD, 30)
    if step == "field":
        if not _type(page, EMAIL_FIELD, account):
            guard.phase = "read"
            return "challenge"
        emit({"event": "typed", "field": "account"})
        step = wait_for(page, PASSWORD_FIELD, 45)
        if step == "field":
            if not _type(page, PASSWORD_FIELD, password):
                guard.phase = "read"
                return "challenge"
            emit({"event": "typed", "field": "password"})
            step = wait_for(page, "#never-shown", 60)
    guard.phase = "read"
    if step == "classroom":
        return None
    return step.removeprefix("stop:") if step.startswith("stop:") else "challenge"


def open_home(page: Any) -> str:
    """`alive`, `expired` or `unreachable`: one load of Classroom's home page."""
    try:
        page.goto(CLASSROOM_HOME, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(int(3000 * PACE) + 500)
    except Exception:
        return "unreachable"
    return "alive" if kind(page.url) == "classroom" else "expired"


def account_matches(page: Any, account: str) -> bool | None:
    """Whether the page names the expected account; None when it names none."""
    found = page.evaluate(ACCOUNTS_JS)
    if not found:
        return None
    return account.strip().lower() in found


def capture(page: Any, guard: Guard, run: str, out: Path) -> dict[str, Any]:
    """The extractor's calls over every class; returns the end event's fields."""
    page.evaluate(EXTRACTOR.read_text())
    listed = page.evaluate(CLASSES_JS, {"run": run})
    out.mkdir(parents=True, exist_ok=True)
    (out / listed["name"]).write_text(json.dumps(listed["capture"], ensure_ascii=False))
    classes = listed["capture"]
    if classes["type"] == "stop":
        return {"outcome": "stopped", "reason": classes["reason"], "classes": {"read": 0, "failed": 0}}
    read, failed, reason = 0, 0, None
    for cls in classes["classes"]:
        if ONLY and cls["id"] not in ONLY:
            continue
        if guard.breached:
            reason = "unexpected_ui"
            break
        try:
            got = page.evaluate(
                CLASS_JS,
                {
                    "run": run,
                    "classId": cls["id"],
                    "title": cls["title"],
                    "account": classes["account_index"],
                    "pace": PACE,
                },
            )
        except Exception:
            failed += 1
            reason = reason or "unexpected_ui"
            emit({"event": "class", "id": cls["id"], "type": "stop", "reason": "unexpected_ui", "complete": False})
            continue
        if guard.breached:  # a redirect outside the allowance during this class: not kept, read stops (FR-030)
            failed += 1
            reason = "unexpected_ui"
            emit({"event": "class", "id": cls["id"], "type": "stop", "reason": "unexpected_ui", "complete": False})
            break
        (out / got["name"]).write_text(json.dumps(got["capture"], ensure_ascii=False))
        c = got["capture"]
        emit(
            {
                "event": "class",
                "id": cls["id"],
                "type": c["type"],
                "reason": c.get("reason"),
                "complete": c.get("complete"),
            }
        )
        if c["type"] == "class":
            read += 1
            continue
        failed += 1
        if c["reason"] == "unexpected_ui":  # FR-008: only that class stops
            reason = reason or "unexpected_ui"
            continue
        reason = c["reason"]  # session_expired (FR-009) or challenge: the rest waits for the next read
        break
    outcome = "ok" if not failed else ("partial" if read else "stopped")
    return {"outcome": outcome, "reason": reason, "classes": {"read": read, "failed": failed}}


def r4_id(url: str) -> str | None:
    """The Drive id an R4 address fetches, or None if it is not one of R4's routes."""
    parts = urlsplit(url)
    origin = f"{parts.scheme}://{parts.netloc}"
    query = parse_qs(parts.query)
    if f"{origin}{parts.path}" == DRIVE_DOWNLOAD:
        ids = query.get("id", [])
        if len(ids) == 1 and query.get("export") == ["download"] and SAFE_ID.match(ids[0]):
            return ids[0]
        return None
    if origin == DOCS_ORIGIN:
        match = DOCS_EXPORT.match(parts.path)
        return match.group(2) if match else None
    return None


def safe_name(name: object) -> bool:
    """One path component: the teacher's file name, never a way out of the inbox folder."""
    return (
        isinstance(name, str)
        and 0 < len(name) <= 255
        and name not in (".", "..")
        and not any(c in name for c in ("/", "\\", "\0"))
    )


def fetch_netlocs() -> set[str]:
    """Where a fetch may go: R4's two origins and the measured redirect hosts."""
    return {urlsplit(DRIVE_DOWNLOAD).netloc, urlsplit(DOCS_ORIGIN).netloc} | set(FETCH_REDIRECT_NETLOCS)


def fetch_one(page: Any, wanted: dict[str, Any], out: Path) -> tuple[str, str | None, str | None]:
    """Fetch one listed attachment: (`brought`|`not_brought`|`refused`|`expired`, why, refused host)."""
    item, attachment, url, name = (wanted.get(k) for k in ("item", "attachment", "url", "expected_name"))
    if not (isinstance(item, str) and SAFE_ID.match(item) and isinstance(attachment, str) and safe_name(name)):
        return "refused", "name", None
    if not isinstance(url, str) or r4_id(url) != attachment or not SAFE_ID.match(attachment):
        return "refused", "route", None
    current = url
    scheme = urlsplit(url).scheme
    for _ in range(FETCH_MAX_HOPS + 1):
        try:
            response = page.request.get(current, max_redirects=0, timeout=FETCH_TIMEOUT_MS, fail_on_status_code=False)
        except Exception:
            return "not_brought", "error", None
        if 300 <= response.status < 400:
            location = response.headers.get("location")
            response.dispose()
            if not location:
                return "not_brought", "redirect", None
            following = urljoin(current, location)
            parts = urlsplit(following)
            if parts.netloc in fetch_netlocs() and parts.scheme == scheme:
                current = following
                continue
            if (parts.hostname or "") in ACCOUNT_HOSTS:
                return "expired", None, None
            return "refused", "host", parts.hostname or ""
        if response.status != 200:
            return "not_brought", f"status_{response.status}", None
        headers = response.headers
        html = headers.get("content-type", "").split(";")[0].strip().lower() == "text/html"
        if html and not str(name).lower().endswith((".html", ".htm")):
            return "not_brought", "html", None
        declared = headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > FETCH_MAX_BYTES:
            return "not_brought", "too_large", None
        body = response.body()
        if len(body) > FETCH_MAX_BYTES:
            return "not_brought", "too_large", None
        # The request context unpacks a compressed body; its Content-Length is then the packed size.
        if declared and declared.isdigit() and not headers.get("content-encoding") and int(declared) != len(body):
            return "not_brought", "length", None
        folder = out / "inbox" / f"{item}__{attachment}"
        folder.mkdir(parents=True, exist_ok=True)
        part = folder / ".part"
        part.write_bytes(body)
        os.replace(part, folder / str(name))  # a read killed mid-write leaves only `.part`, never moved
        return "brought", None, None
    return "not_brought", "redirect", None


def fetch(page: Any, wanted: list[Any], out: Path) -> dict[str, Any]:
    """The attachments pass: each listed attachment once, never retried; an expired session ends it."""
    counts = {"brought": 0, "not_brought": 0, "refused": 0}
    reason = None
    for index, entry in enumerate(wanted):
        result, why, host = fetch_one(page, entry if isinstance(entry, dict) else {}, out)
        if result == "expired":
            reason = "session_expired"
            counts["not_brought"] += len(wanted) - index
            emit({"event": "attachment", "result": "not_brought", "why": "session_expired"})
            break
        counts[result] += 1
        event: dict[str, Any] = {"event": "attachment", "result": result, "why": why}
        if host is not None:
            event["host"] = host
        emit(event)
    return {"outcome": "stopped" if reason else "ok", "reason": reason, "attachments": counts}


def run(request: dict[str, Any]) -> dict[str, Any]:
    """The whole read; returns the end event."""
    from playwright.sync_api import sync_playwright

    started = time.monotonic()
    account = str(request.get("account") or "")
    guard = Guard()
    end: dict[str, Any] = {"event": "end", "outcome": "stopped", "reason": None, "classes": {"read": 0, "failed": 0}}
    PROFILE.mkdir(mode=0o700, parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE),
            channel=CHANNEL,
            headless=True,
            locale=LOCALE,
            timezone_id=TIMEZONE,
            ignore_default_args=IGNORE_DEFAULT_ARGS,
            service_workers="block",  # a worker's requests would not go through the route
        )
        try:
            ctx.add_init_script(
                "window.__abClassroom = "
                + json.dumps(sorted(CLASSROOM_HOSTS))
                + ".includes(location.hostname) && location.pathname.startsWith('/u/');"
            )
            ctx.add_init_script(GUARD_JS)
            ctx.route("**/*", guard.route)
            ctx.on("request", guard.watch)
            ctx.expose_binding("__abCount", lambda _source, kind: guard.bump(kind))
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            emit({"event": "browser", **page.evaluate(BROWSER_CHECK_JS)})
            state = open_home(page)
            if state == "unreachable":
                end["reason"] = "unreachable"
                return end
            fetching = "fetch" in request
            if state == "expired":
                if not request.get("signin") or fetching:  # the attachments pass never signs in
                    end["reason"] = "session_expired"
                    return end
                code = sign_in(ctx, page, guard, account, request.get("password"))
                emit({"event": "signin", "result": code or "signed_in"})
                if code:
                    end["reason"] = code
                    return end
                if open_home(page) != "alive":
                    end["reason"] = "session_expired"
                    return end
            matches = account_matches(page, account)
            if matches is None:
                end["reason"] = "unexpected_ui"
                return end
            if not matches:
                emit({"event": "account", "result": "other_account"})
                end["reason"] = "session_expired"
                return end
            if guard.breached:
                end["reason"] = "unexpected_ui"
                return end
            if fetching:
                end.update(fetch(page, list(request["fetch"]), OUT))
                return end
            end.update(capture(page, guard, str(request["run"]), OUT))
            return end
        finally:
            end["blocked"] = dict(guard.blocked)
            end["seconds"] = int(time.monotonic() - started)
            ctx.close()


def main() -> int:
    """Read the request line, run, print the end event; 0 ok, 3 partial, 1 stopped."""
    line = sys.stdin.readline()
    sys.stdin.close()
    try:
        request = json.loads(line)
    except ValueError:
        emit({"event": "end", "outcome": "stopped", "reason": "unexpected_ui", "classes": {"read": 0, "failed": 0}})
        return 1
    if (
        not isinstance(request, dict)
        or not request.get("account")
        or not request.get("run")
        or ("fetch" in request and not isinstance(request["fetch"], list))
    ):
        emit({"event": "end", "outcome": "stopped", "reason": "unexpected_ui", "classes": {"read": 0, "failed": 0}})
        return 1
    try:
        end = run(request)
    except Exception:
        end = {"event": "end", "outcome": "stopped", "reason": "unexpected_ui", "classes": {"read": 0, "failed": 0}}
    del request
    emit(end)
    return 0 if end["outcome"] == "ok" else 3 if end["outcome"] == "partial" else 1


if __name__ == "__main__":
    sys.exit(main())
