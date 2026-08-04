"""Gap analysis vs SweRank-7B (85.5 / 88.4 on LocBench).

A. Subgroups where our single-call configs already reach SweRank levels.
B. Offline ensembles of the nine full-run models (dev/holdout split).
C. Headroom anatomy: oracle-any-model vs ceiling vs conversion.
Pure offline: uses per-instance outputs already in the repo.
"""
import hashlib
import json
import math
import re
from collections import defaultdict
from itertools import combinations
from pathlib import Path

EXP = Path(__file__).parent
TARGET7B, TARGET32B, AGENT = 85.5, 86.6, 83.4  # SweRank-7B/-32B, LocAgent-3.5

# ---------------------------------------------------------------- load
inp = {}
for line in open(EXP / "data" / "rerank_final_locbench.jsonl", encoding="utf-8"):
    r = json.loads(line)
    inp[r["instance_id"]] = r

MODELS = {
    "qwen7b": EXP / "results" / "rerank_qwen_final_50.jsonl",
    "kimi-k2": EXP / "results" / "bakeoff" / "full_kimi-k2.jsonl",
    "glm-5.1": EXP / "results" / "bakeoff" / "full_glm-5-1.jsonl",
    "qwen3-coder": EXP / "results" / "bakeoff" / "full_qwen3-coder.jsonl",
    "ds-v4-flash": EXP / "results" / "bakeoff" / "full_ds-v4-flash.jsonl",
    "ds-v4-pro": EXP / "results" / "bakeoff" / "full_ds-v4-pro.jsonl",
    "minimax": EXP / "results" / "bakeoff" / "full_minimax-m2.7.jsonl",
    "glm-4.7": EXP / "results" / "bakeoff" / "full_glm-4.7.jsonl",
    "kimi-k3": EXP / "results" / "bakeoff" / "full_kimi-k3.jsonl",
}

rank_of = {}  # model -> iid -> backfilled ranking (list of files)
for name, path in MODELS.items():
    d = {}
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        if "ranked" not in r or r["instance_id"] not in inp:
            continue
        cands = [c["file"] for c in inp[r["instance_id"]]["hybrid_top"]][:50]
        d[r["instance_id"]] = list(r["ranked"]) + [c for c in cands
                                                   if c not in r["ranked"]]
    rank_of[name] = d

ids = sorted(set.intersection(*(set(d) for d in rank_of.values())))
gold_of = {i: set(inp[i]["gold"]) for i in ids}
cands_of = {i: [c["file"] for c in inp[i]["hybrid_top"]][:50] for i in ids}
print(f"instances with all {len(MODELS)} models: {len(ids)}")


def acc(ranking, gold, k=5):
    return gold <= set(ranking[:k])


def wilson(k, n, z=1.96):
    if not n:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * (c - h), 100 * (c + h)


hit5 = {m: {i: acc(rank_of[m][i], gold_of[i], 5) for i in ids} for m in MODELS}
hit10 = {m: {i: acc(rank_of[m][i], gold_of[i], 10) for i in ids} for m in MODELS}

# ---------------------------------------------------------------- metadata
nfiles = {}
for line in open(EXP / "results" / "results_locbench_gt.jsonl", encoding="utf-8"):
    r = json.loads(line)
    if "n_files" in r:
        nfiles[r["instance_id"]] = r["n_files"]
commits = json.loads((EXP / "data" / "repo_commit_counts.json").read_text())

PATH_RE = re.compile(r"[\w/]+\.py")


