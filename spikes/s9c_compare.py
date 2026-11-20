"""Spike S9, step 3 (#279), offline: the read by calls against the extractor's capture of the same session.

Usage, from the repository root: STUDENT=<id> uv run python spikes/s9c_compare.py — on the student's machine, no
network. Reads the answers s9b kept (~/.alfabeta/<id>/data/spike-s9/answers.json), the captures of the refresh run
they name, and the student's school year (config.toml), and compares field by field, per class s9b read:
- ids: items from dpT4Vd's records (by slot), posts from pONvgf's slot 2, topics from ZZFlc; what only one side has;
- the item type each record slot stands for;
- titles, descriptions and topics: found as they are, or only after collapsing whitespace; the class title as a
  gXtzob string plus another gXtzob string (name and section);
- posting days: the epoch milliseconds in each item's record that fall, in Europe/Madrid, on the day
  capture.normalize_class reads from the capture (per index path); due instants found exactly as milliseconds;
- the status: the index path of Zj93ge's answer whose small number tells apart the statuses normalize_class
  derives from the texts (R7's table);
- attachments: ids and names found, and in which call an unfound one appears at all;
- the largest topic of every class of the run (dpT4Vd asks for 10 per call).
Prints counts, yes/no, index paths, call names, Classroom's status words and ItemStatus values. Never a body, a
cookie, a name, a title or an id.
"""

from __future__ import annotations

import base64
import collections
import datetime as dt
import glob
import json
import os
import re
import sys
import tomllib
from typing import Any
from zoneinfo import ZoneInfo

from alfabeta import capture as cap_mod

HOME = os.path.expanduser(f"~/.alfabeta/{os.environ['STUDENT']}")
DATA = HOME + "/data"
MADRID = ZoneInfo("Europe/Madrid")


def b64decode(text: str) -> str:
    try:
        return base64.b64decode(text + "=" * (-len(text) % 4)).decode()
    except Exception:
        return ""


def values(x: Any, out: set[str] | None = None) -> set[str]:
    """Every string and number in x, as text."""
    out = set() if out is None else out
    if isinstance(x, list):
        for v in x:
            values(v, out)
    elif isinstance(x, (int, float, str)) and not isinstance(x, bool):
        out.add(str(x))
    return out


def leaves(x: Any, p: tuple = ()):
    if isinstance(x, list):
        for i, v in enumerate(x):
            yield from leaves(v, p + (i,))
    elif isinstance(x, (int, str)) and not isinstance(x, bool):
        yield p, x


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def records(payload: Any, cls: str) -> list[tuple[int, str, Any]]:
    """[(slot, id, record)] for every record whose key payload[2][i][slot][0][0] is [id, [class]]."""
    out = []
    for entry in (payload[2] or []) if isinstance(payload, list) and len(payload) > 2 else []:
        for slot, rec in enumerate(entry if isinstance(entry, list) else []):
            try:
                key = rec[0][0]
                if str(key[1][0]) == cls and key[0] is not None:
                    out.append((slot, str(key[0]), rec))
            except (IndexError, TypeError, KeyError):
                continue
    return out


def emit(**kw: Any) -> None:
    print(json.dumps(kw, ensure_ascii=False, default=str))


