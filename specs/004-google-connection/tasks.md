# Tasks: alfabeta's own Google connection (Calendar and Drive)

**Input**: Design documents from `specs/004-google-connection/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: included. The plan asks for one test module per module, the FR-009a scope test and the
"no socket outside `transport`" test. Every test replays recorded shapes (research R8); none calls
Google. The live proof is the quickstart's.

**Depends on spec 001**: the package and gates (spec 001 T001–T009), the guardrail (T013–T015),
the configuration loader and template (T017–T020), and the state store, log and lock (T025–T026).
Phase 6's agenda line needs spec 001's agenda module. Without it, that one task is deferred and the
other two channels of research R9 still ship.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1 link once · US2 a reminder that rings · US3 Drive · US4 a lost link is loud

---

## Phase 1: Setup

- [x] T001 Add the keys of `specs/004-google-connection/contracts/config-template.toml` to `config/template.toml`. Change the comment of `[drive] root` to "the alfabeta folder's path inside the student's My Drive", and add `[storage] base`, `[calendar] id` and `[google]`. Run spec 001's `tests/test_template_covers_reads.py`.
- [ ] T002 [P] Create `src/alfabeta/google/__init__.py` and the empty `tests/fixtures/google/README.md`. The README says every file there is a recorded response with invented values, named `<call>-<YYYY-MM-DD>.json`.

---

## Phase 2: Foundational (blocks every story)

- [ ] T003 [P] Write `tests/test_google_transport.py`, two parts:
  - `FakeTransport` serves files from `tests/fixtures/google/` keyed by method and URL path, and fails on any unmatched request.
  - An AST walk asserts that no module under `src/alfabeta/` except `google/transport.py` imports `urllib.request`, `http.client` or `socket`.
- [ ] T004 Implement `src/alfabeta/google/transport.py`:
  - the `HttpTransport` Protocol, `request(method, url, *, headers, body) -> Response(status, headers, body)`;
  - `UrllibTransport`, which never logs URLs with query strings or bodies.
- [ ] T005 [P] Write `tests/test_google_keychain.py` against a fake `security` runner. Assert three things:
  - `set`/`get`/`delete` send their commands on stdin to `security -i`;
  - no secret appears in the argv passed to the subprocess;
  - service `alfabeta.google`, account `<student>/<alias>` and `<student>/client`.
- [ ] T006 Implement `src/alfabeta/google/keychain.py`: the `TokenStore` Protocol and `KeychainStore` over `security -i` (research R3).
- [ ] T007 [P] Implement the domain values of `data-model.md` in `src/alfabeta/google/model.py`:
  - `LinkedAccount`: alias lowercase ASCII; role `student`, "only value this spec defines";
  - `AuthStatus`: `ok` · `revoked` · `expired` · `missing_scope` · `no_token` · `network`;
  - `UploadRecord` and `MigrationPlan`: lists `adopted`, `to_upload`, `differs`, `native`, `only_in_drive`;
  - `DriveRoot`.

**Checkpoint**: transport, keychain and domain exist. No Google call has been made yet.

---

## Phase 3: User Story 1 — the family links the student's Gmail once (P1) MVP

**Goal**: `google client set`, `google link`, `google check` and `google unlink` work on the real
accounts.

**Independent test**: quickstart steps 1–4, and the school-account negative control of step 3.

- [ ] T008 [P] [US1] Write `tests/test_google_oauth.py`. It covers:
  - the authorisation URL carries `code_challenge_method=S256`, `state`, `access_type=offline`, `prompt=consent` and R4's scopes, and **no `login_hint`**;
  - the loopback server rejects a callback with a wrong `state`;
  - the exchange and the refresh map `invalid_grant` to `expired` (or `revoked` when Google says so);
  - `revoke` calls Google's revocation endpoint.
- [ ] T009 [US1] Implement `src/alfabeta/google/oauth.py` (research R2):
  - the loopback and PKCE flow with `http.server` on `127.0.0.1` and a free port;
  - the exchange, refresh and revoke;
  - reading the `email` claim from the `id_token` payload, with no signature check needed for a token received directly from Google's token endpoint over TLS. A comment cites that.
- [ ] T010 [P] [US1] Write `tests/test_google_accounts.py`:
  - link validation per `data-model.md`: "The `email` claim of the token response's `id_token` equals `address`"; the domain is not `accounts.school`'s; the granted scopes include every scope in `scopes`;
  - on failure the token is revoked and nothing is stored;
  - re-link replaces the keychain entry;
  - `check` returns one status per alias;
  - output never contains the address. Assert with the configured address of an invented fixture.
- [ ] T011 [US1] Implement `src/alfabeta/google/accounts.py`: `link_account`, `check_accounts`, `unlink_account`, `set_client` (reads the downloaded client JSON), and `data/google/accounts.json` (`linked_on`). `check_accounts` also warns when a token fails with `invalid_grant` less than 8 days after `linked_on`, the symptom of an app left in Testing (data model, GoogleApp).
- [ ] T012 [US1] Wire `google client set|link|check|unlink` into `src/alfabeta/__main__.py` per `contracts/cli.md`: JSON on stdout, exit 0 / 1 / 2, and the reasons `bad_client_file`, `wrong_account`, `school_account`, `missing_scope`, `denied`, `no_client`.
- [ ] T013 [US1] Run quickstart steps 1–4 on the real accounts. Save the token, refresh and revoke responses, with invented values, to `tests/fixtures/google/`. Record the dates in `specs/004-google-connection/research.md` under Observed facts.

**Checkpoint**: alfabeta acts as the student's Gmail with no conversation open.

---

## Phase 4: User Story 4 — a lost link is loud, never silent (P1)

**Goal**: a revoked or expired link stops the outputs that need it and reaches the family on a
channel that does not need that link.

**Independent test**: quickstart step 6.

- [x] T014 [P] [US4] Write `tests/test_google_notify.py`. A non-`ok` status from `check_accounts` calls the `Notifier` once per failed alias, with text naming the alias only, and the CLI exits 2.
- [x] T015 [US4] Implement `src/alfabeta/google/notify.py`: a `Notifier` Protocol and `MacNotifier`, which calls `osascript -e 'display notification …'` with the alias, never the address. Call it from `check_accounts` (research R9, channels 1–2).
- [x] T016 [US4] Make `google check` refresh every linked token on every run, even when the run writes nothing to Google (FR-015, research R10). Spec 001's run entry calls it first; a status other than `ok` skips the Google outputs and lets the others finish (FR-013).
- [ ] T017 [US4] Run quickstart step 6. Revoke, check, see the notification, then link again. Save the `invalid_grant` response to `tests/fixtures/google/`.

---

## Phase 5: User Story 2 — a reminder set by alfabeta rings on the student's phone (P1)

**Goal**: an event written as the student carries his own reminder, and his phone rings.

**Independent test**: quickstart step 5. It unblocks building spec 003 (its gate 1; the plan went ahead, 2026-10-28).

- [ ] T018 [P] [US2] Write `tests/test_google_calendar.py`. It covers:
  - insert with a deterministic base32hex id of 5 to 1024 characters, "lowercase letters a-v and digits 0-9";
  - `reminders.useDefault` is always `false`, with at most 5 overrides of 0–40320 minutes; a sixth raises;
  - patch only when an owned field differs;
  - a 409 on insert leads to get, then update with `status: confirmed` (research R5);
  - `timeZone` is `Europe/Madrid`.
- [ ] T019 [US2] (The `patch` part is done by spec 003 T007–T008.) Implement `src/alfabeta/google/calendar.py`, the `CalendarClient`: `get`, `insert`, `patch`, `delete`, `upsert`. It writes only to the configured family calendar id.
- [ ] T020 [US2] Add `calendar probe` and `calendar probe-clean` to `src/alfabeta/__main__.py` per `contracts/cli.md`.
- [ ] T021 [US2] Run quickstart step 5 with the family, on the student's phone. Record:
  - the date the notification was seen (spec 003, FR-019);
  - the reminders of the probe event read as the owner;
  - the existing-event patch;
  - the id-reuse result.

  Save the event responses to `tests/fixtures/google/`. If id reuse behaves differently from the design, update `research.md` R5 and T018 before continuing.
- [ ] T022 [US2] Once T021 is recorded, the operator removes the chat connector's account (the work account) from the family calendar's sharing, so that alfabeta's `CalendarClient` is its only writer (FR-008b). Record the date in `research.md` under Observed facts.

---

## Phase 6: User Story 3 — files reach the student's Drive, and alfabeta knows they did (P2)

**Goal**: Drive adopts the existing tree, uploads only what is missing or changed, and confirms
each file.

**Independent test**: quickstart step 7.

- [ ] T023 [P] [US3] Write `tests/test_google_drive_scope.py` (FR-009a). Two checks:
  - every public method of `ScopedDrive`, called with a file or parent id outside the folder allowlist, raises before any request reaches `FakeTransport`;
  - the allowlist is rebuilt from `files.list` per run, and a trashed root fails the run.
- [ ] T024 [P] [US3] Write `tests/test_google_drive.py`:
  - multipart upload up to 5 MB, resumable above;
  - an upload counts as done only when the response's `size` and `md5Checksum` equal the local file's (FR-012);
  - a changed local file becomes `files.update` with media on the same Drive id, never a second file.
- [ ] T025 [US3] Implement `src/alfabeta/google/drive.py`, the `ScopedDrive` of research R6. It resolves the root from `[drive] root`, caches `root_id` in `data/google/drive.json`, and lists, uploads and updates, always inside the allowlist.
- [ ] T026 [P] [US3] Write `tests/test_google_migrate.py`. Match by relative path; same size and md5 → `adopted`; missing → `to_upload`; different → `differs`; no checksum → `native`; Drive-only → `only_in_drive`. `--apply` refuses while `differs` is non-empty, and nothing is ever deleted.
- [ ] T027 [US3] Implement `src/alfabeta/google/migrate.py` and `drive migrate [--apply]`. Write `data/google/migration-<run>.json` with names, and print counts only.
- [ ] T028 [US3] Implement `drive push` and the mount check of FR-011:
  - refuse a `[storage] base` under `~/Library/CloudStorage/GoogleDrive-*`;
  - append to `data/google/uploads.jsonl`;
  - exit 3 on a partial failure, after finishing the other files.
- [ ] T029 [US3] Run quickstart step 7 on the real Drive:
  1. dry run;
  2. review `differs`;
  3. apply;
  4. the operator moves the base folder off the mount;
  5. `drive push` twice, the second reporting `uploaded: 0`.

  Save the `files.list` and upload responses, with invented values, to `tests/fixtures/google/`.
- [ ] T029a [US3] Added by spec 005. Write `tests/test_google_pull.py` for FR-011a, one test per branch: a Drive id with no upload record is downloaded and recorded `adopted`; a recorded id with a new version overwrites a master copy whose md5 equals the last pulled version; the same with a master copy changed since is written beside with « (de Drive)» and reported; a file whose md5 the master already holds is recorded, not copied; a rename in Drive renames an unchanged master copy and leaves a changed one alone; a removed Drive file deletes nothing; files under `.alfabeta/` are skipped; the pull refuses to run without the student's lock; a file the placer numbered « (2)» is never renamed; pull then `drive push` uploads 0, including for a « (de Drive)» copy.
- [ ] T029b [US3] Added by spec 005. Implement `drive pull` in `src/alfabeta/google/pull.py` and `src/alfabeta/__main__.py`: its own cursor in `data/google/pull.json` (its own log, constitution V), `ScopedDrive.changes` (built by spec 005's T006, which must land first), the student's lock (spec 001's `lock take`), the rule of FR-011a, JSON `{ok, pulled, beside, recorded}`, codes 0 · 2 · 3. Call it at the start of every sync run. Must be done before T029 step 4 moves the base folder off the mount.

---

## Phase 7: Polish and cross-cutting

- [ ] T030 [P] Extend spec 001's guardrail patterns so that a refresh token (`1//…`), a client secret (`GOCSPX-…`) and the configured addresses are caught by `guardrail --all --history` (SC-006). Add the cases to `tests/test_guardrail.py`, built at run time. Add a test that scans the log lines and the reports under an invented `data/` written by a full test run, and finds no address, token or secret.
- [ ] T031 Add the agenda's failure line, research R9 channel 3, when spec 001's agenda module exists. Otherwise leave a `TODO(tech-debt)` in `src/alfabeta/google/notify.py` naming that blocker and this branch's issue (`origin: #30`).
- [ ] T032 [P] Update spec 001's `specs/001-classroom-sync/contracts/config-template.toml` comment on `[drive] root`, and the `study-pack` skill's path instructions, to the meanings this spec gives them.
- [ ] T033 Run quickstart step 9 from the scheduled run of julioarguello/alfabeta#13: 8 days after linking, `ok` with no sign-in and 0 keychain prompts. Then count 30 consecutive scheduled runs for SC-001.

---

## Dependencies and order

```text
spec 001 T001–T026 ─▶ Phase 1 ─▶ Phase 2 ─▶ US1 (Phase 3) ─┬─▶ US4 (Phase 4)
                                                          ├─▶ US2 (Phase 5) ─▶ spec 003 build
                                                          └─▶ US3 (Phase 6)
Phases 4–6 ─▶ Phase 7 (T033 also needs #13's schedule)
```

- US1 blocks everything else: no story works without a link.
- US4, US2 and US3 are independent of each other once US1 is done.
- Within a phase, a test task [P] is written before its implementation task.

## Parallel examples

- Phase 2: T003, T005 and T007 together, then T004 and T006.
- After US1: one person on US2 (T018–T021), another on US3 (T023–T029). They touch different files.

## Implementation strategy

1. **MVP = US1 + US2** (T001–T013, T018–T022). It answers the question that has blocked spec 003
   since the start: does a reminder alfabeta sets ring on the student's phone?
2. **Then US4.** Nothing goes unattended while a lost link could fail silently.
3. **Then US3.** It replaces Drive for desktop; until then spec 001 keeps writing to the mount.
4. **Then Phase 7.**
