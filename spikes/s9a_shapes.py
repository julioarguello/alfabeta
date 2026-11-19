"""Spike S9, step 1 (#279), read-only: the argument shapes and answer shapes of the ten allowlisted calls.

S8's last pieces saw pONvgf, t51ITc and UG41I only from the home page and kept every number as «num». This loads,
for one class of the refresh named on stdin, «Trabajo de clase», the stream and one detail per item type, 2–3 s
apart through the extractor's hidden frame (S8's LOAD_JS), behind s9_common's routing, and prints:
- the request envelope of a batchexecute (query and body parameter names, x- header names, and where each value
  comes from: a WIZ_global_data key, the page path, a literal word or number) — never a value;
- per call name and page kind, up to three distinct shapes of its f.req arguments;
- per call name, the shape of its first non-empty answer from a class page, and where in its answers each kind of
  capture value sits (index paths, counts).
Labels: CLASS, ITEM, TOPIC, POST, ATT_ID… for the capture's values; WIZ:<key> for WIZ_global_data's; ANS:<name> for a
value first seen in that call's answer. Never a body, a cookie, a name, a title or an id.
stdin: {"account": "...", "run": "<refresh run id>"}; /captures read-only; /s9 holds this folder.
"""

from __future__ import annotations

import collections
import glob
import json
import random
import sys
import time
from typing import Any
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, "/s9")
import s9_common as C  # noqa: E402
from s8_calls import LOAD_JS, ROUTE  # noqa: E402

R = C.R
WIZ_JS = """
() => { const w = window.WIZ_global_data || {}; const o = {};
  for (const [k, v] of Object.entries(w)) if (typeof v === "string" || typeof v === "number") o[k] = String(v);
  return o; }
"""


def pick(run: str) -> dict[str, Any]:
    caps = [json.load(open(p)) for p in glob.glob(f"/captures/alfabeta-capture-{run}-*.json")]
    caps = [c for c in caps if c.get("type") == "class" and c.get("complete")]
    caps.sort(key=lambda d: (len({i["type"] for i in d["items"]}), len(d.get("stream", [])), len(d["items"])), reverse=True)
    return caps[0]


def source(value: str, wiz: dict[str, str], path: str) -> str:
    for k, v in wiz.items():
        if v == value and len(v) > 2:
            return "WIZ:" + k
    if value == path or (value and value in path):
        return "PATH" if value == path else "PATH_PART"
    if value.isdigit():
        return "digits%d" % len(value)
    if value in C.VOCAB or len(value) <= 2:
        return "w:" + value
    return "S%d" % len(value)


