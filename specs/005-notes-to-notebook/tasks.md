# Tasks: Class notes and new material reach the topic's notebook by themselves

**Input**: Design documents from `specs/005-notes-to-notebook/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: included. The plan asks for one test module per module. Drive answers are recorded
responses with invented values (spec 004 research R8); Claude answers are recorded with invented
content; `nlm` is a fake; image fixtures are drawn by the tests. No test calls Google, Claude or
`nlm`. The live proof is the quickstart's.

**Depends on spec 004**: the transport, OAuth refresh and keychain (built); its scoped Drive adapter
`src/alfabeta/google/drive.py` (its T025); its `notify.py` (its T015); and the pull into the master,
FR-011a, added to spec 004 by this pull request as its T029a and T029b. The pull carries FR-002 of
this spec and must ship before spec 004 moves the master out of the Drive for desktop mount.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1 a photo reaches the notebook · US2 the student corrects · US3 Classroom items ·
  US4 the report · US5 a topic's living files

---

## Phase 1: Setup

- [ ] T001 Add the keys of `specs/005-notes-to-notebook/contracts/config-template.toml` (`[notes]` and the new `[notebook]` keys; `[cloud]` is added by T025, the first task that reads it, so no configuration carries unset keys before then) to `config/template.toml`, each with its comment; read them in `src/alfabeta/config.py`; run `tests/test_template_covers_reads.py`.
- [ ] T002 Add `reportlab` and `pypdf` to `pyproject.toml` as runtime dependencies with exact pins, update `uv.lock`, and say beside each pin, in one comment, why the standard library is not enough (plan, Complexity Tracking).
- [ ] T003 [P] Create `src/alfabeta/notes/__init__.py` and `tests/fixtures/notes/README.md`; the README says every file is a recorded response with invented values, named `<call>-<YYYY-MM-DD>.json`, and that images are drawn by the tests, never photos of real notes.

---

## Phase 2: Foundational (blocks every story)

- [ ] T004 Write the domain values in `src/alfabeta/notes/model.py` from `data-model.md`: `Topic` keyed by folder id "never by name"; `Arrival` with kinds `notes_photo`, `notes_transcript`, `notes_text`, `classroom_item`, `living_file`, `unexpected`, `version` = md5 or `modifiedTime`, and `own` ("a change to it is consumed, never an arrival"); notes-photo states `seen` → `transcribed` → `in_living_file` plus `duplicate`, `unsupported`, `unreadable`, `failed` ("retried on the next three runs, then `failed_final`"), `budget_wait`, `gone`; Classroom states `seen` → `in_living_file` plus `failed`, `gone`; `NotesPage` (`review` `automatic`/`checked`/`wrong`, `source` `claude`/`adopted`, `order` "the order pages were first seen"); `LivingFile` ("`file_id` set only by `notebook setup`, never changes once set"; `health` `ok`/`missing`); `ClassroomEntry` keyed by item with `parts` kinds `pdf`, `export`, `office`, `text`, `image`, `named`; `RunLog` with `last_ok_ended` and `page_token`; `RunReport`; `SpendLedger`; and a `Clock` port. No I/O.
- [ ] T005 [P] Test in `tests/test_notes_model.py`: every transition; "same version → duplicate"; the retry cap; a persisting state is not a reportable change, a new one is; a failed run keeps `last_ok_ended` and the previous `page_token`.
- [ ] T006 Extend spec 004's `ScopedDrive` in `src/alfabeta/google/drive.py` with `start_page_token()` and `changes(page_token, known_ids)`: page through `changes.list` with the fields of research R2; keep a change whose parents are in the allowlist or whose file id is in `known_ids` (so a recorded file removed or moved out arrives); add a folder that joins the allowlist and list its tree once; drop everything else inside the adapter and log nothing about it (spec 004 FR-009a as amended). Extend spec 004's scope test in `tests/test_google_drive_scope.py` to the feed: a recorded page mixing inside, outside and recorded-but-moved-out changes returns only the first and last, and the log holds no outside name or id.
- [ ] T007 Write `NotesStateStore` and `DriveNotesStateStore` in `src/alfabeta/notes/state.py`: read and write `.alfabeta/state.json` through `ScopedDrive`; remember `headRevisionId` at read, re-read it immediately before writing, and on a difference stop without writing and retry the caller once (research R4); write `state.json` only when a record changed; write `.alfabeta/last-run.json` (the `RunLog`, with the cursor) at the end of every run; record every file it writes as `own`.
- [ ] T008 [P] Test in `tests/test_notes_state.py`: round trip; refusal and one retry on a changed revision; no write of `state.json` when unchanged; the run log written every time.
- [ ] T009 Write `ChangeFeed` and `DriveChangeFeed` in `src/alfabeta/notes/changes.py` over T006: pass the recorded ids; consume changes to `own` files (research R2, echoes), except a new name of a `notes_transcript` (a mark) and a `notes_text` whose checksum differs from the one alfabeta recorded (a correction); map the rest to an `Arrival` by folder (`apuntes/`, `classroom/` and the item a file belongs to, topic root); skip `.alfabeta/` and `Informes/`; with no cursor, take `start_page_token()` first and list the tree once (FR-004); a removed, trashed or moved-out recorded file is `gone`.
- [ ] T010 [P] Record `changes.list` pages and a tree listing with invented values in `tests/fixtures/notes/` and test in `tests/test_notes_changes.py`: each kind; a rename of an own transcription PDF arriving as a mark, not consumed; a file inside an item folder mapped to that item; the first-run listing; `gone`; a page holding only the previous run log's change plus an outside change yields no arrival.
- [ ] T011 Write `PdfBuilder` and `ReportlabPdfBuilder` in `src/alfabeta/notes/pdf.py`: cover page; a notes page (photo scaled to the page, then the transcription with research R5's conventions rendered, headed «Transcripción automática», «Revisada por el alumno» or «En corrección»); a Classroom entry (cover with title, posting date, description and addresses, then each part: `pdf` copied with `pypdf`, `export` and `office` from the PDF Drive returns, `text` set as text, `image` one page, `named` on the cover only); never a file in an `entrega/` subfolder or whose name starts with `entrega - ` or `correccion`, nor a `(anterior YYYY-MM-DD)` version. Fixed metadata and creation date so the same input gives the same bytes (research R6).
- [ ] T012 [P] Test in `tests/test_notes_pdf.py`: two builds of the same records have the same checksum; page order; each heading; each part kind; drawn image fixtures, never photos.

---

## Phase 3: User Story 1 and User Story 5 on the Mac — a photo becomes a page (P1) — MVP part 1

**Goal**: one photo in `apuntes/` becomes a page of `Apuntes · <topic>.pdf`, the notebook answers
about it, run from the Mac.

**Independent test**: quickstart steps 1 to 3.

- [ ] T013 [US1] Write `Transcriber` and `ClaudeTranscriber` in `src/alfabeta/notes/transcribe.py`: one Messages API call per photo through `HttpTransport`, image first, research R5's instructions, model from `[notes] model`, key from a `TokenStore` (the Mac's own key in the keychain); JPEG, PNG and WebP up to 10 MB only, anything else `unsupported` without a call; return Markdown and `usage`; the single line `[ilegible: página completa]` → `unreadable`; a credit or spend-limit refusal → `budget_wait`; any other error → `failed`.
- [ ] T014 [P] [US1] Record a Claude answer with invented content and a credit refusal in `tests/fixtures/notes/` and test `tests/test_notes_transcribe.py`: request shape (image block before text); an unsupported format makes no call; the unreadable answer → `unreadable`; the key in no log line; `budget_wait` on refusal.
- [ ] T015 [US5] Write `NotebookSources` and `NlmSources` in `src/alfabeta/notes/sources.py`: `find_notebook(title)` with `nlm notebook list --json --profile <profile>`, `add_drive_source(notebook, file_id, title)` with `nlm source add --drive <id> --type pdf --wait --json --profile <profile>`, `list_sources(notebook)`; "not signed in" → exit 5. Mac only; the cloud image does not include it.
- [ ] T016 [US5] Write `setup_topic` in `src/alfabeta/notes/setup.py` for `--topic <subject>/<folder>`: find the notebook by `[notebook] title_pattern` with `[notebook] nlm_profile`; run the recording pass of `run_notes` for the topic first (so an adopted Markdown is in the first build); when no `file_id` is recorded, create `Apuntes · <topic>.pdf` and `Classroom · <topic>.pdf` from what is recorded (a cover page when nothing is); share each read-only with the account in `[notebook] owner`, and nothing else in the folder; add each as a source; record `file_id` and `source_id` through `DriveNotesStateStore`; list sources titled «Apuntes ·…» or «Classroom ·…» whose id is not a recorded living source as `plain_sources_to_remove`; remove nothing (FR-011).
- [ ] T017 [P] [US5] Test `tests/test_notes_setup.py` with a fake `NotebookSources`: first run creates two files, shares exactly those two with the owner, and adds two sources; second run creates, adds and lists nothing (its own living sources are not listed); a recorded but deleted living file is reported, not recreated; Tema 01's plain sources are listed, never removed; no notebook → exit 1 `no_notebook`; the address in `[notebook] owner` appears in no output, log or report line.
- [ ] T018 [US1] Write `run_notes` in `src/alfabeta/notes/run.py` for notes: read state and run log through `Clock`; for each new `notes_photo`, adopt a Markdown section that embeds it by name (`source = adopted`, no call, and write its PDF), else skip it as `duplicate` when its version is known, else transcribe and write `<photo name> · transcripción.pdf` and `.md` next to the photo, each with `properties.alfabeta_for = <photo id>`, first looking for an existing file with that property in the folder and updating it instead of creating (research R4); append pages in first-seen order; for each topic with a `file_id`, check its living files' parent and `trashed` (else `missing`, reported) and rebuild a changed one, uploading a new revision of the same `file_id` only when its checksum changed; a topic without `file_id` is `waiting_setup` and no file is created; warn above `[notes] warn_pages`; write the state only if a record changed, then the run log.
- [ ] T019 [P] [US1] Test `tests/test_notes_run.py` with fakes for every port: one photo → one page; a second run with nothing new writes only the run log (SC-004); a run whose feed holds only the previous run log's change leaves `state.json` untouched; the same photo twice → one page and a duplicate; Tema 01's form (one Markdown, a section per photo) → pages adopted with zero Claude calls; a crash after a transcription upload and before the run log → the next run finds it by `alfabeta_for` and creates no second one; two overlapping passes leave one transcription per photo; `waiting_setup` creates no file; a living file over `warn_pages` is reported; the run calls no study-pack generation (FR-012).
- [ ] T020 [US1] Add `notes run` and `notebook setup` to `src/alfabeta/__main__.py` with the output and exit codes of `contracts/cli.md` (highest code wins; a spent budget exits 0), and test the JSON shapes in `tests/test_notes_cli.py`.
- [ ] T021 [US1] Run quickstart steps 1 to 3 on a test topic.

---

## Phase 3b: User Story 1 — the owner's refresh on the Mac, with no app open (P1)

**Goal**: a page that reached a living file reaches the student's view of the notebook with nobody
touching it as its owner (FR-018, FR-019, SC-002).

**Independent test**: quickstart step 3b.

- [ ] T043 [US1] Extend `NotebookSources` and `NlmSources` in `src/alfabeta/notes/sources.py`: `read_source(source_id)` with `nlm source content <id> --profile <[notebook] nlm_profile>`, whose output is discarded and never logged; `session_ok()` with `nlm login --check --profile <profile>`; `renew_session()` with `nlm auth refresh --profile <profile>` in its default mode, never `--http-only` (research R14). Mac only, like the rest of the module.
- [ ] T044 [US1] Write `RefreshRecord` in `src/alfabeta/notes/model.py`, and `RefreshStore`, `LocalRefreshStore` and `refresh_sources` in `src/alfabeta/notes/refresh.py`: the record is `notebook-refresh.json` in the student's data folder, user-only, written only when a field changes (data-model.md); a pass reads `state.json` through `DriveNotesStateStore` over spec 004's `ScopedDrive` with its cached tree, listing no folder, and selects the living files with a `source_id`, `health = ok` and a `built_md5` that differs from the record's `read_md5`; with none selected it returns without calling `nlm`; otherwise it checks the session, renews it once if it fails, and reads each selected source once and records its checksum; a session that still fails sets `session = signed_out`, and only when that is a change gives FR-019's notice through spec 004's `notify` and an agenda line (spec 001's agenda module), then exits 5.
- [ ] T045 [P] [US1] Test `tests/test_notes_refresh.py` with a fake `NotebookSources` and a fake state store: an idle pass makes no `nlm` call and writes no record (SC-004); one changed living file → one read, its checksum recorded, and the next pass reads nothing; a `missing` living file is not read; a failing session → one renewal, then the notice once and code 5; a second failing pass → no second notice; a pass that finds the session working again and a later failure → a new notice; no source id, checksum or address appears in any output or log line.
- [ ] T046 [US1] Add `notebook refresh` and `notebook agent install|remove` to `src/alfabeta/__main__.py` with the output and exit codes of `contracts/cli.md`, and write `LaunchdAgent` in `src/alfabeta/notes/agent.py`: a plist whose label comes from the student id, never a name; `ProgramArguments` running `notebook refresh --student <id>` through `uv run --project <tools.repository>` with the `uv` path resolved at install; one `StartCalendarInterval` entry every `[notebook] refresh_minutes`, refusing a value that does not divide 60, and `RunAtLoad`; standard output and error in the student's data folder; loaded and unloaded with `launchctl bootstrap` and `bootout` in the user's GUI domain; installing again rewrites the plist only when it differs. Add `[notebook] refresh_minutes` to `config/template.toml`. Test the plist and the JSON shapes in `tests/test_notes_agent.py` with a fake `launchctl`.
- [ ] T047 [US1] Run quickstart step 3b on a test topic and record the result in `specs/005-notes-to-notebook/research.md`.

---

## Phase 4: User Story 1 in the cloud — with the Mac off (P1) — MVP part 2

**Goal**: the same pass runs every 15 minutes in the operator's Google Cloud project for alfabeta.

**Independent test**: quickstart step 5.

- [ ] T022 [US1] Add `--client-file`, `--scopes` and `--print-token` to spec 004's `google link` in `src/alfabeta/google/accounts.py` and `src/alfabeta/__main__.py` (contracts/cli.md): use the client in the file, never the keychain's; ask for the listed scopes plus `openid` and `email`; validate the grant against what was asked (spec 004's account check, unchanged otherwise); write `{client_id, client_secret, refresh_token}` as one JSON line to stdout; keep nothing in the keychain or on disk; refuse when stdout is a terminal (`stdout_is_terminal`). Test in `tests/test_google_accounts.py`, including that the keychain is never read or written.
- [ ] T022b [US1] Add `claude key set --student <id>` to `src/alfabeta/__main__.py` (contracts/cli.md): read the Mac's own Claude key from standard input into the keychain; refuse an empty key. Test in `tests/test_notes_cli.py`. Built with phase 3 (julioarguello/alfabeta#66): quickstart step 3 needs the Mac's key, so it lands before the rest of phase 4.
- [ ] T023 [US1] Write `FileTokenStore` in `src/alfabeta/notes/secrets.py`: spec 004's `TokenStore` over `/secrets/google/link.json` and `/secrets/claude/key`, read-only; and a log-only `Notifier` for the cloud, where spec 004's `MacNotifier` cannot run. Test in `tests/test_notes_secrets.py` that a missing file is a clear `no_token`, never a traceback with a path.
- [ ] T024 [US1] Write `deploy/notes-cloud-run/Dockerfile` (Python 3.12 slim, the package installed with `uv --locked`, without `notes/sources.py`) and its entry script: copy `/secrets/config/config.toml` to a writable temporary home, read the student id from it, and run `python -m alfabeta --home <tmp> notes run --student <id>` with `FileTokenStore`; a missing Claude key exits 3. `deploy/notes-cloud-run/README.md` points to the how-to.
- [ ] T025 [US1] Add the `[cloud]` keys of `contracts/config-template.toml` to `config/template.toml`, then write `docs/how-to/notes-cloud-run.md` (layered how-to, `doc-howto`): billing account on the project; enabling Cloud Run, Scheduler, Secret Manager, Cloud Build, Artifact Registry and Monitoring, and reading each one's free allowance at that moment; a Tier 1 region; the second OAuth client; the cloud link (`google link … --client-file … --scopes drive --print-token | gcloud secrets versions add …`, then deleting the JSON); the cloud's own Claude key and the configuration as the other two secrets; a service account allowed to read exactly those three; the job (one task, task retries 0, 10-minute timeout) with the secrets mounted as files; the Scheduler job with `[cloud] schedule` in time zone `Europe/Madrid`; an alert policy emailing the operator on a failed execution; checking the three free Scheduler jobs are not already used; reading a run's log. No project id, region or secret value in the page.
- [ ] T026 [US1] Write `check_cloud` in `src/alfabeta/notes/watch.py` and call it from the Mac's sync: read `last_ok_ended` (moved only by `ran_on = cloud` runs) from `.alfabeta/last-run.json` with the Mac's link; older than `[notes] cloud_stale_hours` → an agenda line and a notification through spec 004's `notify` (FR-017). Test in `tests/test_notes_watch.py`.
- [ ] T027 [US1] Run quickstart step 5 with the Mac off; record the delay and the free allowances read in `specs/005-notes-to-notebook/research.md` as dated facts.

---

## Phase 5: User Story 3 - New Classroom material reaches the notebook (P2)

**Goal**: each Classroom item becomes one entry in `Classroom · <topic>.pdf`.

**Independent test**: quickstart step 6.

- [ ] T028 [US3] Extend `run_notes` in `src/alfabeta/notes/run.py`: build a `ClassroomEntry` per item (a file, a `.md` note, or a folder with its files, `descripcion.md` and `enlaces.md`) from `YYYYMMDD - <title>`; never include a file whose name starts with `entrega - ` or `correccion`, whatever follows (constitution III), nor a `(anterior YYYY-MM-DD)` version, and leave out announcement notes (`aviso`); render parts per research R6, with Office copies made in `.alfabeta/conversions/`, exported, and put in Drive's trash at once; route a material in `Sin tema` to the living Classroom file of its subject's most recent topic, the topic folder with the latest date when the material is first seen, and keep it there (spec 002 FR-023); a new `item_version` replaces the entry's pages in place; an item moved to another topic leaves the first file and enters the second; order by posting date.
- [ ] T029 [P] [US3] Test in `tests/test_notes_run.py`: one file item added once; a folder with a PDF, a Word file and `descripcion.md` → one entry; a links-only folder → cover with addresses; an assignment folder → the statement only, no `entrega` or `correccion` page, also with a `correccion (anterior 2026-10-01).md` beside it; an edited item with its `(anterior …)` version → its pages once; an announcement → no entry; a `Sin tema` item lands in the most recent topic's file; a moved item appears once, in the second file; a changed item replaced in place; a second run with nothing new writes only the run log.
- [ ] T030 [US3] Run quickstart step 6 and record SC-003's delay.

---

## Phase 6: User Story 2 - The student corrects a transcription (P2)

**Goal**: marks change a page's heading; a correction replaces the page.

**Independent test**: quickstart step 4.

- [ ] T031 [US2] Extend `run_notes`: a rename of a `notes_transcript` ending in « (revisada)» sets `review = checked`, « (mal)» sets `review = wrong`; a photo named like a page's photo plus « (corregida)» replaces its photo and transcription keeping `order`; a family edit of the page's Markdown re-renders the page without calling Claude; after either, alfabeta writes the new PDF under the name without a mark and sets `review` to `automatic`; the latest event wins (research R7).
- [ ] T032 [P] [US2] Test in `tests/test_notes_run.py`: each mark and its heading; each correction replaces the page once, in place, and the PDF loses its mark.
- [ ] T033 [US2] Run quickstart step 4.

---

## Phase 7: User Story 4 - The family learns what changed and what it adds (P2)

**Goal**: a report in Spanish after any run that changed something, none otherwise, and a repeating
failure reported once.

**Independent test**: upload notes holding an idea the study guide misses; the report names it.

- [ ] T034 [US4] Write `write_report` in `src/alfabeta/notes/report.py`: `Informes/Informe AAAAMMDD-HHMM.md` in Spanish with the state changes of `RunReport` since the last report, and the month's spend from the `SpendLedger`; "what it adds" by one Claude call per changed topic given the new pages and the study guide section of `Tema NN para imprimir · <title>.pdf` (the study-pack skill's printable PDF) extracted with `pypdf`, skipped with a line when that PDF is missing or the budget is spent; every call's `usage` into the ledger (research R8).
- [ ] T035 [P] [US4] Test `tests/test_notes_report.py`: no report when nothing changed; a repeating failure appears once and its clearing once; the ledger sums transcriptions and "what it adds" by month; the guardrail's detectors find no name, address or id in the output.
- [ ] T036 [US4] In the Mac's sync, list `Informes/` through `ScopedDrive` and add one agenda line per report not listed before (spec 001's agenda module).
- [ ] T037 [US4] Run quickstart step 7.

---

## Phase 8: Polish

- [ ] T038 [P] Update `skills/study-pack/SKILL.md` step 1: notes reach the notebook as automatic transcriptions only through the living notes file (spec 005); the pack adds no source for them; the ranking of the notes first is unchanged.
- [ ] T039 [P] Update `docs/explanation/study-material.md` with the living files and why the notebook follows a Drive file instead of gaining sources.
- [ ] T040 Run US5 scenarios 2 and 4 on Tema 01 of 2026-2027: `notebook setup` adopts its Markdown, builds `Apuntes · <topic>.pdf`, and lists the two plain sources for the family to remove.
- [ ] T041 [P] Add to `tests/test_guardrail.py` a case that a run report and a run log with invented values pass, and one with a planted address fails (SC-008).
- [ ] T042 Run quickstart step 8 for two weeks and record SC-001, SC-002, SC-005 and SC-006 in `specs/005-notes-to-notebook/research.md`, as aggregates only.

---

## Dependencies

- Phase 1 → Phase 2 → every story.
- Spec 004's `drive.py` (its T025) before T006; its `notify.py` (its T015) before T026.
- This spec's T006 (`ScopedDrive.changes`) before spec 004's T029b, and spec 004's T029a and T029b
  (the pull, FR-002 here) before spec 004's T029 step 4 moves the master folder; the pull blocks no
  phase here.
- Phase 3 (Mac) before Phase 4 (cloud): the cloud job runs the same pass.
- Phase 3 before Phase 3b: the refresh reads the records `notes run` and `notebook setup` write, and
  extends `sources.py`. Spec 004's `notify.py` (its T015) before T044. Phase 3b needs nothing from
  Phases 4 to 7 and can run beside them.
- Phases 5, 6 and 7 each extend `run.py` after T018; same file, so one after another, in that order.

## Parallel examples

- Phase 2: T005, T008, T010 and T012 once their modules exist.
- Phase 3: T014, T017 and T019 beside the modules they test.
- Phase 3b: T045 beside `refresh.py`.
- Phase 8: T038, T039 and T041.

## Implementation strategy

1. **MVP**: Phases 1 to 4 and 3b. One photo from the phone, with the Mac off, becomes a page, and
   the student's view of the notebook answers about it once the Mac is awake (quickstart steps 1,
   3, 3b and 5). Without Phase 3b the notebook takes the page only when its owner opens it.
2. Spec 004's pull before spec 004 moves the master folder.
3. Then US3, US2, US4, each proved by its quickstart step.
4. Tema 01 and two weeks of real use close the spec.
