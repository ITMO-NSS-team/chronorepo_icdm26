"""LocBench rerank experiment: vanilla Qwen2.5-7B-Instruct via OpenRouter.

Three conditions per instance (one chat call each, no agent loop):
  bm25_plain      -- BM25 top-20 candidates, paths only
  hybrid_plain    -- ChronoRepo graph top-20, paths only
  hybrid_evidence -- ChronoRepo top-20 + evidence annotations

API key: env OPENROUTER_API_KEY, or file experiments/.openrouter_key.
Resumable; raw responses kept. Usage:
  py -3.12 run_rerank.py [--limit N] [--workers 8]
"""
import argparse
import json
import os
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock

HERE = Path(__file__).parent
INP = HERE / "data" / "rerank_input.jsonl"
OUT = HERE / "results" / "rerank_qwen7b.jsonl"
MODEL = "qwen/qwen-2.5-7b-instruct"
URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_LIST = 10

SYSTEM = ("You are a code localization assistant. Given a GitHub issue and a "
          "list of candidate files from the repository, select the files "
          "that most likely need to be modified to resolve the issue. "
          "Answer with ONLY a JSON array of up to 10 file paths from the "
          "candidate list, most likely first. No explanations.")


def api_key():
    k = os.environ.get("OPENROUTER_API_KEY")
    if not k:
        f = HERE / ".openrouter_key"
        if f.exists():
            k = f.read_text().strip()
    if not k:
        raise SystemExit("No API key: set OPENROUTER_API_KEY or create "
                         "experiments/.openrouter_key")
    return k


MAX_CANDS = 0  # 0 = use all


def build_prompt(rec, condition):
    if condition == "bm25_plain":
        cands = [{"file": p} for p in rec["bm25_top"]]
    elif condition == "hybrid_plain":
        cands = [{"file": c["file"]} for c in rec["hybrid_top"]]
    else:  # hybrid_evidence / hybrid_content: keep annotations
        cands = rec["hybrid_top"]
    if MAX_CANDS:
        cands = cands[:MAX_CANDS]
    lines = []
    for i, c in enumerate(cands, 1):
        ev = ""
        if c.get("evidence"):
            ev = f"   [{c['evidence']}]"
        elif condition == "hybrid_content" and c.get("snippet"):
            ev = f"\n   {c['snippet']}"
        lines.append(f"{i}. {c['file']}{ev}")
    return (f"## Issue\n{rec['issue']}\n\n## Candidate files\n"
            + "\n".join(lines)
            + "\n\n## Task\nJSON array of up to 10 paths, most likely first."),\
        [c["file"] for c in cands]


def call_llm(key, prompt, retries=4):
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 400,
    }).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(URL, data=body, headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                payload = json.load(r)
            return payload["choices"][0]["message"]["content"], payload.get(
                "usage", {})
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(3 * (attempt + 1))


def parse_ranking(text, candidates):
    m = re.search(r"\[.*?\]", text, re.S)
    ranked = []
    if m:
        try:
            arr = json.loads(m.group())
            cand_set = set(candidates)
            for p in arr:
                if isinstance(p, str) and p.strip() in cand_set \
                        and p.strip() not in ranked:
                    ranked.append(p.strip())
        except json.JSONDecodeError:
            pass
    if not ranked:  # fallback: keep candidate order
        ranked = list(candidates)
    return ranked


def main():
    global INP, OUT, MODEL, URL, MAX_CANDS
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--input", default=str(INP))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--url", default=URL,
                    help="OpenAI-compatible chat completions endpoint")
    ap.add_argument("--max-cands", type=int, default=0,
                    help="truncate candidate list to first N (0 = all)")
    ap.add_argument("--conditions", nargs="*",
                    default=["bm25_plain", "hybrid_plain", "hybrid_evidence"])
    args = ap.parse_args()
    INP, OUT, MODEL, URL = (Path(args.input), Path(args.out), args.model,
                            args.url)
    MAX_CANDS = args.max_cands
    key = "local" if "localhost" in URL or "127.0.0.1" in URL else api_key()

    recs = [json.loads(l) for l in open(INP, encoding="utf-8")]
    if args.limit:
        recs = recs[:args.limit]
    done = set()
    if OUT.exists():
        for line in open(OUT, encoding="utf-8"):
            try:
                r = json.loads(line)
                done.add((r["instance_id"], r["condition"]))
            except (json.JSONDecodeError, KeyError):
                pass
    jobs = [(rec, cond) for rec in recs
            for cond in args.conditions
            if (rec["instance_id"], cond) not in done]
    print(f"{len(jobs)} calls to make ({len(done)} already done)", flush=True)

    OUT.parent.mkdir(exist_ok=True)
    out = open(OUT, "a", encoding="utf-8")
    lock = Lock()
    counter = [0]

    def work(job):
        rec, cond = job
        prompt, cands = build_prompt(rec, cond)
        try:
            text, usage = call_llm(key, prompt)
            ranked = parse_ranking(text, cands)
            gold = set(rec["gold"])
            row = {
                "instance_id": rec["instance_id"], "condition": cond,
                "category": rec.get("category"),
                "ranked": ranked[:10], "raw": text[:500],
                "acc5": float(gold <= set(ranked[:5])),
                "acc10": float(gold <= set(ranked[:10])),
                "ceiling": float(gold <= set(cands)),
                "tokens": usage.get("total_tokens"),
            }
        except Exception as e:
            row = {"instance_id": rec["instance_id"], "condition": cond,
                   "error": str(e)[:300]}
        with lock:
            out.write(json.dumps(row) + "\n")
            out.flush()
            counter[0] += 1
            if counter[0] % 50 == 0:
                print(f"{counter[0]}/{len(jobs)}", flush=True)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(work, jobs))
    out.close()

    # summary
    import collections
    agg = collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0])
    for line in open(OUT, encoding="utf-8"):
        r = json.loads(line)
        if "acc5" in r:
            a = agg[r["condition"]]
            a[0] += r["acc5"]; a[1] += r["acc10"]; a[2] += r["ceiling"]
            a[3] += 1
    print("\ncondition          Acc@5   Acc@10  ceiling  n")
    for cond, (a5, a10, ce, n) in sorted(agg.items()):
        print(f"{cond:18s} {100*a5/n:5.1f}%  {100*a10/n:5.1f}%  "
              f"{100*ce/n:5.1f}%  {n}")


if __name__ == "__main__":
    main()
