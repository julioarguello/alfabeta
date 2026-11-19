"""S8 follow-up (#267): the shape of t51ITc's answer vs a tagged call's, every string replaced by its kind.

Read-only, never signs in. Loads one material and one assignment detail through the extractor's loader. A string
becomes TAG:<it> only if it is short, lower-case and dotted (a protocol tag); otherwise N<len> for digits, S<len>.
Also prints the path words of any Classroom POST that is not batchexecute, when they hold no digit (no ids).
"""
import json, re, sys, time, glob, collections
from urllib.parse import urlsplit
sys.path.insert(0, "/app")
sys.path.insert(0, "/s8")
import read as R  # noqa: E402
import s8_calls as S  # noqa: E402

def shape(x, depth=0):
    if depth > 6: return "…"
    if isinstance(x, list): return [shape(v, depth + 1) for v in x[:6]] + (["+%d" % (len(x) - 6)] if len(x) > 6 else [])
    if isinstance(x, str):
        if re.fullmatch(r"[a-z]{1,8}(\.[a-z0-9_]{1,10}){1,2}", x): return "TAG:" + x
        return ("N%d" if x.isdigit() else "S%d") % len(x)
    if isinstance(x, bool) or x is None: return x
    if isinstance(x, (int, float)): return "num"
    return type(x).__name__

out = collections.defaultdict(list)
others = collections.Counter()
def on_response(resp):
    parts = urlsplit(resp.url)
    if resp.request.method == "POST" and parts.hostname == "classroom.google.com" and not parts.path.endswith("/batchexecute"):
        words = [w for w in parts.path.split("/") if w and not any(c.isdigit() for c in w)]
        others["/".join(words)] += 1
    if not parts.path.endswith("/batchexecute"): return
    try: text = resp.text()
    except Exception: return
    for name, payload in S.answer_rows(text):
        if name == "t51ITc":
            out["t51ITc answers"].append("empty" if payload in ([], None) else "nonempty")
            if payload not in ([], None) and len(out["t51ITc"]) < 2:
                out["t51ITc"].append(shape(payload))

req = json.loads(sys.stdin.readline()); sys.stdin.close()
from playwright.sync_api import sync_playwright
guard = R.Guard()
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(str(R.PROFILE), channel=R.CHANNEL, headless=True, locale=R.LOCALE,
        timezone_id=R.TIMEZONE, ignore_default_args=R.IGNORE_DEFAULT_ARGS, service_workers="block")
    try:
        ctx.add_init_script("window.__abClassroom = " + json.dumps(sorted(R.CLASSROOM_HOSTS)) + ".includes(location.hostname) && location.pathname.startsWith('/u/');")
        ctx.add_init_script(R.GUARD_JS)
        ctx.route("**/*", guard.route); ctx.on("request", guard.watch); ctx.on("response", on_response)
        ctx.expose_binding("__abCount", lambda _s, k: guard.bump(k))
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        st = R.open_home(page); print(json.dumps({"home": st}))
        if st != "alive": sys.exit(1)
        if R.wait_account(page, req["account"]) is not True: print("account?"); sys.exit(1)
        page.evaluate(R.EXTRACTOR.read_text())
        cap = S.choose_classes()[0]; cid = cap["class"]["id"]
        for t in ("material", "assignment"):
            it = next((i for i in cap["items"] if i["type"] == t and (i.get("detail") or {}).get("attachments")), None)
            if not it: continue
            time.sleep(2.5)
            got = page.evaluate(S.LOAD_JS, {"path": f"/u/0/c/{cid}/{S.ROUTE[t]}/{it['id']}/details", "dwell": 4000})
            print(json.dumps({"page": t, "ok": got["ok"], "attachments_in_capture": len(it["detail"]["attachments"])}))
        for name, shapes in out.items():
            for s in shapes: print(json.dumps({"call": name, "shape": s})[:1500])
        print(json.dumps({"other_classroom_posts": dict(others)}))
    finally:
        print(json.dumps({"end": dict(guard.blocked), "breached": guard.breached})); ctx.close()
