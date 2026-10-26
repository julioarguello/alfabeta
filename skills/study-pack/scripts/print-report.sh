#!/usr/bin/env bash
# Render one Gemini Notebook report to a print-ready A4 PDF with formulas.
# Usage: print-report.sh <notebook-id> <artifact-id> <output.pdf> [nlm-profile]
# Kept for the command it has always been; the work is done by print_pack.py beside it.
set -euo pipefail
exec python3 -I "$(dirname "$0")/print_pack.py" report "$1" "$2" "$3" ${4:+--profile "$4"}
