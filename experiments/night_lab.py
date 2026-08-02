"""Overnight lab: iterate on candidate-set construction, measure ceilings.

Protocol: LocBench split by instance-id hash into DEV (iterate) and HOLDOOUT
(final validation only). Official edit_functions ground truth. Expensive raw
materials are built once per instance; every registered variant recombines
them cheaply, so one sweep evaluates all variants of the night's batch.

Usage:
  py -3.12 night_lab.py run --sweep sweep1 --split dev [--limit N]
  py -3.12 night_lab.py analyze --sweep sweep1 --split dev
"""
import argparse
import hashlib
import json
import math
import re
import time
import traceback
from collections import Counter, defaultdict
from pathlib import Path

import chrono

HERE = Path(__file__).parent
NIGHT = HERE / "results" / "night"
LAM = 1 / 90
TOP = 100

_PATH_RE = re.compile(r"[\w./-]+?([\w-]+/)*[\w-]+\.py")


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def split_of(iid):
    return "dev" if int(hashlib.sha1(iid.encode()).hexdigest(), 16) % 2 == 0 \
        else "holdout"


# ------------------------------------------------------------------ context

def build_context(inst, repo_dir, history, bc):
    ctx = {}
    base = inst["base_commit"]
    ancestors = chrono.ancestor_set(repo_dir, base)
    files = chrono.tree_at(repo_dir, base)
    py_files = {p: s for p, s in files.items() if p.endswith(".py")}
    base_ts = int(chrono.git(repo_dir, "show", "-s", "--format=%ct",
                             base).strip())
    bc.load_missing(files)
    docs = {p: bc.tokens[s] for p, s in files.items() if s in bc.tokens}
    bm25 = chrono.BM25(docs)
    issue = inst["problem_statement"]
    seed_bm = bm25.query(chrono.tokenize(issue, cap=3000), top=200)
    idents = chrono.issue_identifiers(issue)
    seed_gr = chrono.grep_scores(idents, files, bc, top=200)

    # explicit paths quoted in the issue (tracebacks, prose)
    explicit = []
    seen = set()
    for m in _PATH_RE.finditer(issue[:6000]):
        cand = m.group(0).lstrip("./")
        for p in files:
            if (p == cand or p.endswith("/" + cand)) and p not in seen:
                explicit.append(p)
                seen.add(p)
    ctx["explicit_paths"] = explicit[:10]

    # path-token BM25: score files by issue tokens hitting their path
    q_toks = set(chrono.tokenize(issue, cap=1500))
    path_scores = []
    for p in files:
        toks = set(chrono.subtokens(p.replace("/", "_").replace(".", "_")))
        inter = len(q_toks & toks)
        if inter:
            path_scores.append((p, inter / (1 + math.log(1 + len(toks)))))
    ctx["seed_path"] = sorted(path_scores, key=lambda kv: -kv[1])[:60]

    # RM3-style expansion: top tokens of top-5 BM25 docs added to the query
    exp = Counter()
    for p, _ in seed_bm[:5]:
        s = files.get(p)
        if s and s in bc.tokens:
            exp.update(dict(bc.tokens[s].most_common(30)))
    exp_query = chrono.tokenize(issue, cap=3000) + \
        [t for t, _ in exp.most_common(25)]
    ctx["seed_rm3"] = bm25.query(exp_query, top=200)

    # recency prior: decayed change count per file
    rec = defaultdict(float)
    freq = Counter()
    for sha, ts, fs in history:
        if sha not in ancestors:
            continue
        w = math.exp(-LAM * max(0.0, (base_ts - ts) / 86400.0))
        for f in fs:
            if f in files:
                rec[f] += w
                freq[f] += 1
    ctx["recency"] = rec
    ctx["freq"] = freq

    s_edges = chrono.static_edges(files, bc, repo_dir)
    t_dec = chrono.temporal_edges(history, ancestors, base_ts, LAM,
                                  set(py_files))
    t_raw = chrono.temporal_edges(history, ancestors, base_ts, 0.0,
                                  set(py_files))
    all_set = set(files)
    t_all = chrono.temporal_edges(history, ancestors, base_ts, LAM, all_set)

    py_paths = sorted(py_files)
    py_idx = {p: i for i, p in enumerate(py_paths)}
    all_paths = sorted(files)
    all_idx = {p: i for i, p in enumerate(all_paths)}

    conf = {}
    for (a, b), w in t_dec.items():
        conf[(a, b)] = w / math.sqrt((1 + freq[a]) * (1 + freq[b]))

    dir_edges = {}
    by_dir = defaultdict(list)
    for p in py_paths:
        by_dir[p.rsplit("/", 1)[0]].append(p)
    for d, members in by_dir.items():
        if 2 <= len(members) <= 40:
            for i in range(len(members) - 1):
                dir_edges[(members[i], members[i + 1])] = 1.0

    ctx.update({
        "history": history, "ancestors": ancestors, "base_ts": base_ts,
        "py_set": set(py_files),
        "files": files, "py_idx": py_idx, "n_py": len(py_paths),
        "all_idx": all_idx, "n_all": len(all_paths),
        "all_paths_list": list(files), "bm25": bm25,
        "seed_bm": seed_bm, "seed_gr": seed_gr,
        "rows_s": chrono.row_normalized(s_edges, py_idx),
        "rows_t": chrono.row_normalized(t_dec, py_idx),
        "rows_conf": chrono.row_normalized(conf, py_idx),
        "rows_all_t": chrono.row_normalized(t_all, all_idx),
        "rows_dir": chrono.row_normalized(dir_edges, py_idx),
    })
    return ctx


