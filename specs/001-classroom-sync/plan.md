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

Amended 2026-10-27 (User Story 7): for a student with the unattended runner enabled, the scheduled
read of Classroom leaves the Mac. A container job in the family's cloud project (or on a home
device), started at the `[schedule]` times, signs in with a secret the family seeded by hand in the
project's vault, and reads one of two ways settled by a spike: the **token route** (primary), a
first-party sign-in token exchanged for read-only access tokens to read Classroom through the API;
or the **web route** (fallback), a headless Chromium with Playwright that loads the stored session,
signs in again by a deterministic script when it has expired, and runs `extract.js` in a `todo` mode
behind a browser-level read-only guard. Either way it feeds the same deterministic command (`plan`,
`apply` (unattended, from the lock), `agenda`) on the student's single data home — a state folder in the student's Drive (constitution II/VII) — and the agenda goes to Drive through spec 004's connection. Nothing in it is
Claude; constitution III is amended (MAJOR, 2.0.0) to permit the vault; and it is built only after
its spikes pass (S4 decides the token route; S5 decides the web route, and S6 only settles how
precise the web guard's background-call allowlist can be, not whether to build).

## Technical Context

**Language/Version**: Python 3.12 (package and command); browser JavaScript (extractor).

**Primary Dependencies**: none at runtime (standard library: `tomllib`, `json`, `zoneinfo`,
`hashlib`, `argparse`, `fcntl`). Development: `uv`, `ruff`, strict `pyright`, `pytest`, `jsonschema`
(to validate contracts in tests); Node with `jsdom` only to test the extractor. The unattended
runner (User Story 7) adds runtime dependencies of its own, in its container image only (Complexity
Tracking): Playwright for Python with its Chromium for the web route, and, if spike S4 shows the
first-party token exchange cannot be done with the standard library alone, a token-exchange library
(e.g. `gpsoauth`) for the token route. It reaches Secret Manager and the student's Drive (the data home, R19) over their REST APIs with the standard library, as spec 004 does for Google's.

**Storage**: files. Per-student TOML configuration in `~/.alfabeta/<student>/config.toml`; JSON
decisions, JSON state, JSON Lines log, lock, plan and captures in `~/.alfabeta/<student>/data/`;
replicas and agenda in the student's folder inside the Drive mounted by Google Drive for desktop.

**Testing**: `pytest` (unit and contract, against synthetic pages and captures); `node --test` with
`jsdom` for the extractor; the guardrail with cases in both directions. No test calls Classroom.

**Target Platform**: macOS with the Claude desktop app, Chrome with the Claude extension, and Google
Drive for desktop. For User Story 7, also a Linux container run as a Cloud Run job in the family's
cloud project, started by Cloud Scheduler (research R17).

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
| I. The student is configuration | `--student <id>` (an opaque alias) selects a folder `~/.alfabeta/<id>/`; the code knows no students, schools, school years, grade levels or accounts. Science Bits' `build.py` takes the topic's texts only from its mandatory `--config` (T057, #10) | Pass |
| II. Three layers that never mix | `config/template.toml` in the repo; `config.toml` outside it; decisions, state and other data in `data/`; keys validated against the template; guardrail in pre-commit and CI with a self-test | Pass |
| III. Minors' data | Nothing personal in URLs (the account is located by its `/u/<n>` index, comparing the email locally), in the log (opaque ids, relative paths, never the absolute path of the root) or in the repository: test pages are synthetic (only the structure of the real ones; every text and attribute invented). Classmates' comments and names are not stored. The student's grades, gradings and submissions are stored because they are study material, and they go to a family folder, not to third parties | Pass |
| IV. Read-only on the school's platforms | The extractor only reads the DOM; it navigates only to the home page, «Trabajo de clase» (Classwork), the stream and the detail page; it never follows forms or quizzes and never clicks the «Tu trabajo» (Your work) panel (a `jsdom` test checks this); it detects anti-bot challenges and stops; at least 2 s between pages. Reading a question's detail page is not opening a quiz: opening one means answering it or following its form, and S3 checks that reading it changes nothing (if it did, questions are read from the listing only) | Pass |
| V. Idempotent, incremental sync | Classroom identifier per item, hash per replica, comparison before writing (the agenda too, which does not depend on the day), previous versions kept, nothing deleted (the mirrors are never pruned: `rsync` without `--delete`, which writes nothing to a mirror already up to date), a per-student lock and a lock on the Mac's browser with `fcntl.flock` for the whole run, renewed at every step and released only on idle. A run's captures, plan and log line are its own record (the exception V allows); state and decisions are not rewritten unless they change, and the date of the last full review is taken from the log, not from the state | Pass |
| VI. One source, one isolated and tested provider | A shared `Source` port: `ClassroomSource` (captures) and `BookSource` (a book provider's directory); the subfolder comes from the source's name; adding another book touches neither `placement` nor `replicas`. Classroom extractor tested with `jsdom` on synthetic pages and the logic with `pytest`. Recorded exception: Science Bits' existing extractors remain untested (Complexity Tracking) | Pass with recorded exception |
| VII. Every output is optional and degrades on its own | The Drive folder is the base output and the master of its mirrors; a mirror that fails is counted in the summary and the log and stops neither the master nor the other mirrors (FR-011a). The calendar is left for epic 2, with its `shared_with` list already in the template (FR-011b). The Science Bits notebook stays as it is today (enabled or not by configuration), and its result, a failure included, is logged with `log notebook`; if it fails, what was placed in the Drive is not touched | Pass |
| VIII. Local time, always `Europe/Madrid` | A single date resolver with `zoneinfo`; year inferred from the school year; tests across clock changes and year changes | Pass |
| IX. Simplicity | No runtime dependencies (runtime capture validation checks keys by hand); files instead of a database; `jsonschema`, Node and `jsdom` only in development (see Complexity Tracking); `uv`, already adopted for the environment, only prepares the environment and launches the command on the Mac, with no new libraries | Pass with justification |

Re-evaluated after Phase 1 and after the first `/speckit-analyze` (2026-10-25): III, IV, V, VI and IX
corrected as above.

Re-check for User Story 7 against constitution 2.0.0 (2026-10-27); the principles not listed pass
as above:

| Principle | How the unattended runner meets it | Status |
|---|---|---|
| I. The student is configuration | The runner takes `--student <id>`; its route, secret name and state-folder name come from the student's configuration (`[runner]`, `[schedule]`); the image knows no student | Pass |
| II. Three layers that never mix | The sign-in secret and the Drive credential live in the project's secret store, one set per student; the data home is a state folder in the student's Drive (constitution II/VII, research R19); neither is in the repository or the configuration, which holds only their names (research R15, R19). The secret is readable by the runner's identity, the family and the project's administrators — II (2.0.0) names the project and organisation whose administrators can read it, and the family accepts them (the operator's work organisation, per R17) | Pass |
| III. Minors' data | The family signs in by hand once; no password is typed by Claude; the secret is the minimum for the route; it never reaches a log, an error, Claude's context or a URL; the notice names the opaque `id`. III (2.0.0) permits a vault and a scripted sign-in under limits, which this meets (FR-033). The risks (first-party impersonation for the token route, a scripted sign-in on a minor's account for the web route, and the administrators' access) are named for the family to accept (research R15, R17) | Pass (III amended, risks named) |
| IV. Read-only on the school's platforms | Token route: read-only scope only, and IV (2.0.0) permits this first-party token read with no OAuth client of ours, proven by S4. Web route: a browser-level guard, installed before any page script, cancels presses and blocks loads and form requests outside the exact allowlist, so the page's own `extract.js` cannot press (research R18), tested offline; a sign-in page runs only the permitted scripted sign-in, a challenge a human would clear stops the run; no proxy, no fingerprint change, no second address after a challenge. The web guard's background-call allowlist depends on S6 | Pass (token read under IV's 2.0.0 exception; web route conditional on S6) |
| V. Idempotent, incremental sync | Same command and state on the single data home (FR-035); the lock is a lease in the Drive state folder (research R19); a read that is not complete marks nothing done or withdrawn; a no-change run writes no secret version and no agenda (FR-025) | Pass |
| VII. Every output is optional and degrades on its own | The runner writes no replica and skips the master and mirrors (FR-036); the agenda goes straight to Drive through spec 004's connection and counts only when Drive confirms it; a failed Drive write stops the run `drive_write_failed` and the next run retries | Pass |
| VIII. Local time | Each detail page carries its own `seen_at` (research R5), used for the date and for the overdue decision; the job's time zone is irrelevant because every instant is stored with its offset and resolved in `Europe/Madrid` | Pass |
| IX. Simplicity | The job is the measured need of 2.0.0 (the second named need after spec 005): it starts, reads and ends, in the operator's Google Cloud project for alfabeta, with no server of ours left running; Playwright (web route only) is the one new dependency, in the runner's image only (Complexity Tracking) | Pass with justification |

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
├── dates.py                        # year from the school year, relative dates against each page's read instant (seen_at), Europe/Madrid
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
├── runner/                         # User Story 7, used only in the runner's image
│   ├── browser.py                  # Playwright Chromium, the request guard and the single press function (research R18)
│   ├── session.py                  # load, renew and store the session in Secret Manager; `runner session login` (research R15)
│   ├── home.py                     # the data home in the Drive state folder and its lease (research R19)
│   └── read.py                     # `runner read`: lease, session, todo extraction, plan, apply, agenda, stop and notice
└── schemas/                        # capture and agenda (copies of contracts/) for tests and documentation
runner/
└── Dockerfile                      # the runner's image: Python 3.12, the package, Playwright and its Chromium
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
| Domain | `Placer` | Folder and name of each replica from school year, subject, confirmed match, teacher's topic or `No topic`, source and role; finds an existing topic folder by the name after its `YYYYMMDD - ` prefix |
| Domain | `DateResolver` | Absolute date in `Europe/Madrid` from the displayed text, the school year and the instant the page was read (`seen_at`, falling back to the capture instant); the same instant decides overdue vs pending (H10) |
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
   updates state and log, regenerates the agenda if it changes, brings each mirror up to date
   from the root (`rsync -rlt --exclude .DS_Store <root>/ <mirror>/`, no `--delete`; FR-011a) and
   prints the summary for the family, mirrors included by count. `lock release` at the end; if the run dies, the lock is released on idle.

### Unattended run (User Story 7)

1. Cloud Scheduler starts the runner's job for one student at a `[schedule]` time. `runner read
   --student <id>` takes the lease in the data home (research R19); if it is held, `lock_busy`.
2. It reads the newest version of the student's sign-in secret. None: `stopped` `session_expired`
   against a sentinel version `none`, so the family is told once to seed the vault (later no-secret
   runs repeat `none`, exit 0). The version whose last run already stopped: that reason, exit 0, no
   new notice. Either way nothing is reached.
3. It reads by `runner.route`:
   - **token route**: exchanges the stored token for a read-only access token and makes the
     read-only Classroom calls; `account_blocked` if the API refuses the account.
   - **web route**: starts Chromium with the browser-level guard (research R18, FR-038) and the
     stored session, opens `/u/0/h`, checks the account button locally against `classroom.account`
     and the Spanish labels, then runs `extract.js` in `todo` mode («Tareas pendientes» with each
     collapsed section by its header, «Sin entregar» with «Ver todo», each listed detail and the
     `recheck` items `plan` computes, ≥2 s with jitter, each detail carrying its `seen_at`). A load
     to `accounts.google.com` the scripted sign-in cannot clear is `session_expired`; a CAPTCHA,
     `challenge`; missing labels, `unexpected_ui`; a page past its limit, `timeout`. The capture
     lands in `captures/`.
4. `plan` and `apply` (unattended, from the lock) run with `--home` on the pulled-down copy of the Drive state folder, with nothing to download,
   no replica, and no master or mirror write (H1); `apply` regenerates the agenda and uploads it
   through spec 004's connection with the credential of FR-033a, confirmed by Drive, and only if its
   hash changed (FR-036).
5. It stores the renewed secret as a new version only if it changed, destroys the older ones,
   releases the lease and ends. A stop stores no version and writes its `stopped` (or `partial`)
   line; the job exits 1 the first time a `(reason, version)` appears, which the project's alert
   policy turns into one email to the family, and 0 when it repeats (research R17). Job retries are
   0, with a cooldown after `challenge`.

## Science Bits in the same structure (FR-022, FR-023)

- The skill reads `~/.alfabeta/<student>/config.toml` instead of `~/.alfabeta/config.json`:
  `[[subjects]]` with `book = "sciencebits"` and `book_class`, the school year from `[student]`,
  `[sciencebits] url`, `[tools] folder` (instead of the tools folder in Dropbox), `[drive] mirrors`
  (instead of `storage.mirrors`) and `[notebook]` (instead of `notebook.*`, `share_with` included). No key outside the template, and the skill never writes to the
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
  the value of `book`), with the same hash and previous-version rules as Classroom, and then brings the
  mirrors up to date as `apply` does. It reuses the
  existing folder named `Tema NN - <title>` after its date, whatever the date and the title (of two,
  the one already holding `<book>/`); only if there is none does it create one dated today.
- It neither reads nor writes Dropbox; what was captured there before stays as it is.
- The Gemini Notebook notebook stays as today, enabled or not with `[notebook] enabled`, until
  epic 3. In the `nlm` step the skill lists the notebook's sources, adds only the missing ones and replaces
  the source of a file `book place` placed again because it changed (constitution V: repeating a topic
  does not duplicate sources, and a change reaches the notebook). It then shares the notebook as
  viewer with each account in `[notebook] share_with` that `nlm share status` does not already list
  (`nlm share invite <id> <account> --role viewer`; FR-011b). Measured 2026-10-26: the school domain
  allows a notebook owned by a personal Gmail account to be shared with the school account as
  viewer, and it opens there. After that step, the skill calls
  `log notebook` with its result and the sharing counts (`created`, `unchanged`, `failed` with a reason, or `disabled`): a
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

Spikes before User Story 7 (research R15 to R18); each records its result in research, runs
read-only, and leaves no code on `main`. Pass criteria, so the gate is objective:

- **S4 · The token route (primary)**: seed a first-party sign-in token by hand and, from a test job,
  exchange it for an access token and make one read-only Classroom call for the real account.
  **Pass**: that call returns the student's work (the account-policy block of
  `docs/classroom-investigacion.md` does not stop a first-party token). It also records whether the
  device shows as new and whether a home address differs from the cloud one. On pass, the token
  route is the route and S5/S6 are not needed for the build.
- **S5 · The web route (fallback)**: seed a session by hand and, behind a minimal guard (page-load
  allowlist, zero presses), read the to-do page twice a day for 14 days from the cloud and from a
  home address, prototyping the scripted sign-in. **Pass**: it signs in and reads without evasion
  (no CAPTCHA, no extra factor) and the family would sign in at most once a week (SC-012). If it
  passes only from a home address and not from the cloud, the web route is not built (IX commits the
  run to the cloud project, not a home host); if from neither, the web route is not built.
- **S6 · The web route's background calls**: record method, host, path and call name (never bodies
  or cookies) of a to-do read and a detail read, decide the guard's allowlist (research R18), and
  check that the browser-level guard blocks a planted press (including one fired by the page's own
  `extract.js`) and a planted call on a local fake page. **Pass**: reads can be told from writes, so
  the allowlist is precise; otherwise the guard falls back to page-loads-and-presses only and that
  weaker guarantee is recorded.

If S4 fails and S5 fails, User Story 7 is not built and the family keeps the Mac route (R1) and the
guardian email summaries (research R16).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Node and `jsdom` as development dependencies (IX) | The constitution requires testing every extractor against saved pages, and the extractor is JavaScript | Reimplementing the extraction in Python would duplicate the logic and would not test the code that runs in the browser |
| `jsonschema` as a development dependency (IX) | Tests check captures and agendas against the full contracts | Checking the whole schema by hand in the tests would repeat the contract in code; at runtime the essential keys are checked by hand, with no dependency |
| A scheduled cloud job (IX), for User Story 7 only | The operator excludes their Mac and their browser from the unattended read, and the read must happen with nobody present (constitution 2.0.0, the second named need after spec 005, measured 2026-10-27) | The desktop app's scheduled task needs the Mac on and the operator's browser; GitHub Actions publishes its logs in a public repository; IX (2.0.0) commits a Mac-off need to the operator's Google Cloud project (research R17) |
| A vault for a minor's sign-in credential (III), for User Story 7 only | The school session is too short to reuse and Google refuses an automated password sign-in, so an unattended read needs a stored token (or, in the fallback, the password); III (2.0.0) permits it under limits | Reusing only a hand-signed session fails because the session expires «cada nada» (R16); a password typed live is impossible for Claude and barred for everyone before 2.0.0 (research R15) |
| Playwright for Python and its Chromium as a runtime dependency (IX), in the runner's image only (web route only) | The web route must start a browser with no person in front of it, give it a session, and guard it request by request; the standard library cannot drive a browser | The Claude extension and the built-in browser need the Mac and a model; Chrome's remote debugging protocol by hand would rewrite what Playwright already tests; the token route needs no browser at all |
| A token-exchange library (e.g. `gpsoauth`) as a runtime dependency (IX), in the runner's image only (token route only), only if S4 shows the standard library is not enough | The first-party token exchange signs with Google's keys; if S4 shows that cannot be done with `urllib` alone, a small library does it | Implementing the exchange by hand duplicates a fragile, undocumented protocol; the dependency is isolated to the token route's image and recorded here |
| Science Bits' existing extractors and scripts without tests or quality gates (VI, Development workflow) | This epic changes only where that skill reads its configuration from and where it places its result; testing its capture needs synthetic Science Bits pages | Doing it here would double the epic's scope. It stays as a follow-up issue ("tests and gates for the Science Bits skill"), opened together with this spec's issues |
