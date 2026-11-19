"""Issue #263 research probe, read-only: what Classroom's home page shows per class card, and whether
one class's «Trabajo de clase» listing and stream match its newest capture.

Runs inside alfabeta-classroom-read:<hash> with --entrypoint python; imports /app/read.py and installs
its Guard exactly as read.run() does. Never signs in. Prints only counts, attribute names and yes/no. The `listing` mode was written but not run:
research S15 compared the listing and the stream offline, over the kept captures, instead.
stdin: {"account": "..."}; /captures mounted read-only.
"""

from __future__ import annotations

import glob
import json
import re
import sys
import time
from collections import Counter

sys.path.insert(0, "/app")
import read as R  # noqa: E402

CARDS_JS = r"""
() => {
  const link = (n) => [...n.querySelectorAll("a[href]")].find((a) => /^\/u\/\d+\/c\/[^/?#]+$/.test(a.getAttribute("href")));
  const cards = [...document.querySelectorAll("li")].filter((li) => li.querySelector("h2, h3, [role=heading]") && link(li));
  const out = [];
  const NEW = /nuev|novedad|sin leer|unread|\bnew\b|reciente|actividad|activity/i;
  const DUE = /entrega|vence|vencimiento|mañana|hoy|due|pendiente|para el|próxim/i;
  for (const li of cards) {
    const id = link(li).getAttribute("href").split("/")[4];
    const attrs = new Set();
    const dataAttrs = new Set();
    let ariaN = 0, ariaNew = 0, ariaDue = 0, ariaDigits = 0;
    const all = [li, ...li.querySelectorAll("*")];
    for (const e of all) {
      for (const a of e.getAttributeNames()) { attrs.add(a); if (a.startsWith("data-")) dataAttrs.add(a); }
      const al = e.getAttribute("aria-label");
      if (al) { ariaN++; if (NEW.test(al)) ariaNew++; if (DUE.test(al)) ariaDue++; if (/\d/.test(al)) ariaDigits++; }
    }
    const leaves = [];
    const walk = document.createTreeWalker(li, NodeFilter.SHOW_TEXT);
    while (walk.nextNode()) { const t = walk.currentNode.textContent.trim(); if (t) leaves.push(t); }
    const links = [...li.querySelectorAll("a[href]")].map((a) => a.getAttribute("href"));
    const linkKinds = {};
    for (const h of links) {
      const k = h.replace(/\/u\/\d+\//, "/u/N/").replace(/\/[A-Za-z0-9_-]{8,}/g, "/ID");
      linkKinds[k] = (linkKinds[k] || 0) + 1;
    }
    out.push({
      id,
      elements: all.length,
      attrs: [...attrs].sort(),
      dataAttrs: [...dataAttrs].sort(),
      dataValuesShort: [...li.querySelectorAll("*")].flatMap((e) => e.getAttributeNames().filter((a) => a.startsWith("data-")).map((a) => a + "=" + ((e.getAttribute(a) || "").length))).slice(0, 40),
      aria: { n: ariaN, new: ariaNew, due: ariaDue, digits: ariaDigits },
      leaves: leaves.length,
      leavesNew: leaves.filter((t) => NEW.test(t)).length,
      leavesDue: leaves.filter((t) => DUE.test(t)).length,
      leavesDigitsOnly: leaves.filter((t) => /^\d{1,3}\+?$/.test(t)).length,
      leavesWithDate: leaves.filter((t) => /\d{1,2}\s*(ene|feb|mar|abr|may|jun|jul|ago|sept?|oct|nov|dic)|\d{1,2}:\d{2}|lunes|martes|miércoles|jueves|viernes|sábado|domingo|ayer|hoy|mañana/i.test(t)).length,
      linkKinds,
      textSig: leaves.join("|"),
    });
  }
  const page = {
    cards: cards.length,
    bodyNew: [...document.querySelectorAll("[aria-label]")].filter((e) => NEW.test(e.getAttribute("aria-label"))).length,
  };
  return { page, cards: out };
}
"""

LISTING_JS = r"""
async ({ classId, account }) => {
  const X = window.alfabetaExtract;
  const load = X.iframeLoader(window);
  const t0 = Date.now();
  const cw = await load(`/u/${account}/w/${classId}/t/all`);
  const listing = X.readClasswork(cw.doc);
  await new Promise((r) => setTimeout(r, 2000 + Math.floor(Math.random() * 1000)));
  const st = await load(`/u/${account}/c/${classId}`);
  const stream = X.readStream(st.doc);
  return { listing, stream, ms: Date.now() - t0 };
}
"""


def emit(**kw: object) -> None:
    print(json.dumps(kw, ensure_ascii=False), flush=True)


def two_newest_differ() -> dict[str, bool | None]:
    by: dict[str, list] = {}
    for p in glob.glob("/captures/alfabeta-capture-*.json"):
        try:
            d = json.load(open(p))
        except Exception:
            continue
        if d.get("type") == "class":
            by.setdefault(d["class"]["id"], []).append(d)
    def body(d: dict) -> object:
        return (sorted(json.dumps(i, sort_keys=True) for i in d["items"]), d["topics"], sorted(json.dumps(x, sort_keys=True) for x in d.get("stream", [])))
    out: dict[str, bool | None] = {}
    for k, caps in by.items():
        caps.sort(key=lambda d: d["captured_at"])
        out[k] = None if len(caps) < 2 else body(caps[-1]) != body(caps[-2])
    return out