# ------------------------------------------------------------------ helpers

def hybrid(ctx, seed_list, rows, beta=0.5, top=TOP, idx_key="py_idx",
           n_key="n_py"):
    return chrono.hybrid_rank(seed_list, rows, ctx[idx_key], ctx[n_key],
                              ctx["all_paths_list"], beta=beta, top=top)


def mix(ctx, alpha, extra=None):
    rows = chrono.mix_rows(ctx["rows_s"], ctx["rows_t"], alpha, ctx["n_py"])
    if extra:
        merged = {}
        for i in range(ctx["n_py"]):
            acc = defaultdict(float)
            for j, w in rows.get(i, ()):
                acc[j] += 0.9 * w
            for j, w in extra.get(i, ()):
                acc[j] += 0.1 * w
            if acc:
                merged[i] = list(acc.items())
        return merged
    return rows


def union(*ranked_lists, caps, top=TOP):
    out = []
    for lst, cap in zip(ranked_lists, caps):
        out.extend(lst[:cap])
    return list(dict.fromkeys(out))[:top]


def rrf(lists, k=60, top=TOP):
    score = defaultdict(float)
    for lst in lists:
        for r, p in enumerate(lst):
            score[p] += 1.0 / (k + r + 1)
    return [p for p, _ in sorted(score.items(), key=lambda kv: -kv[1])[:top]]


def baseline(ctx):
    rows = mix(ctx, 0.25)
    hb = hybrid(ctx, ctx["seed_bm"], rows, top=80)
    hg = hybrid(ctx, ctx["seed_gr"], rows, top=30)
    return union(hb, hg, [p for p, _ in ctx["seed_bm"]],
                 caps=(80, 30, 15))


# ------------------------------------------------------------------ variants

def v_baseline(ctx):
    return baseline(ctx)


def v_paths(ctx):
    return list(dict.fromkeys(ctx["explicit_paths"] + baseline(ctx)))[:TOP]


def v_rm3(ctx):
    rows = mix(ctx, 0.25)
    hb = hybrid(ctx, ctx["seed_rm3"], rows, top=80)
    hg = hybrid(ctx, ctx["seed_gr"], rows, top=30)
    return union(hb, hg, [p for p, _ in ctx["seed_rm3"]], caps=(80, 30, 15))


def v_pathbm(ctx):
    rows = mix(ctx, 0.25)
    hb = hybrid(ctx, ctx["seed_bm"], rows, top=70)
    hg = hybrid(ctx, ctx["seed_gr"], rows, top=25)
    return union(hb, hg, [p for p, _ in ctx["seed_path"]],
                 [p for p, _ in ctx["seed_bm"]], caps=(70, 25, 15, 10))


def v_recency(ctx):
    base = baseline(ctx)
    rec = ctx["recency"]
    mx = max(rec.values()) if rec else 1.0
    scored = [(p, (TOP - r) / TOP + 0.3 * rec.get(p, 0) / mx)
              for r, p in enumerate(base)]
    return [p for p, _ in sorted(scored, key=lambda kv: -kv[1])]


