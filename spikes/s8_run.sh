#!/bin/zsh
# Spike S8 (#267): read-only, never signs in. Run only with a live session in the read profile and no read
# running. `s8_shape.py` runs the same way, with this folder mounted at /s8 (it imports s8_calls).
HERE=$(cd "$(dirname "$0")" && pwd)
source "$HERE/s8_common.sh"
echo "{\"account\": $ACCOUNT}" | docker run --rm -i --name alfabeta-s8 --platform linux/amd64 \
  -v "$HOME/.alfabeta/s1/data/classroom-profile:/profile" -v "$HOME/.alfabeta/s1/data/captures:/captures:ro" \
  -v "$HERE/s8_calls.py:/probe.py:ro" --entrypoint python "$IMG" /probe.py > "$HERE/s8-out.jsonl" 2>/dev/null
echo "s8 exit $?"
