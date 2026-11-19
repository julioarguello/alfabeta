# Implementation Plan: Classroom read on the Mac with no app open, signed in from the phone

> **Amendment of 2026-11-17.** This plan was written before spec 006's amendment of that date (spec
> FR-027 to FR-032, constitution 2.11.0): a scripted sign-in with the password in the keychain, the
> read in a Docker container on the Mac with alfabeta's extractor, and no email notices or remote
> view in that build. Its Constitution Check rows for III, IV and IX, its dependencies (Docker,
> Google Chrome in the image) and its slices are redone before that build; until then they describe
> the read on the Mac's own Chrome.

**Branch**: `docs/166-spec-006-plan` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-classroom-from-the-phone/spec.md`

## Summary

alfabeta reads Classroom on the family's Mac with its own commands, started by a launchd agent, a
launcher or a command, with neither the Claude app nor a window on screen. Each student has a
browser profile in the data folder. When its school session has expired, `classroom sign-in` opens
the plain installed Chrome on Google's sign-in in that profile — a window alfabeta starts and does
not drive — emails the family one link and shows the macOS notification; the family signs in at
the Mac or, from the phone, through Chrome Remote Desktop. When the window's address reaches
Classroom, alfabeta closes it, and `classroom capture` opens the same profile headless with
Playwright, behind a guard installed before any page script, loads one Classroom page and sends
Classroom's own read calls, allowlisted by name, one at a time. It writes spec 001's capture,
asking for an item's materials only when the item changed since the last capture, and fetches the
attachments it listed through the session's request context. `classroom refresh` chains sign-in,
capture, `classroom plan` and `classroom apply` under one lock and ends with one result email.

The approach follows lifecoderua/classroom-advisor (MIT), which reads Classroom this way on another
school domain. Its call names, shapes and the claim that direct calls draw no challenge are
external and not measured on this account: spikes S7 to S13 measure them before anything is built
(research, «Spikes before the build»), and three of them can stop the build.

## Technical Context

**Language/Version**: Python 3.12 in spec 001's package `src/alfabeta`; JavaScript only inside the
browser, for the guard's init script (constitution, Technical constraints).

**Primary Dependencies**: `playwright` for Python, pinned, at runtime on the Mac, driving the
installed Google Chrome (research R2; Complexity Tracking). Gmail and Drive through spec 004's
`HttpTransport` with `urllib.request`. Development: `ruff`, strict `pyright`, `pytest`, Node's
`node --test` with `jsdom` (spec 001).

**Storage**:

- configuration: two `[classroom]` keys, `profile_read` and `notice_account`
  ([contracts/config-template.toml](contracts/config-template.toml)), plus a
  `[google.accounts.<alias>]` with role `family` (spec 004 as amended);
- secrets: the read profile, in the student's data folder with user-only permissions (constitution
  II), which holds the school session; the `family` account's token in the keychain;
- records: spec 001's captures, lock, plan and run log; the sign-in wait and the read's line in the
  run log (FR-020); nothing new in Drive.

**Testing**: `pytest` with fakes for every seam (research R12); a call-answer parser tested against
invented answers shaped like the ones S8 records; the guard tested offline in a real headless
browser against a local fake Classroom (SC-004) and its init script with `jsdom`; a test over every
notice text (SC-006). CI runs on Linux (SC-007). The live proof is [quickstart.md](quickstart.md).

**Target Platform**: macOS (the family's Mac), in the family's user session, from launchd or a
terminal; CI on Linux with the fakes.

**Project Type**: subcommands of spec 001's local command (`python -m alfabeta classroom …`).

**Performance Goals**: a whole read within 30 minutes of the sign-in (SC-003); expected in minutes,
measured in S9. Sign-in from the phone in under 2 minutes, median (SC-002).

**Constraints**:

- read-only by construction: nothing pressed, no call outside the allowlist, no form host
  (constitution IV, FR-005);
- nothing typed on a sign-in page, no challenge got past (constitution III, IV, FR-011);
- nothing personal in an email, log line or URL; the sign-in window's address compared in memory
  only (constitution III, FR-010, FR-014);
- idempotent: a second apply with nothing changed writes nothing (constitution V);
- no prompt mid-run: every macOS permission granted once at set-up (S7 found the keychain and window activation needed none from a shell of the Claude app; launchd is S10's).

**Scale/Scope**: one student, twelve classes, about a hundred items; one read a school day, plus the
family's launches.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Checked against
constitution 2.6.0, amended by the spec.

| Principle | How the plan meets it | Status |
|---|---|---|
| I. The student is configuration | The school account, the switch and the notice account are configuration; the profile lives in the student's data folder; two students have two profiles and run one at a time under the browser lock | Pass |
| II. Three layers | Two template keys with `changeme`; the session in the data folder (user-only); the family's token in the keychain; nothing in a file beside the configuration; nothing copied off the Mac | Pass |
| III. Minors' data | *(Written before the amendment of 2026-11-17, which stores the password in the keychain and signs in by script, spec FR-027 to FR-032; this plan is redone before that build.)* The family types the sign-in; alfabeta stores no password or second factor; emails and logs carry the student's id and counts only, tested (SC-006); the sign-in address never logged; data goes to Google (the family's account sends the email) and nowhere else; fixtures invented, not the peer's | Pass |
| IV. Read-only on the school's platforms | The guard of research R4 in the browser before any page script: presses cancelled, document loads and calls allowlisted by name, form hosts blocked; the allowlist from read-only loads only (R3), and no write is sent to test it; a challenge stops the run; no stealth flags, no proxy: only the keychain flags Chrome needs to read its own cookies are changed | Pass, conditional on S8 (if reads cannot be told from writes by name, the read is not built). *S8 (2026-11-19): the names carrying the capture's fields have query tags in every answer (reading `.lr`, `.laa` and `rubric.list` as list or get tags) but one, `t51ITc` (the attachment ids), admitted by name on the family's decision (R3, #270); S8's second half passed with ten names and the dates are mapped (research, «S8, second half»); the to-do pages, the session upkeep's exact host and path (R4) and the mapping of statuses and grades are still to measure* |
| V. Idempotent, incremental | Captures keep today's ids (base64 of the decimal id, R7); apply unchanged; an unchanged item's materials are copied from the last capture, and a periodic full read asks again (R1) | Pass |
| VI. One isolated, tested provider | The read is a second capture route of the Classroom provider behind the same capture contract; one class's failure stops only that class (FR-008); tests against fake answers and a fake Classroom, never the real one | Pass |
| VII. Outputs degrade on their own | A failed email does not stop the read; a failed read applies what it read (`partial`); the shares and the agenda as today | Pass |
| VIII. `Europe/Madrid` | Instants converted with `zoneinfo`; a due date without time stays a date (R7); the schedule's times are local | Pass |
| IX. Simplicity | On the Mac; one new runtime dependency, justified below; no database, no server, no third party | Pass, with the exceptions in Complexity Tracking |

Re-checked after Phase 1 (data model, contracts): unchanged. The capture's new optional fields
(data-model.md) change no apply rule.

## Project Structure

### Documentation (this feature)

```text
specs/006-classroom-from-the-phone/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   └── config-template.toml
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks, after spikes S7–S9
```

### Source Code (additions to the layout of specs 001, 004 and 005)

```text
src/alfabeta/classroom/
├── __init__.py
├── model.py        # ReadAllowlist, CallRecord, SignInWait, ReadResult, Notice (no I/O)
├── calls.py        # batchexecute request and answer framing; the allowlist check; ids ↔ base64
├── parse.py        # call answers → spec 001's capture dicts (classes, topics, items, stream, attachments)
├── guard.js        # the init script: presses and form submits cancelled, counted
├── guard.py        # GuardedBrowser: Playwright context, init script, request routing, blocked counts
├── session.py      # ReadSession port + PlaywrightReadSession: open the profile, load one page, account check
├── capture.py      # classroom capture: the read, pacing, the materials cache, attachments through the request context
├── signin.py       # SignInWindow port + ChromeSignInWindow (process, the DevTools pipe's tab addresses, front, close); classroom sign-in
├── notice.py       # Mailer port + GmailMailer; the two Spanish templates
├── refresh.py      # classroom refresh: sign-in, capture, plan, apply under one lock; the log line
├── status.py       # classroom status
├── agent.py        # classroom agent install|uninstall: launchd plist from [schedule], the launcher bundle
└── cli.py          # the classroom read's subcommands
tests/
├── fixtures/classroom-calls/   # invented call answers, shaped as S8 records them
├── fake_classroom.py           # a local HTTP server serving synthetic pages and answers, for the guard test
├── js/guard.test.js
└── test_classroom_*.py         # one per module
```

**Structure Decision**: a subpackage beside `notes/` and `google/`, as spec 005 did, reusing spec
001's lock, captures, plan and apply, spec 004's transport, keychain and notifier, and spec 005's
`Launchctl` port. The existing `classroom` CLI group gains the subcommands; spec 001's flat modules
are not moved.

## Class design (by layer)

Facts the design rests on: [research.md](research.md#observed-facts).

| Layer | Names | Responsibility |
|---|---|---|
| Domain | `ReadAllowlist`, `CallRecord`, `SignInWait` (`signed_in`, `session_expired`, `challenge`), `ReadResult` (counts, stop reason, blocked counts), `Notice` | Values and transitions from the [data model](data-model.md); no I/O |
| Ports | `ReadSession` (`open`, `account_ok`, `call`, `fetch_file`, `close`), `SignInWindow` (`open`, `address_is_classroom`, `front`, `close`, `closed`), `Mailer`, `Scheduler`, `RemoteView` (`link`), `BrowserInstall`; reused: `TokenStore`, `Notifier`, `Launchctl`, `Clock` | What the core needs from the outside; the five seams of FR-025 among them (research R12) |
| Adapters | `PlaywrightReadSession` (with `GuardedBrowser`), `ChromeSignInWindow`, `GmailMailer`, `LaunchdScheduler`, `CrdRemoteView`, `MacBrowserInstall`; reused: `KeychainTokenStore`, `MacNotifier` | Each implements one port; each has a fake |
| Services | `capture_classes`, `sign_in`, `refresh`, `status`, `install_agent`, `uninstall_agent` | One per subcommand; return results the CLI prints |
| CLI | `classroom sign-in`, `classroom capture`, `classroom refresh`, `classroom status`, `classroom agent install`, `classroom agent uninstall` | Arguments, JSON out, exit codes ([contracts/cli.md](contracts/cli.md)) |

## Run flow (`classroom refresh`)

1. Take the student's lock and the browser lock (FR-024a); held by another run → `lock_busy`, and
   if that run is waiting for a sign-in, bring its window to the front (FR-017).
2. `classroom status`'s check, inside the lock: open the profile headless, load one page, check the
   account (R6). Alive → step 4.
3. `classroom sign-in`: open the window (R5), send the notice (FR-013) and the macOS notification,
   renew the lock while waiting; the address reaches Classroom → close the window → step 4; the
   family closes it → check once; `wait_minutes` → close, check once; not alive → stop
   `session_expired`, result email, log line.
4. `classroom capture`: the guarded read (R1, R3, R4, R7, R8), class by class, each class's capture
   written when it ends; the session dies → the classes read are kept (`partial`, FR-009); a
   challenge → stop `challenge`.
5. `classroom plan` and `classroom apply` (spec 001), which apply, check the shares and
   regenerate the agenda; judgement left pending (FR-007).
6. Result email (FR-014), one log line (FR-020), release the locks.

## Vertical slices (each leaves the system demonstrable)

Slice 1 needs no spike: it is built and tested offline. Every later slice waits for S7, S8 and S9
to pass (research), since each of them can stop the read; `/speckit-tasks` writes `tasks.md` after
those three are recorded, so the tasks follow what was measured rather than the peer's notes.

1. **The guard and the parser, offline.** FR-005, SC-004, SC-007. `calls.py`, `parse.py`,
   `guard.js`, `guard.py`, the fake Classroom; the CI step that installs Playwright's headless
   browser for the guard test. Done when the planted press, form link and write call are blocked
   and counted in CI, and invented answers parse into a capture the schema accepts.
2. **`classroom capture` and `classroom status` on the real account.** US1, FR-001 to FR-009,
   FR-023, FR-024, SC-003, SC-005. The read profile, the account check, the allowlist from S8, the
   materials cache, attachments through the request context, the capture's optional structured
   fields in spec 001's normaliser. Done when quickstart steps 2 and 3 pass: the comparison with
   the extractor's capture of the same day, and a second apply that writes nothing.
3. **`classroom sign-in`.** US2 scenarios 3 to 5, FR-010, FR-011, FR-021. The window, the address
   watch (or S7's fallback), the macOS notification. Done when quickstart step 4 passes at the Mac.
4. **`classroom refresh`.** FR-022, FR-024a, FR-020, US3 scenarios 1 and 2. Done when quickstart
   step 5 passes from a terminal with the app closed.
5. **The notices.** FR-013, FR-014, SC-006. Needs spec 004's `family` role and `gmail.send` linked
   (its own task there). Done when quickstart step 6 passes: notice and result email on the phone.
6. **Schedule and launcher.** FR-015 to FR-017, `classroom agent install|uninstall`, `config check`'s
   exclusivity with spec 001's runner. Done when quickstart step 7 passes: a scheduled read with
   the app closed and the screen locked.
7. **From the phone, ten days.** US2, SC-001, SC-002; the remote view's set-up as a how-to page.
   Done when quickstart step 8 records ten school days.

Slices 3 and 5 can run in parallel with 2 once S7 has passed; 6 needs 4.

## Who does what

| Step | Needs |
|---|---|
| S7, S8, S9, S13 | Claude runs the probes; the family signs the school account in by hand at the Mac |
| S10 | Claude installs a throwaway agent; the family locks the Mac, closes the app and signs in |
| S11 | The family, with their own phone and Chrome Remote Desktop on their Google account |
| S12 | The family consents to a throwaway `gmail.send` link and watches their phone |
| Slice 1 | Claude alone |
| Slices 2–7 | Claude builds; each live proof needs a family sign-in; slice 7 needs the family's phone for ten school days |

No step needs the student's phone.

## Amendment of 2026-11-17 — the container read

What the amendment builds (spec FR-027 to FR-032), on spec 001's lock, captures, plan and apply,
spec 004's keychain and macOS notifier, and spec 005's launchd agent. The read on the Mac's own
Chrome above (window, remote view, notices, read by calls) is not built here.

### Source code

```text
src/alfabeta/classroom/
├── __init__.py
├── password.py     # PasswordStore over spec 004's TokenStore: set (getpass), delete, get; the wrong_password mark
├── container.py    # ReadContainer port + DockerReadContainer: build the image, run it with the profile and an
│                   #   out folder mounted, the account and password on stdin, --rm; parse its JSON log lines
├── refresh.py      # classroom refresh: locks, CLAUDECODE refusal, password checks, container, collect, plan,
│                   #   apply, the stop notification, the log line
├── agent.py        # classroom agent install|uninstall: launchd plist from [schedule] (spec 005's Launchctl)
└── cli.py          # classroom password set|delete, classroom refresh, classroom agent install|uninstall
docker/classroom/
├── Dockerfile      # python:3.12-slim, playwright==1.64.1, Google Chrome (linux/amd64); built from the repo root
└── read.py         # in the container: the scripted sign-in (FR-027), the guard (FR-030), the extractor's calls
                    #   per class, attachments through the page's request context; writes captures and
                    #   attachments to /out, one JSON line per event on stdout