def v_conf(ctx):
    rows = chrono.mix_rows(ctx["rows_s"], ctx["rows_conf"], 0.25,
                           ctx["n_py"])
    hb = hybrid(ctx, ctx["seed_bm"], rows, top=80)
    hg = hybrid(ctx, ctx["seed_gr"], rows, top=30)
    return union(hb, hg, [p for p, _ in ctx["seed_bm"]], caps=(80, 30, 15))


def v_allfiles(ctx):
    hb = hybrid(ctx, ctx["seed_bm"], ctx["rows_all_t"], top=80,
                idx_key="all_idx", n_key="n_all")
    hg = hybrid(ctx, ctx["seed_gr"], ctx["rows_all_t"], top=30,
                idx_key="all_idx", n_key="n_all")
    return union(hb, hg, [p for p, _ in ctx["seed_bm"]], caps=(80, 30, 15))


def v_dirsmooth(ctx):
    rows = mix(ctx, 0.25, extra=ctx["rows_dir"])
    hb = hybrid(ctx, ctx["seed_bm"], rows, top=80)
    hg = hybrid(ctx, ctx["seed_gr"], rows, top=30)
    return union(hb, hg, [p for p, _ in ctx["seed_bm"]], caps=(80, 30, 15))


def v_rrf(ctx):
    rows = mix(ctx, 0.25)
    lists = [
        [p for p, _ in ctx["seed_bm"][:100]],
        [p for p, _ in ctx["seed_gr"][:100]],
        hybrid(ctx, ctx["seed_bm"], rows, top=100),
        hybrid(ctx, ctx["seed_gr"], rows, top=100),
        [p for p, _ in sorted(ctx["recency"].items(),
                              key=lambda kv: -kv[1])[:100]],
    ]
    return rrf(lists)


def v_demote_tests(ctx):
    base = baseline(ctx)
    core = [p for p in base if "test" not in p and not p.startswith("doc")]
    rest = [p for p in base if p not in core]
    return (core + rest)[:TOP]


def v_3step(ctx):
    rows = mix(ctx, 0.25)
    seed_list = ctx["seed_bm"]
    seed_vec = [0.0] * ctx["n_py"]
    tot = sum(s for _, s in seed_list[:20]) or 1.0
    for p, s in seed_list[:20]:
        i = ctx["py_idx"].get(p)
        if i is not None:
            seed_vec[i] += s / tot
    pv = chrono.ppr(rows, seed_vec, ctx["n_py"], damping=0.6, iters=3)
    pmax = max(pv) or 1.0
    smax = (seed_list[0][1] if seed_list else 1.0) or 1.0
    sd = dict(seed_list)
    final = {}
    for p in ctx["all_paths_list"]:
        sc = 0.5 * sd.get(p, 0.0) / smax
        i = ctx["py_idx"].get(p)
        if i is not None:
            sc += 0.5 * pv[i] / pmax
        if sc > 0:
            final[p] = sc
    ranked = [p for p, _ in sorted(final.items(), key=lambda kv: -kv[1])]
    hg = hybrid(ctx, ctx["seed_gr"], rows, top=30)
    return union(ranked, hg, [p for p, _ in seed_list], caps=(80, 30, 15))


def demote(cands, top=TOP):
    core = [p for p in cands if "test" not in p.lower()
            and not p.split("/")[0].startswith("doc")]
    rest = [p for p in cands if p not in core]
    return (core + rest)[:top]


def rrf7(ctx, k=60, weights=None):
    rows = mix(ctx, 0.25)
    lists = [
        [p for p, _ in ctx["seed_bm"][:100]],
        [p for p, _ in ctx["seed_gr"][:100]],
        hybrid(ctx, ctx["seed_bm"], rows, top=100),
        hybrid(ctx, ctx["seed_gr"], rows, top=100),
        [p for p, _ in sorted(ctx["recency"].items(),
                              key=lambda kv: -kv[1])[:100]],
        [p for p, _ in ctx["seed_path"][:60]],
        ctx["explicit_paths"],
    ]
    weights = weights or [1] * len(lists)
    score = defaultdict(float)
    for lst, w in zip(lists, weights):
        for r, p in enumerate(lst):
            score[p] += w / (k + r + 1)
    return [p for p, _ in sorted(score.items(), key=lambda kv: -kv[1])[:TOP]]


