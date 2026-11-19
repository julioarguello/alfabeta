"""Spike S8 (#267), read-only: the calls Classroom's own pages make, recorded by name and tag only.

Runs in alfabeta-classroom-read:<hash> with --entrypoint python; imports /app/read.py and installs its Guard as
read.run() does. Never signs in: an expired session stops it after one home-page load. Loads each page kind the
read loads for two classes through the extractor's own frame loader, paced as the extractor. Records per request:
method, host, masked path, batchexecute call names; per answer, its protocol tags. In memory only, it checks
which call names' answers carry each kind of id the capture holds. Prints counts, names and tags only — never a
body, a cookie, a name or a title. stdin: {"account": "..."}; /captures mounted read-only; /out for the summary.
"""

from __future__ import annotations

import base64
import collections
import glob
import json
import random
import re
import sys
import time
from typing import Any
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, "/app")
import read as R  # noqa: E402

ROUTE = {"assignment": "a", "material": "m", "question": "mc"}
TAG = re.compile(r"^[a-z]{1,6}\.[a-z]{1,4}$")  # protocol tags such as hrq.crs (seen in the peer project)
NOT_TAGS = {"com", "es", "org", "net", "edu", "eus", "cat", "gal", "io", "gle", "pdf", "jpg", "png", "doc", "docx", "html", "mp4"}
ID_SEGMENT = re.compile(r"/[A-Za-z0-9_-]{8,}")

# The page in a hidden frame, as the extractor loads it, kept for DWELL_MS after it is ready so late calls
# (the non-query ones R3 cares most about) are seen; then removed.
DWELL_MS = 8000
LOAD_JS = """
async ({ path, dwell }) => {
  const X = window.alfabetaExtract;
  const frame = document.createElement("iframe");
  frame.style.cssText = "position:absolute;left:-10000px;width:1200px;height:800px;visibility:hidden";
  frame.src = path;
  document.body.appendChild(frame);
  const t0 = Date.now();
  let ready = false;
  while (Date.now() - t0 < 40000) {
    await new Promise((r) => setTimeout(r, 300));
    let doc = null;
    try { doc = frame.contentDocument; } catch (_) { doc = null; }
    if (doc === null || (doc.location && /accounts\\.google\\.com/.test(doc.location.host))) { frame.remove(); return { ok: false, why: "session_expired", ms: Date.now() - t0 }; }
    if (doc.body && doc.location.href !== "about:blank" && X.pageReady(path, doc)) { ready = true; break; }
  }
  const readyMs = Date.now() - t0;
  await new Promise((r) => setTimeout(r, dwell));
  frame.remove();
  return { ok: ready, why: ready ? null : "timeout", ms: readyMs };
}
"""


def emit(**kw: object) -> None:
    print(json.dumps(kw, ensure_ascii=False), flush=True)


def masked(path: str) -> str:
    """A path with every id-like, dotted or @ segment masked, and the account index as N."""
    out = []
    for seg in path.split("/"):
        if seg.isdigit() and len(seg) <= 2:
            out.append("N")
        elif len(seg) >= 8 or "." in seg or "@" in seg or any(c.isdigit() for c in seg):
            out.append("ID")
        else:
            out.append(seg)
    return "/".join(out)


def answer_rows(text: str) -> list[tuple[str, Any]]:
    """batchexecute answer → [(call name, parsed payload)], ignoring what is not a wrb.fr row."""
    rows: list[tuple[str, Any]] = []
    body = text[text.find("\n") + 1:] if text.startswith(")]}'") else text
    # Length-prefixed chunks: a decimal line, then that JSON. Parse every line that is a JSON array.
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("["):
            continue
        try:
            chunk = json.loads(line)
        except ValueError:
            continue
        for row in chunk if isinstance(chunk, list) else []:
            if isinstance(row, list) and len(row) >= 3 and row[0] == "wrb.fr" and isinstance(row[1], str):
                payload = None
                if isinstance(row[2], str):
                    try:
                        payload = json.loads(row[2])
                    except ValueError:
                        payload = None
                rows.append((row[1], payload))
    return rows


