# Implementation Plan: Classroom read on the Mac with no app open, signed in from the phone

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
- no prompt mid-run: every macOS permission (keychain, window activation) granted once at set-up.

**Scale/Scope**: one student, twelve classes, about a hundred items; one read a school day, plus the
family's launches.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Checked against
constitution 2.6.0, amended by the spec.

| Principle | How the plan meets it | Status |
|---|---|---|
| I. The student is configuration | The school account, the switch and the notice account are configuration; the profile lives in the student's data folder; two students have two profiles and run one at a time under the browser lock | Pass |
| II. Three layers | Two template keys with `changeme`; the session in the data folder (user-only); the family's token in the keychain; nothing in a file beside the configuration; nothing copied off the Mac | Pass |
| III. Minors' data | The family types the sign-in; alfabeta stores no password or second factor; emails and logs carry the student's id and counts only, tested (SC-006); the sign-in address never logged; data goes to Google (the family's account sends the email) and nowhere else; fixtures invented, not the peer's | Pass |
| IV. Read-only on the school's platforms | The guard of research R4 in the browser before any page script: presses cancelled, document loads and calls allowlisted by name, form hosts blocked; the allowlist from read-only loads only (R3), and no write is sent to test it; a challenge stops the run; no stealth flags, no proxy: only the keychain flags Chrome needs to read its own cookies are changed | Pass, conditional on S8 (if reads cannot be told from writes by name, the read is not built) |
| V. Idempotent, incremental | Captures keep today's ids (base64 of the decimal id, R7); apply unchanged; an unchanged item's materials are copied from the last capture, and a periodic full read asks again (R1) | Pass |
| VI. One isolated, tested provider | The read is a second capture route of the Classroom provider behind the same capture contract; one class's failure stops only that class (FR-008); tests against fake answers and a fake Classroom, never the real one | Pass |
| VII. Outputs degrade on their own | A failed email does not stop the read; a failed read applies what it read (`partial`); the mirrors and the agenda as today | Pass |
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
├── signin.py       # SignInWindow port + ChromeSignInWindow (process, /json/list, front, close); classroom sign-in
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
5. `classroom plan` and `classroom apply` (spec 001), which apply, bring the mirrors up to date and
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

## Credit

The read's pattern — a profile kept for the read, the hand sign-in in the plain browser, Classroom's
own read calls from one page behind an allowlist, the account check before any call, and the cookie
flags on macOS — comes from lifecoderua/classroom-advisor (MIT), read on 2026-11-02. Any code later
ported from it keeps its copyright notice and is listed in `THIRD_PARTY_NOTICES.md` (research R13).

## Complexity Tracking

| Departure | Why it is needed | Simpler alternative rejected because |
|---|---|---|
| `playwright` for Python at runtime on the Mac (IX), and its headless browser in the CI job for the guard test | The read must start a browser with no person at it, on a given profile, with a guard on every request before any page script (constitution IV); the standard library cannot drive a browser (research R2). Spec 001 already justified it for the runner's image | The Claude extension and the built-in browser need the app and a window, the two needs this spec removes; Chrome's DevTools protocol by hand needs a WebSocket client the standard library lacks and rewrites Playwright's tested routing; Selenium has no interception before page scripts |
| A launchd agent and a launcher for `classroom refresh` (Technical constraints, 2.6.0) | The read must start at the scheduled times and from the phone with no app open (FR-001, FR-015, FR-016) | The desktop app's scheduled task: needs the app open, which the spec removes |
| A read by Classroom's undocumented internal calls (VI: a second capture route) | One page load instead of 126, and no stall when no window is on screen (research R1) | The DOM extractor headless: the same 126 loads; the Classroom API: refused for this account (spec 001 R20) |
| Optional structured fields in spec 001's capture | The calls give instants and enums, not the Spanish texts; inventing those texts would test an invention (research R7) | A second capture format with its own apply: doubles spec 001's apply |
| A Gmail send scope on a family account (spec 004 as amended) | The notice must reach the family away from the Mac (FR-013) | A calendar reminder rings for the student only; a messaging app is a third party (III) |
