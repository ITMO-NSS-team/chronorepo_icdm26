"""Download SWE-bench metadata via the HF datasets-server rows API.
Usage: py -3.12 fetch_swebench.py [lite|verified]"""
import json
import sys
import urllib.request
from pathlib import Path

DATASETS = {
    "lite": ("princeton-nlp%2FSWE-bench_Lite", "swebench_lite.jsonl"),
    "verified": ("princeton-nlp%2FSWE-bench_Verified", "swebench_verified.jsonl"),
}
API = ("https://datasets-server.huggingface.co/rows"
       "?dataset={ds}&config=default&split=test&offset={off}&length=100")
KEEP = ["instance_id", "repo", "base_commit", "problem_statement", "patch"]


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "lite"
    ds, fname = DATASETS[which]
    out = Path(__file__).parent / "data" / fname
    out.parent.mkdir(parents=True, exist_ok=True)
    rows, off = [], 0
    while True:
        req = urllib.request.Request(API.format(ds=ds, off=off),
                                     headers={"User-Agent": "chronorepo-pilot"})
        with urllib.request.urlopen(req, timeout=120) as r:
            payload = json.load(r)
        batch = payload.get("rows", [])
        if not batch:
            break
        for item in batch:
            row = item["row"]
            rows.append({k: row[k] for k in KEEP})
        off += len(batch)
        print(f"fetched {off} rows", flush=True)
        if off >= payload.get("num_rows_total", 0):
            break
    with open(out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"wrote {len(rows)} instances -> {out}")


if __name__ == "__main__":
    main()
