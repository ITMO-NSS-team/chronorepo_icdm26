"""Paper figure: spatio-temporal repository graph walkthrough on the real
SWE-bench Lite instance sphinx-doc__sphinx-8595. All numbers are real
(mined from the sphinx repository at the issue's base commit, Dec 2020)."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
FIGS = HERE / "overleaf" / "figs"

BLUE, ORANGE, AQUA, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#898781"
INK, MUT = "#222222", "#666666"
plt.rcParams.update({"font.size": 6.8, "font.family": "sans-serif"})

# real rerank rank of the gold file, updated after the Lite Qwen run
QWEN_GOLD_RANK = 1

fig = plt.figure(figsize=(7.1, 2.75))

# ---------------- panel 1: the issue ------------------------------------
ax1 = fig.add_axes([0.005, 0.03, 0.185, 0.94])
ax1.axis("off")
ax1.add_patch(FancyBboxPatch((0.03, 0.30), 0.94, 0.62, mutation_aspect=0.4,
              boxstyle="round,pad=0.02", fc="#f6f6f4", ec="#c9c8c2", lw=0.7))
ax1.text(0.08, 0.86, "GitHub issue #8595", fontsize=7.2,
         fontweight="bold", color=INK)
ax1.text(0.08, 0.79, "sphinx-doc/sphinx", fontsize=6.2, color=MUT)
ax1.text(0.08, 0.40, '"autodoc: empty __all__\nattribute is ignored...\n'
         'All foo, bar, baz are\nshown. Expected: no\nentries."',
         fontsize=6.6, color=MUT, va="bottom", linespacing=1.35)
ax1.text(0.08, 0.245, "lexical seeds:", fontsize=6.4, color=MUT)
for tok, x, y, w in [("__all__", 0.05, 0.150, 0.36), ("autodoc", 0.47,
                     0.150, 0.36), ("automodule", 0.05, 0.045, 0.48),
                     ("members", 0.60, 0.045, 0.37)]:
    ax1.add_patch(FancyBboxPatch((x, y), w, 0.082,
                  boxstyle="round,pad=0.012", fc="white", ec=GREY, lw=0.5))
    ax1.text(x + 0.04, y + 0.022, tok, fontsize=6.0, color=INK,
             family="monospace")

# ---------------- panel 2: the graph ------------------------------------
ax2 = fig.add_axes([0.20, 0.03, 0.46, 0.94])
ax2.set_xlim(0, 1)
ax2.set_ylim(0, 1)
ax2.axis("off")
ax2.text(0.5, 0.97, "two-layer temporal graph at the issue's base commit "
         "(Dec 2020)", ha="center", fontsize=6.8, color=MUT, style="italic")

N = {
    "bug_tpl":  (0.19, 0.845, ".github/.../bug_report.md", GREY, "seed #1"),
    "docs":     (0.10, 0.50, "doc/.../autodoc.rst",       GREY, "seed #2"),
    "test":     (0.46, 0.80, "tests/test_ext_autodoc.py", BLUE, "seed #5"),
    "configs":  (0.83, 0.80, "tests/test_ext_\nautodoc_configs.py", BLUE,
                 "seed #8"),
    "app":      (0.16, 0.16, "sphinx/application.py",     BLUE, None),
    "gold":     (0.55, 0.30, "sphinx/ext/autodoc/\n__init__.py", ORANGE,
                 None),
}


def node(key, star=False):
    x, y, label, color, seed = N[key]
    w = 0.185, 0.16
    bb = FancyBboxPatch((x - 0.095, y - 0.075), 0.19, 0.15,
                        boxstyle="round,pad=0.008",
                        fc="white" if not star else "#fdf0e7",
                        ec=color, lw=1.4 if star else 0.8)
    ax2.add_patch(bb)
    ax2.text(x, y + (0.012 if seed else 0.0), label, ha="center",
             va="center", fontsize=5.9, color=INK, linespacing=1.2)
    if seed:
        ax2.text(x, y - 0.055, seed, ha="center", fontsize=5.6, color=AQUA,
                 fontweight="bold")
    if star:
        ax2.text(x - 0.088, y + 0.062, "★", fontsize=8, color=ORANGE,
                 ha="center", va="center")
        ax2.text(x, y - 0.058, "gold: file of the actual fix", ha="center",
                 fontsize=5.4, color=ORANGE)


def edge(a, b, color, lw, ls, rad=0.0, alpha=1.0):
    xa, ya = N[a][0], N[a][1]
    xb, yb = N[b][0], N[b][1]
    ax2.add_patch(FancyArrowPatch((xa, ya), (xb, yb), arrowstyle="-",
                  connectionstyle=f"arc3,rad={rad}", color=color, lw=lw,
                  linestyle=ls, alpha=alpha, shrinkA=16, shrinkB=16))


# edges: import (solid blue) and co-change (dashed orange, width~decayed w)
edge("test", "gold", BLUE, 0.8, "-", rad=0.12)
edge("app", "gold", BLUE, 0.8, "-", rad=-0.10)
edge("test", "gold", ORANGE, 2.6, (0, (4, 2)), rad=-0.10)
edge("configs", "gold", ORANGE, 1.2, (0, (4, 2)), rad=-0.15)
edge("app", "gold", ORANGE, 0.6, (0, (4, 2)), rad=0.14, alpha=0.45)

ax2.text(0.385, 0.565, "co-changed ×34\nall in 2020 → w=11.9",
         fontsize=5.6, color=ORANGE, ha="center", linespacing=1.2)
ax2.text(0.835, 0.53, "×10, 2019–20\nw=2.7", fontsize=5.6, color=ORANGE,
         ha="center")
ax2.text(0.235, 0.31, "×10, but 2017–19\nfaded: w=0.02", fontsize=5.6,
         color=ORANGE, alpha=0.75, ha="center")

# mini year-bars for fresh vs faded coupling
for x0, y0, bars, col, alpha in [
        (0.56, 0.655, [0, 0, 0, 34], ORANGE, 1.0),
        (0.045, 0.275, [1, 5, 4, 0], ORANGE, 0.5)]:
    mx = max(bars) or 1
    for j, v in enumerate(bars):
        ax2.add_patch(plt.Rectangle((x0 + j * 0.018, y0),
                      0.013, 0.055 * v / mx, fc=col, alpha=alpha, ec="none"))
    for j, yr in enumerate(["'17", "", "", "'20"]):
        if yr:
            ax2.text(x0 + j * 0.018 + 0.006, y0 - 0.026, yr, fontsize=4.6,
                     color=MUT, ha="center")

# propagation arrows (seed mass flowing into gold)
for src, rad in [("test", -0.28), ("configs", -0.30)]:
    xa, ya = N[src][0], N[src][1]
    xb, yb = N["gold"][0], N["gold"][1]
    ax2.add_patch(FancyArrowPatch((xa, ya - 0.02), (xb, yb + 0.02),
                  arrowstyle="-|>,head_width=2.2,head_length=3.5",
                  connectionstyle=f"arc3,rad={rad}", color=AQUA, lw=1.1,
                  shrinkA=18, shrinkB=18, zorder=5))
ax2.text(0.79, 0.335, "propagation:\nseed mass flows\nalong edges",
         fontsize=5.6, color=AQUA, ha="center", linespacing=1.25)
ax2.text(0.145, 0.675, "lexical hits without\ngraph support: mass dies",
         fontsize=5.4, color=GREY, ha="center", linespacing=1.2)

# legend
lx = 0.015
ax2.plot([lx, lx + 0.05], [0.015, 0.015], color=BLUE, lw=0.9)
ax2.text(lx + 0.06, 0.008, "import", fontsize=5.6, color=MUT)
ax2.plot([lx + 0.17, lx + 0.22], [0.015, 0.015], color=ORANGE, lw=1.8,
         linestyle=(0, (4, 2)))
ax2.text(lx + 0.23, 0.008, "co-change, width = Σe^(−λ·age)", fontsize=5.6,
         color=MUT)

for key in N:
    node(key, star=(key == "gold"))

# ---------------- panel 3: the three rankings ---------------------------
ax3 = fig.add_axes([0.675, 0.03, 0.32, 0.94])
ax3.axis("off")
ax3.set_xlim(0, 1)
ax3.set_ylim(0, 1)

def ranked_list(y0, title, cost, rows, gold_note, note_color):
    ax3.add_patch(FancyBboxPatch((0.02, y0), 0.96, 0.255,
                  boxstyle="round,pad=0.010", fc="#f6f6f4", ec="#c9c8c2",
                  lw=0.7))
    ax3.text(0.05, y0 + 0.215, title, fontsize=6.6, fontweight="bold",
             color=INK)
    ax3.text(0.97, y0 + 0.215, cost, fontsize=6.0, color=MUT, ha="right")
    for j, r in enumerate(rows):
        ax3.text(0.06, y0 + 0.155 - j * 0.048, r, fontsize=5.7, color=MUT,
                 family="monospace")
    ax3.text(0.06, y0 + 0.022, gold_note, fontsize=6.0, color=note_color,
             fontweight="bold")

ranked_list(0.70, "1 · BM25 only", "~0 ms",
            ["1 .github/.../bug_report.md", "2 doc/.../autodoc.rst",
             "3 doc/man/sphinx-apidoc.rst"],
            "gold not in top-20  ✗", "#c0392b")
ranked_list(0.37, "2 · + graph propagation", "+40 ms, $0",
            ["1 tests/test_ext_autodoc.py", "2 sphinx/ext/apidoc.py",
             "3 tests/test_ext_autodoc_configs.py"],
            "gold pulled to rank 9  (top-10) ✓", "#a8620a")
ranked_list(0.04, "3 · + one 7B call (top-50)", "+2 s, <$0.001",
            [f"{QWEN_GOLD_RANK} sphinx/ext/autodoc/__init__.py  ★"] +
            ["2 tests/test_ext_autodoc.py", "3 doc/.../autodoc.rst"],
            f"gold at rank {QWEN_GOLD_RANK}  ✓", "#1e7a34")

for y in (0.665, 0.335):
    ax3.annotate("", xy=(0.5, y - 0.028), xytext=(0.5, y),
                 arrowprops=dict(arrowstyle="-|>", color=MUT, lw=1.0))

FIGS.mkdir(parents=True, exist_ok=True)
fig.savefig(FIGS / "walkthrough.pdf")
fig.savefig(HERE / "walkthrough_preview.png", dpi=150)
print("saved walkthrough.pdf + preview png")
