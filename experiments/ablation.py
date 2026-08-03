"""Full ablation of the ChronoRepo candidate pipeline.

Five axes: (A) candidate sources, (B) graph layers, (C) temporal decay,
(D) propagation parameters, (E) fusion mechanism.

Run on the LocBench holdout half by default: that half was never used when
the recipe was selected, so the ablation is not measuring tuning artifacts.

Usage:
  py -3.12 ablation.py run [--split holdout|dev|all] [--limit N]
  py -3.12 ablation.py analyze [--split holdout] [--latex]
"""
import argparse
import json
import math
import sys
import time
import traceback
from collections import defaultdict
from pathlib import Path

import chrono
import night_lab as nl

HERE = Path(__file__).parent
OUTDIR = HERE / "results" / "ablation"
LAMBDAS = {"l0": 0.0, "l365": 1 / 365, "l90": 1 / 90, "l30": 1 / 30}
DEPTH = 50          # candidate list length used for evaluation
FUSE_K = 40


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


# --------------------------------------------------------------- context

def build(inst, repo_dir, history, bc):
    """Everything every variant may need, computed once per instance."""
    base = inst["base_commit"]
    anc = chrono.ancestor_set(repo_dir, base)
    files = chrono.tree_at(repo_dir, base)
    py = {p: s for p, s in files.items() if p.endswith(".py")}
    base_ts = int(chrono.git(repo_dir, "show", "-s", "--format=%ct",
                             base).strip())
    bc.load_missing(files)

    ctx = nl.build_context(inst, repo_dir, history, bc)  # seeds, recency...
    py_idx, n_py = ctx["py_idx"], ctx["n_py"]

    s_edges = chrono.static_edges(files, bc, repo_dir)
    rows_s = chrono.row_normalized(s_edges, py_idx)
    rows_t = {}
    for name, lam in LAMBDAS.items():
        rows_t[name] = chrono.row_normalized(
            chrono.temporal_edges(history, anc, base_ts, lam, set(py)),
            py_idx)

    def mixed(alpha, lam="l90"):
        return chrono.mix_rows(rows_s, rows_t[lam], alpha, n_py)

    ctx["rows_cfg"] = {
        "recipe": mixed(0.25), "static": rows_s, "temporal": rows_t["l90"],
        "a50": mixed(0.5), "a75": mixed(0.75),
        "l0": mixed(0.25, "l0"), "l365": mixed(0.25, "l365"),
        "l30": mixed(0.25, "l30"),
    }
    ctx["files"] = files
    ctx["_ppr_cache"] = {}
    return ctx


def ppr_scores(ctx, rows_key, seed_key, damping=0.5, iters=10):
    """Cached propagated score dict over all files."""
    ck = (rows_key, seed_key, damping, iters)
    if ck in ctx["_ppr_cache"]:
        return ctx["_ppr_cache"][ck]
    rows = ctx["rows_cfg"][rows_key]
    seed_list = ctx["seed_bm"] if seed_key == "bm" else ctx["seed_gr"]
    n_py, py_idx = ctx["n_py"], ctx["py_idx"]
    vec = [0.0] * n_py
    tot = sum(s for _, s in seed_list[:20]) or 1.0
    for p, s in seed_list[:20]:
        i = py_idx.get(p)
        if i is not None:
            vec[i] += s / tot
    pv = chrono.ppr(rows, vec, n_py, damping=damping, iters=iters)
    pmax = max(pv) or 1.0
    smax = (seed_list[0][1] if seed_list else 1.0) or 1.0
    sd = dict(seed_list)
    out = {}
    for p in ctx["files"]:
        sc = 0.5 * sd.get(p, 0.0) / smax
        i = py_idx.get(p)
        if i is not None:
            sc += 0.5 * pv[i] / pmax
        if sc > 0:
            out[p] = sc
    ctx["_ppr_cache"][ck] = out
    return out


def ranked(d, top=200):
    return [p for p, _ in sorted(d.items(), key=lambda kv: -kv[1])[:top]]


