"""Score dump for the CodeScout F1 protocol (variable-size predictions).

For each SWE-bench instance stores top-50 scored files for the hybrid
(bm25 seed, alpha=0.25, lambda=1/90) and for plain BM25. Threshold sweep
and F1 aggregation happen offline in analyze_f1.py. Resumable.
Usage: py -3.12 run_f1.py lite|verified"""
import json
import sys
import time
import traceback
from collections import defaultdict
from pathlib import Path

import chrono

HERE = Path(__file__).parent
WHICH = sys.argv[1] if len(sys.argv) > 1 else "lite"
DATA = HERE / "data" / ("swebench_lite.jsonl" if WHICH == "lite"
                        else "swebench_verified.jsonl")
OUT = HERE / "results" / f"f1_scores_{WHICH}.jsonl"


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    done = set()
    if OUT.exists():
        for line in open(OUT, encoding="utf-8"):
            try:
                done.add(json.loads(line)["instance_id"])
            except (json.JSONDecodeError, KeyError):
                pass
    insts = [json.loads(l) for l in open(DATA, encoding="utf-8")]
    by_repo = defaultdict(list)
    for i in insts:
        if i["instance_id"] not in done:
            by_repo[i["repo"]].append(i)
    log(f"{sum(map(len, by_repo.values()))} instances to score")

    out = open(OUT, "a", encoding="utf-8")
    for repo in sorted(by_repo, key=lambda r: len(by_repo[r])):
        repo_dir = HERE / "repos" / (repo.replace("/", "__") + ".git")
        history = chrono.mine_history(
            repo_dir, HERE / "cache" / (repo.replace("/", "__") + "_log.pkl"))
        bc = chrono.BlobCache(repo_dir)
        log(f"=== {repo}: {len(by_repo[repo])} ===")
        for inst in by_repo[repo]:
            try:
                base = inst["base_commit"]
                gold = chrono.gold_files_from_patch(inst["patch"])
                ancestors = chrono.ancestor_set(repo_dir, base)
                files = chrono.tree_at(repo_dir, base)
                py_files = {p: s for p, s in files.items()
                            if p.endswith(".py")}
                base_ts = int(chrono.git(repo_dir, "show", "-s",
                                         "--format=%ct", base).strip())
                bc.load_missing(files)
                docs = {p: bc.tokens[s] for p, s in files.items()
                        if s in bc.tokens}
                bm25 = chrono.BM25(docs)
                seed = bm25.query(
                    chrono.tokenize(inst["problem_statement"], cap=3000))
                s_edges = chrono.static_edges(files, bc, repo_dir)
                t_dec = chrono.temporal_edges(history, ancestors, base_ts,
                                              1 / 90, set(py_files))
                py_paths = sorted(py_files)
                py_idx = {p: i for i, p in enumerate(py_paths)}
                n_py = len(py_paths)
                rows = chrono.mix_rows(
                    chrono.row_normalized(s_edges, py_idx),
                    chrono.row_normalized(t_dec, py_idx), 0.25, n_py)
                hyb = chrono.hybrid_rank(seed, rows, py_idx, n_py,
                                         list(files), return_scores=True)
                out.write(json.dumps({
                    "instance_id": inst["instance_id"],
                    "gold": gold,
                    "hybrid": [[p, round(s, 5)] for p, s in hyb],
                    "bm25": [[p, round(s, 3)] for p, s in seed[:50]],
                }) + "\n")
                out.flush()
            except Exception:
                log(f"  {inst['instance_id']} ERROR "
                    f"{traceback.format_exc().splitlines()[-1]}")
            bc.maybe_trim()
    out.close()
    log(f"F1 SCORES DONE ({WHICH})")


if __name__ == "__main__":
    main()
