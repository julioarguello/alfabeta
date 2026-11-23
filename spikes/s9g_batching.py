"""Spike S9 (#287 review), read-only: does the page itself send several calls in one request?

Loads the home page, then one class's «Trabajo de clase», stream and one assignment's detail (hidden frame), as s9t
does, and counts, for every batchexecute request the page sends, how many calls its f.req carries and how many names
its rpcids lists. Prints counts and call names only; never a body, a cookie or an id.
stdin: {"account": "...", "run": "<refresh run id>"}; /captures read-only; /s9 this folder.
"""

from __future__ import annotations

import collections
import glob
import json
import os
import sys
import time
from typing import Any
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, "/s9")
import s9_common as C  # noqa: E402
from s8_calls import LOAD_JS, ROUTE  # noqa: E402

R = C.R


def main() -> int:
    req = json.loads(sys.stdin.readline())
    sys.stdin.close()
    from playwright.sync_api import sync_playwright

    guard = R.Guard()
    routing = C.Routing(guard, block_browserinfo=os.environ.get("S9_BLOCK_BROWSERINFO") == "1")
    hist: collections.Counter = collections.Counter()
    multi: collections.Counter = collections.Counter()
    where = {"page": "home"}

    def on_request(request: Any) -> None:
        parts = urlsplit(request.url)
        if not parts.path.endswith("/batchexecute"):
            return
        try:
            calls = json.loads(parse_qs(request.post_data or "").get("f.req", ["[]"])[0])[0]
            rpc = (parse_qs(parts.query).get("rpcids", [""])[0]).split(",")
        except Exception:
            hist["unparsed"] += 1
            return
        hist[f"{where['page']}:calls={len(calls)},rpcids={len(rpc)}"] += 1
        if len(calls) > 1:
            multi["+".join(sorted(c[0] for c in calls))] += 1

    with sync_playwright() as p:
        ctx = C.launch(p, guard, routing)
        ctx.on("request", on_request)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            st = R.open_home(page)
            C.emit(home=st)
            if st != "alive" or R.wait_account(page, req["account"]) is not True:
                return 1
            page.wait_for_timeout(5000)
            caps = [json.load(open(f)) for f in sorted(glob.glob(f"/captures/alfabeta-capture-{req['run']}-*.json"))]
            cap = max((c for c in caps if c.get("type") == "class" and c.get("complete")), key=lambda c: len(c["items"]))
            cid = cap["class"]["id"]
            item = next((i for i in cap["items"] if i["type"] == "assignment"), None)
            paths = [("classwork", f"/u/0/w/{cid}/t/all"), ("stream", f"/u/0/c/{cid}")]
            if item:
                paths.append(("assignment", f"/u/0/c/{cid}/{ROUTE['assignment']}/{item['id']}/details"))
            page.evaluate(R.EXTRACTOR.read_text())
            for name, path in paths:
                where["page"] = name
                time.sleep(2)
                got = page.evaluate(LOAD_JS, {"path": path, "dwell": 5000})
                C.emit(page=name, ok=got["ok"])
            C.emit(requests_by_shape=dict(hist), several_calls=dict(multi))
            return 0
        finally:
            C.emit(end=dict(guard.blocked), breached=guard.breached)
            ctx.close()


if __name__ == "__main__":
    sys.exit(main())
