"""S8, last pieces (#267), read-only: the session upkeep, Classroom's other POSTs, and the shape of each call's arguments.

Runs in the read image with --entrypoint python and the read's own Guard, as read.run() installs it; never signs in.
1. Loads «Trabajo de clase», the stream and one assignment's detail of the class s8_calls picks first, 2–3 s apart,
   through a hidden frame, recording for each allowlisted call the shape of its `f.req` arguments: the class, item
   and topic ids the capture holds replaced by CLASS/ITEM/TOPIC, any other digit run of 6+ by N<len>, any other
   string by S<len> (short lower-case words kept, they are enum-like), numbers by «num».
2. Then leaves Classroom's home page open DWELL_MIN minutes and records every request to Google's sign-in and
   cookie hosts (method, host, path without query, frame or page, document or not, blocked or let through) and
   every Classroom request that is not batchexecute (method and path words without digits).
Prints shapes, hosts, paths and counts — never a body, a cookie, a name, a title or an id.
stdin: {"account": "..."}; /captures read-only; /s8 holds s8_calls.py.
"""

from __future__ import annotations

import collections
import json
import random
import re
import sys
import time
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, "/app")
sys.path.insert(0, "/s8")
import read as R  # noqa: E402
import s8_calls as S  # noqa: E402

ALLOW = ("dpT4Vd", "pONvgf", "tQShAc", "ZZFlc", "Zj93ge", "cCzVwf", "t51ITc", "gXtzob", "O1Xqee", "UG41I")
AUTH_HOSTS = ("accounts.google.com", "accounts.google.es", "accounts.youtube.com", "www.google.com", "www.google.es",
              "oauth2.googleapis.com", "content-autofill.googleapis.com")
DWELL_MIN = 10
WORD = re.compile(r"^[a-z_]{1,24}$")


def shape(x, ids, depth=0):
    if depth > 8:
        return "…"
    if isinstance(x, list):
        return [shape(v, ids, depth + 1) for v in x[:12]] + (["+%d" % (len(x) - 12)] if len(x) > 12 else [])
    if isinstance(x, bool) or x is None:
        return x
    if isinstance(x, (int, float)):
        s = str(x)
        return ids.get(s) or ("N%d" % len(s) if s.isdigit() and len(s) >= 6 else "num")
    if isinstance(x, str):
        if x in ids:
            return ids[x]
        if x.isdigit():
            return "N%d" % len(x) if len(x) >= 6 else "digits"
        if WORD.match(x):
            return "w:" + x
        try:
            inner = json.loads(x)
            if isinstance(inner, list):
                return {"json": shape(inner, ids, depth + 1)}
        except ValueError:
            pass
        return "S%d" % len(x)
    return type(x).__name__