def newest_captures() -> dict[str, dict]:
    newest: dict[str, dict] = {}
    for p in glob.glob("/captures/alfabeta-capture-*.json"):
        try:
            d = json.load(open(p))
        except Exception:
            continue
        if d.get("type") != "class":
            continue
        k = d["class"]["id"]
        if k not in newest or d["captured_at"] > newest[k]["captured_at"]:
            newest[k] = d
    return newest


def listing_key(items: list[dict]) -> dict[str, str]:
    import base64
    return {base64.b64encode(str(i["numericId"]).encode()).decode().rstrip("="): i.get("listing_date_text", "") for i in items}


def main() -> int:
    req = json.loads(sys.stdin.readline())
    sys.stdin.close()
    account = req["account"]
    mode = req.get("mode", "home")
    from playwright.sync_api import sync_playwright

    guard = R.Guard()
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(R.PROFILE), channel=R.CHANNEL, headless=True, locale=R.LOCALE, timezone_id=R.TIMEZONE,
            ignore_default_args=R.IGNORE_DEFAULT_ARGS, service_workers="block",
        )
        try:
            ctx.add_init_script(
                "window.__abClassroom = " + json.dumps(sorted(R.CLASSROOM_HOSTS))
                + ".includes(location.hostname) && location.pathname.startsWith('/u/');"
            )
            ctx.add_init_script(R.GUARD_JS)
            ctx.route("**/*", guard.route)
            ctx.on("request", guard.watch)
            ctx.expose_binding("__abCount", lambda _s, k: guard.bump(k))
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            state = R.open_home(page)
            emit(step="home", state=state)
            if state != "alive":
                return 1
            matches = R.wait_account(page, account)
            emit(step="account", matches=matches)
            if matches is not True:
                return 1
            page.wait_for_timeout(4000)
            got = page.evaluate(CARDS_JS)
            cards = got["cards"]
            emit(step="page", **got["page"])
            attrs_union = Counter(a for c in cards for a in c["attrs"])
            data_union = Counter(a for c in cards for a in c["dataAttrs"])
            emit(step="card_attrs", attrs=dict(attrs_union), data_attrs=dict(data_union))
            caps = newest_captures()
            differ = two_newest_differ()
            order = [c["id"] for c in cards]
            for n, c in enumerate(cards, 1):
                cap = caps.get(c["id"])
                emit(
                    step="card", index=n, elements=c["elements"], aria=c["aria"], leaves=c["leaves"],
                    leaves_new=c["leavesNew"], leaves_due=c["leavesDue"], leaves_digits_only=c["leavesDigitsOnly"],
                    leaves_with_date=c["leavesWithDate"], link_kinds=c["linkKinds"], data_values_len=c["dataValuesShort"],
                    has_capture=cap is not None, changed_in_last_read=differ.get(c["id"]),
                )
            # Save card text signatures locally (hashes only) for a later comparison.
            import hashlib
            sigs = {c["id"]: hashlib.sha256(c["textSig"].encode()).hexdigest()[:16] for c in cards}
            json.dump(sigs, open(f"/out/card-sigs-{int(time.time())}.json", "w"))
            if mode == "listing":
                page.evaluate(R.EXTRACTOR.read_text())
                account_index = 0
                for n, cid in enumerate(order, 1):
                    cap = caps.get(cid)
                    if guard.breached:
                        emit(step="stop", why="breached")
                        break
                    time.sleep(2.5)
                    try:
                        got = page.evaluate(LISTING_JS, {"classId": cid, "account": account_index})
                    except Exception:
                        emit(step="listing", index=n, error=True)
                        continue
                    now_l = listing_key(got["listing"]["items"])
                    cap_l = {str(i["id"]): i.get("listing_date_text", "") for i in (cap or {}).get("items", [])}
                    # capture ids are the detail-page ids (base64 of numericId); compare by count and texts.
                    now_s = {s.get("id"): (s.get("created_text"), s.get("text"), len(s.get("attachments", []))) for s in got["stream"]}
                    cap_s = {s.get("id"): (s.get("created_text"), s.get("text"), len(s.get("attachments", []))) for s in (cap or {}).get("stream", [])}
                    emit(
                        step="listing", index=n, ms=got["ms"],
                        items_now=len(now_l), items_capture=len(cap_l),
                        listing_ids_equal=set(now_l) == set(cap_l),
                        listing_equal=now_l == cap_l,
                        topics_now=len(got["listing"]["topics"]), topics_capture=len((cap or {}).get("topics", [])),
                        stream_now=len(now_s), stream_capture=len(cap_s),
                        stream_ids_equal=set(now_s) == set(cap_s),
                        stream_equal=now_s == cap_s,
                    )
            return 0
        finally:
            emit(step="end", blocked=dict(guard.blocked), breached=guard.breached)
            ctx.close()


if __name__ == "__main__":
    sys.exit(main())
