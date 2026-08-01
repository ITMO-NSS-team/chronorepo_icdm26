"""Overnight E1/E2 pilot runner. Resumable: instances already present in
results/results.jsonl are skipped, so the run can be killed and restarted.

Usage:
  py -3.12 run_experiments.py                 # full SWE-bench Lite
  py -3.12 run_experiments.py --repos pallets/flask --limit 2   # smoke test
"""
import argparse
import json
import time
import traceback
from collections import defaultdict
from pathlib import Path

import chrono

HERE = Path(__file__).parent
REPOS = HERE / "repos"
CACHE = HERE / "cache"

LAMBDAS = {"l0": 0.0, "l90": 1 / 90, "l30": 1 / 30}
ALPHAS = [0.0, 0.25, 0.5, 0.75, 1.0]
BETA = 0.5


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def clone_bare(repo):
    dest = REPOS / (repo.replace("/", "__") + ".git")
    if dest.exists():
        return dest
    log(f"cloning {repo} (bare) ...")
    chrono.git(REPOS, "clone", "--bare",
               f"https://github.com/{repo}.git", str(dest))
    return dest


def load_done(results_path):
    done = set()
    if results_path.exists():
        with open(results_path, encoding="utf-8") as f:
            for line in f:
                try:
                    done.add(json.loads(line).get("instance_id"))
                except json.JSONDecodeError:
                    pass
    return done


def process_instance(inst, repo_dir, history, blob_cache, do_e1):
    t0 = time.time()
    base = inst["base_commit"]
    gold = inst.get("gold_override") or chrono.gold_files_from_patch(
        inst["patch"])
    if not gold:
        return {"instance_id": inst["instance_id"], "skip": "no gold files"}

    ancestors = chrono.ancestor_set(repo_dir, base)
    files = chrono.tree_at(repo_dir, base)          # {path: sha}, text files
    py_files = {p: s for p, s in files.items() if p.endswith(".py")}
    base_ts = int(chrono.git(repo_dir, "show", "-s", "--format=%ct",
                             base).strip())
    blob_cache.load_missing(files)

    # --- graphs ---------------------------------------------------------
    s_edges = chrono.static_edges(files, blob_cache, repo_dir)
    t_edges = {name: chrono.temporal_edges(history, ancestors, base_ts, lam,
                                           set(py_files))
               for name, lam in LAMBDAS.items()}

    py_paths = sorted(py_files)
    py_idx = {p: i for i, p in enumerate(py_paths)}
    n_py = len(py_paths)
    rows_s = chrono.row_normalized(s_edges, py_idx)
    rows_t = {k: chrono.row_normalized(v, py_idx) for k, v in t_edges.items()}

    # --- seeds ----------------------------------------------------------
    docs = {p: blob_cache.tokens[s] for p, s in files.items()
            if s in blob_cache.tokens}
    bm25 = chrono.BM25(docs)
    q_tokens = chrono.tokenize(inst["problem_statement"], cap=3000)
    bm25_list = bm25.query(q_tokens)
    idents = chrono.issue_identifiers(inst["problem_statement"])
    grep_list = chrono.grep_scores(idents, files, blob_cache)
    seeds = {"bm25": bm25_list, "grep": grep_list}

    # --- config grid ------------------------------------------------------
    configs = {}
    configs["bm25"] = chrono.eval_ranking([p for p, _ in bm25_list], gold)
    configs["grep"] = chrono.eval_ranking([p for p, _ in grep_list], gold)
    all_paths = list(files)
    for seed_name, seed_list in seeds.items():
        for a in ALPHAS:
            lam_names = ["l0"] if a >= 1.0 else list(LAMBDAS)
            for ln in lam_names:
                rows = chrono.mix_rows(rows_s, rows_t[ln], a, n_py)
                ranked = chrono.hybrid_rank(seed_list, rows, py_idx, n_py,
                                            all_paths, beta=BETA)
                key = f"{seed_name}_a{int(a * 100):03d}_{ln}"
                configs[key] = chrono.eval_ranking(ranked, gold)

    rec = {
        "instance_id": inst["instance_id"],
        "category": inst.get("category"),
        "repo": inst["repo"],
        "base": base,
        "n_files": len(files),
        "n_py": n_py,
        "n_static_edges": len(s_edges),
        "n_temporal_edges": len(t_edges["l0"]),
        "gold": gold,
        "configs": configs,
        "sec": round(time.time() - t0, 1),
    }
    if do_e1:
        rec["e1"] = chrono.e1_orthogonality(s_edges, t_edges["l90"])
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", nargs="*", help="only these repos")
    ap.add_argument("--limit", type=int, default=0,
                    help="max instances per repo (0 = all)")
    ap.add_argument("--data", default=str(HERE / "data" / "swebench_lite.jsonl"))
    ap.add_argument("--out", default=str(HERE / "results" / "results.jsonl"))
    args = ap.parse_args()
    results_path = Path(args.out)

    REPOS.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    results_path.parent.mkdir(parents=True, exist_ok=True)

    instances = [json.loads(l) for l in open(args.data, encoding="utf-8")]
    by_repo = defaultdict(list)
    for inst in instances:
        by_repo[inst["repo"]].append(inst)
    # smallest repos first: diverse coverage even if the night ends early
    repo_order = sorted(by_repo, key=lambda r: len(by_repo[r]))
    if args.repos:
        repo_order = [r for r in repo_order if r in set(args.repos)]

    done = load_done(results_path)
    log(f"{len(instances)} instances, {len(done)} already done, "
        f"{len(repo_order)} repos")

    out = open(results_path, "a", encoding="utf-8")
    for repo in repo_order:
        todo = [i for i in by_repo[repo] if i["instance_id"] not in done]
        if args.limit:
            todo = todo[:args.limit]
        if not todo:
            continue
        log(f"=== {repo}: {len(todo)} instances ===")
        try:
            repo_dir = clone_bare(repo)
            history = chrono.mine_history(
                repo_dir, CACHE / (repo.replace("/", "__") + "_log.pkl"))
            log(f"history: {len(history)} usable commits")
        except Exception:
            log(f"REPO FAILED {repo}\n{traceback.format_exc()}")
            continue
        blob_cache = chrono.BlobCache(repo_dir)
        first = True
        for inst in todo:
            try:
                rec = process_instance(inst, repo_dir, history, blob_cache,
                                       do_e1=first)
                first = False
                out.write(json.dumps(rec) + "\n")
                out.flush()
                best = rec.get("configs", {}).get("bm25", {}).get("r10")
                log(f"  {inst['instance_id']} ok "
                    f"({rec.get('sec', '?')}s, bm25 r10={best})")
            except Exception:
                out.write(json.dumps({
                    "instance_id": inst["instance_id"], "repo": repo,
                    "error": traceback.format_exc()[-500:]}) + "\n")
                out.flush()
                log(f"  {inst['instance_id']} ERROR (logged)")
            blob_cache.maybe_trim()
    out.close()
    log("ALL DONE")


if __name__ == "__main__":
    main()
