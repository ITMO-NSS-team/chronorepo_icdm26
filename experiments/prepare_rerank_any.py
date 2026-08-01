"""Top-50 union candidate baskets for any SWE-bench-style dataset.
Usage: py -3.12 prepare_rerank_any.py --data data/swebench_lite.jsonl \
           --out data/rerank50_lite.jsonl
Same basket recipe as LocBench: union of graph(BM25 seed) top-40,
graph(grep seed) top-20, plain BM25 top-10, deduplicated, capped at 50."""
import argparse
import json
import time
import traceback
from pathlib import Path

import chrono

HERE = Path(__file__).parent
TOP = 50


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out_path = Path(args.out)

    done = set()
    if out_path.exists():
        for line in open(out_path, encoding="utf-8"):
            try:
                done.add(json.loads(line)["instance_id"])
            except (json.JSONDecodeError, KeyError):
                pass
    insts = [json.loads(l) for l in open(args.data, encoding="utf-8")]
    todo = [i for i in insts if i["instance_id"] not in done]
    log(f"{len(todo)} instances to prepare -> {out_path.name}")

    out = open(out_path, "a", encoding="utf-8")
    cur_repo, bc = None, None
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
            base = inst["base_commit"]
            gold = (inst.get("gold_override")
                    or chrono.gold_files_from_patch(inst["patch"]))
            ancestors = chrono.ancestor_set(repo_dir, base)
            files = chrono.tree_at(repo_dir, base)
            py_files = {p: s for p, s in files.items() if p.endswith(".py")}
            base_ts = int(chrono.git(repo_dir, "show", "-s", "--format=%ct",
                                     base).strip())
            bc.load_missing(files)
            docs = {p: bc.tokens[s] for p, s in files.items()
                    if s in bc.tokens}
            bm25 = chrono.BM25(docs)
            seed_list = bm25.query(
                chrono.tokenize(inst["problem_statement"], cap=3000))
            grep_list = chrono.grep_scores(
                chrono.issue_identifiers(inst["problem_statement"]),
                files, bc)
            s_edges = chrono.static_edges(files, bc, repo_dir)
            t_dec = chrono.temporal_edges(history, ancestors, base_ts,
                                          1 / 90, set(py_files))
            py_paths = sorted(py_files)
            py_idx = {p: i for i, p in enumerate(py_paths)}
            n_py = len(py_paths)
            rows = chrono.mix_rows(chrono.row_normalized(s_edges, py_idx),
                                   chrono.row_normalized(t_dec, py_idx),
                                   0.25, n_py)
            hyb_bm = chrono.hybrid_rank(seed_list, rows, py_idx, n_py,
                                        list(files), top=40)
            hyb_gr = chrono.hybrid_rank(grep_list, rows, py_idx, n_py,
                                        list(files), top=20)
            hybrid = list(dict.fromkeys(
                hyb_bm + hyb_gr + [p for p, _ in seed_list[:10]]))[:TOP]
            out.write(json.dumps({
                "instance_id": inst["instance_id"],
                "repo": inst["repo"],
                "issue": inst["problem_statement"][:1500],
                "gold": gold,
                "bm25_top": [p for p, _ in seed_list[:20]],
                "hybrid_top": [{"file": p} for p in hybrid],
            }) + "\n")
            out.flush()
            if (k + 1) % 50 == 0:
                log(f"{k + 1}/{len(todo)}")
            bc.maybe_trim()
        except Exception:
            log(f"{inst['instance_id']} ERROR "
                f"{traceback.format_exc().splitlines()[-1]}")
    out.close()
    log("PREP DONE")


if __name__ == "__main__":
    main()
