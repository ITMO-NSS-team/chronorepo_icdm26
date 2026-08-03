"""Sanity checks for main.tex: citations, environments, refs, dashes."""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent / "overleaf"
tex = (HERE / "main.tex").read_text(encoding="utf-8")
bib = (HERE / "refs.bib").read_text(encoding="utf-8")

keys = set()
for m in re.finditer(r"\\cite\{([^}]*)\}", tex):
    keys.update(k.strip() for k in m.group(1).split(","))
defined = set(re.findall(r"@\w+\{([^,]+),", bib))
print(f"cited={len(keys)} defined={len(defined)}")
print("missing:", sorted(keys - defined) or "none")
print("unused :", sorted(defined - keys) or "none")

for env in ("table", "figure", r"figure\*", "itemize", "tabular",
            "tikzpicture", "abstract"):
    o = len(re.findall(r"\\begin\{" + env + r"\}", tex))
    c = len(re.findall(r"\\end\{" + env + r"\}", tex))
    print(f"{env:12s} begin={o} end={c} {'OK' if o == c else 'MISMATCH'}")

labs = set(re.findall(r"\\label\{([^}]*)\}", tex))
refs = set(re.findall(r"\\ref\{([^}]*)\}", tex))
print("dangling refs:", sorted(refs - labs) or "none")
print("em-dashes:", tex.count("---"))
print("figures referenced:",
      sorted(re.findall(r"includegraphics\[[^]]*\]\{([^}]*)\}", tex)))
missing_files = [f for f in re.findall(
    r"includegraphics\[[^]]*\]\{([^}]*)\}", tex)
    if not (HERE / f).exists()]
print("missing figure files:", missing_files or "none")
