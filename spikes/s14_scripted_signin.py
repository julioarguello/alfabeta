#!/usr/bin/env python3
"""Spike S14 (spec 006, #166): the scripted sign-in on the Mac — read only, local only, no evasion.

`signin` opens the installed Google Chrome with Playwright on a profile of its own, types the school
account and the password the family stored in the macOS keychain, and waits for Classroom. It
presses only Google's own «Siguiente» on the sign-in pages. Any page other than the identifier and
the password ones — a «this browser may not be secure» rejection, a challenge, a second factor, the
school's own sign-in, a terms page — stops it: nothing tries to get past a check (constitution III,
IV). Playwright's own flags are kept (navigator.webdriver stays true; no user agent is changed);
only the two keychain flags are removed, as in S7, so the profile's cookies are readable later.
`read` reopens the same profile headless and loads Classroom's home page, as S7's read did.

Claude wrote this script and never runs `signin` against the real account: the family launches it
(constitution III). The password is read from the keychain into memory and typed; it is never
printed, logged, written or passed on a command line. The log keeps instants, categories, and the
path of Google's sign-in pages (never a query, an address of the school's, a title, a body or a
cookie). On a stop, a screenshot is left in the data folder with user-only permissions, for the
family to look at; it may show the account's address, so it never leaves the Mac.

Set-up, once, by the family (the password is asked by `security`, not typed on the command line):
    security add-generic-password -s alfabeta-classroom -a s1 -w
Run:
    uv run --with playwright==1.64.1 python spikes/s14_scripted_signin.py signin [--headed]
    uv run --with playwright==1.64.1 python spikes/s14_scripted_signin.py read
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import subprocess
import sys
import time
import tomllib
from urllib.parse import urlsplit

STUDENT = os.environ.get("S14_STUDENT", "s1")
HOME = pathlib.Path.home() / ".alfabeta" / STUDENT
DATA = HOME / "data"
# A run that must sign in from scratch names a profile of its own (S14_PROFILE=<name>).
PROFILE = DATA / os.environ.get("S14_PROFILE", "classroom-profile-s14")
OUT = DATA / "spike-166"
LOG = OUT / "s14.log"
KEYCHAIN_SERVICE = os.environ.get("S14_KEYCHAIN_SERVICE", "alfabeta-classroom")

# A local fake (tests only) serves /accounts/... and /classroom/... on one origin.
FAKE = os.environ.get("S14_FAKE", "").rstrip("/")
CLASSROOM = f"{FAKE}/classroom/u/0/h" if FAKE else "https://classroom.google.com/u/0/h"
SIGN_IN = (
    f"{FAKE}/accounts/v3/signin/identifier?continue={CLASSROOM}"
    if FAKE
    else "https://accounts.google.com/ServiceLogin?service=classroom&continue=" + CLASSROOM
)

EMAIL_FIELD = "#identifierId, input[name=identifier], input[type=email]"
PASSWORD_FIELD = "input[name=Passwd], input[type=password]"
CHALLENGE_MARKS = (
    "verifica que eres",
    "demuestra que eres",
    "verify it",
    "unusual",
    "tráfico inusual",
    "captcha",
    "no es seguro",
    "may not be secure",
)
# Document loads the sign-in may make, by host; any other is blocked and counted by host.
SIGN_IN_HOSTS = {
    "accounts.google.com",
    "accounts.youtube.com",
    "www.google.com",
    "www.google.es",
    "classroom.google.com",
}
BLOCKED_HOSTS = ("forms.gle", "drive.usercontent.google.com")
# On Classroom only: no press and no form reaches the page (spec 001 R18's minimal guard).
GUARD_JS = """
(() => {
  if (!/(^|\\.)classroom\\.google\\.com$/.test(location.hostname) && !location.pathname.startsWith("/classroom")) return;
  const count = (k) => { window.__s14 = window.__s14 || {}; window.__s14[k] = (window.__s14[k] || 0) + 1; };
  for (const type of ["click", "submit", "keydown", "pointerdown"]) {
    window.addEventListener(type, (e) => { e.preventDefault(); e.stopImmediatePropagation(); count("presses"); }, true);
  }
  const block = function () { count("forms"); };
  HTMLFormElement.prototype.submit = block;
  HTMLFormElement.prototype.requestSubmit = block;
})();
"""


def log(*fields: object) -> None:
    line = "\t".join([datetime.datetime.now().isoformat(timespec="seconds"), *map(str, fields)])
    print(line, flush=True)
    OUT.mkdir(mode=0o700, parents=True, exist_ok=True)
    with LOG.open("a") as handle:
        handle.write(line + "\n")


def kind(url: str) -> str:
    """A page's address as a category; for Google's sign-in, its path (which holds no account)."""
    if FAKE and url.startswith(FAKE):
        path = url[len(FAKE) :].split("?", 1)[0]
        if path.startswith("/classroom"):
            return "classroom"
        if path.startswith("/accounts"):
            return "accounts:" + path[len("/accounts") :]
        return "other"
    parts = urlsplit(url)
    if parts.hostname == "classroom.google.com":
        return "classroom"
    if parts.hostname == "accounts.google.com":
        return "accounts:" + parts.path
    if parts.scheme in ("chrome", "about", "chrome-error"):
        return "internal"
    return "other"  # the school's own sign-in (SSO) included: its address is never kept


def stop_reason(category: str, body: str) -> str | None:
    """Why the sign-in must stop here, or None while it is on a page the script may fill."""
    if category.startswith("accounts:"):
        path = category[len("accounts:") :]
        if "/rejected" in path:
            return "not_secure"
        if "/challenge/" in path and not path.endswith("/challenge/pwd"):
            return "challenge:" + path.rsplit("/", 1)[-1]
        if "/speedbump" in path or "/deniedsigninrejected" in path:
            return "speedbump"
    if "contraseña incorrecta" in body or "wrong password" in body:
        return "wrong_password"  # tried once only: retrying risks locking the account
    if any(mark in body for mark in CHALLENGE_MARKS):
        return "challenge:page"
    if category == "other":
        return "other_sign_in"
    if category == "internal":
        return "navigation_blocked"  # the guard aborted a main-frame load (the school's own sign-in?)
    return None


def account() -> str:
    """The school account: in the cloud from its secret (S14_ACCOUNT), on the Mac from the config."""
    override = os.environ.get("S14_FAKE_ACCOUNT")
    if FAKE and override:
        return override
    if os.environ.get("S14_ACCOUNT"):
        return os.environ["S14_ACCOUNT"].strip()
    with (HOME / "config.toml").open("rb") as handle:
        return tomllib.load(handle)["classroom"]["account"].strip()


def password() -> str:
    """The password: in the cloud Cloud Run injects it from Secret Manager; on the Mac, the keychain."""
    if os.environ.get("S14_PASSWORD"):
        return os.environ.pop("S14_PASSWORD").rstrip("\n")
    done = subprocess.run(
        ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", STUDENT, "-w"],
        capture_output=True,
        text=True,
    )
    if done.returncode != 0 or not done.stdout.strip():
        log("NO_PASSWORD", f"service={KEYCHAIN_SERVICE}", f"exit={done.returncode}")
        sys.exit(3)
    return done.stdout.rstrip("\n")


def body_text(page) -> str:
    try:
        return (page.inner_text("body", timeout=3000) or "").lower()
    except Exception:  # noqa: BLE001 — a page mid-navigation has no body to read
        return ""


def shot(page, name: str) -> None:
    path = OUT / f"s14-{name}-{datetime.datetime.now():%Y%m%d-%H%M%S}.png"
    try:
        page.screenshot(path=str(path))
        os.chmod(path, 0o600)
        log("SCREENSHOT", path.name)
    except Exception as err:  # noqa: BLE001
        log("SCREENSHOT_FAILED", type(err).__name__)


def diagnose(page, who: str) -> None:
    """On a stop, what the page shows, for a run whose screenshot cannot be kept (the cloud).

    Flags for Google's checks, and the page's visible lines with every e-mail address replaced: the
    account never reaches the log. The lines are Google's own wording, not the student's data.
    """
    import re

    flags = page.evaluate(
        """() => ({
          captcha_img: !!document.querySelector('img#captchaimg, img[src*="Captcha"]'),
          recaptcha: !!document.querySelector('iframe[src*="recaptcha"], iframe[title*="reCAPTCHA" i]'),
          password_field: !!document.querySelector('input[type=password]'),
        })"""
    )
    log("DIAG_FLAGS", json.dumps(flags, sort_keys=True))
    try:
        text = page.inner_text("main, [role=main], body", timeout=3000)
    except Exception:  # noqa: BLE001
        text = ""
    lines = [line.strip() for line in text.splitlines() if line.strip()][:20]
    for line in lines:
        line = line.replace(who, "<account>")
        line = re.sub(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", "<email>", line)
        log("DIAG_TEXT", line[:160])


def launch(p, headless: bool):
    PROFILE.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(PROFILE, 0o700)
    return p.chromium.launch_persistent_context(
        str(PROFILE),
        # The installed Google Chrome, as on the Mac; the bundled Chromium only for the local fake.
        channel=None if FAKE and not os.environ.get("S14_CHANNEL") else os.environ.get("S14_CHANNEL", "chrome"),
        headless=headless,
        locale="es-ES",
        ignore_default_args=["--use-mock-keychain", "--password-store=basic"],
    )


def guard_factory(counts: dict, blocked: dict):
    def guard(route, request) -> None:
        parts = urlsplit(request.url)
        host = parts.hostname or ""
        if FAKE and request.url.startswith(FAKE):
            route.continue_()
            return
        if request.resource_type == "document":
            if host in SIGN_IN_HOSTS:
                counts["loads_allowed"] += 1
                route.continue_()
                return
            counts["loads_blocked"] += 1
            # A blocked main-frame load is the school's own sign-in or another site: its host is not kept.
            key = "main_frame" if request.frame.parent_frame is None else host
            blocked[key] = blocked.get(key, 0) + 1
            route.abort()
            return
        if host in BLOCKED_HOSTS or (host == "docs.google.com" and parts.path.startswith("/forms")):
            counts["requests_blocked"] += 1
            route.abort()
            return
        route.continue_()

    return guard


def field(page, selector: str):
    """The first visible element of `selector`: Google's pages keep hidden inputs beside the real one."""
    return page.locator(selector).filter(visible=True).first


