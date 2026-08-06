"""Night lab 2: multi-step rerank schemes with small models only.

Goal: close the gap to SweRank-7B (85.5 strict Acc@5 on LocBench) without
training. Schemes are multi-call compositions of one small model over the
final-recipe baskets (up to 100 candidates, official gold embedded).

Protocol: iterate on the dev half (sha1 split, as night_lab), validate the
winner once on holdout, then full set. Resumable per (scheme, instance).

Usage:
  py -3.12 night2_lab.py run --scheme cascade --model qwen/qwen3.5-9b
                             [--split dev] [--limit N] [--workers 6]
  py -3.12 night2_lab.py analyze [--split dev] [--model ...]
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
INP = HERE / "data" / "rerank_final_locbench.jsonl"
OUTDIR = HERE / "results" / "night2"
URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM = ("You are a code localization assistant. Given a GitHub issue and "
          "a list of candidate files, select the files that most likely "
          "need to be modified to resolve the issue. Answer with ONLY a "
          "JSON array of file paths from the candidate list, most likely "
          "first. No explanations.")


def split_of(iid):
    return "dev" if int(hashlib.sha1(iid.encode()).hexdigest(), 16) % 2 == 0 \
        else "holdout"


def api_key():
    k = os.environ.get("OPENROUTER_API_KEY")
    if not k:
        f = HERE / ".openrouter_key"
        if f.exists():
            k = f.read_text().strip()
    if not k:
        raise SystemExit("no OpenRouter key")
    return k


KEY = None


def call(model, user_msg, max_tokens=900, temperature=0.0):
    body = json.dumps({
        "model": model, "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": user_msg}]}).encode()
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(URL, data=body, headers={
                "Authorization": f"Bearer {KEY}",
                "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                payload = json.load(r)
            msg = payload["choices"][0]["message"]
            text = msg.get("content") or msg.get("reasoning") or ""
            return text, payload.get("usage", {}).get("total_tokens", 0)
        except Exception as e:
            last = e
            time.sleep(3 * (attempt + 1))
    raise last


def parse_list(text, allowed):
    out = []
    m = re.search(r"\[.*?\]", text, re.S)
    if m:
        try:
            arr = json.loads(m.group())
            aset = set(allowed)
            for p in arr:
                if isinstance(p, str) and p.strip() in aset \
                        and p.strip() not in out:
                    out.append(p.strip())
        except json.JSONDecodeError:
            pass
    return out


def ask_rank(model, issue, cands, top=10, note=""):
    lines = "\n".join(f"{i+1}. {p}" for i, p in enumerate(cands))
    msg = (f"## Issue\n{issue}\n\n## Candidate files\n{lines}\n\n## Task\n"
           f"{note}JSON array of up to {top} paths, most likely first.")
    text, tok = call(model, msg)
    ranked = parse_list(text, cands)
    return ranked or list(cands[:top]), tok


# ------------------------------------------------------------------ schemes

def s_base50(model, rec):
    c = [x["file"] for x in rec["hybrid_top"]][:50]
    r, t = ask_rank(model, rec["issue"], c)
    return r + [x for x in c if x not in r], 1, t


def s_base100(model, rec):
    c = [x["file"] for x in rec["hybrid_top"]][:100]
    r, t = ask_rank(model, rec["issue"], c)
    return r + [x for x in c if x not in r], 1, t


def s_cascade(model, rec):
    c = [x["file"] for x in rec["hybrid_top"]][:100]
    toks = calls = 0
    finalists = []
    for i in range(0, len(c), 25):
        chunk = c[i:i + 25]
        if not chunk:
            continue
        r, t = ask_rank(model, rec["issue"], chunk, top=8)
        toks += t
        calls += 1
        finalists.extend(r[:8])
    finalists = list(dict.fromkeys(finalists))
    r, t = ask_rank(model, rec["issue"], finalists, top=10)
    toks += t
    calls += 1
    return r + [x for x in finalists if x not in r] \
        + [x for x in c if x not in r and x not in finalists], calls, toks


def s_window(model, rec):
    c = [x["file"] for x in rec["hybrid_top"]][:100]
    toks = calls = 0
    carry = []
    segments = [c[50:100], c[20:50], c[:20]]
    for seg in segments:
        pool = list(dict.fromkeys(seg + carry))
        if not pool:
            continue
        r, t = ask_rank(model, rec["issue"], pool, top=10)
        toks += t
        calls += 1
        carry = r[:10]
    return carry + [x for x in c if x not in carry], calls, toks


def s_refine2(model, rec):
    c = [x["file"] for x in rec["hybrid_top"]][:100]
    r1, t1 = ask_rank(model, rec["issue"], c[:50])
    pool = list(dict.fromkeys(r1[:10] + c[50:90]))
    r2, t2 = ask_rank(model, rec["issue"], pool, top=10)
    final = r2 + [x for x in r1 if x not in r2]
    return final + [x for x in c if x not in final], 2, t1 + t2


def s_twopass(model, rec):
    c = [x["file"] for x in rec["hybrid_top"]][:100]
    ra, ta = ask_rank(model, rec["issue"], c[:50])
    rb, tb = (([], 0) if len(c) <= 50
              else ask_rank(model, rec["issue"], c[50:]))
    pool = list(dict.fromkeys(ra[:10] + rb[:10]))
    rc, tc = ask_rank(model, rec["issue"], pool, top=10)
    final = rc + [x for x in ra if x not in rc]
    return final + [x for x in c if x not in final], 3, ta + tb + tc


def s_anchor(model, rec):
    c = [x["file"] for x in rec["hybrid_top"]][:50]
    r1, t1 = ask_rank(model, rec["issue"], c)
    anchor = r1[0] if r1 else c[0]
    rest = [x for x in c if x != anchor]
    note = (f"The most likely file is `{anchor}`. Now select up to 6 OTHER "
            f"files that would need to change together with it for this "
            f"issue (or an empty array if the fix is single-file). ")
    r2, t2 = ask_rank(model, rec["issue"], rest, top=6, note=note)
    final = [anchor] + r2 + [x for x in r1 if x != anchor and x not in r2]
    cc = [x["file"] for x in rec["hybrid_top"]]
    return final + [x for x in cc if x not in final], 2, t1 + t2


SCHEMES = {"base50": s_base50, "base100": s_base100, "cascade": s_cascade,
           "window": s_window, "refine2": s_refine2, "twopass": s_twopass,
           "anchor": s_anchor}


# ------------------------------------------------------------------ run

def slug(model):
    return model.split("/")[-1].replace(".", "-")


def cmd_run(args):
    global KEY
    KEY = api_key()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTDIR / f"{args.scheme}_{slug(args.model)}_{args.split}.jsonl"
    done = set()
    if out_path.exists():
        for line in open(out_path, encoding="utf-8"):
            try:
                done.add(json.loads(line)["instance_id"])
            except (json.JSONDecodeError, KeyError):
                pass
    recs = [json.loads(l) for l in open(INP, encoding="utf-8")]
    recs = [r for r in recs
            if (args.split == "all" or split_of(r["instance_id"]) ==
                args.split) and r["instance_id"] not in done]
    if args.limit:
        recs = recs[:args.limit]
    print(f"{args.scheme}/{slug(args.model)}/{args.split}: {len(recs)} "
          f"instances", flush=True)
    fn = SCHEMES[args.scheme]
    out = open(out_path, "a", encoding="utf-8")
    lock = Lock()
    counter = [0]

    def work(rec):
        try:
            ranked, calls, toks = fn(args.model, rec)
            gold = set(rec["gold"])
            row = {"instance_id": rec["instance_id"], "ranked": ranked[:120],
                   "calls": calls, "tokens": toks,
                   "acc5": float(gold <= set(ranked[:5])),
                   "acc10": float(gold <= set(ranked[:10]))}
        except Exception as e:
            row = {"instance_id": rec["instance_id"], "error": str(e)[:200]}
        with lock:
            out.write(json.dumps(row) + "\n")
            out.flush()
            counter[0] += 1
            if counter[0] % 40 == 0:
                print(f"{counter[0]}/{len(recs)}", flush=True)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(work, recs))
    out.close()
    print("SCHEME DONE", flush=True)


def cmd_analyze(args):
    recs = {json.loads(l)["instance_id"]: json.loads(l)
            for l in open(INP, encoding="utf-8")}
    print(f"{'scheme':22s} {'n':>4s} {'Acc@5':>6s} {'Acc@10':>7s} "
          f"{'g=1':>6s} {'g>=2':>6s} {'calls':>6s} {'tok':>6s}")
    for f in sorted(OUTDIR.glob(f"*_{args.split}.jsonl")):
        rows = [json.loads(l) for l in open(f, encoding="utf-8")]
        ok = [r for r in rows if "acc5" in r]
        if not ok:
            continue
        n = len(ok)
        g1 = [r for r in ok if len(recs[r["instance_id"]]["gold"]) == 1]
        g2 = [r for r in ok if len(recs[r["instance_id"]]["gold"]) >= 2]
        a5 = 100 * sum(r["acc5"] for r in ok) / n
        a10 = 100 * sum(r["acc10"] for r in ok) / n
        s1 = 100 * sum(r["acc5"] for r in g1) / max(1, len(g1))
        s2 = 100 * sum(r["acc5"] for r in g2) / max(1, len(g2))
        calls = sum(r.get("calls", 1) for r in ok) / n
        tok = sum(r.get("tokens", 0) for r in ok) / n
        name = f.name.replace(f"_{args.split}.jsonl", "")
        print(f"{name:22s} {n:4d} {a5:6.1f} {a10:7.1f} {s1:6.1f} "
              f"{s2:6.1f} {calls:6.1f} {tok:6.0f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "analyze"])
    ap.add_argument("--scheme", default="base50")
    ap.add_argument("--model", default="qwen/qwen3.5-9b")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    (cmd_run if a.cmd == "run" else cmd_analyze)(a)