def main() -> int:
    req = json.loads(sys.stdin.readline())
    sys.stdin.close()
    from playwright.sync_api import sync_playwright

    cap = S.choose_classes()[0]
    known = S.ids_of(cap)
    ids: dict[str, str] = {}
    for kind, label in (("class", "CLASS"), ("item", "ITEM"), ("topic", "TOPIC"), ("post", "POST"), ("attachment", "ATTACHMENT")):
        for v in known.get(kind, ()):
            ids[str(v)] = label
    ids[cap["class"]["id"]] = "CLASS_B64"
    for i in cap["items"]:
        ids[i["id"]] = "ITEM_B64"

    args: dict[str, list] = collections.defaultdict(list)
    auth: collections.Counter = collections.Counter()
    others: collections.Counter = collections.Counter()
    phase = {"now": "pages"}
    guard = R.Guard()

    def on_request(request):
        parts = urlsplit(request.url)
        host = parts.hostname or ""
        frame = "page" if request.frame.parent_frame is None else "frame"
        if host in AUTH_HOSTS:
            path = "/".join(w if not any(c.isdigit() for c in w) and len(w) < 40 else "ID" for w in parts.path.split("/"))
            auth[(phase["now"], request.method, host, path, frame, request.resource_type)] += 1
        elif host in R.CLASSROOM_HOSTS and request.method == "POST" and not parts.path.endswith("/batchexecute"):
            words = "/".join(w for w in parts.path.split("/") if w and not any(c.isdigit() for c in w))
            others[(phase["now"], words)] += 1
        if parts.path.endswith("/batchexecute"):
            names = [n for n in parse_qs(parts.query).get("rpcids", [""])[0].split(",") if n]
            for n in names:
                if n in ALLOW and len(args[n]) < 2:
                    try:
                        freq = json.loads(parse_qs(request.post_data or "").get("f.req", ["[]"])[0])
                        for c in freq[0]:
                            if isinstance(c, list) and c and c[0] == n:
                                args[n].append({"page": phase["now"], "args": shape(json.loads(c[1]) if isinstance(c[1], str) else c[1], ids)})
                    except Exception:
                        args[n].append({"page": phase["now"], "args": "unparsed"})

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(R.PROFILE), channel=R.CHANNEL, headless=True, locale=R.LOCALE, timezone_id=R.TIMEZONE,
            ignore_default_args=R.IGNORE_DEFAULT_ARGS, service_workers="block",
        )
        try:
            ctx.add_init_script("window.__abClassroom = " + json.dumps(sorted(R.CLASSROOM_HOSTS)) + ".includes(location.hostname) && location.pathname.startsWith('/u/');")
            ctx.add_init_script(R.GUARD_JS)
            ctx.route("**/*", guard.route)
            ctx.on("request", guard.watch)
            ctx.on("request", on_request)
            ctx.expose_binding("__abCount", lambda _s, k: guard.bump(k))
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            phase["now"] = "home"
            st = R.open_home(page)
            print(json.dumps({"home": st}), flush=True)
            if st != "alive":
                return 1
            if R.wait_account(page, req["account"]) is not True:
                print(json.dumps({"account": "no"}))
                return 1
            page.evaluate(R.EXTRACTOR.read_text())
            cid = cap["class"]["id"]
            item = next((i for i in cap["items"] if i["type"] == "assignment"), None)
            paths = [("classwork", f"/u/0/w/{cid}/t/all"), ("stream", f"/u/0/c/{cid}")]
            if item:
                paths.append(("assignment", f"/u/0/c/{cid}/a/{item['id']}/details"))
            for kind, path in paths:
                time.sleep(2 + random.random())
                phase["now"] = kind
                got = page.evaluate(S.LOAD_JS, {"path": path, "dwell": 4000})
                print(json.dumps({"page": kind, "ok": got["ok"]}), flush=True)
            phase["now"] = "dwell"
            t0 = time.monotonic()
            while time.monotonic() - t0 < DWELL_MIN * 60:
                page.wait_for_timeout(30000)
                if guard.breached or "classroom.google.com" not in page.url:
                    print(json.dumps({"dwell_stopped": "breached" if guard.breached else "left classroom"}))
                    break
            print(json.dumps({"dwell_minutes": round((time.monotonic() - t0) / 60, 1), "still_on_classroom": "classroom.google.com" in page.url}))
            for n in ALLOW:
                for a in args.get(n, []):
                    print(json.dumps({"call": n, **a})[:2000])
            for (ph, m, h, pth, fr, rt), c in sorted(auth.items()):
                print(json.dumps({"auth": {"phase": ph, "method": m, "host": h, "path": pth, "in": fr, "type": rt, "count": c}}))
            for (ph, w), c in sorted(others.items()):
                print(json.dumps({"classroom_post": {"phase": ph, "path_words": w, "count": c}}))
            return 0
        finally:
            print(json.dumps({"end": dict(guard.blocked), "breached": guard.breached}))
            ctx.close()


if __name__ == "__main__":
    sys.exit(main())