def main() -> int:
    school_year = tomllib.load(open(HOME + "/config.toml", "rb"))["student"]["school_year"]
    ans = json.load(open(f"{DATA}/spike-s9/answers.json"))
    caps = {b64decode(c["class"]["id"]): c for c in (json.load(open(f)) for f in glob.glob(f"{DATA}/captures/alfabeta-capture-{ans['run']}-*.json"))
            if c.get("type") == "class"}
    status_paths: dict[tuple, dict[str, set]] = collections.defaultdict(lambda: collections.defaultdict(set))
    status_n: collections.Counter = collections.Counter()
    posted_paths: collections.Counter = collections.Counter()
    posted_n = 0
    due_paths: collections.Counter = collections.Counter()
    due_n = 0
    for n, cls in enumerate(ans["classes"]):
        cap = caps[cls]
        norm_items = {b64decode(i.id): i for i in cap_mod.normalize_class(cap, school_year).items}
        log = [e for e in ans["log"] if e["key"] == cls or e["key"].startswith(cls + "/")]
        by = collections.defaultdict(list)
        for e in log:
            by[e["name"]].append(e)
        r: dict[str, Any] = {}
        gv = {x for x in values([e["payload"] for e in ans["log"] if e["name"] == "gXtzob"]) if not x.isdigit()}
        t = cap["class"]["title"]
        r["class_title"] = "as is" if t in gv else "name + section" if any(
            t.startswith(a) and t[len(a):].strip(" -·,") in gv for a in gv if len(a) > 3) else "no"
        zz_topics = {str(tp[0][0]) for e in by["ZZFlc"] for tp in (e["payload"][2] or []) if isinstance(tp, list) and tp and isinstance(tp[0], list)}
        cap_topics = {tp["id"]: tp for tp in cap.get("topics", [])}
        zz_vals = values([e["payload"] for e in by["ZZFlc"]])
        r["topics"] = {"capture": len(cap_topics), "capture_without_id": sum(1 for k in cap_topics if not k), "calls": len(zz_topics),
                       "same_ids": len(set(cap_topics) & zz_topics), "titles_found": sum(1 for tp in cap_topics.values() if tp["id"] and tp.get("title") in zz_vals)}
        dp = {i: (s, rec) for e in by["dpT4Vd"] for s, i, rec in records(e["payload"], cls)}
        po = {i: (s, rec) for e in by["pONvgf"] for s, i, rec in records(e["payload"], cls)}
        items = {i: v for i, v in dp.items() if v[0] != 2}
        posts = {i: v for i, v in po.items() if v[0] == 2}
        cap_items = {b64decode(i["id"]): i for i in cap["items"]}
        stream_only = {i: v for i, v in po.items() if v[0] != 2 and i not in items}
        r["items"] = {"capture": len(cap_items), "dpT4Vd": len(items), "same_ids": len(set(cap_items) & set(items)),
                      "only_capture": len(set(cap_items) - set(items)), "only_dpT4Vd": len(set(items) - set(cap_items)),
                      "stream_records_not_in_dpT4Vd": len(stream_only),
                      "of_those_in_capture": len(set(stream_only) & set(cap_items))}
        # what sets the stream-only records apart: the small numbers at the same paths in other stream records
        if stream_only:
            others = [v[1] for i, v in po.items() if v[0] != 2 and i in items]
            diff = collections.Counter()
            for _i, (_s, rec) in stream_only.items():
                mine = {p: v for p, v in leaves(rec) if isinstance(v, int) and 0 <= v < 100}
                for o in others:
                    theirs = {p: v for p, v in leaves(o) if isinstance(v, int) and 0 <= v < 100}
                    for p in set(mine) ^ set(theirs):
                        diff[p] += 1
                    for p in set(mine) & set(theirs):
                        diff[p] += mine[p] != theirs[p]
            n_pairs = len(stream_only) * max(1, len(others))
            r["stream_only_differ_always_at"] = [list(p) for p, c in diff.items() if c == n_pairs][:8]
        r["type_by_slot"] = dict(collections.Counter(f"{items[i][0]}->{cap_items[i]['type']}" for i in set(cap_items) & set(items)))
        per_item: dict[str, list] = collections.defaultdict(list)
        for e in log:
            if "/i/" in e["key"]:
                per_item[e["key"].split("/i/")[1]].append(e)
        f: collections.Counter = collections.Counter()
        unfound_att: collections.Counter = collections.Counter()
        all_vals = values([e["payload"] for e in log])
        for iid, ci in cap_items.items():
            if iid not in items:
                continue
            rec = items[iid][1]
            calls = per_item.get(iid, [])
            v_rec = values(rec)
            v_by = {name: values([e["payload"] for e in calls if e["name"] == name]) for name in ("tQShAc", "t51ITc", "cCzVwf", "Zj93ge")}
            v_all = v_rec.union(*v_by.values())
            v_norm = {norm(x) for x in v_all}
            d = ci.get("detail") or {}
            for field, val in (("title", ci.get("title")), ("description", d.get("description"))):
                if val:
                    f[field + ":in_capture"] += 1
                    f[field + ":as_is"] += val in v_all
                    f[field + ":after_whitespace"] += val not in v_all and norm(val) in v_norm
                    f[field + ":in_record"] += val in v_rec or norm(val) in {norm(x) for x in v_rec}
                    f[field + ":in_tQShAc"] += val in v_by["tQShAc"] or norm(val) in {norm(x) for x in v_by["tQShAc"]}
            if ci.get("topic"):
                f["topic:in_capture"] += 1
                f["topic:in_record"] += ci["topic"] in v_rec
            if d.get("points") not in (None, ""):
                f["points:in_capture"] += 1
                f["points:found"] += str(d["points"]).split(" ")[0] in v_all
            for a in d.get("attachments") or []:
                f["att:in_capture"] += 1
                hit_id, hit_name = str(a.get("id")) in v_all, str(a.get("name")) in v_all
                f["att_id:found"] += hit_id
                f["att_id:in_t51ITc"] += str(a.get("id")) in v_by["t51ITc"]
                f["att_name:found"] += hit_name
                f["att_name:inside_a_string"] += not hit_name and any(str(a.get("name")) in x for x in v_all if len(x) > len(str(a.get("name"))))
                if not hit_id:
                    unfound_att[f"id kind={a.get('kind')} elsewhere_in_class={str(a.get('id')) in all_vals}"] += 1
                if not hit_name and not any(str(a.get("name")) in x for x in v_all):
                    unfound_att[f"name kind={a.get('kind')} elsewhere_in_class={str(a.get('name')) in all_vals}"] += 1
            ni = norm_items.get(iid)
            if ni is not None:
                if ni.posted_at:
                    posted_n += 1
                    for p, v in leaves(rec):
                        if isinstance(v, int) and 10**12 <= v < 10**13 and dt.datetime.fromtimestamp(v / 1000, MADRID).date() == ni.posted_at:
                            posted_paths[p] += 1
                if isinstance(ni.due_at, dt.datetime):
                    due_n += 1
                    ms = str(int(ni.due_at.timestamp() * 1000))
                    for p, v in leaves(rec):
                        if str(v) == ms:
                            due_paths[p] += 1
                zj = [e for e in calls if e["name"] == "Zj93ge"]
                if zj and zj[0]["payload"] and ni.status is not None:
                    key = f"{d.get('status_text') or '-'} -> {ni.status.value}"
                    status_n[key] += 1
                    for p, v in leaves(zj[0]["payload"]):
                        if isinstance(v, int) and 0 <= v < 100:
                            status_paths[p][key].add(v)
            f["submission_answered"] += any(e["name"] == "Zj93ge" and e["payload"] for e in calls)
            f["items"] += 1
        r["item_fields"] = dict(sorted(f.items()))
        r["attachments_unfound"] = dict(unfound_att)
        r["tQShAc_adds_nothing_the_record_lacks"] = f["title:in_record"] == f["title:in_tQShAc"] and f["description:in_record"] >= f["description:in_tQShAc"]
        cap_posts = {str(s["id"]): s for s in cap.get("stream", [])}
        pv = values([p[1] for p in posts.values()] + [e["payload"] for e in log if "/p/" in e["key"]])
        r["posts"] = {"capture": len(cap_posts), "calls": len(posts), "same_ids": len(set(cap_posts) & set(posts)),
                      "text_found": sum(1 for s in cap_posts.values() if s.get("text") and (s["text"] in pv or norm(s["text"]) in {norm(x) for x in pv})),
                      "text_in_capture": sum(1 for s in cap_posts.values() if s.get("text")),
                      "att_in_capture": sum(len(s.get("attachments") or []) for s in cap_posts.values())}
        r["seconds"] = None
        emit(**{f"class_{n}": r})
    emit(posted_days={"items": posted_n, "best_paths": [[list(p), c] for p, c in posted_paths.most_common(3)]},
         due_instants={"items_with_time": due_n, "best_paths": [[list(p), c] for p, c in due_paths.most_common(3)]})
    exact = [p for p, m in status_paths.items() if len(m) == len(status_n) and all(len(v) == 1 for v in m.values())
             and len({next(iter(v)) for v in m.values()}) == len(m)]
    emit(status_items=dict(status_n), status_paths_one_to_one=[[list(p), {k: sorted(v)[0] for k, v in status_paths[p].items()}] for p in exact])
    sizes = collections.Counter()
    for c in caps.values():
        per_topic = collections.Counter(i.get("topic") or "-" for i in c["items"])
        sizes["largest_topic_" + ("over_10" if max(per_topic.values(), default=0) > 10 else "10_or_less")] += 1
        sizes["max"] = max(sizes["max"], max(per_topic.values(), default=0))
    emit(topic_sizes_all_classes=dict(sizes), classes_in_run=len(caps))
    return 0


if __name__ == "__main__":
    sys.exit(main())
