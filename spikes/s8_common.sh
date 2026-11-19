# Sourced: the student (STUDENT, required), its data folder, the read image, the account as JSON (never
# printed), and a stop if a read is running for that student.
: ${STUDENT:?set STUDENT to the student id, as in ~/.alfabeta/<id>}
HOME_DIR="$HOME/.alfabeta/$STUDENT"
DATA="$HOME_DIR/data"
IMG=$(docker images alfabeta-classroom-read --format '{{.Repository}}:{{.Tag}}' | head -1)
ACCOUNT=$(STUDENT_HOME="$HOME_DIR" python3 -c 'import tomllib,json,os;c=tomllib.load(open(os.environ["STUDENT_HOME"]+"/config.toml","rb"));print(json.dumps(c["classroom"]["account"]))')
if [ -n "$(docker ps -q --filter name=alfabeta-classroom-read)" ] || [ -f "$DATA/lock.json" ]; then echo "busy: a read is running"; exit 1; fi
