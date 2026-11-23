"""Spike S9 (#283 review), read-only: which of the page's own UG41I requests answer with the student's number.

Run after s9t_templates.py in the same session. From one loaded home page, every UG41I template s9t learnt from the
home page, sent once each, 1–2 s apart: the placeholders it carries (kinds only) and whether its answer holds the number
the page puts in its own O1Xqee request. Prints kinds, index paths and yes/no; never a body, a cookie or an id.
"""

from __future__ import annotations

import glob
import json
import os
import random
import sys
import time
from typing import Any
from urllib.parse import parse_qs

sys.path.insert(0, "/s9")
import s9_common as C  # noqa: E402
from s8_calls import LOAD_JS  # noqa: E402
from s9b_calls import at_path, fill, kinds_in  # noqa: E402
from s9d_followup import SEND_JS  # noqa: E402

R = C.R
TPL = "/s9out/templates.json"


def main() -> int:
    req = json.loads(sys.stdin.readline())
    sys.stdin.close()
    from playwright.sync_api import sync_playwright

    tpl = json.load(open(TPL))
    env = tpl["envelope"]
    query = [[k, "WIZ:FdrFJe" if k == "f.sid" else v] for k, v in env["query"]]
    guard = R.Guard()
    routing = C.Routing(guard, block_browserinfo=os.environ.get("S9_BLOCK_BROWSERINFO") == "1")
    state: dict[str, Any] = {"user": None, "reqid": random.randint(100000, 900000)}

    def on_request(request: Any) -> None:
        if state["user"] or not request.url.split("?")[0].endswith("/batchexecute"):
            return
        try:
            for c in json.loads(parse_qs(request.post_data or "").get("f.req", ["[]"])[0])[0]:
                if c[0] == "O1Xqee":
                    vals = at_path(json.loads(c[1]), [2, 1, "*", 1, 0])
                    if vals:
                        state["user"] = str(vals[0])
        except Exception:
            return

    with sync_playwright() as p:
        ctx = C.launch(p, guard, routing)
        ctx.on("request", on_request)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            st = R.open_home(page)
            C.emit(home=st)
            if st != "alive" or R.wait_account(page, req["account"]) is not True:
                return 1
            for _ in range(30):
                if state["user"]:
                    break
                page.wait_for_timeout(500)
            if not state["user"]:  # the home page did not send O1Xqee: one class's stream page does
                first = sorted(glob.glob(f"/captures/alfabeta-capture-{req['run']}-*.json"))
                cid = next((json.load(open(f))["class"]["id"] for f in first if json.load(open(f)).get("type") == "class"), None)
                if cid:
                    page.evaluate(R.EXTRACTOR.read_text())
                    page.evaluate(LOAD_JS, {"path": f"/u/0/c/{cid}", "dwell": 3000})
                    C.emit(user_fallback_page="stream")
            user = state["user"]
            C.emit(user_from_page=bool(user))
            for page_name in ("home", "classwork", "assignment"):
                for i, e in enumerate(e for e in tpl["calls"].get("UG41I", []) if e["page"] == page_name):
                    kinds = sorted(kinds_in(e["args"]))
                    if set(kinds) - {"user"}:
                        C.emit(page=page_name, variant=i, kinds=kinds, sent=False)
                        continue
                    time.sleep(1 + random.random())
                    state["reqid"] += 100000
                    got = page.evaluate(SEND_JS, {"calls": [["UG41I", fill(e["args"], {"user": user})]], "query": query,
                                                  "body": env["body"], "headers": env["headers"], "tail": env["tail"],
                                                  "reqid": state["reqid"]})
                    rows = [pl for n, pl, _ in C.answer_rows(got["text"]) if n == "UG41I"]
                    hits = [list(pth) for _l, pth in C.find_paths(rows[0], {user: "U"})] if rows and user else []
                    C.emit(page=page_name, variant=i, kinds=kinds, sent=True, status=got["status"], answered=bool(rows),
                           holds_number=bool(hits), paths=hits[:3])
            return 0
        finally:
            C.emit(end=dict(guard.blocked), breached=guard.breached)
            ctx.close()


if __name__ == "__main__":
    sys.exit(main())
