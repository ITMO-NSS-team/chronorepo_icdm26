"""Inline demo_data.json into index.html so the demo stays a single file.

Replaces the whole first <script> block. Uses a lambda replacement because
backslashes inside the JSON would otherwise be treated as regex replacement
escapes and corrupt the payload.
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
blob = json.dumps(json.loads((HERE / "demo_data.json").read_text("utf-8")),
                  ensure_ascii=False, separators=(",", ":"))
html = (HERE / "index.html").read_text(encoding="utf-8")

pat = re.compile(r'"use strict";\n.*?\n</script>', re.S)
if not pat.search(html):
    raise SystemExit("first script block not found")
new = pat.sub(lambda m: f'"use strict";\nwindow.REAL={blob};\n</script>',
              html, count=1)
(HERE / "index.html").write_text(new, encoding="utf-8")

# verify the payload survived
m = re.search(r"window\.REAL=(.*?);\n</script>", new, re.S)
json.loads(m.group(1))
print(f"inlined and validated {len(blob) // 1024} KB of real data")
