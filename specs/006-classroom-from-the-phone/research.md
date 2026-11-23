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
- **Rationale**: the pages it loads carry no data of their own (read in the peer project; S8
  measures it), and a read by calls needs one page
  load per run instead of 126; the hidden-iframe extractor stalls when its tab is not on screen
  (spec 001 Observed facts, 2026-10-28) and a headless page has no screen to lose. The peer
  project reports the same calls working headless (read, not measured — spikes S8 and S9).
- **Pacing**: one call at a time, as a student's browsing makes several calls per page
  (constitution IV); each class needs a handful of calls, so a whole read is expected to take
  minutes, well inside SC-003's 30 minutes. S9 measures it. *(2026-11-20, S9: 118 and 106 calls
  for two classes, 1.79 s a call; about 17 minutes extrapolated for the run's 12 classes, under
  30 but slower than the extractor's 884 s for the same run; research «S9».)* *(2026-11-20, family
  decision, #283: every list call is paged until Classroom says there is no more, whatever the
  page size seen. *(2026-11-23, S9's third measurement: the next-page token is at answer `[1,1,0]`
  and goes at request `[0][1]`; within a topic read 3 a page, the pages equal the capture's items
  of that topic, 3 topics of 3. Lists longer than 10 gave 5 items the extractor's capture lacks,
  #288.)* Classes are not read in parallel: constitution IV, «no bursts». Whether calls can
  be grouped as the page itself groups them — several items in one call, several names in one
  request — is measured in S9's second measurement; FR-003's «one call at a time» stands until
  then.)* *(2026-11-23, S9's second and third measurements: several calls in one request — two
  names, or one name six times — are answered, and six `t51ITc` calls in one request give the same
  attachments as one request each; `Zj93ge` with 12 items in one call, as the page sends it, gives
  the same statuses as one call per item. A whole read of the 12 classes with `Zj93ge` still one
  item a call took 270 requests and 503 s. FR-003 now reads «one request at a time», several calls
  in a request as the page sends them: the operator, 2026-11-23, spec Clarifications.)*
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
- **Revised 2026-11-17 (amendment, FR-030)**: the DOM extractor headless was measured working inside
  the container: 12 of 12 classes complete in 14 min 20 s, the same items as the Chrome read
  (S14). It ships first, unchanged, because it already produces the captures spec 001 applies; the
  read by calls stays the planned optimisation of the same captures, not a precondition.

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
  `hrq.*`, `hrsi.qr`, `hrcw.qr`, `hrt.qr`) and it is needed for a field the capture holds (or the
  page needs it: see «A tagged name the page needs» below). A name
  never seen is blocked and counted. The peer's thirteen names seed what S8 looks for; they are not
  copied into the allowlist.
- **One exception, by name (family decision of 2026-11-19, #270)**: `t51ITc` is admitted although its
  answers carry no tag. S8 found it the only name whose answers hold the teacher's attachment ids;
  the pages send it themselves while they load or sit open, with zero presses, alongside the tagged
  queries, and its non-empty answers are the item's materials keyed by item id, not an
  acknowledgement. Today's container read already lets it reach Classroom (S8 measured it behind
  the read's own guard), though the read by calls would send it with its own arguments, not the
  page's. That is consistent with a read and does not prove one (see below): admitting it is the
  family's decision («Admitirla, seguir», the operator, 2026-11-19; spec Clarifications, Session
  2026-11-19), not a measurement. No other untagged name is admitted; a new one stays blocked until a
  recording and a decision of its own.
- **The to-do lists** (2026-11-19, «S8, last pieces»): not needed for the fields the two classes of
  S8's second half hold — their statuses came through the ten names, from FR-030's pages — so they
  leave the list of pages above; S9's whole read confirms it for every class. *(2026-11-20, S9: the
  statuses of two classes came through `Zj93ge`; the other ten classes were not read.)*
