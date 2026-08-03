"""Export real pipeline data for the web demo (demo/index.html).

Produces demo_data.json with: a real flask graph snapshot (import edges and
per-year co-change counts mined at a real base commit) and three real
SWE-bench Lite instances with their actual BM25 ranking, final candidate
ranking and 7B rerank output.
"""
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import chrono
import night_lab as nl

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
OUT = HERE / "data" / "demo_data.json"

DEMO_INSTANCES = ["sphinx-doc__sphinx-8595", "django__django-11964",
                  "mwaskom__seaborn-3010", "astropy__astropy-14182"]
FLASK_FILES = [
    "src/flask/app.py", "src/flask/ctx.py", "src/flask/globals.py",
    "src/flask/blueprints.py", "src/flask/helpers.py", "src/flask/config.py",
    "src/flask/wrappers.py", "src/flask/sessions.py",
    "src/flask/templating.py", "src/flask/cli.py", "src/flask/testing.py",
    "tests/test_basic.py", "tests/test_blueprints.py", "tests/test_cli.py",
]


def flask_snapshot():
    repo_dir = HERE / "repos" / "pallets__flask.git"
    history = chrono.mine_history(repo_dir,
                                  HERE / "cache" / "pallets__flask_log.pkl")
    head = chrono.git(repo_dir, "rev-parse", "HEAD").strip()
    anc = chrono.ancestor_set(repo_dir, head)
    files = chrono.tree_at(repo_dir, head)
    present = [f for f in FLASK_FILES if f in files]
    bc = chrono.BlobCache(repo_dir)
    bc.load_missing({p: files[p] for p in present})
    s_edges = chrono.static_edges({p: files[p] for p in present}, bc,
                                  repo_dir)
    years = list(range(2018, 2026))
    pair_years = defaultdict(lambda: Counter())
    for sha, ts, fs in history:
        if sha not in anc:
            continue
        alive = [f for f in fs if f in present]
        y = date.fromtimestamp(ts).year
        if y not in years:
            continue
        for i in range(len(alive)):
            for j in range(i + 1, len(alive)):
                pair_years[tuple(sorted((alive[i], alive[j])))][y] += 1
    temporal = []
    for (a, b), c in pair_years.items():
        total = sum(c.values())
        if total >= 3:
            temporal.append({"a": a, "b": b, "total": total,
                             "years": [c.get(y, 0) for y in years]})
    temporal.sort(key=lambda e: -e["total"])
    # PageRank-ish node weight: total co-change involvement
    involve = Counter()
    for e in temporal:
        involve[e["a"]] += e["total"]
        involve[e["b"]] += e["total"]
    mx = max(involve.values()) if involve else 1
    return {
        "years": years,
        "nodes": [{"f": p, "w": round(involve.get(p, 0) / mx, 3)}
                  for p in present],
        "static": [list(k) for k in s_edges],
        "temporal": temporal[:18],
    }


def instance_data():
    lite = {json.loads(l)["instance_id"]: json.loads(l)
            for l in open(HERE / "data" / "swebench_lite.jsonl",
                          encoding="utf-8")}
    cands = {json.loads(l)["instance_id"]: json.loads(l)
             for l in open(HERE / "data" / "rerank_final_lite.jsonl",
                           encoding="utf-8")}
    rr = {json.loads(l)["instance_id"]: json.loads(l)
          for l in open(HERE / "data" / "../results/rerank_qwen_final_lite"
                        ".jsonl", encoding="utf-8")
          if "ranked" in json.loads(l)}
    out = []
    for iid in DEMO_INSTANCES:
        inst, cd = lite[iid], cands[iid]
        repo_dir = HERE / "repos" / (inst["repo"].replace("/", "__")
                                     + ".git")
        history = chrono.mine_history(
            repo_dir, HERE / "cache" / (inst["repo"].replace("/", "__")
                                        + "_log.pkl"))
        ctx = nl.build_context(inst, repo_dir, history,
                               chrono.BlobCache(repo_dir))
        gold = cd["gold"]
        cand_files = [c["file"] for c in cd["hybrid_top"]]
        ranked = rr[iid]["ranked"]
        final = list(ranked) + [c for c in cand_files if c not in ranked]

        # evidence for the gold file: strongest co-change partner among seeds
        base_ts = int(chrono.git(repo_dir, "show", "-s", "--format=%ct",
                                 inst["base_commit"]).strip())
        anc = chrono.ancestor_set(repo_dir, inst["base_commit"])
        ev = {}
        for g in gold:
            best, raw = None, 0
            for sha, ts, fs in history:
                if sha not in anc or g not in fs:
                    continue
                for f in fs:
                    if f != g and f in cand_files[:10]:
                        ev.setdefault(f, 0)
                        ev[f] += 1
            top = sorted(ev.items(), key=lambda kv: -kv[1])[:2]
        out.append({
            "id": iid,
            "repo": inst["repo"],
            "title": inst["problem_statement"].strip().splitlines()[0][:90],
            "text": inst["problem_statement"][:700],
            "gold": gold,
            "bm25": [p for p, _ in ctx["seed_bm"][:10]],
            "candidates": cand_files[:10],
            "final": final[:10],
            "gold_rank_cand": [i + 1 for i, p in enumerate(cand_files)
                               if p in gold],
            "gold_rank_final": [i + 1 for i, p in enumerate(final)
                                if p in gold],
            "evidence": [{"file": f, "cochange": n} for f, n in top],
            "n_candidates": len(cand_files),
        })
    return out


def main():
    data = {"flask": flask_snapshot(), "instances": instance_data()}
    OUT.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT}")
    for i in data["instances"]:
        print(f"  {i['id']}: gold rank {i['gold_rank_cand']} -> "
              f"{i['gold_rank_final']}")
    print(f"  flask: {len(data['flask']['nodes'])} nodes, "
          f"{len(data['flask']['static'])} import edges, "
          f"{len(data['flask']['temporal'])} co-change edges")


if __name__ == "__main__":
    main()
