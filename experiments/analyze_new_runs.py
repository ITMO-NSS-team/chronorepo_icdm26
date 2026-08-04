"""Evaluate the new gap-closing runs vs the Kimi-d50 baseline.

Handles: depth-100 runs (backfill from 100), count-prompt runs (50),
self-consistency vote over multiple sampled runs. Strict Acc@k, official
gold (embedded in rerank_final_locbench.jsonl), exact McNemar vs baseline.
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

EXP = Path(__file__).parent

inp = {}
for line in open(EXP / "data" / "rerank_final_locbench.jsonl",
                 encoding="utf-8"):
    r = json.loads(line)
    inp[r["instance_id"]] = r


def load_run(path, depth):
    d = {}
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        if "ranked" not in r or r["instance_id"] not in inp:
            continue
        cands = [c["file"] for c in
                 inp[r["instance_id"]]["hybrid_top"]][:depth]
        d[r["instance_id"]] = list(r["ranked"]) + [
            c for c in cands if c not in r["ranked"]]
    return d


def sc_vote(paths, depth):
    """Union-vote over sampled runs: count top-5 appearances, tie-break by
    best mean rank; backfill from candidates."""
    per = [load_run(p, depth) for p in paths]
    ids = set.intersection(*(set(d) for d in per))
    out = {}
    for i in ids:
        cnt = defaultdict(int)
        rk = defaultdict(list)
        for d in per:
            for r, p in enumerate(d[i][:10]):
                if r < 5:
                    cnt[p] += 1
                rk[p].append(r)
        ranked = sorted(cnt, key=lambda p: (-cnt[p],
                                            sum(rk[p]) / len(rk[p])))
        cands = [c["file"] for c in inp[i]["hybrid_top"]][:depth]
        out[i] = ranked + [c for c in cands if c not in ranked]
    return out


def mcnemar(aw, bw):
    n, k = aw + bw, min(aw, bw)
    return min(1.0, sum(math.comb(n, j) for j in range(k + 1))
               / 2 ** n * 2) if n else 1.0


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * (c - h), 100 * (c + h)


def report(name, run, base, ids):
    gold = {i: set(inp[i]["gold"]) for i in ids}
    h5 = {i: gold[i] <= set(run[i][:5]) for i in ids}
    h10 = {i: gold[i] <= set(run[i][:10]) for i in ids}
    b5 = {i: gold[i] <= set(base[i][:5]) for i in ids}
    a5 = 100 * sum(h5.values()) / len(ids)
    a10 = 100 * sum(h10.values()) / len(ids)
    lo, hi = wilson(sum(h5.values()), len(ids))
    aw = sum(h5[i] and not b5[i] for i in ids)
    bw = sum(b5[i] and not h5[i] for i in ids)
    p = mcnemar(aw, bw)
    g1 = [i for i in ids if len(gold[i]) == 1]
    g2 = [i for i in ids if len(gold[i]) >= 2]
    perf = [i for i in ids
            if inp[i].get("category") == "Performance Issue"]
    a5g1 = 100 * sum(h5[i] for i in g1) / len(g1)
    a5g2 = 100 * sum(h5[i] for i in g2) / len(g2)
    a5pf = 100 * sum(h5[i] for i in perf) / len(perf)
    print(f"{name:26s} n={len(ids)} Acc@5={a5:5.1f} [{lo:.1f},{hi:.1f}] "
          f"Acc@10={a10:5.1f} | vs base {aw}/{bw} p={p:.4f} | "
          f"gold1={a5g1:.1f} gold2+={a5g2:.1f} perf={a5pf:.1f}")
    return h5


BASE = load_run(EXP / "results" / "bakeoff" / "full_kimi-k2.jsonl", 50)

RUNS = []
for arg in sys.argv[1:]:
    tag, path, depth = arg.split(":")
    RUNS.append((tag, EXP / path, int(depth)))

print("baseline: Kimi-K2 d50 (82.8 / 86.6)")
for tag, path, depth in RUNS:
    if not path.exists():
        print(f"{tag}: MISSING {path}")
        continue
    if "+" in str(path.name):
        continue
    run = load_run(path, depth)
    ids = sorted(set(run) & set(BASE))
    report(tag, run, BASE, ids)
