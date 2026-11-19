"""Items whose attachment count drops to 0 in one complete capture and comes back in the next: a read miss."""
import json, glob, collections, sys
by = collections.defaultdict(list)
for p in glob.glob(f"{sys.argv[1]}/alfabeta-capture-*.json"):
    d = json.load(open(p))
    if d.get("type") == "class": by[d["class"]["id"]].append(d)
dips = collections.Counter(); classes = collections.defaultdict(set); dates = {}
for cid, caps in by.items():
    caps.sort(key=lambda d: d["captured_at"])
    for a, b, c in zip(caps, caps[1:], caps[2:]):
        for it in b["items"]:
            n = lambda cap: next((len((i.get("detail") or {}).get("attachments") or []) for i in cap["items"] if i["id"] == it["id"]), None)
            na, nb, nc = n(a), n(b), n(c)
            if nb == 0 and na and nc:
                dips[b["run"]] += 1; classes[b["run"]].add(cid); dates[b["run"]] = (b["captured_at"][:16], b.get("complete"))
for r in dips: print({"run_date": dates[r][0], "complete": dates[r][1], "items_with_attachments_missing": dips[r], "classes": len(classes[r])})
