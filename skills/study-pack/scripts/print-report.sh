#!/usr/bin/env bash
# Render one Gemini Notebook report to a print-ready A4 PDF with formulas.
# Usage: print-report.sh <notebook-id> <artifact-id> <output.pdf> --student <id> [--home <dir>]
# Kept for the command it has always been; the work is done by print_pack.py beside it, run with
# the alfabeta clone this script sits in, whose loader reads the student's configuration.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
exec uv run --project "$here/../../.." python "$here/print_pack.py" report "$@"
