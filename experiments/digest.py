"""Final digest: aggregate all experiment results with readable method names.
Writes results/digest.json used by the HTML report and the paper tables."""
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
R = HERE / "results"

# Readable names for the handful of configs that matter.
# key config -> (short name RU, short name EN)
E2_NAMED = {
    "bm25":          ("Текстовый поиск BM25", "BM25 text search"),
    "grep":          ("Поиск идентификаторов (grep)", "Identifier search (grep)"),
    "bm25_a100_l0":  ("BM25 + граф импортов", "BM25 + import graph"),
    "bm25_a000_l90": ("BM25 + граф истории", "BM25 + history graph"),
    "bm25_a025_l90": ("BM25 + оба графа", "BM25 + both graphs"),
    "grep_a025_l0":  ("Grep + оба графа", "Grep + both graphs"),
}
E3_NAMED = {
    "freq":         ("Часто меняемые файлы", "Most-changed files"),
    "rose":         ("Счётчик совместных изменений", "Co-change counts"),
    "static_ppr":   ("Распространение: импорты", "Propagation: imports"),
    "temporal_ppr": ("Распространение: история", "Propagation: history"),
    "hybrid_a25":   ("Распространение: гибрид 25/75", "Propagation: hybrid 25/75"),
    "hybrid_a50":   ("Распространение: гибрид 50/50", "Propagation: hybrid 50/50"),
}


def load(path):
    recs = []
    p = R / path
    if not p.exists():
        return recs
    for line in open(p, encoding="utf-8"):
        r = json.loads(line)
        if "error" not in r and "skip" not in r:
            recs.append(r)
    return recs


def agg_e2(recs, group_key=None):
    """mean metrics per config, optionally grouped by a record field."""
    groups = defaultdict(list)
    for r in recs:
        groups[r.get(group_key) if group_key else "all"].append(r)
    out = {}
    for g, rs in groups.items():
        cfgs = {}
        for cfg in {c for r in rs for c in r["configs"]}:
            ms = [r["configs"][cfg] for r in rs
                  if cfg in r["configs"] and r["configs"][cfg]]
            if not ms:
                continue
            cfgs[cfg] = {k: round(sum(m.get(k, 0) for m in ms) / len(ms), 4)
                         for k in ("r1", "r5", "r10", "hit5", "hit10", "ap")}
            cfgs[cfg]["n"] = len(ms)
        out[g] = cfgs
    return out


def main():
    digest = {}
    for name, path in [("lite", "results.jsonl"),
                       ("verified", "results_verified.jsonl"),
                       ("locbench", "results_locbench_gt.jsonl")]:
        recs = load(path)
        if not recs:
            continue
        d = {"n": len(recs), "all": agg_e2(recs)["all"]}
        if name == "locbench":
            d["by_category"] = agg_e2(recs, "category")
            strict = {}
            for cfg in E2_NAMED:
                ms = [r["configs"][cfg] for r in recs
                      if cfg in r["configs"] and r["configs"][cfg]]
                if ms:
                    strict[cfg] = {
                        "acc5": round(sum(m["r5"] == 1.0 for m in ms)
                                      / len(ms), 4),
                        "acc10": round(sum(m["r10"] == 1.0 for m in ms)
                                       / len(ms), 4)}
            d["strict"] = strict
        secs = [r["sec"] for r in recs if "sec" in r]
        if secs:
            secs.sort()
            d["sec_median"] = round(statistics.median(secs), 1)
            d["sec_p90"] = round(secs[int(0.9 * len(secs))], 1)
        # E1 (one record per repo, first batch wins)
        e1 = {}
        for r in recs:
            if r.get("e1") and r["repo"] not in e1:
                e1[r["repo"]] = r["e1"]
        if e1:
            d["e1"] = {repo: m for repo, m in sorted(e1.items())}
        digest[name] = d

    # E3
    e3_recs = load("e3.jsonl")
    per_cfg = defaultdict(lambda: [0.0, 0.0, 0])
    for r in e3_recs:
        for seed in r.get("seeds") or []:
            for cfg, m in seed["configs"].items():
                s = per_cfg[cfg]
                s[0] += m["r10"]
                s[1] += m["mrr"]
                s[2] += 1
    if per_cfg:
        digest["e3"] = {
            "n_commits": len([r for r in e3_recs if r.get("seeds")]),
            "configs": {c: {"r10": round(v[0] / v[2], 4),
                            "mrr": round(v[1] / v[2], 4), "n": v[2]}
                        for c, v in per_cfg.items()},
        }

    digest["names"] = {"e2": E2_NAMED, "e3": E3_NAMED}
    out = R / "digest.json"
    out.write_text(json.dumps(digest, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"wrote {out}")
    # console preview of the named E2 table
    for bench in ("lite", "verified", "locbench"):
        if bench not in digest:
            continue
        print(f"\n=== {bench} (n={digest[bench]['n']}) ===")
        for cfg, (ru, en) in E2_NAMED.items():
            m = digest[bench]["all"].get(cfg)
            if m:
                print(f"  {ru:38s} R@1={m['r1']:.3f} R@10={m['r10']:.3f} "
                      f"MAP={m['ap']:.3f}")


if __name__ == "__main__":
    main()