def source_lists(ctx, rows_key="recipe", damping=0.5, iters=10):
    return {
        "bm25": [p for p, _ in ctx["seed_bm"][:100]],
        "ppr_bm": ranked(ppr_scores(ctx, rows_key, "bm", damping, iters),
                         100),
        "ppr_gr": ranked(ppr_scores(ctx, rows_key, "gr", damping, iters),
                         100),
        "recency": [p for p, _ in sorted(ctx["recency"].items(),
                                         key=lambda kv: -kv[1])[:100]],
        "path": [p for p, _ in ctx["seed_path"][:60]],
        "explicit": ctx["explicit_paths"],
    }


def fuse_rrf(lists, k=FUSE_K):
    sc = defaultdict(float)
    for lst in lists.values():
        for r, p in enumerate(lst):
            sc[p] += 1.0 / (k + r + 1)
    return [p for p, _ in sorted(sc.items(), key=lambda kv: -kv[1])]


def fuse_scoresum(ctx, rows_key="recipe"):
    parts = []
    bm = dict(ctx["seed_bm"][:100])
    parts.append(bm)
    parts.append(ppr_scores(ctx, rows_key, "bm"))
    parts.append(ppr_scores(ctx, rows_key, "gr"))
    parts.append(dict(ctx["recency"]))
    parts.append(dict(ctx["seed_path"][:60]))
    parts.append({p: 1.0 for p in ctx["explicit_paths"]})
    sc = defaultdict(float)
    for d in parts:
        mx = max(d.values()) if d else 1.0
        for p, v in d.items():
            sc[p] += v / (mx or 1.0)
    return [p for p, _ in sorted(sc.items(), key=lambda kv: -kv[1])]


def fuse_union(ctx):
    """The pre-optimization recipe: fixed-cap union of three lists."""
    rows = ctx["rows_cfg"]["recipe"]
    hb = chrono.hybrid_rank(ctx["seed_bm"], rows, ctx["py_idx"],
                            ctx["n_py"], list(ctx["files"]), top=80)
    hg = chrono.hybrid_rank(ctx["seed_gr"], rows, ctx["py_idx"],
                            ctx["n_py"], list(ctx["files"]), top=30)
    return list(dict.fromkeys(hb + hg
                              + [p for p, _ in ctx["seed_bm"][:15]]))


# --------------------------------------------------------------- variants

def full(ctx):
    return nl.demote(fuse_rrf(source_lists(ctx)), top=DEPTH)


def drop(name):
    def f(ctx):
        ls = source_lists(ctx)
        ls.pop(name)
        return nl.demote(fuse_rrf(ls), top=DEPTH)
    return f


def rows_variant(key):
    def f(ctx):
        return nl.demote(fuse_rrf(source_lists(ctx, rows_key=key)),
                         top=DEPTH)
    return f


def prop_variant(damping=0.5, iters=10):
    def f(ctx):
        return nl.demote(fuse_rrf(source_lists(ctx, damping=damping,
                                               iters=iters)), top=DEPTH)
    return f


VARIANTS = {
    "full": full,
    # A. sources
    "no_bm25": drop("bm25"),
    "no_ppr_bm": drop("ppr_bm"),
    "no_ppr_gr": drop("ppr_gr"),
    "no_recency": drop("recency"),
    "no_path": drop("path"),
    "no_explicit": drop("explicit"),
    "no_demote": lambda c: fuse_rrf(source_lists(c))[:DEPTH],
    "no_graph": lambda c: nl.demote(fuse_rrf(
        {k: v for k, v in source_lists(c).items()
         if k not in ("ppr_bm", "ppr_gr")}), top=DEPTH),
    # B. graph layers
    "static_only": rows_variant("static"),
    "temporal_only": rows_variant("temporal"),
    "alpha50": rows_variant("a50"),
    "alpha75": rows_variant("a75"),
    # C. decay
    "decay_none": rows_variant("l0"),
    "decay_365": rows_variant("l365"),
    "decay_30": rows_variant("l30"),
    # D. propagation
    "prop_1step": prop_variant(iters=1),
    "prop_2step": prop_variant(iters=2),
    "prop_3step": prop_variant(iters=3),
    "damp_03": prop_variant(damping=0.3),
    "damp_07": prop_variant(damping=0.7),
    # E. fusion
    "fuse_scoresum": lambda c: nl.demote(fuse_scoresum(c), top=DEPTH),
    "fuse_union": lambda c: nl.demote(fuse_union(c), top=DEPTH),
    "rrf_k20": lambda c: nl.demote(fuse_rrf(source_lists(c), k=20),
                                   top=DEPTH),
    "rrf_k80": lambda c: nl.demote(fuse_rrf(source_lists(c), k=80),
                                   top=DEPTH),
}