def s2_rrf_dem(ctx):
    return demote(v_rrf(ctx))


def s2_rrf7(ctx):
    return rrf7(ctx)


def s2_rrf7_dem(ctx):
    return demote(rrf7(ctx))


def s2_rrf7_dem_k30(ctx):
    return demote(rrf7(ctx, k=30))


def s2_rrf7w_dem(ctx):
    return demote(rrf7(ctx, weights=[1.5, 1, 2, 2, 1, 1, 3]))


def s2_rrf7_dem_rec(ctx):
    cands = demote(rrf7(ctx))
    rec = ctx["recency"]
    mx = max(rec.values()) if rec else 1.0
    scored = [(p, (TOP - r) / TOP + 0.25 * rec.get(p, 0) / mx)
              for r, p in enumerate(cands)]
    return [p for p, _ in sorted(scored, key=lambda kv: -kv[1])]


def s2_paths_first(ctx):
    return list(dict.fromkeys(
        ctx["explicit_paths"] + demote(rrf7(ctx))))[:TOP]


def _pr_transactions(ctx_history, ancestors, base_ts, file_set,
                     window=3600):
    """Merge consecutive commits by the same author within a time window
    into one transaction before pair counting (approximates PR grouping).
    History entries lack author, so approximate by time adjacency alone."""
    txs, cur, last_ts = [], set(), None
    for sha, ts, fs in sorted(ctx_history, key=lambda x: x[1]):
        if sha not in ancestors:
            continue
        alive = [f for f in fs if f in file_set]
        if not alive:
            continue
        if last_ts is not None and ts - last_ts > window:
            if 2 <= len(cur) <= 30:
                txs.append((last_ts, sorted(cur)))
            cur = set()
        cur.update(alive)
        last_ts = ts
    if last_ts is not None and 2 <= len(cur) <= 30:
        txs.append((last_ts, sorted(cur)))
    edges = defaultdict(float)
    for ts, fs in txs:
        w = math.exp(-LAM * max(0.0, (base_ts - ts) / 86400.0))
        for i in range(len(fs)):
            for j in range(i + 1, len(fs)):
                edges[(fs[i], fs[j])] += w
    return edges


def rrf7x(ctx, k=60, depth=100, exclude=(), pr_tx=False):
    rows = mix(ctx, 0.25)
    if pr_tx:
        tx = _pr_transactions(ctx["history"], ctx["ancestors"],
                              ctx["base_ts"], ctx["py_set"])
        rows = chrono.mix_rows(ctx["rows_s"],
                               chrono.row_normalized(tx, ctx["py_idx"]),
                               0.25, ctx["n_py"])
    lists = [
        ("bm", [p for p, _ in ctx["seed_bm"][:depth]]),
        ("gr", [p for p, _ in ctx["seed_gr"][:depth]]),
        ("ppr_bm", hybrid(ctx, ctx["seed_bm"], rows, top=depth)),
        ("ppr_gr", hybrid(ctx, ctx["seed_gr"], rows, top=depth)),
        ("rec", [p for p, _ in sorted(ctx["recency"].items(),
                                      key=lambda kv: -kv[1])[:depth]]),
        ("path", [p for p, _ in ctx["seed_path"][:60]]),
        ("expl", ctx["explicit_paths"]),
    ]
    score = defaultdict(float)
    for name, lst in lists:
        if name in exclude:
            continue
        for r, p in enumerate(lst):
            score[p] += 1.0 / (k + r + 1)
    return [p for p, _ in sorted(score.items(), key=lambda kv: -kv[1])[:TOP]]


def demote_dirs(cands, top=TOP):
    def is_aux(p):
        segs = p.lower().split("/")
        return any(s in ("tests", "test", "docs", "doc", "examples",
                         "benchmarks") for s in segs[:-1]) or \
            segs[-1].startswith("test_") or segs[-1].endswith("_test.py")
    core = [p for p in cands if not is_aux(p)]
    rest = [p for p in cands if p not in core]
    return (core + rest)[:top]


def make_drop(name):
    def f(ctx):
        return demote(rrf7x(ctx, exclude=(name,)))
    return f


