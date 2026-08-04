"""Generate paper figures (PDF).

The Pareto figure is self-contained (published + our final numbers,
hardcoded below with sources); the remaining figures need
experiments/results/digest.json and are skipped when it is absent.
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
FIGS = HERE / "overleaf" / "figs"
FIGS.mkdir(parents=True, exist_ok=True)

DIGEST = HERE.parent / "experiments" / "results" / "digest.json"
D = json.loads(DIGEST.read_text("utf-8")) if DIGEST.exists() else None

BLUE, ORANGE, AQUA, PURPLE = "#2a78d6", "#eb6834", "#1baf7a", "#8e5bd0"
plt.rcParams.update({"font.size": 8, "font.family": "sans-serif",
                     "axes.edgecolor": "#c3c2b7", "axes.linewidth": 0.6})

# ---- Fig: Pareto (strict Acc@5 on LocBench vs cost, log x) ---------------
# Ours: paper Table "locbench"/"heavy" (559/560 instances, official GT).
# x for the free rows is a nominal CPU-time placeholder; LLM rows use
# measured OpenRouter spend per issue (appendix L). Quoted points:
# LocAgent ACL'25 Table 7 (accuracy) and Table 5 (costs, SWE-bench Lite
# setting); SweRank ICLR'26 Table 2 (accuracy) and its reported ~$0.01.
fig, ax = plt.subplots(figsize=(3.45, 2.4))
pts = [
    # name, cost $/issue, strict Acc@5, color, marker, (dx, dy) pts, ha
    ("BM25", 2e-4, 0.347, ORANGE, "o", (8, -3), "left"),
    ("candidates, no LLM", 4e-4, 0.674, BLUE, "s", (7, -3), "left"),
    ("+ one 9B call", 1e-3, 0.805, BLUE, "*", (-7, -4), "right"),
    ("+ one MoE call (d100)", 1.5e-3, 0.837, BLUE, "P", (-4, 8), "center"),
    ("Agentless", 0.70, 0.675, AQUA, "^", (0, -13), "center"),
    ("LocAgent (7B ft)", 0.05, 0.786, AQUA, "v", (0, -13), "center"),
    ("OpenHands", 0.79, 0.798, AQUA, "s", (7, -3), "left"),
    ("LocAgent (Claude-3.5)", 0.66, 0.834, AQUA, "D", (0, 8), "center"),
    ("SweRank (7B)", 0.011, 0.855, PURPLE, "X", (0, -13), "center"),
    ("SweRank (32B)", 0.015, 0.866, PURPLE, "d", (4, 8), "center"),
]
for name, x, y, c, m, (dx, dy), ha in pts:
    ax.scatter(x, y, c=c, marker=m, s=70 if m in "*P" else 30, zorder=3,
               edgecolors="white", linewidths=0.5)
    ax.annotate(name, (x, y), xytext=(dx, dy), ha=ha,
                textcoords="offset points", fontsize=6.0)
ax.set_xscale("log")
ax.set_xlim(8e-5, 4)
ax.set_ylim(0.28, 0.95)
ax.set_xlabel("cost per issue, USD (log)")
ax.set_ylabel("strict Acc@5 (LocBench)")
ax.grid(True, which="major", lw=0.3, color="#e1e0d9", zorder=0)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(FIGS / "pareto.pdf")
print("pareto.pdf")

if D is None:
    print("digest.json not found - skipping data-dependent figures")
    sys.exit(0)

# ---- Fig: LocBench per-category gains -----------------------------------
fig, ax = plt.subplots(figsize=(3.45, 1.9))
cats = D["locbench"]["by_category"]
order = sorted(cats, key=lambda c: -cats[c]["bm25"]["n"])
labels = {"Bug Report": "Bug\n(n=230)", "Feature Request": "Feature\n(n=145)",
          "Performance Issue": "Perf.\n(n=137)",
          "Security Vulnerability": "Security\n(n=28)"}
xs = range(len(order))
bm = [cats[c]["bm25"]["r10"] for c in order]
hy = [cats[c]["bm25_a025_l90"]["r10"] for c in order]
ax.bar([x - 0.2 for x in xs], bm, 0.36, color=ORANGE, label="BM25")
ax.bar([x + 0.2 for x in xs], hy, 0.36, color=BLUE, label="+ graphs (ours)")
for x, (b, h) in enumerate(zip(bm, hy)):
    ax.text(x + 0.2, h + 0.015, f"+{100 * (h - b):.0f}", ha="center",
            fontsize=6.5, color=BLUE)
ax.set_xticks(list(xs))
ax.set_xticklabels([labels[c] for c in order], fontsize=7)
ax.set_ylabel("Recall@10")
ax.set_ylim(0, 0.75)
ax.legend(frameon=False, fontsize=7, loc="upper right")
ax.grid(True, axis="y", lw=0.3, color="#e1e0d9", zorder=0)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(FIGS / "categories.pdf")
print("categories.pdf")

# ---- Fig: orthogonality --------------------------------------------------
fig, ax = plt.subplots(figsize=(3.45, 1.8))
e1 = D["verified"]["e1"]
items = sorted(((r.split("/")[-1], m["median"]) for r, m in e1.items()),
               key=lambda t: t[1])
ax.barh([t[0] for t in items], [t[1] for t in items], color=BLUE, height=0.6)
ax.axvline(0.3, color=ORANGE, lw=1, ls="--")
ax.text(0.305, 0.2, "0.3", color=ORANGE, fontsize=6.5)
ax.set_xlabel("median Jaccard overlap: import vs. co-change neighbourhoods")
ax.tick_params(axis="y", labelsize=6.5)
ax.set_xlim(0, 0.45)
fig.tight_layout()
fig.savefig(FIGS / "orthogonality.pdf")
print("orthogonality.pdf")