def strings(node: Any, out: list[str], limit: int = 200000) -> None:
    """Every string and number in a payload, as text (in memory only)."""
    stack = [node]
    while stack and len(out) < limit:
        x = stack.pop()
        if isinstance(x, list):
            stack.extend(x)
        elif isinstance(x, dict):
            stack.extend(x.values())
        elif isinstance(x, (str, int)) and not isinstance(x, bool):
            out.append(str(x))


def tags_of(payload: Any) -> list[str]:
    found: list[str] = []
    strings(payload, found, 50000)
    return sorted({s for s in found if TAG.match(s) and s.split(".")[1] not in NOT_TAGS})[:8]


def b64decode(text: str) -> str:
    try:
        return base64.b64decode(text + "=" * (-len(text) % 4)).decode()
    except Exception:
        return ""


def choose_classes() -> list[dict[str, Any]]:
    newest: dict[str, dict] = {}
    for p in glob.glob("/captures/alfabeta-capture-*.json"):
        d = json.load(open(p))
        if d.get("type") == "class" and d.get("complete"):
            k = d["class"]["id"]
            if k not in newest or d["captured_at"] > newest[k]["captured_at"]:
                newest[k] = d
    ranked = sorted(newest.values(), key=lambda d: (len({i["type"] for i in d["items"]}), len(d.get("stream", [])), len(d["items"])), reverse=True)
    return ranked[:2]


def ids_of(cap: dict[str, Any]) -> dict[str, set[str]]:
    ids: dict[str, set[str]] = collections.defaultdict(set)
    ids["class"].add(b64decode(cap["class"]["id"]) or cap["class"]["id"])
    for t in cap.get("topics", []):
        if t.get("id"):
            ids["topic"].add(str(t["id"]))
    for i in cap["items"]:
        ids["item"].add(b64decode(i["id"]) or i["id"])
        if i.get("title"):
            ids["item_title"].add(i["title"])
        for a in (i.get("detail") or {}).get("attachments") or []:
            if a.get("id"):
                ids["attachment"].add(a["id"])
            if a.get("name"):
                ids["attachment_name"].add(a["name"])
        if (i.get("detail") or {}).get("description"):
            ids["description"].add(i["detail"]["description"])
    for s in cap.get("stream", []):
        if s.get("id"):
            ids["post"].add(str(s["id"]))
        if s.get("text"):
            ids["post_text"].add(s["text"])
        for a in s.get("attachments") or []:
            if a.get("id"):
                ids["attachment"].add(a["id"])
    return ids


