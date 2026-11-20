"""Spike S9, step 2 (#279), read-only: a read by Classroom's own calls, from one loaded home page.

Loads Classroom's home page once (the read's Guard, s9_common's routing: every call outside the allowlist, the
telemetry, push and Google-bar hosts aborted; RotateCookiesPage blocked as in every read; browserinfo aborted when
S9_BLOCK_BROWSERINFO=1), checks the account, then sends calls one at a time with a 1–2 s jittered pause
(constitution IV), through `fetch` in the page, built from s9t's templates (/s9out/templates.json: the page's own
arguments with every id a placeholder). It never sends UG41I nor O1Xqee (R3; O1Xqee holds nothing the capture keeps).
The «user» number Zj93ge needs is taken from the home page's own O1Xqee request (the page sends it on load).
Discovery comes from the answers themselves: classes from gXtzob, topics from ZZFlc, items and posts from dpT4Vd and
pONvgf (records [[id, [class]], …] by slot: 2 = post, any other = item); never an id from the capture.
Per class: gXtzob ×2 (class), ZZFlc, dpT4Vd (no topic, then per topic), pONvgf (stream, no date range); per item:
tQShAc, t51ITc, cCzVwf, and Zj93ge but for slot 5 (materials have no submission); per post: t51ITc, cCzVwf.
Stops at the first non-200, a missing answer row (Zj93ge: after three), a page that left Classroom or a breached
guard; no retry. Then loads the home page once more: the session survived if it is still Classroom with the account.
The answers go to /s9out/answers.json (0600, the student's data folder, deleted after the comparison); nothing printed
holds a body, a cookie, a name, a title or an id.
stdin: {"account": "...", "run": "<refresh run id>"}; /captures read-only; /s9 this folder; /s9out writable.
"""

from __future__ import annotations

import collections
import glob
import json
import os
import random
import sys
import time
from typing import Any

sys.path.insert(0, "/s9")
import s9_common as C  # noqa: E402

R = C.R
TPL = "/s9out/templates.json"
OUT = "/s9out/answers.json"
NEVER = frozenset({"UG41I", "O1Xqee"})

