"""Host side of s8_dates.py: the two classes' due instants and posting days from their newest captures.

Usage: STUDENT=<id> uv run python spikes/s8_dates_prepare.py > spikes/dates.json — counts are printed to stderr;
mount spikes/ at /s8 when running s8_dates.py. The school year comes from the student's configuration.
"""
import datetime as dt, glob, json, os, sys, tomllib
from alfabeta import capture
home = os.path.expanduser(f"~/.alfabeta/{os.environ['STUDENT']}")
year = tomllib.load(open(f"{home}/config.toml", "rb"))["student"]["school_year"]
newest = {}
for p in glob.glob(f"{home}/data/captures/alfabeta-capture-*.json"):
    d = json.load(open(p))
    if d.get("type") == "class" and d.get("complete"):
        k = d["class"]["id"]
        if k not in newest or d["captured_at"] > newest[k]["captured_at"]:
            newest[k] = d
ranked = sorted(newest.values(), key=lambda d: (len({i["type"] for i in d["items"]}), len(d.get("stream", [])), len(d["items"])), reverse=True)[:2]
out = {"due": set(), "posted_day": set()}
for d in ranked:
    for it in capture.normalize_class(d, year).items:
        if isinstance(it.due_at, dt.datetime):
            out["due"].add(int(it.due_at.timestamp()))
        if it.posted_at:
            out["posted_day"].add(it.posted_at.isoformat()[:10])
print({k: len(v) for k, v in out.items()}, file=sys.stderr)
json.dump({k: sorted(v) for k, v in out.items()}, sys.stdout)
