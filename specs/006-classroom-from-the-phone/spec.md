# Feature Specification: Classroom read on the Mac with no app open, signed in from the phone

**Feature Branch**: `ccr-d87a94c2-915xmy` (spec dir `006-classroom-from-the-phone`)

**Created**: 2026-11-02

**Status**: Draft

**Input**: Operator's request (translated from Spanish): "Why the Mac? I would like it to be a web
page or an app I could launch from the Mac or the phone" («me gustaría que fuera una web o app que
pudiera lanzar desde el mac o el movil»), and "Copy classroom-advisor: after all they went through
the same, and everything we have measured leads in that same direction" («copia a
classroom-advisor... al fin y al cabo han pasado por lo mismo»). Tracked in
julioarguello/alfabeta#166.

## Context and scope

Today a Classroom read (spec 001) runs inside the Claude desktop app: the `classroom-sync` skill
drives the operator's Chrome through the Claude extension, and a scheduled run is a scheduled task of
the app that, finding the school session expired, shows a macOS notification and waits for someone
to sign in at the Mac (FR-021a, #163). A read therefore needs three things: the Claude app open, a
Chrome window on the Mac's screen, and a person at the Mac to sign in.

The measurements of 2026-10-31 and 2026-11-01 leave one of those three standing. Every read needs a
human sign-in shortly before it, and nothing alfabeta may build removes that. What this spec removes
is the other two, and where the person has to be.

### What was measured before writing this

| Fact | Observed with | Date |
|---|---|---|
| The Classroom API refuses the student's school account, also from Google's own reference «Try it» («una organización … tiene este servicio desactivado») | the operator, spec 001 research R20 | 2026-11-01 |
| No first-party Android client is registered for the read-only Classroom scopes, so the token route is not built | spike S4, spec 001 research R15 | 2026-10-31 |
| The school session dies within about an hour of a hand sign-in, and a reload every 30 minutes does not extend it: a reloaded arm and an untouched arm expired in the same window (absolute timeout) | a two-arm overnight probe on the operator's Mac, R20 | 2026-11-01 |
| A hand sign-in in a browser the probe itself started (not the operator's everyday Chrome) was accepted, and that browser then read Classroom with no window on screen until the session expired | the same probe | 2026-11-01 |
| The school domain refuses adding an external forwarding address, so Classroom's per-event notification emails cannot leave the school account; they sit behind the same hour-long session | the operator, R20 | 2026-11-01 |
| With the current extractor, Classroom pages hardly load while the Chrome window is hidden | spec 001 Clarifications | 2026-11-01 |
| Classroom's web app gets its data through named read calls, which a peer project calls directly from one loaded page behind an allowlist of call names, headless included, with no challenge seen. External, not measured on this account | lifecoderua/classroom-advisor, `docs/CLASSROOM-INTERNALS.md`, read | 2026-11-01 |
| Google's web session length is set by each domain's administrator, and does not apply to native mobile apps or OAuth apps | Google Workspace admin help, «Set session length for Google services», read | 2026-11-01 |

### In this spec

- **A read with no app open.** alfabeta's own command reads Classroom on the Mac from a browser
  profile kept for the student, with no window on screen, through Classroom's own read calls behind
  the browser guard spec 001 R18 designed. It writes the capture spec 001 already applies, so
  replicas, mirrors and the agenda do not change.
- **The sign-in from the phone.** When a read needs a sign-in, the family is told on the phone
  through a Google service they already use, and signs in on the Mac's screen seen remotely from the
  phone. Once the session answers, the read goes on alone.
- **Launching from the phone or the Mac.** At the scheduled times, or whenever the family opens the
  launcher, from the Mac or from the phone through the same remote view.

### Out of this spec

- **Reading with nobody signing in** (spec 001 User Story 7, #2). R15 and R20 leave no route that
  keeps the session alive; User Story 7 stays as specified and gated on its spikes.
- **A machine other than the Mac.** Constitution IX names the family's Mac or the operator's cloud
  project. A dedicated always-on machine at home, as the peer project uses, would need IX amended
  first (FR-001, Clarifications).
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
names and response shapes are a starting point, not a measurement of this account: the allowlist is
recorded on this account first (spec 001 spike S6, FR-004).

## Clarifications

### Session 2026-11-02

- Q: Why must it be the Mac? → A: Only the session has to live somewhere real. The school account
  needs a human sign-in before every read (R20), and Google is warier of a browser in a datacenter
  (R16, R17), so the browser that holds the session runs at home. The family does not have to be in
  front of it: they launch the read and sign in from the phone through a remote view of the Mac's
  screen. Which machine at home holds it is FR-001's open question.
- Q: Notifications to the phone, through what? → A: Through the family's own Google account
  (constitution III), not a messaging app. The plan picks between an email to the account the
  configuration names for notices and an event with an immediate reminder on a calendar of that
  account (FR-013); both reach the phone with nothing new installed.
- Q: Can Classroom's own notification emails start a read? → A: No. They sit in the school account,
  behind the same hour-long session (R20), so they cannot be read before the sign-in. Once a read is
  signed in they may serve as a quick index of what is new; the schedule or the launcher is what
  asks for the sign-in.

## User Scenarios & Testing *(mandatory)*

The actors are **the family** (the parent who configures alfabeta and signs the student's school
account in), **the student**, whose school account and material are read, and **the teachers**, who
post in Classroom and never interact with alfabeta.

### User Story 1 - Classroom is read on the Mac with no app open and no window on screen (Priority: P1)

Once the student's school account is signed in to the profile alfabeta keeps for it, a read runs on
the Mac from alfabeta's own command, without the Claude app and without any window on screen. It
reads every active class and leaves the same capture spec 001's apply step uses, so the topic
folders, the mirrors and the agenda are updated exactly as today.

**Why this priority**: it removes the two needs that force the family to the Mac today, the open app
and the visible window, and the other stories stand on it.

**Independent Test**: with the Claude app closed and the screen locked, sign in at the Mac, run the
read for one student, and compare: the capture lists the same classes, items, statuses and
attachments as a capture of the same classes by the current extractor, and a second apply writes
nothing.

**Acceptance Scenarios**:

1. **Given** a signed-in profile, the Claude app closed and the Mac's screen locked, **When** the
   read runs, **Then** it reads every active class, downloads the attachments it lists, and leaves
   a capture marked `complete` for each class it finished.
2. **Given** the same class read by the current extractor and by this read on the same day,
   **When** both captures are compared, **Then** they hold the same items with the same
   identifiers, statuses, modification marks and attachments.
3. **Given** a capture already applied, **When** the read runs again with nothing changed in
   Classroom, **Then** applying it writes nothing (constitution V).
4. **Given** a class whose data the read cannot interpret, **When** the read runs, **Then** that
   class stops with `drift`, the other classes are read and applied, and nothing is withdrawn
   because it was not read.

---

### User Story 2 - The family signs in from the phone (Priority: P1)

A read that finds the session expired opens the Google sign-in for the school account in a browser
window on the Mac and tells the family on the phone. The family opens a remote view of the Mac's
screen on the phone, unlocks the Mac if needed, signs in, and closes the remote view. The read goes
on by itself, and when it ends the family gets the result on the phone.

**Why this priority**: the session lasts about an hour (R20), so nearly every read needs this. Without
it the family still has to be at the Mac.

**Independent Test**: with nobody at the Mac and the Claude app closed, let a scheduled read start
with the session expired. On the phone, follow the notice, sign in through the remote view, and
close it; within the read's time the topic folders show the new material and the phone shows the
result notice.

**Acceptance Scenarios**:

1. **Given** an expired session at a scheduled time, **When** the read starts, **Then** within a
   minute a notice reaches the family's phone, in Spanish, naming the student by its id and saying
   until when the sign-in waits, and a browser window with the Google sign-in for the school account
   is open on the Mac.
2. **Given** that window, **When** the family signs in from the phone, **Then** the read closes the
   window, reads in the background and, when it ends, sends one result notice with counts only.
3. **Given** no sign-in before the wait ends, **When** it ends, **Then** the read stops with
   `session_expired`, writes nothing to the student's folder, and says so once.
4. **Given** the family signs in with an account other than the student's school account, **When**
   the session answers, **Then** the read stops with `wrong_account` before reading anything.
5. **Given** Google answers the sign-in or the read with a check a human must clear beyond what the
   family typed, **When** it appears, **Then** the read stops with `challenge` and nothing is typed
   to get past it.

---

### User Story 3 - A read is launched from the phone or the Mac when the family wants (Priority: P2)

Besides the scheduled times, the family can start a read whenever they want: on the Mac with one
command or by opening a launcher, and from the phone by opening that same launcher through the remote
view. The read asks for the sign-in only if the session is not alive.

**Why this priority**: the schedule covers the usual day; this covers the day a teacher posts
something urgent or a scheduled read was missed.

**Independent Test**: with the Claude app closed, open the launcher from the phone through the remote
view; sign in when asked; the read runs and the phone gets the result notice.

**Acceptance Scenarios**:

1. **Given** no read running for the student, **When** the family opens the launcher (on the Mac or
   through the remote view), **Then** a read starts, asking for the sign-in only if the session is
   not alive.
2. **Given** a read for the student already running or waiting for its sign-in, **When** the
   launcher is opened again, **Then** no second read starts and the family is told one is under way.
3. **Given** the family's usual request to Claude for a full sync (FR-021a), **When** they make it,
   **Then** it still works as today.

### Edge Cases

- **The Mac is asleep at a scheduled time.** No read runs. A missed time is not made up outside the
  hours the configuration sets; it is logged, and the next time or the launcher covers it.
- **The Mac's screen is locked.** The read needs no unlocked screen. The sign-in does: the family
  unlocks the Mac through the remote view with its password, which they type themselves; alfabeta
  never stores or types it.
- **The remote view is not set up, or the phone has no connection.** The notice still says a sign-in
  is waiting on the Mac; signing in at the Mac works the same.
- **The session dies in the middle of a read.** Classes already read are applied as `partial` with
  `session_expired` (FR-021a's rule); the rest wait for the next read.
- **Classroom changes a call name or a response shape.** A call not on the allowlist is blocked and
  counted, never sent. A response that cannot be interpreted stops its class with `drift`; an item
  that cannot be interpreted is skipped and listed. Nothing is withdrawn because it was not read
  (spec 001 FR-027).
- **A page tries to press something or open a form.** The browser guard blocks it before it reaches
  Classroom and counts it (constitution IV).
- **Two students.** Each has a profile and a sign-in window of their own; reads run one at a time
  under the Mac's browser lock (FR-021a), and each notice names its student by id.
- **The notice does not arrive.** The read waits its full time regardless; the log shows the wait and
  its outcome.
- **An attachment Drive holds behind its virus-scan notice.** It is noted as not brought, with its
  link, as today (spec 001 research R4).

## Requirements *(mandatory)*

### Functional Requirements

**Where it runs**

- **FR-001**: The read MUST run as alfabeta's own command on [NEEDS CLARIFICATION: the family's Mac,
  as constitution IX stands, or a dedicated always-on machine at home, which needs IX amended
  first?], started by that machine's scheduler, by the launcher or by the family, with no app open
  (the Claude desktop app included) and with no window on screen while it reads.
- **FR-002**: Each student MUST have a browser profile of their own, kept in the student's data
  folder with user-only permissions (constitution II), used only by this read and its sign-in. Its
  session never leaves that machine. The sign-in and the read MUST use the same browser installation,
  so the read can use the session the family started.

**Reading**

- **FR-003**: The read MUST get Classroom's data from the read calls Classroom's own pages make, sent
  from a Classroom page loaded in the student's profile, one call at a time with pauses, as a
  student browsing (constitution IV).
- **FR-004**: The read MUST send only calls whose names are on an allowlist of reads, recorded on
  this account before anything is built (spec 001 spike S6); the peer project's catalogue may seed
  the recording but does not replace it. If reads and writes cannot be told apart by call name on
  this account, this read is not built and the plan says so.
- **FR-005**: Read-only MUST hold by construction (constitution IV), with the guard of spec 001
  research R18 installed in the browser before any page script runs. It blocks, before they reach
  Classroom, every press, every document load outside the read's own pages and the sign-in page,
  every call not on the allowlist, and every request to a form or quiz host. Downloads are allowed
  only for the attachments this read itself listed in this run, through the routes of spec 001
  research R4. Every blocked item is counted, and the counts go into the log.
- **FR-006**: Before any call, the read MUST check that the account signed in to the profile is the
  student's configured school account; another account stops the read with `wrong_account`, with
  nothing read.
- **FR-007**: The read MUST leave the capture spec 001's apply step consumes (classes, topics,
  items, statuses, modification marks, attachments), so planning, applying, replicas, mirrors and
  the agenda work unchanged. What needs judgement (a class not yet linked to a subject, a new topic
  match, an exam candidate; spec 001 R7) MUST NOT be decided by this read: it is left pending,
  counted in the result notice and decided in the family's next session with Claude (FR-021b);
  what is already decided is applied.
- **FR-008**: A response the read cannot interpret MUST stop only its class, with `drift`, and an
  item that cannot be interpreted MUST be skipped and listed; the other classes go on, and nothing is
  withdrawn because it was not read (spec 001 FR-027). A course list that cannot be read stops the
  read with `drift`.
- **FR-009**: When the session ends in the middle of a read, the classes already read MUST be applied
  as `partial` with `session_expired` (FR-021a's rule).

**Signing in**

- **FR-010**: A read that finds the profile's session expired MUST open a browser window on the
  machine's screen, in the student's profile, on Google's sign-in for the school account, and MUST
  wait for the sign-in up to `schedule.wait_minutes` (spec 001 FR-021a), renewing the read's lock
  while it waits. When the session answers, it MUST close that window and read in the background.
- **FR-011**: alfabeta MUST NOT type, fill or submit anything on a sign-in page: the family types
  everything (constitution III). A check a human must clear, beyond what the family typed, stops the
  read with `challenge` and is reported once; nothing is typed to get past it (constitution IV).
- **FR-012**: The family MUST be able to complete the sign-in from the phone through a remote view of
  the machine's screen given by a service of the family's own Google account, including unlocking
  the machine with its password, which they type themselves and alfabeta never stores.

**Telling the family**

- **FR-013**: When a read starts waiting for a sign-in, it MUST send the family a notice that reaches
  the phone through the family's own Google account (constitution III): an email to the account the
  configuration names for notices, or an event with an immediate reminder on a calendar of that
  account; the plan picks one. The notice is in Spanish, names the student only by its id and says
  until when the sign-in waits. The macOS notification of FR-021a is shown as well.
- **FR-014**: When a read ends, it MUST send one result notice the same way, with counts only:
  classes read, new and changed items, attachments brought and not brought, decisions left pending,
  items blocked by the guard, and the stop reason if any. No notice, log line or URL MAY carry a
  name, an email address or the title of anything in Classroom (constitution III).

**Launching**

- **FR-015**: A read MUST start at the times `[schedule]` sets for each weekday, only if the
  machine is awake; a time missed while it slept is logged and not made up outside those hours.
- **FR-016**: The family MUST be able to start a read at any time with one command, and by opening a
  launcher on the machine that does the same, so it can be opened from the phone through the remote
  view.
- **FR-017**: A launch while a read for that student is running or waiting for its sign-in MUST NOT
  start another; it tells the family one is under way (the browser lock of FR-021a).
- **FR-018**: The full sync launched with a request to Claude (FR-021a) MUST keep working. Whether
  it uses this read instead of the Claude extension is for the plan.

**Configuration and records**

- **FR-019**: Every new key this spec adds (the account for notices, the launcher) MUST be declared
  in `config/template.toml` with a `changeme` value (template mirroring, constitution II), and no
  key MAY hold a password, a cookie or an address of the student's.
- **FR-020**: Every read MUST leave one log line with what started it (schedule, launcher, command,
  Claude), how long it waited for the sign-in, its stop reason, its counts and the guard's blocked
  counts (constitution V).

### Key Entities

- **Read profile**: the browser profile kept for one student's read; holds the school session after
  the family signs in; lives in the student's data folder.
- **Read allowlist**: the names of Classroom's read calls the read may send, recorded on this
  account; anything else is blocked.
- **Sign-in wait**: one read's wait for the family's sign-in: when it started, until when it waits,
  how it ended (`signed_in`, `session_expired`, `wrong_account`, `challenge`).
- **Notice**: a message to the family's phone through their Google account, of two kinds: a sign-in
  is waiting (student id, deadline) or a read ended (student id, counts, stop reason).
- **Capture**: what the read leaves for spec 001's apply step, in spec 001's format.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Over 10 consecutive school days, at least 9 scheduled reads that the family signs in
  to from the phone update the topic folders with nobody at the Mac and the Claude app closed.
- **SC-002**: From opening the sign-in notice on the phone to finishing the sign-in takes the family
  under 2 minutes in the usual case.
- **SC-003**: A read of all the student's classes finishes within 30 minutes of the sign-in, inside
  the hour the session lasts (R20).
- **SC-004**: Over those reads, nothing is pressed, no form or quiz is opened, and every call outside
  the allowlist is blocked and counted; in the offline test, a planted press, a planted form link and
  a planted write call are all blocked and never reach the fake server.
- **SC-005**: For the same classes on the same day, this read and the current extractor give the
  same items, identifiers, statuses and attachments, and a second apply writes nothing.
- **SC-006**: No notice, log line or URL from these reads contains a name, an email address or a
  Classroom title (the guardrail, and a test over the notices).

## Assumptions

- The machine that holds the session is awake with the family's user session logged in at the
  scheduled times, the condition spec 005 already accepts for the Mac.
- The family sets up, once, a remote view of that machine on the phone through a service of their
  own Google account (Chrome Remote Desktop).
- The read's pages, call names and response shapes are those of the same Classroom web app the peer
  project documents; spike S6 checks them on this account before building.
- Reading all classes through calls is faster than the hidden-iframe extractor (14 minutes for 12
  classes, spec 001 research R4), which leaves room inside the hour.

## Dependencies

- **Spec 001**: the capture format and apply step, FR-021a's lock and sign-in wait (#163), FR-027,
  research R4 (downloads), R7 (judgement), R18 (the browser guard) and spike S6 (the allowlist).
- **Spec 004**: the family's Google connection, through which the notice is sent.
- **Constitution**: II (the profile in the data folder), III (no third party, the family types the
  sign-in), IV (read-only by construction, no evasion), IX (where it runs, FR-001).
- **The peer project**: lifecoderua/classroom-advisor (MIT), credited in the plan.
