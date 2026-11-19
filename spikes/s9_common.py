"""Spike S9 (#279): what s9a and s9b share — the allowlist routing, the labelled shapes, the browser set-up.

Runs in the read image with --entrypoint python; imports /app/read.py and installs its Guard exactly as read.run()
does, plus one routing step before it (S8's second half): a batchexecute naming any call outside ALLOW — in its URL
or in its body — is aborted, and so is every request to the telemetry, push and Google-bar hosts. Optional extra
blocks: RotateCookiesPage stays blocked by the Guard itself (a frame outside the read phase's documents);
ClassroomUi/browserinfo is aborted only when BLOCK_BROWSERINFO is set.
Nothing printed holds a body, a cookie, a name, a title or an id: shapes use kind labels, lengths and literal small
numbers (field masks and enums), never values.
"""

from __future__ import annotations

import base64
import collections
import json
import re
import sys
from typing import Any
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, "/app")
sys.path.insert(0, "/s9")
import read as R  # noqa: E402

ALLOW = frozenset({"dpT4Vd", "pONvgf", "tQShAc", "ZZFlc", "Zj93ge", "cCzVwf", "t51ITc", "gXtzob", "O1Xqee", "UG41I"})
BLOCK_HOSTS = frozenset({"play.google.com", "signaler-pa.clients6.google.com", "ogads-pa.clients6.google.com", "ogs.google.com"})
WORD = re.compile(r"^[a-z_]{1,24}$")
# The only words a shape keeps as they are: protocol words and Drive kinds. A lower-case title could match WORD.
VOCAB = frozenset({"generic", "document", "spreadsheet", "presentation", "drawing", "form", "file", "link", "video", "youtube",
                   "pdf", "folder", "image", "c", "es", "eu", "en"})
TAG = re.compile(r"^[a-z]{1,6}\.[a-z]{1,4}$")


def emit(**kw: object) -> None:
    print(json.dumps(kw, ensure_ascii=False)[:4000], flush=True)


def b64decode(text: str) -> str:
    try:
        return base64.b64decode(text + "=" * (-len(text) % 4)).decode()
    except Exception:
        return ""


def b64encode(decimal: str) -> str:
    return base64.b64encode(decimal.encode()).decode().rstrip("=")


def body_names(post_data: str | None) -> list[str]:
    """The call names a batchexecute body carries in f.req; ['?'] if it cannot be read."""
    if not post_data:
        return []
    try:
        freq = json.loads(parse_qs(post_data).get("f.req", ["[]"])[0])
        return [c[0] for c in freq[0] if isinstance(c, list) and c]
    except Exception:
        return ["?"]


class Routing:
    """The allowlist step before the Guard's own route; counts what it aborts."""

    def __init__(self, guard: Any, block_browserinfo: bool = False) -> None:
        self.guard = guard
        self.block_browserinfo = block_browserinfo
        self.seen_browserinfo = 0
        self.rotate = collections.Counter()

    def route(self, route: Any, request: Any) -> None:
        parts = urlsplit(request.url)
        host = parts.hostname or ""
        if host in BLOCK_HOSTS:
            self.guard._count("host:" + host)
            route.abort()
            return
        if host == "accounts.google.com" and "RotateCookies" in parts.path:
            self.rotate["requested"] += 1
        if host in R.CLASSROOM_HOSTS and parts.path.endswith("/browserinfo"):
            self.seen_browserinfo += 1
            if self.block_browserinfo:
                self.guard._count("browserinfo")
                route.abort()
                return
        if parts.path.endswith("/batchexecute"):
            names = [n for n in parse_qs(parts.query).get("rpcids", [""])[0].split(",") if n]
            names_body = body_names(request.post_data)
            outside = [n for n in names + names_body if n not in ALLOW]
            if not names or outside or sorted(set(names)) != sorted(set(names_body)):
                for n in outside or ["(mismatch)"]:
                    self.guard._count("call:" + n)
                route.abort()
                return
        self.guard.route(route, request)


