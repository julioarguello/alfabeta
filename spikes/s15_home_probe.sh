#!/bin/zsh
# Issue 263 (research S15): one load of Classroom's home page in the read image, signin false, no
# password. Run only with a live session in the read profile and no read running (lock released).
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$HERE/s15-out"
IMG=$(docker images alfabeta-classroom-read --format '{{.Repository}}:{{.Tag}}' | head -1)
python3 -c 'import tomllib,json,os;c=tomllib.load(open(os.path.expanduser("~/.alfabeta/s1/config.toml"),"rb"));print(json.dumps({"account":c["classroom"]["account"],"mode":"home"}))' \
 | docker run --rm -i --name alfabeta-probe-263 --platform linux/amd64 \
   -v "$HOME/.alfabeta/s1/data/classroom-profile:/profile" \
   -v "$HOME/.alfabeta/s1/data/captures:/captures:ro" \
   -v "$HERE/s15-out:/out" -v "$HERE/s15_home_probe.py:/probe.py:ro" \
   --entrypoint python "$IMG" /probe.py
