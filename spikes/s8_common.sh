# Sourced: the read image, the account as JSON (never printed), and a stop if a read is running.
IMG=$(docker images alfabeta-classroom-read --format '{{.Repository}}:{{.Tag}}' | head -1)
ACCOUNT=$(python3 -c 'import tomllib,json,os;c=tomllib.load(open(os.path.expanduser("~/.alfabeta/s1/config.toml"),"rb"));print(json.dumps(c["classroom"]["account"]))')
if [ -n "$(docker ps -q --filter name=alfabeta)" ] || [ -f ~/.alfabeta/s1/data/lock.json ]; then echo "busy: a read is running"; exit 1; fi
