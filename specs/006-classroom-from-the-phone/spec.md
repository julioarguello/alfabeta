# Feature Specification: Classroom read on the Mac with no app open, signed in from the phone

**Feature Branch**: `ccr-d87a94c2-915xmy` (spec dir `006-classroom-from-the-phone`)

**Created**: 2026-11-02

**Status**: Draft

**Input**: Operator's request (translated from Spanish): "Why the Mac? I would like it to be a web
page or an app I could launch from the Mac or the phone" («me gustaría que fuera una web o app que
pudiera lanzar desde el mac o el movil»); "Copy classroom-advisor: after all they went through the
same, and everything we have measured leads in that same direction" («copia a classroom-advisor...
al fin y al cabo han pasado por lo mismo»); and "I would like a notice to pop up with a link; I click
it and it sets everything off" («me gustaría que saltara un aviso con un enlace. clico en él y
dispara todo»). Tracked in julioarguello/alfabeta#166.

## Context and scope

Today a Classroom read (spec 001) runs inside the Claude desktop app: the `classroom-sync` skill
drives the operator's Chrome through the Claude extension, and a scheduled run is a scheduled task of
the app that, finding the school session expired, shows a macOS notification and waits for someone
to sign in at the Mac (FR-021a, #163). A read therefore needs three things: the Claude app open, a
Chrome window on the Mac's screen, and a person at the Mac to sign in.

The measurements of 2026-10-31 and 2026-11-01 leave one of those three standing. Every read needs a
human sign-in shortly before it, and nothing alfabeta may build removes that. This spec removes the
other two, and the need to be at the Mac for the third.

### What was measured before writing this

| Fact | Observed with | Date |
|---|---|---|
| The Classroom API refuses the student's school account, also from Google's own reference «Try it» («una organización … tiene este servicio desactivado») | the operator, spec 001 research R20 | 2026-11-01 |
| Neither client spike S4 tried, the Classroom Android app and Play services, drew a read-only Classroom token for the student's account, so the token route is not built | spike S4, spec 001 research R15 | 2026-10-31 |
| The school session signed in at 20:12 was alive at 20:42 and gone at 21:12, although a page was loaded at each. Whether the limit counts from the sign-in or from the last activity is not settled: both gaps were 30 minutes | a probe on the operator's Mac, spec 001 research R20 | 2026-11-01 |
| The session's life varies: others of this account died within about 1 h 20 min or lasted at least 2 h 47 min; none has been seen to last from one day's read to the next | spec 001 research R1, R16 | 2026-10-25 to 2026-10-28 |
| The family's hand sign-in was accepted in a visible browser window the probe itself had started, and the probe then loaded the Classroom home page from that profile with no window on screen. Only the home page was loaded; no class was read that way | the same probe, R20 | 2026-11-01 |
| The school domain refuses adding an external forwarding address, so Classroom's per-event notification emails cannot leave the school account; they sit behind the same session | the operator, R20 | 2026-11-01 |
| With the current extractor, the pages it loads hardly progress while the Classroom tab is hidden behind another window | spec 001 research, Observed facts | 2026-10-28 |
| Classroom's web app gets its data through named read calls, which a peer project calls directly from one loaded page behind an allowlist of call names, headless included, with no challenge seen. External, not measured on this account | lifecoderua/classroom-advisor, its `docs/CLASSROOM-INTERNALS.md`, read | 2026-11-01 |
| Google's web session length is set by each domain's administrator and does not apply to native mobile apps or OAuth apps | Google Workspace admin help, «Set session length for Google services», read | 2026-11-01 |

### Not measured, so asked of the plan's spikes

- Reading every class through Classroom's read calls from a profile with no window on screen: the
  probe loaded only the home page.
- Which read calls this account's Classroom makes for every page the read needs (courses,
  classwork, stream, item details, materials, the student's submissions), and whether reads and
  writes can be told apart by call name. Spec 001's spike S6 records only a to-do read and a detail
  read, for User Story 7; this spec needs it widened (FR-004).
- Signing in, and unlocking the Mac, from the phone through a remote view of the Mac's screen
  (FR-012).
- How long the notice email takes to reach the phone, and whether Gmail notifies the phone at all for
  an email the account sent to itself (FR-013).
- One link that, opened on the Mac, brings the sign-in window to the front and, opened on the phone,
  opens the remote view of the Mac (FR-013).
- Whether the session's limit counts from the sign-in or from the last activity (a probe loading
  every 5 minutes), and so how soon after the sign-in the read must start (FR-010).