def wait_for(page, selector: str, seconds: int) -> str:
    """Waits until `selector` shows or the page stops being one the script may fill."""
    end = time.monotonic() + seconds
    last = None
    while time.monotonic() < end:
        category = kind(page.url)
        if category != last:
            log("PAGE", category)
            last = category
        if category == "classroom":
            return "classroom"
        reason = stop_reason(category, body_text(page))
        if reason:
            return "stop:" + reason
        try:
            if field(page, selector).count():
                return "field"
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1)
    return "stop:timeout"


def do_signin(headed: bool, settle_seconds: int) -> int:
    from importlib.metadata import version

    from playwright.sync_api import sync_playwright

    who, secret = account(), password()
    counts = {"loads_allowed": 0, "loads_blocked": 0, "requests_blocked": 0}
    blocked: dict[str, int] = {}
    started = time.monotonic()
    log("SIGNIN_START", f"playwright={version('playwright')}", f"headless={not headed}", f"fake={bool(FAKE)}")
    outcome = "unknown"
    with sync_playwright() as p:
        ctx = launch(p, headless=not headed)
        ctx.add_init_script(GUARD_JS)
        ctx.route("**/*", guard_factory(counts, blocked))
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(SIGN_IN, wait_until="domcontentloaded", timeout=45000)

        step = wait_for(page, EMAIL_FIELD, 30)
        if step == "field":
            field(page, EMAIL_FIELD).fill(who)
            page.keyboard.press("Enter")  # Google's «Siguiente»
            log("TYPED", "identifier")
            step = wait_for(page, PASSWORD_FIELD, 45)
            if step == "field":
                field(page, PASSWORD_FIELD).fill(secret)
                page.keyboard.press("Enter")
                log("TYPED", "password")
                step = wait_for(page, "#never-shown", 60)
        del secret
        if step == "classroom":
            outcome = "classroom"
            page.wait_for_timeout(settle_seconds * 1000)  # Chrome flushes its cookie store about every 30 s
            cards = page.evaluate("() => document.querySelectorAll('li a[href*=\"/c/\"]').length")
            log("CLASSROOM", f"class_links={cards}", f"page_counts={page.evaluate('() => window.__s14 || {}')}")
        else:
            outcome = step.removeprefix("stop:")
            shot(page, outcome.replace(":", "-"))
            diagnose(page, who)
        ctx.close()  # Playwright's orderly close, which writes the cookie store
    log(
        "SIGNIN_END",
        outcome,
        f"seconds={int(time.monotonic() - started)}",
        *(f"{k}={v}" for k, v in counts.items()),
        f"blocked={blocked}",
    )
    return 0 if outcome == "classroom" else 1


