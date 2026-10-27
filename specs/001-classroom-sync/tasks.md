---

description: "Tasks for spec 001: Classroom → family Drive, with per-student configuration"
---

# Tasks: Each subject's content, from Classroom to the family's Drive

**Input**: `specs/001-classroom-sync/` (plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md)

**Tests**: mandatory. The constitution requires tests of each extractor against saved pages with
invented data (VI) and a guardrail with cases that prove it fires (II); every PR's gate
includes `ruff`, `pyright`, `pytest` and the guardrail.

**Organization**: by user story; each phase is a vertical slice that leaves the package coherent
and demonstrable, and each PR passes `make ci`. The issues are opened after the spec PR is approved; each phase
will name its own then.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no pending dependencies)
- **[Story]**: story of the spec (US1…US6)

---

## Phase 0: Spec PR

- [ ] T000 Before the constitution commit in the spec PR, copy the «Sync Impact Report» block of `.specify/memory/constitution.md` to the PR description (Governance) and delete it from the file, and run a personal-data scan over `specs/`, `.specify/` and the published history (`git log --all -p`) (the guardrail does not exist yet: a search for the values of the private configuration, without displaying them; record the result in the PR, without the values), and name in the PR the gates that do not run because there is no code yet (ruff, Pyright, pytest, guardrail)

---

## Phase 1: Setup

**Purpose**: Python and test project ready, with the single gate `make ci` green from the first PR.

- [x] T001 Create `pyproject.toml` (project `alfabeta`, `requires-python = ">=3.12"`, no runtime dependencies, `dev` group with `ruff`, `pyright`, `pytest` and `jsonschema`, `[tool.uv] package = true`, package in `src/alfabeta/`), `.python-version` with `3.12` and `uv.lock` with `uv lock`
- [x] T002 [P] Configure ruff in `pyproject.toml` (`target-version = "py312"`, `line-length = 120`, double quotes, Google docstrings; `select` E W F I B C4 SIM UP RUF D TC ANN; `ignore` E501 D100 D104 D107 ANN401; `tests/**` without ANN, D, RUF001, RUF012, RUF043, RUF059, TC, SIM) with `src = ["src", "tests"]` and `extend-exclude = ["skills/sciencebits-a-notebooklm"]` (Complexity Tracking exception), and pytest (`testpaths = ["tests"]`, `python_files = ["test_*.py"]`, `addopts = "-v --tb=short"`)
- [x] T003 [P] Create a single `pyrightconfig.json` at the root: `pythonVersion` "3.12", `typeCheckingMode` "strict", `venvPath` ".", `venv` ".venv", `include` ["src", "tests"], `reportMissingTypeStubs` false, `executionEnvironments` for `src` and `tests` (the latter with `reportPrivateUsage` "none")
- [x] T004 [P] Create `package.json` with `jsdom` as the only development dependency and the `test` script = `node --test "tests/js/**/*.test.mjs"` (Node 23 no longer accepts a directory); generate `package-lock.json`; create `tests/js/smoke.test.mjs` that loads `jsdom`
- [x] T005 Create `src/alfabeta/__init__.py` (version), a minimal `src/alfabeta/__main__.py` with argparse, the global option `--home` and `--version`, and `tests/test_smoke.py` that runs it; that way the gate collects tests from the first PR
- [x] T006 Create `Makefile` with `setup-python` (`uv lock --check`, `uv sync --locked`), `setup-node` (`npm ci`) and `ci` (`ruff check`, `ruff format --check`, `pyright`, `pytest` that fails if it collects zero tests, `npm test`), each step named in the output; every recipe with the `.venv` interpreter. The guardrail step is added by T014: the phase 1 PR names that gate as skipped until then
- [x] T007 [P] Create `.github/workflows/ci.yml` with two jobs with no `needs:` between them and no `paths:` filter: `autofix` (ruff `--fix` and format, non-blocking) and `quality-gate` (setup-uv with cache, `python-version-file: .python-version`, Node, `make setup-python setup-node ci`, blocking)
- [x] T008 [P] Extend `.gitignore` with `.venv/`, `node_modules/`, `.pytest_cache/` and `*.local.*`
- [x] T009 [P] Create `CONTRIBUTING.md` in English: preparing the environment (`make setup-python setup-node`), the `make ci` gate, strict Pyright as the only type checker, and the rule that only synthetic pages generated with `anonymize` go into `tests/fixtures/`

---

## Phase 2: Foundational (blocks every story)

**Purpose**: the three spikes, the guardrail, the anonymizer, the per-student configuration, the domain,
dates, state, lock, sources, placement and the command.

**⚠️ CRITICAL**: no saved page enters the repository before T013–T016.

### Spikes (results in `specs/001-classroom-sync/research.md`)

