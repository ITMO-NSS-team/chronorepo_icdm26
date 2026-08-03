"""End-to-end ablation: dump candidate baskets for key ablation variants
so the LLM rerank stage can be measured on each.

Variants: full, no_graph, no_path, fuse_union (the earlier recipe).
Runs on the LocBench holdout half. Output: data/abl_<variant>.jsonl
"""
import json
import time
import traceback
from pathlib import Path

import ablation as ab
import chrono
import night_lab as nl

HERE = Path(__file__).parent
VARIANTS = ["no_graph", "no_path", "fuse_union"]


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    insts = nl.load_instances("holdout")
    outs = {}
    done = {}
    for v in VARIANTS:
        p = HERE / "data" / f"abl_{v}.jsonl"
        d = set()
        if p.exists():
            for line in open(p, encoding="utf-8"):
                try:
                    d.add(json.loads(line)["instance_id"])
                except (json.JSONDecodeError, KeyError):
                    pass
        done[v] = d
        outs[v] = open(p, "a", encoding="utf-8")
    todo = [i for i in insts
            if any(i["instance_id"] not in done[v] for v in VARIANTS)]
    log(f"{len(todo)} instances")

    cur_repo, bc, t0 = None, None, time.time()
    for k, inst in enumerate(sorted(todo, key=lambda x: x["repo"])):
        try:
            repo_dir = HERE / "repos" / (inst["repo"].replace("/", "__")
                                         + ".git")
            if inst["repo"] != cur_repo:
                cur_repo = inst["repo"]
                bc = chrono.BlobCache(repo_dir)
            history = chrono.mine_history(
                repo_dir, HERE / "cache" / (inst["repo"].replace("/", "__")
                                            + "_log.pkl"))
            ctx = ab.build(inst, repo_dir, history, bc)
            for v in VARIANTS:
                if inst["instance_id"] in done[v]:
                    continue
                cands = ab.VARIANTS[v](ctx)
                outs[v].write(json.dumps({
                    "instance_id": inst["instance_id"],
                    "repo": inst["repo"],
                    "issue": inst["problem_statement"][:1500],
                    "gold": inst["gold"],
                    "hybrid_top": [{"file": p} for p in cands],
                }) + "\n")
                outs[v].flush()
            if (k + 1) % 25 == 0:
                log(f"{k + 1}/{len(todo)} "
                    f"({(time.time() - t0) / (k + 1):.1f}s/inst)")
            bc.maybe_trim()
        except Exception:
            log(f"{inst['instance_id']} ERROR "
                f"{traceback.format_exc().splitlines()[-1]}")
    for f in outs.values():
        f.close()
    log("E2E PREP DONE")


if __name__ == "__main__":
    main()
