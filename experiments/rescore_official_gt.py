"""Rescore legacy rerank runs under LocBench's official ground truth.

The early rerank inputs (rerank_input.jsonl / rerank_input50.jsonl /
rerank_input100.jsonl) embedded patch-file gold — the definition Appendix A
retracts. This script rescores any rerank output produced from those
baskets against the official `edit_functions` gold (files of functions
edited by the fix), with the same backfilled strict metric used everywhere
else: model ranking first, then unreturned candidates in basket order;
an instance counts at k only if *all* gold files are in the top-k.

Instances whose official gold is empty are skipped (they are not part of
the benchmark's ground truth). Also prints the no-LLM strict accuracy of
the raw basket order on the identical instance set, so the LLM lift stays
paired.

Usage:
  py -3.12 rescore_official_gt.py --input data/rerank_input50.jsonl \
      --results results/rerank_qwen7b_top50.jsonl [more results files ...]
"""
import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent


def wilson(k, n, z=1.96):
    if not n:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * (c - h), 100 * (c + h)


def official_gold():
    ef = json.loads((HERE / "data" / "edit_functions.json").read_text())
    return {iid: sorted({e.split(":")[0] for e in v})
            for iid, v in ef.items() if v}


def basket_of(rec, condition):
    if condition == "bm25_plain":
        return list(rec.get("bm25_top") or [])
    return [c["file"] for c in rec.get("hybrid_top") or []]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True,
                    help="rerank input jsonl (baskets)")
    ap.add_argument("--results", nargs="+", required=True,
                    help="rerank output jsonl file(s)")
    ap.add_argument("--max-cands", type=int, default=0,
                    help="truncate baskets to first N before backfill "
                         "(match the run's --max-cands)")
    args = ap.parse_args()

    gold_of = official_gold()
    inp = {}
    for line in open(args.input, encoding="utf-8"):
        r = json.loads(line)
        inp[r["instance_id"]] = r

    for path in args.results:
        per_cond = defaultdict(lambda: [0, 0, 0, 0])  # a5, a10, ceil, n
        skipped_no_gold = errors = 0
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            if "ranked" not in r:
                errors += 1
                continue
            iid = r["instance_id"]
            gold = gold_of.get(iid)
            rec = inp.get(iid)
            if not gold or rec is None:
                skipped_no_gold += 1
                continue
            cands = basket_of(rec, r.get("condition", "hybrid_plain"))
            if args.max_cands:
                cands = cands[:args.max_cands]
            full = list(r["ranked"]) + [c for c in cands
                                        if c not in r["ranked"]]
            g = set(gold)
            s = per_cond[r.get("condition", "?")]
            s[0] += g <= set(full[:5])
            s[1] += g <= set(full[:10])
            s[2] += g <= set(cands)
            s[3] += 1
        print(f"\n=== {path} (official edit_functions gold; "
              f"{skipped_no_gold} skipped w/o gold, {errors} errors) ===")
        print(f"{'condition':18s} {'n':>5s} {'Acc@5':>7s} {'95% CI':>15s} "
              f"{'Acc@10':>7s} {'ceiling':>8s}")
        for cond, (a5, a10, ce, n) in sorted(per_cond.items()):
            lo, hi = wilson(a5, n)
            print(f"{cond:18s} {n:5d} {100*a5/n:6.1f}% "
                  f"[{lo:5.1f}, {hi:5.1f}] {100*a10/n:6.1f}% "
                  f"{100*ce/n:7.1f}%")

    # paired no-LLM reference: strict accuracy of the raw basket order
    ids = [i for i in inp if i in gold_of]
    for cond, key in [("basket bm25_top", "bm25_plain"),
                      ("basket hybrid_top", "hybrid_plain")]:
        a5 = a10 = n = 0
        for i in ids:
            cands = basket_of(inp[i], key)
            if args.max_cands:
                cands = cands[:args.max_cands]
            if not cands:
                continue
            g = set(gold_of[i])
            a5 += g <= set(cands[:5])
            a10 += g <= set(cands[:10])
            n += 1
        if n:
            print(f"\n{cond} order, no LLM (n={n}): "
                  f"Acc@5 {100*a5/n:.1f}%  Acc@10 {100*a10/n:.1f}%")


if __name__ == "__main__":
    main()
