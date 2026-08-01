"""Aggregate results/e3.jsonl -> results/summary_e3.md."""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
RESULTS = HERE / "results" / "e3.jsonl"
OUT = HERE / "results" / "summary_e3.md"


def main():
    per_cfg = defaultdict(lambda: [0.0, 0.0, 0])   # r10 sum, mrr sum, n
    per_repo = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0, 0]))
    n_commits, errors = 0, 0
    for line in open(RESULTS, encoding="utf-8"):
        r = json.loads(line)
        if "error" in r or not r.get("seeds"):
            errors += 1
            continue
        n_commits += 1
        for seed in r["seeds"]:
            for cfg, m in seed["configs"].items():
                for store in (per_cfg[cfg], per_repo[r["repo"]][cfg]):
                    store[0] += m["r10"]
                    store[1] += m["mrr"]
                    store[2] += 1

    lines = [f"# E3 blast radius — {n_commits} commits, {errors} errors/skips",
             "", "| config | R@10 | MRR | n seeds |", "|---|---|---|---|"]
    for cfg, (r10, mrr, n) in sorted(per_cfg.items(),
                                     key=lambda kv: -kv[1][0] / kv[1][2]):
        lines.append(f"| {cfg} | {r10 / n:.3f} | {mrr / n:.3f} | {n} |")

    lines += ["", "## R@10 by repo", "",
              "| repo | " + " | ".join(sorted(per_cfg)) + " |",
              "|---|" + "---|" * len(per_cfg)]
    for repo, cfgs in sorted(per_repo.items()):
        cells = []
        for cfg in sorted(per_cfg):
            r10, _, n = cfgs.get(cfg, [0, 0, 0])
            cells.append(f"{r10 / n:.3f}" if n else "–")
        lines.append(f"| {repo} | " + " | ".join(cells) + " |")

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