- [x] T010 Spike S1: with the school account in Chrome and a real attachment, try in order `drive.usercontent.google.com/download?id=<id>&export=download&authuser=<n>`, the export `docs.google.com/<type>/d/<id>/export?format=pdf&authuser=<n>` and the viewer's download button; record in research R4 the method that leaves the complete file in the downloads folder, for files and for Google Docs/Slides/Sheets
- [x] T011 Spike S2: create a test scheduled task in the app that opens Classroom in Chrome, reads the title and downloads a file without approval at that moment, and check with a detached test process (no need for `lock take`, which does not exist yet) that a process started by a Claude tool call survives that call; record the result in research R1 and, if it does not survive, apply the alternative of research R6 in T024–T025, and delete the test task
- [x] T012 Spike S3: save the HTML of the home page, «Trabajo de clase» (Classwork), an assignment detail page, a material one, a question one and the stream of a real class in `~/.alfabeta/<student>/data/raw-captures/` (outside the repo); check that reading the detail of a question does not change «Tu trabajo» (Your work); record whether the detail of an assignment shows any modification mark, and the URL patterns of items and attachments; decide and record in research R3 how the extractor walks the pages without losing the injected script; record in research R8 the list of interface labels observed and how long a full class takes, and set with that measurement the value of `lock_idle_minutes` in `contracts/config-template.toml` and `config/template.toml` at once (longer than the longest stretch without renewal of either skill, the Classroom one and the Science Bits one)

### Guardrail and anonymizer (constitution II and III; FR-005)

- [ ] T013 [P] Write `tests/test_guardrail.py`: cases that must fire, built at run time so that the test file itself does not trip the guardrail (email, macOS user path, id shaped like a Classroom, Drive and notebook (UUID) id, and the `id`, `display_name`, `account`, `root` and `classroom_class` of a test configuration in a temporary `--home`, and a class id saved in its `data/decisions.json`), and cases that must not (template `config/template.toml`, `example.org`/`example.com` emails, relative paths, `<…>` placeholders, synthetic ids `synth-<n>`, hashes in `uv.lock` and `package-lock.json`, long code identifiers in `snake_case` or `camelCase` and test file names, non-identifying values such as `school_year` and `languages`); `--history` finds a value planted in a commit of a temporary repository and already deleted from the tree; `--all` with no files to review exits with 2 and `--staged` with no files exits with 0 and a warning; with no local configurations, a warning on stderr and exit 0 with the generic detectors; file and line in the output without repeating the value
- [ ] T014 Implement `src/alfabeta/guardrail.py` and the subcommand `guardrail [--staged | --all | --history]` per `contracts/cli.md` and research R13: generic detectors (email, user path, ids shaped like Classroom, Drive or notebook ids) and named-value detectors (only the identifying keys of the local configurations and the Classroom and Drive ids in their `data/decisions.json` and `data/state.json`), a self-test that plants one defect per detector in memory on every run, exits 0 · 1 · 2 (the generic detectors reviewed no file) · 3 (blind detector); add `guardrail --all` as a step of `make ci` in `Makefile`
- [ ] T015 Add the hook `.githooks/pre-commit` that calls `python -m alfabeta guardrail --staged`, the recipe `make setup-hooks` that copies it to `.git/hooks/pre-commit` and that `make setup-python` depends on (the environment is not ready without the hook); `make ci` outside continuous integration fails if `.git/hooks/pre-commit` is not equal to `.githooks/pre-commit`; and the section on the guardrail and `make setup-hooks` in `CONTRIBUTING.md`
- [ ] T016 Implement `src/alfabeta/anonymize.py` and the subcommand `anonymize <input> <output>`: generates a synthetic page that keeps HTML tags, CSS classes, hierarchy and the interface labels of the allow list (the one recorded in T012), and invents every remaining text and attribute (titles, descriptions, dates, file names, accessible texts) with stable values, and the ids with the shape `synth-<n>` in the same position of the URL; exits with 1 and writes nothing if any text of the input outside the list survives or if the guardrail finds something; test in `tests/test_anonymize.py` with an invented page that plants a title, a name and an id

### Per-student configuration (FR-001…FR-004; contracts/config-template.toml)

- [ ] T017 [P] Copy the contract to `config/template.toml` and delete `config.example.json`
- [ ] T018 [P] Write `tests/test_config.py`: a key that is missing, extra, changes type or contains `changeme` anywhere in the value → an error that names the key and does not show the value; `drive.root` equal to the root of «Mi unidad» (My Drive) or nonexistent → an error without showing the path; nonexistent `--home` → an error without creating it; `data/` or `tools.folder` inside `drive.root` → error
- [ ] T019 Implement `src/alfabeta/config.py` and the subcommand `config check`: loads with `tomllib`, compares the set of keys and types with `config/template.toml`, rejects values that contain `changeme`, resolves the student's paths (`config.toml`, `data/`) from `--home` and the student `id` («lowercase ASCII»)
- [ ] T020 [P] Write `tests/test_template_covers_reads.py`: every key that `src/alfabeta/` reads exists in `config/template.toml` (an AST walk of the configuration accesses), with a positive control: over a test module with N known accesses it finds the N, and an undeclared key planted in it makes the check fail (no comparison with the number of keys in the template: some are read only by the skills)

### Domain, dates, state, lock, sources and placement