def main() -> int:
    req = json.loads(sys.stdin.readline())
    sys.stdin.close()
    from playwright.sync_api import sync_playwright

    cap = pick(req["run"])
    cap_lab = C.capture_labels(cap)
    ans_lab: dict[str, str] = {}
    wiz: dict[str, str] = {}
    phase = {"now": "home"}
    raw_args: dict[tuple[str, str], list] = collections.defaultdict(list)
    envelopes: list[tuple[str, Any]] = []
    first_answer: dict[str, Any] = {}
    answers = collections.Counter()
    empty = collections.Counter()
    paths: dict[tuple[str, str], collections.Counter] = collections.defaultdict(collections.Counter)
    pending_paths: list[tuple[str, Any]] = []

    guard = R.Guard()
    routing = C.Routing(guard)

    def on_request(request: Any) -> None:
        parts = urlsplit(request.url)
        if not parts.path.endswith("/batchexecute"):
            return
        try:
            body = parse_qs(request.post_data or "")
            freq = json.loads(body.get("f.req", ["[]"])[0])
        except Exception:
            return
        if len(envelopes) < 3:
            envelopes.append((phase["now"], (parts.path, parse_qs(parts.query), {k: v[0] for k, v in body.items() if k != "f.req"},
                                             {k: v for k, v in request.headers.items() if k.startswith("x-")},
                                             [[c[0], "ARGS", *c[2:]] for c in freq[0] if isinstance(c, list)])))
        for c in freq[0]:
            if isinstance(c, list) and c and c[0] in C.ALLOW:
                try:
                    args = json.loads(c[1]) if isinstance(c[1], str) else c[1]
                except ValueError:
                    args = "unparsed"
                if len(raw_args[(c[0], phase["now"])]) < 12:
                    raw_args[(c[0], phase["now"])].append(args)

    def on_response(response: Any) -> None:
        if not urlsplit(response.url).path.endswith("/batchexecute"):
            return
        try:
            text = response.text()
        except Exception:
            return
        for name, payload, _ in C.answer_rows(text):
            answers[(name, phase["now"])] += 1
            if not payload:
                empty[(name, phase["now"])] += 1
                continue
            if phase["now"] != "home" and name not in first_answer:
                first_answer[name] = payload
            pending_paths.append((name, payload))
            stack = [payload]
            while stack and len(ans_lab) < 200000:
                x = stack.pop()
                if isinstance(x, list):
                    stack.extend(x)
                elif isinstance(x, (str, int)) and not isinstance(x, bool):
                    s = str(x)
                    if len(s) >= 8 and " " not in s and s not in ans_lab:
                        ans_lab[s] = "ANS:" + name

    t_start = time.monotonic()
    with sync_playwright() as p:
        ctx = C.launch(p, guard, routing)
        ctx.on("request", on_request)
        ctx.on("response", on_response)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            st = R.open_home(page)
            C.emit(home=st)
            if st != "alive":
                return 1
            if R.wait_account(page, req["account"]) is not True:
                C.emit(account="no")
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
                    break
            phase["now"] = "end"
            C.emit(classes_items=len(cap["items"]), types=sorted({i["type"] for i in cap["items"]}), stream=len(cap.get("stream", [])),
                   seconds=round(time.monotonic() - t_start))

            labels = {**ans_lab, **{v: "WIZ:" + k for k, v in wiz.items() if len(v) >= 6}, **cap_lab}
            for ph, (path, query, body, headers, freq) in envelopes:
                C.emit(envelope={
                    "page": ph,
                    "path": "/".join("N" if w.isdigit() else w for w in path.split("/")),
                    "query": {k: source(v[0], wiz, "") if k != "source-path" else "PAGE_PATH" for k, v in query.items()},
                    "body": {k: source(v, wiz, "") for k, v in body.items()},
                    "x_headers": {k: source(v, wiz, "") for k, v in headers.items()},
                    "freq_entry": C.shape(freq, labels),
                })
            for (name, ph), lst in sorted(raw_args.items()):
                seen: list[str] = []
                for a in lst:
                    s = json.dumps(C.shape(a, labels, width=20))
                    if s not in seen:
                        seen.append(s)
                for s in seen[:3]:
                    C.emit(call=name, page=ph, args=json.loads(s))
                C.emit(call=name, page=ph, sent=len(lst), distinct=len(seen))
            for (name, ph), n in sorted(answers.items()):
                C.emit(answers=name, page=ph, n=n, empty=empty[(name, ph)])
            for name, payload in pending_paths:
                for label, pth in C.find_paths(payload, cap_lab):
                    paths[(name, label)][pth] += 1
            for (name, label), ctr in sorted(paths.items()):
                C.emit(where=name, label=label, total=sum(ctr.values()), paths=[list(k) for k, _ in ctr.most_common(6)])
            for name, payload in sorted(first_answer.items()):
                C.emit(answer_shape=name, shape=C.shape(payload, labels, width=6))
            return 0
        finally:
            C.emit(end=dict(guard.blocked), breached=guard.breached, browserinfo_seen=routing.seen_browserinfo,
                   rotate=dict(routing.rotate))
            ctx.close()


if __name__ == "__main__":
    sys.exit(main())
