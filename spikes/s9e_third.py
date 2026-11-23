"""Spike S9, third measurement (#287), read-only: a whole read by calls, grouped, with what #283 left open.

Run after s9t_templates.py in the same session (it reads /s9out/templates.json). Behind s9_common's routing and the
read's Guard, from one loaded home page, one request at a time, 1–2 s jittered apart (constitution IV). For every class
the home page lists and the refresh captured:
W. the read as it would be built: gXtzob ×2, ZZFlc, dpT4Vd without a topic and per topic, each paged by the token at
   answer [1,1,0] placed at request [0][1]; pONvgf ×3; Zj93ge 12 items a call; t51ITc and cCzVwf K calls a request
   (several calls of one name in one request, told apart by the row index); requests and seconds per class and in all;
P. paging: per list, pages and whether its ids equal the capture's items of that topic (extra / missing counts), and
   for up to three classes the largest topic read 3 a page;
T. t51ITc batched: for the first 5 items of the first 3 classes, one call per item against the batched answers
   (each capture attachment found in both, or not);
M. the mark: over every item with a status, Zj93ge's [32] = 3 against the capture's «falta esto» notice (a 2×2 count);
D. stream-only records: slot, whether tQShAc answers for it, the small values at the paths the others lack.
Prints counts, call names, index paths, small numbers and yes/no. Never a body, a cookie, a name, a title or an id.
stdin: {"account": "...", "run": "<refresh run id>"}; /captures read-only; /s9 this folder; /s9out (templates).
Env: S9_K (calls a request, default 6), S9_BLOCK_BROWSERINFO=1.
"""

from __future__ import annotations

import collections
import copy
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
from s9b_calls import at_path, fill, pick  # noqa: E402
from s9d_followup import SEND_JS, grouped, leaves, records, small  # noqa: E402

R = C.R
TPL = "/s9out/templates.json"
NEVER = frozenset({"O1Xqee", "UG41I"})
GROUP = 12
K = int(os.environ.get("S9_K", "6"))
TOKEN_AT = [1, 1, 0]


