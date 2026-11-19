"""S8 (#267), the mapping of dates: which calls' answers hold the capture's due instants and posting days.

Read-only, never signs in; the read's own Guard. Loads «Trabajo de clase» and the stream of the two classes
s8_calls picks, through a frame, 2–3 s apart. /s8/dates.json (written by the host from the capture, counts only
printed) holds due instants as epoch seconds and posting days as YYYY-MM-DD. Prints, per call name, how many due
instants appear as seconds or milliseconds and how many posting days fall on a number in its answers that is an
epoch (s or ms) of that day in Madrid, and how many due dates appear as a [year, month, day] run. Counts only.
"""
import collections, datetime as dt, json, random, sys, time
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
sys.path.insert(0, "/app"); sys.path.insert(0, "/s8")
import read as R  # noqa: E402
import s8_calls as S  # noqa: E402

MADRID = ZoneInfo("Europe/Madrid")
dates = json.load(open("/s8/dates.json"))
due = set(dates["due"]); due_ms = {d * 1000 for d in due}
due_ymd = {tuple(dt.datetime.fromtimestamp(d, MADRID).timetuple()[:3]) for d in due}
posted_days = set(dates["posted_day"])
nums = collections.defaultdict(set)
runs = collections.defaultdict(set)

def walk(x, name):
    if isinstance(x, list):
        ints = [v for v in x if isinstance(v, int) and not isinstance(v, bool)]
        if len(ints) >= 3:
            for i in range(len(x) - 2):
                t = x[i:i + 3]
                if all(isinstance(v, int) and not isinstance(v, bool) for v in t):
                    runs[name].add(tuple(t))
        for v in x:
            walk(v, name)
    elif isinstance(x, (int, str)) and not isinstance(x, bool):
        s = str(x)
        if s.isdigit() and 9 <= len(s) <= 13:
            nums[name].add(int(s))

def on_response(resp):
    if not urlsplit(resp.url).path.endswith("/batchexecute"):
        return
    try:
        text = resp.text()
    except Exception:
        return
    for name, payload in S.answer_rows(text):
        walk(payload, name)

def day_of(n):
    sec = n / 1000 if n > 10**11 else n
    try:
        return dt.datetime.fromtimestamp(sec, MADRID).date().isoformat()
    except Exception:
        return None

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
        if R.wait_account(page, req["account"]) is not True: print(json.dumps({"account": "no"})); sys.exit(1)
        page.evaluate(R.EXTRACTOR.read_text())
        for cap in S.choose_classes():
            cid = cap["class"]["id"]
            for kind, path in (("classwork", f"/u/0/w/{cid}/t/all"), ("stream", f"/u/0/c/{cid}")):
                time.sleep(2 + random.random())
                got = page.evaluate(S.LOAD_JS, {"path": path, "dwell": 3000})
                print(json.dumps({"page": kind, "ok": got["ok"]}))
        print(json.dumps({"known": {"due": len(due), "posted_days": len(posted_days)}}))
        for name in sorted(set(nums) | set(runs)):
            n = nums[name]
            row = {"call": name,
                   "due_seconds": len(due & n), "due_ms": len(due_ms & n),
                   "due_ymd_runs": len(due_ymd & runs[name]),
                   "posted_days_with_an_epoch": len(posted_days & {day_of(v) for v in n})}
            if any(v for k, v in row.items() if k != "call"):
                print(json.dumps(row))
    finally:
        print(json.dumps({"end": dict(guard.blocked), "breached": guard.breached})); ctx.close()
