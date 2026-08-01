"""CodeScout-style F1 analysis over f1_scores_{lite,verified}.jsonl.

Prediction set = files with score >= theta * max_score, capped at 5, min 1.
Theta is swept on Lite (dev) and the winner applied to Verified (test).
Reports macro-averaged file-level Precision / Recall / F1."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
THETAS = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
CAP = 5


def load(which):
    p = HERE / "results" / f"f1_scores_{which}.jsonl"
    return [json.loads(l) for l in open(p, encoding="utf-8")]


def predict(scored, theta):
    if not scored:
        return []
    smax = scored[0][1] or 1e-9
    pred = [p for p, s in scored if s >= theta * smax][:CAP]
    return pred or [scored[0][0]]


def prf(recs, key, theta):
    P = R = F = 0.0
    for r in recs:
        gold = set(r["gold"])
        pred = set(predict(r[key], theta))
        tp = len(gold & pred)
        p = tp / len(pred) if pred else 0.0
        q = tp / len(gold) if gold else 0.0
        P += p
        R += q
        F += 2 * p * q / (p + q) if p + q else 0.0
    n = len(recs)
    return 100 * P / n, 100 * R / n, 100 * F / n


def main():
    lite = load("lite")
    print(f"Lite dev sweep (n={len(lite)}):")
    best = {}
    for key in ("hybrid", "bm25"):
        rows = [(t, *prf(lite, key, t)) for t in THETAS]
        bt = max(rows, key=lambda r: r[3])
        best[key] = bt[0]
        print(f"  {key}: " + "  ".join(
            f"θ={t}:F1={f:.1f}" for t, _, _, f in rows))
        print(f"  -> best θ={bt[0]} (P={bt[1]:.1f} R={bt[2]:.1f} "
              f"F1={bt[3]:.1f})")

    try:
        ver = load("verified")
    except FileNotFoundError:
        print("verified scores not ready yet")
        return
    print(f"\nVerified test (n={len(ver)}), θ fixed from Lite:")
    for key in ("hybrid", "bm25"):
        p, r, f = prf(ver, key, best[key])
        print(f"  {key:7s} θ={best[key]}  Prec={p:.1f}  Rec={r:.1f}  "
              f"F1={f:.1f}")
    print("\nReference (CodeScout paper, Table 3, file-level F1 on "
          "Verified): Agentless 35.4, LocAgent 44.2, CodeScout-1.7B 55.5, "
          "CodeScout-4B 68.5, CodeScout-14B 68.6, "
          "RepoNavigator-32B 67.8, Claude-Sonnet-4.5 (best scaffold) 82.0")


if __name__ == "__main__":
    main()
