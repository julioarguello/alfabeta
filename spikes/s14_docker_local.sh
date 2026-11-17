#!/bin/zsh
# Spike S14 in a container on the Mac (#166): the scripted sign-in and the whole read, inside Docker,
# from the home address. The family runs it (constitution III); Claude never starts the real sign-in.
#
#   spikes/s14_docker_local.sh build             builds alfabeta-s14:local (linux/amd64, Google Chrome)
#   spikes/s14_docker_local.sh run               one sign-in and one session check, nothing kept
#   spikes/s14_docker_local.sh capture [ids]     a real alfabeta run: lock, sign in and capture every
#                                                class (or only the comma-separated class ids), hand
#                                                the captures to `alfabeta download collect`, then
#                                                `alfabeta classroom plan`; nothing is copied to Drive
#
# The account comes from the student's config and the password from the keychain item the family
# stored (`security add-generic-password -s alfabeta-classroom -a s1 -w`). Both reach the container
# as environment variables passed by name (`-e NAME`), so neither is on any command line.
set -u
HERE="${0:A:h}"
REPO="${HERE:h}"
STUDENT="${S14_STUDENT:-s1}"
IMAGE=alfabeta-s14:local
DATA="$HOME/.alfabeta/$STUDENT/data"

alfabeta() { uv run -q --project "$REPO" python -m alfabeta "$@" --student "$STUDENT"; }
config_value() {  # $1 table, $2 key: one value of the student's config, never printed by the caller
  uv run -q --project "$REPO" python -c \
    'import pathlib, sys, tomllib; c = tomllib.loads((pathlib.Path.home() / ".alfabeta" / sys.argv[1] / "config.toml").read_text()); print(str(c[sys.argv[2]][sys.argv[3]]).strip())' \
    "$STUDENT" "$1" "$2"
}
credentials() {
  S14_ACCOUNT="$(config_value classroom account)"
  S14_PASSWORD="$(security find-generic-password -s alfabeta-classroom -a "$STUDENT" -w)"
  export S14_ACCOUNT S14_PASSWORD
}

case "${1:-}" in
  build)
    context="$(mktemp -d)"
    cp "$HERE/s14_scripted_signin.py" "$HERE/s14_capture.py" "$HERE/s14-cloud/Dockerfile" "$context/"
    cp "$REPO/skills/classroom-sync/scripts/extract.js" "$context/extract.js"
    docker build --platform linux/amd64 -t "$IMAGE" "$context"; rc=$?
    rm -rf "$context"
    exit $rc
    ;;
  run)
    credentials
    docker run --rm --platform linux/amd64 -e S14_ACCOUNT -e S14_PASSWORD "$IMAGE"
    ;;
  capture)
    taken="$(alfabeta lock take --mode interactive 2>&1)"
    run="$(print -r -- "$taken" | python3 -c 'import json, sys
for line in sys.stdin:
    if line.startswith("{"): print(json.loads(line).get("run", "")); break')"
    [[ -n "$run" ]] || { print -u2 "lock not taken: $taken"; exit 1; }
    print "lock taken: run $run"
    export ALFABETA_RUN="$run" S14_ONLY="${2:-}"
    out="$DATA/spike-166/out-$run"
    mkdir -p -m 700 "$out"
    credentials
    print "run $run: signing in and capturing (10-15 min for every class)"
    docker run --rm --platform linux/amd64 -e S14_ACCOUNT -e S14_PASSWORD -e ALFABETA_RUN -e S14_ONLY \
      -v "$out:/out" "$IMAGE" python /app/s14_capture.py &
    docker_pid=$!
    while kill -0 $docker_pid 2>/dev/null; do alfabeta lock renew --wait 60 >/dev/null 2>&1; done
    wait $docker_pid; rc=$?
    unset S14_PASSWORD
    downloads="$(config_value downloads folder)"; downloads="${downloads/#\~/$HOME}"
    moved=0
    for f in "$out"/alfabeta-capture-"$run"-*.json(N); do mv "$f" "$downloads/" && moved=$((moved + 1)); done
    rmdir "$out" 2>/dev/null
    print "captures handed over: $moved (container exit $rc)"
    alfabeta download collect --wait 10 | tail -1 | python3 -c 'import json, sys; d = json.load(sys.stdin); print("collected classes:", len(d.get("classes", [])))'
    alfabeta classroom plan | tail -1 | python3 -c 'import json, sys; d = json.load(sys.stdin); print("plan: downloads", len(d.get("downloads", [])), "pending decisions", len(d.get("pending_decisions", [])))' 2>/dev/null \
      || print "plan: see $DATA/plan.json"
    alfabeta lock release >/dev/null
    print "lock released; nothing copied to Drive (classroom apply not run)"
    exit $rc
    ;;
  *) print -u2 "usage: $0 build|run|capture [class ids]"; exit 2;;
esac