def launch(p: Any, guard: Any, routing: Routing) -> Any:
    """The persistent context exactly as read.run() opens it, with the routing step first."""
    ctx = p.chromium.launch_persistent_context(
        str(R.PROFILE), channel=R.CHANNEL, headless=True, locale=R.LOCALE, timezone_id=R.TIMEZONE,
        ignore_default_args=R.IGNORE_DEFAULT_ARGS, service_workers="block",
    )
    ctx.add_init_script(
        "window.__abClassroom = " + json.dumps(sorted(R.CLASSROOM_HOSTS)) + ".includes(location.hostname) && location.pathname.startsWith('/u/');"
    )
    ctx.add_init_script(R.GUARD_JS)
    ctx.route("**/*", routing.route)
    ctx.on("request", guard.watch)
    ctx.expose_binding("__abCount", lambda _s, k: guard.bump(k))
    return ctx


def answer_rows(text: str) -> list[tuple[str, Any, Any]]:
    """batchexecute answer → [(call name, parsed payload or None, row's index field)], from wrb.fr rows only."""
    rows: list[tuple[str, Any, Any]] = []
    body = text[text.find("\n") + 1:] if text.startswith(")]}'") else text
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
                rows.append((row[1], payload, row[6] if len(row) > 6 else None))
    return rows


def shape(x: Any, labels: dict[str, str], depth: int = 0, width: int = 14) -> Any:
    """x with every value replaced: known values by their label, small ints/bools/null literal, rest by kind+length."""
    if depth > 12:
        return "…"
    if isinstance(x, list):
        out = [shape(v, labels, depth + 1, width) for v in x[:width]]
        return out + (["+%d" % (len(x) - width)] if len(x) > width else [])
    if isinstance(x, bool) or x is None:
        return x
    if isinstance(x, (int, float)):  # a number's label or length starts with «#», a string's does not
        s = str(x)
        if s in labels:
            return "#" + labels[s]
        if isinstance(x, int) and len(s) <= 5:
            return x
        return "#N%d" % len(s) if s.lstrip("-").isdigit() else "float"
    if isinstance(x, str):
        if x in labels:
            return labels[x]
        if x.isdigit():
            return "N%d" % len(x) if len(x) > 5 else "d:" + x
        if x in VOCAB or TAG.match(x):
            return "w:" + x
        if len(x) > 1 and x[0] in "[{":
            try:
                return {"json": shape(json.loads(x), labels, depth + 1, width)}
            except ValueError:
                pass
        return "S%d" % len(x)
    if isinstance(x, dict):
        return {"dict": len(x)}
    return type(x).__name__


def find_paths(x: Any, wanted: dict[str, str], path: tuple[int, ...] = (), out: list | None = None, limit: int = 4000) -> list:
    """[(label, path)] for every string/number in x whose text is a key of `wanted` (whole-string match)."""
    if out is None:
        out = []
    if len(out) >= limit:
        return out
    if isinstance(x, list):
        for i, v in enumerate(x):
            find_paths(v, wanted, path + (i,), out, limit)
    elif isinstance(x, (str, int)) and not isinstance(x, bool):
        s = str(x)
        if s in wanted:
            out.append((wanted[s], path))
    return out


def capture_labels(cap: dict[str, Any]) -> dict[str, str]:
    """value → label for the values a class capture holds (in memory only)."""
    lab: dict[str, str] = {}

    def put(v: Any, label: str) -> None:
        if v not in (None, "") and str(v) not in lab:
            lab[str(v)] = label

    put(b64decode(cap["class"]["id"]), "CLASS")
    put(cap["class"]["id"], "CLASS_B64")
    put(cap["class"].get("title"), "CLASS_TITLE")
    for t in cap.get("topics", []):
        put(t.get("id"), "TOPIC")
        put(t.get("title"), "TOPIC_TITLE")
    for i in cap["items"]:
        put(b64decode(i["id"]), "ITEM")
        put(i["id"], "ITEM_B64")
        put(i.get("title"), "ITEM_TITLE")
        d = i.get("detail") or {}
        put(d.get("description"), "DESCRIPTION")
        put(d.get("points"), "POINTS")
        for a in d.get("attachments") or []:
            put(a.get("id"), "ATT_ID")
            put(a.get("name"), "ATT_NAME")
    for s in cap.get("stream", []):
        put(s.get("id"), "POST")
        put(b64decode(str(s.get("id"))), "POST_DEC")
        put(s.get("text"), "POST_TEXT")
        for a in s.get("attachments") or []:
            put(a.get("id"), "ATT_ID")
            put(a.get("name"), "ATT_NAME")
    return lab
