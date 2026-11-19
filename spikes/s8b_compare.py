"""Compare the check's class captures with the refresh's capture of the same class: counts, yes/no and seconds only."""
import glob, json, sys, datetime as dt
out, caps = sys.argv[1], sys.argv[2]
def att(a): return sorted((x.get("id"), x.get("name"), x.get("kind")) for x in (a or []))
def at(d): return dt.datetime.fromisoformat(d["captured_at"].replace("Z", "+00:00"))
allc = [json.load(open(q)) for q in glob.glob(f"{caps}/alfabeta-capture-*.json")]
for p in sorted(glob.glob(f"{out}/alfabeta-capture-*.json")):
    d = json.load(open(p))
    if d.get("type") != "class": continue
    mine = [c for c in allc if c.get("type") == "class" and c["class"]["id"] == d["class"]["id"]]
    prev = max(mine, key=at)
    same_run = sorted((c for c in allc if c.get("run") == prev["run"]), key=at)
    i = [id(c) for c in same_run].index(id(prev))
    refresh_s = round((at(prev) - at(same_run[i - 1])).total_seconds()) if i > 0 else None
    A = {x["id"]: x for x in prev["items"]}; B = {x["id"]: x for x in d["items"]}
    diff = {}
    for k in set(A) & set(B):
        da, db = A[k].get("detail") or {}, B[k].get("detail") or {}
        for f in set(da) | set(db):
            x, y = (att(da.get(f)), att(db.get(f))) if f in ("attachments", "submission") else (da.get(f), db.get(f))
            if x != y: diff[f] = diff.get(f, 0) + 1
    print(json.dumps({"complete": d["complete"], "items": len(B), "items_refresh": len(A), "only_refresh": len(set(A) - set(B)),
           "only_check": len(set(B) - set(A)), "attachments": sum(len((x.get("detail") or {}).get("attachments") or []) for x in B.values()),
           "attachments_refresh": sum(len((x.get("detail") or {}).get("attachments") or []) for x in A.values()),
           "fields_differing": diff, "stream_equal": json.dumps(d["stream"], sort_keys=True) == json.dumps(prev["stream"], sort_keys=True),
           "loader": d.get("loader"), "check_s": round((d.get("loader") or {}).get("ms", 0) / 1000), "refresh_s_approx": refresh_s,
           "refresh_minutes_before": round((at(d) - at(prev)).total_seconds() / 60)}))