GROUPS = [
    ("A. Candidate sources (drop one)",
     ["no_bm25", "no_ppr_bm", "no_ppr_gr", "no_recency", "no_path",
      "no_explicit", "no_demote", "no_graph"]),
    ("B. Graph layers", ["static_only", "temporal_only", "alpha50",
                         "alpha75"]),
    ("C. Temporal decay", ["decay_none", "decay_365", "decay_30"]),
    ("D. Propagation", ["prop_1step", "prop_2step", "prop_3step",
                        "damp_03", "damp_07"]),
    ("E. Fusion", ["fuse_scoresum", "fuse_union", "rrf_k20", "rrf_k80"]),
]

PRETTY = {
    "full": "Full method",
    "no_bm25": "without BM25 list",
    "no_ppr_bm": "without propagation (BM25 seed)",
    "no_ppr_gr": "without propagation (identifier seed)",
    "no_recency": "without recency prior",
    "no_path": "without path tokens",
    "no_explicit": "without paths quoted in issue",
    "no_demote": "without test/doc demotion",
    "no_graph": "without graph (both propagations)",
    "static_only": "imports only ($\\alpha{=}1$)",
    "temporal_only": "co-change only ($\\alpha{=}0$)",
    "alpha50": "$\\alpha{=}0.5$",
    "alpha75": "$\\alpha{=}0.75$",
    "decay_none": "no decay ($\\lambda{=}0$)",
    "decay_365": "$\\lambda{=}1/365$",
    "decay_30": "$\\lambda{=}1/30$",
    "prop_1step": "1 iteration",
    "prop_2step": "2 iterations",
    "prop_3step": "3 iterations",
    "damp_03": "restart $0.7$",
    "damp_07": "restart $0.3$",
    "fuse_scoresum": "score sum instead of RRF",
    "fuse_union": "fixed-cap union (earlier recipe)",
    "rrf_k20": "RRF $k{=}20$",
    "rrf_k80": "RRF $k{=}80$",
}


# --------------------------------------------------------------- run

def cmd_run(args):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTDIR / f"ablation_{args.split}.jsonl"
    done = set()
    if out_path.exists():
        for line in open(out_path, encoding="utf-8"):
            try:
                done.add(json.loads(line)["instance_id"])
            except (json.JSONDecodeError, KeyError):
                pass
    insts = [i for i in nl.load_instances(args.split)
             if i["instance_id"] not in done]
    if args.limit:
        insts = insts[:args.limit]
    log(f"ablation/{args.split}: {len(insts)} instances, "
        f"{len(VARIANTS)} variants")
    out = open(out_path, "a", encoding="utf-8")
    cur_repo, bc, t0 = None, None, time.time()
    for k, inst in enumerate(sorted(insts, key=lambda x: x["repo"])):
        try:
            repo_dir = HERE / "repos" / (inst["repo"].replace("/", "__")
                                         + ".git")
            if inst["repo"] != cur_repo:
                cur_repo = inst["repo"]
                bc = chrono.BlobCache(repo_dir)
            history = chrono.mine_history(
                repo_dir, HERE / "cache" / (inst["repo"].replace("/", "__")
                                            + "_log.pkl"))
            ctx = build(inst, repo_dir, history, bc)
            gold = set(inst["gold"])
            row = {"instance_id": inst["instance_id"], "n_gold": len(gold)}
            for name, fn in VARIANTS.items():
                cands = fn(ctx)
                row[name] = sorted(r + 1 for r, p in enumerate(cands)
                                   if p in gold)
            out.write(json.dumps(row) + "\n")
            out.flush()
            if (k + 1) % 20 == 0:
                log(f"{k + 1}/{len(insts)} "
                    f"({(time.time() - t0) / (k + 1):.1f}s/inst)")
            bc.maybe_trim()
        except Exception:
            log(f"{inst['instance_id']} ERROR "
                f"{traceback.format_exc().splitlines()[-1]}")
    out.close()
    log("ABLATION DONE")