SWEEPS3 = {"winner": lambda ctx: demote(rrf7x(ctx)),
           "win_dirdem": lambda ctx: demote_dirs(rrf7x(ctx)),
           "win_prtx": lambda ctx: demote(rrf7x(ctx, pr_tx=True)),
           "win_d150": lambda ctx: demote(rrf7x(ctx, depth=150)),
           "win_k20": lambda ctx: demote(rrf7x(ctx, k=20)),
           "win_k90": lambda ctx: demote(rrf7x(ctx, k=90))}
for _n in ("bm", "gr", "ppr_bm", "ppr_gr", "rec", "path", "expl"):
    SWEEPS3[f"drop_{_n}"] = make_drop(_n)


def rrf_final(ctx, k=60, exclude=("gr",), rec_depth=100, path_depth=60,
              rec_w=1.0, div_cap=0):
    rows = mix(ctx, 0.25)
    lists = [
        ("bm", 1.0, [p for p, _ in ctx["seed_bm"][:100]]),
        ("gr", 1.0, [p for p, _ in ctx["seed_gr"][:100]]),
        ("ppr_bm", 1.0, hybrid(ctx, ctx["seed_bm"], rows, top=100)),
        ("ppr_gr", 1.0, hybrid(ctx, ctx["seed_gr"], rows, top=100)),
        ("rec", rec_w, [p for p, _ in sorted(ctx["recency"].items(),
                        key=lambda kv: -kv[1])[:rec_depth]]),
        ("path", 1.0, [p for p, _ in ctx["seed_path"][:path_depth]]),
        ("expl", 1.0, ctx["explicit_paths"]),
    ]
    score = defaultdict(float)
    for name, w, lst in lists:
        if name in exclude:
            continue
        for r, p in enumerate(lst):
            score[p] += w / (k + r + 1)
    ranked = [p for p, _ in sorted(score.items(), key=lambda kv: -kv[1])]
    if div_cap:
        seen_dir, out, spill = defaultdict(int), [], []
        for p in ranked:
            d = p.rsplit("/", 1)[0]
            (out if seen_dir[d] < div_cap else spill).append(p)
            seen_dir[d] += 1
        ranked = out + spill
    return demote(ranked[:TOP * 2])[:TOP]


SWEEPS4 = {
    "winner3": lambda c: demote(rrf7x(c)),
    "no_gr": lambda c: rrf_final(c, exclude=("gr",)),
    "no_gr2": lambda c: rrf_final(c, exclude=("gr", "ppr_gr")),
    "no_gr_k20": lambda c: rrf_final(c, k=20, exclude=("gr",)),
    "no_gr2_k20": lambda c: rrf_final(c, k=20, exclude=("gr", "ppr_gr")),
    "no_gr_k40": lambda c: rrf_final(c, k=40, exclude=("gr",)),
    "rec_deep": lambda c: rrf_final(c, rec_depth=150),
    "path_deep": lambda c: rrf_final(c, path_depth=100),
    "rec_w2": lambda c: rrf_final(c, rec_w=2.0),
    "divers12": lambda c: rrf_final(c, div_cap=12),
}


SWEEPS_FINAL = {
    "baseline": v_baseline,
    "winner3": lambda c: demote(rrf7x(c)),
    "final_k40": lambda c: rrf_final(c, k=40, exclude=("gr",)),
    "final_k20": lambda c: rrf_final(c, k=20, exclude=("gr",)),
}


SWEEPS = {
    "final": SWEEPS_FINAL,
    "sweep4": SWEEPS4,
    "sweep3": SWEEPS3,
    "sweep2": {
        "baseline": v_baseline, "demote_tests": v_demote_tests,
        "rrf_dem": s2_rrf_dem, "rrf7": s2_rrf7, "rrf7_dem": s2_rrf7_dem,
        "rrf7_dem_k30": s2_rrf7_dem_k30, "rrf7w_dem": s2_rrf7w_dem,
        "rrf7_dem_rec": s2_rrf7_dem_rec, "paths_first": s2_paths_first,
    },
    "sweep1": {
        "baseline": v_baseline, "paths": v_paths, "rm3": v_rm3,
        "pathbm": v_pathbm, "recency": v_recency, "conf": v_conf,
        "allfiles": v_allfiles, "dirsmooth": v_dirsmooth, "rrf": v_rrf,
        "demote_tests": v_demote_tests, "threestep": v_3step,
    },
}


