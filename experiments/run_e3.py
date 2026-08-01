"""E3: blast-radius / co-change prediction, leave-last-N-commits-out.

For each repo: take the most recent N commits on HEAD that touched 2..10
.py files. For each such commit, seed with one changed file (up to 2 seeds
per commit) and predict the *other* changed files, using only history and
code state strictly before the commit (graphs built at commit^, temporal
edges filtered to ancestors of commit^ — exact, no leakage).

Baselines: freq (most-changed files), rose (direct co-change neighbours,
raw counts — Zimmermann-style association), static-PPR, temporal-PPR,
hybrid PPR. Metrics: R@10, MRR. Resumable like run_experiments.
"""
import argparse
import json
import time
import traceback
from collections import Counter
from pathlib import Path

import chrono

HERE = Path(__file__).parent
REPOS = HERE / "repos"
CACHE = HERE / "cache"
RESULTS = HERE / "results" / "e3.jsonl"

REPO_LIST = [
    "pallets/flask", "psf/requests", "mwaskom/seaborn", "pydata/xarray",
    "pylint-dev/pylint", "pytest-dev/pytest", "sphinx-doc/sphinx",
    "astropy/astropy", "scikit-learn/scikit-learn", "matplotlib/matplotlib",
    "sympy/sympy", "django/django",
]
N_COMMITS = 200
LAM = 1 / 90  # decay for the temporal PPR variants

CONFIGS = ["freq", "rose", "static_ppr", "temporal_ppr", "hybrid_a25",
           "hybrid_a50"]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def head_commits(repo_dir, n, lo=2, hi=10):
    """Most recent HEAD commits touching lo..hi .py files."""
    raw = chrono.git_bytes(repo_dir, "log", "--numstat",
                           "--format=%x01%H%x09%ct", "-n", "3000", "HEAD")
    out, sha, ts, files = [], None, None, []
    for line in raw.decode("utf-8", "replace").splitlines():
        if line.startswith("\x01"):
            if sha and lo <= len(files) <= hi:
                out.append((sha, ts, files))
            sha, ts_s = line[1:].split("\t")
            ts, files = int(ts_s), []
        elif line and "\t" in line:
            parts = line.split("\t")
            if len(parts) == 3:
                p = chrono._clean_path(parts[2])
                if p.endswith(".py"):
                    files.append(p)
    if sha and lo <= len(files) <= hi:
        out.append((sha, ts, files))
    return out[:n]


def rank_of(ranked, gold):
    """metrics for one seed: R@10 over gold set + MRR of first hit."""
    gold = set(gold)
    top10 = ranked[:10]
    r10 = len(gold & set(top10)) / len(gold)
    mrr = 0.0
    for i, p in enumerate(ranked[:50], 1):
        if p in gold:
            mrr = 1.0 / i
            break
    return {"r10": r10, "mrr": mrr}


def process_commit(repo_dir, history, blob_cache, sha, ts, files):
    parent = sha + "^"
    ancestors = chrono.ancestor_set(repo_dir, parent)
    tree = chrono.tree_at(repo_dir, parent)
    py_files = {p: s for p, s in tree.items() if p.endswith(".py")}
    # gold/seed candidates must exist before the commit
    present = [f for f in files if f in py_files]
    if len(present) < 2:
        return None
    blob_cache.load_missing(py_files)

    s_edges = chrono.static_edges(py_files, blob_cache, repo_dir)
    t_raw = chrono.temporal_edges(history, ancestors, ts, 0.0, set(py_files))
    t_dec = chrono.temporal_edges(history, ancestors, ts, LAM, set(py_files))

    py_paths = sorted(py_files)
    py_idx = {p: i for i, p in enumerate(py_paths)}
    n_py = len(py_paths)
    rows_s = chrono.row_normalized(s_edges, py_idx)
    rows_t = chrono.row_normalized(t_dec, py_idx)

    # freq baseline: change counts before cutoff
    freq = Counter()
    for csha, _, cfiles in history:
        if csha in ancestors:
            for f in cfiles:
                if f in py_files:
                    freq[f] += 1
    freq_rank = [p for p, _ in freq.most_common(50)]

    # direct co-change neighbours by raw count (ROSE-style)
    nbrs = {}
    for (a, b), w in t_raw.items():
        nbrs.setdefault(a, {})[b] = w
        nbrs.setdefault(b, {})[a] = w

    results = []
    for seed in present[:2]:
        gold = [f for f in present if f != seed]
        seed_list = [(seed, 1.0)]
        rose_rank = sorted(nbrs.get(seed, {}),
                           key=nbrs.get(seed, {}).get, reverse=True)[:50]
        per_cfg = {
            "freq": rank_of([p for p in freq_rank if p != seed], gold),
            "rose": rank_of(rose_rank, gold),
        }
        for name, alpha in [("static_ppr", 1.0), ("temporal_ppr", 0.0),
                            ("hybrid_a25", 0.25), ("hybrid_a50", 0.5)]:
            rows = chrono.mix_rows(rows_s, rows_t, alpha, n_py)
            ranked = chrono.hybrid_rank(seed_list, rows, py_idx, n_py,
                                        list(py_files), beta=0.0)
            per_cfg[name] = rank_of([p for p in ranked if p != seed], gold)
        results.append({"seed": seed, "n_gold": len(gold), "configs": per_cfg})
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", nargs="*")
    ap.add_argument("--n", type=int, default=N_COMMITS)
    args = ap.parse_args()

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if RESULTS.exists():
        for line in open(RESULTS, encoding="utf-8"):
            try:
                done.add(json.loads(line)["key"])
            except (json.JSONDecodeError, KeyError):
                pass

    repos = args.repos or REPO_LIST
    out = open(RESULTS, "a", encoding="utf-8")
    for repo in repos:
        repo_dir = REPOS / (repo.replace("/", "__") + ".git")
        if not repo_dir.exists():
            log(f"skip {repo}: no clone")
            continue
        history = chrono.mine_history(
            repo_dir, CACHE / (repo.replace("/", "__") + "_log.pkl"))
        commits = head_commits(repo_dir, args.n)
        todo = [(s, t, f) for s, t, f in commits if f"{repo}@{s}" not in done]
        log(f"=== {repo}: {len(todo)}/{len(commits)} commits ===")
        blob_cache = chrono.BlobCache(repo_dir)
        t_repo = time.time()
        for k, (sha, ts, files) in enumerate(todo):
            try:
                t0 = time.time()
                res = process_commit(repo_dir, history, blob_cache, sha, ts,
                                     files)
                out.write(json.dumps({
                    "key": f"{repo}@{sha}", "repo": repo, "sha": sha,
                    "n_changed": len(files), "seeds": res,
                    "sec": round(time.time() - t0, 1)}) + "\n")
                out.flush()
            except Exception:
                out.write(json.dumps({
                    "key": f"{repo}@{sha}", "repo": repo,
                    "error": traceback.format_exc()[-400:]}) + "\n")
                out.flush()
            if (k + 1) % 25 == 0:
                log(f"  {k + 1}/{len(todo)} "
                    f"({(time.time() - t_repo) / (k + 1):.1f}s/commit)")
            blob_cache.maybe_trim()
        log(f"  {repo} done in {(time.time() - t_repo) / 60:.1f} min")
    out.close()
    log("E3 DONE")


if __name__ == "__main__":
    main()
