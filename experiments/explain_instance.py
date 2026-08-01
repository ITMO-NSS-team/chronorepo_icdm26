"""Reconstruct and explain one instance's rankings (debug/demo helper).
Usage: py -3.12 explain_instance.py <instance_id>"""
import json
import sys
from pathlib import Path

import chrono
import run_experiments as rx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent

iid = sys.argv[1]
inst = next(json.loads(l) for l in open(HERE / "data" / "swebench_lite.jsonl",
                                        encoding="utf-8")
            if json.loads(l)["instance_id"] == iid)
repo_dir = HERE / "repos" / (inst["repo"].replace("/", "__") + ".git")
history = chrono.mine_history(
    repo_dir, HERE / "cache" / (inst["repo"].replace("/", "__") + "_log.pkl"))
gold = set(chrono.gold_files_from_patch(inst["patch"]))

print("=" * 72)
print("ISSUE", iid, "| repo:", inst["repo"])
print("-" * 72)
text = inst["problem_statement"]
print(text[:600].strip())
print("..." if len(text) > 600 else "")
print("-" * 72)
print("GOLD (файлы реального фикса):", sorted(gold))

base = inst["base_commit"]
ancestors = chrono.ancestor_set(repo_dir, base)
files = chrono.tree_at(repo_dir, base)
py_files = {p: s for p, s in files.items() if p.endswith(".py")}
base_ts = int(chrono.git(repo_dir, "show", "-s", "--format=%ct", base).strip())
bc = chrono.BlobCache(repo_dir)
bc.load_missing(files)

docs = {p: bc.tokens[s] for p, s in files.items() if s in bc.tokens}
bm25 = chrono.BM25(docs)
seed_list = bm25.query(chrono.tokenize(inst["problem_statement"], cap=3000))

print("\nBM25 top-10 (чистый текстовый поиск):")
for i, (p, s) in enumerate(seed_list[:10], 1):
    mark = "  <-- GOLD" if p in gold else ""
    print(f"  {i:2d}. {p}{mark}")

s_edges = chrono.static_edges(files, bc, repo_dir)
t_edges = chrono.temporal_edges(history, ancestors, base_ts, 1 / 90,
                                set(py_files))
py_paths = sorted(py_files)
py_idx = {p: i for i, p in enumerate(py_paths)}
n_py = len(py_paths)
rows = chrono.mix_rows(chrono.row_normalized(s_edges, py_idx),
                       chrono.row_normalized(t_edges, py_idx), 0.25, n_py)
ranked = chrono.hybrid_rank(seed_list, rows, py_idx, n_py, list(files))

print("\nГибрид top-10 (BM25-затравка + распространение по графу):")
for i, p in enumerate(ranked[:10], 1):
    mark = "  <-- GOLD" if p in gold else ""
    print(f"  {i:2d}. {p}{mark}")

# why did gold rise? show seed files connected to gold and by what edge
print("\nОткуда граф узнал ответ — связи затравки с GOLD-файлом:")
seed_top = dict(seed_list[:20])
for g in gold:
    for p, s in list(seed_top.items()):
        chips = []
        te = t_edges.get(tuple(sorted((p, g))))
        if te:
            raw = chrono.temporal_edges(history, ancestors, base_ts, 0.0,
                                        {p, g}).get(tuple(sorted((p, g))))
            chips.append(f"менялись вместе x{int(raw)} (вес с затуханием "
                         f"{te:.2f})")
        if tuple(sorted((p, g))) in s_edges:
            chips.append("связь импорта")
        if chips:
            print(f"  {p}  ->  {g}: " + "; ".join(chips))
