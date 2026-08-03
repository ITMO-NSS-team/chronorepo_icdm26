"""Rough page-length estimate for the IEEEtran two-column draft."""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
t = (Path(__file__).parent / "overleaf" / "main.tex").read_text("utf-8")
body = t[t.find(r"\begin{document}"):]
prose = re.sub(r"\\begin\{(table|figure\*|figure|tikzpicture|tabular)\}"
               r".*?\\end\{\1\}", "", body, flags=re.S)
words = len(re.findall(r"[A-Za-z][A-Za-z'-]+", prose))
n_tab = len(re.findall(r"\\begin\{table\}", body))
n_fig = len(re.findall(r"\\begin\{figure\}", body))
n_figw = len(re.findall(r"\\begin\{figure\*\}", body))
# IEEEtran conference: ~950 words per page of two-column prose;
# a column float ~0.30 page, a full-width float ~0.45 page.
est = words / 950 + 0.28 * n_tab + 0.30 * n_fig + 0.45 * n_figw
print(f"prose words: {words}")
print(f"tables: {n_tab}  column figures: {n_fig}  full-width: {n_figw}")
print(f"estimated pages: {est:.1f}")
print(f"over 4-page limit by roughly: {max(0, est - 4):.1f} pages")
