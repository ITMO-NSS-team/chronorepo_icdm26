"""Appendix H: does effectiveness depend on project history length?

Buckets LocBench instances by the commit count of their repository and
reports, per bucket: the paired gain of graph propagation over BM25, the
temporal-vs-static layer difference, end-to-end reranked accuracy, and the
median number of co-change edges available at the instance's base commit.

Requires data/repo_commit_counts.json (built here on first run).
Usage: py -3.12 analyze_history_length.py
"""
import json
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
COUNTS = HERE / "data" / "repo_commit_counts.json"


def commit_counts(repos):
    if COUNTS.exists():
        return json.loads(COUNTS.read_text())
    counts = {}
    for rp in sorted(repos):
        d = HERE / "repos" / (rp.replace("/", "__") + ".git")
        if not d.exists():
            continue
        try:
            out = subprocess.run(["git", "-C", str(d), "rev-list", "--count",
                                  "HEAD"], capture_output=True, check=True)
            counts[rp] = int(out.stdout)
        except (subprocess.CalledProcessError, ValueError):
            pass
    COUNTS.write_text(json.dumps(counts))
    return counts


def main():
    recs = {}
    for line in open(HERE / "results" / "results_locbench.jsonl",
                     encoding="utf-8"):
        r = json.loads(line)
        if "configs" in r:
            recs[r["instance_id"]] = r
    counts = commit_counts({r["repo"] for r in recs.values()})
    recs = {i: r for i, r in recs.items() if r["repo"] in counts}

    ef = json.loads((HERE / "data" / "edit_functions.json").read_text())
    gold_of = {k: sorted({e.split(":")[0] for e in v})
               for k, v in ef.items() if v}
    inp = {json.loads(l)["instance_id"]: json.loads(l)
           for l in open(HERE / "data" / "rerank_input50.jsonl",
                         encoding="utf-8")}
    son = {}
    p = HERE / "results" / "rerank_sonnet45_top50.jsonl"
    if p.exists():
        for line in open(p, encoding="utf-8"):
            r = json.loads(line)
            if "ranked" in r:
                son[r["instance_id"]] = r

    ids = sorted(set(recs) & set(gold_of) & set(inp) & set(son))
    ordered = sorted(ids, key=lambda i: counts[recs[i]["repo"]])
    th = [counts[recs[ordered[k * len(ordered) // 4]]["repo"]]
          for k in (1, 2, 3)]

    def bucket(i):
        c = counts[recs[i]["repo"]]
        return 0 if c <= th[0] else 1 if c <= th[1] else 2 if c <= th[2] else 3

    names = [f"Q1 short (<={th[0]})", f"Q2 (<={th[1]})",
             f"Q3 (<={th[2]})", f"Q4 long (>{th[2]})"]
    groups = defaultdict(list)
    for i in ids:
        groups[bucket(i)].append(i)

    def acc5(i):
        cands = [c["file"] for c in inp[i]["hybrid_top"]]
        full = list(son[i]["ranked"]) + [c for c in cands
                                         if c not in son[i]["ranked"]]
        return set(gold_of[i]) <= set(full[:5])

    print("history bucket             n   dR@10 graph-BM25   d temporal-"
          "static   Sonnet Acc@5   median co-edges")
    for b in range(4):
        g = groups[b]
        gain = statistics.mean(
            recs[i]["configs"]["bm25_a025_l90"]["r10"]
            - recs[i]["configs"]["bm25"]["r10"] for i in g)
        dtemp = statistics.mean(
            recs[i]["configs"]["bm25_a000_l90"]["r10"]
            - recs[i]["configs"]["bm25_a100_l0"]["r10"] for i in g)
        a = 100 * sum(acc5(i) for i in g) / len(g)
        edges = statistics.median(r["n_temporal_edges"]
                                  for r in (recs[i] for i in g))
        print(f"{names[b]:24s} {len(g):4d} {100 * gain:+16.1f} "
              f"{100 * dtemp:+18.1f} {a:14.1f}% {edges:16.0f}")


if __name__ == "__main__":
    main()
