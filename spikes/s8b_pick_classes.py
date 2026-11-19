"""The two classes with the most kinds of item and posts in their newest complete capture (ids printed for the runner only)."""
import glob, json, sys
newest = {}
for p in glob.glob(f"{sys.argv[1]}/alfabeta-capture-*.json"):
    d = json.load(open(p))
    if d.get("type") == "class" and d.get("complete"):
        k = d["class"]["id"]
        if k not in newest or d["captured_at"] > newest[k]["captured_at"]:
            newest[k] = d
ranked = sorted(newest.values(), key=lambda d: (len({i["type"] for i in d["items"]}), len(d.get("stream", [])), -len(d["items"])), reverse=True)
print(" ".join(d["class"]["id"] for d in ranked[:2]))
