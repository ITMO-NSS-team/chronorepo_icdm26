"""Precompute rerank inputs for the LocBench x Qwen experiment.

For every valid LocBench instance produces: issue excerpt, gold files, and
two top-20 candidate lists (BM25; hybrid graph) — the hybrid one annotated
with human-readable evidence (co-change counts, imports, propagation).
Output: data/rerank_input.jsonl. No LLM calls here. Resumable."""
import json
import time
import traceback
from pathlib import Path

import chrono

HERE = Path(__file__).parent
OUT = HERE / "data" / "rerank_input.jsonl"
TOP = 20


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def evidence_str(seed_top, g, s_edges, t_edges_raw, ppr_score):
    parts = []
    best = None
    for p in seed_top:
        e = t_edges_raw.get(tuple(sorted((p, g))))
        if e and (best is None or e > best[1]):
            best = (p, e)
    if best:
        parts.append(f"co-changed with {best[0].rsplit('/',1)[-1]} "
                     f"x{int(best[1])}")
    for p in seed_top:
        if tuple(sorted((p, g))) in s_edges:
            parts.append(f"import link to {p.rsplit('/',1)[-1]}")
            break
    if ppr_score > 0:
        parts.append(f"graph score {ppr_score:.2f}")
    return "; ".join(parts[:3])


def main():
    done = set()
    if OUT.exists():
        for line in open(OUT, encoding="utf-8"):
            try:
                done.add(json.loads(line)["instance_id"])
            except (json.JSONDecodeError, KeyError):
                pass
    insts = [json.loads(l) for l in
             open(HERE / "data" / "locbench.jsonl", encoding="utf-8")]
    # only instances that produced valid results in the main run
    valid = set()
    for line in open(HERE / "results" / "results_locbench.jsonl",
                     encoding="utf-8"):
        r = json.loads(line)
        if "configs" in r:
            valid.add(r["instance_id"])
    todo = [i for i in insts if i["instance_id"] in valid
            and i["instance_id"] not in done]
    log(f"{len(todo)} instances to prepare")

    out = open(OUT, "a", encoding="utf-8")
    cur_repo, bc = None, None
    for k, inst in enumerate(sorted(todo, key=lambda x: x["repo"])):
        try:
            repo_dir = HERE / "repos" / (inst["repo"].replace("/", "__")
                                         + ".git")
            if inst["repo"] != cur_repo:
                cur_repo = inst["repo"]
                bc = chrono.BlobCache(repo_dir)
            history = chrono.mine_history(
                repo_dir,
                HERE / "cache" / (inst["repo"].replace("/", "__")
                                  + "_log.pkl"))
            base = inst["base_commit"]
            gold = chrono.gold_files_from_patch(inst["patch"])
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

            s_edges = chrono.static_edges(files, bc, repo_dir)
            t_dec = chrono.temporal_edges(history, ancestors, base_ts, 1 / 90,
                                          set(py_files))
            t_raw = chrono.temporal_edges(history, ancestors, base_ts, 0.0,
                                          set(py_files))
            py_paths = sorted(py_files)
            py_idx = {p: i for i, p in enumerate(py_paths)}
            n_py = len(py_paths)
            rows = chrono.mix_rows(chrono.row_normalized(s_edges, py_idx),
                                   chrono.row_normalized(t_dec, py_idx),
                                   0.25, n_py)
            hybrid = chrono.hybrid_rank(seed_list, rows, py_idx, n_py,
                                        list(files), top=TOP)
            seed_top = [p for p, _ in seed_list[:10]]
            # per-candidate propagation score for evidence
            seed_vec = [0.0] * n_py
            tot = sum(s for _, s in seed_list[:20]) or 1.0
            for p, s in seed_list[:20]:
                i = py_idx.get(p)
                if i is not None:
                    seed_vec[i] += s / tot
            pv = chrono.ppr(rows, seed_vec, n_py)
            pmax = max(pv) or 1.0
            cand_hybrid = []
            for p in hybrid:
                i = py_idx.get(p)
                ev = evidence_str(seed_top, p, s_edges, t_raw,
                                  (pv[i] / pmax) if i is not None else 0.0)
                cand_hybrid.append({"file": p, "evidence": ev})

            out.write(json.dumps({
                "instance_id": inst["instance_id"],
                "repo": inst["repo"],
                "category": inst.get("category"),
                "issue": inst["problem_statement"][:1500],
                "gold": gold,
                "bm25_top": [p for p, _ in seed_list[:TOP]],
                "hybrid_top": cand_hybrid,
            }) + "\n")
            out.flush()
            if (k + 1) % 50 == 0:
                log(f"{k + 1}/{len(todo)}")
        except Exception:
            log(f"{inst['instance_id']} ERROR "
                f"{traceback.format_exc().splitlines()[-1]}")
    out.close()
    log("PREP DONE")


if __name__ == "__main__":
    main()
