"""Candidate baskets built with the night-lab final recipe.

Recipe (validated on holdout + Lite + Verified): RRF fusion (k=40) of six
lists — BM25, PPR(BM25 seed), PPR(grep seed), recency prior, path-token
scores, explicit paths from the issue — raw grep list excluded; tests/docs
demoted over the top-200; truncated to 100.

Usage: py -3.12 prepare_final.py [--bench locbench|lite|verified]
"""
import argparse
import json
import time
import traceback
from pathlib import Path

import chrono
import night_lab as nl

HERE = Path(__file__).parent


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default="locbench",
                    choices=["locbench", "lite", "verified"])
    args = ap.parse_args()
    out_path = HERE / "data" / f"rerank_final_{args.bench}.jsonl"

    done = set()
    if out_path.exists():
        for line in open(out_path, encoding="utf-8"):
            try:
                done.add(json.loads(line)["instance_id"])
            except (json.JSONDecodeError, KeyError):
                pass
    insts = [i for i in nl.load_instances("all", args.bench)
             if i["instance_id"] not in done]
    log(f"{args.bench}: {len(insts)} instances to prepare")

    out = open(out_path, "a", encoding="utf-8")
    cur_repo, bc, t0 = None, None, time.time()
    for k, inst in enumerate(sorted(insts, key=lambda x: x["repo"])):
        try:
            repo_dir = HERE / "repos" / (inst["repo"].replace("/", "__")
                                         + ".git")
            if inst["repo"] != cur_repo:
                cur_repo = inst["repo"]
                bc = chrono.BlobCache(repo_dir)
            history = chrono.mine_history(
                repo_dir, HERE / "cache" / (inst["repo"].replace("/", "__")
                                            + "_log.pkl"))
            ctx = nl.build_context(inst, repo_dir, history, bc)
            cands = nl.rrf_final(ctx, k=40, exclude=("gr",))
            out.write(json.dumps({
                "instance_id": inst["instance_id"],
                "repo": inst["repo"],
                "category": inst.get("category"),
                "issue": inst["problem_statement"][:1500],
                "gold": inst["gold"],
                "hybrid_top": [{"file": p} for p in cands],
            }) + "\n")
            out.flush()
            if (k + 1) % 50 == 0:
                log(f"{k + 1}/{len(insts)} "
                    f"({(time.time() - t0) / (k + 1):.1f}s/inst)")
            bc.maybe_trim()
        except Exception:
            log(f"{inst['instance_id']} ERROR "
                f"{traceback.format_exc().splitlines()[-1]}")
    out.close()
    log("FINAL PREP DONE")


if __name__ == "__main__":
    main()