def main() -> int:
    req = json.loads(sys.stdin.readline())
    sys.stdin.close()
    from playwright.sync_api import sync_playwright

    tpl = json.load(open(TPL))
    env = tpl["envelope"]
    query = [[k, "WIZ:FdrFJe" if k == "f.sid" else v] for k, v in env["query"]]
    guard = R.Guard()
    routing = C.Routing(guard, block_browserinfo=os.environ.get("S9_BLOCK_BROWSERINFO") == "1")
    state: dict[str, Any] = {"n": 0, "reqid": random.randint(100000, 900000), "stopped": None, "user": None, "extra": 0}

    def on_request(request: Any) -> None:
        if state["user"] or not request.url.split("?")[0].endswith("/batchexecute"):
            return
        try:
            freq = json.loads(parse_qs(request.post_data or "").get("f.req", ["[]"])[0])
            for c in freq[0]:
                if c[0] == "O1Xqee":
                    vals = at_path(json.loads(c[1]), [2, 1, "*", 1, 0])
                    if vals:
                        state["user"] = str(vals[0])
        except Exception:
            return

    def send(page: Any, calls: list[tuple[str, Any]], extra: bool = False, tolerate: bool = False) -> list[Any] | None:
        """One request carrying `calls`; their payloads in order, or None after the stop rule."""
        if state["stopped"] or any(n not in C.ALLOW or n in NEVER for n, _ in calls):
            return None
        time.sleep(1 + random.random())
        state["n"] += 1
        state["extra"] += extra
        state["reqid"] += 100000
        got = page.evaluate(SEND_JS, {"calls": [[n, a] for n, a in calls], "query": query, "body": env["body"],
                                      "headers": env["headers"], "tail": env["tail"], "reqid": state["reqid"]})
        rows = C.answer_rows(got["text"])
        if len(calls) == 1:
            by = [p for n, p, _ in rows if n == calls[0][0]][:1]
        else:
            idx = {str(i): p for _n, p, i in rows}
            by = [idx.get(str(k + 1)) for k in range(len(calls))]
        if tolerate and got["status"] == 200 and not guard.breached and "classroom.google.com" in page.url:
            state["tolerated"] = state.get("tolerated", 0) + sum(1 for p in by if p is None) + len(calls) - len(by)
            return by + [None] * (len(calls) - len(by))
        if got["status"] != 200 or len(by) != len(calls) or any(p is None for p in by) or guard.breached \
                or "classroom.google.com" not in page.url:
            state["stopped"] = {"names": sorted({n for n, _ in calls}), "status": got["status"], "rows": len(rows),
                                "breached": guard.breached}
            return None
        return by

    def one(page: Any, name: str, args: Any, extra: bool = False) -> Any:
        got = send(page, [(name, args)], extra)
        return got[0] if got else None

    def paged(page: Any, args: Any, cls: str, size: int | None = None, extra: bool = False) -> tuple[list, int]:
        a = copy.deepcopy(args)
        if size:
            a[0][0] = size
        out, pages, seen = [], 0, set()
        while pages < 30:
            ans = one(page, "dpT4Vd", a, extra)
            if ans is None:
                break
            pages += 1
            new = records(ans, cls)
            if pages > 1 and not ({i for _s, i, _r in new} - {i for _s, i, _r in out}):
                break
            out += new
            got = at_path(ans, TOKEN_AT)
            tok = got[0] if got and isinstance(got[0], str) else None
            if not tok or tok in seen:
                break
            seen.add(tok)
            a[0][1] = tok
        return out, pages

    with sync_playwright() as p:
        ctx = C.launch(p, guard, routing)
        ctx.on("request", on_request)
        t0 = time.monotonic()
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            st = R.open_home(page)
            C.emit(home=st, browserinfo_blocked=routing.block_browserinfo)
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
            T = {"gX": pick(tpl, "gXtzob", "classwork", {"class"}), "ZZFlc": pick(tpl, "ZZFlc", "classwork", {"class"})[:1],
                 "dp_all": pick(tpl, "dpT4Vd", "classwork", {"class"}, {"topic"})[:1],
                 "dp_topic": pick(tpl, "dpT4Vd", "classwork", {"class", "topic"})[:1], "pO": pick(tpl, "pONvgf", "stream", {"class"}),
                 "Zj": pick(tpl, "Zj93ge", "assignment", {"class", "item", "user"})[:1], "t5": pick(tpl, "t51ITc", "assignment", {"class", "item"})[:1],
                 "cC": pick(tpl, "cCzVwf", "assignment", {"class", "item"})[:1], "tQ": pick(tpl, "tQShAc", "assignment", {"class", "item"})[:1]}
            C.emit(templates={k: len(v) for k, v in T.items()}, k=K)
            if not all(T[k] for k in ("ZZFlc", "dp_all", "dp_topic", "Zj", "t5", "cC")) or not user:
                return 2

            courses = one(page, "gXtzob", pick(tpl, "gXtzob", "home", set())[0])
            listed = [str(v) for v in at_path(courses, [2, "*", 0, 0])]
            caps = [json.load(open(f)) for f in glob.glob(f"/captures/alfabeta-capture-{req['run']}-*.json")]
            caps = {C.b64decode(c["class"]["id"]): c for c in caps if c.get("type") == "class" and c.get("complete")}
            targets = [k for k in dict.fromkeys(listed) if k in caps]
            C.emit(classes_listed=len(set(listed)), targets=len(targets))
            notice = lambda i: "falta esto" in ((i.get("detail") or {}).get("status_notice_text") or "").lower()  # noqa: E731
            mark = collections.Counter()
            totals = collections.Counter()
            paging_tests = 0

            for n, cls in enumerate(targets):
                if state["stopped"]:
                    break
                cap = caps[cls]
                cap_by = {C.b64decode(ci["id"]): ci for ci in cap["items"]}
                cap_topic = collections.defaultdict(set)
                for i, ci in cap_by.items():
                    cap_topic[str(ci.get("topic")) if ci.get("topic") else ""].add(i)
                c = {"class": cls, "user": user}
                tc, n0, x0 = time.monotonic(), state["n"], state["extra"]
                for a in T["gX"][:2]:
                    one(page, "gXtzob", fill(a, c))
                topics = [str(v) for v in at_path(one(page, "ZZFlc", fill(T["ZZFlc"][0], c)), [2, "*", 0, 0])]
                lists: dict[str, list] = {}
                pages_by: dict[str, int] = {}
                lists[""], pages_by[""] = paged(page, fill(T["dp_all"][0], c), cls)
                for tp in topics:
                    lists[tp], pages_by[tp] = paged(page, fill(T["dp_topic"][0], {**c, "topic": tp}), cls)
                # P. each list against the capture's items of that topic
                pg = collections.Counter()
                for tp, recs in lists.items():
                    ids = {i for s, i, _r in recs if s != 2}
                    want = cap_topic.get(tp, set())
                    pg["lists"] += 1
                    pg["multi_page"] += pages_by[tp] > 1
                    pg["equal"] += ids == want
                    pg["extra"] += len(ids - want)
                    pg["extra_in_other_topic"] += len((ids - want) & set(cap_by))
                    pg["missing"] += len(want - ids)
                if paging_tests < 3 and topics:
                    big = max(topics, key=lambda t: len(lists[t]))
                    if len(cap_topic.get(big, ())) >= 4:
                        paging_tests += 1
                        p3, n3 = paged(page, fill(T["dp_topic"][0], {**c, "topic": big}), cls, size=3, extra=True)
                        ids3 = {i for s, i, _r in p3 if s != 2}
                        want = cap_topic.get(big, set())
                        C.emit(part="P", cls=n, topic_size=len(want), pages_by_3=n3, equal=ids3 == want, extra=len(ids3 - want),
                               extra_in_other_topic=len((ids3 - want) & set(cap_by)), missing=len(want - ids3))
                po: list = []
                for a in T["pO"]:
                    ans = one(page, "pONvgf", fill(a, c))
                    po += records(ans, cls) if ans is not None else []
                rec: dict[str, tuple[int, Any]] = {}
                for s, i, r in [x for v in lists.values() for x in v] + po:
                    rec.setdefault(i, (s, r))
                items = list(dict.fromkeys(i for v in lists.values() for s, i, _r in v if s != 2))
                stream_only = list(dict.fromkeys(i for s, i, _r in po if s != 2 and i not in set(items)))
                with_status = [i for i in items if rec[i][0] != 5]
                zj: dict[str, Any] = {}
                zj_fail = collections.Counter()
                for k in range(0, len(with_status), GROUP):
                    got = send(page, [("Zj93ge", grouped(T["Zj"][0], c, with_status[k:k + GROUP]))], tolerate=True)
                    ans = got[0] if got else None
                    if ans is None:
                        zj_fail["groups"] += 1
                        for it in with_status[k:k + GROUP]:
                            g1 = send(page, [("Zj93ge", fill(T["Zj"][0], {**c, "item": it}))], tolerate=True)
                            zj_fail["single_ok" if g1 and g1[0] is not None else "single_failed"] += 1
                            if g1 and g1[0] is not None:
                                for entry in at_path(g1[0], [2, "*"])[:1]:
                                    zj[it] = entry
                        continue
                    for entry in at_path(ans, [2, "*"]):
                        hit = [i for i in with_status[k:k + GROUP] if i in {str(v) for _p, v in leaves(entry) if not small(v)}]
                        if hit:
                            zj[hit[0]] = entry
                t5: dict[str, set] = {}
                for k in range(0, len(items), K):
                    chunk = items[k:k + K]
                    got = send(page, [("t51ITc", fill(T["t5"][0], {**c, "item": i})) for i in chunk], tolerate=True)
                    for i, ans in zip(chunk, got or [None] * len(chunk), strict=True):
                        t5[i] = {str(v) for _p, v in leaves(ans)} if ans is not None else set()
                    send(page, [("cCzVwf", fill(T["cC"][0], {**c, "item": i})) for i in chunk], tolerate=True)
                req_n, req_s = state["n"] - n0 - (state["extra"] - x0), round(time.monotonic() - tc)
                # T. batched t51ITc against one call per item
                tb = collections.Counter()
                if n < 3:
                    for i in items[:5]:
                        single = one(page, "t51ITc", fill(T["t5"][0], {**c, "item": i}), extra=True)
                        ids1 = {str(v) for _p, v in leaves(single)} if single is not None else set()
                        for a in (cap_by.get(i, {}).get("detail") or {}).get("attachments") or []:
                            aid = str(a.get("id"))
                            tb["compared"] += 1
                            tb["single_found"] += aid in ids1
                            tb["batched_found"] += aid in t5.get(i, set())
                            tb["same"] += (aid in ids1) == (aid in t5.get(i, set()))
                # M. the mark against [32] = 3
                for i in with_status:
                    if i in zj and i in cap_by:
                        f32 = at_path(zj[i], [32])
                        mark[f"notice={notice(cap_by[i])},f32_is_3={bool(f32) and f32[0] == 3}"] += 1
                # D. stream-only records
                typical = [rec[i][1] for i in items[:10]]
                common = set.intersection(*[{pth for pth, _v in leaves(t)} for t in typical]) if typical else set()
                for i in stream_only:
                    s, r = rec[i]
                    extra_paths = sorted({pth for pth, _v in leaves(r)} - common)
                    tq = one(page, "tQShAc", fill(T["tQ"][0], {**c, "item": i}), extra=True) if T["tQ"] else None
                    C.emit(part="D", cls=n, slot=s, in_capture=i in cap_by, tqshac_answered=tq is not None,
                           tqshac_records=len(records(tq, cls)) if tq is not None else 0,
                           extra_small=[[list(pth), v] for pth, v in leaves(r) if pth in set(extra_paths) and small(v)][:10],
                           extra_kinds=sorted({type(v).__name__ for pth, v in leaves(r) if pth in set(extra_paths)}))
                att = collections.Counter()
                for i in items:
                    for a in (cap_by.get(i, {}).get("detail") or {}).get("attachments") or []:
                        aid = str(a.get("id"))
                        in_rec = i in rec and aid in {str(v) for _p, v in leaves(rec[i][1])}
                        att[f"record={in_rec},t51={aid in t5.get(i, set())}"] += 1
                totals["requests"] += req_n
                totals["seconds"] += req_s
                totals["items"] += len(items)
                C.emit(part="W", cls=n, items=len(items), capture_items=len(cap_by), same_items=set(items) == set(cap_by),
                       topics=len(topics), requests=req_n, seconds=req_s, attachments=dict(att), stream_only=len(stream_only),
                       paging=dict(pg), zj=dict(zj_fail) or None, tolerated=state.get("tolerated", 0),
                       **({"t51_batched": dict(tb)} if tb else {}))
            C.emit(part="M", counts=dict(mark))
            C.emit(part="W", classes=len(targets), **totals, all_requests=state["n"], stopped=state["stopped"],
                   seconds_all=round(time.monotonic() - t0))
            time.sleep(2 + random.random())
            st2 = R.open_home(page)
            C.emit(survived=st2 == "alive" and R.wait_account(page, req["account"]) is True)
            return 0 if not state["stopped"] else 3
        finally:
            C.emit(end=dict(guard.blocked), breached=guard.breached, browserinfo_seen=routing.seen_browserinfo, rotate=dict(routing.rotate))
            ctx.close()


if __name__ == "__main__":
    sys.exit(main())