tests/
├── fake_classroom.py         # local server: fake Google sign-in (ok, captcha, rejected, wrong password, second
│                             #   factor, other sign-in, account chooser) and the
│                             #   synthetic Classroom pages of tests/fixtures/classroom/pages, <base> stripped
├── test_classroom_password.py
├── test_classroom_refresh.py # with a fake ReadContainer, a fake TokenStore and a fake Notifier
├── test_classroom_read.py    # docker/classroom/read.py run as a module with Playwright's Chromium against the fake
├── test_classroom_container.py # DockerReadContainer's argv and build, with a fake process runner
├── test_classroom_image.py   # the built image offline: no secret in its configuration, stdin never echoed
└── test_classroom_agent.py   # classroom agent install|uninstall with spec 005's fake Launchctl
```

`docker/classroom/read.py` is a program of its own, copied into the image with the extractor
(`skills/classroom-sync/scripts/extract.js`, unchanged): it imports nothing from `alfabeta`, so the
image needs no copy of the package. The host never runs a browser.

### Run flow (`classroom refresh`, container read)

1. Read `[classroom] profile_read` (FR-019); off → `disabled`. Take the student's lock and the
   browser lock (FR-024a).
2. Docker not running → stop `docker_unavailable` (FR-028) → step 7.
3. Inside Claude Code (`CLAUDECODE` set): stdin carries the account and `"signin": false`, never the
   password (FR-027). Else, the `wrong_password` mark → `"signin": false` as well, so a dead
   session stops with `wrong_password`; otherwise `"signin": true` with the keychain's password, or
   none if it holds none (`read.py` stops `no_password` only if a sign-in is needed).
4. Build the image if its inputs changed (`docker build -f docker/classroom/Dockerfile` from the
   repository root, so the extractor is copied unchanged; the image labelled with the inputs' hash),
   then `docker run --rm -i` with the read profile `data/classroom-profile/` (0700) and an out
   folder under `data/` mounted; write the stdin line and close it. Renew the lock while it runs.
5. `read.py`: the account check (FR-006); alive → read; else, if allowed, clear the profile's Google
   cookies and sign in (stops by code, the sign-in's guard); capture the class list and each class
   with the extractor (FR-008 `unexpected_ui`, FR-009 `partial`); one JSON line per event and a
   final line with counts and stop code. No line carries the account or the password.
6. Host: a sign-in stop → the `wrong_password` mark if that is the code; else move the captures to
   the downloads folder, `download collect`, `classroom plan`. Then the attachments pass (amended
   2026-11-18, slice D): which attachments to fetch is spec 001 research R4's rule (new, modified,
   renamed, or the periodic full review), and only `classroom plan` knows it, on the host, after the
   capture — fetching every attachment the captures list would download the whole course every day
   (principle V). So the plan's `downloads` (out of this run's captures) go to a second
   `docker run` of the same image, same run id, same profile, its own container name, with
   `"signin": false` and no password: it never signs in (one scripted sign-in per run at most).
   It checks the account, then fetches each one by R4's routes through the page's request
   context, checked against its listed attachment id before the request, redirects followed by
   hand within R4's hosts and scheme (a hop to the sign-in ends the pass as the expired session;
   another host is refused, and the run's log line lists it by host only in `refused_hosts`, so a
   real run shows what to allow; an HTML page, a wrong length or an oversized body is not a file),
   written to a temporary name and renamed into `/out/inbox/<item>__<attachment>/<name>`. The host
   moves only each download's exact `data/inbox/<item>__<attachment>/<name>` (ids and name checked
   as single path components, every part a real folder of the out folder, no symlink), and
   runs `classroom apply` without planning again; what was not brought apply notes «no traído».
   The pass is skipped when the plan asks for nothing or the first pass ended `session_expired`,
   `challenge` or breached.
7. On a stop, the macOS notification in Spanish (FR-032), except under `CLAUDECODE`; one log line
   with what started it (`ALFABETA_STARTED_BY`: `schedule`, or `command`; FR-020); release the locks.

### Slices

Tasks in [tasks.md](tasks.md). No test reaches a real account, a keychain value or a Google host,
and none needs `CLAUDECODE` lifted.

0. **Shared vocabulary** — the new stop codes, `contracts/cli.md`, `data-model.md`.
A. **`classroom password set|delete`** — FR-031, the mark, its own keychain service. Claude alone.
B. **`read.py` against the fake** — FR-006, FR-008, FR-009, FR-027, FR-029, FR-030, SC-004, SC-009,
   run as a module with Playwright's Chromium in CI, the fake's hosts set in the test. Claude alone.
C. **`classroom refresh`** — FR-019, FR-020, FR-022, FR-024a, FR-028, FR-032, with a fake
   `ReadContainer`, the real adapter's argv tested with a fake runner, and the built image checked
   offline (`--network none`). Claude alone; the first real run is the family's.
D. **Attachments in the container** — FR-028, FR-030's exception, against the fake: a second pass
   of the container over the plan's downloads (run flow, step 6).
E. **`classroom agent install|uninstall`** — FR-015. The family installs it.

0 first; A and B in parallel; C after both; D after B and C; E after C.

### Constitution Check (amendment)

| Principle | How | Status |
|---|---|---|
| II | The password in the keychain (spec 004's store); the profile under `data/` with mode 0700; stdin only into the container; `--rm`; nothing beside the configuration | Pass |
| III | The deterministic script types; Claude never starts it (`CLAUDECODE` refusal, R15); one try of a wrong password; the family's acceptance quoted in the spec; ids only in logs and notifications | Pass |
| IV | `read.py`'s guard: presses, page loads outside FR-007's pages, form, quiz and download hosts blocked before they reach Classroom; attachments only from this run's list by R4's routes, checked before each request; any check stops the read; nothing typed past it; no guard setting comes from the environment | Pass |
| VIII | `read.py` sets the browser zone to Europe/Madrid and the locale to es-ES; a test renders a due date from an instant where UTC differs, and across a DST change | Pass |
| IX | On the Mac; Docker and Chrome in the image justified below | Pass with the rows below |

### Complexity Tracking (amendment)

| Departure | Why it is needed | Simpler alternative rejected because |
|---|---|---|
| Docker Desktop on the Mac and an image with Google Chrome and Playwright | The operator's requirement of portability («se ejecuta donde se pueda», spec FR-028): the same read runs unchanged wherever Google accepts the sign-in | The host's Chrome also signed in (S14); rejected by the operator's requirement, not by a measurement |
| Google Chrome in the image instead of Playwright's Chromium | The measured sign-ins used Google Chrome (S14); Chromium was not measured against Google | Chromium: one less download, but an unmeasured browser on the one step Google judges |

## Credit

The read's pattern — a profile kept for the read, the hand sign-in in the plain browser, Classroom's
own read calls from one page behind an allowlist, the account check before any call, and the cookie
flags on macOS — comes from lifecoderua/classroom-advisor (MIT), read on 2026-11-02. Any code later
ported from it keeps its copyright notice and is listed in `THIRD_PARTY_NOTICES.md` (research R13).

## Complexity Tracking

| Departure | Why it is needed | Simpler alternative rejected because |
|---|---|---|
| `playwright` for Python at runtime on the Mac (IX) — *amendment 2026-11-17: in the container read, pinned in the image (1.64.1) and in the dev group for `test_classroom_read.py`; the host runs no browser* — and its headless browser in the CI job for the guard test | The read must start a browser with no person at it, on a given profile, with a guard on every request before any page script (constitution IV); the standard library cannot drive a browser (research R2). Spec 001 already justified it for the runner's image | The Claude extension and the built-in browser need the app and a window, the two needs this spec removes; Chrome's DevTools protocol by hand needs a WebSocket client the standard library lacks and rewrites Playwright's tested routing; Selenium has no interception before page scripts |
| A launchd agent and a launcher for `classroom refresh` (Technical constraints, 2.6.0) | The read must start at the scheduled times and from the phone with no app open (FR-001, FR-015, FR-016) | The desktop app's scheduled task: needs the app open, which the spec removes |
| A read by Classroom's undocumented internal calls (VI: a second capture route) | One page load instead of 126, and no stall when no window is on screen (research R1) | The DOM extractor headless: the same 126 loads; the Classroom API: refused for this account (spec 001 R20) |
| Optional structured fields in spec 001's capture | The calls give instants and enums, not the Spanish texts; inventing those texts would test an invention (research R7) | A second capture format with its own apply: doubles spec 001's apply |
| A Gmail send scope on a family account (spec 004 as amended) | The notice must reach the family away from the Mac (FR-013) | A calendar reminder rings for the student only; a messaging app is a third party (III) |