- **A tagged name the page needs** (2026-11-19, S8's second half): a name every answer of which
  carries a query, list or get tag (as recorded in S8's first half) but no field of the capture is
  admitted when a recording shows the page the read loads failing with it blocked — by the same
  test as R4's for what a page cannot load without. The page sends it; the read by calls never does,
  and nothing of its answer is kept (constitution III). S8 found one, `UG41I` (`hrq.usr`): with it
  blocked the home page listed no class (16:43). *(2026-11-20, family decision, spec Clarifications
  2026-11-20, #283: the read by calls sends `UG41I` once, first, for the student's own number, which
  it keeps in memory for that run only; nothing else of the answer is kept.)* *(2026-11-23, S9's
  second and third measurements: `UG41I` answers with the number only when its request already
  carries it — the page's own shapes that carry it, 3 of 3; those without it, 3 of 3 not. So the
  read cannot learn the number by sending `UG41I`. The number is in the page's own requests as it
  loads (`O1Xqee`'s, and `UG41I`'s), and in no `WIZ_global_data` key. Decided by the operator,
  2026-11-23 (spec Clarifications): the read takes it from the page's own request as the page
  loads, keeps it in memory for that run only, and sends eight names, neither `UG41I` nor
  `O1Xqee`.)*
- **What cannot be measured, said plainly**: no spike sends a write to prove it is one, since that
  is what constitution IV forbids. "Reads and writes can be told apart by call name" therefore means:
  a read-only load of every page needed sends only names whose responses are queries, and each name
  the read needs is one of those. If a read-only load itself sends a name whose response is not a
  query (a "seen" mark, a view counter), that name stays blocked; if a page then fails to give the
  read what it needs, FR-004 is not met and the read is not built. (Save the exception above, admitted by name.)
- **Batched calls**: one `batchexecute` request can carry several names (`rpcids=a,b`); the guard
  admits it only if every name in it, in the URL and in the body, is on the allowlist.
- **Drift**: a Classroom release can rename a call. The read then finds a needed name missing from
  the answers or a page asking for a blocked name; the class stops with `unexpected_ui` (FR-008)
  and the log counts the blocked name, never its body. The allowlist is changed only by a new
  recording, in a pull request.
- **What the read by calls sends** (2026-11-20, S9): eight of the ten names — never `UG41I` nor
  `O1Xqee`, which the home page sends itself. `Zj93ge` needs the student's own number, which only
  `UG41I`'s answer (and `O1Xqee`'s and `Zj93ge`'s own) carries; S9 took it from the home page's own
  `O1Xqee` request. Whether the read may take it so is open (research, «S9»). *(2026-11-20, family
  decision, #283: the read sends `UG41I` itself, once, as above; nine names, never `O1Xqee`.)*
  *(2026-11-23: `UG41I` cannot give the number without it (above); eight names, the number from
  the page's own request, the operator's decision of that day.)*

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
    `accounts.google.com`, the device-bound session refresh) follow the rule below like any other:
    blocked until S8 records each one's exact host and path; then allowed by that host and path
    and counted, since blocking them could end the session (Observed facts, DBSC). S9 checks the
    session survives a full read with them. *(2026-11-19, «S8, last pieces»: the only one the pages
    request is `accounts.google.com/RotateCookiesPage`, a frame; it stays blocked until S9 measures
    whether the read by calls lets it through, and what it requests then.)* *(2026-11-20, S9: kept
    blocked through a 7-minute read by calls of two classes, twice; the session survived each, so it
    stays blocked. A longer read is not measured.)*
  - **everything else** a page asks for (telemetry, push channels) is blocked and counted, unless S8
    shows the page cannot load without it, in which case it is allowed by exact host and path and
    recorded here; *(2026-11-19: Classroom's own `ClassroomUi/browserinfo` POST, never blocked in S8,
    is S9's to test.)* *(2026-11-20, S9: aborted 3 times a run; the home page still listed its
    classes and every call answered, so the page does not need it and it is blocked.)*
  - **downloads**: no browser download; the read fetches only the attachments it listed in this run,
    through the session's request context (R8), and the adapter refuses any other id.
- **Test** (SC-004): offline, in CI, a real headless browser opens a local fake Classroom that serves
  synthetic pages with a planted «Entregar» press, a planted form link and a planted write call
  name, and a planted press fired by the page's own script; all are blocked and counted and none
  reaches the fake server. The JavaScript init script also has `node --test` cases with `jsdom`,
  like the extractor's (spec 001 R11).

### R5. The sign-in window: the plain installed Chrome, and how alfabeta knows it is done (FR-010)

- **Decision**: `classroom sign-in` starts the installed Google Chrome as a separate process —
  `--user-data-dir=<read profile>` and Google's sign-in page whose continue address is Classroom —
  with no Playwright, no extension and no script of alfabeta's. The address carries no account
  hint (no `login_hint`, no email address), so neither the URL nor the process's arguments hold the
  student's address (constitution III); S7 found the sign-in needs no hint, not
  even the school's domain. To know the family has signed in without reading anything but the address,
  alfabeta starts that Chrome with `--remote-debugging-pipe` and, every few seconds, sends one
  browser-level `Target.getTargets` over the pipe (file descriptors 3 and 4, which only the process
  that started Chrome holds; written with the standard library). The answer lists each tab's
  address, title and other fields; the adapter keeps only each tab's `url` field and discards the
  rest unread, so a title that names the account is never kept. It never attaches to a tab, never
  sends `Runtime` or any page command, opens no network port and reads no file of the profile, and
  compares each address with Classroom's in memory without logging or storing it. When an address reaches `classroom.google.com`, alfabeta
  waits 40 seconds, then closes the browser with the browser-level `Browser.close` over the same
  pipe; if it has not exited 20 seconds later, a SIGTERM, and a SIGKILL 10 seconds after that. A
  SIGTERM 5 seconds after Classroom left none of the session's cookies on disk; the wait and the
  orderly close together kept them (S7 result below). The family may also close it;
  `schedule.wait_minutes` ends it otherwise.
- **Measured (spike S7, passed)**: Google accepted the hand sign-in in a Chrome started with that
  flag (the peer's reason for no automation is that Google refuses sign-ins it sees as automated;
  the flag sets no `navigator.webdriver`, but this is not measured), and `Target.getTargets`
  showed the address change.
- **Fallback, had S7 refused it**: the window starts with no flag, and alfabeta watches only the
  process: the wait ends when the family closes the window or at `wait_minutes`. That is the spec's
  first wording, which the independent review rejected because the session could die while the
  read waits; the notice would then ask the family to close the window, and FR-010 would be amended
  before building.
- **Alternatives rejected**: `--remote-debugging-port` with `GET /json/list` — the same list, but
  it opens a DevTools port on the loopback, which any local process can reach, on the profile that
  holds the minor's session, for the whole wait, and its port is read from a file in the profile;
  AppleScript to Chrome for the active tab's address — with the family's
  everyday Chrome running, "Google Chrome" names two processes and the script can read the wrong
  one, and it needs an Automation permission for the whole application; reading the profile's
  files (history, cookies) — reads more than the address, which FR-010 forbids.
- **Bringing the window to the front** (FR-013, FR-017): by the process id alfabeta started, through
  the macOS seam: `NSRunningApplication` activation through `osascript -l JavaScript`, which sends
  no Apple event and so needs no Automation permission. S7 saw no prompt when run from a shell of
  the Claude app; whether it raises a window that is behind others, and whether it works from
  launchd, are not measured (S10).

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
  by the extractor name the same items. S9 checks it on every class. *(2026-11-20, S9: the same ids on the two
  classes read; types by the record's slot in `dpT4Vd`'s answer, 1 assignment, 3 question,
  5 material; posting days at record path `[0, 9, 2]` and due instants at `[1, 0]`, as epoch
  milliseconds.)*
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
- **Attachment names** (2026-11-20, family decision, #283): the read writes the name the call gives,
  as it comes; it adds nothing of its own. An empty name stays empty (spec 001's placement then
  names the file by its id), and two files with one name in one folder get spec 001's own
  numbering (FR-015c). The replica's identity stays its ids (spec 001: unique per source, item and
  attachment), so a name that differs from the extractor's makes no new replica; but spec 001's
  plan reads a changed name as a rename, so each attachment whose name differs between the two
  routes (13 of 52 in S9) is downloaded again and moved once each time the route changes.
  SC-005's comparison of attachments is by id.
- **The teacher's «missing» mark** (2026-11-20, family decision, #283): the read detects it, and
  the item's status follows spec 001's rule — `missing_per_teacher` overrides the bucket. When the
  mark appears (absent from the class's last capture, present in this one) the read raises an
  event so the family hears of it: once, on that change, not on every read. The channel and its
  contents (the item's opaque id only, constitution III) are to be specified as a requirement
  before the build, since no notice kind or result field carries it; the field that holds the mark
  is S9's second measurement. *(2026-11-23: the family chose the channel, an email to the family
  (#283) — R9's `Mailer`, a third notice kind. The contents are the spec's, FR-033: an opaque id
  would not let the family find the item, so each item goes as its subject folder and a link to
  its Classroom page built from ids, which constitution III allows; «once» is kept by a record of
  sent marks rather than by comparing captures, so a failed send is retried.)* *(2026-11-23, S9's
  second and third measurements: field `[32]` of an item's entry in `Zj93ge`'s answer is 3 on every
  item the capture shows with the teacher's notice, and on no other item of the 12 classes — graded
  items without the notice included, so it is not the graded bucket. The item record holds nothing
  that differs. The read reads the mark from there.)*
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
  bytes equal those of the last replicas. *(2026-11-20, S9: not measured; no attachment was
  fetched.)*

### R9. Notices by email from the `family` account (FR-013, FR-014, FR-033)

- **Decision**: one `Mailer` port; its adapter sends through the Gmail API `users.messages.send`
  with spec 004's `HttpTransport` and the token of the account linked with role `family` and scope
  `gmail.send` only (spec 004 FR-004, FR-005 as amended), from that account to itself. Texts in
  Spanish, naming the student by its id and nothing from Classroom (FR-014); a test over every
  template (SC-006). *(2026-11-23: FR-033's notice also carries Classroom links built from ids
  and alfabeta's subject folders; still no name, address or title.)*
- **Depends on**: spec 004's role `family` and the Gmail scope, which no code links yet; that is
  its own task in spec 004 before slice 5. *(2026-11-23: the teacher's «missing» mark is sent the
  same way by the read by calls, wherever it runs, the container included (FR-033), so the read
  by calls needs this link too.)*
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
  started outside the configured hours (more than `wait_minutes` after its time, at least 10
  minutes since launchd starts a few seconds late; a window past midnight belongs to the day it
  started) logs the miss and ends (FR-015 «not made up»). A refresh started by hand reads no
  `[schedule]`.
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
| Shares | spec 001's share step (FR-011a) | the Drive API, through alfabeta's own connection | a fake transport |

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

Each live spike loads Classroom only behind the minimal guard of spec 001 R18 — the document-load
allowlist and zero presses, installed in the browser before any page script — whether a person is
at the Mac or not (S10 runs with nobody present, which constitution IV requires be read-only by
construction). Each runs read-only, with code kept outside `main` (a `spike/166-…` branch, as S4 was), and
records its result in this file with its date. Pass criteria are written so the gate is objective.
**Who** says what each needs: *agent* — Claude alone; *family sign-in* — someone signs the school
account in by hand at the Mac (or through the remote view); *family phone* — the family's own phone
with their Google account. No spike needs the student's phone: the remote view and the notices are
the family's.

| Spike | Who | Pass | If it fails |
|---|---|---|---|
| **S7 · The sign-in window and the profile.** Start the installed Chrome with a fresh profile in the data folder and `--remote-debugging-pipe`; the family signs in by hand; `Target.getTargets` shows the address reach Classroom; alfabeta closes it; Playwright (`channel="chrome"`, keychain flags removed) opens the profile headless and loads one Classroom page with the session; the window can be brought to the front by process id | agent + family sign-in | Google accepts the sign-in with the same steps the R20 probe of 2026-11-01 showed, and no «this browser may not be secure» page; the address change is seen; the headless open reads the session with no keychain dialog | Sign-in refused with the flag: R5's fallback (watch the process only) and FR-010 amended. Session not readable headless: the read is not built |
| **S8 · The calls of every page** (widens spec 001's S6). Behind the minimal guard (document-load allowlist, zero presses), load once each page kind of R3 for two classes, headless, and record per request: method, host, path, call names, response tag — never bodies or cookies | agent + family sign-in | Every capture field comes from a name whose responses are queries, or from the name R3 admits by name; besides those, only tagged names R3 admits because the page needs them are let through; the pages load with everything outside those names and the session upkeep blocked; the stream's announcements are found | A needed field only behind a non-query name: FR-004 not met, the read is not built, this plan says so. *(2026-11-19: S8 failed this way on `t51ITc` alone; the family admitted it by name in R3, #270. Its second half passed the same day with ten names, research «S8, second half»; its last pieces: «S8, last pieces»)* |
| **S9 · A whole read by calls, compared.** Same day, same classes: the current extractor (the family's usual run) and a throwaway read by S8's names from S7's profile, headless, timed; then fetch every listed attachment through the request context (R8) | agent + family sign-in | All classes read in under 30 minutes of the sign-in with no challenge; the same item ids (base64 of decimals), types, topics, attachments and stream posts; the status table of R7 filled with no contradiction; attachment bytes equal the replicas; and, inherited from S8 (2026-11-19, R4's notes): whether the session survives a whole read with `accounts.google.com/RotateCookiesPage` blocked or needs it let through, and whether the page needs `ClassroomUi/browserinfo` | A challenge: stop (constitution IV), record it, the read is not built. Differences: recorded per field; a field that cannot be matched is a spec question before building *(2026-11-20: no challenge; on two classes the ids, types, topics, posts, posting days and due instants match and four status rows are confirmed; attachments, the graded status, the bytes and the whole read stay open; research «S9»)* |
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
*(Since the amendment of 2026-11-17 a read with nobody signing in is in this spec, by the scripted
sign-in of FR-027; keeping the session alive between reads still is not.)*

## Spike results

### S7 · The sign-in window and the profile — passed

Measured 2026-11-03 against the school account on the operator's Mac, with the family signing in by
hand twice in the same profile, with the installed Google Chrome and Playwright 1.64.1. The code is
`spikes/s7_signin.py` on branch `spike/166-s7-signin`. The first sign-in ran an earlier, uncommitted
revision (a 5-second wait, then SIGTERM); the second ran the committed one. The log kept instants,
categories, and the host and path of the headless read's navigations; never a query, a title, a
body or a cookie.

| Pass criterion | Seen |
|---|---|
| Google accepts the sign-in in a Chrome started with `--remote-debugging-pipe`, no «this browser may not be secure» page | Accepted both times, with no account hint in the address; no tab reached Google's rejection page, and the family noticed no such warning |
| The address change is seen | `Target.getTargets`, asked every 3 seconds, showed the tab go from `accounts.google.com` to `classroom.google.com`: 4 min 3 s after the window opened in the first sign-in, 3 min 48 s in the second |
| The headless open reads the session with no keychain dialog | Met after the second sign-in only (see below). Playwright (`channel="chrome"`, headless, `--use-mock-keychain` and `--password-store=basic` removed, checked absent from the process arguments) read 21 cookies for Classroom's and Google's sign-in addresses, the session's included, and landed on the Classroom home page; the whole read, a fixed 5-second pause included, took 6 seconds. The family noticed no macOS dialog, during the sign-in or the read. The session's rows were still on disk after the read |

The window was also brought to the front by its process id, a step of S7 though not one of its
pass criteria: `NSRunningApplication` activation answered `true`, the family believes the window
came to the front, and noticed no prompt. It was called 3 seconds after launch, when a new window
is usually in front already, so whether it raises a window that is behind others is not measured.

What it changed or left open:

- **The window is closed in order, after a wait.** The first sign-in was ended by a SIGTERM
  5 seconds after Classroom; Chrome exited with code 0. Both headless reads after it landed on
  Google's sign-in page; the second found 4 cookies for Classroom's and Google's sign-in addresses,
  none of the session's (no `SID`, `__Secure-1PSID` or `SSID`). A one-off count of the
  profile's Google cookie rows after those reads (names and creation times only) found 4 rows, all
  created in the first 65 seconds of that sign-in. The second sign-in, closed with `Browser.close` 40
  seconds after Classroom, left 22 rows with the session's cookies. R5 now does both. Which of the
  two is enough on its own was not measured; that Chrome writes its cookies periodically is the
  likely reason, not a measurement. The second sign-in was also not in a fresh profile.
- **Chrome's own sign-in offers.** On reaching Classroom, Chrome offered to sign in to the browser
  and to switch to, or open without, a profile (an extra internal page beside Classroom in the tab
  list). The family declined them. Whether a launch switch can suppress them, or the notice must
  tell the family to decline them, is open for the plan before slice 2.
- **Passwords.** The profile offered no saved username or password; the family typed both. Whether
  Chrome offers to save the password, and how that is refused (a launch switch or policy, or the
  notice), is not measured.
- **The minimal guard blocked two frame loads**, one on `accounts.google.com` and one on
  `ogs.google.com` (Google's bar); the main frame stayed on Classroom. Their exact paths are S8's
  (R4, session upkeep).
- **Questions for the plan, not measured**: the 40-second wait sits beside spec.md's «the read
  closes it and starts at once»; and on macOS closing the last window leaves Chrome running, so a
  family that closes the window is seen only when the pipe closes or at `wait_minutes`.
- Not measured here: whether the peer's claim holds that Playwright's keychain flags break the read
  (S7 ran only with them removed).

### S14 · The scripted sign-in and the read in a container — passed at home, stopped in the cloud

Measured 2026-11-16/17 on the school account (password only, no second factor) with Playwright
1.64.1 and the installed Google Chrome, headless, a fresh profile, Playwright's own flags kept
(`navigator.webdriver` true) but the two keychain flags removed as in S7. Code on branch
`spike/166-s14-scripted-signin` (`spikes/s14_*`), kept off `main`. The real sign-ins were launched
by the operator, except two reads of 2026-11-17 that Claude launched on the operator's standing
permission to run tests: the 12-class read and the 2-class re-read below. Each signed in by script
in a fresh profile, which breaches spec 001 research R15's first limit («Claude never runs a
sign-in»); it was stopped there and is not repeated (FR-027). The log kept
instants, categories and Google's sign-in paths; never the account, the password, a title or a
cookie. Results also in julioarguello/alfabeta#166.

| Where | Result |
|---|---|
| Mac, home address, Chrome on the host | Identifier → password → Classroom in 5 s; no rejection, challenge or second factor; reopened headless: session alive, class list present |
| Google Cloud Run job, `europe-southwest1`, same script and Chrome (linux/amd64 image), account and password from Secret Manager | Stopped twice: after the account, the identifier page came back with an image captcha («Escribe el texto que escuches o veas»); the password page never showed |
| Mac, home address, the same image in Docker (amd64 under emulation), launched by the operator | Identifier → password → Classroom in 6 s; session alive |
| Mac, Docker, the whole read with alfabeta's extractor (`classroom-sync`'s calls, unchanged), launched by Claude | 12 of 12 classes `complete` in 14 min 20 s (13–164 s each); 0 presses on Classroom pages; the guard blocked 128 `drive.google.com` and 5 `ogs.google.com` frame loads; `download collect` took all 12 |
| Same read compared with the Chrome read of the day before (2026-11-16) | Same item identifiers, posts and attachment counts in all 12 classes (statuses not compared), but every due time 1–2 h early: the container ran in UTC and Classroom writes dates in the browser's zone |
| After setting the browser zone to `Europe/Madrid`, 2 classes (34 items), launched by Claude | Identical to the Chrome read of the day before (titles, types, attachment counts, due and posting texts), times included |

What it settles and leaves open:

- **The captcha met twice from Cloud Run `europe-southwest1`**, while the same image signed in from
  home: not Linux, the container, the emulation or the automation flag. The address is the likely
  cause, but it is not isolated from Cloud Run's own environment (its sandbox, native amd64).
  Getting past the captcha is evasion (constitution IV), so the read stays where Google accepts it
  (FR-028).
- **The spike's guard departs from the rule of these spikes** (document allowlist, zero presses):
  it allowed document loads by host, pressed Enter twice on Google's sign-in pages, and counted
  presses on Classroom pages only. FR-027 and FR-030 set the build's guard.
- **Zone and locale are requirements** (FR-029), not defaults: UTC silently shifts every date.
- **The account index differs**: in the container's fresh profile the school account is `/u/0`;
  in the family's Chrome it is another number. Attachment addresses carry it, so the design fetches
  attachments inside the container's session (FR-028), not by the family's Chrome — a design
  choice, not measured.
- **Captures from the first, UTC-shifted read** were moved to the data folder's quarantine, so the
  plan does not take them as the newest of each class.
- **Not measured**: the sign-in from the launchd agent with the screen locked (S10's question for
  this route); signing in again into a mounted, used profile whose session expired (the daily case:
  every S14 run used a fresh profile); fetching attachments inside the container; the read behind
  the build's guard (FR-030: S14's guard let every request that was not a document through); how many daily
  scripted sign-ins Google tolerates before a check; and the session's life inside the container
  beyond the read (S13).
- **The cloud copy of the password** (account and password in Secret Manager of the alfabeta
  project, with the job, its image and its service account) was deleted on 2026-11-17 with the
  operator's yes, as S4's token was.

### S15 · Reading only the classes with news — not feasible

Asked in julioarguello/alfabeta#263: can `classroom refresh` skip the classes that did not change
since the last read, with a periodic full read, so a run reads fewer pages at the same pace
(constitution IV's «no bursts» rules out reading classes in parallel)? Measured 2026-11-19, read-only, by Claude on the
operator's standing permission to run tests, inside spec 001 research R15's limits: the probe never
calls the sign-in and is given no password. Nothing printed or kept names a student, a teacher, an account or a class
title.

**The pass rule, fixed before the numbers.** A change signal is reliable only if, whenever it says
«unchanged», every field that `classroom plan`, `classroom apply` and the agenda take from the class
is unchanged too: the items and topics, each item's attachments (they are what the read copies to
Drive), its due date, posting and modification dates, and the student's status, grade, return and
teacher comment. One miss on any of those fails it; so does a signal that flags most classes on most
days (nothing saved).

**What a skipped class costs downstream (code, read).** Nothing breaks: the run's scope is the
lease's class list, which `download collect` fills from this run's captures, so a class with no
capture in the run is neither planned nor applied and none of its items is withdrawn, its earlier captures are kept
(`plan.prune_captures` keeps them by class), and the agenda keeps the class's items from the state
and the instant of its newest earlier capture. Two things go stale with it: the plan's
periodic attachment review (`[sync] full_review_days`) covers only the classes in scope yet the run
is logged `full_review: true`, so a skipped class would miss it; and the agenda's past-exam test
(`agenda.later_than`) compares with the class's newest capture instant, which stays old (an exam is
shown as coming for longer — the safe side).

**The cheapest page that could carry a signal (data/captures, offline).** The two pages per class
that the extractor already reads besides the item details — «Trabajo de clase» (each item's id,
title, topic, type and its listing date text) and the stream (each post's id, date text, text and
attachments) — were taken as a fingerprint and compared with what the full capture holds. Over the
12 classes' captures kept in the data folder from 2026-10-28 to 2026-11-18, as they stood that morning
before its read (each apply trims the folder to the newest `[sync] kept_captures` per class, so a
later re-run counts fewer old pairs) (106 class captures; 83 consecutive pairs of the same
class, 11 pairs with an incomplete capture left out), normalised with `capture.normalize_class`:

| Consecutive pairs | Count |
|---|---|
| Fingerprint changed (the class would have been read) | 35 |
| Fingerprint unchanged and nothing consumed changed (a correct skip) | 43 |
| **Fingerprint unchanged but a consumed field changed (a wrong skip)** | **5** |

The fingerprint would have skipped 48 of the 83 pairs; 5 of those 48 skips were wrong.

The five wrong skips, each traced through every kept capture of its item, by what changed
on the item's detail page only:

| Wrong skip | What it was |
|---|---|
| 1 pair | **A read miss repaired, not a change**: one capture of 2026-11-10, marked `complete`, held two items with no attachments (they have them in every capture before and after) and a garbled status text; the next read brought them back |
| 1 pair | An attachment renamed by the teacher (same Drive id, new name, kept since) |
| 1 pair | Attachments replaced by files of the same names (one Drive id out, another in, kept since): to the plan a new attachment to copy |
| 2 pairs | The student's side: status to «Calificado» with a grade, once with the submission's file |

So four real changes that alfabeta acts on — two to the files it copies, two to the student's
status and grade — sat behind an unchanged fingerprint: 4 of 48 skips (1 in 12), and none moved the
item's listing date text. Both captures of each pair are `complete` and of the same extractor
version. The listing and the stream cannot be finer than the item's detail page, where these four
changes live.

**The home page `/u/0/h` (live, one page load).** Measured 2026-11-19 at 09:40, right after the
family's `classroom refresh` of that morning (its own sign-in, 12 of 12 classes), by a diagnostic run of the
read image (Playwright 1.64.1, Google Chrome, linux/amd64) that never calls the sign-in and is given no password: the read profile mounted, `/app/read.py`'s `Guard`
installed as the read installs it, one load of the home page, the account check, then a count of each
class card's elements, attribute names, `aria-label`s and text pieces — never their text.

| Question | Answer |
|---|---|
| Session alive, expected account | yes, yes |
| Class cards | 12, each with 88 elements and the same attribute names, but for the one card below whose preview item adds `data-stream-item-id` |
| A «new» or «unread» badge, a count, an activity or last-update text or attribute on a card | no (0 of 12) |
| A `data-` attribute named for a change, a time or a count | no: 23 `data-` names, the same on every card — the class and user ids and widget wiring (`data-focus-id`, `data-tooltip-id`, `data-menu-uid`…); values not read |
| A date on a card | only on 1 of 12: the card's «upcoming work» preview, one link to an assignment due soon |
| Card links | the class stream, the student's own work page, the class's Drive folder, and that one assignment |
| Guard | 2 frame loads blocked, no redirect, no press |

The upcoming-work preview names assignments with a due date in the coming days, so it moves only
when such an assignment appears or falls due: it says nothing of a material, an announcement, an
attachment added to an existing item, or a grade. Between the night read of 2026-11-18 and that
morning's read no class changed (the two newest captures of each class are equal), so the cards
could not be watched turning over: the snapshot is of a no-news state, in which a marker drawn only
when there is news would be absent too.

**Verdict: not feasible.** No page the read may load was seen to say that a class changed in the
fields alfabeta copies: the listing and the stream, as the extractor reads them, hid a real change in
1 in 12 of their skips, two of them to attachments, which are what the read is for; the home page's cards
showed no change marker in a no-news state, and the only dated thing on them, the upcoming-work
preview, cannot see an attachment or a grade. A periodic full read would bound how late such a
change arrives, not prevent it. The read keeps reading every class. A faster read stays where the
spec put it: the read by Classroom's own calls (FR-003, FR-004, R1), still planned and unmeasured
(S8, S9).

What it leaves open:

- **Not measured**: the home page's cards at a moment when a class has news (a new material, an
  attachment added, a grade). A marker that shows only then would not have been seen; it would
  still have to cover detail-only changes to pass the rule above.
- **A `complete` capture can miss attachments** (the 2026-11-10 read above, before the container
  read): a full read every run repairs it on the next run, a skip would not. It is a question for
  the extractor's readiness test, not for this entry.
- **The probes** are on branch `spike/263-incremental-read` (`spikes/s15_*`), kept off `main`: the
  offline comparison over `data/captures` and the home-page probe run in the read image with
  `--entrypoint python`, which imports `/app/read.py` and installs its `Guard`.

### S8 · The calls of every page — fails: the attachments only behind a call without a tag

Asked in julioarguello/alfabeta#267, the first step of the read by Classroom's own calls (FR-003,
FR-004, R1, R3). These are the private calls Classroom's web page makes from the student's
signed-in page, not Google's Classroom API: no school grant, no OAuth scope. Measured 2026-11-19,
read-only, by Claude on the operator's standing permission to run tests, inside spec 001 research
R15's limits (the probes never call the sign-in and are given no password). Live loads, in order:

| When | Session | What loaded |
|---|---|---|
| about 12:40 | the family's refresh of 12:34, which then failed for lack of memory in Docker (#268) | home, the account check and one «Trabajo de clase»; then the container's Chrome crashed. Nothing kept |
| 14:09 | the family's refresh of 13:53 (12 of 12 classes, `ok`) | the run below: home and 9 pages of two classes |
| 14:18 | same | an uncommitted revision of the shape probe: home and two item details; printed the shapes of `Zj93ge`'s and `t51ITc`'s first answers (`t51ITc`'s were empty) |
| 14:19 | same | the committed shape probe: home and two item details, 2.5 s apart, each kept 4 s |

Every run used the read's own `Guard` as the read installs it (zero presses, documents only on
FR-030's pages); in the runs whose guard counts were printed (14:09, 14:19) none was breached and
the guard blocked only frame loads.

**How (14:09).** The read image (Playwright 1.64.1, Google Chrome, linux/amd64), one load of the home
page, the account check, then for the two classes with the most kinds of item: «Trabajo de clase»,
the stream, and one assignment's, one material's and (where the class has one) one question's
detail — 9 pages, loaded in a hidden frame as the extractor loads them, 2–3 s apart, each kept 8 s
after it was ready so late calls are seen. Recorded per request: method, host, path with ids, dots
and `@` masked, `batchexecute` call names (`rpcids`) and, per call name, the short lower-case dotted
strings in its answers (protocol tags). In memory only, each call's answers were searched, by whole
string, for the ids and texts the newest capture of those classes holds (class, topic, item, post
and attachment ids; item titles, descriptions, attachment names, post texts), printing counts. The
shape probe printed, for the call without tags, its answer's structure with every string replaced by
its length unless it was a short lower-case dotted string. A file name or a domain could have that
form; none did: the only such strings printed were protocol tags (`hrq.*`, `hrsi.*`, `hrcw.qr`,
`hrt.qr`, `hra.laa`, `hrgb.lr`, `rubric.list`, `edu.rt`). Nothing printed or kept holds a body, a
cookie, a name or a title.

| Question | Answer (14:09) |
|---|---|
| `batchexecute` requests | 244, every one with a single name; the names in the body equal `rpcids` in all 244 |
| Data in the pages' own HTML | none of the capture's decoded ids found in it (ids searched, not texts): each page's HTML has 3 `AF_initDataCallback` and an `AF_dataServiceRequests` in which the probe's pattern found no call name |
| Call names seen | 13, all sent while the pages loaded or sat open, with zero presses (on load and during the 8 s are not told apart, nor the frame from the home page under it) |
| Names with a protocol tag in their answers | 12, every answer of each carrying one (the probe counted untagged answers: only `t51ITc`'s); in `Zj93ge`'s answer printed at 14:18 the tag comes first |
| Names without a tag | 1, `t51ITc`: 23 answers, none with a tag; some empty, the others start with `null` where a tagged answer has its tag, then a list of materials keyed by item id |

| Call | Tags | Pages | Carries, by whole-string match against the capture |
|---|---|---|---|
| `dpT4Vd` | `hrcw.qr`, `edu.rt` | classwork | items 49 of 49, titles 47 of 49, descriptions 22 of 27, topics 11 of 11, attachment names 1 |
| `pONvgf` | `hrsi.qr`, `edu.rt` | home, classwork, stream | items 34, titles 33, descriptions 14, topics 10, posts 4 of 4 with their texts, attachment names 1 |
| `tQShAc` | `hrsi.lr`, `edu.rt` | item details | items 5, titles 5, topics 3, descriptions 1 |
| `ZZFlc` | `hrt.qr` | classwork, stream | topics 11 of 11, titles 2 |
| `Zj93ge` | `hrq.sub` | classwork, assignment, question | items 36 |
| `cCzVwf` | `hra.laa` | item details, stream | items 5, posts 4 |
| `Bypadc` | `rubric.list` | assignment | items 2 |
| `gkSD8b` | `hrgb.lr` | classwork | the class |
| `gXtzob`, `O1Xqee` | `hrq.crs`, `hrq.cus` | every page | the class |
| `UG41I` | `hrq.usr` | every page | nothing of the capture |
| `sLc6hf` | `hrq.cmt`, `edu.rt` | every page but home | one item (97 requests) |
| **`t51ITc`** | **none** | every page | **attachment ids 2, attachment names 2** — the only name whose answers hold attachment ids; by the shape, each material also has a type and an address (inferred from lengths) |

Of the 51 attachment ids the two classes' captures hold, the 5 items opened had 2 between them and
the 4 posts none; both were found, in `t51ITc`. Dates, statuses and grades were not mapped (numbers and codes, not
texts the capture holds). Besides these calls, the pages asked for telemetry (`play.google.com/log`),
a push channel (`signaler-pa.clients6.google.com`), the Google bar (`ogads-pa`, `ogs.google.com`),
2 other Classroom POSTs (at 14:19, one was `ClassroomUi/browserinfo`), scripts, fonts and images; the
guard blocked 27 frame loads (by the request list: 7 of Drive's viewer, 10 of the Google bar's
widget, 10 of Google's sign-in host).

**Against the pass rule** (spike table: every capture field comes from a name whose answers are
queries): the teacher's attachment ids come only from `t51ITc`, whose answers carry no tag. R3 admits a
name only if its answers carry a query, list or get tag, so the spike fails by its own rule: FR-004
not met, the read by calls not built. The other fields seen came from tagged names (reading `.lr`,
`.laa` and `rubric.list` as list or get tags is this entry's reading); dates, statuses and grades
were not mapped.

What it leaves open:

- **Whether R3 should admit `t51ITc`.** What was seen of it is consistent with a read: the pages send
  it while they load, with zero presses, alongside the tagged queries, and its answer is the item's
  materials, not an acknowledgement. But R3 chose the tag because no spike may send a write to tell
  one from the other (constitution IV), and a name without a tag is what R3 says to block. Admitting
  it changes R3 and S8's pass row; whether FR-004 is then met is the family's reading, not this
  entry's.
- **The peer project's catalogue** (Observed facts) lists `t51ITc` among names that are «all reads by
  their response tags»; on this account its answers carry none. R1's «Only what changed» rests on
  that call.
- **Not measured**: S8's second half (the pages loaded with every name outside the allowlist, the
  telemetry and the push channel blocked); the exact host and path of the session upkeep R4 asks for
  (Google's sign-in host was requested 10 times as frames and blocked, paths masked); the to-do pages (outside the
  container guard's pages); and S9's whole read.
- **The probes** are on branch `spike/267-s8-calls` (`spikes/s8_*`), kept off `main`.
- **Decided after (2026-11-19, #270)**: the family admitted `t51ITc` by name in R3. This verdict stays
  as measured; before anything is built, S8's second half, the to-do pages, the session upkeep's exact host and path (R4) and the mapping of dates, statuses and grades, then S9.

### S8, second half · The pages with only the allowlist let through — passes with ten names

Asked in julioarguello/alfabeta#267 and R3 as amended (#270): do the pages still give the read what
it needs when every call outside an allowlist, the telemetry, the push channel and the Google bar
are blocked? Measured 2026-11-19, read-only, by Claude on the operator's standing permission to run
tests, inside spec 001 research R15's limits (no sign-in, no password), in the session of the
family's `classroom refresh` that ended at 16:42 (12 of 12 classes, `ok`).

**How.** The container read itself (`read.py` and the extractor, unchanged) for two classes, with
one addition to its guard's routing, run before it: a `batchexecute` request naming any call
outside the allowlist was aborted, and so was every request to `play.google.com`,
`signaler-pa.clients6.google.com` and `ogads-pa.clients6.google.com`; each abort counted by call
name or host. The captures were compared with the same classes' captures of that refresh, minutes
before.

| Run | Allowlist | Result |
|---|---|---|
| 16:43 | the 9 names S8 saw carrying the capture's fields or the course (`dpT4Vd`, `pONvgf`, `tQShAc`, `ZZFlc`, `Zj93ge`, `cCzVwf`, `t51ITc`, `gXtzob`, `O1Xqee`) | the home page listed no class (`unexpected_ui` after the read's own retries); the page had asked 18 times for `UG41I`, blocked |
| 16:44–16:48 | the same and `UG41I` (`hrq.usr`, tagged in every answer) | both classes complete (25 and 9 items, 23 and 13 attachments): the same items, fields and stream as the refresh, but one attachment |

The one attachment that differed was read as a Google document, as in all 9 earlier captures of
that item since 2026-10-28; the refresh minutes before had read it as a Drive file under a shorter
name. The odd read was the refresh's, not this one's.

Blocked in the second run (280 s): `sLc6hf` 376 times (comments; the page asks again and again),
`Bypadc` 71 (the rubric), `gkSD8b` 4, and the three hosts 371, 125 and 39 times; 79 frame loads by
the guard itself. An aborted request stops in the browser and never reaches the server, so the
page's retries are no burst at Classroom (constitution IV).

**Verdict: passes, for the fields these classes hold.** With ten names let through — the nine above
and `UG41I`, which the home page needs to list the classes — and the telemetry, the push channel
and the Google bar blocked, the read got the same items, topics, stream, attachments, statuses,
points, submissions, due and posting texts and descriptions as the full page gave the refresh.
Teacher comments, grades and returned marks were empty in both reads (no class held any), so they
were not tested: if they live in a blocked call (`sLc6hf`, `gkSD8b`, `Bypadc`), mapping them adds a
name. Only `batchexecute` calls and the three hosts were blocked; other requests, among them
Classroom's own non-`batchexecute` POSTs (`ClassroomUi/browserinfo`), went through uncounted. These
ten names are the allowlist S8 records (R3; `t51ITc` by its exception, `UG41I` because the page
needs it).

**Dates (16:50, same session).** For S8's first-half classes (one of them also read in the run
above), the capture's due instants (17, as epoch seconds from `capture.normalize_class`) and posting
days (34) were written by the host to a file the probe read; the probe loaded «Trabajo de clase» and the stream of each and counted, per call,
the due instants found exactly as milliseconds and the posting days on which some epoch number in
its answers falls (Madrid). `dpT4Vd` (`hrcw.qr`) holds all 17 due instants and an epoch on 33 of
the 34 posting days; `pONvgf` (`hrsi.qr`) 14 and 26. No due instant appeared as seconds or as a
year-month-day run. The posting days are a loose match (any epoch of that day; it also fires on
calls that do not hold posting dates, e.g. `Zj93ge` 22); the due instants an exact one. The guard
blocked 12 frame loads, not breached. Statuses and grades are still unmapped: the capture holds them as texts and codes, and
`Zj93ge` (`hrq.sub`, the submissions by its tag) is the likely carrier, not shown; statuses arrive
under the ten names (above) and their table is S9's (R7).

What it leaves open:

- **The odd read of the refresh**: one attachment read as a Drive file with a shorter name, in 1 of
  10 captures. If it repeats, it belongs with #264's readiness work.
- **Still to measure before anything is built** (R3, FR-004's note): the to-do pages (outside the
  container guard's pages), the session upkeep's exact host and path (R4), Classroom's own
  non-`batchexecute` POSTs (R4: allowed by host and path, or blocked), and the mapping of comments,
  grades and returned marks to calls (due dates: above; posting days and the status table: S9's
  comparison, R7); then S9.
- **The probes** are on branch `spike/267-s8-calls` (`spikes/s8b_*`, `spikes/s8_dates.py` with
  `spikes/s8_dates_prepare.py` and `spikes/s8_dates_run.sh`), kept off `main`.

### S16 · A browser out of memory, and what tells it apart — measured (#268)

Recorded 2026-11-19. Not a spike planned before the build: the family's read of 12:34 failed and
julioarguello/alfabeta#268 asked why. Read-only throughout; the sign-in was never called by Claude.
Nothing printed or kept names a student, an account or a class.

| Fact | Read from |
|---|---|
| The 12:34 read signed in, listed 12 classes and failed each of them (`read: 0, failed: 12`, 312 s), logged and notified as `unexpected_ui` | its line in the student's `log.jsonl` |
| What failed was the page's renderer dying: `Page.evaluate: Target crashed` | a read-only diagnostic of the same session, recorded in #268 |
| Ten minutes after that read, with no read running, Docker's machine had 7835 MB and 1213 MB available | `free -m` in a short container of the image, 12:44 (the diagnostic session's record) |
| The load of one class then took the diagnostic's container from about 0.7 GB to about 1.2 GB, and the page died; #268 gives about 0.5 GB to about 1.26 GB, and about 0.2 GB left available in the machine | `docker stats` sampled during the load (the same record), and #268 |
| `--shm-size=1g`, one renderer, no site isolation and a JS heap cap did not avoid it | the same diagnostic (#268) |
| The 09:24 read of the same day read 12 of 12; #268 says it was the same image, with the other containers stopped | `log.jsonl` for the result; the image and the containers' state from #268 |
| A container with no limit of its own reads the machine's `/proc/meminfo`: its `MemTotal`, 8024028 kB, is `docker info`'s 8216604672 bytes to the byte | `docker run --rm --entrypoint cat <image> /proc/meminfo` and `docker info --format '{{.MemTotal}}'` on the Mac (Docker Engine 29.0.1 in Docker Desktop 4.53.0) |
| That reading takes 0.1 s with the image present, and an image that is not there answers no reading | `DockerReadContainer.memory`, timed on the Mac |
| `MemAvailable` moved from 5725 MB to 3294 MB within the hour, with eight other containers running | the same reading, twice |
| A dead page raises `Target crashed` from the call that was pending and from `evaluate` and `inner_text` after it, and `Page crashed` from `wait_for_timeout`; the page's `crash` event reaches the program with the first of those errors, not before | `chrome://crash` in Playwright 1.64.1's Chromium (macOS) and in the image's Chrome 157.0.8103.78 (`linux/amd64`), twice in the image |
| A load on the dead page raises `net::ERR_ABORTED; maybe frame was detached?` in Playwright's Chromium and `Page crashed` in the image's Chrome; `open_home` takes either for `unreachable` | the same two browsers |
| In the image's Chrome the `crash` event has arrived when a load right after the crash fails | `chrome://crash`, then a load, three times in the image |
| In Chromium on Linux it has not: a read whose page died before the home load ended `unreachable`, and after a sign-in `session_expired` | the two tests of this fix that failed in the first CI run of its pull request, julioarguello/alfabeta#274 (Ubuntu, Playwright's Chromium), and pass on macOS |

- **Decided**: two codes, each naming what was observed — `browser_crashed` for a page that died,
  `docker_low_memory` for a reading under the floor before the read starts (#268's text asked for
  one code for both; a check that has seen no browser cannot say one crashed). The crash is told
  by the page's event or by an error's first line. Where `read.py` ends with a stop it asks the
  page once more — one read of at most five seconds that a dead page cannot answer, so a late
  event does not matter — and applies the code there, so
  a step that swallowed the error (`unreachable`, `challenge`, `unexpected_ui`) does not name the
  stop — `session_expired` included, which is what `read.py` calls a home page that does not
  load after a sign-in; a sign-in code read from the page while it lived (`wrong_password`,
  `second_factor`, `rejected`, `other_sign_in`) is kept, since the host acts on it.
- **The floor is 1536 MB**: above the one failing reading (1213 MB, taken the way the read takes
  it: a short container, no read running), not a measured sufficiency. A reading that cannot be
  taken stops nothing. The log line of every read that asked keeps its reading, so the floor can
  be moved on evidence.
- **The three browsers differ**: in the error of a load on a dead page, and in whether the
  `crash` event has arrived by then. The tests run Playwright's Chromium; one of them silences the
  event, so the last read of the page is proven on every platform, not only where the event is late.
- **Not measured**: what a whole read needs at its peak (the failing one was cut short at about
  1.2 GB); whether a read that starts at the floor ends well; the memory at the family's own
  12:34 read, of which only the log line is known; a container killed with no `end`
  event (the kernel's own kill of the Python process), which still reads `unexpected_ui`.

### S8, last pieces · The session upkeep, Classroom's other POSTs, the calls' arguments — recorded

Asked in julioarguello/alfabeta#267: what S8's second half left before S9. Measured 2026-11-19 at
20:52–21:02, read-only, by Claude on the operator's standing permission to run tests, inside spec
001 research R15's limits (no sign-in, no password), in the session of the family's `classroom
refresh` that ended at 20:52 (`ok`). The read image with the read's own `Guard`; «Trabajo de
clase», the stream and one assignment's detail of one class, 2–3 s apart, through a hidden frame;
then Classroom's home page left open 10 minutes. Recorded: for each of the ten allowlisted names,
the shape of the first two `f.req` arguments it was sent with (the capture's class, item, topic and
post ids replaced by their kind, other digit runs by their length, short lower-case words kept as
enum-like — none appeared —, other strings by their length); every request the pages made to
Google's sign-in and cookie hosts (method, host, path without query, frame or page); every
Classroom POST that is not `batchexecute` (path words). Nothing printed holds a body, a cookie, a
name or an id.

| Question | Answer |
|---|---|
| Session upkeep, as the pages request it | one request kind: `GET accounts.google.com/RotateCookiesPage`, a frame document, once per page load (4), none in the 10 minutes with the home page open; the guard aborted it every time, as in every container read. Requests made by Chrome itself (outside the pages) are not seen by this probe |
| Session after the 10 minutes | the home page was still on Classroom (not reloaded) |
| Classroom's other POSTs | one kind: `ClassroomUi/browserinfo`, twice (once on a page load, once while the page sat open), let through |
| Arguments (first two per name) | `dpT4Vd` the class, and a topic; `ZZFlc` the class; `tQShAc` the item and the class; `Zj93ge` the item and the class, several at once, each with one more 12-digit id of another kind; `cCzVwf` the post and the class; `pONvgf`, `t51ITc` and `UG41I` (both shapes from the home page) ids that are not this class's and, for `pONvgf`, instants; `gXtzob` no id; `O1Xqee` the class or a list of ids. Each also carries a field-selection mask of numbers |
| Guard | 10 frame loads blocked, not breached |

Against R3, R4 and the open list of «S8, second half»:

- **To-do pages: not needed for the fields the two classes of S8's second half hold.** Every status
  those captures hold arrived through the ten names; the extractor reads only FR-030's pages.
  R3's list of pages is amended accordingly (dated note in R3).
- **Comments, grades and returned marks: not read yet.** The extractor does not read them today
  (`teacher_comment` and `returned_text` written empty; spec 001 T061 is open to read them), and the
  kept captures hold 14 «Calificado» items (seen 120 times) with no grade the extractor could read.
  So the read by calls has nothing to compare them against. They stay open until spec 001 T061 reads them; then they are mapped, possibly adding one of the names blocked in S8's second half
  (`sLc6hf`, `gkSD8b`, `Bypadc`).
- **Session upkeep (R4)**: the frame the pages load is recorded — `accounts.google.com`
  `/RotateCookiesPage` —, not what it would request once let through. Every container read so far
  kept it blocked in the read phase (the scripted sign-in's own phase lets the account host's frames
  through) and no read ended `session_expired` in the log. Whether the read by calls lets it
  through moves to S9 (dated note in R4).
- **Classroom's other POSTs (R4)**: `ClassroomUi/browserinfo` only, never blocked in S8; whether
  the page needs it moves to S9 (dated note in R4).
- **S9's input**: the arguments' shapes, with the gaps above (`pONvgf`, `t51ITc` and `UG41I` seen
  only from the home page).

**The probe** is on branch `spike/267-s8-calls` (`spikes/s8c_*`), kept off `main`. S8 has recorded
what it could; S9 inherits R4's two tests above, and comments, grades and returned marks stay open.

### S9 · A read by calls, compared — matches on two classes for ids, types, topics, posts and dates; attachments, one status, the bytes and five questions open

Asked in julioarguello/alfabeta#279: can a read made only of Classroom's own calls, sent from one
loaded home page, give spec 001's capture, and how does it compare with the extractor's capture of
the same session? Measured 2026-11-20, read-only, by Claude on the operator's standing permission to
run tests, inside spec 001 research R15's limits (no sign-in, no password), in the session of the
family's scheduled `classroom refresh` that ended at 16:30 (12 of 12 classes, `ok`, 884 s). An
earlier attempt, at 21:57 the day before, found the session of the 20:52 refresh already expired
and sent nothing.

**How.** Four throwaway probes, headless, in the container read image with the refresh's profile,
not S7's (R1, revised 2026-11-17), behind the read's own `Guard` and S8's routing
(every `batchexecute` naming a call outside R3's ten names aborted; `play.google.com`,
`signaler-pa`, `ogads-pa` and `ogs.google.com` aborted; `RotateCookiesPage` blocked as in every
read; `ClassroomUi/browserinfo` aborted on purpose):

1. 16:31 — the arguments' and answers' shapes for the class of the run with the most item types,
   its «Trabajo de clase», stream and one detail per type (this fills S8's gap: every name now seen
   from a class's own pages).
2. 16:34 and 16:49 — the request templates, learnt from the same pages' own requests: each call's
   arguments with the class, item, topic and post ids replaced by placeholders, and the request's
   envelope (each query and body parameter a `WIZ_global_data` key, the page path, the call name,
   the request id or a literal). Written to the student's data folder, 0600, deleted after.
3. 16:38 and 16:49 — the read by calls: one home page, then one call per request through `fetch` in
   the page, 1–2 s jittered apart (constitution IV); classes from `gXtzob`, topics from `ZZFlc`,
   items from `dpT4Vd` (once without a topic, then once per topic), posts from `pONvgf` (stream), and
   per item `tQShAc`, `t51ITc`, `cCzVwf` and, for assignments and questions, `Zj93ge`; per post
   `t51ITc` and `cCzVwf`. Per class also `gXtzob` twice and `pONvgf` three times (the pages' own
   variants); an item record found only in the stream got the item calls too. Ids came from the answers only, never from the capture. Two classes: the
   two of the run with the most item types and posts. Raw answers kept 0600 for step 4, then deleted.
4. Offline, on the host: each value the refresh's capture holds for those classes, looked for in the
   answers of the call that should carry it; dates through `capture.normalize_class`.

Both runs of step 3 gave the same counts; the figures below are the second's. Nothing printed held
a body, a cookie, a name, a title or an id.

| S9 row | Result |
|---|---|
| No challenge | none; every answer `200` with its row; the guard never breached |
| Calls | 225 for two classes, 402 s (1.79 s a call, 0.24 s of it the answer; the rest the pause): the home page's `gXtzob`, then class 1: 118 calls, 209 s; class 2: 106, 191 s |
| All classes in under 30 minutes | **extrapolated, not measured**: the run's 12 classes hold 122 items (81 assignments, 1 question, 40 materials), 28 topics and 11 posts, so about 583 calls (stream-only item records left out) ≈ 17 min at the same pace — under 30, though slower than the extractor's 884 s for the same run. Calls only: no sign-in in S9, the home page's load not counted |
| Item ids (base64 of decimals) | 25 = 25 and 24 = 24, none on one side only, items taken from `dpT4Vd` |
| Types | by the record's slot in `dpT4Vd`'s answer: 1 → assignment (35), 3 → question (1), 5 → material (13); no contradiction |
| Topics | 4 = 4 and 7 = 7 with the same ids and titles; the capture's one extra topic per class is the item-less bucket with no id |
| Stream posts | 2 = 2 and 2 = 2, same ids, texts found; no post held an attachment in either class |
| Titles, descriptions, topic of each item | all found in the item's own `dpT4Vd` record (titles 49 of 49, descriptions 27 of 27, topics 47 of 47); 2 titles and 5 descriptions only after collapsing runs of whitespace |
| Class title | the capture's is `gXtzob`'s name and section joined |
| Points | 36 of 36 |
| Posting days | an epoch-millisecond at record path `[0, 9, 2]` falls on the capture's posting day (Madrid) for 49 of 49 items |
| Due instants | exact milliseconds at record path `[1, 0]`, 19 of 19 items with a time |
| Status table (R7) | `Zj93ge` answered for all 36 assignments and questions; the small number at `[2, 0, 20]` of its answer tells the five statuses seen one to one (below) |
| Attachments, ids | 50 of 52 in `t51ITc`'s answer; one form and one link appear in no answer of their class |
| Attachments, names | 39 of 52 as they are; 1 video, 10 links and 2 files not found, not even inside another string |
| Attachment bytes through the request context (R8) | **not measured**: no attachment was fetched |
| `RotateCookiesPage` blocked | requested 2 times a run, blocked; the session survived the whole read (the home page loaded again on Classroom, account matching), and was still alive 27 minutes after the refresh ended. Not measured over a longer read |
| `ClassroomUi/browserinfo` | aborted 3 times a run; the page loaded, listed its classes and answered every call: not needed |

**The status table** (data-model.md, «Status from the call's bucket»), from 36 items, each status
seen at least once:

| `Zj93ge` `[2, 0, 20]` | Classroom's status text | `ItemStatus` from the capture today |
|---|---|---|
| 1 | Asignado | `pending` |
| 2 | Sin entregar | `overdue` |
| 3 | Entregado | `turned_in` |
| 4 | Entregado con retraso | `turned_in_late` |
| 5 | Calificado | `missing_per_teacher` (one item, with the capture's notice «El profesor ha indicado que falta esto») |

It is the peer's bucket order. The one graded item also carried the teacher's «missing» notice,
so today's normaliser reads it `missing_per_teacher`; the bucket says graded (`returned` in R7's
hypothesis). Which field of `Zj93ge` holds the teacher's mark is not located: one item is too few.
Excused was not seen.

**Verdict: matches on two classes for the fields above, not passed as a whole.** For the two
classes read, the calls gave the same item ids, types, topics and stream posts as the extractor;
titles, descriptions, points, posting days and due instants were all found; and four status rows
are confirmed in the peer's bucket order. Not passed: attachment ids (50 of 52) and names (39 of
52) do not all match; the graded row is not settled (the bucket says graded, the capture's
notice says `missing_per_teacher`); the attachments' bytes (R8) were not fetched; ten of the twelve
classes and the 30-minute bound are extrapolated; and the questions below are open. No challenge appeared, so nothing stops the read.

Open, before the build (each a spec question under the S9 row: «a field that cannot be matched is
a spec question before building»). *(2026-11-20: the operator decided all five the same day — spec
Clarifications 2026-11-20, #283; each bullet below ends with its decision.)*

- **The student's number.** `Zj93ge` (the submission) needs the student's own 12-digit number. It
  is not in `WIZ_global_data` nor in the answer of any call the read sends; only `UG41I`'s answer
  has it, and `O1Xqee`'s and `Zj93ge`'s own. The probe took it from the home page's own `O1Xqee`
  request, sent by the page as it loads, and so sent only eight names, never `UG41I` nor `O1Xqee`.
  R3 says nothing of `UG41I`'s answer is kept: taking the number from the page's request needs a
  decision (or R3 admits reading it). *Decided: the read sends `UG41I` once and keeps the number in
  memory for that run only (R3).* *(2026-11-23: `UG41I` answers with the number only when its
  request already carries it; since the operator's decision of that day the number comes from the
  page's own request, R3.)*
- **Attachment names.** 13 of 52 names, mostly links, are not in the answers as the capture writes
  them (1 video, 10 links, 2 files), and 2 ids (a form, a link) are in no answer: how the capture's name of a link or a file is
  made has to be settled before the read writes it. *Decided: the call's name, by R7's rule; the
  two missing ids are S9's second measurement.* *(2026-11-23: over the 12 classes, 117 of the
  capture's 122 attachment ids are in a `t51ITc` answer and none in the item record; the 5 others
  are open, #287.)*
- **Paging.** `dpT4Vd` asks for 10 items a call and was never paged here. The largest topic of the
  run's 12 classes holds exactly 10 items; one more would need the next page, untested. *Decided:
  always paged (R1); paging is forced and tested in S9's second measurement.* *(2026-11-23: tested,
  R1; «exactly 10» was the first page of a longer list, #288.)*
- **Two stream records.** Class 1's stream (`pONvgf`) held 2 item records, slot 1, that neither
  `dpT4Vd` nor the capture holds. The read takes items from `dpT4Vd` only; what they are is not
  known. The comparison takes items from `dpT4Vd` only; the probe sent the four item calls for
  these two as well (8 of the 225). *Decided: measured and explained in S9's second measurement.*
  *(2026-11-23: with every list paged, no item record is left to the stream alone; these were most
  likely items past a list's first 10, which the capture lacks too, #288.)*
- **The teacher's «missing» mark** (above). *Decided: detected and raised as an event (R7); its
  field is S9's second measurement. The event's channel, 2026-11-23: an email to the family
  (FR-033).*

**S9's second measurement** (#283), after the next scheduled refresh: the read sending `UG41I`
itself, once; grouping calls as the page does, and the time of a whole read so grouped; paging
forced with a small page; the two stream-only records; the field of the teacher's «missing» mark;
and the two attachments no call returned. *(Measured 2026-11-23, with a third measurement for what
it left: «S9 · Second and third measurements» below.)*

Also measured: **`tQShAc` adds nothing** the `dpT4Vd` record lacks for the compared fields (titles,
descriptions); leaving it out would save 122 of the 583 calls.

**The probes** are on branch `spike/279-s9-read-by-calls` (`spikes/s9*`), kept off `main`.

### S9 · Second and third measurements — a whole read in 8 minutes, paging within a topic works, the mark has its field; the student's number from the page's own request

Asked in julioarguello/alfabeta#283 and #287. Measured 2026-11-23, read-only, by Claude on the
operator's standing permission to run tests, inside spec 001 research R15's limits (no sign-in, no
password), in the session of the family's `classroom refresh` that ended `ok` at 16:47 — run by
the family by hand, the scheduled 16:15 one having stopped `docker_low_memory`. The read image with
the read's own `Guard`, `browserinfo` blocked; before each probe the request templates were learnt
again from the page (`s9t`); one request at a time, 1–2 s apart. Three probes kept: `s9d`
(16:51–16:57, the 3 classes whose capture shows the teacher's notice, 86 requests), `s9f`
(17:10, `UG41I`'s shapes, 6 requests) and `s9e` (17:13–17:22, every class, 288 requests). Earlier
tries of `s9d` and `s9e` that afternoon stopped on faults of the probes, and their output is not
used. No breach; no stop; the session survived each (`RotateCookiesPage` requested and blocked).

| Question | Answer |
|---|---|
| The student's number | `UG41I` answers with it (at `[2,0,0,0]`) only when its request carries it already: of the page's own shapes, the 3 that carry it do, the 3 that do not, do not. It is in the page's own requests as it loads, in no `WIZ_global_data` key. The home page sent its `O1Xqee` within 15 s each time the probe waited for it; once, 1.5 s was too short |
| Several calls in one request | answered: two names (`s9d`), one name six times (`s9e`) |
| `Zj93ge`, 12 items in one call | as the page sends it: the same status as one call per item, 15 of 15 compared (first 5 items of 3 classes). `s9e` built the group at the wrong depth and got an error row each time, then sent one item a call |
| `t51ITc` for several items | 12 item keys in one call (a shape the probe made, not the page's): agrees with one call per item for 1 of 11 attachments. Six `t51ITc` calls in one request: agrees for 9 of 9 |
| Attachments | 117 of the capture's 122 attachment ids are in a `t51ITc` answer, none in the item record; 5 in neither |
| Paging | the next-page token is at answer `[1,1,0]` and goes at request `[0][1]`. Within a topic read 3 a page, the pages equal the capture's items of that topic (topics of 5, 6 and 7 items). With 10 a page, every single-page list equals the capture; the two lists that ran to a second page (two classes) gave 2 and 3 items the capture lacks, under no other topic either (#288) |
| The stream-only records | with every list paged, none: no item record is left to the stream alone. One `s9d` saw before paging was in place was 48–82 days old by its instants, with paths `[0,14]`, `[0,25]` and `[0,27,…]` not common to the class's first 10 records |
| The teacher's «missing» mark | `[32]` of the item's entry in `Zj93ge`'s answer is 3 on every item the capture shows with the notice and on no other item of the 12 classes, graded items without the notice included. The item record shows no difference |
| A whole read | 12 classes, 131 items, the same items as the capture in 10 classes (the other two: #288): 270 requests, 503 s, with `Zj93ge` one item a call; the extractor's refresh of the same session took 916 s. With `Zj93ge` grouped as `s9d` measured, about 75 requests fewer (estimated) |

Against the family's decisions of 2026-11-20 and R1, R3, R7:

- **The student's number** — decided by the operator, 2026-11-23. The family's earlier decision,
  the read sends `UG41I` once, cannot work as written: `UG41I` answers with the number only when
  asked with it. The read takes it from the page's own request as the page loads (home, or one
  class page if the home page sends none), keeps it in memory for that run only, and sends eight
  names (R3).
- **FR-003's «one call at a time»** — decided by the operator, 2026-11-23: one request at a time, each
  with several calls of the read's allowlist as the page sends them (`Zj93ge` grouped, `t51ITc` and
  `cCzVwf` six to a request), pauses kept. The page itself sends so.
- **Paging**: settled; R1's «always page» is built with the token's places above.
- **Items past a list's first 10**: the read by calls finds items the extractor's capture lacks;
  whether the student sees them, and the extractor's fix, are #288.
- **The mark**: settled, `[32]` = 3 (R7; data-model's status table).
- **Attachments**: 5 of 122 in no `t51ITc` answer; what they are stays in #287.

**The probes**: `spikes/s9d_followup.py`, `s9e_third.py` and `s9f_number.py` on the same branch.
