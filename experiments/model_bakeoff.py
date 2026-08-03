"""Bake-off: which open model, used as a single-call reranker over our
candidates, gets closest to (or past) the LocAgent + Claude-3.5 agent
(83.4 strict Acc@5 on LocBench)?

Stage 1 runs a fixed random subset; stage 2 runs the winner on everything.

Usage:
  py -3.12 model_bakeoff.py stage1 [--n 80]
  py -3.12 model_bakeoff.py report
"""
import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
INP = HERE / "data" / "rerank_final_locbench.jsonl"
OUTDIR = HERE / "results" / "bakeoff"

CANDIDATES = [
    "qwen/qwen-2.5-7b-instruct",          # current baseline
    "qwen/qwen3-32b",
    "qwen/qwen-2.5-72b-instruct",
    "qwen/qwen3-next-80b-a3b-instruct",
    "qwen/qwen3-235b-a22b-2507",
    "qwen/qwen3-coder",                   # 480B MoE coder
    "deepseek/deepseek-chat-v3.1",
    "moonshotai/kimi-k2-0905",
    "meta-llama/llama-3.3-70b-instruct",
]


def subset_ids(n):
    ids = [json.loads(l)["instance_id"] for l in open(INP, encoding="utf-8")]
    ids.sort(key=lambda i: hashlib.sha1(("bake" + i).encode()).hexdigest())
    return set(ids[:n])


def wilson(k, n, z=1.96):
    if not n:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * (c - h), 100 * (c + h)


def slug(model):
    return model.replace("/", "_").replace(".", "-")


def cmd_stage1(args):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    keep = subset_ids(args.n)
    sub = OUTDIR / f"subset_{args.n}.jsonl"
    with open(sub, "w", encoding="utf-8") as f:
        for line in open(INP, encoding="utf-8"):
            if json.loads(line)["instance_id"] in keep:
                f.write(line)
    print(f"subset: {sum(1 for _ in open(sub, encoding='utf-8'))} instances")
    for model in CANDIDATES:
        out = OUTDIR / f"{slug(model)}_s1.jsonl"
        print(f"=== {model}", flush=True)
        subprocess.run([sys.executable, "-u", str(HERE / "run_rerank.py"),
                        "--input", str(sub), "--out", str(out),
                        "--model", model, "--conditions", "hybrid_plain",
                        "--max-cands", "50", "--workers", "6"],
                       cwd=HERE, check=False)


def evaluate(path, inp):
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    ok = [r for r in rows if "ranked" in r]
    hit5 = hit10 = n = 0
    toks = []
    for r in ok:
        i = r["instance_id"]
        if i not in inp:
            continue
        cands = [c["file"] for c in inp[i]["hybrid_top"]][:50]
        full = list(r["ranked"]) + [c for c in cands if c not in r["ranked"]]
        gold = set(inp[i]["gold"])
        hit5 += gold <= set(full[:5])
        hit10 += gold <= set(full[:10])
        n += 1
        if r.get("tokens"):
            toks.append(r["tokens"])
    return {"n": n, "errors": len(rows) - len(ok),
            "acc5": 100 * hit5 / n if n else 0,
            "acc10": 100 * hit10 / n if n else 0,
            "ci": wilson(hit5, n),
            "tokens": sum(toks) / len(toks) if toks else 0}


def cmd_report(args):
    inp = {json.loads(l)["instance_id"]: json.loads(l)
           for l in open(INP, encoding="utf-8")}
    print(f"{'model':42s} {'n':>4s} {'err':>4s} {'Acc@5':>7s} "
          f"{'95% CI':>14s} {'Acc@10':>7s} {'tok':>6s}")
    rows = []
    for model in CANDIDATES:
        p = OUTDIR / f"{slug(model)}_s1.jsonl"
        if p.exists():
            rows.append((evaluate(p, inp)["acc5"], model,
                         evaluate(p, inp)))
    for a5, model, m in sorted(rows, reverse=True):
        lo, hi = m["ci"]
        print(f"{model:42s} {m['n']:4d} {m['errors']:4d} {a5:6.1f}% "
              f"[{lo:5.1f},{hi:5.1f}] {m['acc10']:6.1f}% {m['tokens']:6.0f}")
    print("\nreference on full LocBench: LocAgent+Claude-3.5 agent 83.4, "
          "LocAgent ft-7B agent 78.6, CodeRankEmbed 74.3")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["stage1", "report"])
    ap.add_argument("--n", type=int, default=80)
    a = ap.parse_args()
    (cmd_stage1 if a.cmd == "stage1" else cmd_report)(a)
