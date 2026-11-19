#!/bin/zsh
# S8's last pieces. Usage: STUDENT=<id> run_s8c.sh — with a live session in that student's read profile, no read running.
HERE=$(cd "$(dirname "$0")" && pwd)
: ${STUDENT:?set STUDENT to the student id, as in ~/.alfabeta/<id>}
HOME_DIR="$HOME/.alfabeta/$STUDENT"; DATA="$HOME_DIR/data"
if [ -n "$(docker ps -q --filter name=alfabeta-classroom-read)" ] || [ -f "$DATA/lock.json" ]; then echo "busy: a read is running"; exit 1; fi
IMG=$(docker images alfabeta-classroom-read --format '{{.Repository}}:{{.Tag}}' | head -1)
ACCOUNT=$(STUDENT_HOME="$HOME_DIR" python3 -c 'import tomllib,json,os;c=tomllib.load(open(os.environ["STUDENT_HOME"]+"/config.toml","rb"));print(json.dumps(c["classroom"]["account"]))')
echo "{\"account\": $ACCOUNT}" | docker run --rm -i --name "alfabeta-s8c-$STUDENT" --platform linux/amd64 \
  -v "$DATA/classroom-profile:/profile" -v "$DATA/captures:/captures:ro" -v "$HERE:/s8:ro" \
  --entrypoint python "$IMG" /s8/s8c_upkeep_args.py > "$HERE/s8c-out.jsonl" 2>/dev/null
echo "s8c exit $?"
