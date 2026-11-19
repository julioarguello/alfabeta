#!/bin/zsh
# S8's dates mapping. Usage: STUDENT=<id> spikes/s8_dates_run.sh — with a live session in that student's read
# profile and no read running. Writes spikes/dates.json from the captures, then runs s8_dates.py with spikes/
# at /s8 and the captures at /captures (s8_calls.choose_classes reads them).
HERE=$(cd "$(dirname "$0")" && pwd)
source "$HERE/s8_common.sh"
(cd "$HERE/.." && STUDENT=$STUDENT uv run python spikes/s8_dates_prepare.py > "$HERE/dates.json")
echo "{\"account\": $ACCOUNT}" | docker run --rm -i --name "alfabeta-s8d-$STUDENT" --platform linux/amd64 \
  -v "$DATA/classroom-profile:/profile" -v "$DATA/captures:/captures:ro" \
  -v "$HERE:/s8:ro" --entrypoint python "$IMG" /s8/s8_dates.py
