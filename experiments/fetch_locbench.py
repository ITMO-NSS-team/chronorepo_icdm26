"""Download Loc-Bench V1 (560 instances) via the HF datasets-server API.

Writes the two files the rest of the pipeline expects:
  data/locbench.jsonl       -- instance metadata (id, repo, base_commit,
                               problem_statement, patch, category)
  data/edit_functions.json  -- {instance_id: ["path.py:func", ...]}, the
                               benchmark's official ground truth (files of
                               functions edited by the fix), identical to
                               what LocAgent's eval_metric.py consumes.

Usage: py -3.12 fetch_locbench.py
"""
import json
import urllib.request
from pathlib import Path

DATASET = "czlll%2FLoc-Bench_V1"
API = ("https://datasets-server.huggingface.co/rows"
       "?dataset={ds}&config=default&split=test&offset={off}&length=100")
KEEP = ["instance_id", "repo", "base_commit", "problem_statement", "patch",
        "category"]


def main():
    out_dir = Path(__file__).parent / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows, off = [], 0
    while True:
        req = urllib.request.Request(API.format(ds=DATASET, off=off),
                                     headers={"User-Agent": "chronorepo"})
        with urllib.request.urlopen(req, timeout=120) as r:
            payload = json.load(r)
        batch = payload.get("rows", [])
        if not batch:
            break
        rows.extend(item["row"] for item in batch)
        off += len(batch)
        print(f"fetched {off} rows", flush=True)
        if off >= payload.get("num_rows_total", 0):
            break

    with open(out_dir / "locbench.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({k: r[k] for k in KEEP}) + "\n")
    ef = {r["instance_id"]: list(r.get("edit_functions") or []) for r in rows}
    with open(out_dir / "edit_functions.json", "w", encoding="utf-8") as f:
        json.dump(ef, f)
    n_gold = sum(1 for v in ef.values() if v)
    print(f"wrote {len(rows)} instances -> locbench.jsonl; "
          f"{n_gold} with non-empty edit_functions -> edit_functions.json")


if __name__ == "__main__":
    main()
