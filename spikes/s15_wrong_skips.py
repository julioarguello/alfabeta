"""For each fingerprint-same pair whose attachments differ, the item's attachment count across ALL captures of its class."""
import json, glob, collections, sys
SCHOOL_YEAR = sys.argv[2]  # the student's [student] school_year, e.g. from its config.toml
by = collections.defaultdict(list)
for p in glob.glob(f"{sys.argv[1]}/alfabeta-capture-*.json"):
    d = json.load(open(p))
    if d.get("type") == "class": by[d["class"]["id"]].append(d)
def att(a): return sorted((x.get("id"), x.get("name"), x.get("kind")) for x in (a or []))
def F(d):
    return (tuple(sorted((i["id"], i.get("title"), i.get("listing_date_text"), i.get("topic"), i.get("type")) for i in d["items"])),
            tuple((t.get("id"), t.get("title"), t.get("order")) for t in d["topics"]),
            tuple(sorted((s.get("id"), s.get("created_text"), s.get("text"), tuple(att(s.get("attachments")))) for s in d.get("stream", []))))
for cid, caps in by.items():
    caps.sort(key=lambda d: d["captured_at"])
    for j, (a, b) in enumerate(zip(caps, caps[1:])):
        if not a.get("complete", True) or not b.get("complete", True) or F(a) != F(b): continue
        ra = {i["id"]: i.get("detail") or {} for i in a["items"]}; rb = {i["id"]: i.get("detail") or {} for i in b["items"]}
        for k in ra:
            if att(ra[k].get("attachments")) != att(rb.get(k, {}).get("attachments")):
                seq = []
                for n, c in enumerate(caps):
                    it = next((i for i in c["items"] if i["id"] == k), None)
                    mark = "*" if n in (j, j + 1) else ""
                    seq.append(f"{mark}{'-' if it is None else len((it.get('detail') or {}).get('attachments') or [])}{'' if c.get('complete', True) else 'i'}")
                # distinct attachment-id sets over time, as letters
                sets = []
                for c in caps:
                    it = next((i for i in c["items"] if i["id"] == k), None)
                    if it is not None:
                        s = tuple(sorted(x.get("id") or "" for x in (it.get("detail") or {}).get("attachments") or []))
                        if s not in sets: sets.append(s)
                print({"counts_over_captures": " ".join(seq), "distinct_id_sets": len(sets),
                       "modified_text_values": len({(next((i for i in c["items"] if i["id"] == k), {}).get("detail") or {}).get("modified_text") for c in caps})})
print("--- per-capture variant index of (ids) and (names) for those items, plus run of each capture")
runs_seen = {}
for cid, caps in by.items():
    caps.sort(key=lambda d: d["captured_at"])
    for j, (a, b) in enumerate(zip(caps, caps[1:])):
        if not a.get("complete", True) or not b.get("complete", True) or F(a) != F(b): continue
        ra = {i["id"]: i.get("detail") or {} for i in a["items"]}; rb = {i["id"]: i.get("detail") or {} for i in b["items"]}
        for k in ra:
            if att(ra[k].get("attachments")) != att(rb.get(k, {}).get("attachments")):
                ids, names, rr = [], [], []
                vi, vn = [], []
                for c in caps:
                    it = next((i for i in c["items"] if i["id"] == k), None)
                    A = (it.get("detail") or {}).get("attachments") or [] if it else []
                    s = tuple(sorted(x.get("id") or "" for x in A)); n = tuple(sorted(x.get("name") or "" for x in A))
                    if s not in vi: vi.append(s)
                    if n not in vn: vn.append(n)
                    ids.append(vi.index(s)); names.append(vn.index(n))
                    rr.append(runs_seen.setdefault(c["run"], len(runs_seen)))
                print({"ids": ids, "names": names, "run_no": rr})
print("--- per wrong-skip pair (normalized differs), what differs, by kind")
from alfabeta import capture as C
import dataclasses
def N(d): return {it.id: dataclasses.asdict(it) for it in C.normalize_class(d, SCHOOL_YEAR).items}
for cid, caps in by.items():
    caps.sort(key=lambda d: d["captured_at"])
    for j, (a, b) in enumerate(zip(caps, caps[1:])):
        if not a.get("complete", True) or not b.get("complete", True) or F(a) != F(b): continue
        na, nb = N(a), N(b)
        if na == nb: continue
        kinds = []
        ra = {i["id"]: i.get("detail") or {} for i in a["items"]}; rb = {i["id"]: i.get("detail") or {} for i in b["items"]}
        for k in na:
            x, y = na[k], nb.get(k, {})
            diff = sorted(f for f in x if x.get(f) != y.get(f))
            if not diff: continue
            A, B = ra[k].get("attachments") or [], rb[k].get("attachments") or []
            ia, ib = {t.get("id") for t in A}, {t.get("id") for t in B}
            na_, nb_ = sorted(t.get("name") for t in A), sorted(t.get("name") for t in B)
            if "attachments" in diff:
                kinds.append("att:empty_before" if not A else "att:ids_changed_names_same" if ia != ib and na_ == nb_ else "att:renamed" if ia == ib else "att:other")
            for f in diff:
                if f != "attachments": kinds.append(f)
            st = (ra[k].get("status_text"), rb[k].get("status_text"))
            if st[0] != st[1]: kinds.append(f"status_text:{st[0]}->{st[1]}")
        print({"runs": [runs_seen.get(a["run"]), runs_seen.get(b["run"])], "kinds": kinds})