### In this spec

- **A read with no app open.** alfabeta's own command reads Classroom on the Mac from a browser
  profile kept for the student, with no window on screen, through Classroom's own read calls behind
  the browser guard spec 001 research R18 designed. It leaves the capture spec 001 already applies,
  so replicas, mirrors and the agenda do not change.
- **A notice with a link, and the sign-in from the phone.** When a read needs a sign-in, the family
  gets an email with one link. On the Mac the link brings the sign-in window to the front; on the
  phone it opens a remote view of the Mac's screen with that window. The family signs in; alfabeta
  closes the window and the read goes on alone.
- **Launching when the family wants**, from the Mac or, through the remote view, from the phone.

### Out of this spec

- **Reading with nobody signing in** (spec 001 User Story 7, #2). R15 and R20 leave no route that
  keeps the session alive; User Story 7 stays as specified and gated on its spikes.
- **Running the read on the phone, or on a machine other than the Mac.** The session lives in the
  browser where the family signs in, and the read, Drive and the mirrors are on the Mac; the phone
  is a remote view, not where the read runs. A dedicated always-on machine at home, as the peer
  project uses, is left to a later spec, with constitution IX amended first.
- **A third-party messaging channel** such as Telegram, which the peer project uses: constitution
  III lets data go only to services the family uses and configures.
- **Judgement.** Linking a new class to a subject, matching a new topic and detecting an exam
  (spec 001 R7) stay with Claude in the family's next session; this read leaves them pending
  (FR-007).
- **The notebook refresh** (spec 005) and the study pack (spec 002).

### What alfabeta takes from the peer project

lifecoderua/classroom-advisor is MIT, like alfabeta. This spec takes its pattern: a browser profile
kept for the read on the machine that runs it, a sign-in by hand in that profile, the data read from
Classroom's own read calls behind an allowlist of call names, and the parent signing in again from
the phone. The plan credits it, and any code ported from it keeps its copyright notice. Its call
names and response shapes are a starting point, not a measurement of this account (FR-004).

### Changes elsewhere, in this pull request

- **Constitution, Technical constraints** (2.5.0 → 2.6.0, MINOR): the environment allows this
  read's per-student browser profile, signed in by hand in a window alfabeta does not drive, and its
  start from the launchd agent with no app open.
- **Spec 001 FR-006 and FR-021a**: for a student with this read switched on, the scheduled read is
  this one, started by `[schedule]`; the full sync launched with a request to Claude keeps the
  extension; this switch and the unattended runner cannot both be on.
- **Spec 004 FR-004, FR-005, Key Entities and data model**: a family account may be linked, role
  `family`, with Gmail send only, for this spec's notices. This answers spec 001 research R17, which
  rejected an email notice because no spec granted that scope; R17 now points here.
- **Spec 001 research R20**: the probe's details, and corrections of #165: only the probe's time of
  death was measured, it does not tell an absolute limit from an idle one, and the session's life
  varies (R1, R16).

## Clarifications

### Session 2026-11-02

- Q: Why must it be the Mac? → A: Only the session has to live somewhere real. The school account
  needs a human sign-in before every read (R20), and Google is warier of a browser in a datacenter
  (spec 001 research R16, R17), so the browser that holds the session runs at home, on the Mac (IX).
  The family does not have to be in front of it.
- Q: The operator: «Si lo hago desde el móvil pues se ejecutaría en el móvil, si lo hago desde el
  mac, pues desde el mac» — can the read run on whichever device the link is clicked? → A: The link
  works from both, but the read always runs on the Mac: the session lives in the browser where the
  family signs in, and Google ties it to that device, so a sign-in on the phone's own browser would
  leave the Mac without it; and the read, Drive and the mirrors are on the Mac. From the phone the
  link opens the remote view of the Mac's screen. For the family the steps are the same on both:
  click and sign in.
- Q: Notices to the phone, through what? → A: An email from a family account alfabeta links only
  for it (spec 004 as amended). A calendar reminder would ring for the student only (spec 003
  FR-002), and a messaging app is a third party (III).
- Q: Can Classroom's own notification emails start a read? → A: No. They sit in the school account,
  behind the same session (R20), so they cannot be read before the sign-in.
- Q: How does the read know the family has signed in, if alfabeta does not drive the sign-in
  window? → A: alfabeta watches only the address the window shows, never its content: when it
  reaches Classroom, the sign-in is done and alfabeta closes the window and reads. The family may
  also close it themselves. (First wording: only the family closing it, or the end of the wait,
  ended it; the independent review found the session could die while the read waited.)

## User Scenarios & Testing *(mandatory)*

The actors are **the family** (the parent who configures alfabeta and signs the student's school
account in), **the student**, whose school account and material are read, and **the teachers**, who
post in Classroom and never interact with alfabeta.

### User Story 1 - Classroom is read on the Mac with no app open and no window on screen (Priority: P1)

Once the student's school account is signed in to the profile alfabeta keeps for it, a read runs on
the Mac from alfabeta's own command, without the Claude app and without any window on screen. It
reads every active class and leaves the capture spec 001's apply step uses, so the topic folders,
the mirrors and the agenda are updated exactly as today.

**Why this priority**: it removes the two needs that force the family to the Mac today, the open app
and the visible window, and the other stories stand on it.

**Independent Test**: with the Claude app closed, sign in to the read profile at the Mac and close
the sign-in window; lock the screen; run the read for one student. Compare its capture with a
capture of the same classes by the current extractor on the same day, and apply it twice.

**Acceptance Scenarios**:

1. **Given** a signed-in profile, the Claude app closed and the Mac's screen locked, **When** the
   read runs, **Then** it reads every active class, downloads the attachments it lists, and leaves
   a capture marked `complete` for each class it finished.
2. **Given** the same class read by the current extractor and by this read on the same day,
   **When** both captures are compared, **Then** they hold the same items with the same
   identifiers, statuses, modification marks, attachments, stream posts, and, where spec 001 User
   Story 6 is built, the same submissions and gradings.
3. **Given** a capture already applied, **When** the read runs again with nothing changed in
   Classroom, **Then** applying it writes nothing (constitution V).
4. **Given** a class whose data the read cannot interpret, **When** the read runs, **Then** that
   class stops with `unexpected_ui`, the other classes are read and applied, and nothing is
   withdrawn because it was not read.

---

### User Story 2 - A notice with a link, and the sign-in from the phone (Priority: P1)

A read that finds the session expired opens the Google sign-in for the school account in a browser
window on the Mac and emails the family one link. The family clicks it on the phone, which opens a
remote view of the Mac's screen; they unlock the Mac if needed and sign in. alfabeta closes the
sign-in window. The read goes on by itself, and when it ends the family gets the result by email.

**Why this priority**: no session has been seen to last from one day's read to the next (R20), so
nearly every read needs this.
Without it the family still has to be at the Mac.

**Independent Test**: with nobody at the Mac and the Claude app closed, let a scheduled read start
with the session expired. On the phone, click the notice's link and sign in through the remote
view; when the read ends, the topic folders show the new material and the result email has
arrived.

**Acceptance Scenarios**:

1. **Given** an expired session at a scheduled time, **When** the read starts, **Then** within a
   minute it has sent the notice email, in Spanish, naming the student only by its id, saying until
   when the sign-in waits and carrying one link, and a browser window with the Google sign-in for
   the school account is open on the Mac.
2. **Given** that window, **When** the family signs in from the phone, **Then** alfabeta closes
   the window, the read reads in the background and, when it ends, sends one result email with counts only.
3. **Given** no sign-in before the wait ends, **When** it ends, **Then** the read closes the
   window, finds the session expired, stops with `session_expired`, writes nothing to the student's
   folder, and says so once.
4. **Given** the family signs in with an account other than the student's school account, **When**
   the read checks the session, **Then** it stops with `session_expired` before reading anything,
   and the result email says another account was signed in, without naming it.
5. **Given** Google answers the sign-in or the read with a check a human must clear beyond what the
   family typed, **When** it appears, **Then** the read stops with `challenge` and nothing is typed
   to get past it.

---

### User Story 3 - A read is launched when the family wants (Priority: P2)

Besides the scheduled times, the family can start a read whenever they want: on the Mac with one
command or by opening a launcher, and from the phone by opening that launcher through the remote
view. The read asks for the sign-in only if the session is not alive.

**Why this priority**: the schedule covers the usual day; this covers the day a teacher posts
something urgent or a scheduled read was missed.

**Independent Test**: with the Claude app closed, open the launcher from the phone through the
remote view; sign in when the window appears; the read runs and the result email
arrives.

**Acceptance Scenarios**:

1. **Given** no read running for the student, **When** the family opens the launcher (on the Mac or
   through the remote view), **Then** a read starts, asking for the sign-in only if the session is
   not alive.
2. **Given** a read for the student already running or waiting for its sign-in, **When** the
   launcher is opened again, **Then** no second read starts and the family is told one is under way.
3. **Given** the family's usual request to Claude for a full sync (spec 001 FR-021a), **When** they
   make it, **Then** it still works as today, with the extension.

### Edge Cases

- **The Mac is asleep at a scheduled time.** No read runs. A missed time is not made up outside the
  hours the configuration sets; it is logged, and the next time or the launcher covers it.
- **The Mac's screen is locked.** The read needs no unlocked screen. The sign-in does: the family
  unlocks the Mac through the remote view with its password, which they type themselves; alfabeta
  never stores or types it.
- **The remote view is not set up, or the phone has no connection.** The notice still says a sign-in
  is waiting on the Mac; signing in at the Mac works the same.
- **The family signs in but leaves the window open.** When the window's address reaches Classroom,
  the read closes it and starts at once, so the session is not spent waiting.
- **The session dies in the middle of a read.** Classes already read are applied as `partial` with
  `session_expired` (FR-021a's rule); the rest wait for the next read.
- **Classroom changes a call name or a response shape.** A call not on the allowlist is blocked and
  counted, never sent. A response that cannot be interpreted stops its class with `unexpected_ui`; an
  item that cannot be interpreted is skipped and listed. Nothing is withdrawn because it was not
  read (spec 001 FR-027).
- **A page tries to press something or open a form during the read.** The browser guard blocks it
  before it reaches Classroom and counts it (constitution IV).
- **Two students.** Each has a profile and a sign-in window of their own; reads run one at a time
  under the Mac's browser lock (FR-021a), and each notice names its student by id.
- **The notice does not arrive.** The read waits its full time regardless; the log shows the wait and
  its outcome.
- **An attachment Drive holds behind its virus-scan notice.** It is noted as not brought, with its
  link, as today (spec 001 research R4).

## Requirements *(mandatory)*

### Functional Requirements

**Where it runs**

- **FR-001**: The read MUST run on the family's Mac as alfabeta's own command, started by the
  launchd agent at the scheduled times, by the launcher, or by a command, with no app open (the
  Claude desktop app included) and with no window on screen while it reads. It runs only for a
  student whose switch for it is on (FR-019).
- **FR-002**: Each student MUST have a browser profile of their own, kept in the student's data
  folder with user-only permissions (constitution II), used only by this read and its sign-in. Its
  session never leaves the Mac. The sign-in window and the read MUST use the same browser
  installation, so the read can use the session the family started, and MUST NOT hold the profile
  at the same time.

**Reading**

- **FR-003**: The read MUST get Classroom's data from the read calls Classroom's own pages make, sent
  from a Classroom page loaded in the student's profile, one call at a time with pauses, as a
  student browsing (constitution IV).
- **FR-004**: The read MUST send only calls whose names are on an allowlist of reads, recorded on
  this account before anything is built, for every page the read needs: a spike in this spec's plan
  widens spec 001's S6 to them. The peer project's catalogue may seed the recording but does not
  replace it. If reads and writes cannot be told apart by call name on this account, this read is
  not built and the plan says so.
- **FR-005**: Read-only MUST hold by construction during the whole read (constitution IV), with the
  guard of spec 001 research R18 installed in the browser before any page script runs. It blocks,
  before they reach Classroom, every press, every document load outside the pages spec 001 FR-007
  lets the full sync load, every
  call not on the allowlist, and every request to a form or quiz host. Downloads are allowed only
  for the attachments this read listed in this run, through the routes of spec 001 research R4.
  Every blocked item is counted, and the counts go into the log.
- **FR-006**: Before any call, the read MUST check that the account signed in to the profile is the
  student's configured school account. Another account counts as no session: the read stops with
  `session_expired`, with nothing read, and the result email says another account was signed in,
  without naming it.
- **FR-007**: The read MUST leave, in spec 001's capture format, everything the current extractor
  captures: classes, topics, items with their details, statuses, modification marks and
  attachments, the stream's posts, and, where spec 001 User Story 6 is built, the student's
  submissions and gradings. Planning, applying, replicas, mirrors and the agenda then work
  unchanged. What needs judgement (a class not yet linked to a subject, a new topic match, an exam
  candidate; spec 001 R7) MUST NOT be decided by this read: it is left pending, counted in the
  result email and decided in the family's next session with Claude (spec 001 FR-021b); what is
  already decided is applied.
- **FR-008**: A response the read cannot interpret MUST stop only its class, with `unexpected_ui`
  (spec 001's reason), and an item that cannot be interpreted MUST be skipped and listed; the other
  classes go on, and nothing is withdrawn because it was not read (spec 001 FR-027). A course list
  that cannot be read stops the read with `unexpected_ui`.
- **FR-009**: When the session ends in the middle of a read, the classes already read MUST be applied
  as `partial` with `session_expired` (FR-021a's rule).

**Signing in**

- **FR-010**: A read that finds the profile's session expired MUST open, on the Mac's screen, a
  browser window in the student's profile on Google's sign-in for the school account. alfabeta
  starts that browser and does not drive it: no script of alfabeta's runs in it, and alfabeta
  presses, types and reads nothing in it while it is open, except the address of the page the
  window shows. The read's guard is not in it, because a person, not alfabeta, acts in it. The wait
  ends at the first of: the family closes the window; the window's address reaches Classroom,
  which means the family has signed in; or `schedule.wait_minutes` (spec 001 FR-021a) runs out. In
  the last two cases alfabeta closes the window itself. The read then opens the profile with the
  guard on and checks the session once, so it starts as soon as the sign-in ends. The read's lock is
  renewed while it waits.
- **FR-011**: alfabeta MUST NOT type, fill or submit anything on a sign-in page: the family types
  everything (constitution III). A check a human must clear, met during the read beyond what the
  family typed, stops the read with `challenge` and is reported once; nothing is typed to get past
  it (constitution IV).
- **FR-012**: The family MUST be able to complete the sign-in from the phone through a remote view
  of the Mac's screen given by a service of the family's own Google account, including unlocking the
  Mac with its password, which they type themselves and alfabeta never stores.

**Telling the family**

- **FR-013**: Within a minute of starting to wait for a sign-in, the read MUST send a notice email
  from the account linked with role `family` (spec 004 as amended) to that same account. It is in
  Spanish, names the student only by its id, says until when the sign-in waits, and carries one
  link: opened on the Mac, it brings the sign-in window to the front; opened on the phone, it opens
  the remote view of the Mac's screen. The macOS notification of FR-021a is shown as well.
- **FR-014**: When a read ends, it MUST send one result email the same way, with counts only: classes
  read, new and changed items, attachments brought and not brought, decisions left pending, items
  the guard blocked, and the stop reason if any. No email, log line or URL MAY carry a name, an email
  address or the title of anything in Classroom (constitution III).

**Launching**

- **FR-015**: When a student's switch is on, the times `[schedule]` sets for each weekday MUST start
  this read instead of the desktop app's scheduled task of spec 001 FR-021a, and only if the Mac is
  awake; a time missed while it slept is logged and not made up outside those hours. This switch and
  spec 001's unattended runner (FR-032) MUST NOT both be on for one student: the configuration check
  reports it.
- **FR-016**: The family MUST be able to start a read at any time with one command, and by opening a
  launcher on the Mac that does the same, which the notice's link and the remote view can open.
- **FR-017**: A launch while a read for that student is running or waiting for its sign-in MUST NOT
  start another; it tells the family one is under way (the browser lock of FR-021a).
- **FR-018**: The full sync launched with a request to Claude (spec 001 FR-021a) MUST keep working
  with the extension (spec 001 FR-006 as amended).

**Configuration and records**

- **FR-019**: This spec's keys — the per-student switch that turns the read on, and the alias of the
  `family` account for notices — MUST be declared in `config/template.toml` with `changeme` values
  when its code lands (template mirroring, constitution II), and no key MAY hold a password, a cookie
  or an address of the student's.
- **FR-020**: Every read MUST leave one log line with what started it (schedule, launcher, command),
  how long it waited for the sign-in, its stop reason, its counts and the guard's blocked counts
  (constitution V).

### Key Entities

- **Read profile**: the browser profile kept for one student's read; holds the school session after
  the family signs in; lives in the student's data folder.
- **Sign-in window**: the browser window alfabeta opens on Google's sign-in in the read profile and
  does not drive; the family signs in in it, and alfabeta closes it when its address reaches
  Classroom (or the family closes it).
- **Read allowlist**: the names of Classroom's read calls the read may send, recorded on this
  account; anything else is blocked.
- **Sign-in wait**: one read's wait for the family: when it started, until when it waits, and how it
  ended (`signed_in`, `session_expired`, `challenge`).
- **Notice**: an email to the family account, of two kinds: a sign-in is waiting (student id,
  deadline, link) or a read ended (student id, counts, stop reason).
- **Capture**: what the read leaves for spec 001's apply step, in spec 001's format.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Over 10 consecutive school days, at least 9 scheduled reads that the family signs in
  to from the phone update the topic folders with nobody at the Mac and the Claude app closed.
- **SC-002**: Over the reads of SC-001, with the remote view set up and the Mac awake, the median
  time from opening the notice's link on the phone to the end of the sign-in is under 2 minutes.
- **SC-003**: A read of all the student's classes finishes within 30 minutes of the sign-in, inside
  the session's life (R20).
- **SC-004**: Over those reads, nothing is pressed, no form or quiz is opened, and every call outside
  the allowlist is blocked and counted; in the offline test, a planted press, a planted form link and
  a planted write call are all blocked and never reach the fake server.
- **SC-005**: For the same classes on the same day, this read and the current extractor give the
  same items, identifiers, statuses, attachments, stream posts and, where built, submissions and
  gradings; a second apply writes nothing.
- **SC-006**: No email, log line or URL from these reads contains a name, an email address or a
  Classroom title (the guardrail, and a test over the emails).

## Assumptions

- The Mac is awake with the family's user session logged in at the scheduled times, the condition
  spec 005 already accepts.
- The family sets up, once, a remote view of the Mac on the phone through a service of their own
  Google account (Chrome Remote Desktop).
- The read's call names and response shapes are those of the same Classroom web app the peer
  project documents; the widened spike checks them on this account before building.
- Reading through calls is faster than the hidden-iframe extractor, which took 14 minutes for eleven
  classes (spec 001 research R4), so a whole read fits inside the session's life.

## Dependencies

- **Spec 001**: the capture format and apply step, FR-006 (as amended), FR-021a's lock and sign-in
  wait (#163), FR-021b, FR-027, research R4 (downloads), R7 (judgement), R18 (the browser guard),
  and spike S6, widened.
- **Spec 004**: the family's Google connection, with the `family` account FR-004 and FR-005 now
  allow, through which the notices are sent.
- **Constitution**: II (the profile in the data folder), III (no third party, the family types the
  sign-in), IV (read-only by construction, no evasion), IX (on the Mac) and Technical constraints
  (2.6.0, amended here).
- **A library that drives a browser**: a new dependency, which the plan must justify (IX).
- **The peer project**: lifecoderua/classroom-advisor (MIT), credited in the plan.
