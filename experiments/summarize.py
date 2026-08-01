"""Aggregate results/results.jsonl -> results/summary.md (+ stdout)."""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).parent
RESULTS = Path(sys.argv[1]) if len(sys.argv) > 1 else (
    HERE / "results" / "results.jsonl")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else (
    HERE / "results" / "summary.md")


def main():
    recs, errors, e1 = [], 0, []
    with open(RESULTS, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if "error" in r or "skip" in r:
                errors += 1
                continue
            recs.append(r)
            if r.get("e1"):
                e1.append((r["repo"], r["e1"]))

    agg = defaultdict(lambda: defaultdict(float))
    counts = defaultdict(int)
    for r in recs:
        for cfg, m in r["configs"].items():
            if not m:
                continue
            counts[cfg] += 1
            for k, v in m.items():
                agg[cfg][k] += v

    lines = [f"# Pilot summary — {len(recs)} instances, {errors} errors/skips",
             "",
             "| config | R@1 | R@5 | R@10 | Hit@5 | Hit@10 | MAP | n |",
             "|---|---|---|---|---|---|---|---|"]
    def key(cfg):
        m = agg[cfg]
        return -(m["r10"] / max(1, counts[cfg]))
    for cfg in sorted(agg, key=key):
        n = counts[cfg]
        m = {k: v / n for k, v in agg[cfg].items()}
        lines.append(
            f"| {cfg} | {m.get('r1', 0):.3f} | {m.get('r5', 0):.3f} "
            f"| {m.get('r10', 0):.3f} | {m.get('hit5', 0):.3f} "
            f"| {m.get('hit10', 0):.3f} | {m.get('ap', 0):.3f} | {n} |")

    lines += ["", "## E1 orthogonality (median Jaccard of top-10 neighbours)",
              "", "| repo | median | mean | files |", "|---|---|---|---|"]
    for repo, m in e1:
        lines.append(f"| {repo} | {m['median']:.3f} | {m['mean']:.3f} "
                     f"| {m['n_files']} |")

    # per-repo best-config vs bm25 delta
    by_repo = defaultdict(list)
    for r in recs:
        by_repo[r["repo"]].append(r)
    lines += ["", "## R@10 by repo: BM25 vs best hybrid", "",
              "| repo | n | bm25 | best hybrid | Δ | best cfg |",
              "|---|---|---|---|---|---|"]
    for repo, rs in sorted(by_repo.items()):
        bm = sum(x["configs"]["bm25"].get("r10", 0) for x in rs) / len(rs)
        best_cfg, best_v = None, -1
        cfgs = {c for x in rs for c in x["configs"] if c not in ("bm25", "grep")}
        for c in cfgs:
            xs = [x["configs"][c].get("r10", 0) for x in rs if c in x["configs"]]
            v = sum(xs) / len(xs) if xs else 0
            if v > best_v:
                best_cfg, best_v = c, v
        lines.append(f"| {repo} | {len(rs)} | {bm:.3f} | {best_v:.3f} "
                     f"| {best_v - bm:+.3f} | {best_cfg} |")

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
