"""Spike S9, step 1b (#279), read-only: the read by calls' request templates, learnt from the page's own requests.

s9a's shapes cut long field masks («+N») and hid the envelope's literal values, so a request cannot be rebuilt from
them. This loads the same pages as s9a (one class of the refresh on stdin: «Trabajo de clase», the stream, one
detail per item type, through the extractor's hidden frame, behind s9_common's routing) and keeps, per call and page
kind, the distinct f.req arguments with every id of that class replaced by a placeholder: {"$": kind} for a string,
{"$#": kind} for a number (class, item, topic, post, and «user»: a number the page sends that no capture holds and
an answer gave first). It writes them, with the envelope's parameters (each a WIZ_global_data key, the page path,
the call name, the request id, or a literal), to /s9out/templates.json — 0600, the student's data folder, deleted
after S9. It prints only counts, call names, WIZ key names and index paths: where the «user» value can be found
without UG41I (a WIZ key, or a path in another allowlisted call's answer). Never a body, a cookie, a name or an id.
stdin: {"account": "...", "run": "<refresh run id>"}; /captures read-only; /s9 this folder; /s9out writable.
"""

from __future__ import annotations

import collections
import json
import os
import random
import sys
import time
from typing import Any
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, "/s9")
import s9_common as C  # noqa: E402
from s8_calls import LOAD_JS, ROUTE  # noqa: E402
from s9a_shapes import WIZ_JS, pick  # noqa: E402

R = C.R
OUT = "/s9out/templates.json"


