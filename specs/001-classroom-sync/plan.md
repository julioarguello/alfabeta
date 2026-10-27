# Implementation Plan: Each subject's content, from Classroom to the family's Drive

**Branch**: `docs/1-spec-001-classroom-sync` | **Date**: 2026-10-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-classroom-sync/spec.md`

## Summary

A `classroom-sync` skill that Claude follows in the desktop app, on demand or as a daily scheduled
task. Claude opens Classroom in Chrome with the student's school session and runs a read-only
JavaScript extractor that downloads what it sees as JSON. A deterministic Python command
(`python -m alfabeta`) turns those captures into a plan, collects the attachment downloads, places
the replicas in the student's folder inside the mounted family Drive and regenerates the agenda.
Claude contributes judgement only where it is needed (matching the teacher's topics to the book's,
detecting exams in announcements), and what the family confirms is stored so it is never decided
again. The Science Bits skill moves to the same configuration and structure.

## Technical Context

**Language/Version**: Python 3.12 (package and command); browser JavaScript (extractor).

**Primary Dependencies**: none at runtime (standard library: `tomllib`, `json`, `zoneinfo`,
`hashlib`, `argparse`, `fcntl`). Development: `uv`, `ruff`, strict `pyright`, `pytest`, `jsonschema`
(to validate contracts in tests); Node with `jsdom` only to test the extractor.

**Storage**: files. Per-student TOML configuration in `~/.alfabeta/<student>/config.toml`; JSON
decisions, JSON state, JSON Lines log, lock, plan and captures in `~/.alfabeta/<student>/data/`;
replicas and agenda in the student's folder inside the Drive mounted by Google Drive for desktop.

**Testing**: `pytest` (unit and contract, against synthetic pages and captures); `node --test` with
`jsdom` for the extractor; the guardrail with cases in both directions. No test calls Classroom.

**Target Platform**: macOS with the Claude desktop app, Chrome with the Claude extension, and Google
Drive for desktop.

**Project Type**: Claude skills + one local command-line command.

**Performance Goals**: no speed target of its own; the limit is browsing as a student does, one class
at a time. The duration of the first sync (the whole school year) is measured in spike S3.

**Constraints**: read-only on Classroom; no student data in URLs, the log or the repository;
idempotent writes; scheduled runs need no intervention except for an expired session, a challenge,
an unmounted Drive or pending decisions.

**Scale/Scope**: one student (designed for several), about 12 classes, hundreds of items per school
year.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How the plan meets it | Status |
|---|---|---|
| I. The student is configuration | `--student <id>` (an opaque alias) selects a folder `~/.alfabeta/<id>/`; the code knows no students, schools, school years, grade levels or accounts. Science Bits' existing `build.py` defaults to a specific grade level, subject and topic: T057 removes those defaults and makes their configuration mandatory | Temporary exception until T057 (see Complexity Tracking) |
| II. Three layers that never mix | `config/template.toml` in the repo; `config.toml` outside it; decisions, state and other data in `data/`; keys validated against the template; guardrail in pre-commit and CI with a self-test | Pass |
| III. Minors' data | Nothing personal in URLs (the account is located by its `/u/<n>` index, comparing the email locally), in the log (opaque ids, relative paths, never the absolute path of the root) or in the repository: test pages are synthetic (only the structure of the real ones; every text and attribute invented). Classmates' comments and names are not stored. The student's grades, gradings and submissions are stored because they are study material, and they go to a family folder, not to third parties | Pass |
| IV. Read-only on the school's platforms | The extractor only reads the DOM; it navigates only to the home page, «Trabajo de clase» (Classwork), the stream and the detail page; it never follows forms or quizzes and never clicks the «Tu trabajo» (Your work) panel (a `jsdom` test checks this); it detects anti-bot challenges and stops; at least 2 s between pages. Reading a question's detail page is not opening a quiz: opening one means answering it or following its form, and S3 checks that reading it changes nothing (if it did, questions are read from the listing only) | Pass |
| V. Idempotent, incremental sync | Classroom identifier per item, hash per replica, comparison before writing (the agenda too, which does not depend on the day), previous versions kept, nothing deleted, a per-student lock and a lock on the Mac's browser with `fcntl.flock` for the whole run, renewed at every step and released only on idle. A run's captures, plan and log line are its own record (the exception V allows); state and decisions are not rewritten unless they change, and the date of the last full review is taken from the log, not from the state | Pass |
| VI. One source, one isolated and tested provider | A shared `Source` port: `ClassroomSource` (captures) and `BookSource` (a book provider's directory); the subfolder comes from the source's name; adding another book touches neither `placement` nor `replicas`. Classroom extractor tested with `jsdom` on synthetic pages and the logic with `pytest`. Recorded exception: Science Bits' existing extractors remain untested (Complexity Tracking) | Pass with recorded exception |
| VII. Every output is optional and degrades on its own | The Drive folder is the base output; the calendar is left for epic 2. The Science Bits notebook stays as it is today (enabled or not by configuration), and its result, a failure included, is logged with `log notebook`; if it fails, what was placed in the Drive is not touched | Pass |
| VIII. Local time, always `Europe/Madrid` | A single date resolver with `zoneinfo`; year inferred from the school year; tests across clock changes and year changes | Pass |
| IX. Simplicity | No runtime dependencies (runtime capture validation checks keys by hand); files instead of a database; `jsonschema`, Node and `jsdom` only in development (see Complexity Tracking); `uv`, already adopted for the environment, only prepares the environment and launches the command on the Mac, with no new libraries | Pass with justification |

Re-evaluated after Phase 1 and after the first `/speckit-analyze` (2026-10-25): III, IV, V, VI and IX
corrected as above.

## Project Structure

### Documentation (this feature)

```text
specs/001-classroom-sync/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   ├── config-template.toml
│   ├── capture.schema.json
│   └── agenda.schema.json
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
pyproject.toml   uv.lock   .python-version   pyrightconfig.json   Makefile   package.json
CONTRIBUTING.md
config/
└── template.toml                   # the only configuration layer in the repo
.githooks/pre-commit                # calls the guardrail
src/alfabeta/
├── __main__.py                     # command and subcommands (contracts/cli.md)
├── config.py                       # loading and validation against the template; student paths
├── decisions.py                    # proposals, confirmations, corrections and changes
├── dates.py                        # year from the school year, relative dates against the capture, Europe/Madrid
├── model.py                        # domain dataclasses
├── sources.py                      # Source Protocol; ClassroomSource and BookSource
├── capture.py                      # reads, checks and normalises the extractor's captures
├── classification.py               # each item's category and exam candidates
├── placement.py                    # year/subject/dated topic/source and dated file names
├── state.py                        # JSON state, JSON Lines log, lock with fcntl.flock
├── plan.py                         # sources ↔ state diff: what to download, write, decide
├── downloads.py                    # collection from the downloads folder and verification
├── replicas.py                     # placing replicas, grades, gradings, previous versions
├── agenda.py                       # agenda.json and agenda.md («Pendiente» and «Hecho»)
├── anonymize.py                    # synthetic pages built from the structure of the real ones
├── book.py                         # `book place`
├── sandbox.py                      # `sandbox prepare` and `sandbox download`: invented student for tests and the quickstart
├── guardrail.py                    # personal-data detector with a self-test
└── schemas/                        # capture and agenda (copies of contracts/) for tests and documentation
skills/
├── classroom-sync/
│   ├── SKILL.md                    # the flow Claude follows and its prohibitions
│   └── scripts/extract.js          # read-only extractor
└── sciencebits-a-notebooklm/       # moves to per-student configuration and to `book place`
tests/
├── fixtures/classroom/             # synthetic pages + invented JSON captures
├── js/extract.test.mjs             # extractor against the synthetic pages
└── test_*.py                       # one per module, plus guardrail and contracts
.github/workflows/ci.yml            # autofix (non-blocking) + quality-gate (blocking): make ci
```

**Structure Decision**: a single project. One package in `src/` holds the deterministic logic shared
by both skills, which contain only the `SKILL.md` and the browser JavaScript. `src/` and `tests/` are
under ruff and Pyright with no exceptions; the `classroom-sync` JavaScript under `node --test`. The
scripts the Science Bits skill already has stay outside those gates in this epic (Complexity
Tracking).

## Class design (by layer)

Facts the design starts from (detail in [research.md](research.md#observed-facts)):

| Fact | Where it comes from |
|---|---|
| A task's reliable status is on its detail page, not in the listing | Observed 2026-10-25, the student's Classroom, read-only |
| The teacher's topics and the book's do not match one to one | Observed 2026-10-25, «Trabajo de clase» (Classwork) of a subject with a book |
| Dates carry no year and may be relative | Observed 2026-10-25, «Trabajo de clase» of two subjects |
| The detail URL carries stable class and item ids | Observed 2026-10-25, address bar |
| The listing shows «Última modificación» (Last modified) when an item is edited | Observed 2026-10-25, «Trabajo de clase» |
| Attachments link to `drive.google.com`; the direct download failed | Observed 2026-10-25 and an earlier test in issue #1 |
| Exams are announced on the stream, in the class's language | Observed 2026-10-25, stream of a subject with a book |
| The Classroom UI of the student's account is in Spanish | Observed 2026-10-25, every page visited |
| The extension hides base64-looking values in its output | Observed 2026-10-25, output of the JavaScript tool |

| Layer | Name | Responsibility |
|---|---|---|
| Browser | `extract.js` | Reads the class list, topics, items, detail (status, dates, modification mark, attachments, submission, grading) and stream as displayed; marks the capture as complete or not; detects anti-bot challenges and unexpected UI labels; waits ≥2 s between pages; downloads the result as JSON |
| Browser | Claude + `SKILL.md` | Locates the school account, runs the extractor, downloads attachments according to the plan, proposes matches (with confidence) and exams |
| Domain | `Student`, `Subject`, `Item`, `Attachment`, `Replica`, `AgendaEntry`, `Grading`, `Decision`, `Run` | Immutable dataclasses (see data-model) |
| Domain | `Classifier` | Closed category with precedence, and exam candidates from cues |
| Domain | `Placer` | Folder and name of each replica from school year, subject, confirmed match, teacher's topic or `Sin tema`, source and role; finds an existing topic folder by the name after its `YYYYMMDD - ` prefix |
| Domain | `DateResolver` | Absolute date in `Europe/Madrid` from the displayed text, the school year and the capture time |
| Ports | `Source` | Protocol: `name` (the subfolder) and normalised `items()` for `Planner`; implementations `ClassroomSource` (captures) and `BookSource` (a book provider's directory) |
| Ports | `StateStore`, `DecisionStore`, `StudentFolder`, `DownloadsInbox` | Protocols: state and decisions, writing to the Drive folder, collection from the downloads folder |
| Services | `Planner` | Sources + state + decisions → plan (requested downloads, replicas to write, pending decisions) |
| Services | `Applier` | Plan + collected downloads → replicas, grades, gradings, previous versions, state and log |
| Services | `AgendaBuilder` | State + decisions → `agenda.json` and `agenda.md`, rewritten only if they change |
| Adapters | JSON files, mounted folder, downloads folder | Implement the ports with atomic writes |
| Entry point | `python -m alfabeta` | Resolves the student once, validates the configuration, takes or checks the lock and calls the services |
| Gate | `Guardrail` | Personal-data detectors, self-test and exit codes 0/1/2/3 (contracts/cli.md) |
| Gate | `Anonymizer` | Turns a real page into a synthetic one: keeps tags, CSS classes and UI labels from an allowlist, and invents every remaining text and attribute; refuses to write if any input text outside that list survives |

## Run flow

1. `python -m alfabeta lock take --student <id> --mode <interactive|scheduled>` (its `run` goes in
   `ALFABETA_RUN` on every later command) and `config check --student <id>`: the student's and the
   browser's locks taken for the whole run, valid configuration, Drive mounted. If `lock take` fails,
   it writes its own line; if anything else fails, `log stop` with its reason and a notice to the
   family. Every command runs on the Mac with
   `uv run --project <tools.repository> python -m alfabeta`, and the skill calls `downloads collect`
   after the class list, after each class and after each batch of downloads (every command renews
   the lock; `lock renew` is for long waits).
2. Claude opens Classroom in Chrome, locates the school account by its index and checks the session
   and the UI language. If the session expired, there is a challenge or the UI is not the expected
   one, `log stop` with its reason and a notice (FR-021a).
3. It captures the class list; `downloads collect` and `plan` give the unlinked classes. Claude
   proposes their links with `decisions propose`; in an interactive run the family confirms them on
   the spot, in a scheduled run they stay pending and those classes are not synced yet.
4. For each linked class, it runs `extract.js` with the current `run`, which downloads the capture;
   `downloads collect` moves it to `data/captures/`. If the session expires midway, a challenge
   appears or the UI is not the expected one, the extractor downloads a `stop` capture with `class`
   and the flow jumps to step 7 with the classes already captured (`partial`).
5. `plan --student <id>`: writes `data/plan.json` with the downloads needed, the pending decisions and
   what would change. Claude proposes matches and detected exams (with reason and confidence); in an
   interactive run the family confirms the matches, and detected exams enter the agenda without
   confirmation.
6. Claude downloads each requested attachment (the method from spike S1), in the plan's batches and
   with at least 2 s between downloads; `downloads collect` after each batch verifies them.
7. `apply --student <id>`: recomputes the targets with the decisions in force, places replicas,
   updates state and log, regenerates the agenda if it changes and prints the summary for the
   family. `lock release` at the end; if the run dies, the lock is released on idle.

## Science Bits in the same structure (FR-022, FR-023)

- The skill reads `~/.alfabeta/<student>/config.toml` instead of `~/.alfabeta/config.json`:
  `[[subjects]]` with `book = "sciencebits"` and `book_class`, the school year from `[student]`,
  `[sciencebits] url`, `[tools] folder` (instead of the tools folder in Dropbox) and `[notebook]`
  (instead of `notebook.*`). No key outside the template, and the skill never writes to the
  configuration: if it is missing or invalid, `config check` and stop.
- It takes the student's and the browser's lock (`lock take --mode interactive`, or `scheduled` if a
  scheduled task launches it) before opening Science Bits and releases it when done, so it never
  overlaps a Classroom sync in the browser or in the downloads (FR-030).
- "The next topic" comes from the folders whose name contains `Tema NN`, whatever their
  `YYYYMMDD - ` prefix, that already have `sciencebits/` in the Drive; nothing needs adding to the
  configuration.
- Its result (`TemaNN_<LANG>.pdf` and `.md`) is still generated as today in the working folder under
  Downloads, and `book place` moves it through `BookSource` to
  `<school-year>/<subject>/<YYYYMMDD> - <Tema NN - title>/<book>/` inside the Drive root (the subfolder is
  the value of `book`), with the same hash and previous-version rules as Classroom. It reuses the
  existing folder whose name contains `Tema NN - `, whatever its date; only if there is none does it
  create one dated today.
- It neither reads nor writes Dropbox; what was captured there before stays as it is.
- The Gemini Notebook notebook stays as today, enabled or not with `[notebook] enabled`, until
  epic 3. In the `nlm` step the skill lists the notebook's sources and adds only the missing ones
  (constitution V: repeating a topic does not duplicate sources). After that step, the skill calls
  `log notebook` with its result (`created`, `unchanged`, `failed` with a reason, or `disabled`): a
  notebook failure does not undo what was placed and shows in the log (constitution VII).

## Spikes before the implementation tasks

- **S1 · Downloading Drive attachments** from Chrome with the school account: the three methods in
  research R4, with a real attachment. Output: the method and its manual test in the quickstart.
- **S2 · Scheduled task with browser and downloads**: a scheduled task of the app that opens Chrome
  with the extension, reads Classroom's title and downloads a file (a capture and an attachment)
  without anyone approving anything at that moment. If it cannot, the scheduled run stays in the
  reduced mode FR-021a allows (a notice, and a sync launched with the single command).
- **S3 · Real structure and synthetic pages**: save a class's real pages outside the repository,
  generate their synthetic versions with `anonymize`, check with the guardrail that nothing real
  remains, check that a question's detail page can be read without creating state, and measure how
  long a whole class takes.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Node and `jsdom` as development dependencies (IX) | The constitution requires testing every extractor against saved pages, and the extractor is JavaScript | Reimplementing the extraction in Python would duplicate the logic and would not test the code that runs in the browser |
| `jsonschema` as a development dependency (IX) | Tests check captures and agendas against the full contracts | Checking the whole schema by hand in the tests would repeat the contract in code; at runtime the essential keys are checked by hand, with no dependency |
| Defaults for a specific grade level, subject and topic in Science Bits' existing `build.py` (I), until T057 | They have been on `main` since before this spec; T057, in the US4 phase, removes them | Removing them in the spec PR would mix code into a documentation-only PR (Development workflow) |
| Science Bits' existing extractors and scripts without tests or quality gates (VI, Development workflow) | This epic changes only where that skill reads its configuration from and where it places its result; testing its capture needs synthetic Science Bits pages | Doing it here would double the epic's scope. It stays as a follow-up issue ("tests and gates for the Science Bits skill"), opened together with this spec's issues |
