"""Generate paper figures (PDF) from experiments/results/digest.json."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
D = json.loads((HERE.parent / "experiments" / "results" /
                "digest.json").read_text("utf-8"))
FIGS = HERE / "overleaf" / "figs"
FIGS.mkdir(parents=True, exist_ok=True)

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
plt.rcParams.update({"font.size": 8, "font.family": "sans-serif",
                     "axes.edgecolor": "#c3c2b7", "axes.linewidth": 0.6})

# ---- Fig: Pareto (quality vs cost, log x) -------------------------------
fig, ax = plt.subplots(figsize=(3.45, 2.3))
pts = [
    ("BM25", 2e-4, D["lite"]["all"]["bm25"]["hit10"], ORANGE, "o"),
    ("grep", 2e-4, D["lite"]["all"]["grep"]["hit10"], ORANGE, "s"),
    ("ChronoRepo", 4e-4, D["lite"]["all"]["bm25_a025_l90"]["hit10"], BLUE, "*"),
    ("Agentless", 0.70, 0.697, AQUA, "^"),
    ("LocAgent (Qwen-32B ft)", 0.09, 0.927, AQUA, "v"),
    ("LocAgent (Claude-3.5)", 0.66, 0.942, AQUA, "D"),
]
for name, x, y, c, m in pts:
    ax.scatter(x, y, c=c, marker=m, s=70 if m == "*" else 32, zorder=3,
               edgecolors="white", linewidths=0.5)
    dy = -0.055 if name in ("grep", "LocAgent (Qwen-32B ft)") else 0.028
    ax.annotate(name, (x, y), xytext=(0, 14 * dy * 3), ha="center",
                textcoords="offset points", fontsize=6.5)
ax.set_xscale("log")
ax.set_xlim(8e-5, 3)
ax.set_ylim(0.45, 1.02)
ax.set_xlabel("cost per issue, USD (log)")
ax.set_ylabel("issues with a gold file found")
ax.grid(True, which="major", lw=0.3, color="#e1e0d9", zorder=0)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(FIGS / "pareto.pdf")
print("pareto.pdf")

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