def _metrics(rows, v):
    n = len(rows)
    ceil = a5 = a10 = 0
    for r in rows:
        g, ranks = r["n_gold"], r[v]
        ceil += len(ranks) == g
        a5 += len([x for x in ranks if x <= 5]) == g
        a10 += len([x for x in ranks if x <= 10]) == g
    return 100 * ceil / n, 100 * a5 / n, 100 * a10 / n


def _mcnemar(rows, a, b, k=5):
    def hit(r, v):
        return len([x for x in r[v] if x <= k]) == r["n_gold"]
    x = sum(hit(r, a) and not hit(r, b) for r in rows)
    y = sum(hit(r, b) and not hit(r, a) for r in rows)
    n, m = x + y, min(x, y)
    p = (min(1.0, sum(math.comb(n, j) for j in range(m + 1)) / 2 ** n * 2)
         if n else 1.0)
    return x, y, p


def cmd_analyze(args):
    rows = [json.loads(l) for l in
            open(OUTDIR / f"ablation_{args.split}.jsonl", encoding="utf-8")]
    rows = [r for r in rows if all(v in r for v in VARIANTS)]
    fc, f5, f10 = _metrics(rows, "full")
    print(f"ablation/{args.split}: n={len(rows)}")
    print(f"{'variant':34s} {'ceil@50':>8s} {'Acc@5':>7s} {'d':>6s} "
          f"{'Acc@10':>7s} {'p':>8s}")
    print(f"{'Full method':34s} {fc:7.1f}% {f5:6.1f}% {'--':>6s} "
          f"{f10:6.1f}% {'--':>8s}")
    for title, names in GROUPS:
        print(f"-- {title}")
        for v in names:
            c, a5, a10 = _metrics(rows, v)
            _, _, p = _mcnemar(rows, "full", v)
            print(f"  {PRETTY[v][:32]:32s} {c:7.1f}% {a5:6.1f}% "
                  f"{a5 - f5:+6.1f} {a10:6.1f}% {p:8.4f}")
    if args.latex:
        lines = [r"\begin{tabular}{l rrr r}", r"\toprule",
                 r"Configuration & ceil@50 & Acc@5 & $\Delta$ & $p$\\",
                 r"\midrule",
                 f"Full method & {fc:.1f} & {f5:.1f} & --- & ---\\\\"]
        for title, names in GROUPS:
            lines.append(r"\midrule")
            lines.append(r"\multicolumn{5}{l}{\emph{" + title + r"}}\\")
            for v in names:
                c, a5, _ = _metrics(rows, v)
                _, _, p = _mcnemar(rows, "full", v)
                ps = "$<$0.001" if p < 0.001 else f"{p:.3f}"
                lines.append(f"\\quad {PRETTY[v]} & {c:.1f} & {a5:.1f} & "
                             f"{a5 - f5:+.1f} & {ps}\\\\")
        lines += [r"\bottomrule", r"\end{tabular}"]
        (OUTDIR / f"ablation_{args.split}.tex").write_text(
            "\n".join(lines), encoding="utf-8")
        print(f"\nwrote {OUTDIR / f'ablation_{args.split}.tex'}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "analyze"])
    ap.add_argument("--split", default="holdout")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--latex", action="store_true")
    a = ap.parse_args()
    (cmd_run if a.cmd == "run" else cmd_analyze)(a)