def main() -> int:
    req = json.loads(sys.stdin.readline())
    sys.stdin.close()
    from playwright.sync_api import sync_playwright

    cap = pick(req["run"])
    kinds: dict[str, str] = {}
    for v, label in C.capture_labels(cap).items():
        k = {"CLASS": "class", "ITEM": "item", "TOPIC": "topic", "POST": "post", "POST_DEC": "post"}.get(label)
        if k and len(v) >= 6:
            kinds[v] = k
    ans_first: dict[str, str] = {}
    ans_where: dict[str, dict[str, list]] = collections.defaultdict(dict)
    wiz: dict[str, str] = {}
    phase = {"now": "home"}
    raw: dict[tuple[str, str], list] = collections.defaultdict(list)
    envelope: dict[str, Any] = {}
    payloads: list[tuple[str, Any]] = []

    def on_request(request: Any) -> None:
        parts = urlsplit(request.url)
        if not parts.path.endswith("/batchexecute"):
            return
        try:
            body = parse_qs(request.post_data or "")
            freq = json.loads(body.get("f.req", ["[]"])[0])
        except Exception:
            return
        if not envelope and phase["now"] != "home" and wiz:
            def src(k: str, v: str) -> str:
                if k == "rpcids":
                    return "NAME"
                if k == "_reqid":
                    return "REQID"
                if k == "source-path":
                    return "PATH"
                for wk, wv in wiz.items():
                    if wv == v and len(v) > 2:
                        return "WIZ:" + wk
                return v
            envelope.update(
                query=[[k, src(k, v[0])] for k, v in parse_qs(parts.query).items()],
                body=[[k, src(k, v[0])] for k, v in body.items() if k != "f.req"],
                headers={k: v for k, v in request.headers.items() if k.startswith("x-")},
                tail=freq[0][0][2:] if freq and freq[0] else [None, "generic"],
            )
        for c in freq[0] if freq else []:
            if isinstance(c, list) and c and c[0] in C.ALLOW:
                try:
                    raw[(c[0], phase["now"])].append(json.loads(c[1]))
                except (ValueError, TypeError):
                    pass

    def on_response(response: Any) -> None:
        if not urlsplit(response.url).path.endswith("/batchexecute"):
            return
        try:
            text = response.text()
        except Exception:
            return
        for name, payload, _ in C.answer_rows(text):
            if payload:
                payloads.append((name, payload))
                stack = [payload]
                while stack:
                    x = stack.pop()
                    if isinstance(x, list):
                        stack.extend(x)
                    elif isinstance(x, (str, int)) and not isinstance(x, bool) and len(str(x)) >= 8:
                        ans_first.setdefault(str(x), name)

    with sync_playwright() as p:
        guard = R.Guard()
        routing = C.Routing(guard)
        ctx = C.launch(p, guard, routing)
        ctx.on("request", on_request)
        ctx.on("response", on_response)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            st = R.open_home(page)
            C.emit(home=st)
            if st != "alive" or R.wait_account(page, req["account"]) is not True:
                return 1
            wiz.update(page.evaluate(WIZ_JS))
            page.evaluate(R.EXTRACTOR.read_text())
            cid = cap["class"]["id"]
            pages = [("classwork", f"/u/0/w/{cid}/t/all"), ("stream", f"/u/0/c/{cid}")]
            for kind, r in ROUTE.items():
                it = next((i for i in cap["items"] if i["type"] == kind), None)
                if it:
                    pages.append((kind, f"/u/0/c/{cid}/{r}/{it['id']}/details"))
            for kind, path in pages:
                time.sleep(2 + random.random())
                phase["now"] = kind
                got = page.evaluate(LOAD_JS, {"path": path, "dwell": 4000})
                C.emit(page=kind, ok=got["ok"])
                if guard.breached:
                    return 1
            phase["now"] = "end"

            # The numbers the page sends that no capture holds but an answer gave first: the «user».
            users: collections.Counter = collections.Counter()

            def walk(x: Any) -> None:
                if isinstance(x, list):
                    for v in x:
                        walk(v)
                elif isinstance(x, (str, int)) and not isinstance(x, bool):
                    s = str(x)
                    if s not in kinds and s in ans_first and s.isdigit() and len(s) < 13:
                        users[s] += 1

            for (_name, ph), lst in raw.items():
                if ph != "home":
                    for a in lst:
                        walk(a)
            user = users.most_common(1)[0][0] if users else None
            C.emit(user_candidates=len(users), user_first_answer=ans_first.get(user) if user else None)
            if user:
                kinds[user] = "user"

            def tpl(x: Any) -> Any:
                if isinstance(x, list):
                    return [tpl(v) for v in x]
                if isinstance(x, bool) or x is None:
                    return x
                if isinstance(x, (str, int)) and str(x) in kinds:
                    return {"$#" if isinstance(x, int) else "$": kinds[str(x)]}
                return x

            calls: dict[str, list] = collections.defaultdict(list)
            for (name, ph), lst in sorted(raw.items()):
                seen: list[str] = []
                for a in lst:
                    s = json.dumps(tpl(a))
                    if s not in seen:
                        seen.append(s)
                for s in seen[:6]:
                    calls[name].append({"page": ph, "args": json.loads(s)})
                C.emit(call=name, page=ph, sent=len(lst), templates=min(6, len(seen)))

            user_from: dict[str, Any] = {"wiz": [k for k, v in wiz.items() if user and v == user]}
            for name, payload in payloads:
                if user and name != "UG41I" and name not in user_from:
                    hits = [list(pth) for _l, pth in C.find_paths(payload, {user: "U"})]
                    if hits:
                        user_from[name] = hits[:3]
            C.emit(user_wiz_keys=user_from["wiz"], user_in_answers={k: v for k, v in user_from.items() if k != "wiz"})
            C.emit(envelope_query=[k for k, _ in envelope.get("query", [])], envelope_body=[k for k, _ in envelope.get("body", [])],
                   envelope_headers=sorted(envelope.get("headers", {})),
                   literal_query=[k for k, v in envelope.get("query", []) if v not in ("NAME", "REQID", "PATH") and not v.startswith("WIZ:")])
            with open(OUT, "w") as f:
                json.dump({"run": req["run"], "envelope": envelope, "calls": calls, "user_from": user_from}, f)
            os.chmod(OUT, 0o600)
            return 0
        finally:
            C.emit(end=dict(guard.blocked), breached=guard.breached, browserinfo_seen=routing.seen_browserinfo,
                   rotate=dict(routing.rotate))
            ctx.close()


if __name__ == "__main__":
    sys.exit(main())
