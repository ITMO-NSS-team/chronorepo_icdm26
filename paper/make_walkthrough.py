"""Paper figure: how the pipeline resolves two real issues.

Left: the temporal graph around the gold file of SWE-bench Lite instance
sphinx-8595 (real co-change counts mined at its base commit, Dec 2020).
Middle and right: the three ranking stages on that instance and on
django-11964, where the gold file is too new to have co-change history and
the single 7B call is what recovers it. All numbers come from our runs.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
FIGS = HERE / "overleaf" / "figs"
FIGS.mkdir(parents=True, exist_ok=True)

BLUE, ORANGE, AQUA, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#898781"
INK, MUT = "#222222", "#666666"
GOOD, BAD = "#1e7a34", "#c0392b"
plt.rcParams.update({"font.size": 6.8, "font.family": "sans-serif"})

fig = plt.figure(figsize=(7.1, 2.6))

# ---------------- panel 1: the temporal graph ---------------------------
ax = fig.add_axes([0.004, 0.02, 0.40, 0.96])
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")
ax.text(0.5, 0.965, "temporal graph around the gold file, sphinx at Dec 2020",
        ha="center", fontsize=6.6, color=MUT, style="italic")

GOLD = (0.50, 0.40)
NB = [  # label, position, total co-change, year histogram 2017..2020
    ("tests/test_autodoc.py", (0.16, 0.78), 45, [2, 10, 15, 18]),
    ("tests/test_ext_autodoc.py", (0.82, 0.74), 34, [0, 0, 0, 34]),
    ("sphinx/util/inspect.py", (0.87, 0.30), 25, [1, 6, 4, 14]),
    ("sphinx/ext/autodoc/\nimporter.py", (0.155, 0.315), 20, [5, 3, 2, 10]),
]
maxw = 45
for label, (x, y), tot, hist in NB:
    recent = hist[-1] + 0.5 * hist[-2]
    lw = 0.8 + 3.2 * recent / 40
    alpha = 0.35 + 0.6 * min(1.0, recent / 40)
    ax.add_patch(FancyArrowPatch((x, y), GOLD, arrowstyle="-",
                 connectionstyle="arc3,rad=0.12", color=ORANGE, lw=lw,
                 linestyle=(0, (3.5, 2)), alpha=alpha, shrinkA=20,
                 shrinkB=22))
    ax.add_patch(FancyBboxPatch((x - 0.135, y - 0.052), 0.27, 0.105,
                 boxstyle="round,pad=0.006", fc="white", ec=BLUE, lw=0.7))
    ax.text(x, y + 0.012, label, ha="center", va="center", fontsize=5.6,
            color=INK, linespacing=1.1)
    ax.text(x, y - 0.035, f"co-changed x{tot}", ha="center", fontsize=5.3,
            color=ORANGE)
    # year sparkline
    bx, by = x - 0.05, y - 0.105
    for j, v in enumerate(hist):
        ax.add_patch(plt.Rectangle((bx + j * 0.019, by), 0.014,
                     0.052 * v / maxw, fc=ORANGE, alpha=alpha, ec="none"))
    ax.text(bx - 0.012, by + 0.006, "'17", fontsize=4.4, color=MUT,
            ha="right")
    ax.text(bx + 4 * 0.019, by + 0.006, "'20", fontsize=4.4, color=MUT)

ax.add_patch(FancyBboxPatch((GOLD[0] - 0.16, GOLD[1] - 0.055), 0.32, 0.11,
             boxstyle="round,pad=0.008", fc="#fdf0e7", ec=ORANGE, lw=1.5))
ax.text(GOLD[0], GOLD[1] + 0.012, "sphinx/ext/autodoc/__init__.py",
        ha="center", va="center", fontsize=5.9, color=INK)
ax.text(GOLD[0], GOLD[1] - 0.033, "gold: file of the actual fix",
        ha="center", fontsize=5.4, color=ORANGE)
ax.text(0.53, 0.055, "edge width = decayed weight: 34 co-changes all in 2020\n"
        "outweigh 45 spread over four years",
        ha="center", fontsize=5.5, color=MUT, linespacing=1.25)


# ---------------- panels 2 and 3: the three stages ----------------------
def stages(x0, title, sub, rows, verdicts):
    axp = fig.add_axes([x0, 0.02, 0.29, 0.96])
    axp.set_xlim(0, 1)
    axp.set_ylim(0, 1)
    axp.axis("off")
    axp.text(0.02, 0.955, title, fontsize=7.0, fontweight="bold", color=INK)
    axp.text(0.02, 0.895, sub, fontsize=5.9, color=MUT)
    for k, ((head, cost, items), (verdict, col)) in enumerate(
            zip(rows, verdicts)):
        y0 = 0.60 - k * 0.30
        axp.add_patch(FancyBboxPatch((0.02, y0), 0.96, 0.255,
                      boxstyle="round,pad=0.008", fc="#f6f6f4",
                      ec="#c9c8c2", lw=0.7))
        axp.text(0.05, y0 + 0.20, head, fontsize=6.4, fontweight="bold",
                 color=INK)
        axp.text(0.97, y0 + 0.20, cost, fontsize=5.8, color=MUT, ha="right")
        for j, it in enumerate(items):
            axp.text(0.06, y0 + 0.142 - j * 0.045, it, fontsize=5.5,
                     color=MUT, family="monospace")
        axp.text(0.06, y0 + 0.02, verdict, fontsize=5.9, color=col,
                 fontweight="bold")
        if k < 2:
            axp.annotate("", xy=(0.5, y0 - 0.028), xytext=(0.5, y0 - 0.004),
                         arrowprops=dict(arrowstyle="-|>", color=MUT,
                                         lw=0.9))


stages(0.414, "sphinx-8595", "gold file has years of co-change history",
       [("1 . BM25", "~0 ms",
         [".github/.../bug_report.md", "doc/.../autodoc.rst",
          "doc/man/sphinx-apidoc.rst"]),
        ("2 . fused candidates", "+40 ms, $0",
         ["sphinx/ext/autodoc/__init__.py *", "sphinx/application.py",
          "sphinx/ext/autosummary/generate.py"]),
        ("3 . + one 7B call", "+2 s, <$0.001",
         ["sphinx/ext/autodoc/__init__.py *", "sphinx/domains/python.py",
          "sphinx/ext/autodoc/importer.py"])],
       [("gold not in top-10", BAD), ("gold at rank 1: graph alone", GOOD),
        ("rank 1 confirmed", GOOD)])

stages(0.708, "django-11964", "gold file created 2 months before: no history",
       [("1 . BM25", "~0 ms",
         ["docs/intro/tutorial05.txt", "docs/topics/testing/overview.txt",
          "docs/intro/tutorial02.txt"]),
        ("2 . fused candidates", "+40 ms, $0",
         ["django/db/models/fields/__init__.py", "django/db/models/base.py",
          "django/contrib/auth/models.py"]),
        ("3 . + one 7B call", "+2 s, <$0.001",
         ["django/db/models/enums.py *",
          "django/db/models/fields/__init__.py",
          "django/db/models/base.py"])],
       [("gold not in top-10", BAD), ("gold only at rank 23", BAD),
        ("rank 1: the model recovers it", GOOD)])

fig.savefig(FIGS / "walkthrough.pdf")
fig.savefig(HERE / "walkthrough_preview.png", dpi=150)
print("saved walkthrough.pdf + preview")