# ------------------------------------------------------------------ run

def load_instances(split, bench="locbench"):
    insts = []
    if bench == "locbench":
        ef = json.loads((HERE / "data" / "edit_functions.json").read_text())
        gold_of = {k: sorted({e.split(":")[0] for e in v})
                   for k, v in ef.items() if v}
        for line in open(HERE / "data" / "locbench.jsonl",
                         encoding="utf-8"):
            r = json.loads(line)
            iid = r["instance_id"]
            if iid in gold_of and (split == "all"
                                   or split_of(iid) == split):
                r["gold"] = gold_of[iid]
                insts.append(r)
    else:
        fname = ("swebench_lite.jsonl" if bench == "lite"
                 else "swebench_verified.jsonl")
        for line in open(HERE / "data" / fname, encoding="utf-8"):
            r = json.loads(line)
            r["gold"] = chrono.gold_files_from_patch(r["patch"])
            if r["gold"]:
                insts.append(r)
    return insts


def cmd_run(args):
    NIGHT.mkdir(parents=True, exist_ok=True)
    tag = args.split if args.bench == "locbench" else args.bench
    out_path = NIGHT / f"{args.sweep}_{tag}.jsonl"
    done = set()
    if out_path.exists():
        for line in open(out_path, encoding="utf-8"):
            try:
                done.add(json.loads(line)["instance_id"])
            except (json.JSONDecodeError, KeyError):
                pass
    variants = SWEEPS[args.sweep]
    insts = [i for i in load_instances(args.split, args.bench)
             if i["instance_id"] not in done]
    if args.limit:
        insts = insts[:args.limit]
    log(f"{args.sweep}/{args.split}: {len(insts)} instances, "
        f"{len(variants)} variants")
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
            ctx = build_context(inst, repo_dir, history, bc)
            gold = set(inst["gold"])
            row = {"instance_id": inst["instance_id"], "n_gold": len(gold)}
            for name, fn in variants.items():
                cands = fn(ctx)
                row[name] = {
                    "ranks": sorted(r + 1 for r, p in enumerate(cands)
                                    if p in gold),
                    "n": len(cands)}
            out.write(json.dumps(row) + "\n")
            out.flush()
            if (k + 1) % 25 == 0:
                log(f"{k + 1}/{len(insts)} "
                    f"({(time.time() - t0) / (k + 1):.1f}s/inst)")
            bc.maybe_trim()
        except Exception:
            log(f"{inst['instance_id']} ERROR "
                f"{traceback.format_exc().splitlines()[-1]}")
    out.close()
    log("SWEEP DONE")


def cmd_analyze(args):
    tag = args.split if args.bench == "locbench" else args.bench
    out_path = NIGHT / f"{args.sweep}_{tag}.jsonl"
    rows = [json.loads(l) for l in open(out_path, encoding="utf-8")]
    variants = [k for k in rows[0] if k not in ("instance_id", "n_gold")]
    print(f"{args.sweep}/{args.split}: n={len(rows)}")
    print(f"{'variant':14s} {'ceil@50':>8s} {'ceil@100':>9s} "
          f"{'acc@5':>7s} {'acc@10':>7s} {'pfile@50':>9s}")
    res = []
    for v in variants:
        c50 = c100 = a5 = a10 = pf = pt = 0
        for r in rows:
            g = r["n_gold"]
            ranks = r[v]["ranks"]
            c50 += len([x for x in ranks if x <= 50]) == g
            c100 += len(ranks) == g
            a5 += len([x for x in ranks if x <= 5]) == g
            a10 += len([x for x in ranks if x <= 10]) == g
            pf += len([x for x in ranks if x <= 50])
            pt += g
        n = len(rows)
        res.append((v, c50 / n, c100 / n, a5 / n, a10 / n, pf / pt))
    for v, c50, c100, a5, a10, pfr in sorted(res, key=lambda t: -t[2]):
        print(f"{v:14s} {100*c50:7.1f}% {100*c100:8.1f}% {100*a5:6.1f}% "
              f"{100*a10:6.1f}% {100*pfr:8.1f}%")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "analyze"])
    ap.add_argument("--sweep", default="sweep1")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--bench", default="locbench",
                    choices=["locbench", "lite", "verified"])
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    (cmd_run if a.cmd == "run" else cmd_analyze)(a)
