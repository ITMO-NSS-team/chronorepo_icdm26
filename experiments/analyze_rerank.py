"""Final analysis of the Qwen-7B rerank experiment (E4).

Backfilled strict Acc@k, no-LLM baselines on the identical instance set,
Wilson 95% CIs, exact McNemar tests between key pairs, per-category table.
Writes results/summary_rerank.md."""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
R = HERE / "results"


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def mcnemar(a_wins, b_wins):
    """Exact two-sided McNemar on discordant pairs."""
    b, c = a_wins, b_wins
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n * 2
    return min(1.0, p)


def main():
    inp = {json.loads(l)["instance_id"]: json.loads(l)
           for l in open(HERE / "data" / "rerank_input.jsonl",
                         encoding="utf-8")}
    llm = defaultdict(dict)   # instance -> condition -> acc5/acc10
    for line in open(R / "rerank_qwen7b.jsonl", encoding="utf-8"):
        r = json.loads(line)
        if "acc5" not in r:
            continue
        rec = inp[r["instance_id"]]
        cands = (rec["bm25_top"] if r["condition"] == "bm25_plain"
                 else [c["file"] for c in rec["hybrid_top"]])
        ranked = list(r["ranked"]) + [c for c in cands
                                      if c not in r["ranked"]]
        gold = set(rec["gold"])
        llm[r["instance_id"]][r["condition"]] = {
            "acc5": gold <= set(ranked[:5]),
            "acc10": gold <= set(ranked[:10])}

    base = defaultdict(dict)  # instance -> method -> acc5/acc10
    for line in open(R / "results_locbench.jsonl", encoding="utf-8"):
        r = json.loads(line)
        if r.get("instance_id") not in llm or "configs" not in r:
            continue
        for cfg, tag in (("bm25", "bm25_nollm"),
                         ("bm25_a025_l90", "graph_nollm")):
            m = r["configs"].get(cfg)
            if m:
                base[r["instance_id"]][tag] = {
                    "acc5": m["r5"] == 1.0, "acc10": m["r10"] == 1.0}

    ids = [i for i in llm if len(llm[i]) == 3 and len(base[i]) == 2]
    methods = ["bm25_nollm", "graph_nollm", "bm25_plain", "hybrid_plain",
               "hybrid_evidence"]
    names = {
        "bm25_nollm": "BM25, без LLM",
        "graph_nollm": "Граф, без LLM",
        "bm25_plain": "Qwen-7B на кандидатах BM25",
        "hybrid_plain": "Qwen-7B на кандидатах графа",
        "hybrid_evidence": "Qwen-7B на кандидатах графа + доказательства",
    }

    def acc_of(i, m):
        return (base[i] if m.endswith("nollm") else llm[i])[m]

    lines = [f"# E4 · Qwen-7B rerank — итог (n={len(ids)}, метрика строгая, "
             "с дозаполнением)", "",
             "| метод | Acc@5 | 95% ДИ | Acc@10 |", "|---|---|---|---|"]
    for m in methods:
        k5 = sum(acc_of(i, m)["acc5"] for i in ids)
        k10 = sum(acc_of(i, m)["acc10"] for i in ids)
        lo, hi = wilson(k5, len(ids))
        lines.append(f"| {names[m]} | {100*k5/len(ids):.1f}% "
                     f"| [{100*lo:.1f}, {100*hi:.1f}] "
                     f"| {100*k10/len(ids):.1f}% |")

    lines += ["", "## Тесты Мак-Немара (Acc@5, точные, двусторонние)", ""]
    pairs = [("hybrid_evidence", "bm25_plain"),
             ("hybrid_evidence", "hybrid_plain"),
             ("hybrid_evidence", "graph_nollm"),
             ("graph_nollm", "bm25_nollm")]
    for a, b in pairs:
        aw = sum(acc_of(i, a)["acc5"] and not acc_of(i, b)["acc5"]
                 for i in ids)
        bw = sum(acc_of(i, b)["acc5"] and not acc_of(i, a)["acc5"]
                 for i in ids)
        p = mcnemar(aw, bw)
        lines.append(f"- {names[a]} vs {names[b]}: "
                     f"{aw}/{bw} дискордантных, p = {p:.4f}")

    lines += ["", "## По категориям (Acc@5, лучшее LLM-условие vs граф без "
              "LLM)", "", "| категория | n | граф без LLM | Qwen + "
              "доказательства |", "|---|---|---|---|"]
    bycat = defaultdict(list)
    for i in ids:
        bycat[inp[i].get("category") or "?"].append(i)
    for cat, cids in sorted(bycat.items(), key=lambda kv: -len(kv[1])):
        g = sum(acc_of(i, "graph_nollm")["acc5"] for i in cids)
        q = sum(acc_of(i, "hybrid_evidence")["acc5"] for i in cids)
        lines.append(f"| {cat} | {len(cids)} | {100*g/len(cids):.1f}% "
                     f"| {100*q/len(cids):.1f}% |")

    text = "\n".join(lines)
    (R / "summary_rerank.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
