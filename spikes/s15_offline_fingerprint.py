"""Issue #263 offline measurement: cheap fingerprint vs consumed (normalized) fields, per consecutive capture pair."""
import json, glob, collections, dataclasses, sys
from alfabeta import capture
DIR = sys.argv[1]
by = collections.defaultdict(list)
for p in glob.glob(f"{DIR}/alfabeta-capture-*.json"):
    d = json.load(open(p))
    if d.get("type") == "class": by[d["class"]["id"]].append(d)
def att(a): return sorted((x.get("id"), x.get("name"), x.get("kind")) for x in (a or []))
def F(d):
    return (tuple(sorted((i["id"], i.get("title"), i.get("listing_date_text"), i.get("topic"), i.get("type")) for i in d["items"])),
            tuple((t.get("id"), t.get("title"), t.get("order")) for t in d["topics"]),
            tuple(sorted((s.get("id"), s.get("created_text"), s.get("text"), tuple(att(s.get("attachments")))) for s in d.get("stream", []))))
def N(d):
    c = capture.normalize_class(d, "2026-2027")
    out = {}
    for it in c.items:
        out[it.id] = {k: v for k, v in dataclasses.asdict(it).items()}
    return out
stats = collections.Counter(); fields = collections.Counter(); versions = collections.Counter(); detail = []
for cid, caps in by.items():
    caps.sort(key=lambda d: d["captured_at"])
    for a, b in zip(caps, caps[1:]):
        if not a.get("complete", True) or not b.get("complete", True):
            stats["incomplete_pair"] += 1; continue
        stats["pairs"] += 1
        if F(a) != F(b): stats["fp_changed"] += 1; continue
        na, nb = N(a), N(b)
        if na == nb: stats["fp_same_norm_same"] += 1; continue
        stats["FALSE_NEG"] += 1
        versions[(a.get("version"), b.get("version"))] += 1
        diff = set()
        for k in set(na) | set(nb):
            x, y = na.get(k, {}), nb.get(k, {})
            for f in set(x) | set(y):
                if x.get(f) != y.get(f): diff.add(f); fields[f] += 1
        detail.append({"hours_apart": round((capture.captured_at(b) - capture.captured_at(a)).total_seconds() / 3600, 1),
                       "versions": [a.get("version"), b.get("version")], "fields": sorted(diff)})
print(dict(stats)); print("fields:", dict(fields)); print("versions:", dict(versions))
for x in detail: print(x)
print("--- attachment diffs in false negatives")
for cid, caps in by.items():
    caps.sort(key=lambda d: d["captured_at"])
    for a, b in zip(caps, caps[1:]):
        if not a.get("complete", True) or not b.get("complete", True) or F(a) != F(b): continue
        ra = {i["id"]: i.get("detail") or {} for i in a["items"]}; rb = {i["id"]: i.get("detail") or {} for i in b["items"]}
        for k in ra:
            x, y = ra[k].get("attachments") or [], rb.get(k, {}).get("attachments") or []
            if x != y:
                ix = {t.get("id") for t in x}; iy = {t.get("id") for t in y}
                keys = sorted({f for t in x + y for f in t})
                changed = sorted({f for t in x for u in y if t.get("id") == u.get("id") for f in keys if t.get(f) != u.get(f)})
                print({"n_before": len(x), "n_after": len(y), "added": len(iy - ix), "removed": len(ix - iy), "fields_changed": changed, "item_type": next(i["type"] for i in a["items"] if i["id"] == k)})
            s, t = ra[k].get("status_text"), rb.get(k, {}).get("status_text")
            if s != t: print({"status_change": [s, t], "listing_date_prefix": next(i.get("listing_date_text","").split(":")[0] for i in a["items"] if i["id"]==k)})
