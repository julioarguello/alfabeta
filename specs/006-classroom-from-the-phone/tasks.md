# Tasks: spec 006, amendment of 2026-11-17 — the container read

**Input**: [spec.md](spec.md) FR-026 to FR-032, SC-008, SC-009; [plan.md](plan.md) «Amendment of
2026-11-17»; [research.md](research.md) S14.
**Scope**: the container read through `classroom refresh`, `classroom password set|delete` and
`classroom agent install|uninstall`. `classroom capture` and `classroom status` stay in `PLANNED`
(the container read reaches them through `refresh`); the launcher of FR-016 and the read on the
Mac's own Chrome (window, remote view, notices, read by calls) get their tasks when they are built.
**Rules for every test**: no real account, no keychain value and no Google host is ever reached; the
fakes are local; `CLAUDECODE` is honoured everywhere (no task needs to bypass it).

Format: `[ID] [P?] [Slice] Description`. `[P]`: no dependency on another open task of the slice.

## Slice 0 — shared vocabulary

- [x] T001 [0] Extend `StopReason` (`src/alfabeta/model.py`) with `rejected`, `second_factor`,
  `other_sign_in`, `wrong_password`, `no_password`, `docker_unavailable`, `unreachable` and `disabled`
  (`challenge`, `session_expired`, `unexpected_ui`, `lock_busy` exist); update
  `contracts/cli.md` (the password commands, `refresh`'s codes and `started_by`) and
  `data-model.md` (the stored password, the `wrong_password` mark, the read container; the profile
  spelled `data/classroom-profile/`, the student's data folder, as in the plan).

## Slice A — `classroom password set|delete` (FR-031)

- [x] T002 [P] [A] Write `tests/test_classroom_password.py` with a fake `TokenStore` and a fake
  prompt: `set` stores the typed value under the keychain service `alfabeta.classroom`, account
  `<student>`, and clears the `wrong_password` mark; `delete` removes both; an empty answer stores
  nothing; a non-TTY stdin is refused (no echoing fallback); a Google link of the same student in
  `alfabeta.google` is untouched; neither command prints, logs or accepts the password as an option,
  an argument or an environment variable (a planted `ALFABETA_PASSWORD` is ignored); each takes the
  student's lock and the browser lock (FR-024a).
- [x] T003 [A] Implement `src/alfabeta/classroom/password.py` (`PasswordStore` over a `KeychainStore`
  with its own service, `getpass` behind a TTY check, the mark as a file under `data/` holding only
  its date) and the two commands in `src/alfabeta/classroom/cli.py`, attached to the existing
  `classroom` subparser of `src/alfabeta/__main__.py`; drop them from `PLANNED` in
  `tests/test_cli_naming.py`.

## Slice B — `read.py` against the fake (FR-006, FR-008, FR-009, FR-027, FR-029, FR-030; SC-004, SC-009)

- [x] T004 [P] [B] Write `tests/fake_classroom.py`: a local HTTP server with a fake Google sign-in in
  modes ok, image captcha after the account, rejected browser, wrong password, second factor,
  the school's own sign-in (`other_sign_in`), an account chooser, and an «other account» session;
  the synthetic pages of `tests/fixtures/classroom/pages` at their paths with `<base>` removed; one
  page outside spec 001 FR-007's pages, one planted press, one form link, one quiz link, one
  third-party frame, one class page that cannot be interpreted, and one page that ends the session
  mid-read; one page that renders a due date from an instant with `Intl.DateTimeFormat` on a date
  where UTC and Europe/Madrid differ, and one across a DST change.
- [x] T005 [P] [B] Write `tests/test_classroom_read.py`, running `docker/classroom/read.py` as a
  module with Playwright's Chromium against the fake; the test overrides `read.py`'s host constants
  in the module object (never an environment variable or a production option). It never skips in
  CI (T007). Cases:
  - ok → captures valid against `src/alfabeta/schemas/capture.schema.json`, every class
    `complete`; a live profile → no sign-in; `"signin": false` and no session → `session_expired`,
    nothing typed;
  - the cookies cleared before the sign-in, so the account chooser never shows to the script;
  - captcha → `challenge`, nothing typed after the account; rejected → `rejected`; second factor →
    `second_factor`; the school's sign-in → `other_sign_in`; wrong password → `wrong_password`
    after one try; `"password": null` and a sign-in needed → `no_password`;
  - another account signed in → `session_expired` with nothing read (FR-006); the unreadable class
    → `unexpected_ui` and the others read (FR-008); the session ending mid-read → the classes read
    kept and `session_expired` (FR-009);
  - the planted press, the outside page, the form and quiz links and the third-party frame blocked
    and counted; no press beyond the two Enters;
  - `Intl.DateTimeFormat().resolvedOptions().timeZone` is `Europe/Madrid`, `navigator.language` is
    `es-ES`, and both rendered due dates read as in Madrid;
  - neither the password nor the account appears in stdout, the captures or any JSON line; the
    sign-in's host-and-path lines carry no query.
- [x] T006 [B] Implement `docker/classroom/read.py` (stdin JSON `{account, password, signin}`, the
  account check, the cookie clearing, the scripted sign-in and its guard, the extractor injected
  unchanged and its calls per class, captures returned through the page and written to `/out`, one
  JSON line per event — for each sign-in page load its host and path, never a query — the browser
  zone and locale) and `docker/classroom/Dockerfile` (python 3.12
  slim, `playwright==1.64.1`, Google Chrome, `linux/amd64`, built from the repository root with
  `-f docker/classroom/Dockerfile` so `skills/classroom-sync/scripts/extract.js` is copied
  unchanged).
- [x] T007 [B] Add `playwright==1.64.1` to the dev group, the CI step that installs its Chromium,
  and make `test_classroom_read.py` required in CI; note its cost per
  `.claude/rules/python-test-cost.md`. *(Recorded on #255: the file runs about 143–175 s locally; only
  the cases that read a class pay ~35 s each, the extractor's fixed settle per page; the Chromium
  install is not cached.)*

## Slice C — `classroom refresh`, container read (FR-019, FR-020, FR-022, FR-024a, FR-027, FR-028, FR-032; SC-008, SC-009)

- [x] T008 [P] [C] Write `tests/test_classroom_refresh.py` with a fake `ReadContainer`, a fake
  `TokenStore`, a fake `Notifier` and a fake clock:
  - `profile_read` off → `disabled`, nothing started;
  - `CLAUDECODE` set → stdin `{account, signin: false}`, no password, no notification;
  - the mark → `signin: false`, a dead session → `wrong_password`, the container never given the
    password; no stored password → `password: null`;
  - Docker not running → `docker_unavailable`, notified;
  - a container stop by code → that code, the notification in Spanish naming it (and, for
    `wrong_password` and `no_password`, `classroom password set`), the mark set for
    `wrong_password`, nothing written to the student's folder;
  - a full read → captures collected, plan and apply once, the lock renewed while the container
    runs, one log line with `started_by` (`ALFABETA_STARTED_BY`), counts and blocked counts;
  - neither the account nor the password in any log line or notification.
- [x] T009 [P] [C] Write `tests/test_classroom_container.py`, the `DockerReadContainer` tests with a fake process runner (as
  `src/alfabeta/google/keychain.py`'s `Runner`): `docker run --rm -i`, the profile and out folders
  mounted with mode 0700, the stdin line written once, the password absent from argv, every
  `-e`/`--env`, the build arguments and the build context; the image rebuilt only when its inputs'
  hash changes; a failed build → `docker_unavailable`.
- [x] T010 [C] Implement `src/alfabeta/classroom/container.py` (`ReadContainer`,
  `DockerReadContainer`) and `src/alfabeta/classroom/refresh.py` with
  `classroom refresh` (`started_by` from `ALFABETA_STARTED_BY`, as `contracts/cli.md` says); declare `[classroom] profile_read` in
  `config/template.toml` (`false`, as `contracts/config-template.toml`); drop `refresh` from `PLANNED`.
- [x] T011 [C] Write `tests/test_classroom_image.py` (marked `docker`, run on the Mac before the pull
  request and recorded in it): the image builds; `docker image inspect` shows no `ENV` or label
  holding a secret; `docker run --rm -i --network none` with an invented account and password on
  stdin ends with a JSON stop line with code `unreachable`, never echoes stdin, and leaves no container behind.

## Slice D — attachments in the container (FR-028, FR-030; spec 001 research R4)

- [ ] T012 [P] [D] Extend `tests/test_classroom_read.py`: an attachment listed by this run's
  captures is fetched by R4's routes through the request context into
  `/out/inbox/<item>__<attachment>/<name>` and counted; an unlisted file, a non-R4 host and a form
  or quiz link are refused and counted; a file that does not arrive is reported, not retried.
- [ ] T013 [D] Implement the attachments in `read.py` and their hand-over to `download collect` in
  `refresh.py`.

## Slice E — `classroom agent install|uninstall` (FR-015)

- [ ] T014 [P] [E] Write `tests/test_classroom_agent.py` with spec 005's fake `Launchctl`: the plist
  runs `classroom refresh` with `ALFABETA_STARTED_BY=schedule` at the `[schedule]` times; uninstall removes it;
  `config check` reports the switch on together with spec 001's runner (FR-015).
- [ ] T015 [E] Implement `src/alfabeta/classroom/agent.py` and the two commands; drop them from
  `PLANNED`.

## The family's steps (not Claude's)

- [ ] T016 `classroom password set --student <id>` at the Mac, then the first real
  `classroom refresh --student <id>` from a terminal; its stop code and counts recorded in #166.
- [ ] T017 After T016, a pull request narrows `read.py`'s sign-in allowlist to the hosts and paths
  the first real run logged (no queries) (FR-027).
- [ ] T018 `classroom agent install --student <id>`; one scheduled read with the screen locked
  recorded in #166; then ten school days for SC-008, as a table in #166.

## Dependencies

Slice 0 first; A and B in parallel; C after A and B; D after B and C; E after C; T016–T018 after
C (T017 and T018 after T016). Each pull request runs `make ci` and an independent review before its
merge (constitution, Development workflow).
