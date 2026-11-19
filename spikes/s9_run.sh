#!/bin/zsh
# Spike S9 (#279). Usage: STUDENT=<id> s9_run.sh <probe.py> [extra env for the container, e.g. S9_BLOCK_BROWSERINFO=1]
# Runs one probe in the read image against the session the family's last `classroom refresh` left in that student's
# read profile. Never signs in: the probes stop on an expired session. Stops if a read holds the student's lock or a
# read container runs, or if Docker's machine has less than the read's 1536 MB floor available (#274).
HERE=$(cd "$(dirname "$0")" && pwd)
: ${STUDENT:?set STUDENT to the student id, as in ~/.alfabeta/<id>}
PROBE=${1:?probe file}; shift
HOME_DIR="$HOME/.alfabeta/$STUDENT"; DATA="$HOME_DIR/data"
if [ -n "$(docker ps -q --filter name=alfabeta-classroom-read)" ]; then echo "busy: a read container is running"; exit 1; fi
if ! LOCK="$DATA/lock" python3 -c 'import fcntl,os,sys
h=open(os.environ["LOCK"]);
try: fcntl.flock(h, fcntl.LOCK_EX|fcntl.LOCK_NB)
except OSError: sys.exit(1)'; then echo "busy: the student's lock is held"; exit 1; fi
IMG=$(docker images alfabeta-classroom-read --format '{{.Repository}}:{{.Tag}}' | grep -v ':test$' | head -1)
AVAIL=$(docker run --rm --entrypoint cat "$IMG" /proc/meminfo | awk '/MemAvailable/ {print int($2/1024)}')
echo "memory available MB: $AVAIL"
if [ "${AVAIL:-0}" -lt 1536 ]; then echo "stop: under the 1536 MB floor"; exit 1; fi
REQ=$(STUDENT_HOME="$HOME_DIR" python3 - <<'EOF'
import tomllib, json, os
home = os.environ["STUDENT_HOME"]
acct = tomllib.load(open(home + "/config.toml", "rb"))["classroom"]["account"]
run = None
for line in open(home + "/data/log.jsonl"):
    d = json.loads(line)
    if d.get("type") == "classroom_refresh" and d.get("step") == "classes" and d.get("outcome") == "ok":
        run = d["run"]
print(json.dumps({"account": acct, "run": run}))
EOF
)
ENVS=()
for kv in "$@"; do ENVS+=(-e "$kv"); done
OUT="${S9_OUT:-$HERE/out}"; mkdir -p "$OUT"
# The answers s9b keeps for the offline comparison stay in the student's own data folder, 0700, deleted after.
ANS="$DATA/spike-s9"; mkdir -p -m 700 "$ANS"
NAME=$(basename "$PROBE" .py)
echo "$REQ" | docker run --rm -i --name "alfabeta-s9-$STUDENT" --platform linux/amd64 "${ENVS[@]}" \
  -v "$DATA/classroom-profile:/profile" -v "$DATA/captures:/captures:ro" -v "$HERE:/s9:ro" -v "$ANS:/s9out" \
  --entrypoint python "$IMG" "/s9/$PROBE" > "$OUT/$NAME.jsonl" 2> "$OUT/$NAME.err"
echo "$NAME exit $? at $(date +%H:%M:%S)"
