# Tasks: Class notes and new material reach the topic's notebook by themselves

**Input**: Design documents from `specs/005-notes-to-notebook/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: included. The plan asks for one test module per module. Drive answers are recorded
responses with invented values (spec 004 research R8); Claude answers are recorded with invented
content; `nlm` is a fake; image fixtures are drawn by the tests. No test calls Google, Claude or
`nlm`. The live proof is the quickstart's.

**Depends on spec 004**: the transport, OAuth refresh and keychain (built), and its scoped Drive
adapter `src/alfabeta/google/drive.py` with the folder allowlist (spec 004 slice 3, not built). Every
Drive task below uses that adapter; none opens its own HTTP path to Drive.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1 a photo reaches the notebook · US2 the student corrects · US3 Classroom items ·
  US4 the report · US5 a topic's living files

---

## Phase 1: Setup

- [ ] T001 Add the keys of `specs/005-notes-to-notebook/contracts/config-template.toml` (`[notes]`, `[cloud]`) to `config/template.toml`, each with its comment; read them in `src/alfabeta/config.py`; run `tests/test_template_covers_reads.py`.
- [ ] T002 Add `reportlab` and `pypdf` to `pyproject.toml` as runtime dependencies with exact pins, update `uv.lock`, and say beside each pin, in one comment, why the standard library is not enough (plan, Complexity Tracking).
- [ ] T003 [P] Create `src/alfabeta/notes/__init__.py` and `tests/fixtures/notes/README.md`; the README says every file is a recorded response with invented values, named `<call>-<YYYY-MM-DD>.json`, and that images are drawn by the tests, never photos of real notes.

---

## Phase 2: Foundational (blocks every story)

- [ ] T004 Write the domain values in `src/alfabeta/notes/model.py` from `data-model.md`: `Arrival` (kinds `notes_photo`, `notes_text`, `classroom_item`, `living_file`, `unexpected`; `origin` `alfabeta` or `family`), the notes-photo states `seen` → `transcribed` → `in_living_file` plus `duplicate`, `unreadable`, `failed`, `budget_wait`, the Classroom states `seen` → `in_living_file` plus `failed`, `NotesPage` (`review` one of `automatic`, `checked`, `wrong`), `LivingFile` (`kind` `notes` or `classroom`; "`file_id` never changes once set"), `ClassroomEntry`, `ChangeCursor`, `RunReport`. No I/O.
- [ ] T005 [P] Test the state transitions and the "same md5 → duplicate" rule in `tests/test_notes_model.py`.
- [ ] T006 Write `StateStore` and `DriveStateStore` in `src/alfabeta/notes/state.py`: read and write `.alfabeta/estado.json` at the alfabeta root through `ScopedDrive`, remember `headRevisionId` at read, and refuse to write when it changed (research R4). Files it writes carry `appProperties.origin = "alfabeta"`.
- [ ] T007 [P] Test in `tests/test_notes_state.py`: round trip; refusal on a changed revision; nothing written when the state is unchanged.
- [ ] T008 Write `ChangeFeed` and `DriveChangeFeed` in `src/alfabeta/notes/changes.py`: `changes.list` from a page token with `fields=newStartPageToken,nextPageToken,changes(fileId,removed,file(name,mimeType,parents,md5Checksum,modifiedTime,appProperties,trashed))`, follow `nextPageToken`, keep files inside the allowlist, map each to an `Arrival` by its folder (`apuntes/`, `classroom/`, topic root) and skip `.alfabeta/` and `Informes/` (research R2, R10).
- [ ] T009 [P] Record `changes.list` pages with invented values in `tests/fixtures/notes/` and test in `tests/test_notes_changes.py`: paging, the allowlist, each kind, a rename arriving as a change, and a file outside the alfabeta folder ignored.
- [ ] T010 Write `PdfBuilder` and `ReportlabPdfBuilder` in `src/alfabeta/notes/pdf.py`: cover page; a notes page (photo scaled to the page, then the transcription with the conventions of research R5 rendered, headed «Transcripción automática», «Revisada por el alumno» or «En corrección»); a Classroom item (cover with title, posting date and address, then its PDF pages copied with `pypdf`). Fixed metadata and creation date so the same input gives the same bytes (research R6).
- [ ] T011 [P] Test in `tests/test_notes_pdf.py`: two builds of the same records have the same checksum; page order; each heading; a Classroom item with 0 pages is its cover alone; a drawn image fixture, never a photo.

---

## Phase 3: User Story 1 - A photo of the notes reaches the notebook with no one at a computer (P1) — MVP

**Goal**: a photo uploaded to `apuntes/` becomes a page of `Apuntes · Tema NN.pdf` with the Mac off.

**Independent test**: quickstart steps 3 and 5.

- [ ] T012 [US1] Write `Transcriber` and `ClaudeTranscriber` in `src/alfabeta/notes/transcribe.py`: one Messages API call per photo through `HttpTransport`, image first, the instructions of research R5, model from `[notes] model`, key from the keychain on the Mac or from the environment the job mounts; return Markdown and `usage`; map a credit or spend-limit refusal to `budget_wait` and any other error to `failed`.
- [ ] T013 [P] [US1] Record a Claude answer with invented content and a credit refusal in `tests/fixtures/notes/` and test `tests/test_notes_transcribe.py`: request shape (image block before text), the key never in a log line, `budget_wait` on refusal.
- [ ] T014 [US1] Write `run_notes` in `src/alfabeta/notes/run.py` for notes: read state and cursor; for each new `notes_photo`, skip it as `duplicate` when its md5 is known, else transcribe, write the PDF and Markdown next to the photo (Spanish names, `appProperties.origin = "alfabeta"`), record the `NotesPage`; rebuild each changed living notes file and upload it as a new revision of its `file_id` only when its checksum changed; save the state, then the cursor, last.
- [ ] T015 [P] [US1] Test `tests/test_notes_run.py` with fakes for every port: one photo → one page; a second run with nothing new → zero writes (SC-004); the same photo twice → one page and a duplicate; a crash before the cursor is saved → the next run repeats nothing; a topic with no `source_id` is reported `waiting_setup` and its file is still built.
- [ ] T016 [US1] Add `notes run --student <id>` to `src/alfabeta/__main__.py` with the output and exit codes of `contracts/cli.md` (0, 2, 3, 4) and a test of the JSON shape in `tests/test_notes_cli.py`.
- [ ] T017 [US1] Write `deploy/notes-cloud-run/Dockerfile` (Python 3.12 slim, the package installed with `uv --locked`, entry point `python -m alfabeta --home /config notes run --student "$STUDENT"`) and `deploy/notes-cloud-run/README.md` pointing to the how-to.
- [ ] T018 [US1] Write `docs/how-to/notes-cloud-run.md` (layered how-to, `doc-howto`): billing account on the company project, enabling Cloud Run, Scheduler and Secret Manager, a Tier 1 region, the cloud's own link of the student's Gmail (research R3) stored as a secret, the OAuth client and the Claude key of the `alfabeta` workspace as secrets, the configuration as a secret mounted at `/config`, the job, the Scheduler job with `[cloud] schedule`, and how to read a run's log. No project id, region or secret value in the page.
- [ ] T019 [US1] Run quickstart step 5 with the Mac off; record the time from upload to page in `specs/005-notes-to-notebook/research.md` as a dated fact.

---

## Phase 4: User Story 5 - A topic's notebook gets its living files once (P3, needed by US1's test)

**Goal**: each topic has its two living files as notebook sources.

**Independent test**: quickstart step 1.

- [ ] T020 [US5] Write `NotebookSources` and `NlmSources` in `src/alfabeta/notes/sources.py`: `add_drive_source(notebook, file_id, title)` with `nlm source add --drive <id> --type pdf --wait --json --profile <profile>`, `list_sources(notebook)`; map "not signed in" to exit 5. Mac only; the cloud image never calls it.
- [ ] T021 [US5] Write `setup_topic` in `src/alfabeta/notes/setup.py`: create `Apuntes · Tema NN.pdf` and `Classroom · Tema NN.pdf` (cover page only) when missing, add each as a source, record `source_id`; list plain file sources whose title starts with «Apuntes ·» or «Classroom ·» as `plain_sources_to_remove`; remove nothing (FR-010).
- [ ] T022 [P] [US5] Test `tests/test_notes_setup.py` with a fake `NotebookSources`: first run adds two sources, second adds none; plain sources listed, never removed; a missing notebook exits 1 `no_notebook`.
- [ ] T023 [US5] Add `notebook setup --student <id> --topic <folder>` to `src/alfabeta/__main__.py` per `contracts/cli.md`, with its test in `tests/test_notes_cli.py`.
- [ ] T024 [US5] Run quickstart steps 1 to 3 on a test topic.

---

## Phase 5: Family files reach the master (FR-002, serves US1)

**Goal**: what the student uploads in Drive reaches the master on the Mac. Must ship before spec
004's slice 4 moves the master out of the Drive for desktop mount.

- [ ] T025 [US1] Write `pull_family_files` in `src/alfabeta/notes/pull.py`: its own cursor in `data/drive/pull.json`; download into the master every file under a topic folder without `appProperties.origin = "alfabeta"`, outside `.alfabeta/` and `Informes/`, whose md5 the master does not already hold; never delete in the master (research R10).
- [ ] T026 [P] [US1] Test `tests/test_notes_pull.py`: a family photo is pulled; an alfabeta file is not; a file already in the master by checksum is skipped; a deleted Drive file deletes nothing.
- [ ] T027 [US1] Add `drive pull --student <id>` to `src/alfabeta/__main__.py` per `contracts/cli.md` and call it at the start of spec 001's sync run, before classroom-sync writes.

---

## Phase 6: User Story 3 - New Classroom material reaches the notebook (P2)

**Goal**: each Classroom item in `classroom/` becomes a cover page and its pages in
`Classroom · Tema NN.pdf`.

**Independent test**: quickstart step 6.

- [ ] T028 [US3] Extend `run_notes` in `src/alfabeta/notes/run.py`: for each `classroom_item`, build its `ClassroomEntry` from the name `YYYYMMDD - <title>`; a PDF is copied page by page, a Google-native file is exported to PDF through `ScopedDrive`, a link or video is its cover alone with the address from classroom-sync's sidecar; a new md5 for the same `file_id` replaces its pages in place; order by posting date.
- [ ] T029 [P] [US3] Test in `tests/test_notes_run.py`: one item added once; a changed item replaced in place; a second run with nothing new writes nothing; a link with 0 pages.
- [ ] T030 [US3] Run quickstart step 6.

---

## Phase 7: User Story 2 - The student corrects a transcription (P2)

**Goal**: « (revisada)» and « (mal)» on a transcription's PDF change its page's heading; a
correction replaces the page.

**Independent test**: quickstart step 4.

- [ ] T031 [US2] Extend `run_notes`: a rename of a transcription PDF ending in « (revisada)» sets `review = checked`, « (mal)» sets `review = wrong` and adds the page to the report; a new photo or Markdown for the same page replaces `pdf_id`/`markdown_id` and resets `review` to `automatic` (research R7).
- [ ] T032 [P] [US2] Test in `tests/test_notes_run.py`: each mark and its heading; a correction replaces the page once.
- [ ] T033 [US2] Run quickstart step 4.

---

## Phase 8: User Story 4 - The family learns what changed and what it adds (P2)

**Goal**: a report in Spanish after any run that changed something, and none otherwise.

**Independent test**: approve notes holding an idea the pack misses; the report names it.

- [ ] T034 [US4] Write `write_report` in `src/alfabeta/notes/report.py`: `Informes/Informe AAAAMMDD-HHMM.md` in Spanish with the per-topic counts of `RunReport`, marks, unexpected files, `waiting_setup`, failures and spend; "what it adds" by one Claude call per changed topic given the new pages and the topic's study guide text, skipped with a line when there is no guide or the budget is spent (research R8).
- [ ] T035 [P] [US4] Test `tests/test_notes_report.py`: no report when nothing changed; spend summed from recorded `usage`; no student name, address or id in the text (the guardrail's detectors over the output).
- [ ] T036 [US4] Add to spec 001's agenda one line per new report, pointing at it, in `src/alfabeta/` where the agenda is written (spec 001).
- [ ] T037 [US4] Run quickstart step 7 (budget stop, exit 4; transcription stops, the Classroom step still runs).

---

## Phase 9: Polish

- [ ] T038 [P] Update `skills/study-pack/SKILL.md` step 1: notes reach the notebook as automatic transcriptions through the living notes file (spec 005), no check required; the ranking of the notes first is unchanged.
- [ ] T039 [P] Update `docs/explanation/study-material.md` with the living files and why the notebook follows a Drive file instead of gaining sources.
- [ ] T040 Run US5 scenario 2 on Tema 01 of 2026-2027: set up its living files, move its notes into `Apuntes · Tema 01.pdf`, report the two plain sources for the family to remove.
- [ ] T041 Run quickstart step 8 for two weeks and record SC-001's result in `specs/005-notes-to-notebook/research.md`.

---

## Dependencies

- Phase 1 → Phase 2 → every story.
- Spec 004's `drive.py` (slice 3) before T006, T008, T014, T025, T028.
- US1 (Phase 3) needs US5's T020–T023 for its notebook check; T024 proves both.
- Phase 5 (pull) depends only on Phase 2 and spec 004's `drive.py`; it runs in parallel with
  Phases 3, 4 and 6 to 8, and must ship before spec 004's slice 4.
- US3, US2 and US4 each extend `run.py` after T014; they touch the same file, so they go one after
  another, in that order.

## Parallel examples

- Phase 2: T005, T007, T009 and T011 once their modules exist.
- Phase 3 and Phase 5: T012–T016 and T025–T027 by two people, different files.
- Phase 9: T038 and T039.

## Implementation strategy

1. **MVP**: Phases 1 to 4. One photo from the phone, with the Mac off, becomes a page the notebook
   answers about (quickstart steps 1, 3 and 5).
2. Phase 5 before spec 004 moves the master folder.
3. Then US3, US2, US4, each proved by its quickstart step.
4. Tema 01 and two weeks of real use close the spec.
