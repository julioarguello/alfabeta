#!/bin/zsh
# Spike S14 in a container on the Mac (#166): the same scripted sign-in and read, inside Docker, from
# the home address. The family runs it (constitution III); Claude never starts the real sign-in.
#
#   spikes/s14_docker_local.sh build   builds alfabeta-s14:local (linux/amd64, Google Chrome)
#   spikes/s14_docker_local.sh run     one sign-in and one read in a throwaway container
#
# The account comes from the student's config and the password from the keychain item the family
# stored (`security add-generic-password -s alfabeta-classroom -a s1 -w`). Both reach the container
# as environment variables passed by name (`-e NAME`), so neither is on any command line; the
# container keeps nothing (--rm) and its log is stdout.
set -eu
HERE="${0:A:h}"
STUDENT="${S14_STUDENT:-s1}"
IMAGE=alfabeta-s14:local

case "${1:-}" in
  build)
    docker build --platform linux/amd64 -t "$IMAGE" -f "$HERE/s14-cloud/Dockerfile" "$HERE"
    ;;
  run)
    S14_ACCOUNT="$(uv run -q --project "${HERE:h}" python -c \
      'import pathlib, sys, tomllib; p = pathlib.Path.home() / ".alfabeta" / sys.argv[1] / "config.toml"; print(tomllib.loads(p.read_text())["classroom"]["account"].strip())' \
      "$STUDENT")"
    S14_PASSWORD="$(security find-generic-password -s alfabeta-classroom -a "$STUDENT" -w)"
    export S14_ACCOUNT S14_PASSWORD
    docker run --rm --platform linux/amd64 -e S14_ACCOUNT -e S14_PASSWORD "$IMAGE"
    ;;
  *) print -u2 "usage: $0 build|run"; exit 2;;
esac
