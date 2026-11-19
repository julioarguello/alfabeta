#!/bin/zsh
# Spike S9 (#279). Usage: STUDENT=<id> s9_watch.sh <probe.py> — waits for the student's next `classroom refresh` to end
# `ok` (a new run id in log.jsonl), then runs the probe at once through s9_run.sh. Prints only times and the run's
# outcome. A refresh that ends otherwise is reported and the wait goes on.
HERE=$(cd "$(dirname "$0")" && pwd)
: ${STUDENT:?set STUDENT to the student id, as in ~/.alfabeta/<id>}
LOG="$HOME/.alfabeta/$STUDENT/data/log.jsonl"
last() { LOG="$LOG" python3 -c '
import json, os
r = None
for line in open(os.environ["LOG"]):
    d = json.loads(line)
    if d.get("type") == "classroom_refresh" and d.get("step") == "classes":
        r = (d["run"], d.get("outcome"))
print(r[0] if r else "", r[1] if r else "")'; }
read SEEN _ <<< "$(last)"
echo "waiting from $(date +%H:%M:%S)"
while true; do
  sleep 20
  read RUN OUTCOME <<< "$(last)"
  [ "$RUN" = "$SEEN" ] && continue
  SEEN=$RUN
  echo "refresh ended $(date +%H:%M:%S): $OUTCOME"
  [ "$OUTCOME" = "ok" ] || continue
  sleep 5  # let the refresh's container and lock go
  "$HERE/s9_run.sh" "$1"
  exit $?
done