- [ ] T021 [P] Implement `src/alfabeta/model.py` with the immutable dataclasses of data-model.md: `Student`, `Subject`, `Decision` (`type` ∈ `class_link` · `topic_match` · `item_match` · `detected_exam` · `dismissed_candidate` · `exam_correction`; key `(type, origin)`; `confidence` ∈ `high` · `medium` · `low`; `state` `proposed` → `confirmed` · `rejected`, `confirmed` or `rejected` → `superseded`), `Item` (`type` ∈ `assignment` · `material` · `question` · `announcement`; `status` ∈ `pending` · `turned_in` · `returned` · `overdue` · `missing_per_teacher` · empty), `Attachment` (`kind` ∈ `file` · `google_doc` · `video` · `link` · `form`; «the last three are not downloaded»), `Replica`, `Grading`, `AgendaEntry` (`category` ∈ `exam` · `assignment` · `quiz` · `material` · `announcement`, «exactly one»), `Run`
- [ ] T022 [P] Write `tests/test_dates.py` with a table of cases: «13 oct» in a 2026-2027 school year → 2026; «14 ene» → 2027; «Mañana, 8:00», «Hoy» and a weekday resolved relative to `captured_at`, also for a capture applied the next day; «Fecha de entrega: 19 oct, 8:00»; the October and March clock changes; «Última modificación» is never taken as posting
- [ ] T023 Implement `src/alfabeta/dates.py` (`DateResolver`): Classroom texts in Spanish → date or date-time in `Europe/Madrid` with `zoneinfo`, year from the school year (September to December, first year; January to August, second), relative ones relative to the moment of the capture
- [ ] T024 [P] Write `tests/test_state.py`: atomic write; no rewrite if nothing changes; `lock take --mode` stores the mode and returns a run identifier; `lock take` prevents a second `lock take` for the same student or another one (browser lock; exit 1, reason `lock_busy`, a single `stopped` line); a second run can neither use nor release the first one's lock (another `ALFABETA_RUN` → exit 1); without `ALFABETA_RUN`, the subcommands that require the lock exit with 1; `lock take` and `log stop` work with a configuration whose `[sync]` is valid even if another key fails or the Drive is missing; every subcommand renews it; with no renewal for `lock_idle_minutes` (simulated clock) the watcher releases it on its own and writes `stopped` with reason `idle`; if the watcher dies, the system releases the `flock`s; `log stop` writes its line with every reason in the list (including `lock_not_held` and `invalid_config`) and rejects one that is not in it; one JSON line per run in `log.jsonl` without the student's name or email
- [ ] T025 Implement `src/alfabeta/state.py` (`StateStore`, JSON Lines log) and the subcommands `lock take` / `lock renew` / `lock release` (the student lock and the Mac's browser lock with `fcntl.flock` in a watcher process that is released on idleness) and `log stop` (research R6, contracts/cli.md)
- [ ] T026 [P] Implement `src/alfabeta/sources.py`: Protocol `Source` (`name`, `items()`); `ClassroomSource` and `BookSource` are completed in US1 and US4
- [ ] T027 [P] Write `tests/test_placement.py`: topic matched and confirmed → `<school-year>/<subject>/<YYYYMMDD> - Tema NN - <title>/<source>/`, where `YYYYMMDD` is the posting date of the first item placed in the folder; an existing folder whose name after the date matches is reused whatever its date, and its date does not change when a later item is earlier or the first one is deleted; teacher's topic with no book → `<YYYYMMDD> - <teacher's title>`, with no `Tema NN`; unconfirmed match → the teacher's topic's own folder, and the replicas move to the book topic when the match is confirmed; no topic → `<YYYYMMDD> - Sin tema/<source>/`, one per subject, and never a `YYYY`-`MM` month folder; material with one file → `YYYYMMDD - <title>.<ext>`; material with several files, with links or with a description → folder with its files, `descripcion.md` if it has text and `enlaces.md` if it has links; assignment or question → always a folder with `enunciado - <name>` and `enunciado.md` with the instructions or the question; material with no files or links, only text → `.md` note (even if it has a description); material with no files and with links → folder with `descripcion.md` and `enlaces.md`; teacher's topic rejected as a match → it stays in `<YYYYMMDD> - <teacher's title>`; item with a confirmed `item_match` → that book topic, even if its topic says otherwise; announcement → note `YYYYMMDD - aviso - <first words, 60 characters>.md` in `Sin tema`, or a folder with the note and the attachments if it has any; names valid in Drive, at most 255 UTF-8 bytes and unique without losing items
- [ ] T028 Implement `src/alfabeta/placement.py` (`Placer`) per FR-012…FR-015c
- [ ] T029 Create in `tests/fixtures/classroom/` invented JSON captures with an invented `run`, which `sandbox download --captures` replaces (class list and two classes: topics, items of every type, attachments of every kind, one assignment turned in, one returned, one marked missing, one with «Última modificación», an exam announcement in Spanish and another in a second language of the class), valid against `contracts/capture.schema.json`, and copy the schemas to `src/alfabeta/schemas/`; a test in `tests/test_contracts.py` with `jsonschema` and another that checks that the copies, and `config/template.toml`, are byte-for-byte identical to `contracts/`
- [ ] T030 Implement `src/alfabeta/sandbox.py` and the subcommand `sandbox prepare`: requires an explicit `--home` and creates there the student `sample` with a valid invented configuration, `drive/` as root with a folder `Tema 01 - <invented title>/sciencebits/` in a subject with a book, an empty `downloads/` and the captures of T029 in `sandbox-captures/`; also implement `sandbox download --captures`, which copies them to `downloads/` with the current `run`, as the extractor would leave them (attachments and decisions are added by T039)

**Checkpoint**: `make ci` green with configuration, dates, state, lock, placement and guardrail; spikes recorded.

---

## Phase 3: User Story 1 - What the teacher posts, in its topic's folder (P1) 🎯 MVP

**Goal**: one subject synced: materials and assignment statements replicated with the date in front,
links noted, unmatched topics waiting in their own teacher's-topic folder.

**Independent Test**: quickstart scenario 2.

### Tests for User Story 1

- [ ] T031 [P] [US1] Generate with `anonymize` the synthetic pages of S3 and save them in `tests/fixtures/classroom/pages/` (home, listing, assignment, material and question detail, stream), with their date and the source page type, without the student's ids or paths, in `tests/fixtures/classroom/README.md`; add a synthetic anti-bot challenge page and one with interface labels in another language
- [ ] T032 [P] [US1] Write `tests/js/extract.test.mjs`: with `jsdom` over the synthetic pages, `extract.js` returns `classes` and `class` captures with the keys of the contract; the class comments, private comments and author planted in the detail pages do not appear in the capture; topics in order, literal `listing_date_text`, «Sin tema» (No topic) as `topic: null`, attachments by `kind` and `complete: true`; with the challenge page it returns `stop` with reason `challenge`; with the other-language one, `unexpected_ui`
- [ ] T033 [US1] Write in `tests/js/extract.test.mjs` the read-only test: listeners for clicks, form submission and navigation in the synthetic pages; the extractor clicks no button of the «Tu trabajo» panel, submits nothing, does not navigate to forms or quizzes and waits at least 2 s between navigations (simulated clock)
- [ ] T034 [P] [US1] Write `tests/test_capture.py`: normalization of the captures of T029 to `Item` and `Attachment`, status per the table of data-model.md (every row, including «Falta» (Missing) with a future date → `pending`, including «falta esto» beating «Calificado» (Graded), and an unknown text that leaves the status empty and is logged)
- [ ] T035 [P] [US1] Write `tests/test_plan_apply_us1.py`: with the student `sample`, `lock take` → `sandbox download --captures` → `downloads collect` (captures) → `plan` → `sandbox download` → `downloads collect` (attachments) → `apply`, with `ALFABETA_RUN`; a capture with another `run` in the downloads is not collected; a capture outside the configured school year → `plan` exits with 1 and writes `stopped` with `invalid_config`; an attachment not fetched stays in its item's `enlaces.md` with link and reason; `plan` requests the expected downloads and `apply` leaves each item in its folder or noted with link and reason (SC-001); an attachment that does not arrive stays `not_fetched` and is noted in `enlaces.md` as «no traído»; an invalid class capture does not prevent applying the other one (FR-029); without the lock held, `plan` and `apply` exit with 1; confirming a match after a first `apply` moves the replicas from the teacher's topic's own folder to the book topic's without duplicating them; with `--subject` only that subject is planned and applied; a `stop` capture with `class` leaves that class unapplied and the result `partial` with its reason; `apply` with no new captures still moves the replicas that a decision changed

### Implementation for User Story 1

- [ ] T036 [US1] Implement `skills/classroom-sync/scripts/extract.js` per research R3: capture of the class list and one capture per class («Trabajo de clase» and the assignment, material and question detail: posting, modification, due date, points, description, «Tu trabajo» status and attachments; the id of each item and each attachment is taken from its position in the URL patterns recorded in S3, with one rule for items and another for Drive attachments, never from its shape); only navigates to the pages allowed by FR-007, waits ≥2 s with jitter between pages, never clicks the «Tu trabajo» panel nor follows forms or quizzes; detects challenges and unexpected interface labels and returns a `stop`; marks `complete`; receives the current `run` from Claude and downloads the result as `alfabeta-capture-<run>-<class>-<stamp>.json`, with the `run` field
- [ ] T037 [US1] Implement `src/alfabeta/capture.py`: reads captures, checks their essential keys by hand (no dependencies) and normalizes them to `Item` and `Attachment` with `DateResolver` and the status table; the status comes from the detail, not the listing (FR-008a); complete `ClassroomSource` in `src/alfabeta/sources.py`
- [ ] T038 [US1] Implement `src/alfabeta/decisions.py` (`DecisionStore` in `data/decisions.json`) and the subcommands `decisions propose`, `confirm`, `correct` and `change` per `contracts/cli.md`; test in `tests/test_decisions.py` (a `(type, origin)` with a non-superseded decision is not proposed again, except a `rejected` one whose origin shows a later modification or, for `topic_match`, whose title changed or with a new book topic in the Drive after the rejection; an identical proposal does not write; `confirm --reject` on a `detected_exam` exits with 1; `change` leaves the previous one (confirmed or rejected) `superseded`; `--type` disambiguates; `confidence` mandatory in proposals; a `dismissed_candidate` counts from when it is proposed and, rejected by the family, returns the candidate to pending; a `detected_exam` or `dismissed_candidate` whose `origin_hash` no longer matches the text becomes `superseded`, unless it has an `exam_correction`)
- [ ] T039 [US1] Implement `src/alfabeta/plan.py` (`Planner`) and the subcommand `plan`: sources + state + decisions → `data/plan.json` with the requested downloads (url per S1 and expected name; only new, modified, renamed or full-review ones, FR-026), replicas to write and pending decisions (unlinked classes, unmatched topics, and items of a teacher's topic that spans several book topics); a rejected topic returns to pending only if its title changes or a new book topic appears; `--subject` limits the scope and, without it, only the classes that `downloads collect` recorded in the lock since the last `lock take` are included; a `(type, origin)` that already has a non-superseded decision does not return to `pending_decisions` (except under the rule for rejected ones), so a `dismissed_candidate` of an item does not prevent proposing its `item_match`; a `dismissed_candidate` rejected by the family returns its candidate to pending in the next `plan`; exits with 1 and `invalid_config` if a capture was taken outside the configured school year; spreads downloads with the same expected name over different batches; extend `sandbox prepare` to leave in `sandbox-attachments/` (outside the downloads) the invented attachments with the names the plan requests, implement `sandbox download` per `contracts/cli.md`, and leave the class links confirmed and a `detected_exam` proposal
- [ ] T040 [US1] Implement `src/alfabeta/downloads.py` (`DownloadsInbox` over `downloads.folder`) and `downloads collect`: moves only the files of the plan and the captures of the current run (`run` in name and field), records in the lock the classes collected, ignores Chrome's half-downloaded `.crdownload` files, matches each attachment by its expected name or that name with the browser's ` (<n>)` suffix, and only if it was created after the plan, and verifies they are complete (FR-018); test in `tests/test_downloads.py` with two attachments with the same name in different batches (each one ends up in its item's replica) and a file with the expected name older than the plan, which is not collected
- [ ] T041 [US1] Implement `src/alfabeta/replicas.py` (`Applier`) and `apply` for materials, statements and the `enlaces.md` and `descripcion.md` notes, deleting from `data/` the collected attachments once placed or verified identical, noting an attachment not fetched in its item's `enlaces.md`, leaving unapplied the class of a `stop` capture (result `partial` with its reason), recomputing targets with the current decisions, moving without duplicating the replicas whose target changed because of a decision confirmed after they were placed, writing only in the student's root, never showing its absolute path, and stopping without writing if the Drive is not mounted (FR-030, FR-031)
- [ ] T042 [US1] Write `skills/classroom-sync/SKILL.md`: every command runs on the Mac with `uv run --project <tools.repository> python -m alfabeta`, never in the app's virtual machine; `lock take --mode interactive`, whose `run` is passed in `ALFABETA_RUN` to every following command (inline, `ALFABETA_RUN=<id> uv run …`, because every tool call is a new shell), and `config check`; open Classroom in Chrome with the Claude extension and locate the school account by walking `/u/<n>` and comparing the email locally; if the session expired, there is a challenge or the interface is not the expected one, `log stop` with its reason and a notice to the family; capture the class list (the extractor receives the `run`), `downloads collect`, `plan` and propose the class links (in interactive mode, confirm them right then); capture each linked class (or only those of the requested subject), with `downloads collect` after each class (which also renews the lock); if midway the session expires, a challenge appears or the interface is not the expected one, collect the `stop` and apply the classes already captured (`partial` with its reason, data-model «Run»); `plan` again and propose topic matches and, for the topics that span several book topics, per-item matches, with reason and confidence; download the requested attachments with the method of S1, with at least 2 s with jitter between downloads and `downloads collect` after each batch; `apply`; `lock release`; read-only and personal-data prohibitions
- [ ] T043 [US1] List in the `apply` summary the unlinked classes and the hidden ones (FR-008), the matches pending confirmation and the unknown statuses

**Checkpoint**: US1 works on its own with the student `sample` and with a real subject (quickstart 2 and the US1 points of scenario 9).

---

## Phase 4: User Story 2 - The student's agenda (P1)

**Goal**: `agenda.json` and `agenda.md` per school year with the five categories, detected exams, «Pendiente»
and «Hecho», independent of the day.

**Independent Test**: quickstart scenario 3.

### Tests for User Story 2

- [ ] T044 [P] [US2] Write `tests/test_classification.py`: every item gets exactly one category with the precedence exam > quiz > assignment > material > announcement (a question that is an exam → `exam`; an assignment with a test title in any of the student's languages → `exam`; «Pregunta» (Question) with no hints → `quiz`; an assignment whose only attachment is a form → `quiz`; an assignment with a form and a file → `assignment`; an announcement with no exam → `announcement`); 100 % of the invented exam announcements of T029 come out as candidates (SC-004a)
- [ ] T045 [P] [US2] Write `tests/test_agenda.py`: `agenda.md` shows the Spanish labels of data-model's "Language of names" (categories, statuses, «detectado», «sin fecha») and never the English values; every status in its list per the table of FR-020c (`pending`, `overdue`, `missing_per_teacher` → Pendiente; `turned_in`, `returned` → Hecho; detected exam → Pendiente until there is a capture of its class later than its date, dismissed → out; an exam that is an assignment in `overdue` with a capture of its class later than its date → Hecho, and in `missing_per_teacher` → Pendiente); «Pendiente» from nearest to farthest with the undated ones at the end; «Hecho» by due or exam date, from newest to oldest; a detected exam is an entry of its own `<item>#exam-<k>` and the source material or announcement keeps its own; an assignment, quiz or exam with no `status` goes to «Pendiente»; a detected exam with no date stays in «Pendiente» until the family corrects or dismisses it; statuses including `missing_per_teacher`; a detected exam with `detected: true` and `origin`, in the agenda from the moment it is proposed and unconfirmed; an item that announces two exams gives two entries `<item>#exam-1` and `-2`; 100 % of the sample `detected_exam` proposals are in the agenda (SC-004a); material and announcement in «Publicado» after «Hecho»; a family correction prevails in the next run; empty `folder` for an announcement with no replica; `classroom_link` without `/u/<n>`; `agenda.json` valid against `contracts/agenda.schema.json` (every key required) and with no timestamp; `agenda.md` says to open the links with the school account; generating twice with a different "today" does not rewrite the files
- [ ] T046 [P] [US2] Extend `tests/js/extract.test.mjs` with the stream: announcements with `created_text`, text and attachments; the notifications of new items are ignored; no student comments or names

### Implementation for User Story 2

- [ ] T047 [US2] Extend `skills/classroom-sync/scripts/extract.js` to read the stream announcements (text, «Fecha de creación» (Created) and attachments), without comments or authors, and `src/alfabeta/capture.py` to normalize them to an `Item` of type `announcement` with `posted_at` from «Fecha de creación» (new case in `tests/test_capture.py`)
- [ ] T048 [US2] Implement `src/alfabeta/classification.py` (`Classifier`): closed category with precedence (FR-020a) and exam candidates from hints in titles, descriptions and announcements, which go to `plan.json` as pending decisions unless their origin already has a current `detected_exam` or `dismissed_candidate` decision (a `rejected` one does not count: the candidate comes back) (a `detected_exam` or `dismissed_candidate` stops counting if the hash of its origin's text, `origin_hash`, changes, unless the family corrected it); a single candidate per item (Claude decides how many exams it announces and numbers `k`)
- [ ] T049 [US2] Extend `skills/classroom-sync/SKILL.md`: for each exam candidate, Claude proposes date, reason and confidence in the class's language with `decisions propose` (`detected_exam`, origin `<item>#exam-<k>` with `k` = 1, 2… if it announces several); in a scheduled run they stay as detected
- [ ] T050 [US2] Implement `src/alfabeta/agenda.py` (`AgendaBuilder`) and the subcommand `agenda`: content that depends only on the state and the decisions, files rewritten only if their bytes change, lock checked and renewed, JSON `{written:[…]}` on stdout and the human-readable text on stderr; `apply` regenerates it at the end (FR-020…FR-020c)

**Checkpoint**: US1 and US2 work; the family sees a complete agenda for the school year.

---

## Phase 5: User Story 3 - Syncing again without duplicating and with changes (P2)

**Goal**: repeated runs are idempotent, changes detected, nothing deleted, resumption after an interruption.

**Independent Test**: quickstart scenario 4.

- [ ] T051 [P] [US3] Write `tests/test_incremental.py`: a second run with no changes → zero files modified in the root and state not rewritten (SC-002); an item with a later «Última modificación» → its attachment is requested again and, if the hash changes, a new version and `<name> (anterior YYYY-MM-DD)`; an unchanged item → not requested until the full review; an item absent from a `complete: true` capture → replica kept and `withdrawn_at`; absent from a `complete: false` one → nothing withdrawn; a run cut midway → the next one finishes without duplicating; a full review that finds the same bytes does not rewrite `state.json` and the next one is counted from the log line with `full_review: true` (the first sync counts as a full review); two identical captures with an exam date between them → only that entry changes in the agenda; a second capture with another `captured_at` and no date between the two → neither `state.json` nor the agenda is rewritten (FR-025)
- [ ] T052 [US3] Implement in `src/alfabeta/replicas.py` and `src/alfabeta/plan.py` the SHA-256 hash comparison before writing, the modification mark seen, the periodic full review (`sync.full_review_days`), the previous versions (FR-015b), marking withdrawn ones only with a complete capture (FR-027) and resuming from `plan.json`, and pruning old captures in `data/captures/` above `kept_captures`
- [ ] T053 [US3] Complete the run's log in `src/alfabeta/state.py` (counters, unknown statuses, pending decisions, `mode` read from the lock (`lock take --mode`), `/u/<n>` index read from `account_index` in the classes capture, `result`, `reason`) and the «what has changed since last time» summary of `apply` (FR-028)
- [ ] T054 [US3] Apply `decisions change` to a confirmed or rejected match: move the replicas to their correct folder without duplicating or losing them (edge case of the spec), with a test in `tests/test_incremental.py`
- [ ] T068 [P] [US3] Write `tests/test_mirror.py` (FR-011a, SC-002, SC-010) on two sandbox folders: after `mirror` every file of the root is in each mirror with the same size and modification time; a second `mirror` with no change writes nothing to any mirror; a file deleted or moved in the root stays in the mirror; a file added in a mirror is never copied to the root; a mirror that does not exist is counted as failed by its index and the other mirrors are still brought up to date; `config check` rejects a mirror that is the root, is inside it, contains it or is «Mi unidad», and only warns when one is not mounted; neither the JSON, nor stderr, nor the log carries a mirror's path
- [ ] T069 [US3] Implement `src/alfabeta/mirror.py` and the subcommand `mirror` per `contracts/cli.md` (`rsync -rlt --exclude .DS_Store <root>/ <mirror>/` through `subprocess`, no `--delete`), call it at the end of `apply` and `book place`, add `mirrors` (`up_to_date`, `failed`) to their log lines and the mirrors line to the summary for the family, and the `drive.mirrors` checks to `config check`

---

## Phase 6: User Story 4 - The book in the same structure (P2)

**Goal**: Science Bits writes into `<topic>/sciencebits/` of the family Drive with the per-student configuration.

**Independent Test**: place a sample topic and check the path and that `classroom/` of the same topic does not change.

- [ ] T055 [P] [US4] Write `tests/test_book.py`: `book place` leaves `TemaNN_<LANG>.pdf` and `.md` in `<school-year>/<subject>/<YYYYMMDD> - Tema NN - <title>/<book>/` with hash and previous version, reusing the folder whose name contains `Tema NN - ` whatever its date and creating `<today> - Tema NN - <title>` only if there is none, and adds a line to the log (time, source, topic, placed or unchanged); `log notebook` writes its line with every result and exits with 1 if `--reason` is missing with `failed`; it never writes outside the student's root nor in Dropbox; an invented third provider plugs in as another `Source` without touching `placement.py` or `replicas.py`
- [ ] T056 [US4] Complete `BookSource` in `src/alfabeta/sources.py` and implement in `src/alfabeta/book.py` and `src/alfabeta/__main__.py` the subcommands `book place` and `log notebook` per `contracts/cli.md` (`--shares` included), with the lock checked and renewed
- [ ] T057 [US4] Update `skills/sciencebits-a-notebooklm/SKILL.md`: run the commands on the Mac with `uv run --project <tools.repository> python -m alfabeta` (never in the virtual machine, which only sees Downloads); take the lock (`lock take --mode interactive`, or `scheduled` if a scheduled task launches it, and pass its `run` in `ALFABETA_RUN` to every following command) before opening Science Bits, renew it (`lock renew`) on every poll of the capture, between the build steps and between each source that `nlm` uploads, and release it at the end; receive or ask for the student `id` (never guess it); read `~/.alfabeta/<student>/config.toml` (`[[subjects]]` with `book = "sciencebits"` and `book_class`, school year, `student.grade_level` instead of `student.grade`, `[sciencebits] url` and `languages` instead of the top-level `languages` (the first one gives the folder title), `[tools] folder`, `[downloads] folder` instead of `~/Downloads` (also in `scripts/watch.py`), `[notebook] enabled` and `share_with` and the notebook name the constitution sets, «`<grade level>. <Subject>. Tema NN - <title>`» with `student.grade_level`), generate as today and place with `book place` (which brings the mirrors up to date, replacing the skill's own `rsync` over `storage.mirrors`); in the `nlm` step, first list the sources of the topic's notebook (`nlm source list <notebook> --json`) and add only the files that are not there, comparing by the title under which `nlm source add --file` registers the source (check that first with a test notebook; constitution V and «Notebooks»: repeating does not duplicate sources); share the notebook as viewer with each account in `[notebook] share_with` that `nlm share status <notebook> --json` does not already list (FR-011b); after the `nlm` step (or if `[notebook] enabled` is false), `log notebook` with its result and `--shares` (`unchanged` = the notebook existed and no source was added), and if `nlm` fails, `failed` with a reason and a notice to the family, without touching what was placed; replace the old `config.json` keys `storage.tools_dir`, `storage.base_dir`, `storage.mirrors`, `storage.topic_folder_pattern`, `subjects` (a map), `sciencebits.url` and `notebook.*` with those TOML keys; in `scripts/build.py`, remove from `L10N` the `unit` and `course` values (which name a specific grade, subject and topic; constitution I) and make `--config` mandatory, exiting with the name of the missing key, and remove every reference to `config.json` and Dropbox; no key read outside the template; in the description, the steps and the examples of `SKILL.md` (also the paths with a language in the URL), neutral languages (`es`, `en`) and the set of languages taken from `sciencebits.languages`; the `L10N` table of `build.py` with the interface texts for each language the provider supports is a capability, not student data, and stays; remove the instructions that create the configuration or write to it (if it is missing or invalid, `config check` and stop); «the next topic» comes from the `Tema NN` folders that already have `sciencebits/` in the Drive

---

## Phase 7: User Story 5 - A second student and nothing personal in the repository (P2)

**Goal**: two invented students coexist without touching the repository; the guardrail covers the whole repo.

**Independent Test**: quickstart scenario 5.

- [ ] T058 [P] [US5] Write `tests/test_multiple_students.py`: two students created from the template in a temporary `--home`; syncing one writes only its root, its state and its log; while one syncs, the other cannot take the browser lock (they share Chrome and the downloads folder) and their student locks are independent; `git status` of the repository unchanged
- [ ] T059 [US5] Run `python -m alfabeta guardrail --all` with the first student's real configuration present on the Mac over the whole repository (including `specs/` and `tests/fixtures/`), and `guardrail --history` over what is published (`git log --all -p`), and fix any finding before closing the phase (one in the published history is taken to the family: rewriting it is their decision)

---

## Phase 8: User Story 6 - Stream, student submissions and grading (P3)

**Goal**: announcements saved in the subject's `Sin tema` folder; in each assignment, `entrega` and `correccion` next to the `enunciado`.

**Independent Test**: two announcements (one with an attachment), an assignment turned in and not graded and another returned with
grading; each role recognizable by its name (SC-008a), with no comments or classmates' names.

- [ ] T060 [P] [US6] Write `tests/test_us6.py` (the author and the class and private comments planted in the synthetic page do not appear in `correccion.md` nor in the announcement): announcement → `<YYYYMMDD> - Sin tema/classroom/YYYYMMDD - aviso - <summary>.md` (or a folder if it has attachments) and its agenda entry gets a `folder`; student submission → `entrega - <name>`; grading → `correccion.md` with grading state, grade only if Classroom shows it, teacher comment and return date; resubmission → the earlier one as previous
- [ ] T061 [US6] Extend `skills/classroom-sync/scripts/extract.js` and `tests/js/extract.test.mjs` to read from the detail the files the student turned in, the visible comment and grade and the return date (`returned_text`), without touching the «Tu trabajo» panel
- [ ] T062 [US6] Implement in `src/alfabeta/replicas.py` the replicas of announcements, student submissions and `correccion.md` (FR-015a, FR-016a)

---

## Phase 9: Polish & Cross-Cutting

- [ ] T063 Scheduled run (FR-021a), per S2: add to `skills/classroom-sync/SKILL.md` the scheduled mode (`lock take --mode scheduled`; no questions, proposals left pending; with the same stops as the interactive mode (data-model «Run»: before capturing any class or with the Drive not mounted, `log stop` with its reason and without writing to the student's folder; midway, `partial`), and the notice is the task's result in the app; in reduced mode, only the «toca sincronizar» ("time to sync") notice) and document in `README.md` how to create the daily scheduled task at the time in `schedule.daily`
- [ ] T064 [P] Update `README.md` (skills table with `classroom-sync`; requirements: Chrome with the extension, Google Drive for desktop, `uv`, Node for development; installation with `config/template.toml`, and how the skills run the command with `uv run --project`), `docs/roadmap.md` (epics 2 and 3, and the «today» and «this week» in epic 2), and remove from `README.md` and `docs/classroom-investigacion.md` the details that narrow down grade or region (specific level, specific languages in examples and descriptions; the per-language interface text table of `build.py` does not count, see T057)
- [ ] T065 [P] Write `tests/test_privacy.py`: after a full run of the student `sample`, neither `log.jsonl`, nor `plan.json`, nor stderr, nor the URLs built contain its `id`, `display_name`, `account`, any address in `calendar.shared_with` or `notebook.share_with`, or the absolute path of its root or of a mirror (SC-009, FR-031): the command never prints `display_name`
- [ ] T066 [P] Open the follow-up issue «tests and quality gates for the Science Bits skill» (exception recorded in the plan) together with the issues of this spec
- [ ] T067 Run the whole of quickstart.md (scenarios 1 to 9) and record the results in the PR

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (1)**: no dependencies; T005 before T006 so that the gate collects tests.
- **Foundational (2)**: after Setup. T013–T016 before any real page in the repo (T031). S1 (T010) before T039–T040; S3 (T012) before T014, T016, T031, T032 and T036; S2 (T011) before T024–T025 and T063.
- **US1 (3)**: after Foundational. It is the MVP.
- **US2 (4)**: uses the capture and the state of US1.
- **US3 (5)**: on top of US1 (replicas and state). T068–T069 (mirrors) after T041 (`apply`); T056 calls the `mirror` of T069.
- **US4 (6)**: after US1 (T041, `Applier`) and US3 (T052, hashes and previous versions).
- **US5 (7)**: T058 after T041 (needs `plan` and `apply`); T059 closes phase 7; after that, `guardrail --all` keeps running in `make ci` on every PR.
- **US6 (8)**: on top of US1 (assignment folders), US2 (agenda) and US3 (previous versions).
- **Polish (9)**: at the end. T000 goes in the spec PR, before any implementation; T066 is done when opening the issues after it is approved.

### Within Each Story

Tests first (they must fail), then domain, services, command and skill.

### Parallel Opportunities

- Setup: T002, T003, T004, T007, T008, T009 at once after T001.
- Foundational: T013, T017, T018, T020, T021, T022, T024, T026, T027 at once; the spikes T010–T012 first, because their results set T014, T024–T025 and T032.
- US1: T031–T035 at once; T038 after T037 (both add subcommands to `__main__.py`).
- T058 (US5) in parallel with US2–US4, once T041 is done.

### Parallel Example: User Story 1

```text
T031 synthetic pages   T032 extract.js test   T033 read-only test   T034 capture test   T035 plan/apply test
```

## Implementation Strategy

### MVP First (User Story 1)

1. Setup and Foundational, with the three spikes.
2. US1 with a real subject.
3. **Stop and validate** with quickstart 2 and 9.

### Incremental Delivery

1. US1 → folders with the teacher's material.
2. US2 → agenda with exams: what matters most to the family.
3. US3 → repeatable daily without duplicating.
4. US4 → the book next to the material.
5. US5 → second student and a clean repository.
6. US6 → stream, submissions and grading.
7. Polish → scheduled run and documentation.
