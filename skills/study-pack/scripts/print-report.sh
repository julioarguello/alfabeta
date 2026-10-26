#!/usr/bin/env bash
# Render a Gemini Notebook report (study guide, briefing…) to a print-ready A4 PDF with formulas.
# Usage: print-report.sh <notebook-id> <artifact-id> <output.pdf> [nlm-profile]
set -euo pipefail
NB="$1"; ID="$2"; OUT="$3"
# Profile: 4th argument, else notebook.nlm_profile from the private configuration, else nlm's default.
PROFILE="${4:-$(python3 -I -c 'import json,os,sys
try: print(json.load(open(os.path.expanduser("~/.alfabeta/config.json"))).get("notebook",{}).get("nlm_profile","default"))
except OSError: print("default")')}"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
NLM_PROFILE="$PROFILE" nlm download report "$NB" --id "$ID" -o "$WORK/report.md" >/dev/null
cat > "$WORK/print.css" <<'CSS'
@page { size: A4; margin: 18mm 16mm 20mm 16mm; @bottom-center { content: counter(page) " / " counter(pages); font: 9pt sans-serif; color: #666; } }
body { font: 11pt/1.45 -apple-system, "Helvetica Neue", Arial, sans-serif; color: #111; max-width: none; }
h1 { font-size: 20pt; margin: 0 0 6mm; } h2 { font-size: 15pt; margin-top: 8mm; border-bottom: 1px solid #ccc; padding-bottom: 1mm; }
h3 { font-size: 12.5pt; margin-top: 5mm; } h2, h3 { break-after: avoid; }
table { border-collapse: collapse; table-layout: auto; width: 100%; font-size: 10pt; margin: 3mm 0; } th, td { border: 1px solid #bbb; padding: 1.5mm 2mm; vertical-align: top; }
th { background: #f0f0f0; } tr, li, pre { break-inside: avoid; }
pre, code { font-family: Menlo, "DejaVu Sans Mono", monospace; font-size: 9pt; } pre { background: #f7f7f7; padding: 3mm; white-space: pre; overflow: hidden; }
col { width: auto !important; }
hr { border: 0; border-top: 1px solid #ddd; margin: 5mm 0; }
CSS
# NotebookLM omits the blank line pandoc needs before a list; add it.
python3 -I -c 'import re,sys; L=open(sys.argv[1]).read().split("\n"); out=[]
for l in L:
    if re.match(r"\s*([*+-]|\d+[.)])\s", l) and out and out[-1].strip() and not re.match(r"\s*([*+-]|\d+[.)])\s", out[-1]): out.append("")
    out.append(l)
open(sys.argv[1],"w").write("\n".join(out))' "$WORK/report.md"
pandoc "$WORK/report.md" -f markdown-fancy_lists+tex_math_dollars -t html5 -s --math-method=katex:https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/ \
  --metadata title=" " -c "$WORK/print.css" --embed-resources=false -o "$WORK/report.html"
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --no-pdf-header-footer \
  --virtual-time-budget=15000 --run-all-compositor-stages-before-draw --print-to-pdf="$OUT" "file://$WORK/report.html" 2>/dev/null
echo "$OUT"
