"""Prompt-variant sweep for the small models (dev half, holdout check).

Variants are compared on the LocBench dev half only (same instance-id hash
split as the recipe sweep); the winner is validated once on the untouched
holdout. Strict Acc@k with backfill, exact McNemar against the default
prompt on the identical instances.

Usage:
  py -3.12 analyze_prompts.py dev
  py -3.12 analyze_prompts.py holdout
"""
import json
import math
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
VARIANTS = ["default", "top1", "exact10", "verbatim", "fewshot", "cat"]
MODELS = {"qwen35-9b": "Qwen3.5-9B", "qwen7b": "Qwen2.5-7B"}


def load_baskets():
    return {json.loads(l)["instance_id"]: json.loads(l)
            for l in open(HERE / "data" / "rerank_final_locbench.jsonl",
                          encoding="utf-8")}


def load_run(path, inp, depth=50):
    d = {}
    if not path.exists():
        return d
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        if "ranked" not in r or r["instance_id"] not in inp:
            continue
        cands = [c["file"] for c in inp[r["instance_id"]]["hybrid_top"]][:depth]
        d[r["instance_id"]] = list(r["ranked"]) + [
            c for c in cands if c not in r["ranked"]]
    return d


def wilson(k, n, z=1.96):
    if not n:
        return 0.0, 0.0
    p = k / n
    dd = 1 + z * z / n
    c = (p + z * z / (2 * n)) / dd
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / dd
    return 100 * (c - h), 100 * (c + h)


def mcnemar(aw, bw):
    n, k = aw + bw, min(aw, bw)
    return min(1.0, sum(math.comb(n, j) for j in range(k + 1))
               / 2 ** n * 2) if n else 1.0


def main():
    split = sys.argv[1] if len(sys.argv) > 1 else "dev"
    inp = load_baskets()
    for slug, name in MODELS.items():
        runs = {v: load_run(HERE / "results" / "bakeoff"
                            / f"prompt_{slug}_{v}_{split}.jsonl", inp)
                for v in VARIANTS}
        runs = {v: r for v, r in runs.items() if r}
        if "default" not in runs:
            print(f"{name}: no default run for {split}")
            continue
        ids = sorted(set.intersection(*(set(r) for r in runs.values())))
        gold = {i: set(inp[i]["gold"]) for i in ids}
        base = runs["default"]
        print(f"\n=== {name}, {split} half (n={len(ids)}) ===")
        print(f"{'prompt':10s} {'Acc@5':>7s} {'95% CI':>14s} {'Acc@10':>7s} "
              f"{'vs default':>12s} {'p':>7s}")
        for v in VARIANTS:
            if v not in runs:
                continue
            h5 = {i: gold[i] <= set(runs[v][i][:5]) for i in ids}
            b5 = {i: gold[i] <= set(base[i][:5]) for i in ids}
            a5 = 100 * sum(h5.values()) / len(ids)
            a10 = 100 * sum(gold[i] <= set(runs[v][i][:10])
                            for i in ids) / len(ids)
            lo, hi = wilson(sum(h5.values()), len(ids))
            aw = sum(h5[i] and not b5[i] for i in ids)
            bw = sum(b5[i] and not h5[i] for i in ids)
            tag = "--" if v == "default" else f"{aw}/{bw}"
            p = 1.0 if v == "default" else mcnemar(aw, bw)
            print(f"{v:10s} {a5:6.1f}% [{lo:5.1f},{hi:5.1f}] {a10:6.1f}% "
                  f"{tag:>12s} {p:7.3f}")


if __name__ == "__main__":
    main()