SEND_JS = """
async ({ name, args, query, body, headers, tail, reqid }) => {
  const w = window.WIZ_global_data || {};
  const val = (src) => src === "REQID" ? String(reqid) : src === "NAME" ? name : src === "PATH" ? location.pathname
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
    """A template with its placeholders filled: {"$": kind} as a string, {"$#": kind} as a number."""
    if isinstance(t, list):
        return [fill(v, ctx) for v in t]
    if isinstance(t, dict):
        if "$" in t:
            return str(ctx[t["$"]])
        if "$#" in t:
            return int(ctx[t["$#"]])
        raise ValueError("unknown placeholder")
    return t


def kinds_in(t: Any) -> set[str]:
    if isinstance(t, list):
        return set().union(*(kinds_in(v) for v in t)) if t else set()
    if isinstance(t, dict):
        return {next(iter(t.values()))}
    return set()


def has_big_int(t: Any) -> bool:
    if isinstance(t, list):
        return any(has_big_int(v) for v in t)
    return isinstance(t, int) and not isinstance(t, bool) and abs(t) >= 10**12


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


def records(ans: Any, cls: str) -> list[tuple[int, str]]:
    """[(slot, id)] for every record whose key ans[2][i][slot][0][0] is [id, [class]] of this class."""
    out: list[tuple[int, str]] = []
    for entry in at_path(ans, [2, "*"]):
        if not isinstance(entry, list):
            continue
        for slot, rec in enumerate(entry):
            try:
                key = rec[0][0]
                if isinstance(key, list) and str(key[1][0]) == cls and key[0] is not None:
                    out.append((slot, str(key[0])))
            except (IndexError, TypeError, KeyError):
                continue
    return out


def pick(tpl: dict[str, Any], name: str, page: str, need: set[str], avoid: set[str] = frozenset()) -> list[Any]:
    """The distinct templates of a call from a page kind whose placeholders include `need` and none of `avoid`."""
    return [e["args"] for e in tpl["calls"].get(name, []) if e["page"] == page and need <= kinds_in(e["args"])
            and not (kinds_in(e["args"]) & avoid) and not has_big_int(e["args"])]


def main() -> int:
    req = json.loads(sys.stdin.readline())
    sys.stdin.close()
    from playwright.sync_api import sync_playwright

    tpl = json.load(open(TPL))
    env = tpl["envelope"]
    query = [[k, "WIZ:FdrFJe" if k == "f.sid" else v] for k, v in env["query"]]
    want = int(os.environ.get("S9_CLASSES", "2"))
    guard = R.Guard()
    routing = C.Routing(guard, block_browserinfo=os.environ.get("S9_BLOCK_BROWSERINFO") == "1")
    log: list[dict[str, Any]] = []
    sent = {"n": 0, "reqid": random.randint(100000, 900000), "zj_missing": 0}
    stopped: dict[str, Any] = {}
    page_user: list[str] = []

    def on_request(request: Any) -> None:
        if page_user or not request.url.split("?")[0].endswith("/batchexecute"):
            return
        from urllib.parse import parse_qs
        try:
            freq = json.loads(parse_qs(request.post_data or "").get("f.req", ["[]"])[0])
            for c in freq[0]:
                if c[0] == "O1Xqee":
                    vals = at_path(json.loads(c[1]), [2, 1, "*", 1, 0])
                    if vals:
                        page_user.append(str(vals[0]))
        except Exception:
            return

    def send(page: Any, name: str, args: Any, key: str) -> Any:
        if name not in C.ALLOW or name in NEVER or stopped:
            raise RuntimeError("refused")
        time.sleep(1 + random.random())
        sent["n"] += 1
        sent["reqid"] += 100000
        got = page.evaluate(SEND_JS, {"name": name, "args": args, "query": query, "body": env["body"],
                                      "headers": env["headers"], "tail": env["tail"], "reqid": sent["reqid"]})
        rows = [p for n, p, _ in C.answer_rows(got["text"]) if n == name]
        found = bool(rows)
        log.append({"name": name, "key": key, "status": got["status"], "ms": got["ms"], "row": found,
                    "payload": rows[0] if rows else None})
        if name == "Zj93ge" and not found and got["status"] == 200:
            sent["zj_missing"] += 1
            if sent["zj_missing"] <= 3:
                return None
        if got["status"] != 200 or not found or guard.breached or "classroom.google.com" not in page.url:
            stopped.update(name=name, status=got["status"], row=found, breached=guard.breached)
        return rows[0] if rows else None

    t0 = time.monotonic()
    with sync_playwright() as p:
        ctx = C.launch(p, guard, routing)
        ctx.on("request", on_request)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            st = R.open_home(page)
            C.emit(home=st, browserinfo_blocked=routing.block_browserinfo)
            if st != "alive":
                return 1
            if R.wait_account(page, req["account"]) is not True:
                C.emit(account="no")
                return 1
            page.wait_for_timeout(1500)
            C.emit(user_from_page_request=bool(page_user))
            t_calls = time.monotonic()

            courses = send(page, "gXtzob", pick(tpl, "gXtzob", "home", set())[0], "once")
            class_ids = [str(v) for v in at_path(courses, [2, "*", 0, 0])]
            C.emit(classes_found=len(class_ids))
            caps = [json.load(open(f)) for f in glob.glob(f"/captures/alfabeta-capture-{req['run']}-*.json")]
            caps = [c for c in caps if c.get("type") == "class" and c.get("complete")]
            caps.sort(key=lambda d: (len({i["type"] for i in d["items"]}), len(d.get("stream", [])), len(d["items"])), reverse=True)
            cap_ids = [C.b64decode(c["class"]["id"]) for c in caps]
            C.emit(capture_classes=len(cap_ids), capture_classes_listed=len([c for c in cap_ids if c in class_ids]),
                   listed_not_captured=len([c for c in class_ids if c not in cap_ids]))
            targets = [t for t in cap_ids if t in class_ids][:want]

            T = {
                "gX_class": pick(tpl, "gXtzob", "classwork", {"class"}),
                "ZZFlc": pick(tpl, "ZZFlc", "classwork", {"class"})[:1],
                "dp_all": pick(tpl, "dpT4Vd", "classwork", {"class"}, {"topic"})[:1],
                "dp_topic": pick(tpl, "dpT4Vd", "classwork", {"class", "topic"})[:1],
                "pO_stream": pick(tpl, "pONvgf", "stream", {"class"}),
                "tQ_item": pick(tpl, "tQShAc", "assignment", {"class", "item"})[:1],
                "t5_item": pick(tpl, "t51ITc", "assignment", {"class", "item"})[:1],
                "cC_item": pick(tpl, "cCzVwf", "assignment", {"class", "item"})[:1],
                "Zj_item": pick(tpl, "Zj93ge", "assignment", {"class", "item", "user"})[:1],
                "t5_post": pick(tpl, "t51ITc", "stream", {"class", "post"})[:1],
                "cC_post": pick(tpl, "cCzVwf", "stream", {"class", "post"})[:1],
            }
            C.emit(templates={k: len(v) for k, v in T.items()})
            per_class: list[dict[str, Any]] = []
            for cls in targets:
                if stopped:
                    break
                tc, n0 = time.monotonic(), sent["n"]
                c: dict[str, Any] = {"class": cls, "user": page_user[0] if page_user else None}
                for a in T["gX_class"]:
                    send(page, "gXtzob", fill(a, c), cls)
                topics = [str(v) for a in T["ZZFlc"] for v in at_path(send(page, "ZZFlc", fill(a, c), cls), [2, "*", 0, 0])]
                found: list[tuple[int, str]] = []
                for a in T["dp_all"]:
                    found += records(send(page, "dpT4Vd", fill(a, c), cls), cls)
                for tp in topics:
                    for a in T["dp_topic"]:
                        if not stopped:
                            found += records(send(page, "dpT4Vd", fill(a, {**c, "topic": tp}), cls + "/t"), cls)
                for a in T["pO_stream"]:
                    if not stopped:
                        found += records(send(page, "pONvgf", fill(a, c), cls + "/s"), cls)
                slot_of = {i: s for s, i in found if s != 2}
                items = list(slot_of)
                posts = list(dict.fromkeys(i for s, i in found if s == 2))
                slots = collections.Counter(s for s, _ in dict.fromkeys(found))
                for it in items:
                    for key in ("tQ_item", "t5_item", "cC_item") + (("Zj_item",) if c["user"] and slot_of[it] != 5 else ()):
                        for a in T[key]:
                            if not stopped:
                                send(page, {"tQ": "tQShAc", "t5": "t51ITc", "cC": "cCzVwf", "Zj": "Zj93ge"}[key[:2]], fill(a, {**c, "item": it}), cls + "/i/" + it)
                for po in posts:
                    for key in ("t5_post", "cC_post"):
                        for a in T[key]:
                            if not stopped:
                                send(page, {"t5": "t51ITc", "cC": "cCzVwf"}[key[:2]], fill(a, {**c, "post": po}), cls + "/p/" + po)
                per_class.append({"topics": len(topics), "items": len(items), "posts": len(posts), "slots": dict(slots),
                                  "calls": sent["n"] - n0, "seconds": round(time.monotonic() - tc)})
            for i, pc in enumerate(per_class):
                C.emit(class_index=i, **pc)
            C.emit(calls_sent=sent["n"], call_seconds=round(time.monotonic() - t_calls), stopped=stopped or None,
                   zj_missing=sent["zj_missing"], statuses=sorted({e["status"] for e in log}),
                   by_call=dict(collections.Counter(e["name"] for e in log)),
                   no_row=dict(collections.Counter(e["name"] for e in log if not e["row"])),
                   mean_ms=round(sum(e["ms"] for e in log) / max(1, len(log))))
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
