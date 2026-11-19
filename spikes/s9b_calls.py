"""Spike S9, step 2 (#279), read-only: a read by Classroom's own calls, from one loaded home page.

Loads Classroom's home page once (the read's Guard, s9_common's routing: every call outside the allowlist, the
telemetry, push and Google-bar hosts aborted; RotateCookiesPage blocked as in every read; browserinfo aborted when
S9_BLOCK_BROWSERINFO=1), checks the account, then sends the calls of s9b_templates.json one at a time with a 1–2 s
jittered pause (constitution IV), through `fetch` in the page. A call outside the allowlist is refused before it is
sent (and the routing would abort it anyway). It discovers the classes, items and posts from the answers themselves,
by the index paths the templates name; it never takes an id from the capture to send.
Stops at the first non-200, a missing answer row, a page that left Classroom or a breached guard; no retry.
Then loads the home page once more: the session survived if it is still Classroom and the account matches.
The answers are written to /s9out/answers.json (0600, the student's machine only, deleted after the comparison) for
the offline comparison; nothing printed holds a body, a cookie, a name, a title or an id.
stdin: {"account": "...", "run": "<refresh run id>"}; /captures read-only; /s9 holds this folder; /s9out writable.
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
from typing import Any

sys.path.insert(0, "/s9")
import s9_common as C  # noqa: E402

R = C.R
OUT = "/s9out/answers.json"

SEND_JS = """
async ({ name, args, query, body, headers, tail, reqid }) => {
  const w = window.WIZ_global_data || {};
  const val = (src) => src === "REQID" ? String(reqid) : src === "NAME" ? name
    : src.startsWith("WIZ:") ? String(w[src.slice(4)] ?? "") : src;
  const q = new URLSearchParams();
  for (const [k, src] of query) q.append(k, val(src));
  const b = new URLSearchParams();
  b.append("f.req", JSON.stringify([[[name, JSON.stringify(args), ...tail]]]));
  for (const [k, src] of body) b.append(k, val(src));
  const h = { "content-type": "application/x-www-form-urlencoded;charset=UTF-8" };
  for (const [k, v] of Object.entries(headers)) h[k] = v;
  const t0 = performance.now();
  const r = await fetch("/u/0/_/ClassroomUi/data/batchexecute?" + q.toString(), {
    method: "POST", headers: h, body: b.toString() + "&", credentials: "include" });
  const text = await r.text();
  return { status: r.status, text, ms: Math.round(performance.now() - t0) };
}
"""


def fill(t: Any, ctx: dict[str, Any]) -> Any:
    """A template with its placeholders filled: {"$": kind} a string id, {"$#": kind} a number, {"$each": kind, "t": …}."""
    if isinstance(t, list):
        return [fill(v, ctx) for v in t]
    if isinstance(t, dict):
        if "$" in t:
            return str(ctx[t["$"]])
        if "$#" in t:
            return int(ctx[t["$#"]])
        if "$each" in t:
            return [fill(t["t"], {**ctx, t["$each"]: v}) for v in ctx[t["$each"] + "s"]]
        raise ValueError("unknown placeholder")
    return t


def at_path(x: Any, path: list) -> list[Any]:
    """Every value at an index path; «*» walks every element of a list."""
    nodes = [x]
    for step in path:
        nxt = []
        for n in nodes:
            if not isinstance(n, list):
                continue
            if step == "*":
                nxt.extend(n)
            elif isinstance(step, int) and -len(n) <= step < len(n):
                nxt.append(n[step])
        nodes = nxt
    return [n for n in nodes if n is not None]


def payload_of(text: str, name: str) -> tuple[bool, Any]:
    rows = [p for n, p, _ in C.answer_rows(text) if n == name]
    return (bool(rows), rows[0] if rows else None)


def main() -> int:
    req = json.loads(sys.stdin.readline())
    sys.stdin.close()
    from playwright.sync_api import sync_playwright

    tpl = json.load(open("/s9/s9b_templates.json"))
    calls = tpl["calls"]
    bad = [n for n in calls if n not in C.ALLOW or n == "UG41I"]
    if bad:
        C.emit(refused_before_start=bad)
        return 2
    want = int(os.environ.get("S9_CLASSES", "2"))
    guard = R.Guard()
    routing = C.Routing(guard, block_browserinfo=os.environ.get("S9_BLOCK_BROWSERINFO") == "1")
    log: list[dict[str, Any]] = []
    sent = {"n": 0, "reqid": random.randint(100000, 900000)}
    stopped: dict[str, Any] = {}

    def send(page: Any, name: str, args: Any, key: str) -> Any:
        if name not in C.ALLOW or stopped:
            raise RuntimeError("refused")
        time.sleep(1 + random.random())
        sent["n"] += 1
        sent["reqid"] += 100000
        got = page.evaluate(SEND_JS, {"name": name, "args": args, "query": tpl["query"], "body": tpl["body"],
                                      "headers": tpl["headers"], "tail": tpl["freq_tail"], "reqid": sent["reqid"]})
        found, payload = payload_of(got["text"], name)
        log.append({"name": name, "key": key, "status": got["status"], "ms": got["ms"], "text": got["text"]})
        if got["status"] != 200 or not found or guard.breached or "classroom.google.com" not in page.url:
            stopped.update(name=name, status=got["status"], row=found, breached=guard.breached)
        return payload

    t0 = time.monotonic()
    with sync_playwright() as p:
        ctx = C.launch(p, guard, routing)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            st = R.open_home(page)
            C.emit(home=st)
            if st != "alive":
                return 1
            if R.wait_account(page, req["account"]) is not True:
                C.emit(account="no")
                return 1
            page.evaluate(R.EXTRACTOR.read_text())
            listed = page.evaluate(R.CLASSES_JS, {"run": "s9"})["capture"]
            C.emit(home_lists_classes=len(listed.get("classes", [])), browserinfo_blocked=routing.block_browserinfo)
            t_calls = time.monotonic()

            courses = send(page, "gXtzob", fill(calls["gXtzob"]["args"], {}), "once")
            class_ids = [str(v) for v in at_path(courses, calls["gXtzob"]["classes_at"])]
            C.emit(classes_found=len(class_ids))
            # The classes the refresh read completely, best first, as s9a picks; only their ids are compared later.
            import glob
            caps = [json.load(open(f)) for f in glob.glob(f"/captures/alfabeta-capture-{req['run']}-*.json")]
            caps = [c for c in caps if c.get("type") == "class" and c.get("complete")]
            caps.sort(key=lambda d: (len({i["type"] for i in d["items"]}), len(d.get("stream", [])), len(d["items"])), reverse=True)
            targets = [C.b64decode(c["class"]["id"]) for c in caps]
            targets = [t for t in targets if t in class_ids][:want]
            C.emit(targets=len(targets), all_listed=len(caps) == len([t for t in (C.b64decode(c["class"]["id"]) for c in caps) if t in class_ids]))
            per_class: list[dict[str, Any]] = []
            for cls in targets:
                if stopped:
                    break
                tc = time.monotonic()
                cctx: dict[str, Any] = {"class": cls}
                n0 = sent["n"]
                for name in tpl["class_order"]:
                    spec = calls[name]
                    if stopped:
                        break
                    if spec["scope"] == "class":
                        ans = send(page, name, fill(spec["args"], cctx), cls)
                        for kind, path in spec.get("finds", {}).items():
                            cctx[kind + "s"] = [str(v) for v in at_path(ans, path)]
                    elif spec["scope"] == "class_items" and cctx.get("items"):
                        send(page, name, fill(spec["args"], cctx), cls)
                    elif spec["scope"] in ("item", "post"):
                        for one in cctx.get(spec["scope"] + "s", []):
                            if stopped:
                                break
                            send(page, name, fill(spec["args"], {**cctx, spec["scope"]: one}), cls + "/" + one)
                per_class.append({"items": len(cctx.get("items", [])), "posts": len(cctx.get("posts", [])),
                                  "topics": len(cctx.get("topics", [])), "calls": sent["n"] - n0,
                                  "seconds": round(time.monotonic() - tc)})
            for i, pc in enumerate(per_class):
                C.emit(class_index=i, **pc)
            C.emit(calls_sent=sent["n"], call_seconds=round(time.monotonic() - t_calls), stopped=stopped or None,
                   statuses=sorted({e["status"] for e in log}), mean_ms=round(sum(e["ms"] for e in log) / max(1, len(log))))
            with open(OUT, "w") as f:
                json.dump({"run": req["run"], "classes": targets, "log": log}, f)
            os.chmod(OUT, 0o600)
            time.sleep(2 + random.random())
            st2 = R.open_home(page)
            acct = R.wait_account(page, req["account"]) if st2 == "alive" else None
            C.emit(survived=st2 == "alive" and acct is True, home_again=st2,
                   minutes_since_start=round((time.monotonic() - t0) / 60, 1))
            return 0 if not stopped else 3
        finally:
            C.emit(end=dict(guard.blocked), breached=guard.breached, browserinfo_seen=routing.seen_browserinfo,
                   rotate=dict(routing.rotate), seconds=round(time.monotonic() - t0))
            ctx.close()


if __name__ == "__main__":
    sys.exit(main())
