# Tasks: Class notes and new material reach the topic's notebook by themselves

**Input**: Design documents from `specs/005-notes-to-notebook/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: included. The plan asks for one test module per module. Drive answers are recorded
responses with invented values (spec 004 research R8); Claude answers are recorded with invented
content; `nlm` is a fake; image fixtures are drawn by the tests. No test calls Google, Claude or
`nlm`. The live proof is the quickstart's.

**Depends on spec 004**: the transport, OAuth refresh and keychain (built), and its scoped Drive
adapter `src/alfabeta/google/drive.py` with the folder allowlist (spec 004 slice 3, not built), plus
its `uploads.jsonl` (slice 4). Every Drive task below goes through that adapter.

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

- [ ] T004 Write the domain values in `src/alfabeta/notes/model.py` from `data-model.md`: `Topic` keyed by folder id "never by name"; `Arrival` with kinds `notes_photo`, `notes_transcript`, `notes_text`, `classroom_item`, `living_file`, `unexpected` and `version` = md5 or `modifiedTime`; notes-photo states `seen` → `transcribed` → `in_living_file` plus `duplicate`, `unsupported`, `unreadable`, `failed` ("retried on the next three runs, then `failed_final`"), `budget_wait`, `gone`; Classroom states `seen` → `in_living_file` plus `failed`, `gone`; `NotesPage` (`review` `automatic`/`checked`/`wrong`, `source` `claude`/`adopted`); `LivingFile` ("`file_id` set only by `notebook setup`, never changes once set"; `health` `ok`/`missing`); `ClassroomEntry` keyed by item with `parts` kinds `pdf`, `export`, `office`, `text`, `image`, `named`; `ChangeCursor`; `RunLog`; `RunReport`; and a `Clock` port. No I/O.
- [ ] T005 [P] Test in `tests/test_notes_model.py`: every transition; "same version → duplicate"; the retry cap; a persisting state is not a reportable change, a new one is.
- [ ] T006 Extend spec 004's `ScopedDrive` in `src/alfabeta/google/drive.py` with `changes(page_token)` and `start_page_token()`: page through `changes.list` with the fields of research R2, drop every change whose parents are outside the allowlist inside the adapter, add new folders inside it to the allowlist, return only kept changes, and log nothing about dropped ones (spec 004 FR-009a as amended). Extend spec 004's scope test in `tests/test_google_drive.py` to the feed: a recorded page mixing inside and outside changes returns only the inside ones, and the log holds no outside name or id.
- [ ] T007 Write `StateStore` and `DriveStateStore` in `src/alfabeta/notes/state.py`: read and write `.alfabeta/estado.json` through `ScopedDrive`; remember `headRevisionId` at read, re-read it immediately before writing, and on a difference stop without writing and retry the caller once (research R4); write nothing when the state is unchanged; write `.alfabeta/ultima-ejecucion.json` at the end of every run.
- [ ] T008 [P] Test in `tests/test_notes_state.py`: round trip; refusal and one retry on a changed revision; no write of `estado.json` when unchanged, the run log written every time.
- [ ] T009 Write `ChangeFeed` and `DriveChangeFeed` in `src/alfabeta/notes/changes.py` over T006: map each kept change to an `Arrival` by its folder (`apuntes/`, `classroom/` and the item it belongs to, topic root), skip `.alfabeta/` and `Informes/`; with no cursor, take `start_page_token()` first and list the tree once (FR-004); detect a removed or trashed file as `gone`.
- [ ] T010 [P] Record `changes.list` pages and a tree listing with invented values in `tests/fixtures/notes/` and test in `tests/test_notes_changes.py`: each kind; a rename arriving as a change; a file inside an item folder mapped to that item; first-run listing; `gone`.
- [ ] T011 Write `PdfBuilder` and `ReportlabPdfBuilder` in `src/alfabeta/notes/pdf.py`: cover page; a notes page (photo scaled to the page, then the transcription with research R5's conventions rendered, headed «Transcripción automática», «Revisada por el alumno» or «En corrección»); a Classroom entry (cover with title, posting date, description and addresses, then each part: `pdf` copied with `pypdf`, `export` and `office` from the PDF Drive returns, `text` set as text, `image` one page, `named` on the cover only). Fixed metadata and creation date so the same input gives the same bytes (research R6).
- [ ] T012 [P] Test in `tests/test_notes_pdf.py`: two builds of the same records have the same checksum; page order; each heading; each part kind; drawn image fixtures, never photos.

---

## Phase 3: User Story 1 and User Story 5 on the Mac — a photo becomes a page (P1) — MVP part 1

**Goal**: one photo in `apuntes/` becomes a page of `Apuntes · <topic>.pdf`, the notebook answers
about it, run from the Mac.

**Independent test**: quickstart steps 1 to 3.

- [ ] T013 [US1] Write `Transcriber` and `ClaudeTranscriber` in `src/alfabeta/notes/transcribe.py`: one Messages API call per photo through `HttpTransport`, image first, research R5's instructions, model from `[notes] model`, key from a `TokenStore` (the keychain on the Mac); JPEG, PNG and WebP up to 10 MB only, anything else `unsupported` without a call; return Markdown and `usage`; a credit or spend-limit refusal → `budget_wait`; any other error → `failed`.
- [ ] T014 [P] [US1] Record a Claude answer with invented content and a credit refusal in `tests/fixtures/notes/` and test `tests/test_notes_transcribe.py`: request shape (image block before text); an unsupported format makes no call; the key in no log line; `budget_wait` on refusal.
- [ ] T015 [US5] Write `NotebookSources` and `NlmSources` in `src/alfabeta/notes/sources.py`: `add_drive_source(notebook, file_id, title)` with `nlm source add --drive <id> --type pdf --wait --json --profile <profile>`, `list_sources(notebook)`; "not signed in" → exit 5. Mac only; the cloud image never imports it.
- [ ] T016 [US5] Write `setup_topic` in `src/alfabeta/notes/setup.py`: when no `file_id` is recorded, create `Apuntes · <topic>.pdf` and `Classroom · <topic>.pdf` from what is recorded (a cover page when nothing is); add each as a source; record `file_id` and `source_id` through `DriveStateStore` (its revision check); list plain sources whose titles start with «Apuntes ·» or «Classroom ·» as `plain_sources_to_remove`; remove nothing (FR-011).
- [ ] T017 [P] [US5] Test `tests/test_notes_setup.py` with a fake `NotebookSources`: first run creates two files and adds two sources; second run creates and adds nothing; a recorded but deleted living file is reported, not recreated; plain sources listed, never removed; no notebook → exit 1 `no_notebook`.
- [ ] T018 [US1] Write `run_notes` in `src/alfabeta/notes/run.py` for notes: read state and cursor through `Clock`; for each new `notes_photo`, adopt a Markdown section that embeds it by name (`source = adopted`, no call), else skip it as `duplicate` when its version is known, else transcribe and write the PDF and Markdown next to the photo with Spanish names, record the `NotesPage`; for each topic with a `file_id`, check its living files' parent and `trashed` (else `missing`, reported) and rebuild a changed one, uploading a new revision of the same `file_id` only when its checksum changed; a topic without `file_id` is `waiting_setup` and no file is created; warn above `[notes] warn_pages`; save the state, then the cursor only if it moved or something was written, then the run log.
- [ ] T019 [P] [US1] Test `tests/test_notes_run.py` with fakes for every port: one photo → one page; a second run with nothing new writes only the run log (SC-004); the same photo twice → one page and a duplicate; Tema 01's form (one Markdown, a section per photo) → pages adopted with zero Claude calls; a crash before the cursor is saved → the next run repeats nothing; `waiting_setup` creates no file; a living file over `warn_pages` is reported; the run calls no study-pack generation (FR-012).
- [ ] T020 [US1] Add `notes run` and `notebook setup` to `src/alfabeta/__main__.py` with the output and exit codes of `contracts/cli.md` (highest code wins; a spent budget exits 0), and test the JSON shapes in `tests/test_notes_cli.py`.
- [ ] T021 [US5] Run quickstart steps 1 to 3 on a test topic.

---

## Phase 4: User Story 1 in the cloud — with the Mac off (P1) — MVP part 2

**Goal**: the same pass runs every 15 minutes in the operator's Google Cloud project for alfabeta.

**Independent test**: quickstart step 5.

- [ ] T022 [US1] Add `--scopes` and `--print-token` to spec 004's `google link` in `src/alfabeta/google/accounts.py` and `src/alfabeta/__main__.py` (contracts/cli.md): ask only for the listed scopes, write `{client_id, client_secret, refresh_token}` as one JSON line to stdout, keep nothing in the keychain or on disk, refuse when stdout is a terminal (`stdout_is_terminal`). Test in `tests/test_google_accounts.py`.
- [ ] T023 [US1] Write `FileTokenStore` in `src/alfabeta/notes/secrets.py`: spec 004's `TokenStore` over `/secrets/google/link.json` and `/secrets/claude/key`, read-only; test in `tests/test_notes_secrets.py` that a missing file is a clear `no_token`, never a traceback with a path.
- [ ] T024 [US1] Write `deploy/notes-cloud-run/Dockerfile` (Python 3.12 slim, the package installed with `uv --locked`, without `sources.py`'s `nlm`) and its entry script: copy `/secrets/config/config.toml` to a writable temporary home and run `python -m alfabeta --home <tmp> notes run --student "$STUDENT"` with `FileTokenStore`. `deploy/notes-cloud-run/README.md` points to the how-to.
- [ ] T025 [US1] Write `docs/how-to/notes-cloud-run.md` (layered how-to, `doc-howto`): billing account on the project, enabling Cloud Run, Scheduler, Secret Manager and Monitoring; a Tier 1 region; the cloud's own link (`google link … --scopes drive --print-token | gcloud secrets versions add …`); the Claude key of the `alfabeta` workspace and the configuration as the other two secrets; the job (one task, one execution at a time, 10-minute timeout) with the three secrets mounted as files; the Scheduler job with `[cloud] schedule`; an alert policy emailing the operator on a failed execution; checking the three free Scheduler jobs are not already used; reading a run's log. No project id, region or secret value in the page.
- [ ] T026 [US1] Add the staleness check of FR-017 to `src/alfabeta/notes/pull.py` (`cloud_last_ok`): read `.alfabeta/ultima-ejecucion.json` with the Mac's link; older than `[notes] cloud_stale_hours` → an agenda line and a macOS notification (spec 004 R9's `notify`); test in `tests/test_notes_pull.py`.
- [ ] T027 [US1] Run quickstart step 5 with the Mac off; record the delay in `specs/005-notes-to-notebook/research.md` as a dated fact.

---

## Phase 5: Drive's files reach the master (FR-002, serves US1)

**Goal**: everything Drive holds under a topic folder reaches the master, and the mirrors. Must ship
before spec 004's slice 4 moves the master out of the Drive for desktop mount.

- [ ] T028 [US1] Write `pull_family_files` in `src/alfabeta/notes/pull.py`: its own cursor in `data/drive/pull.json`; download into the master every file under a topic folder outside `.alfabeta/` whose Drive id `uploads.jsonl` does not record; record each as an `UploadRecord` with `how = "adopted"`; a path that already exists in the master is never overwritten: write beside it with « (de Drive)» and report it; never delete in the master (research R10).
- [ ] T029 [P] [US1] Test `tests/test_notes_pull.py`: a family photo and a cloud transcription are pulled; a file the Mac uploaded is not; an existing path is written beside, not overwritten; a deleted Drive file deletes nothing; pull then spec 004's `drive push` uploads 0.
- [ ] T030 [US1] Add `drive pull` to `src/alfabeta/__main__.py` per `contracts/cli.md` and call it at the start of spec 001's sync run, before classroom-sync writes.

---

## Phase 6: User Story 3 - New Classroom material reaches the notebook (P2)

**Goal**: each Classroom item becomes one entry in `Classroom · <topic>.pdf`.

**Independent test**: quickstart step 6.

- [ ] T031 [US3] Extend `run_notes` in `src/alfabeta/notes/run.py`: build a `ClassroomEntry` per item (a file, a `.md` note, or a folder with its files, `descripcion.md` and `enlaces.md`) from `YYYYMMDD - <title>`; render parts per research R6 (Office files copied to the Google type through `ScopedDrive`, exported, the copy put in Drive's trash at once); a new `item_version` replaces the entry's pages in place; order by posting date.
- [ ] T032 [P] [US3] Test in `tests/test_notes_run.py`: one file item added once; a folder with a PDF, a Word file and `descripcion.md` → one entry; a links-only folder → cover with addresses; a changed item replaced in place; a second run with nothing new writes only the run log.
- [ ] T033 [US3] Run quickstart step 6 and record SC-003's delay.

---

## Phase 7: User Story 2 - The student corrects a transcription (P2)

**Goal**: marks change a page's heading; a correction replaces the page.

**Independent test**: quickstart step 4.

- [ ] T034 [US2] Extend `run_notes`: a rename of a `notes_transcript` ending in « (revisada)» sets `review = checked`, « (mal)» sets `review = wrong`; a photo named like a page's photo plus « (corregida)» replaces its photo and transcription keeping `order`; a new `markdown_version` re-renders the page from the Markdown without calling Claude; either resets `review` to `automatic` (research R7).
- [ ] T035 [P] [US2] Test in `tests/test_notes_run.py`: each mark and its heading; each correction replaces the page once, in place.
- [ ] T036 [US2] Run quickstart step 4.

---

## Phase 8: User Story 4 - The family learns what changed and what it adds (P2)

**Goal**: a report in Spanish after any run that changed something, none otherwise, and a repeating
failure reported once.

**Independent test**: upload notes holding an idea the study guide misses; the report names it.

- [ ] T037 [US4] Write `write_report` in `src/alfabeta/notes/report.py`: `Informes/Informe AAAAMMDD-HHMM.md` in Spanish with the state changes of `RunReport` since the last report, and the month's spend at `[notes] price_in`/`price_out`; "what it adds" by one Claude call per changed topic given the new pages and the study guide section of `Tema NN para imprimir · <title>.pdf` extracted with `pypdf`, skipped with a line when that PDF is missing or the budget is spent (research R8).
- [ ] T038 [P] [US4] Test `tests/test_notes_report.py`: no report when nothing changed; a repeating failure appears once and its clearing once; spend summed from recorded `usage`; the guardrail's detectors find no name, address or id in the output.
- [ ] T039 [US4] In the Mac's sync, list `Informes/` through `ScopedDrive` and add one agenda line per report not listed before (spec 001's agenda module).
- [ ] T040 [US4] Run quickstart step 7.

---

## Phase 9: Polish

- [ ] T041 [P] Update `skills/study-pack/SKILL.md` step 1: notes reach the notebook as automatic transcriptions through the living notes file (spec 005), no check required; the ranking of the notes first is unchanged.
- [ ] T042 [P] Update `docs/explanation/study-material.md` with the living files and why the notebook follows a Drive file instead of gaining sources.
- [ ] T043 Run US5 scenarios 2 and 4 on Tema 01 of 2026-2027: `notebook setup` adopts its Markdown, builds `Apuntes · <topic>.pdf`, and lists the two plain sources for the family to remove.
- [ ] T044 [P] Add to `tests/test_guardrail.py` a case that a run report and a run log with invented values pass, and one with a planted address fails (SC-008).
- [ ] T045 Run quickstart step 8 for two weeks and record SC-001 and SC-005 in `specs/005-notes-to-notebook/research.md`, as aggregates only.

---

## Dependencies

- Phase 1 → Phase 2 → every story.
- Spec 004's `drive.py` (slice 3) before T006; spec 004's `uploads.jsonl` (slice 4) before T028.
- Phase 3 (Mac) before Phase 4 (cloud): the cloud job runs the same pass.
- Phase 5 depends only on Phase 2 and spec 004; it can run beside Phases 3, 4 and 6 to 8, and must
  ship before spec 004's slice 4 moves the master folder.
- Phases 6, 7 and 8 each extend `run.py` after T018; same file, so one after another, in that order.

## Parallel examples

- Phase 2: T005, T008, T010 and T012 once their modules exist.
- Phase 3 and Phase 5: T013–T020 and T028–T030 by two people, different files.
- Phase 9: T041, T042 and T044.

## Implementation strategy

1. **MVP**: Phases 1 to 4. One photo from the phone, with the Mac off, becomes a page the notebook
   answers about (quickstart steps 1, 3 and 5).
2. Phase 5 before spec 004 moves the master folder.
3. Then US3, US2, US4, each proved by its quickstart step.
4. Tema 01 and two weeks of real use close the spec.
