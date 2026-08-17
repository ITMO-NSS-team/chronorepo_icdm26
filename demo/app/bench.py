"""Benchmark material: real issues with gold files, and the paper's tables.

Issues come from data/swebench_lite.jsonl (gold = files touched by the
reference patch, via chrono.gold_files_from_patch). The recorded runs
(data/rerank_final_lite.jsonl, results/rerank_qwen_final_lite.jsonl) are used
for two things: the offline/booth answer, and a cross-check that what the
live engine produces now matches what was measured then.
"""
import json
from functools import lru_cache

import chrono

from .config import DATA, DEMO, RESULTS

FEATURED = [
    "django__django-11964",      # gold 23 -> 1 after the single call
    "mwaskom__seaborn-3010",     # small repo, fast to index live
    "sphinx-doc__sphinx-8595",
    "astropy__astropy-14182",
    "psf__requests-2317",
    "pallets__flask-4045",
]


def _read_jsonl(path):
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return out


@lru_cache(maxsize=1)
def _lite():
    rows = {}
    for r in _read_jsonl(DATA / "swebench_lite.jsonl"):
        r["gold"] = chrono.gold_files_from_patch(r.get("patch", ""))
        rows[r["instance_id"]] = r
    return rows


@lru_cache(maxsize=1)
def _baskets():
    return {r["instance_id"]: [c["file"] for c in r.get("hybrid_top", [])]
            for r in _read_jsonl(DATA / "rerank_final_lite.jsonl")}


@lru_cache(maxsize=1)
def _recorded_rerank():
    out = {}
    for r in _read_jsonl(RESULTS / "rerank_qwen_final_lite.jsonl"):
        if "ranked" in r:
            out[r["instance_id"]] = r["ranked"]
    return out


def instances(repo=None, limit=200):
    lite, baskets = _lite(), _baskets()
    out = []
    for iid, r in lite.items():
        if iid not in baskets or not r["gold"]:
            continue
        if repo and r["repo"] != repo:
            continue
        text = r["problem_statement"].strip()
        out.append({
            "id": iid,
            "repo": r["repo"],
            "base_commit": r["base_commit"],
            "title": text.splitlines()[0][:110] if text else iid,
            "gold": r["gold"],
            "featured": iid in FEATURED,
            "n_recorded_candidates": len(baskets[iid]),
        })
    out.sort(key=lambda x: (not x["featured"], x["repo"], x["id"]))
    return out[:limit]


def instance(iid):
    r = _lite().get(iid)
    if not r:
        return None
    basket = _baskets().get(iid, [])
    recorded = _recorded_rerank().get(iid, [])
    final = list(recorded) + [p for p in basket if p not in recorded]
    return {
        "id": iid,
        "repo": r["repo"],
        "base_commit": r["base_commit"],
        "issue": r["problem_statement"],
        "gold": r["gold"],
        "recorded": {
            "candidates": basket,
            "final": final,
            "gold_rank_candidates": [i + 1 for i, p in enumerate(basket)
                                     if p in r["gold"]],
            "gold_rank_final": [i + 1 for i, p in enumerate(final)
                                if p in r["gold"]],
            "model": "qwen/qwen-2.5-7b-instruct",
        } if basket else None,
    }


@lru_cache(maxsize=1)
def leaderboard():
    p = DEMO / "data" / "leaderboard.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