def main() -> int:
    req = json.loads(sys.stdin.readline())
    sys.stdin.close()
    from playwright.sync_api import sync_playwright

    guard = R.Guard()
    requests: collections.Counter[tuple[str, str, str, str]] = collections.Counter()
    calls: collections.Counter[str] = collections.Counter()  # call name → requests naming it
    batched: collections.Counter[int] = collections.Counter()  # how many names per batchexecute request
    answers: dict[str, set[str]] = collections.defaultdict(set)  # call name → protocol tags seen
    answer_count: collections.Counter[str] = collections.Counter()
    unread: collections.Counter[str] = collections.Counter()
    untagged: collections.Counter[str] = collections.Counter()  # answers of a call with no protocol tag found
    body_names_match: collections.Counter[str] = collections.Counter()  # yes/no: POST body names == rpcids
    preloaded: dict[str, set[str]] = collections.defaultdict(set)  # page kind → call ids in AF_dataServiceRequests
    seen_by_page: dict[str, set[str]] = collections.defaultdict(set)
    payload_strings: dict[str, set[str]] = collections.defaultdict(set)  # call name → strings (memory only)
    current = {"page": "home"}

    def on_request(request: Any) -> None:
        parts = urlsplit(request.url)
        host = parts.hostname or ""
        if host in R.CLASSROOM_HOSTS or host.endswith("google.com") or host.endswith("gstatic.com"):
            label = masked(parts.path)
        else:
            label = "(other host)"
        requests[(request.method, host if label != "(other host)" else "other", label, request.resource_type)] += 1
        if parts.path.endswith("/batchexecute"):
            names = [n for n in parse_qs(parts.query).get("rpcids", [""])[0].split(",") if n]
            batched[len(names)] += 1
            for n in names:
                calls[n] += 1
                seen_by_page[current["page"]].add(n)
            try:
                form = parse_qs(request.post_data or "")
                freq = json.loads(form.get("f.req", ["[]"])[0])
                in_body = sorted({c[0] for c in freq[0] if isinstance(c, list) and c and isinstance(c[0], str)})
                body_names_match["yes" if in_body == sorted(set(names)) else "no"] += 1
            except Exception:
                body_names_match["unparsed"] += 1

    def on_response(response: Any) -> None:
        parts = urlsplit(response.url)
        if response.request.resource_type == "document" and (parts.hostname or "") in R.CLASSROOM_HOSTS:
            # Data a page carries in its own HTML (AF_initDataCallback), if any: counted under its kind.
            try:
                html = response.text()
            except Exception:
                unread["document"] += 1
                return
            name = f"(html of {current['page']})"
            answer_count[name] += 1
            answers[name].add(f"AF_initDataCallback x{html.count('AF_initDataCallback')}")
            block = re.search(r"AF_dataServiceRequests\s*=\s*\{(.*?)\};", html, re.S)
            if block:
                preloaded[current["page"]].update(re.findall(r"id:'([A-Za-z0-9]{4,8})'", block.group(1)))
            payload_strings[name].update(re.findall(r"[A-Za-z0-9_-]{6,}", html))
            return
        if not parts.path.endswith("/batchexecute"):
            return
        try:
            text = response.text()
        except Exception:
            unread["batchexecute"] += 1
            return
        for name, payload in answer_rows(text):
            answer_count[name] += 1
            tags = tags_of(payload)
            answers[name].update(tags)
            if not tags:
                untagged[name] += 1
            found: list[str] = []
            strings(payload, found)
            payload_strings[name].update(found)

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
            ctx.on("request", on_request)
            ctx.on("response", on_response)
            ctx.expose_binding("__abCount", lambda _s, k: guard.bump(k))
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            state = R.open_home(page)
            emit(step="home", state=state)
            if state != "alive":
                return 1
            matches = R.wait_account(page, req["account"])
            emit(step="account", matches=matches)
            if matches is not True:
                return 1
            page.evaluate(R.EXTRACTOR.read_text())
            classes = choose_classes()
            all_ids: dict[str, set[str]] = collections.defaultdict(set)
            for n, cap in enumerate(classes, 1):
                for kind, values in ids_of(cap).items():
                    all_ids[kind] |= values
                cid = cap["class"]["id"]
                paths = [("classwork", f"/u/0/w/{cid}/t/all"), ("stream", f"/u/0/c/{cid}")]
                for t in ("assignment", "material", "question"):
                    item = next((i for i in cap["items"] if i["type"] == t), None)
                    if item:
                        paths.append((t, f"/u/0/c/{cid}/{ROUTE[t]}/{item['id']}/details"))
                for kind, path in paths:
                    if guard.breached:
                        emit(step="stop", why="breached")
                        return 1
                    time.sleep(2 + random.random())
                    current["page"] = kind
                    got = page.evaluate(LOAD_JS, {"path": path, "dwell": DWELL_MS})
                    emit(step="page", cls=n, kind=kind, ok=got["ok"], why=got.get("why"), ms=got["ms"])
                    if got.get("why") == "session_expired":
                        return 1
            page.wait_for_timeout(1500)
            names = sorted(set(calls) | set(answer_count))
            carriers = {}
            for name in names:
                pool = payload_strings.get(name, set())
                carriers[name] = {kind: len(values & pool) for kind, values in all_ids.items() if values & pool}
            emit(
                step="summary",
                ids_known={k: len(v) for k, v in all_ids.items()},
                calls=[{"name": nm, "requests": calls.get(nm, 0), "answers": answer_count.get(nm, 0),
                        "tags": sorted(answers.get(nm, set())), "carries": carriers[nm],
                        "pages": sorted(k for k, v in seen_by_page.items() if nm in v)} for nm in names],
                names_per_request=dict(batched),
                body_names_equal_rpcids=dict(body_names_match),
                untagged_answers=dict(untagged),
                preloaded_by_page={k: sorted(v) for k, v in preloaded.items()},
                unread_answers=dict(unread),
                requests=[{"method": m, "host": h, "path": pth, "type": t, "count": c} for (m, h, pth, t), c in requests.most_common()],
            )
            return 0
        finally:
            emit(step="end", blocked=dict(guard.blocked), breached=guard.breached)
            ctx.close()


if __name__ == "__main__":
    sys.exit(main())