def do_read() -> int:
    from playwright.sync_api import Error, sync_playwright

    started = time.monotonic()
    with sync_playwright() as p:
        ctx = launch(p, headless=True)
        ctx.add_init_script(GUARD_JS)
        counts = {"loads_allowed": 0, "loads_blocked": 0, "requests_blocked": 0}
        blocked: dict[str, int] = {}
        ctx.route("**/*", guard_factory(counts, blocked))
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(CLASSROOM, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(5000)
            error = "-"
        except Error as err:
            error = type(err).__name__
        where = kind(page.url)
        cards = (
            page.evaluate("() => document.querySelectorAll('li a[href*=\"/c/\"]').length")
            if where == "classroom"
            else 0
        )
        ctx.close()
    state = (
        "ALIVE" if where == "classroom" and cards else "SESSION_EXPIRED" if where.startswith("accounts") else "UNKNOWN"
    )
    log(
        "READ_END",
        state,
        f"at={where.split(':')[0]}",
        f"class_links={cards}",
        f"goto_error={error}",
        f"seconds={int(time.monotonic() - started)}",
        *(f"{k}={v}" for k, v in counts.items()),
    )
    return 0 if state == "ALIVE" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    signin = sub.add_parser("signin")
    signin.add_argument("--headed", action="store_true", help="show the window (default: headless)")
    signin.add_argument("--settle-seconds", type=int, default=40)
    sub.add_parser("read")
    args = parser.parse_args()
    if args.cmd == "signin":
        return do_signin(args.headed, args.settle_seconds)
    return do_read()


if __name__ == "__main__":
    sys.exit(main())
