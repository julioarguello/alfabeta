#!/bin/zsh
# S8 second half. Usage: STUDENT=<id> spikes/s8b_run.sh — with a live session in that student's read profile, no read running.
HERE=$(cd "$(dirname "$0")" && pwd)
: ${STUDENT:?set STUDENT to the student id, as in ~/.alfabeta/<id>}
HOME_DIR="$HOME/.alfabeta/$STUDENT"; DATA="$HOME_DIR/data"
if [ -n "$(docker ps -q --filter name=alfabeta-classroom-read)" ] || [ -f "$DATA/lock.json" ]; then echo "busy: a read is running"; exit 1; fi
IMG=$(docker images alfabeta-classroom-read --format '{{.Repository}}:{{.Tag}}' | head -1)
ACCOUNT=$(STUDENT_HOME="$HOME_DIR" python3 -c 'import tomllib,json,os;c=tomllib.load(open(os.environ["STUDENT_HOME"]+"/config.toml","rb"));print(json.dumps(c["classroom"]["account"]))')
CLASSES=$(python3 "$HERE/s8b_pick_classes.py" "$DATA/captures")
rm -rf "$HERE/s8b-out" && mkdir -p "$HERE/s8b-out"
echo "{\"run\": \"s8b\", \"account\": $ACCOUNT, \"password\": null, \"signin\": false}" | docker run --rm -i --name "alfabeta-s8b-$STUDENT" --platform linux/amd64 \
  -v "$DATA/classroom-profile:/profile" -v "$HERE/s8b-out:/out" -v "$HERE/s8b_allowlist.py:/s8b.py:ro" \
  --entrypoint python "$IMG" /s8b.py ${=CLASSES} > "$HERE/events.jsonl" 2>/dev/null
echo "s8b exit $?"
python3 "$HERE/s8b_compare.py" "$HERE/s8b-out" "$DATA/captures" > "$HERE/compare.txt"
