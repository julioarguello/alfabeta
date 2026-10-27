# Feature Specification: alfabeta's own Google connection (Calendar and Drive)

**Feature Branch**: `docs/30-spec-004-google-connection` (spec dir `004-google-connection`)

**Created**: 2026-10-27

**Status**: Draft

**Input**: Operator's decisions (translated from Spanish and condensed): "alfabeta gets its own
connection to Google, not the chat's. Create the Google Cloud project with my work account and link
the other accounts, in this case my son's Gmail. Use it for Calendar, so that each event carries its
own notifications for him and none for me. Use it for Drive as well, done properly: today it syncs
through Drive for desktop, a bit carelessly."

## Context and scope

alfabeta writes to Google today through two borrowed paths:

- **Calendar:** the chat's Google Calendar connector, which is bound to one Google account, the
  operator's work account, and works only while a conversation is open.
- **Drive:** Google Drive for desktop, which uploads the student's folder on the Mac whenever it
  can, and tells alfabeta nothing about whether a file reached the cloud.

Spec 003 (julioarguello/alfabeta#28) needs reminders that ring for the student. A Calendar reminder
belongs to the account that sets it. Measured 2026-10-27: a reminder of 37 minutes, set on a test
event by the account that writes today, reached neither the student's school account nor the
owner's account; both event pages read «Las notificaciones solo se aplican a ti». alfabeta can only
set the student's reminders by acting as the student's account.

The scheduled sync (julioarguello/alfabeta#13) needs the same thing: a way to write to Google with
no conversation open.

This spec gives alfabeta its own registered connection to Google, which accounts the family links
to it, what each account allows it to do, where the authorisation is kept, and how a lost
authorisation is noticed. It is tracked in julioarguello/alfabeta#30.

Out of this spec:

- The school account. Its administrator blocks unconfigured third-party apps for users designated
  as under 18 (Google Workspace admin help, read 2026-10-27).
- Gmail, Google Tasks and any other Google service. A scope is added only when a spec needs it.
- Gemini Notebook, which has no public API and keeps its own tool (spec 002).
- What the calendar holds and when reminders ring (spec 003).
- How Classroom is captured (spec 001).

**Constitution.** Principle VII says the student's folder on the Mac is the base output and that
"alfabeta only writes in the folder", which a sync client then uploads. Writing to Drive directly
amends that sentence. The folder stays the base output; Drive becomes an output alfabeta writes and
checks itself (FR-012). The constitution is amended to 1.5.0 in the same pull request as this spec.

## Clarifications

### Session 2026-10-27

- Q: Which Drive permission? → A: The whole Drive (`drive`), so alfabeta adopts the tree that Drive
  for desktop already created instead of rebuilding it. Accepted cost: it is a restricted scope, and
  it grants access to everything in a minor's Drive. alfabeta limits itself to the alfabeta folder
  (FR-009a); Google does not enforce that limit.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The family links the student's Gmail once (Priority: P1)

The operator, with the control he has over his son's account, signs in as the student's Gmail once
and accepts what alfabeta asks for. From then on alfabeta acts as that account with no one present.

**Why this priority**: nothing in spec 003 rings for the student without it.

**Independent Test**: run the linking step, then a run with no conversation open that reads the
student's calendar list as that account.

**Acceptance Scenarios**:

1. **Given** no account linked, **When** the operator runs the linking step, **Then** a Google
   sign-in opens in the browser, the operator signs in as the student's Gmail, Google shows the
   unverified-app screen and the consent screen, and alfabeta stores the result without anyone
   typing or copying a credential.
2. **Given** a linked account, **When** a run starts with no conversation open, **Then** it acts as
   that account and says which account it is acting as, by its configured alias, never its
   address.
3. **Given** the student's school account is chosen at sign-in, **When** linking ends, **Then**
   alfabeta refuses it and says that the school blocks it.

---

### User Story 2 - A reminder set by alfabeta rings on the student's phone (Priority: P1)

**Why this priority**: it is the reason for the connection, and the only proof that spec 003 can
work.

**Independent Test**: as the student's Gmail, create a test event in the family calendar with one
reminder ten minutes ahead; the family watches the phone; the event is deleted after.

**Acceptance Scenarios**:

1. **Given** a linked Gmail, **When** alfabeta creates an event with a reminder, **Then** the same
   event read as the operator's account shows no reminder of the student's.
2. **Given** the test event, **When** the reminder time comes, **Then** the student's phone shows
   the notification, and the family records the date it was seen (spec 003, FR-019).

---

### User Story 3 - Files reach the student's Drive, and alfabeta knows they did (Priority: P2)

Today a file written into the folder on the Mac may reach Drive minutes later, hours later, or not
at all, and nothing says which.

**Why this priority**: the study material is the product; a run that says "done" while a file is
still on the Mac misleads the family.

**Independent Test**: one run over a topic folder; compare, file by file, what the run reports as
uploaded with what Drive holds.

**Acceptance Scenarios**:

1. **Given** a new file in the student's folder on the Mac, **When** the run uploads it, **Then**
   the run reports it as uploaded only after Drive confirms it, and a second run uploads nothing.
2. **Given** an upload that fails, **When** the run ends, **Then** the file is listed as not
   uploaded, the other outputs completed, and the next run retries it.
3. **Given** the folder tree that Drive for desktop already created, **When** the connection is
   switched on, **Then** no file in Drive is duplicated or lost (FR-010).

---

### User Story 4 - A lost authorisation is loud, never silent (Priority: P1)

An authorisation can stop working: the account revokes it, it goes six months unused, Google
invalidates it. If it fails quietly, the reminders stop and the family believes they still ring.

**Why this priority**: the incident the operator said the family cannot afford again is exactly
this one: a warning that was expected and never came.

**Independent Test**: revoke the authorisation from the student's Google account settings, then
run.

**Acceptance Scenarios**:

1. **Given** a revoked or expired authorisation, **When** a run starts, **Then** it writes nothing
   to Google, says which linked account failed and what to run to link it again, and exits with a
   status that the schedule reports as a failure.
2. **Given** that failure, **When** the run ends, **Then** the operator learns that the student's
   reminders are off through a channel that does not need the failed link (FR-014).

---

### Edge Cases

- **The app left in Testing.** Google issues refresh tokens that expire after 7 days when an
  External app is in Testing and asks for more than basic profile scopes (Google OAuth 2.0 docs,
  read 2026-10-27). The app MUST be published before the first real link (FR-003).
- **More than 100 refresh tokens** for one account and one client: Google invalidates the oldest. A
  re-link replaces the stored token, it never adds a second one. Spec 005 adds one more link of the
  same account for its cloud run, stored only there: two tokens, one per place, each replaced only
  by a re-link in its own place.
- **The operator's work account changes or leaves the organisation**: the project and every
  authorisation go with it. The run says so as in User Story 4.
- **An organisation policy in the work account forbids External apps**: the project cannot be
  created as needed; linking stops with that reason.
- **Supervision**: if the student's Gmail is supervised with Family Link, Google may ask a parent to
  approve the app; the operator is that parent.
- **The student changes the Gmail password**: Calendar and Drive authorisations survive it (only
  Gmail scopes are revoked on a password change, per the same Google docs).

## Requirements *(mandatory)*

### Functional Requirements

**The project and the app**

- **FR-001**: alfabeta MUST have its own app registered in a Google Cloud project created with the
  operator's work account. The repository holds only how to create it and a template of its
  configuration, never its client secret or identifiers.
- **FR-002**: The app's audience MUST be External: an Internal app admits only accounts of the
  work organisation, and the student's Gmail is not one (Google Cloud help 15549945, read
  2026-10-27).
- **FR-003**: The app MUST be published, never left in Testing, and runs under Google's personal-use
  allowance: fewer than 100 users, all known to the operator, with the unverified-app screen shown at
  sign-in (Google Cloud help 13464323, read 2026-10-27). No verification is requested.

**Accounts and what each allows**

- **FR-004**: The accounts linked MUST be listed in the student's private configuration by alias
  and role. The first is the student's personal Gmail, role `student`. The operator's accounts are
  not linked unless a later spec needs them.
- **FR-005**: Each linked account MUST be asked only for the scopes alfabeta uses: Calendar events,
  to create, update and delete events and their reminders as that account; Drive, as FR-009
  decides; and `openid` and `email`, which only identify the account that was linked (FR-006). A scope is added only by a spec that needs it, and adding one means linking again.
- **FR-006**: The school account MUST be refused at linking.

**Where the authorisation lives**

- **FR-007**: The refresh token MUST be kept in the system keychain, one entry per linked account,
  and never in the repository, the configuration, a log or an error message. The client secret is
  kept the same way. Amended by spec 005 (constitution II, 1.6.0): the cloud run's own link keeps
  its token and the client in the alfabeta project's secret store; the Mac's token never leaves
  the keychain.
- **FR-008**: Linking MUST open Google's own sign-in in the browser. alfabeta never sees or types a
  password (constitution III).

**Calendar**

- **FR-008a**: Calendar writes MUST go through the linked student account, onto the family calendar
  the operator owns and shares with that account with permission to make changes to events.
  Reminders set this way are the student's own; Google allows at most 5 per event, each between 0
  and 40,320 minutes ahead (Calendar API events reference, read 2026-10-27).
- **FR-008b**: Once the connection works, the chat connector's account MUST stop writing to the
  calendar, and its access to the calendar is removed. One writer, one record of who wrote what.

**Drive**

- **FR-009**: Drive access MUST be the whole Drive (`drive`, a restricted scope; Google Cloud help
  13464325, read 2026-10-27), under the personal-use allowance of FR-003. alfabeta adopts the
  existing tree as it is.
- **FR-009a**: Every Drive read and write MUST stay inside the alfabeta folder that the student's
  configuration names (its id, resolved once). A call outside it is refused by alfabeta's own Drive
  adapter, and a test asserts that no call leaves the folder. The scope allows more; alfabeta does
  not use it. Amended by spec 005: Drive's change feed has no folder filter (only `spaces` and
  `restrictToMyDrive`), so reading it is the one account-wide read. The adapter drops every change
  outside the allowlist before returning, and nothing about a dropped change is kept or logged; the
  scope test covers the feed too.
