#!/usr/bin/env python3
"""Spike S7 (spec 006 research): the sign-in window and the read profile — read only, local only.

`signin` starts the installed Google Chrome on the read profile with `--remote-debugging-pipe`, asks
it `Target.getTargets` every few seconds over fds 3/4 and keeps only each tab's `url`, compared in
memory. The family signs in by hand; nothing here types, clicks or reads the profile's files.
`front` brings a running process to the front by its pid through NSRunningApplication.
`read` opens the same profile headless with Playwright (`channel="chrome"`, keychain flags removed)
behind spec 001 R18's minimal guard (document-load allowlist, zero presses) and loads one Classroom
page. The log holds instants and categories only: never an address, a title, a body or a cookie.
"""

from __future__ import annotations

import argparse
import datetime
import fcntl
import json
import os
import pathlib
import signal
import subprocess
import sys
import time
from urllib.parse import urlsplit

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DATA = pathlib.Path.home() / ".alfabeta" / "s1" / "data"
PROFILE = DATA / "classroom-profile"
LOG = DATA / "spike-166" / "s7.log"
CLASSROOM = "https://classroom.google.com/u/0/h"
SIGN_IN = "https://accounts.google.com/ServiceLogin?service=classroom&continue=" + CLASSROOM
CHALLENGE_MARKS = ("verifica que eres", "demuestra que eres", "verify it", "unusual")


def log(*fields: object) -> None:
    line = "\t".join([datetime.datetime.now().isoformat(timespec="seconds"), *map(str, fields)])
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as handle:
        handle.write(line + "\n")


def kind(url: str) -> str:
    """A tab's address as a category: the address itself is never kept."""
    parts = urlsplit(url)
    if parts.hostname == "classroom.google.com":
        return "classroom"
    if parts.hostname == "accounts.google.com":
        return "accounts-rejected" if "/rejected" in parts.path else "accounts"
    if parts.scheme in ("chrome", "about", "chrome-untrusted", "devtools"):
        return "internal"
    return "other"


class Pipe:
    """Chrome's DevTools pipe: JSON messages ended by a NUL byte, browser-level commands only."""

    def __init__(self, to_chrome: int, from_chrome: int) -> None:
        self.out = os.fdopen(to_chrome, "wb", buffering=0)
        self.inp = os.fdopen(from_chrome, "rb", buffering=0)
        self.next_id = 0
        self.buffer = b""

    def call(self, method: str) -> dict | None:
        self.next_id += 1
        try:
            self.out.write(json.dumps({"id": self.next_id, "method": method}).encode() + b"\0")
        except (BrokenPipeError, OSError):
            return None
        while True:
            while b"\0" not in self.buffer:
                chunk = self.inp.read(65536)
                if not chunk:
                    return None
                self.buffer += chunk
            raw, self.buffer = self.buffer.split(b"\0", 1)
            message = json.loads(raw)
            if message.get("id") == self.next_id:
                return message


def tab_kinds(pipe: Pipe) -> list[str] | None:
    answer = pipe.call("Target.getTargets")
    if answer is None:
        return None
    infos = answer.get("result", {}).get("targetInfos", [])
    return sorted(kind(info.get("url", "")) for info in infos if info.get("type") == "page")


def high_fd(fd: int) -> int:
    moved = fcntl.fcntl(fd, fcntl.F_DUPFD_CLOEXEC, 10)
    os.close(fd)
    return moved


def front(pid: int) -> bool:
    script = (
        'ObjC.import("AppKit");'
        f"var app = $.NSRunningApplication.runningApplicationWithProcessIdentifier({pid});"
        'app.isNil() ? "none" : String(app.activateWithOptions($.NSApplicationActivateIgnoringOtherApps))'
    )
    done = subprocess.run(["osascript", "-l", "JavaScript", "-e", script], capture_output=True, text=True, timeout=30)
    log("FRONT", f"exit={done.returncode}", f"answer={done.stdout.strip() or '-'}", f"stderr={bool(done.stderr.strip())}")
    return done.stdout.strip() == "true"


