#!/usr/bin/env python3
"""Spike S14, the whole read (#166): sign in, then capture every class with alfabeta's own extractor.

Runs inside the container. It signs in as `s14_scripted_signin.py signin` does (same stops, same
guard), reopens the profile headless, loads Classroom's home page, injects
`skills/classroom-sync/scripts/extract.js` unchanged, and runs the same calls the classroom-sync
skill runs in Chrome: `captureClasses` on the home page, then `captureClass` for each class, one at a
time, each page in the extractor's hidden iframe. Each capture is written to `S14_OUT` (default
`/out`) under the extractor's own file name, `alfabeta-capture-<run>-<owner>-<stamp>.json`, so
`alfabeta download collect` takes them as if Chrome had downloaded them. Read only: the extractor
never clicks, and the guard cancels any press on Classroom.

`ALFABETA_RUN` is the run id `alfabeta lock take` gave; `S14_ONLY` (class ids, comma separated)
limits the capture, for a short test.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import time

import s14_scripted_signin as s14

EXTRACTOR = pathlib.Path(os.environ.get("S14_EXTRACTOR", "/app/extract.js"))
OUT = pathlib.Path(os.environ.get("S14_OUT", "/out"))

CAPTURE_CLASS_JS = """
async ({ run, classId, title, account }) => {
  const X = window.alfabetaExtract;
  const capture = await X.captureClass({
    run, classId, title, account,
    load: X.iframeLoader(window),
    sleep: (ms) => new Promise((r) => setTimeout(r, ms)),
    now: () => new Date(),
    random: Math.random,
  });
  return { name: X.fileName(capture), capture };
}
"""

CAPTURE_CLASSES_JS = """
({ run }) => {
  const X = window.alfabetaExtract;
  const capture = X.captureClasses({ run, doc: document, path: location.pathname, now: () => new Date() });
  return { name: X.fileName(capture), capture };
}
"""


def save(result: dict) -> dict:
    """Writes one capture under the extractor's own name; returns the capture."""
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / result["name"]
    path.write_text(json.dumps(result["capture"], ensure_ascii=False))
    return result["capture"]


def capture(run: str, only: set[str]) -> int:
    from playwright.sync_api import sync_playwright

    started = time.monotonic()
    source = EXTRACTOR.read_text()
    counts = {"loads_allowed": 0, "loads_blocked": 0, "requests_blocked": 0}
    blocked: dict[str, int] = {}
    with sync_playwright() as p:
        ctx = s14.launch(p, headless=True)
        ctx.add_init_script(s14.GUARD_JS)
        ctx.route("**/*", s14.guard_factory(counts, blocked))
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_default_timeout(0)  # a class takes minutes; the extractor has its own page timeouts
        page.goto(s14.CLASSROOM, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(5000)
        if s14.kind(page.url) != "classroom":
            s14.log("CAPTURE_STOP", "session_expired", f"at={s14.kind(page.url).split(':')[0]}")
            ctx.close()
            return 1
        page.evaluate(source)
        classes = save(page.evaluate(CAPTURE_CLASSES_JS, {"run": run}))
        if classes["type"] == "stop":
            s14.log("CAPTURE_STOP", classes["reason"])
            ctx.close()
            return 1
        wanted = [c for c in classes["classes"] if not only or c["id"] in only]
        s14.log(
            "CLASSES",
            f"listed={len(classes['classes'])}",
            f"to_capture={len(wanted)}",
            f"account_index={classes['account_index']}",
        )
        result = 0
        for n, cls in enumerate(wanted, 1):
            t0 = time.monotonic()
            got = save(
                page.evaluate(
                    CAPTURE_CLASS_JS,
                    {"run": run, "classId": cls["id"], "title": cls["title"], "account": classes["account_index"]},
                )
            )
            # The class id is Classroom's, not the student's; titles are never logged.
            s14.log(
                "CLASS",
                f"{n}/{len(wanted)}",
                cls["id"],
                got["type"],
                f"reason={got.get('reason', '-')}",
                f"complete={got.get('complete', '-')}",
                f"items={len(got.get('items', []))}",
                f"posts={len(got.get('stream', []))}",
                f"seconds={int(time.monotonic() - t0)}",
            )
            if got["type"] == "stop":
                result = 1
                break
        presses = page.evaluate("() => window.__s14 || {}")
        ctx.close()
    s14.log(
        "CAPTURE_END",
        f"seconds={int(time.monotonic() - started)}",
        f"page_counts={presses}",
        *(f"{k}={v}" for k, v in counts.items()),
        f"blocked={blocked}",
    )
    return result


def main() -> int:
    run = os.environ.get("ALFABETA_RUN", "").strip()
    if not run:
        s14.log("NO_RUN", "ALFABETA_RUN is empty")
        return 2
    only = {c for c in os.environ.get("S14_ONLY", "").split(",") if c}
    if s14.do_signin(headed=False, settle_seconds=int(os.environ.get("S14_SETTLE", "40"))) != 0:
        return 1
    return capture(run, only)


if __name__ == "__main__":
    sys.exit(main())