- **FR-010**: Switching Drive on MUST NOT duplicate or lose a file. A one-off migration matches each
  file in the folder on the Mac with the file Drive already holds at the same path, by size and
  checksum. It adopts the matches, uploads what Drive lacks, and reports both lists plus any file
  that differs. Nothing is deleted by the migration.
- **FR-011**: Once the migration is reported clean, alfabeta MUST stop writing inside the folder
  Google Drive for desktop mounts. Drive for desktop cannot exclude one folder in streaming mode
  (research R7), so the operator moves the student's base folder out of the mount, and every run
  refuses a base folder inside it. The mount keeps showing the Drive copy; anything written there
  by hand bypasses alfabeta's upload records.
- **FR-011a**: Leaving the mount MUST NOT stop what the mount used to bring. Added by spec 005
  (julioarguello/alfabeta#44, constitution VII 1.6.0): every sync first pulls into the master what
  Drive holds under a topic folder, outside the cloud run's state folder, with its own change
  cursor. A Drive id with no upload record is downloaded and recorded `adopted`; a recorded id with
  a new Drive version overwrites the master copy only if that copy's md5 still equals the last
  pulled version, else it is written beside it with « (de Drive)» and reported; a file whose md5
  the master already holds at that path is recorded and not copied. A rename in Drive renames the
  master copy when that copy is unchanged since the last pull. Nothing is deleted in the master. The
  pull takes the student's lock like every writer (spec 001), never renames or renumbers a file the
  placer wrote, and its « (de Drive)» copies are never pushed back. This MUST ship before the base
  folder leaves the mount. Other specs cite it as "spec 004 FR-011a", because spec 001 has an FR-011a
  of its own.
- **FR-012**: A file MUST count as uploaded only when Drive confirms it with the same size and
  checksum as on the Mac. An upload is idempotent: a second run with nothing new uploads nothing.

**Failure**

- **FR-013**: A run MUST check every linked account before writing anything. A failed one stops
  the outputs that need it, lets the others complete (constitution VII), and exits with failure.
- **FR-014**: When the student's link fails, the family MUST learn it on a channel that does not
  depend on that link: the run's own report and exit code, a notification on the family's Mac, and
  a line in the agenda (research R9).
- **FR-015**: Every run MUST use each refresh token at least once, so none reaches six months
  unused.

### Key Entities

- **App**: the registered client in the Google Cloud project — audience, publishing status, scopes.
- **Linked account**: an alias, a role (`student`), the scopes granted, the date it was linked, and
  a keychain entry. Never its address in logs.
- **Authorisation check**: per run and per account — ok, revoked, expired, or missing a scope.
- **Upload record**: a file's path in the student's folder, its Drive id, size and checksum, and the
  run that confirmed it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After one linking, 30 consecutive daily runs with no conversation open write as the
  student's Gmail with no new sign-in.
- **SC-002**: A reminder set by alfabeta as the student rings on his phone, seen and dated by the
  family; the same event shows no reminder of his when read as the operator.
- **SC-003**: A run after the authorisation is revoked writes 0 events and 0 files, names the
  account by alias, and is reported as failed by the schedule.
- **SC-004**: After the Drive migration, every file in the student's folder on the Mac is in Drive
  exactly once, checked by size and checksum, and the report lists 0 missing and 0 duplicated.
- **SC-005**: A second run with nothing new uploads 0 files and changes 0 events.
- **SC-006**: A search of the repository, the logs and the run reports for the student's address,
  the client secret and any token finds nothing.

## Assumptions

- The student's personal Gmail is not supervised, or the operator approves the app if it is. In
  Spain the age for managing one's own Google Account is 14 (Google Accounts help 1350409, read
  2026-10-27).
- The Calendar and Drive APIs need no billing account for this volume.
- No organisation policy of the work account forbids an External app; if one does, the operator
  changes it in the admin console or the plan moves the project.
- The family calendar keeps its owner, the operator's Gmail; only its writer changes.
- Whether a token from a published, unverified app stays valid beyond seven days is inferred from
  Google's docs, which tie the seven-day expiry to Testing only; SC-001 measures it.

## Dependencies

- The operator, to create the project, publish the app, sign in once as the student's Gmail, share
  the calendar with that account, and stop Drive for desktop syncing the folder.
- Spec 003 (julioarguello/alfabeta#28) and the scheduled sync (julioarguello/alfabeta#13) depend on
  this spec.