def stop(chrome: subprocess.Popen) -> str:
    if chrome.poll() is not None:
        return "already-exited"
    chrome.send_signal(signal.SIGTERM)
    try:
        chrome.wait(10)
        return "sigterm"
    except subprocess.TimeoutExpired:
        chrome.kill()
        chrome.wait()
        return "sigkill"


def close(pipe: Pipe, chrome: subprocess.Popen) -> str:
    """Chrome's own orderly close over the pipe, which writes the cookie store; a signal if it hangs."""
    pipe.call("Browser.close")
    try:
        chrome.wait(20)
        return "browser-close"
    except subprocess.TimeoutExpired:
        return stop(chrome)


def cookie_rows() -> str:
    """Spike diagnosis only: Google cookie rows on disk, by name, from a copy; never a value."""
    import shutil
    import sqlite3
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        copy = pathlib.Path(tmp) / "c.db"
        shutil.copy(PROFILE / "Default" / "Cookies", copy)
        row = sqlite3.connect(copy).execute(
            "select count(*), sum(name='SID'), sum(name='__Secure-1PSID') from cookies"
            " where host_key like '%google.com'").fetchone()
    return f"rows={row[0]}\tSID={row[1] or 0}\tSecure_1PSID={row[2] or 0}"


def do_signin(wait_minutes: int, settle_seconds: int) -> int:
    PROFILE.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(PROFILE, 0o700)
    to_chrome_r, to_chrome_w = (high_fd(fd) for fd in os.pipe())
    from_chrome_r, from_chrome_w = (high_fd(fd) for fd in os.pipe())

    def child_fds() -> None:  # Chrome reads commands on fd 3 and writes answers on fd 4
        os.dup2(to_chrome_r, 3)
        os.dup2(from_chrome_w, 4)

    args = [CHROME, f"--user-data-dir={PROFILE}", "--remote-debugging-pipe",
            "--no-first-run", "--no-default-browser-check", SIGN_IN]
    chrome = subprocess.Popen(args, preexec_fn=child_fds, close_fds=False,
                              stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.close(to_chrome_r)
    os.close(from_chrome_w)
    pipe = Pipe(to_chrome_w, from_chrome_r)
    started = time.monotonic()
    log("SIGNIN_START", f"pid={chrome.pid}", f"wait_minutes={wait_minutes}")
    time.sleep(3)
    front(chrome.pid)

    seen, ended_by = None, "timeout"
    while time.monotonic() - started < wait_minutes * 60:
        kinds = tab_kinds(pipe)
        if kinds is None:
            ended_by = "closed"
            break
        if kinds != seen:
            log("TABS", ",".join(kinds) or "-", f"t+{int(time.monotonic() - started)}s")
            seen = kinds
        if "classroom" in kinds:
            ended_by = "address"
            time.sleep(settle_seconds)  # Chrome flushes its cookie store about every 30 s
            break
        time.sleep(3)
    how = close(pipe, chrome) if ended_by == "address" else stop(chrome)
    log("SIGNIN_END", f"ended_by={ended_by}", f"stopped={how}", f"exit={chrome.returncode}",
        f"waited_seconds={int(time.monotonic() - started)}")
    log("DISK", cookie_rows())
    return 0 if ended_by == "address" else 1


GUARD_JS = """
(() => {
  const count = (k) => { window.__s7 = window.__s7 || {}; window.__s7[k] = (window.__s7[k] || 0) + 1; };
  for (const type of ["click", "submit", "keydown", "pointerdown"]) {
    window.addEventListener(type, (e) => { e.preventDefault(); e.stopImmediatePropagation(); count("presses"); }, true);
  }
  const block = function () { count("forms"); };
  HTMLFormElement.prototype.submit = block;
  HTMLFormElement.prototype.requestSubmit = block;
})();
"""

BLOCKED_HOSTS = ("forms.gle", "drive.usercontent.google.com")


def do_read() -> int:
    from importlib.metadata import version

    from playwright.sync_api import Error, sync_playwright

    counts = {"loads_blocked": 0, "loads_allowed": 0, "requests_blocked": 0}
    blocked_hosts: dict[str, int] = {}
    flags = {"session_expired": False}

    def guard(route, request) -> None:
        parts = urlsplit(request.url)
        host = parts.hostname or ""
        if request.resource_type == "document":
            if host == "classroom.google.com" and parts.path.startswith("/u/0/h"):
                counts["loads_allowed"] += 1
                route.continue_()
                return
            if host == "accounts.google.com" and request.frame.parent_frame is None:
                flags["session_expired"] = True
            counts["loads_blocked"] += 1
            blocked_hosts[host] = blocked_hosts.get(host, 0) + 1
            route.abort()
            return
        if host in BLOCKED_HOSTS or (host == "docs.google.com" and parts.path.startswith("/forms")) or "/export" in parts.path:
            counts["requests_blocked"] += 1
            route.abort()
            return
        route.continue_()

    log("READ_START", f"playwright={version('playwright')}")
    started = time.monotonic()
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), channel="chrome", headless=True,
            ignore_default_args=["--use-mock-keychain", "--password-store=basic"])
        ps = subprocess.run(["ps", "-axo", "args"], capture_output=True, text=True).stdout
        mine = [line for line in ps.splitlines() if str(PROFILE) in line]
        log("ARGS", f"processes={len(mine)}",
            f"mock_keychain={any('--use-mock-keychain' in line for line in mine)}",
            f"password_store_basic={any('--password-store=basic' in line for line in mine)}",
            f"headless={any('--headless' in line for line in mine)}")
        jar = ctx.cookies(["https://classroom.google.com", "https://accounts.google.com"])
        names = {cookie["name"] for cookie in jar}
        log("COOKIES", f"count={len(jar)}", f"has_SID={'SID' in names}",
            f"has_Secure_1PSID={'__Secure-1PSID' in names}", f"has_SSID={'SSID' in names}")
        ctx.add_init_script(GUARD_JS)
        ctx.route("**/*", guard)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.on("request", lambda r: r.is_navigation_request() and r.frame == page.main_frame and log(
            "NAV", urlsplit(r.url).hostname, urlsplit(r.url).path, f"redirect={r.redirected_from is not None}"))
        try:
            page.goto(CLASSROOM, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(5000)
            error = None
        except Error as err:
            error = type(err).__name__
        where = kind(page.url)
        sign_in_field = bool(page.query_selector("input[type=email], #identifierId")) if where != "other" else False
        try:
            body = (page.inner_text("body") or "").lower()
        except Error:
            body = ""
        challenge = any(mark in body for mark in CHALLENGE_MARKS)
        presses = page.evaluate("() => (window.__s7 || {})")
        ctx.close()
    if flags["session_expired"] or where == "accounts" or sign_in_field:
        state = "SESSION_EXPIRED"
    elif challenge:
        state = "CHALLENGE"
    elif where == "classroom":
        state = "ALIVE"
    else:
        state = "UNKNOWN"
    log("READ_END", state, f"at={where}", f"goto_error={error or '-'}", f"seconds={int(time.monotonic() - started)}",
        *(f"{k}={v}" for k, v in counts.items()), f"page_counts={json.dumps(presses, sort_keys=True)}",
        f"blocked_load_hosts={json.dumps(blocked_hosts, sort_keys=True)}")
    return 0 if state == "ALIVE" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    signin = sub.add_parser("signin")
    signin.add_argument("--wait-minutes", type=int, default=15)
    signin.add_argument("--settle-seconds", type=int, default=40)
    sub.add_parser("front").add_argument("pid", type=int)
    sub.add_parser("read")
    args = parser.parse_args()
    if args.cmd == "signin":
        return do_signin(args.wait_minutes, args.settle_seconds)
    if args.cmd == "front":
        return 0 if front(args.pid) else 1
    return do_read()


if __name__ == "__main__":
    sys.exit(main())
