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
spreads downloads over batches, `sandbox download --batch N` and `downloads collect` for each batch. Expected: `2026-2027/<subject>/<YYYYMMDD> - <Tema NN - title | teacher's title | No topic>/classroom/` with
materials `YYYYMMDD - <title>`, assignment folders with `enunciado - <name>` and `enlaces.md` notes;
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

Create a test scheduled task in the app that opens Classroom in Chrome from inside a Classroom tab
(never with the extension's `navigate`, research R16), reads the title of the page and downloads a capture and an attachment. Record whether it can use the browser and whether it downloads without
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
- The unmatched teacher's topics wait in their own `<YYYYMMDD> - <teacher's title>` folder and the summary asks for confirmation.
- An exam announced in the stream appears in `agenda.md` as «detectado» with a link.
- `grep` for the student's name and email in `~/.alfabeta/<student>/data/log.jsonl` finds
  nothing (SC-009).
- With the book: `book place` leaves the Science Bits topic in `<topic>/sciencebits/` next to
  `classroom/` (SC-005).

## 10. Spikes S4 to S6: the unattended runner (User Story 7)

Before anything of User Story 7 is built, and recording each result in research R15 to R18 with no
title, name or identifier:

- S4 (token route, primary): seed a first-party sign-in token by hand, and from a test job exchange
  it for a read-only access token and make one read-only Classroom call. Pass if it returns the
  student's work; record whether the device shows as new and whether a home address differs from the
  cloud one. On pass, this is the route and S5/S6 are not needed to build.
- S5 (web route, fallback): for 14 days, read the to-do page twice a day from the cloud project and,
  with a second session, from a home address, behind a minimal guard (page-load allowlist, zero
  presses). Record each «Demuestra que eres tú» with the session's age. Pass if it reads without
  evasion and the family would sign in at most once a week (SC-012).
- S6 (web route): record the background requests of a to-do read and a detail read (method, host,
  path, call name; never bodies or cookies), and check that the browser-level guard blocks a planted
  press (one fired by the page's own `extract.js` included) and a planted call on a local fake page.

## 11. The runner with nobody present (no Classroom, then one real week)

With the local fake Classroom of the runner's tests, run `runner read --student sample` and check:

- The agenda lists every item of the synthetic «Tareas pendientes» and «Sin entregar», each with the
  due date of its detail page resolved against that page's `seen_at` (SC-011).
- A planted form link, a planted «Entregar» and a planted unknown call are blocked and counted in
  the log's `blocked`, and the fake server received none of them (SC-013).
- Serving the fake sign-in page the web route cannot clear ends the run with `session_expired`
  within one page's time limit and exit 1; a second run with the same secret version exits 0 without
  reaching Classroom (SC-014). A fake CAPTCHA ends it with `challenge`.
- A `click` on the planted «Entregar» and a `submit()` fired by the page's own `extract.js` are both
  cancelled by the browser-level guard, not by the driver (SC-013).
- An address planted in a sign-in redirect URL and in the account button appears in no log, stdout,
  stderr or the notice (SC-009).

Then, with the runner enabled for the real student and the operator's Mac off, for one school week:
every assignment «Tareas pendientes» showed before each scheduled run is in the agenda in Drive after
it (SC-011), and «Tu trabajo» of every assignment is unchanged (SC-008).
