# Quickstart: validating spec 001

Scenarios that show the epic works, from what does not need Classroom to what does. The
contracts are in [contracts/](contracts/) and the entities in [data-model.md](data-model.md).

## Prerequisites

- macOS with `uv`, Node and Git.
- For scenarios 6 to 9: the Claude desktop app, Chrome with the Claude extension signed in to the
  student's school account, and Google Drive for desktop with the family Drive account mounted.

## 1. Quality gates (no Classroom)

```bash
make setup-python setup-node
make ci
```

Expected: ruff, Pyright, `pytest` (with more than zero tests collected), the extractor's `node --test` and the
guardrail green, each one named in the output.

## 2. US1 with an invented student (no Classroom)

```bash
export ALFABETA_SANDBOX=$(mktemp -d)
uv run python -m alfabeta --home "$ALFABETA_SANDBOX" sandbox prepare
export ALFABETA_RUN=$(uv run python -m alfabeta --home "$ALFABETA_SANDBOX" lock take --student sample --mode interactive | python3 -c 'import json,sys;print(json.load(sys.stdin)["run"])')
uv run python -m alfabeta --home "$ALFABETA_SANDBOX" sandbox download --student sample --captures
uv run python -m alfabeta --home "$ALFABETA_SANDBOX" downloads collect --student sample
uv run python -m alfabeta --home "$ALFABETA_SANDBOX" plan --student sample
uv run python -m alfabeta --home "$ALFABETA_SANDBOX" sandbox download --student sample
uv run python -m alfabeta --home "$ALFABETA_SANDBOX" downloads collect --student sample
uv run python -m alfabeta --home "$ALFABETA_SANDBOX" apply --student sample
uv run python -m alfabeta --home "$ALFABETA_SANDBOX" lock release --student sample
```

`sandbox prepare` leaves the invented captures in `sandbox-captures/` and the attachments in `sandbox-attachments/`,
both outside the downloads. `lock take` returns the `run` we export;
`sandbox download --captures` leaves the captures in the downloads with that `run` (what the extractor leaves in a
real run) and the first `downloads collect` takes them and fixes the scope; `sandbox download` copies to the downloads, after the
plan, the attachments it requests (what Claude does), and the second `downloads collect` collects them. If the plan
spreads downloads over batches, `sandbox download --batch N` and `downloads collect` for each batch. Expected: `2026-2027/<subject>/<Tema NN - title | Tema PNN - title | YYYY-MM>/classroom/` with
materials `YYYY-MM-DD - <title>`, assignment folders with `enunciado - <name>` and `enlaces.md` notes;
every item of the capture in its place or noted with link and reason (SC-001).

## 3. US2: the agenda (no Classroom)

After scenario 2: `2026-2027/agenda.md` opens with «Pendiente» (nearest first, undated at the
end), continues with «Hecho» and ends with «Publicado» (material and announcements); the exam announced in the sample stream, whose proposal `sandbox prepare` seeds, appears as
detected with a link (SC-004a); `agenda.json` is valid against `contracts/agenda.schema.json`. With `lock take --mode interactive` (exporting its `run` as in scenario 2) /
`lock release` around it, correct the exam with `decisions correct … --date <other>` and apply
again: the agenda keeps the correction.

## 4. US3: repeating with no changes and with changes (no Classroom)

- Repeat on the same `$ALFABETA_SANDBOX` the commands of scenario 2 from `lock take` to
  `lock release` (`sandbox download --captures` leaves the captures again with the new `run`): the summary says «sin cambios», `apply`'s JSON counts
  the sample classes (not zero), and `find "$ALFABETA_SANDBOX/drive" -newer <marker>` is empty (SC-002). The repeated captures carry the
  same `captured_at`; the case of another `captured_at` with no dates in between is tested by T051. That
  the agenda does not depend on the day is tested by T045 with a simulated "today", without changing the system clock.
- In the capture in `sandbox-captures/`, move a due date and set a later «Última modificación» (Last modified) on a
  material; replace its attachment in `sandbox-attachments/` with other content; repeat scenario 2: the
  agenda shows the new date and `<name> (anterior YYYY-MM-DD)` remains (SC-003).
- Remove an item from a capture marked `complete: false`: nothing is withdrawn; with `complete: true`
  it is marked withdrawn and the replica stays.

## 5. US5: configuration and guardrail (no Classroom)

- Remove a key from the sample `config.toml` → `config check` exits with 1 and names the key, not its
  value.
- Create a second invented student with `sandbox prepare --student sample2` and sync it with the commands of
  scenario 2 → `git status` unchanged
  (SC-006) and separate folders.
- Add to a staged file an email and a macOS user path, both invented →
  `uv run python -m alfabeta guardrail --staged` exits with 1 and names file and line without repeating the
  value (SC-007). In a clone with no local configurations the guardrail warns on stderr and goes on with the
  generic detectors.

## 6. Spike S1: downloading a Drive attachment

With a real material of the student, try the methods of research R4 in order and record the first one that
leaves the complete file in the downloads folder. `downloads collect` must move it and verify it.

## 7. Spike S2: scheduled task with a browser

Create a test scheduled task in the app that opens Classroom in Chrome, reads the title of the
page and downloads a capture and an attachment. Record whether it can use the browser and whether it downloads without
anyone approving anything. If not, the scheduled run stays in the reduced mode of FR-021a.

## 8. Spike S3: real structure and synthetic pages

Save the real pages of a class in `data/raw-captures/`, generate their synthetic versions
with `anonymize`, run the guardrail over them before adding them to `tests/fixtures/classroom/`,
check that reading the detail page of a question changes nothing in «Tu trabajo» (Your work), and record
how long a full class takes.

## 9. Real sync of one subject

Ask Claude «sincroniza alfabeta para <student>, solo <subject>» ("sync alfabeta for <student>, only <subject>"). Check:

- Kill the run midway: after `lock_idle_minutes` the lock is released and the log
  has a `stopped` line with reason `idle`.
- No status change in Classroom (SC-008): the «Tu trabajo» panel of the assignments stays the same.
- Every item of «Trabajo de clase» (Classwork) is in its folder or noted with link and reason (SC-001).
- The unmatched teacher's topics wait in their month folder and the summary asks for confirmation.
- An exam announced in the stream appears in `agenda.md` as «detectado» with a link.
- `grep` for the student's name and email in `~/.alfabeta/<student>/data/log.jsonl` finds
  nothing (SC-009).
- With the book: `book place` leaves the Science Bits topic in `<topic>/sciencebits/` next to
  `classroom/` (SC-005).
