"""Spike S9, second measurement (#283), read-only: what the family's decisions on S9 need measured.

Run after s9t_templates.py in the same session (it reads /s9out/templates.json). Behind s9_common's routing and the
read's Guard, from one loaded home page, one request at a time, 1–2 s jittered apart (constitution IV):
A. the student's number: the home page's own UG41I requests (learnt by s9t, sent as the page sent them) — does
   their answer hold the number the page puts in its own O1Xqee request, and where;
B. grouping: per class, Zj93ge, t51ITc and cCzVwf for 12 items in one call (as the page sends Zj93ge), and once
   two names in one request; their answers against one call per item for the first items (same values or not);
   requests and seconds per class;
C. paging: dpT4Vd with 3 items a page — the next-page token's path in the answer and in the request, pages until
   none, and whether the pages together give the same ids as one call; every item list of this run is paged;
D. the item records only the stream holds: shape, slot, age in days, which index fields differ from the others;
E. the teacher's «missing» mark: for the items whose capture shows it, the index paths of the submission
   (Zj93ge), the record and the materials call where they differ from every other item of the class;
F. the attachments no call returned in S9: for each capture attachment, found or not, by kind; for up to three
   items with one missing, the item's detail page loaded once (hidden frame), and whether any answer of that load
   holds the id, plus the call names the routing blocked on it.
Prints counts, call names, index paths, small numbers and yes/no. Never a body, a cookie, a name, a title or an id.
stdin: {"account": "...", "run": "<refresh run id>"}; /captures read-only; /s9 this folder; /s9out (templates).
Env: S9_CLASSES (default 3), S9_BLOCK_BROWSERINFO=1.
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
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, "/s9")
import s9_common as C  # noqa: E402
from s8_calls import LOAD_JS, ROUTE  # noqa: E402
from s9b_calls import at_path, fill, kinds_in, pick  # noqa: E402

R = C.R
TPL = "/s9out/templates.json"
NEVER = frozenset({"O1Xqee"})
GROUP = 12

SEND_JS = """
async ({ calls, query, body, headers, tail, reqid }) => {
  const w = window.WIZ_global_data || {};
  const names = calls.map((c) => c[0]).join(",");
  const val = (src) => src === "REQID" ? String(reqid) : src === "NAME" ? names : src === "PATH" ? location.pathname
    : src.startsWith("WIZ:") ? String(w[src.slice(4)] ?? "") : src;
  const q = new URLSearchParams();
  for (const [k, src] of query) q.append(k, val(src));
  const b = new URLSearchParams();
  b.append("f.req", JSON.stringify([calls.map((c, i) => [c[0], JSON.stringify(c[1]), tail[0], calls.length > 1 ? String(i + 1) : tail[1]])]));
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


def leaves(x: Any, p: tuple = ()):
    if isinstance(x, list):
        for i, v in enumerate(x):
            yield from leaves(v, p + (i,))
    elif x is not None:
        yield p, x


def small(x: Any) -> bool:
    return isinstance(x, bool) or (isinstance(x, int) and 0 <= x < 100)


def tokens(payload: Any) -> list[tuple[tuple, str]]:
    """Strings outside the item list (payload[2]) that look like a page token: long, not digits, no spaces."""
    out = []
    for p, v in leaves(payload):
        if p[:1] != (2,) and isinstance(v, str) and len(v) >= 12 and not v.isdigit() and " " not in v:
            out.append((p, v))
    return out


def records(ans: Any, cls: str) -> list[tuple[int, str, Any]]:
    """[(slot, id, record)] for every record whose key ans[2][i][slot][0][0] is [id, [class]] of this class."""
    out: list[tuple[int, str, Any]] = []
    for entry in at_path(ans, [2, "*"]):
        if not isinstance(entry, list):
            continue
        for slot, rec in enumerate(entry):
            try:
                key = rec[0][0]
                if isinstance(key, list) and str(key[1][0]) == cls and key[0] is not None:
                    out.append((slot, str(key[0]), rec))
            except (IndexError, TypeError, KeyError):
                continue
    return out


def ph_path(t: Any, kind: str, p: tuple = ()) -> tuple | None:
    """Path of the first {"$": kind} placeholder in a template."""
    if isinstance(t, dict):
        return p if next(iter(t.values())) == kind else None
    if isinstance(t, list):
        for i, v in enumerate(t):
            got = ph_path(v, kind, p + (i,))
            if got is not None:
                return got
    return None


def grouped(tpl_args: Any, c: dict[str, str], ids: list[str]) -> Any:
    """The template filled for ids[0], with the list that holds the [item, [class]] key repeated once per id."""
    p = ph_path(tpl_args, "item")
    a = fill(tpl_args, {**c, "item": ids[0]})
    if p is None or len(p) < 2:
        return a
    holder = a
    for i in p[:-2]:
        holder = holder[i]
    elem = holder[p[-2]]
    holder[:] = [copy.deepcopy(elem) for _ in ids]
    for e, it in zip(holder, ids, strict=True):
        e[p[-1]] = int(it) if isinstance(e[p[-1]], int) else it
    return a


def main() -> int:
    req = json.loads(sys.stdin.readline())
    sys.stdin.close()
    from playwright.sync_api import sync_playwright

    tpl = json.load(open(TPL))
    env = tpl["envelope"]
    query = [[k, "WIZ:FdrFJe" if k == "f.sid" else v] for k, v in env["query"]]
    guard = R.Guard()
    routing = C.Routing(guard, block_browserinfo=os.environ.get("S9_BLOCK_BROWSERINFO") == "1")
    state: dict[str, Any] = {"n": 0, "reqid": random.randint(100000, 900000), "stopped": None, "user": None}
    seen_answers: list[tuple[str, Any]] = []
    record_loads = {"on": False}

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

    def on_response(response: Any) -> None:
        if not record_loads["on"] or not urlsplit(response.url).path.endswith("/batchexecute"):
            return
        try:
            for name, payload, _ in C.answer_rows(response.text()):
                seen_answers.append((name, payload))
        except Exception:
            return

    def send(page: Any, calls: list[tuple[str, Any]]) -> dict[str, Any] | None:
        """One request carrying `calls`; {name: payload} or None after the stop rule."""
        if state["stopped"] or any(n not in C.ALLOW or n in NEVER for n, _ in calls):
            return None
        time.sleep(1 + random.random())
        state["n"] += 1
        state["reqid"] += 100000
        got = page.evaluate(SEND_JS, {"calls": [[n, a] for n, a in calls], "query": query, "body": env["body"],
                                      "headers": env["headers"], "tail": env["tail"], "reqid": state["reqid"]})
        rows = {n: p for n, p, _ in C.answer_rows(got["text"])}
        if got["status"] != 200 or any(n not in rows for n, _ in calls) or guard.breached or "classroom.google.com" not in page.url:
            state["stopped"] = {"names": [n for n, _ in calls], "status": got["status"], "rows": len(rows), "breached": guard.breached}
            return None
        return rows

    def one(page: Any, name: str, args: Any) -> Any:
        rows = send(page, [(name, args)])
        return rows[name] if rows else None

    with sync_playwright() as p:
        ctx = C.launch(p, guard, routing)
        ctx.on("request", on_request)
        ctx.on("response", on_response)
        t0 = time.monotonic()
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            st = R.open_home(page)
            C.emit(home=st, browserinfo_blocked=routing.block_browserinfo)
            if st != "alive" or R.wait_account(page, req["account"]) is not True:
                return 1
            page.wait_for_timeout(1500)
            user = state["user"]

            # A. the student's number from UG41I, sent as the home page sent it
            ug = [e["args"] for e in tpl["calls"].get("UG41I", []) if e["page"] == "home" and not kinds_in(e["args"])]
            for i, a in enumerate(ug[:2]):
                ans = one(page, "UG41I", a)
                hits = [list(pth) for _l, pth in C.find_paths(ans, {user: "U"})] if user and ans is not None else []
                C.emit(part="A", variant=i, answered=ans is not None, holds_number=bool(hits), paths=hits[:3])

            courses = one(page, "gXtzob", pick(tpl, "gXtzob", "home", set())[0])
            listed = {str(v) for v in at_path(courses, [2, "*", 0, 0])}
            caps = [json.load(open(f)) for f in glob.glob(f"/captures/alfabeta-capture-{req['run']}-*.json")]
            caps = {C.b64decode(c["class"]["id"]): c for c in caps if c.get("type") == "class" and c.get("complete")}
            notice = lambda i: "falta esto" in ((i.get("detail") or {}).get("status_notice_text") or "").lower()  # noqa: E731
            order = sorted(caps, key=lambda k: (any(notice(i) for i in caps[k]["items"]), len({i["type"] for i in caps[k]["items"]}),
                                                len(caps[k].get("stream", [])), len(caps[k]["items"])), reverse=True)
            targets = [k for k in order if k in listed][: int(os.environ.get("S9_CLASSES", "3"))]
            C.emit(classes_listed=len(listed), targets=len(targets), with_notice=sum(1 for k in targets if any(notice(i) for i in caps[k]["items"])),
                   notice_items_in_run=sum(1 for c in caps.values() for i in c["items"] if notice(i)))

            T = {"ZZFlc": pick(tpl, "ZZFlc", "classwork", {"class"})[:1], "dp_all": pick(tpl, "dpT4Vd", "classwork", {"class"}, {"topic"})[:1],
                 "dp_topic": pick(tpl, "dpT4Vd", "classwork", {"class", "topic"})[:1], "pO": pick(tpl, "pONvgf", "stream", {"class"}),
                 "Zj": pick(tpl, "Zj93ge", "assignment", {"class", "item", "user"})[:1], "t5": pick(tpl, "t51ITc", "assignment", {"class", "item"})[:1],
                 "cC": pick(tpl, "cCzVwf", "assignment", {"class", "item"})[:1]}
            C.emit(templates={k: len(v) for k, v in T.items()})
            C.emit(item_paths={k: list(ph_path(T[k][0], "item") or []) for k in ("Zj", "t5", "cC") if T[k]})
            page.evaluate(R.EXTRACTOR.read_text())
            if T["dp_all"]:
                C.emit(dp_all_args_shape=C.shape(T["dp_all"][0], {}))
            token_path: dict[str, Any] = {}

            def paged(page: Any, args: Any, cls: str, size: int | None = None) -> tuple[list, int]:
                """Every record of a dpT4Vd list, following the next-page token; (records, pages)."""
                a = copy.deepcopy(args)
                if size:
                    a[0][0] = size
                out, pages, seen_tok = [], 0, set()
                while pages < 30:
                    ans = one(page, "dpT4Vd", a)
                    if ans is None:
                        break
                    pages += 1
                    new = records(ans, cls)
                    if pages > 1 and not ({i for _s, i, _r in new} - {i for _s, i, _r in out}):
                        break  # the token did not move the list: its place in the request is not this one
                    out += new
                    tok = None
                    if "answer" in token_path:
                        got = at_path(ans, list(token_path["answer"]))
                        tok = got[0] if got and isinstance(got[0], str) else None
                    if not tok or tok in seen_tok:
                        break
                    seen_tok.add(tok)
                    a[0][1] = tok
                return out, pages

            for n, cls in enumerate(targets):
                if state["stopped"]:
                    break
                cap = caps[cls]
                c = {"class": cls, "user": user}
                tc, n0 = time.monotonic(), state["n"]
                topics = [str(v) for a in T["ZZFlc"] for v in at_path(one(page, "ZZFlc", fill(a, c)), [2, "*", 0, 0])]
                # C. paging, forced with 3 a page on the list without a topic
                if T["dp_all"] and "answer" not in token_path:
                    a3 = fill(T["dp_all"][0], c)
                    a3[0][0] = 3
                    first = one(page, "dpT4Vd", a3)
                    cand = tokens(first) if first is not None else []
                    C.emit(part="C", first_page_records=len(records(first, cls)) if first else 0, token_candidates=[list(pth) for pth, _ in cand][:4])
                    if cand:
                        token_path["answer"] = cand[0][0]
                full_once = records(one(page, "dpT4Vd", fill(T["dp_all"][0], c)), cls) if T["dp_all"] else []
                by3, pages3 = paged(page, fill(T["dp_all"][0], c), cls, size=3) if T["dp_all"] else ([], 0)
                C.emit(part="C", cls=n, one_call=len({i for _s, i, _r in full_once}), paged_by_3=len({i for _s, i, _r in by3}), pages=pages3,
                       same_ids={i for _s, i, _r in full_once} == {i for _s, i, _r in by3}, token_path_in_answer=list(token_path.get("answer", [])))
                dp_recs = list(by3 or full_once)
                per_topic: dict[str, list] = {}
                for tp in topics:
                    recs, _pg = paged(page, fill(T["dp_topic"][0], {**c, "topic": tp}), cls)
                    per_topic[tp] = recs
                    dp_recs += recs
                if per_topic and "topic_paged" not in state:
                    big = max(per_topic, key=lambda t: len(per_topic[t]))
                    a3 = fill(T["dp_topic"][0], {**c, "topic": big})
                    a3[0][0] = 3
                    first = one(page, "dpT4Vd", a3)
                    cand = tokens(first) if first is not None else []
                    if cand and "answer" not in token_path:
                        token_path["answer"] = cand[0][0]
                    p3, n3 = paged(page, fill(T["dp_topic"][0], {**c, "topic": big}), cls, size=3)
                    state["topic_paged"] = True
                    C.emit(part="C", cls=n, topic_size=len(per_topic[big]), first_page_records=len(records(first, cls)) if first else 0,
                           token_candidates=[list(pth) for pth, _ in cand][:4], paged_by_3=len({i for _s, i, _r in p3}), pages=n3,
                           same_ids={i for _s, i, _r in p3} == {i for _s, i, _r in per_topic[big]})
                po_recs: list = []
                for a in T["pO"]:
                    ans = one(page, "pONvgf", fill(a, c))
                    po_recs += records(ans, cls) if ans is not None else []
                rec: dict[str, tuple[int, Any]] = {}
                for s, i, r in dp_recs + po_recs:
                    rec.setdefault(i, (s, r))
                items = list(dict.fromkeys(i for s, i, _r in dp_recs if s != 2))
                stream_only = list(dict.fromkeys(i for s, i, _r in po_recs if s != 2 and i not in set(items)))
                with_status = [i for i in items if rec[i][0] != 5]
                C.emit(part="C", cls=n, items_paged=len(items), capture_items=len(cap["items"]),
                       same_as_capture={C.b64decode(ci["id"]) for ci in cap["items"]} == set(items), stream_only=len(stream_only))
                # B. grouped calls, 12 items a call, and once two names in one request
                tb, nb = time.monotonic(), state["n"]
                zj: dict[str, Any] = {}
                for k in range(0, len(with_status), GROUP):
                    a = fill(T["Zj"][0], {**c, "item": with_status[k]})
                    a[2][2] = [copy.deepcopy(a[2][2][0]) for _ in with_status[k:k + GROUP]]
                    for e, it in zip(a[2][2], with_status[k:k + GROUP], strict=True):
                        e[1][0] = int(it)
                    ans = one(page, "Zj93ge", a)
                    for entry in at_path(ans, [2, "*"]) if ans is not None else []:
                        hit = [i for i in with_status[k:k + GROUP] if i in {str(v) for _p, v in leaves(entry) if not small(v)}]
                        if hit:
                            zj[hit[0]] = entry
                t5: dict[str, Any] = {}
                for k in range(0, len(items), GROUP):
                    ans = one(page, "t51ITc", grouped(T["t5"][0], c, items[k:k + GROUP]))
                    for i in items[k:k + GROUP]:
                        t5[i] = {str(v) for _p, v in leaves(ans)} if ans is not None else set()
                    one(page, "cCzVwf", grouped(T["cC"][0], c, items[k:k + GROUP]))
                if with_status and items and "pair" not in state:
                    state["pair"] = (fill(T["Zj"][0], {**c, "item": with_status[0]}), fill(T["t5"][0], {**c, "item": items[0]}))
                grouped_s, grouped_n = round(time.monotonic() - tb), state["n"] - nb
                # one call per item for the first five, to compare
                same = collections.Counter()
                for it in with_status[:5]:
                    single = one(page, "Zj93ge", fill(T["Zj"][0], {**c, "item": it}))
                    s20 = at_path(single, [2, 0, 20]) if single is not None else []
                    g20 = at_path(zj.get(it), [20])
                    same["status_same"] += bool(s20) and s20 == g20
                    same["status_compared"] += 1
                for it in items[:5]:
                    single = one(page, "t51ITc", fill(T["t5"][0], {**c, "item": it}))
                    ids1 = {str(v) for _p, v in leaves(single)} if single is not None else set()
                    att = [str(a.get("id")) for ci in cap["items"] if C.b64decode(ci["id"]) == it for a in (ci.get("detail") or {}).get("attachments") or []]
                    same["att_compared"] += len(att)
                    same["att_same"] += sum(1 for a in att if (a in ids1) == (a in t5.get(it, set())))
                C.emit(part="B", cls=n, items=len(items), with_status=len(with_status), grouped_requests=grouped_n, grouped_seconds=grouped_s,
                       class_requests=state["n"] - n0, class_seconds=round(time.monotonic() - tc), zj_entries=len(zj), **same)
                # D. stream-only records
                typical = [rec[i][1] for i in items[:10]]
                for i in stream_only:
                    s, r = rec[i]
                    mine = {pth for pth, v in leaves(r)}
                    common = set.intersection(*[{pth for pth, _v in leaves(t)} for t in typical]) if typical else set()
                    ages = [round((time.time() * 1000 - v) / 86400000) for pth, v in leaves(r) if isinstance(v, int) and 10**12 <= v < 10**13]
                    C.emit(part="D", cls=n, slot=s, in_capture=i in {C.b64decode(ci["id"]) for ci in cap["items"]},
                           missing_common_paths=[list(x) for x in sorted(common - mine)][:8], extra_paths=[list(x) for x in sorted(mine - common)][:8],
                           small_numbers_differing=[[list(pth), v] for pth, v in leaves(r) if small(v) and all(dict(leaves(t)).get(pth) != v for t in typical)][:8],
                           age_days=sorted(set(ages))[:4])
                # E. the teacher's «missing» mark
                cap_by = {C.b64decode(ci["id"]): ci for ci in cap["items"]}
                marked = [i for i in with_status if i in cap_by and notice(cap_by[i])]
                others = [i for i in with_status if i not in marked]
                for i in marked:
                    for label, mine, theirs in (("Zj93ge", zj.get(i), [zj.get(o) for o in others]), ("record", rec[i][1], [rec[o][1] for o in others])):
                        if mine is None:
                            C.emit(part="E", cls=n, source=label, answered=False)
                            continue
                        md = dict(leaves(mine))
                        tds = [dict(leaves(t)) for t in theirs if t is not None]
                        only = [[list(pth), v if small(v) else type(v).__name__] for pth, v in md.items() if all(pth not in t for t in tds)]
                        diff = [[list(pth), v] for pth, v in md.items() if small(v) and tds and all(t.get(pth) != v for t in tds)]
                        C.emit(part="E", cls=n, source=label, status_text=(cap_by[i].get("detail") or {}).get("status_text"), others=len(tds),
                               only_in_marked=only[:10], small_differing=diff[:10])
                # F. attachments
                miss = collections.Counter()
                hard: list[tuple[str, str]] = []
                for i in items:
                    for a in (cap_by.get(i, {}).get("detail") or {}).get("attachments") or []:
                        ok = str(a.get("id")) in t5.get(i, set())
                        miss[f"{a.get('kind')}:{'found' if ok else 'missing'}"] += 1
                        if not ok and len(hard) < 3:
                            hard.append((i, str(a.get("id"))))
                C.emit(part="F", cls=n, attachments=dict(miss))
                for i, aid in hard:
                    ci = cap_by[i]
                    seen_answers.clear()
                    record_loads["on"] = True
                    before = dict(guard.blocked)
                    time.sleep(2 + random.random())
                    got = page.evaluate(LOAD_JS, {"path": f"/u/0/c/{cap['class']['id']}/{ROUTE[ci['type']]}/{ci['id']}/details", "dwell": 4000})
                    record_loads["on"] = False
                    holders = sorted({name for name, payload in seen_answers if aid in {str(v) for _p, v in leaves(payload)}})
                    C.emit(part="F", cls=n, page_ok=got["ok"], answers=len(seen_answers), id_in=holders,
                           blocked_on_page={k: v - before.get(k, 0) for k, v in guard.blocked.items() if v != before.get(k, 0)})
            # B, last: two names in one request (last, since a refusal ends the run by the stop rule)
            if "pair" in state and not state["stopped"]:
                both = send(page, [("Zj93ge", state["pair"][0]), ("t51ITc", state["pair"][1])])
                C.emit(part="B", two_names_one_request=both is not None, stopped_by_it=state["stopped"] is not None)
            C.emit(requests=state["n"], stopped=state["stopped"], seconds=round(time.monotonic() - t0))
            time.sleep(2 + random.random())
            st2 = R.open_home(page)
            C.emit(survived=st2 == "alive" and R.wait_account(page, req["account"]) is True)
            return 0 if not state["stopped"] else 3
        finally:
            C.emit(end=dict(guard.blocked), breached=guard.breached, browserinfo_seen=routing.seen_browserinfo, rotate=dict(routing.rotate))
            ctx.close()


if __name__ == "__main__":
    sys.exit(main())
