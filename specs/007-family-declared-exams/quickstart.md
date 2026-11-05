# Quickstart: checking spec 007 on the sandbox, then for real

The commands of steps 1 to 3 run on the invented student of `sandbox prepare`, in a scratch `--home`. Nothing
below belongs in an issue or a pull request except counts: no title, no date of the real student.

## Prerequisites

- The slice under test is merged, and `make setup-python` has run.
- `H=$(mktemp -d)`, then `uv run python -m alfabeta --home "$H" sandbox prepare`.
- A run's lock for steps 2 and 3: `export ALFABETA_RUN=$(uv run python -m alfabeta --home "$H" lock take --student <id> --mode interactive | python3 -c 'import json,sys;print(json.load(sys.stdin)["run"])')`. Release it with `lock release` at the end.

## 1. Preparing with nothing declared (slice 1)

The refusals and the requests are covered by `tests/test_exam_prep.py` with the stand-in for `nlm`:

```bash
uv run pytest tests/test_exam_prep.py -q
```

On the real notebook, a family step, with an exam that has no announcement:

```bash
uv run python -m alfabeta exam build --student <id> --subject <folder> --topic <folder>
```

Expected: two PDFs in the topic's `exam/` folder, named `(sin fecha)`, or with the date if the agenda holds one.
The family reads, and records as a count only (SC-010): how many of the scheme's top-level branches have a section,
that the first page of both says no announcement backs them, and that the problems sheet holds only the sources' problems or says it has none. The agenda's bytes do not change.

## 2. Declaring, correcting, cancelling (slice 2)

```bash
uv run python -m alfabeta --home "$H" exam create --student <id> --subject <folder> --date YYYY-MM-DD
```

Expected: `created: true`, `item: declared-1`, and a line in `agenda.md` under «Pendiente» reading «declarado por la
familia» with no Classroom link. The same command again gives `created: false` and no byte changes.

```bash
uv run python -m alfabeta --home "$H" decision update-exam --student <id> --origin declared-1 --date YYYY-MM-DD
```

Expected: the same line, moved, also reading «corregido». Then:

```bash
uv run python -m alfabeta --home "$H" decision update-exam --student <id> --origin declared-1 --discard
```

Expected: the line is gone, and the record stays in `data/decisions.json`.

## 3. The teacher posts it (slice 2)

Covered with invented captures by `tests/test_declared.py`: an assignment titled as a
test, a stream post and a material on the declared day give one line (SC-003); with matching disabled, two.

On the real student, after the next sync with a teacher's post: count the exam lines of that subject; expected one.

## 4. The writer (slice 3)

With spec 003 slice 3 built, `calendar replay` over an agenda with a declared exam shows one event, `Declarado por la
familia` in its description, reminders per spec 003 FR-015. A date correction moves the same event, and a cancellation
turns it «Retirado ·». The first `calendar sync --student <id> --apply` prints `hand_events`, a count. The family then
deletes those events by hand, and nothing else touches them.
