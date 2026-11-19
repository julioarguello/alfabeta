#!/bin/zsh
# Issue 263 (research S15): one load of Classroom's home page in the read image, signin false, no
# password. Usage: STUDENT=<id> spikes/s15_home_probe.sh — only with a live session in that student's read
# profile and no read running (lock released).
set -e
: ${STUDENT:?set STUDENT to the student id, as in ~/.alfabeta/<id>}
HERE=$(cd "$(dirname "$0")" && pwd)
HOME_DIR="$HOME/.alfabeta/$STUDENT"
mkdir -p "$HERE/s15-out"
IMG=$(docker images alfabeta-classroom-read --format '{{.Repository}}:{{.Tag}}' | head -1)
STUDENT_HOME="$HOME_DIR" python3 -c 'import tomllib,json,os;c=tomllib.load(open(os.environ["STUDENT_HOME"]+"/config.toml","rb"));print(json.dumps({"account":c["classroom"]["account"],"mode":"home"}))' \
 | docker run --rm -i --name "alfabeta-probe-263-$STUDENT" --platform linux/amd64 \
   -v "$HOME_DIR/data/classroom-profile:/profile" \
   -v "$HOME_DIR/data/captures:/captures:ro" \
   -v "$HERE/s15-out:/out" -v "$HERE/s15_home_probe.py:/probe.py:ro" \
   --entrypoint python "$IMG" /probe.py