def subgroup_defs():
    g = {}
    g["all"] = ids
    for cat in {inp[i].get("category") for i in ids}:
        g[f"cat: {cat}"] = [i for i in ids if inp[i].get("category") == cat]
    g["gold=1"] = [i for i in ids if len(gold_of[i]) == 1]
    g["gold=2"] = [i for i in ids if len(gold_of[i]) == 2]
    g["gold>=3"] = [i for i in ids if len(gold_of[i]) >= 3]
    sized = sorted((i for i in ids if i in nfiles), key=lambda i: nfiles[i])
    qs = [sized[k * len(sized) // 4] for k in (1, 2, 3)]
    th = [nfiles[q] for q in qs]
    g[f"repo files<= {th[0]}"] = [i for i in sized if nfiles[i] <= th[0]]
    g[f"repo files<= {th[1]}"] = [i for i in sized
                                  if th[0] < nfiles[i] <= th[1]]
    g[f"repo files<= {th[2]}"] = [i for i in sized
                                  if th[1] < nfiles[i] <= th[2]]
    g[f"repo files>  {th[2]}"] = [i for i in sized if nfiles[i] > th[2]]
    g["issue quotes .py path"] = [i for i in ids
                                  if PATH_RE.search(inp[i]["issue"] or "")]
    g["no path in issue"] = [i for i in ids
                             if not PATH_RE.search(inp[i]["issue"] or "")]
    g["gold=1 & small repo"] = [i for i in ids if len(gold_of[i]) == 1
                                and nfiles.get(i, 9e9) <= th[1]]
    g["bug & gold=1"] = [i for i in ids
                         if inp[i].get("category") == "Bug Report"
                         and len(gold_of[i]) == 1]
    return g


print("\n=== A. Subgroups: strict Acc@5 (SweRank-7B aggregate = 85.5) ===")
show = ["kimi-k2", "glm-5.1", "qwen3-coder", "qwen7b"]
print(f"{'subgroup':26s} {'n':>4s} " + " ".join(f"{m:>12s}" for m in show))
for gname, gids in subgroup_defs().items():
    if len(gids) < 20:
        continue
    row = f"{gname:26s} {len(gids):4d} "
    for m in show:
        a = 100 * sum(hit5[m][i] for i in gids) / len(gids)
        mark = "*" if a >= TARGET7B else ("+" if a >= AGENT else " ")
        row += f"{a:11.1f}{mark}"
    print(row)
print("(* >= SweRank-7B 85.5, + >= LocAgent-Claude 83.4)")

# ---------------------------------------------------------------- B. ensembles
def split_of(iid):
    return "dev" if int(hashlib.sha1(iid.encode()).hexdigest(), 16) % 2 == 0 \
        else "holdout"


dev = [i for i in ids if split_of(i) == "dev"]
hold = [i for i in ids if split_of(i) == "holdout"]


def rrf(models, i, k=60, weights=None):
    sc = defaultdict(float)
    weights = weights or [1.0] * len(models)
    for m, w in zip(models, weights):
        for r, p in enumerate(rank_of[m][i]):
            sc[p] += w / (k + r + 1)
    return [p for p, _ in sorted(sc.items(), key=lambda kv: -kv[1])]


def vote5(models, i):
    """files scored by how many models put them top-5; tie-break best rank."""
    cnt = defaultdict(int)
    best = defaultdict(lambda: 99)
    for m in models:
        for r, p in enumerate(rank_of[m][i][:10]):
            if r < 5:
                cnt[p] += 1
            best[p] = min(best[p], r)
    return sorted(cnt, key=lambda p: (-cnt[p], best[p]))


def borda(models, i):
    sc = defaultdict(float)
    for m in models:
        n = len(rank_of[m][i])
        for r, p in enumerate(rank_of[m][i]):
            sc[p] += n - r
    return [p for p, _ in sorted(sc.items(), key=lambda kv: -kv[1])]


def eval_on(fn, gids, k=5):
    return 100 * sum(gold_of[i] <= set(fn(i)[:k]) for i in gids) / len(gids)


results = []
names = list(MODELS)
for r_size in (2, 3, 4):
    for combo in combinations(names, r_size):
        for method, fn in [("rrf", lambda i, c=combo: rrf(c, i)),
                           ("vote", lambda i, c=combo: vote5(c, i))]:
            a = eval_on(fn, dev)
            results.append((a, method, combo))
results.sort(reverse=True)
print(f"\n=== B. Ensembles: top-8 by dev Acc@5 (dev n={len(dev)}, "
      f"holdout n={len(hold)}) ===")
print(f"{'dev':>6s} {'hold':>6s} {'full':>6s} {'h@10':>6s}  method combo")
for a, method, combo in results[:8]:
    fn = (lambda i, c=combo: rrf(c, i)) if method == "rrf" \
        else (lambda i, c=combo: vote5(c, i))
    ah = eval_on(fn, hold)
    af = eval_on(fn, ids)
    ah10 = eval_on(fn, hold, k=10)
    print(f"{a:6.1f} {ah:6.1f} {af:6.1f} {ah10:6.1f}  {method} "
          f"{'+'.join(combo)}")

# best single models for reference
print("\nsingles (full-set Acc@5/@10):")
for m in names:
    a5 = 100 * sum(hit5[m][i] for i in ids) / len(ids)
    a10 = 100 * sum(hit10[m][i] for i in ids) / len(ids)
    print(f"  {m:12s} {a5:5.1f} {a10:5.1f}")

# ---------------------------------------------------------------- C. headroom
oracle_any = 100 * sum(any(hit5[m][i] for m in names) for i in ids) / len(ids)
oracle_top2 = 100 * sum(hit5["kimi-k2"][i] or hit5["glm-5.1"][i]
                        for i in ids) / len(ids)
ceil50 = 100 * sum(gold_of[i] <= set(cands_of[i]) for i in ids) / len(ids)
all_fail_conv = [i for i in ids if gold_of[i] <= set(cands_of[i])
                 and not any(hit5[m][i] for m in names)]
basket_miss = [i for i in ids if not (gold_of[i] <= set(cands_of[i]))]
print(f"\n=== C. Headroom anatomy (n={len(ids)}) ===")
print(f"ceiling@50 (all gold in basket): {ceil50:.1f}")
print(f"oracle any-of-9 models Acc@5:    {oracle_any:.1f}")
print(f"oracle Kimi-or-GLM Acc@5:        {oracle_top2:.1f}")
print(f"convertible but missed by ALL 9: {len(all_fail_conv)} instances")
print(f"basket misses (ceiling fail):    {len(basket_miss)} instances")
mg = defaultdict(int)
for i in all_fail_conv:
    mg[min(3, len(gold_of[i]))] += 1
print(f"  all-9-missed by gold count 1/2/3+: {mg[1]}/{mg[2]}/{mg[3]}")
bg = defaultdict(int)
for i in basket_miss:
    bg[min(3, len(gold_of[i]))] += 1
print(f"  basket-miss by gold count 1/2/3+:  {bg[1]}/{bg[2]}/{bg[3]}")
