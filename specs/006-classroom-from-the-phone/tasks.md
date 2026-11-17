# Tasks: spec 006, amendment of 2026-11-17 — the container read

**Input**: [spec.md](spec.md) FR-027 to FR-032, [plan.md](plan.md) «Amendment of 2026-11-17»,
[research.md](research.md) S14.
**Scope**: the container read only. The read on the Mac's own Chrome (sign-in window, remote view,
notices, read by calls) keeps its plan and gets its tasks when it is built.

Format: `[ID] [P?] [Slice] Description`. `[P]`: no dependency on another open task of the slice.

## Slice A — `classroom password set|delete` (FR-031)

- [ ] T001 [P] [A] Write `tests/test_classroom_password.py` with a fake `TokenStore` and a fake
  prompt: `set` stores the typed value under the student's keychain account and clears the
  `wrong_password` mark; `delete` removes both; an empty answer stores nothing; neither command
  prints, logs or accepts the password as an option, an argument or an environment variable (the
  parser has no such option; a planted `ALFABETA_PASSWORD` is ignored); each takes the student's
  lock (FR-024a).
- [ ] T002 [A] Implement `src/alfabeta/classroom/password.py` (`PasswordStore` over spec 004's
  `TokenStore`, prompt by `getpass`, the mark as a file under `data/` holding only the date) and
  `classroom password set|delete` in `src/alfabeta/classroom/cli.py`; drop them from `PLANNED` in
  `tests/test_cli_naming.py`.

## Slice B — the image and `read.py` (FR-027, FR-029, FR-030; SC-009)

- [ ] T003 [P] [B] Write `tests/fake_classroom.py`: a local HTTP server with a fake Google sign-in
  (modes: ok, image captcha after the account, rejected browser, wrong password, second factor) and
  the synthetic pages of `tests/fixtures/classroom/pages` served at their paths with `<base>`
  removed, plus one page outside spec 001 FR-007's pages and one planted press.
- [ ] T004 [P] [B] Write `tests/test_classroom_read.py`, running `docker/classroom/read.py` with
  Playwright's Chromium against the fake (marked to run where Playwright's browser is installed,
  and in CI): ok → captures valid against `src/alfabeta/schemas/capture.schema.json`, every class
  `complete`; captcha → `challenge` and nothing typed after the account; rejected → `rejected`;
  wrong password → `wrong_password` after one try; second factor → `second_factor`; a live profile
  → no sign-in; the planted press and the outside page blocked and counted; the browser's zone is
  Europe/Madrid (a fake due time read back unchanged); the password never in stdout, the captures
  or the log lines.
- [ ] T005 [B] Implement `docker/classroom/read.py` (stdin JSON with account and password, the
  scripted sign-in and its guard, the extractor injected unchanged and its calls per class, the
  captures returned through the page and written to `/out`, one JSON line per event) and
  `docker/classroom/Dockerfile` (python 3.12 slim, the pinned Playwright, Google Chrome,
  `linux/amd64`, the extractor copied from `skills/classroom-sync/scripts/extract.js` at build).
- [ ] T006 [B] Add the CI step that installs Playwright's Chromium for T004, and name its cost in
  `.claude/rules/python-test-cost.md` terms (one browser test file).

## Slice C — `classroom refresh`, container read (FR-022, FR-024a, FR-027, FR-028, FR-032)

- [ ] T007 [P] [C] Write `tests/test_classroom_refresh.py` with a fake `ReadContainer`, a fake
  `TokenStore` and a fake `Notifier`: `CLAUDECODE` set → no container started, reads only with a
  live session, else `session_expired`; no password → `no_password` and a notification; the mark →
  `wrong_password` without starting the container; a container stop by code → that code, the
  notification in Spanish naming it, the mark set for `wrong_password`, nothing written to the
  student's folder; a full read → captures collected, plan and apply run once, one log line with
  counts and blocked counts; the container started with the password on stdin and never in its
  argv or environment.
- [ ] T008 [C] Implement `src/alfabeta/classroom/container.py` (`ReadContainer` port,
  `DockerReadContainer`: image build from `docker/classroom/`, `docker run --rm -i` with the read
  profile `data/classroom-profile/` (0700) and an out folder under `data/` mounted, stdin, JSON
  line parsing) and `src/alfabeta/classroom/refresh.py` with `classroom refresh`; drop it from
  `PLANNED`.
- [ ] T009 [C] On the Mac, build the image and run `classroom refresh` once against the fake
  (`ALFABETA_CLASSROOM_FAKE`, test-only, refused when not a loopback address); record the result
  in the pull request.

## Slice D — attachments in the container (FR-028; spec 001 research R4)

- [ ] T010 [P] [D] Extend `tests/test_classroom_read.py`: a planted attachment listed by a capture
  is fetched through the page's request context into `/out/inbox/<item>__<attachment>/<name>`; a
  form or quiz link is never fetched; a file that does not arrive is reported, not retried.
- [ ] T011 [D] Implement the attachments in `read.py` and their hand-over to `download collect` in
  `refresh.py`.

## Slice E — `classroom agent install|uninstall` (FR-015, FR-016)

- [ ] T012 [P] [E] Write `tests/test_classroom_agent.py` with spec 005's fake `Launchctl`: the
  plist runs `classroom refresh` at the `[schedule]` times; uninstall removes it; Docker Desktop not
  running at fire time → `docker_unavailable` logged and notified, nothing else run.
- [ ] T013 [E] Implement `src/alfabeta/classroom/agent.py` and the two commands; drop them from
  `PLANNED`.

## The family's steps (not Claude's)

- [ ] T014 `classroom password set --student <id>` at the Mac.
- [ ] T015 The first real `classroom refresh --student <id>` from a terminal, then
  `classroom agent install --student <id>`; ten school days for SC-008.

## Dependencies

A and B in parallel; C after A and B; D after B and C; E after C. Each task's pull request runs
`make ci` and an independent review before its merge (constitution, Development workflow).
