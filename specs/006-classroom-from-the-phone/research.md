# Research: Classroom read on the Mac with no app open, signed in from the phone (spec 006)

Phase 0 of the plan. Each decision carries its reason and the alternatives rejected. Facts measured
on this account cite where they were measured; facts read in another project are marked as read, not
measured. Nothing below names the student, the teachers or a real identifier.

## Observed facts

Measured on this account before this plan (the spec's table holds the rest):

| Fact | Measured with | Date |
|---|---|---|
| A full read by the current extractor, window on screen, took about 11 minutes for 12 classes: 126 pages (each class's listing and stream, plus 102 item details), 13–128 s per class, 2–3 s between pages | the family's manual run, scheduled mode, after `notice send-sign-in` | 2026-11-02 |
| The run of the day before, window covered and the Mac asleep for part of it, read 6 of 12 classes before the session died about 61 minutes after the sign-in | the first scheduled run of FR-021a | 2026-11-01 |
| Loading a Google page with Claude in Chrome's `navigate` drew «Demuestra que eres tú» on the school account twice; about 120 iframe loads and 11 `location.assign` loads drew none. The likely cause is Chrome's device-bound session credentials (DBSC) refusing a load another program starts, which was not proven | the operator's Chrome | 2026-10-27 |
| A capture item without a detail stops the normaliser (`capture.py`: «an item has no detail»), so a capture must carry every item's detail; an incremental capture that leaves unchanged items out is not something the apply step reads today | `src/alfabeta/capture.py`, read | 2026-11-02 |
| Today's capture holds Classroom's Spanish texts (`listing_date_text`, `due_text`, `status_text`…) and the normaliser derives dates with `DateResolver` and the status with data-model.md's table «Status from the detail texts» | `specs/001-classroom-sync/contracts/capture.schema.json`, `capture.py`, read | 2026-11-02 |
| The launchd agent of spec 005 (`notebook agent install`) was built but has not been installed in this house (#105, T047), so no alfabeta command has yet run from launchd here | the handoff of 2026-11-02 | 2026-11-02 |

Read in lifecoderua/classroom-advisor (MIT; `README.md`, `docs/ARCHITECTURE.md`,
`docs/CLASSROOM-INTERNALS.md`, read 2026-11-02). These describe another school domain and were not
measured on this account; they seed the spikes below and replace none of them (FR-004).

| What the peer project reports | Where |
|---|---|
| Classroom pages embed no data; every page's data arrives through `POST /u/<n>/_/ClassroomUi/data/batchexecute?rpcids=<name>…`, form body `f.req=…&at=<token>`, answered as `)]}'` and length-prefixed JSON rows `["wrb.fr", "<name>", "<payload>", …]` | CLASSROOM-INTERNALS, «batchexecute» |
| The tokens a direct call needs (`at`, `f.sid`, `bl`) and the signed-in user sit in the page's `WIZ_global_data`; the signed-in email can be compared with the expected account before any call | CLASSROOM-INTERNALS, «Initial HTML», «RPC client» |
| Thirteen call names seen in a student's read-only browsing, all reads by their response tags (`hrq.crs` courses, `hrsi.qr` stream-item query, `hrq.sub` submissions, `hrcw.qr` classwork per topic, `hrt.qr` topics, `t51ITc` materials of one item, `hrq.cmt` comments…), with masks that choose the fields returned | CLASSROOM-INTERNALS, «RPCs seen» |
| Ids are decimals; the page URLs carry the base64, without padding, of the decimal string — the `<xB64>` spec 001 records in S3 | CLASSROOM-INTERNALS, «Pages and URLs» |
| Calling these names directly with `fetch` from one loaded page, headless included, worked, with no challenge, captcha or re-auth seen during their recon | CLASSROOM-INTERNALS, «Recommended collection strategy» |
| The hand sign-in opens the plain installed browser on the read profile, with no automation attached, because Google often refuses a sign-in in a browser it sees as automated; the read then opens the same profile with Playwright (`launchPersistentContext`, channel `chrome`) | ARCHITECTURE, «Hand login», «Accounts» |
| On macOS, Playwright's default flags `--use-mock-keychain` and `--password-store=basic` leave Chrome unable to decrypt the profile's cookies (their key is in the macOS keychain), so the hand-made sign-in looks gone; the peer drops both | ARCHITECTURE, «Accounts» |
| A live `SingletonLock` in the profile means a browser holds it; the read refuses to open it | ARCHITECTURE, «Accounts» |
| Files are fetched through the session's request context (`context.request`), not a browser download | ARCHITECTURE, «Data sources» |
| All timestamps are UTC epoch milliseconds; a due date «without time» shows as 23:59 local | CLASSROOM-INTERNALS, «Dates and time zones» |

## Decisions

### R1. The read: Classroom's own read calls from one loaded page, in a headless browser on the Mac

- **Decision**: `classroom capture` opens the student's read profile headless with Playwright for
  Python (channel `chrome`, the installed Google Chrome), with the guard of R4 installed first,
  loads one Classroom page, checks the account (R6), reads the tokens from `WIZ_global_data`, and
  sends the allowlisted read calls (R3) one at a time with a pause between them (≥ 1 s, jittered),
  through `fetch` run inside that page so the request carries the page's own origin and cookies.
  It parses the answers into spec 001's capture (R7).
- **Rationale**: the pages it loads carry no data of their own, and a read by calls needs one page
  load per run instead of 126; the hidden-iframe extractor stalls when its tab is not on screen
  (spec 001 Observed facts, 2026-10-28) and a headless page has no screen to lose. The peer
  project reports the same calls working headless (read, not measured — spikes S8 and S9).
- **Pacing**: one call at a time, as a student's browsing makes several calls per page
  (constitution IV); each class needs a handful of calls, so a whole read is expected to take
  minutes, well inside SC-003's 30 minutes. S9 measures it.
- **Only what changed**: every run lists every active class's items (cheap: a few list calls per
  class), but asks for an item's materials (`t51ITc`-like, one call per item) only when its update
  mark differs from the last capture of that class; otherwise it copies that item's attachment list
  from the last capture. The capture stays complete, as `capture.py` requires (Observed facts), and
  the run answers the operator's question of 2026-11-02 («why not only the last day's changes»)
  without a capture format that leaves items out. A periodic full read (`[sync] full_review_days`,
  spec 001 R4) asks again for every item.
- **Alternatives rejected**: the current DOM extractor in a headless page — 126 page loads, the
  slowest part of today's read, and a DOM made for the eye (collapsed sections, localised labels);
  the extension route — needs the Claude app and a window, the two needs this spec removes; reading
  Classroom's per-event emails — behind the same session (spec 001 R20).

### R2. The browser: Playwright for Python driving the installed Google Chrome

- **Decision**: `playwright` (Python, pinned) as a runtime dependency on the Mac, used only by
  `classroom capture`, `classroom status` and the account check after a sign-in. It drives the
  installed Google Chrome (`channel="chrome"`), never Playwright's bundled Chromium, so the sign-in
  window (R5) and the read share one installation (FR-002) and one keychain entry for cookie
  encryption. Playwright's defaults `--use-mock-keychain` and `--password-store=basic` are removed
  (`ignore_default_args`), as the peer project reports they must be (read; S7 measures it).
- **Rationale**: the read needs a browser started with no person at it, given a profile, and guarded
  request by request before any page script runs (R4); the standard library cannot drive a browser
  (spec 001 plan, Complexity Tracking, the same justification for the runner's image).
- **Alternatives rejected**: Chrome's DevTools protocol by hand — needs a WebSocket client the
  standard library lacks and rewrites what Playwright tests; Selenium — WebDriver sets
  `navigator.webdriver` and has no request interception before page scripts; Playwright's bundled
  Chromium — a different application, whose cookie key would be a second keychain entry and whose
  first use could raise a keychain dialog mid-run (the family's standing rule: no prompts during a
  run).

### R3. The allowlist of read calls (FR-004)

- **Decision**: the allowlist is the exact set of call names that Classroom's own pages send while
  they are loaded read-only, with zero presses, for every page the read needs — the class list, a
  class's classwork, its stream, an assignment's, a material's and a question's detail, and the
  to-do lists — recorded on this account in spike S8, with each name's response tag. A name is
  admitted only if every response seen for it carries a query, list or get tag (as the peer's
  `hrq.*`, `hrsi.qr`, `hrcw.qr`, `hrt.qr`) and it is needed for a field the capture holds. A name
  never seen is blocked and counted. The peer's thirteen names seed what S8 looks for; they are not
  copied into the allowlist.
- **What cannot be measured, said plainly**: no spike sends a write to prove it is one, since that
  is what constitution IV forbids. "Reads and writes can be told apart by call name" therefore means:
  a read-only load of every page needed sends only names whose responses are queries, and each name
  the read needs is one of those. If a read-only load itself sends a name whose response is not a
  query (a "seen" mark, a view counter), that name stays blocked; if a page then fails to give the
  read what it needs, FR-004 is not met and the read is not built.
- **Batched calls**: one `batchexecute` request can carry several names (`rpcids=a,b`); the guard
  admits it only if every name in it, in the URL and in the body, is on the allowlist.
- **Drift**: a Classroom release can rename a call. The read then finds a needed name missing from
  the answers or a page asking for a blocked name; the class stops with `unexpected_ui` (FR-008)
  and the log counts the blocked name, never its body. The allowlist is changed only by a new
  recording, in a pull request.

### R4. The guard (FR-005), installed before any page script

- **Decision**: spec 001 research R18's guard, built for the Mac: a Playwright init script on every
  frame, and request routing on the browser context.
  - **presses**: capture-phase listeners cancel every `click`, `submit`, `keydown` and `pointerdown`
    and wrap `HTMLFormElement.submit`/`requestSubmit`; the read presses nothing, so, unlike R18, no
    control is allowlisted;
  - **document loads**: only `classroom.google.com`, only the one page the read opens (R1) and the
    pages spec 001 FR-007 lets the full sync load; a load to `accounts.google.com` ends the run
    `session_expired` (FR-010), any other is blocked;
  - **background calls**: `batchexecute` only with every name on the allowlist (R3); requests to
    form or quiz hosts (`docs.google.com/forms`, `forms.gle`) blocked;
  - **session upkeep**: requests that only keep the session (Google's cookie rotation on
    `accounts.google.com`, the device-bound session refresh) are allowed and counted, since blocking
    them could end the session (Observed facts, DBSC); S8 records which appear and S9 checks the
    session survives a full read with them;
  - **everything else** a page asks for (telemetry, push channels) is blocked and counted, unless S8
    shows the page cannot load without it, in which case it is allowed by exact host and path and
    recorded here;
  - **downloads**: no browser download; the read fetches only the attachments it listed in this run,
    through the session's request context (R8), and the adapter refuses any other id.
- **Test** (SC-004): offline, in CI, a real headless browser opens a local fake Classroom that serves
  synthetic pages with a planted «Entregar» press, a planted form link and a planted write call
  name, and a planted press fired by the page's own script; all are blocked and counted and none
  reaches the fake server. The JavaScript init script also has `node --test` cases with `jsdom`,
  like the extractor's (spec 001 R11).

### R5. The sign-in window: the plain installed Chrome, and how alfabeta knows it is done (FR-010)

- **Decision**: `classroom sign-in` starts the installed Google Chrome as a separate process —
  `--user-data-dir=<read profile>` and the Google sign-in page for the school account — with no
  Playwright, no extension and no script of alfabeta's. To know the family has signed in without
  reading anything but the address, alfabeta starts that Chrome with `--remote-debugging-port=0`
  and polls, every few seconds, the browser's local `GET /json/list` (on the loopback port Chrome
  writes to `DevToolsActivePort` in the profile), which lists each tab's address, title and icon; the adapter keeps only each tab's `url` field and discards the rest of the answer unread, so a title that names the account is never kept; it never attaches
  to a tab, never runs `Runtime` or any script, and compares each address with Classroom's in
  memory without logging or storing it. When an address reaches `classroom.google.com`, alfabeta
  closes the browser (SIGTERM, so Chrome writes its cookies; then SIGKILL after 10 s); the family may
  also close it; `schedule.wait_minutes` ends it otherwise.
- **To be measured (spike S7)**: that Google accepts the hand sign-in in a Chrome started with that
  flag (the peer's reason for no automation is that Google refuses sign-ins it sees as automated;
  the flag sets no `navigator.webdriver`, but this is not measured), and that `/json/list` shows
  the address change.
- **Fallback if S7 refuses it**: the window starts with no flag, and alfabeta watches only the
  process: the wait ends when the family closes the window or at `wait_minutes`. That is the spec's
  first wording, which the independent review rejected because the session could die while the
  read waits; the notice would then ask the family to close the window, and FR-010 would be amended
  before building.
- **Alternatives rejected**: AppleScript to Chrome for the active tab's address — with the family's
  everyday Chrome running, "Google Chrome" names two processes and the script can read the wrong
  one, and it needs an Automation permission for the whole application; reading the profile's
  files (history, cookies) — reads more than the address, which FR-010 forbids.
- **Bringing the window to the front** (FR-013, FR-017): by the process id alfabeta started, through
  the macOS seam (`NSRunningApplication` activation via `osascript`/System Events, a one-time
  permission granted at set-up, never mid-run). S7 checks it does not raise a prompt during a run.

### R6. The account check (FR-006)

- **Decision**: after loading the one page, the read compares, in memory, the signed-in address the
  page declares (the peer reads it from `WIZ_global_data`) with `[classroom] account`; if it differs,
  or the page is Google's sign-in, the run stops `session_expired` before any call, and the result
  email says another account was signed in, without naming it. The read profile holds only the
  school account: the sign-in window opens Google's sign-in with no other account in it.
- **Index**: `/u/<n>` is that of the account in the read profile, normally `0`; the capture's
  `account_index` keeps it, as today.

### R7. From call answers to spec 001's capture (FR-007, SC-005)

- **Identifiers**: the capture keeps today's ids, the URL's `<xB64>`: the read encodes each decimal
  id from the answers as base64 of the decimal string without padding, so a capture by calls and one
  by the extractor name the same items. S9 checks it on every class.
- **Dates and statuses**: the answers give instants (UTC milliseconds) and enums, not the Spanish
  texts today's capture holds. The capture grows, in a minor version, optional structured fields —
  `posted_at`, `modified_at`, `due_at` (with whether a time was set), `status` (an `ItemStatus`
  value), `grade` and `returned_at` — and the normaliser takes them when present and the texts
  otherwise. The texts stay what the extractor writes and are left `null` by the read; nothing
  writes a Spanish text the page did not show. Instants are converted to `Europe/Madrid` with
  `zoneinfo` (constitution VIII); a date without a time stays a date.
  - The status mapping from the submission's to-do bucket to `ItemStatus` is a hypothesis from the
    peer's table (assigned → `pending`, missing → `overdue`, turned in → `turned_in`, done late →
    `turned_in_late`, returned and graded → `returned`), and «El profesor ha indicado que falta
    esto» (`missing_per_teacher`) has no seen field; S9 compares both reads of the same day class by
    class and the table in data-model.md is filled from that comparison, not from the peer.
- **Alternatives rejected**: writing the Spanish texts the page would have shown from the instants
  — the read would invent text and its tests would test the invention; a second capture format
  with its own apply — doubles spec 001's apply and its tests (IX).
- **Stream**: the class stream's announcements, through the stream query; S8 records which call
  and type carry an announcement (the peer documents assignments, not announcements).
- **Judgement** (FR-007): unchanged — a class not linked to a subject, a new topic match and an exam
  candidate are left pending by `classroom plan`, as today.

### R8. Attachments through the session's request context (FR-005)

- **Decision**: R4 of spec 001's routes, sent through Playwright's request context of the read
  profile instead of a hidden iframe and the downloads folder: `drive.usercontent.google.com/download`
  for files and `docs.google.com/<type>/d/<id>/export` for Google files, with the `authuser` of R6.
  The file is written straight to the place `download collect` uses, so `classroom plan` and
  `classroom apply` read it as today. Only ids this run listed; a sign-in page as the answer is
  `session_expired`; Drive's virus-scan notice is «no traído», as today.
- **To be measured (spike S9)**: that both routes answer through the request context, and that the
  bytes equal those of the last replicas.

### R9. Notices by email from the `family` account (FR-013, FR-014)

- **Decision**: one `Mailer` port; its adapter sends through the Gmail API `users.messages.send`
  with spec 004's `HttpTransport` and the token of the account linked with role `family` and scope
  `gmail.send` only (spec 004 FR-004, FR-005 as amended), from that account to itself. Texts in
  Spanish, naming the student by its id and nothing from Classroom (FR-014); a test over every
  template (SC-006).
- **Depends on**: spec 004's role `family` and the Gmail scope, which no code links yet; that is
  its own task in spec 004 before slice 5.
- **To be measured (spike S12)**: how long the email takes to reach the phone and whether Gmail
  notifies the phone of a message the account sent to itself. If it does not, the plan's fallback
  is the family account sending to a second address the family names, which would amend FR-013
  before building.

### R10. One link for the Mac and the phone (FR-013)

- **Candidates** (spike S11 picks):
  1. The remote view's own link (Chrome Remote Desktop's access page for the Mac): on the phone it
     opens the remote view; on the Mac it opens a web page, not the sign-in window.
  2. A link to the launcher (`classroom agent install` registers it): on the Mac it runs
     `classroom refresh`, which, with a read already waiting, brings the sign-in window forward
     (FR-017); on the phone it opens nothing.
  3. A page of the family's own that tells the two apart and forwards — a third host or a page on the
     Mac reachable from outside, which constitution III and IX do not allow.
- **Expected**: no single link does both; the measured answer goes in this section, and FR-013 is
  amended before building if two links, or one link and the macOS notification, are needed.
  On the Mac the macOS notification (FR-021a) already reaches the family, so candidate 1 alone may
  be enough.

### R11. The schedule and the launcher (FR-015, FR-016, FR-017)

- **Decision**: `classroom agent install --student <id>` writes a launchd agent in the family's user
  session (`~/Library/LaunchAgents`, `StartCalendarInterval` from `[schedule]`, one entry per
  weekday time) that runs `classroom refresh --student <id>`, and a launcher the family opens from
  Finder, Spotlight or the remote view (a small application bundle that runs the same command).
  `classroom agent uninstall` removes both. Same pattern and adapter as spec 005's `notebook agent`
  (`notes/agent.py`'s `Launchctl` port).
- **Asleep**: launchd runs a missed `StartCalendarInterval` at the next wake; `classroom refresh`
  started outside the configured hours (more than `wait_minutes` after its time) logs the miss and
  ends (FR-015 «not made up»).
- **Exclusivity**: `config check` reports `[classroom] profile_read = true` together with spec 001's
  unattended runner switched on for the same student (FR-015).
- **Second launch** (FR-017): the student's lock is held: the command says a read is under way and,
  while a sign-in waits, brings its window to the front (R5).

### R12. The five seams (FR-025)

| Seam | Port | Mac implementation | Fake in CI |
|---|---|---|---|
| Secrets | spec 004's `TokenStore` | the macOS keychain | in-memory store |
| Scheduler | `Scheduler` | launchd (`classroom agent`) | records the plist it would write |
| Remote view | `RemoteView` (the notice's link) | Chrome Remote Desktop | a fixed link |
| Local notification | spec 004's `Notifier` | `osascript` (`MacNotifier`) | records texts |
| Mirrors | spec 001's mirror step | Google Drive for desktop | temp folders |

Around the sign-in, Mac-only: the browser installation (`BrowserInstall`: where Chrome is), the
sign-in window (`SignInWindow`: open, address, front, close) and the launcher, each behind a port
with a fake. SC-007's Linux job runs every command's tests against the fakes; the guard test uses
Playwright's own headless browser on Linux, which tests the guard, not the Mac's Chrome.

### R13. What is taken from the peer project

- **Taken as pattern** (credited in the plan): a profile kept for the read; the hand sign-in in the
  plain browser; the read by named calls from one page with an allowlist; the account check before
  any call; the cookie-key flags on macOS.
- **Taken as seed** for the spikes, never as the measurement: the call names, masks and positions.
- **Code**: none ported by this plan. If a task ports code or request templates from it, the file
  keeps the MIT copyright notice of lifecoderua/classroom-advisor, and `LICENSE`'s neighbour
  `THIRD_PARTY_NOTICES.md` lists it. Its fixtures are another family's anonymised data and are not
  copied: alfabeta's fixtures are invented (constitution III).
- **Not taken**: a database, Telegram (constitution III), the LLM checks, a `.env` for keys
  (constitution II), the `drive.google.com/uc` download (spec 001 R4 found it fails).

## Spikes before the build

Each spike runs read-only, with code kept outside `main` (a `spike/166-…` branch, as S4 was), and
records its result in this file with its date. Pass criteria are written so the gate is objective.
**Who** says what each needs: *agent* — Claude alone; *family sign-in* — someone signs the school
account in by hand at the Mac (or through the remote view); *family phone* — the family's own phone
with their Google account. No spike needs the student's phone: the remote view and the notices are
the family's.

| Spike | Who | Pass | If it fails |
|---|---|---|---|
| **S7 · The sign-in window and the profile.** Start the installed Chrome with a fresh profile in the data folder and `--remote-debugging-port=0`; the family signs in by hand; `/json/list` shows the address reach Classroom; alfabeta closes it; Playwright (`channel="chrome"`, keychain flags removed) opens the profile headless and loads one Classroom page with the session; the window can be brought to the front by process id | agent + family sign-in | Google accepts the sign-in with no extra check beyond the family's usual one; the address change is seen; the headless open reads the session with no keychain dialog | Sign-in refused with the flag: R5's fallback (watch the process only) and FR-010 amended. Session not readable headless: the read is not built |
| **S8 · The calls of every page** (widens spec 001's S6). Behind the minimal guard (document-load allowlist, zero presses), load once each page kind of R3 for two classes, headless, and record per request: method, host, path, call names, response tag — never bodies or cookies | agent + family sign-in | Every capture field comes from a name whose responses are queries; the pages load with everything outside those names and the session upkeep blocked; the stream's announcements are found | A needed field only behind a non-query name: FR-004 not met, the read is not built, this plan says so |
| **S9 · A whole read by calls, compared.** Same day, same classes: the current extractor (the family's usual run) and a throwaway read by S8's names from S7's profile, headless, timed; then fetch every listed attachment through the request context (R8) | agent + family sign-in | All classes read in under 30 minutes of the sign-in with no challenge; the same item ids (base64 of decimals), types, topics, attachments and stream posts; the status table of R7 filled with no contradiction; attachment bytes equal the replicas | A challenge: stop (constitution IV), record it, the read is not built. Differences: recorded per field; a field that cannot be matched is a spec question before building |
| **S10 · From launchd, screen locked, no app open.** Install a throwaway LaunchAgent that runs S7's headless open at a set minute; the family locks the Mac and closes the Claude app; then a second agent opens the sign-in window | agent + family (lock the Mac, sign in) | The headless open reads the session with no keychain or other dialog; the window is there when the Mac is unlocked | A keychain dialog: the read profile's cookie key needs a one-time "Always allow" at set-up, recorded in the quickstart; a window that cannot open while locked: FR-012's unlock-first order is written into the notice |
| **S11 · The remote view and the link.** Set up Chrome Remote Desktop to the Mac on the family's Google account; from the family's phone, open the remote view, unlock the Mac with its password, sign in in the window; time it; try R10's candidates from the phone and from the Mac | family phone + family sign-in | The sign-in completes from the phone in under 2 minutes from opening the link (SC-002); R10 records which link does what | No remote view to a locked Mac: the family signs in at the Mac, and FR-012 is amended |
| **S12 · The notice email.** Link a family account with `gmail.send` only (a throwaway link, revoked after), send a notice to itself from a script | family (consent, phone) | The phone notifies within a minute; the time is recorded | No notification of a self-sent email: R9's fallback, FR-013 amended |
| **S13 · Idle or absolute session limit.** After a sign-in, load one Classroom page every 5 minutes until the session dies; then, after another sign-in, load nothing for 35 minutes and check once | agent + two family sign-ins | Whichever answer, recorded: it sets how soon `classroom refresh` must start reading after the sign-in, and whether `classroom sign-in`'s check must be immediate | Nothing to fail: it measures |

Order: S7 first — every other live spike stands on its profile. S8 and S9 follow in one sitting
with one sign-in when the session allows; S10 to S13 do not depend on S8–S9 and can be done on any
day. The build's slice 1 (offline) does not wait for the spikes; slices 2 onwards do (plan,
Vertical slices).

Note on S13: loading a page every 5 minutes is a measurement, not a route. Keeping the session
alive between reads is out of this spec (reading with nobody signing in, spec 001 User Story 7).
