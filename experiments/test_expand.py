"""Test: on multi-file (3+ gold) LocBench instances, do co-change
neighbours of an anchor file recover the companion gold files that
flat retrieval misses?

Anchors: (a) oracle = best-ranked gold file in our top-50;
         (b) realistic = our top-3 candidates.
Expansion: top co-change neighbours of the anchor(s) by decayed weight,
computed strictly on ancestors of the instance's base commit."""
import json
import math
import time
from collections import defaultdict
from pathlib import Path

import chrono

HERE = Path(__file__).parent
LAM = 1 / 90


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def cochange_neighbours(history, ancestors, base_ts, anchor, k=10):
    w = defaultdict(float)
    for sha, ts, files in history:
        if sha not in ancestors or anchor not in files:
            continue
        decay = math.exp(-LAM * max(0.0, (base_ts - ts) / 86400.0))
        for f in files:
            if f != anchor:
                w[f] += decay
    return [f for f, _ in sorted(w.items(), key=lambda kv: -kv[1])[:k]]


def main():
    inp = [json.loads(l) for l in open(HERE / "data" / "rerank_input50.jsonl",
                                       encoding="utf-8")]
    lb = {json.loads(l)["instance_id"]: json.loads(l)
          for l in open(HERE / "data" / "locbench.jsonl", encoding="utf-8")}
    multi = [r for r in inp if len(r["gold"]) >= 3]
    log(f"{len(multi)} instances with 3+ gold files")

    hist_cache = {}
    stats = {"oracle_n": 0, "oracle_comp_tot": 0, "oracle_comp_found": 0,
             "real_n": 0, "real_comp_tot": 0, "real_comp_found": 0,
             "joint_before": 0, "joint_after": 0}
    out = open(HERE / "results" / "expand_test.jsonl", "w", encoding="utf-8")
    for k, r in enumerate(multi):
        iid = r["instance_id"]
        meta = lb[iid]
        repo = meta["repo"]
        repo_dir = HERE / "repos" / (repo.replace("/", "__") + ".git")
        try:
            if repo not in hist_cache:
                hist_cache[repo] = chrono.mine_history(
                    repo_dir,
                    HERE / "cache" / (repo.replace("/", "__") + "_log.pkl"))
            history = hist_cache[repo]
            base = meta["base_commit"]
            ancestors = chrono.ancestor_set(repo_dir, base)
            base_ts = int(chrono.git(repo_dir, "show", "-s", "--format=%ct",
                                     base).strip())
            files50 = [c["file"] for c in r["hybrid_top"]]
            gold = set(r["gold"])

            # oracle anchor: best-ranked gold file among candidates
            oracle = next((f for f in files50 if f in gold), None)
            if oracle:
                comp = gold - {oracle}
                nbrs = cochange_neighbours(history, ancestors, base_ts,
                                           oracle, k=10)
                stats["oracle_n"] += 1
                stats["oracle_comp_tot"] += len(comp)
                stats["oracle_comp_found"] += len(comp & set(nbrs))

            # realistic: expand our top-3 candidates, 5 neighbours each
            anchors = files50[:3]
            exp = []
            for a in anchors:
                exp.extend(cochange_neighbours(history, ancestors, base_ts,
                                               a, k=5))
            pred = list(dict.fromkeys(anchors + exp))[:15]
            comp_all = gold - set(anchors)
            stats["real_n"] += 1
            stats["real_comp_tot"] += len(comp_all)
            stats["real_comp_found"] += len(comp_all & set(pred))
            stats["joint_before"] += gold <= set(files50[:15])
            stats["joint_after"] += gold <= set(pred)
            out.write(json.dumps({"instance_id": iid, "oracle": oracle,
                                  "pred15": pred}) + "\n")
        except Exception as e:
            log(f"{iid} ERROR {e}")
        if (k + 1) % 20 == 0:
            log(f"{k + 1}/{len(multi)}")
    out.close()

    s = stats
    log("=== РЕЗУЛЬТАТ ===")
    log(f"Оракул-якорь найден в {s['oracle_n']} задачах; his co-change top-10 "
        f"возвращает {100 * s['oracle_comp_found'] / max(1, s['oracle_comp_tot']):.0f}% "
        f"недостающих спутников ({s['oracle_comp_found']}/{s['oracle_comp_tot']})")
    log(f"Реалистично (топ-3 + их соседи, 15 слотов): спутники "
        f"{100 * s['real_comp_found'] / max(1, s['real_comp_tot']):.0f}% "
        f"({s['real_comp_found']}/{s['real_comp_tot']})")
    log(f"ВСЕ gold в 15 слотах: было (топ-15 ретривала) "
        f"{100 * s['joint_before'] / s['real_n']:.0f}%, стало (локализуй+расширь) "
        f"{100 * s['joint_after'] / s['real_n']:.0f}%")


if __name__ == "__main__":
    main()
