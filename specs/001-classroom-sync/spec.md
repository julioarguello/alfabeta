# Feature Specification: Each subject's content, from Classroom to the family's Drive, with per-student configuration

**Feature Branch**: `docs/1-spec-001-classroom-sync` (spec dir `001-classroom-sync`)

**Created**: 2026-10-25

**Status**: Draft

**Amended**: 2026-10-27 — reading Classroom with nobody present, without the operator's Mac or
browser (User Story 7, julioarguello/alfabeta#2): a token route (primary) or a scripted web sign-in
(fallback), using a vault; constitution 2.0.0 (principle III redefined).

**Input**: User description (translated from Spanish): "alfabeta epic 1: classroom-sync + folder structure + per-student configuration. Problem: a secondary-school student's study material is spread between Google Classroom (materials, assignment attachments, links, announcements and assignments with dates, organised by each teacher into topics inside «Trabajo de clase» (Classwork)) and the digital textbook (Science Bits). Nothing is where the student studies, and the family cannot see at a glance what is pending. (1) Per-student configuration: template in the repo → private configuration outside the repo → data and secrets in a local data folder and the keychain; a second student only needs another configuration; a guardrail that prevents pushing real data. (2) Access path: the desktop app's built-in browser, read-only, with the student's session; the API is ruled out. (3) Rules: read-only on Classroom, the minor's data kept to the minimum, no tool types credentials." Operator's change of approach (2026-10-25): "We do not sync Classroom, we sync the subject's content: first level the school year, then the subject and then topic or month; inside, `classroom` or `sciencebits`, and the Classroom file name includes the date. The scraper walks Classroom; what I care about most is reminders of what is pending, and that the problems and exercises they keep assigning get downloaded and placed in the right spot of the Drive. I want a replica of the document the teacher posts in our Drive, to combine it with the books we download (Science Bits for now) and have it all go to the notebook together. We do it with the family Drive; the student has a personal Gmail account."

## Context and scope

This epic is the first of three:

1. **This one**: each subject's content reaches the family's Drive with a structure common to every
   source (Classroom and the books), plus an agenda with exams, assignments and what gets
   posted.
2. **Reminders**: the agenda moves to a calendar with alerts, one colour per category (FR-020a;
   colours proposed in Assumptions),
   and Google Tasks is evaluated so the student can mark assignments as done from the calendar.
   It is fed by this epic's agenda.
3. **«Prepárame el tema»** ("prepare the topic for me"): everything in a topic's folder, from every
   source, goes to its Gemini Notebook notebook.

Out of this epic: reminders, notebooks, replicating material without the family's Mac, and book
providers other than Science Bits. Reading Classroom with nobody present is in (User Story 7): it
replaces the local MCP design of julioarguello/alfabeta#2.

## Clarifications

### Session 2026-10-25

- Q: Does the pending-items document also include the exams the teacher announces on the stream or
  in a material, or only Classroom's dated assignments? → A: It includes the exams. Every dated item
  is classified into a closed category (exam, assignment, quiz, material, announcement) so the
  reminders epic can tell them apart at a glance in the calendar; the document becomes an agenda.
- Q: What does a subject's first sync bring: everything posted since the start of the school year,
  or only since a recent date? → A: Everything in the current school year, retroactively. What was
  already turned in or returned appears as done according to the status Classroom shows, and the
  agenda opens with a checklist of what is pending, nearest first, for the student to review on
  getting home (FR-020c).
- Q: Are the files the student turned in for each assignment also replicated? → A: Yes, next to the
  statement and the grading, and clearly told apart in the Drive: each assignment is a folder with
  `enunciado`, `entrega` and `correccion` (FR-015a).
- Q: Where is the material written: only to the family Drive, or also to the previous cloud
  (Dropbox)? → A: Only to the family Drive, which is the sync target. Dropbox is out of this
  epic: it is not read, not written, and what is already there is not migrated.

### Session 2026-10-26

- Q: How are topic folders and Classroom items named, now that the operator has seen the
  `Tema PNN` and `YYYY-MM` folders in the Drive? → A: Every topic folder and every Classroom item
  starts with a date, so the student places each one in time; a `2026-09` folder under a subject
  read as a second school year. The operator decided it and the family's Drive was migrated to it
  by hand on 2026-10-26 (constitution 1.3.0). It replaces the topic, month and item names of the
  2026-10-25 session (FR-012 to FR-015):
  - A topic folder is `YYYYMMDD - <name>`, where the date is the posting date of the topic's first
    Classroom material. `<name>` is `Tema NN - <title>` when the topic matches a book topic
    (`20261001 - Tema 01 - Sustancias puras y mezclas`) and the teacher's title alone when it does
    not (`20260910 - 0.- ZIENTZIA ETA NEURKETAK`). `Tema PNN` is dropped, and with it the
    `teacher_topic_number` decision that fixed its `NN`.
  - There are no month folders. What Classroom posts with no topic, announcements included, goes in
    the subject's `YYYYMMDD - Sin tema`, dated by the first item placed there.
  - Every item inside `classroom/` is `YYYYMMDD - <title>` (it was `YYYY-MM-DD - <title>`).
  - A folder's date is set when the folder is created and never changes: alfabeta finds an existing
    folder by the part of its name after the date, whatever the date, and reuses it. A topic folder
    created by a book provider before any Classroom material takes the date of that day.
  - Inferred, not stated by the operator: a teacher's topic whose match with a book topic is not yet
    confirmed waits in its own `YYYYMMDD - <teacher's title>` folder, like a teacher-only topic,
    and its replicas move when the family confirms the match; `Sin tema` is only for items
    Classroom leaves without a topic.
- Q: The student has a personal Gmail account and a school Google Workspace for Education
  account. Which one does the material reach? → A: Both. The operator decided it on 2026-10-26, and
  the first mirror copy was made by hand that day. Every target takes a list of accounts instead of
  one (FR-011a, FR-011b):
  - Drive: one master folder (`drive.root`, in the personal account's Drive) plus a list of one-way
    mirrors (`drive.mirrors`), each a folder in another account's Drive, mounted by Google Drive for
    desktop on the same Mac. After every sync each mirror is brought up to date from the master.
    Mechanism measured on the family Mac on 2026-10-26: `rsync -rlt --exclude .DS_Store
    <master>/ <mirror>/`, without `--delete`. A mirror is never edited back into the master.
  - Calendar: the one calendar is shared with every account in `calendar.shared_with`, each with
    permission to see all event details.
  - Notebooks: each topic notebook is shared as viewer with every account in
    `notebook.share_with`.
  - Measured 2026-10-26: the school domain allows a notebook owned by a personal Gmail account to be
    shared with the school account as viewer, and it opens there; a calendar shared from a personal
    account can be added in the school account and shows its events. Both depend on the school's
    admin settings and are checked again if the school changes them.
  - Today's `config.example.json`, read by the Science Bits skill until it moves to this template
    (FR-022), carries the same lists as `storage.mirrors`, `calendar.shared_with` and
    `notebook.share_with`.

### Session 2026-10-27

- Q: How is Classroom read with nobody present, without the operator's Mac and without the
  operator's browser? The operator's evidence: a manual read on 2026-10-27 found two assignments
  of one subject, posted that morning, that the capture of 2026-10-26 had missed. The operator does
  not want their own browser used, wants the read to run without their Mac, asks for it to be
  specified now and built later, and left the mechanism to the team («no te quiero condicionar,
  dime tú»). Their proposal: a browser alfabeta drives by itself (headless, not their Chrome) with
  the student's credentials kept in a vault; and, on the constitution, «me da igual que rompa la
  constitución, pues la cambiamos». → A: an **unattended runner** (User Story 7): a job scheduled in
  the family's cloud project that reads Classroom for the student, never Claude and never the
  operator's Chrome or Mac. It signs in with a secret the family placed in a **vault** once, and
  constitution III is amended (MAJOR, 2.0.0) to permit that. Two routes, because the first may not
  work and is proven by a spike before anything is built (research R15 to R17):
  - **Primary — the token route.** The family signs in by hand once to seed a long-lived sign-in
    token for the school account into the vault; the runner exchanges it for short-lived access
    tokens and reads Classroom as a Google first-party client would. The school's block on the
    Classroom API hits third-party developer clients (`docs/classroom-investigacion.md`); the
    student's school account works in the Classroom app on an Android phone (operator, 2026-10-27),
    so a first-party client may reach it where our own client cannot. It escapes the web session's
    short life. Its risks, which the family accepts in this review: it poses as a first-party app,
    which is against Google's terms; it shows as a new device on the account; the stored token is
    account-wide and bypasses the second factor (read-only is only the scope requested from the
    derived tokens), so the stored secret is at least as sensitive as the password and a vault read
    exposes the whole account; and the API may be blocked for a minor's account at the policy level,
    not just for third-party clients, in which case the route fails. Spike S4 decides it with one
    read-only call.
  - **Fallback — the scripted web sign-in.** The vault holds the password and the second-factor
    seed; when the stored browser session has expired, a deterministic script signs in and the
    runner reads the to-do pages in a headless browser (FR-034). Its risks, which the family
    accepts: Google refuses sign-in from automated browsers, so it may never work without evasion,
    which is barred (constitution IV); and repeated sign-ins on a minor's account risk a lockout.
    Spike S5 decides whether it works at all without evasion.
  - Two hard limits hold on both routes, whatever the constitution says (research R15): Claude never
    runs a sign-in and never types a credential — it writes the deterministic script, the scheduled
    job runs it; and no stealth tooling, debug-port hiding, fingerprint spoofing or CAPTCHA solving
    is used — a sign-in that needs any of that stops and the family is told (FR-033, FR-037).
  - **Last resort** if both routes fail: the guardian email summaries (`docs/roadmap.md`, route 2).
- Q: What does the runner read? → The student's pending work and its dates. The token route reads it
  from the API; the web route reads the to-do pages that the operator's manual read of 2026-10-27
  found enough: «Tareas pendientes» (`/u/<n>/a/not-turned-in/all`, sections «Sin fecha», «Esta
  semana», «Próxima semana» and «Más tarde», each collapsed behind its header button), «Sin
  entregar» (`/u/<n>/a/missing/all`, with a «Ver todo» button), and the detail page of each
  assignment they list (`/u/<n>/c/<class>/a/<item>/details`), for its instructions and its
  due date («Fecha de entrega: Mañana, 8:00»). Not the stream, the materials or the attachments,
  which stay in the full sync (FR-034).
- Q: What does it write, with no Mac? → Its data home and the agenda, written to Drive through
  alfabeta's own Google connection (spec 004), and the calendar once spec 003 is built. No replica:
  material keeps reaching the Drive through the master folder on the Mac (FR-036).
- Q: How long does the school session last, and what about «Demuestra que eres tú» ("verify it's
  you")? → The operator says the school's web session lasts «como máximo una hora» (not measured);
  a session a school shortens shows that page (`accounts.google.com/…/confirmidentifier`, seen
  2026-10-27 before Classroom opened) when it ends (research R16). A session that short is why the
  web route needs a stored credential to sign in again, and why the token route (not tied to the
  web session) is preferred. In the web route a sign-in page is where the scripted sign-in runs; a
  challenge that needs a human (CAPTCHA, «unusual traffic», a check that the browser is automated)
  stops the run, and the family is told once (FR-037). How often each happens, and whether a cloud
  address makes it worse, is measured by spikes S4 and S5 before anything is built (SC-012).
- Q: Against what moment are relative dates resolved? → Against the moment the page that shows
  them was read, not the start of the capture: a read can cross midnight, and the manual capture
  of 2026-10-26 placed a bare «8:00» (which means today at 8:00) on the wrong day. Each detail page
  carries its own read instant (FR-021).
- Q: Does the family accept the risks this amendment asks them to carry — custody of the vault
  secret by the cloud project's administrators (II), the terms-of-service risk of automated access
  to a minor's account (R15), and that the token-route secret is account-wide and bypasses the
  second factor, so a vault read exposes the whole account (FR-032a)? → A: Yes. The operator
  accepted all three on 2026-10-27, knowing the stored token is at least as sensitive as the
  password, and asked for the amendment to be merged. This is the explicit, eyes-open request the
  constitution's Development workflow requires to merge a change that weakens NON-NEGOTIABLE
  principles III and IV; it is quoted with its date in the pull request.

### Session 2026-10-28

- Q: In which language are the folders alfabeta names, now that the repository is public? → A: In
  English, as constants (constitution 2.2.0, issue #110, decided by the family on 2026-10-28). What
  Classroom posts with no topic goes in `YYYYMMDD - No topic` (it was `Sin tema`) and what the
  student turned in goes in the assignment's `submission/` (it was `entrega/`, FR-015a). File
  names keep their language (`enunciado - `, `correccion.md`, `enlaces.md`, `descripcion.md`), and
  so do the titles taken from Classroom and the textbook. The sessions above keep the names they
  used then. Classroom's own heading for posts with no topic is still «Sin tema» on its pages.

## User Scenarios & Testing *(mandatory)*

The actors are **the family** (the parent who configures and launches alfabeta), **the student**
(signs in to Classroom and studies with what ends up in their shared folder) and **the teachers**
(post in Classroom; never interact with alfabeta).

### User Story 1 - What the teacher posts, replicated in the folder of its topic (Priority: P1)

The family asks to sync a subject. With the Classroom session the student already started,
alfabeta walks that class's «Trabajo de clase» and leaves a replica of every material and every
assignment attachment (the problems and exercises the teacher sets) in the `classroom` subfolder of
its topic or, if the teacher gave it no topic, of the subject's `No topic` folder. Each file is
prefixed with the date it was posted. What is not a file (a video, a web link, a quiz) is noted with its link. At the end,
the family sees a summary of what was saved and what was not, and why.

**Why this priority**: it is what the operator asks for first: the teacher's material in the right
place, ready to study and to combine with the book.

**Independent Test**: with a test student configuration and a class with two topics, a material
without a topic and attachments of the usual kinds (PDF, Google document, presentation, video, link,
form), sync the subject and check item by item, against what the student sees in
«Trabajo de clase», that each one is in its folder with the date in front or noted with its link.

**Acceptance Scenarios**:

1. **Given** a configured subject and the student's session started, **When** the family asks to
   sync it, **Then** the materials and assignment attachments of each topic are in
   `<topic>/classroom/`, each item named `YYYYMMDD - <title>` (file or folder according to
   FR-015), where the date is the posting date.
2. **Given** a material without a topic posted on 3 March, **When** it is synced, **Then** it ends
   up in its subject's `<YYYYMMDD> - No topic/classroom/` as `YYYY0303 - <title>`.
3. **Given** an attachment that is a Google document, presentation or spreadsheet,
   **When** it is synced, **Then** its replica is saved as a PDF.
4. **Given** an item with a video, a web link or a form, **When** it is synced,
   **Then** a note is left with its title, its date and its links, without downloading anything or
   opening the form.
5. **Given** the Classroom session expired or not started, **When** the family asks to sync,
   **Then** alfabeta stops before reading anything and asks the student to sign in.

---

### User Story 2 - The student's agenda: exams, assignments and what gets posted, in a single document (Priority: P1)

The family wants to see at a glance what the student has ahead and what has been posted. After
syncing, the school-year folder holds an agenda with everything dated in the configured
subjects, each with its category: exams (including those the teacher only announces on the
stream or in a material), assignments, quizzes, new material and announcements. Pending items carry
their status and everything carries the link to its folder. The same content exists in a format a
tool can read: it is the input of the reminders epic, which will paint each category in a colour.

**Why this priority**: it is what interests the operator most (the reminders, and exams above
all) and the basis of epic 2.

**Independent Test**: with test items of every category (an assignment due this week, another
without a date, another overdue, a quiz, an exam that is an assignment, an exam announced only on
the stream, a material and an announcement), sync and check that the agenda lists them all, in
order, each with its category and, for pending ones, with its status.

**Acceptance Scenarios**:

1. **Given** pending assignments in several subjects, **When** it is synced, **Then** the agenda
   lists them sorted by date, with subject, category, title, date, status, Classroom link and
   link to its folder.
2. **Given** a stream announcement saying there is an exam on a topic on a date, **When** it is
   synced, **Then** the agenda has an exam on that date, marked «detectado» and with a link to the
   announcement it comes from.
3. **Given** a detected exam that the family corrects (another date, or it was not an exam), **When**
   it is synced again, **Then** the agenda keeps the correction.
4. **Given** an assignment without a due date, **When** it is synced, **Then** it appears in a
   «sin fecha» ("no date") section of the agenda.
5. **Given** an assignment whose date has passed and that Classroom shows as not turned in, **When**
   it is synced, **Then** it appears marked as overdue.
6. **Given** a material or an announcement posted today, **When** it is synced, **Then** it appears
   in the agenda on its posting date with its category.
7. **Given** exams, assignments and quizzes, some already turned in and others not, **When** it is
   synced, **Then** the agenda opens with the «Pendiente» list, sorted nearest first and with
   the undated ones last, followed by «Hecho» with what was turned in checked off.
8. **Given** a generated agenda, no change in Classroom and no due or exam date
   between the two captures, **When** it is synced again another day, **Then** the agenda files
   are not rewritten. If a date fell between the two, only that entry's list changes (FR-020c).

---

### User Story 3 - Syncing again without duplicating, and learning what changed (Priority: P2)

A few days later the family syncs again. alfabeta brings only what is new or changed: a
new material, an attachment the teacher edited, a moved due date. It duplicates nothing and
deletes nothing. At the end, the family sees what changed since last time, and every sync
is logged.

**Why this priority**: without this the folder degrades with every use and the family stops trusting
it. It depends on story 1.

**Independent Test**: sync twice in a row without changes and check that the second writes
nothing to the folder; then change a date, edit an attachment, add and withdraw a material in the
test class, sync and check each effect.

**Acceptance Scenarios**:

1. **Given** a recent full sync, no change in Classroom and no due or exam date
   between the two captures, **When** it is synced
   again, **Then** no file in the student's folder is created, modified or deleted and the
   summary says «sin cambios» ("no changes").
2. **Given** a due date moved by the teacher, **When** it is synced, **Then** the agenda
   shows the new date and the summary mentions it.
3. **Given** an attachment of an item that Classroom shows as modified after the last replica,
   **When** it is synced, **Then** its folder has the new version and the previous one is kept beside
   it, identified as previous. An attachment edited only in Drive, with no mark in Classroom, arrives
   in the periodic full review (FR-026).
4. **Given** a material the teacher withdrew from Classroom, **When** it is synced, **Then** its
   replica is kept, marked as withdrawn in the log, and the summary mentions it.
5. **Given** any sync, **When** it ends, **Then** the log records when it started and
   ended, which subjects it walked and which items it added, changed, marked as withdrawn or could
   not fetch.

---

### User Story 4 - The book, in the same structure (Priority: P2)

The Science Bits skill leaves its files in the `sciencebits` subfolder of the same topic where
Classroom leaves its own, inside the family Drive.

**Why this priority**: the operator wants to combine the teacher's material with the books to
take them to the notebook (epic 3). Without a common topic folder, that combination is not possible.

**Independent Test**: capture a test topic with the skill and check that it ends up in
`<school-year>/<subject>/<topic>/sciencebits/` of the family Drive, next to `classroom/` if it
exists.

**Acceptance Scenarios**:

1. **Given** the per-student configuration, **When** a Science Bits topic is captured, **Then** its
   files end up in the `sciencebits` subfolder of that topic's folder.

---

### User Story 5 - A second student without touching the code, and nothing personal in the repository (Priority: P2)

The family wants to use alfabeta with the sibling too. They copy the template, fill in the sibling's
private configuration and sync: the sibling's folder, log and data stay separate from the first
student's. Meanwhile, anyone contributing to the public repository has a guardrail that stops them
from accidentally pushing a real name, email, personal path or identifier.

**Why this priority**: it is a principle of the constitution (I, II and III). It is tested on its own,
with invented students, without Classroom.

**Independent Test**: register two invented students from the template and check that the
repository diff is empty and that their outputs do not mix; plant real-looking test data in a commit
and check that the guardrail rejects it.

**Acceptance Scenarios**:

1. **Given** the repository template, **When** the family creates a second student's
   configuration, **Then** they can sync that student without modifying any repository file.
2. **Given** two configured students, **When** one is synced, **Then** only that student's folder,
   log and data are written.
3. **Given** a configuration missing a key or still holding an example value,
   **When** alfabeta is launched, **Then** it stops before doing anything and names the key, never
   its value.
4. **Given** a change containing a value from a student's real configuration (name, email,
   path or class title), **When** a commit is attempted on a Mac with that configuration, **Then**
   the pre-commit hook, installed when setting up the environment, rejects it and says which file and
   which line, without repeating the data.
5. **Given** a change containing an email, a user path or an identifier with a real shape,
   **When** it goes through continuous integration, **Then** the guardrail rejects it as well.

---

### User Story 6 - Stream, the student's submissions and gradings (Priority: P3)

Teachers also post announcements on the stream (exam changes, extra material) and return
graded assignments with a grade and a comment. alfabeta saves each announcement with its date, its
text and its attachments; and in each assignment's folder, next to the statement, it saves what the
student turned in and the grading (grade and teacher's comment), to review what went wrong with
everything in view.

**Why this priority**: useful for the reminders and for studying, but the material and the due
dates live in «Trabajo de clase». It can wait until the rest works.

**Independent Test**: with two test announcements, one with an attachment, an assignment turned in
and not graded and another returned with a grade and a comment, sync and check that each thing is in
its place with its role recognisable by its name, and that no classmates' comment or name has been
saved.

**Acceptance Scenarios**:

1. **Given** announcements on the stream, **When** it is synced, **Then** each one ends up in its
   subject's `No topic` folder with its date, its text and its attachments, without student comments or names
   of other people.
2. **Given** an assignment the student turned in with files, **When** it is synced, **Then** its
   folder has a `submission/` subfolder holding those files with their own names, next to the
   teacher's `enunciado - <name>`.
3. **Given** an assignment returned with a grade and a comment, **When** it is synced, **Then** its
   folder has a `correccion` with the grading state, the grade if Classroom shows it to the
   student, the teacher's comment and the return date.
4. **Given** an assignment the student turned in again, **When** it is synced, **Then** the new
   submission's files are in `submission/` and an earlier file that changed is kept there as previous.

---

### User Story 7 - Classroom read with nobody present, without the operator's Mac or browser (Priority: P2)

On every scheduled day, with nobody at a computer, alfabeta reads what the student has pending in
Classroom and brings the agenda up to date (and the calendar, once spec 003 builds it), so an
assignment posted in the morning is known that day. It runs in the family's cloud project: the
operator's Mac can be off and their Chrome is never used. It signs in with a secret the family
placed in a vault once. It reads Classroom one of two ways, settled by a spike before anything is
built: the **token route**, reading as a first-party client with a sign-in token in the vault
(primary); or the **web route**, a headless browser that signs in with a scripted step when the
stored session has expired, using the password and second-factor seed in the vault (fallback). When
it needs a sign-in it cannot complete without a person or without evasion, it stops and tells the
family once.

**Why this priority**: it is the operator's need of 2026-10-27: two assignments posted that morning
were missed because reading Classroom depended on someone being at the Mac. It builds on stories 1
to 3 (capture, state, agenda) and on spec 004's Google connection. It depends on a MAJOR amendment
of constitution III (the vault) and is built only if its spikes pass: S4 (the token route) decides
the primary route, and S5 (the web route) the fallback; if both fail, the runner is not built and
the family keeps the Mac route and the guardian email summaries (research R15 to R17).

**Independent Test**: for the web route, a local fake Classroom that serves the synthetic to-do and
detail pages, a fake sign-in page and a fake «Demuestra que eres tú» page: the runner reads the
to-do pages, the agenda matches them, no page load or press leaves the allowlist, a fake CAPTCHA
stops the run with one notice, and the scripted sign-in types the vault's test credential only into
the fake sign-in form. For the token route, a fake token endpoint and a fake read-only API: the
agenda matches the API's items and only read-only scope is requested. No real account is used in a
test.

**Acceptance Scenarios**:

1. **Given** the token route in force and assignments pending for the student, **When** the
   scheduled run fires, **Then** each one is in the agenda with its due date and status read from the
   API, only read-only scope was requested, and nobody was asked anything.
2. **Given** the web route in force, a stored session that is still valid and assignments in
   «Tareas pendientes» and «Sin entregar», **When** the run fires, **Then** each one is in the
   agenda with the due date read from its detail page, and no sign-in was attempted.
3. **Given** the web route and a stored session that has expired (the run lands on a Google sign-in
   page), **When** the run fires, **Then** the scripted sign-in runs once with the vault's
   credential, the read continues, and the renewed session is stored; if the sign-in needs a
   challenge a human would clear, the run stops with `challenge` and the family is told once.
4. **Given** the web route, a detail page reading «Fecha de entrega: Mañana, 8:00» read at 23:59 and
   another reading «Fecha de entrega: 8:00» read at 00:01 in the same run, **When** they are
   applied, **Then** each date is resolved against the instant its own page was read.
5. **Given** an assignment pending in the previous read that is in neither list (web route) or no
   longer returned by the API (token route), **When** the runner reads, **Then** it takes that
   assignment's status from its detail or the API once, or marks it withdrawn if it no longer exists.
6. **Given** a page or a call without the expected shape, or one that passes its time limit, **When**
   the runner reaches it, **Then** the run stops with `unexpected_ui` or `timeout`, applies only what
   it read completely, and never waits indefinitely.
7. **Given** the web route, **When** a run ends, **Then** the browser loaded only the pages and
   pressed only the controls of the allowlist (FR-038); every other attempt was blocked before it
   reached Classroom and is counted in the log; no evasion tooling ran.
8. **Given** the runner enabled for a student, **When** it runs, **Then** no step uses the
   operator's Mac or Chrome, Claude runs no sign-in and types no credential, and the vault holds
   only the minimum for the route in force (a token, or the password and its second-factor seed).

### Edge Cases

- A Classroom class that matches no configured subject: it is not synced, and the
  summary lists it so the family can decide whether to add it.
- The teacher's topics and the book's do not line up: different numbering, a different language, a
  teacher's topic that joins two of the book's or one that does not exist in the book. alfabeta
  proposes and the family confirms (FR-013); until then, that topic's items wait in a folder named
  after the teacher's topic.
- A confirmed match that turns out wrong: the family changes it with the `decisions` command and
  the next sync moves the replicas to their correct folder, without duplicating or
  losing them.
- Two items with the same title and the same date in the same folder, or titles with invalid or
  very long characters: the name is sanitised and, if it collides, disambiguated without losing any.
- A Drive attachment the student has no access to, deleted or too large: it is noted with its
  link and the reason, and the sync goes on.
- A download that does not arrive or arrives incomplete: it is not taken as saved; it is retried in
  the next sync.
- Foreign files in the Mac's downloads folder: alfabeta only collects what it requested.
- The session expires mid-sync: it stops, logs how far it got, and the
  next one continues without duplicating.
- Classroom answers with an anti-bot challenge or a block: the sync of that source
  stops and the family is told; no attempt is made to get around it.
- The Drive folder is not mounted or Google Drive for desktop is disconnected: alfabeta writes
  nowhere else; it stops and says so.
- Google Drive for desktop is still uploading files from the previous sync: no effect,
  because alfabeta writes to the folder on disk.
- A mirror's account is not mounted, or its Drive is full: the master and the other mirrors are
  updated, the summary counts that mirror as failed, and the next sync brings it up to date.
- A replica moves or is renamed in the master (a corrected match, a previous version): the mirror
  receives the new name and keeps the old one, because a mirror is never pruned. A mirror holds at
  least what the master holds, not exactly the same.
- Someone edits or adds a file in a mirror: it is never copied back; if the master changes that
  same file, the next sync overwrites the mirror's copy.
- Two syncs of the same student at once: the second does not start while the first is still running.
- Dates around the summer and winter daylight-saving changes: the date shown is the one Classroom
  shows.
- The runner has no secret in the vault yet, or the family removed it: the run stops with
  `session_expired` before reaching Classroom, and the family is told once.
- The token route's token is rejected, or the API answers that the account is not allowed: the run
  stops with `session_expired` (a dead token) or `account_blocked` (the account is not allowed,
  FR-037), tells the family once, and tries no other client or address.
- Google answers the runner with a CAPTCHA, an «unusual traffic» page, an «unusual traffic» block
  or a «this browser may not be secure» page during the scripted sign-in: `challenge`, stop and one
  notice; no stealth tooling, no proxy and no other address is tried (constitution IV).
- The web route's scripted sign-in needs a second factor beyond the stored seed (a device prompt, a
  code to a phone): it cannot be completed unattended, so the run stops with `challenge` and the
  family is told.
- The runner and an interactive sync on the Mac want the same student at once: the lease in the
  single data home stops the second one (FR-035).
- A to-do section that is already open, or that Classroom stops collapsing (web route): the runner
  reads it as is; a section header or a «Ver todo» it cannot find by its label is `unexpected_ui`.
- A run whose job platform kills it at its time limit: the next run finds the lease idle and
  writes the dead run's `stopped` line, as on the Mac (FR-030).

## Requirements *(mandatory)*

### Functional Requirements

**Per-student configuration**

- **FR-001**: The repository MUST contain a configuration template that documents every key with
  an example value (`changeme` for text; a reasonable number for numbers). It replaces the
  current `config.example.json`.
- **FR-002**: Each student's configuration MUST live outside the repository, and their data and
  secrets (log, sync state, sessions, identifiers) in a local data folder of the student and in the
  system keychain, outside the shared folder. For a student read by the unattended runner (User
  Story 7), the secrets live in the secret store of the operator's cloud project (the vault, FR-033)
  and the data home in a state folder in the student's Drive (FR-035), each outside the shared
  folder.
- **FR-003**: On start-up, alfabeta MUST validate the configuration against the template: a key that
  is missing, extra, changes type or contains `changeme` (anywhere in the value) stops the
  run with a message that names the key and does not show its value.
- **FR-004**: Registering another student MUST require only creating their configuration. Each run
  MUST operate on a single student, chosen explicitly.
- **FR-005**: A guardrail MUST reject, on every commit made on a Mac with student configurations,
  any file containing their real values (names, emails, personal paths) or the
  Classroom, Drive or notebook identifiers kept in their data (decisions and state); and, on
  every commit and in continuous integration (which has no configurations), generic patterns of email,
  user path or identifier shaped like Classroom, Drive or notebook ones (UUID). The domains reserved
  for examples (`example.org`, `example.com`) do not count as real emails. It MUST have test cases
  showing that it fires and that the template passes.

**Reading Classroom, read-only**

- **FR-006**: alfabeta MUST read Classroom with the session the student starts in Chrome with the
  Claude extension. The app's built-in browser is left for a later epic, once attachment download is
  tested in it. For a student with the unattended runner enabled (User Story 7), the scheduled read
  is the runner's — the token route's API calls, or the web route's headless browser (FR-032a,
  FR-032b) — with the secret the family placed in the vault (FR-033); the full sync keeps this
  paragraph. On this interactive route, no tool types credentials; the runner's sign-in is governed
  by the amended constitution III and FR-033.
- **FR-007**: alfabeta MUST NOT turn in, comment, mark as done, change any status or open
  a quiz or a form in Classroom. The only pages it navigates to are: the home
  page (class list), «Trabajo de clase», the stream and the detail page of each assignment,
  material or question, which is only read, and, for the runner's web route, the to-do pages
  «Tareas pendientes» (`/u/<n>/a/not-turned-in/all`) and «Sin entregar» (`/u/<n>/a/missing/all`).
  The only controls the runner's web route presses are, on those two to-do pages, the header button
  that opens a collapsed section and the «Ver todo» (see all) button, each found by its label (and,
  on a Google sign-in page, the web route's own scripted sign-in, FR-032b); any other press by the
  runner is a defect. No route follows a link to a form or a quiz
  (Google Forms or similar) or presses a button in the «Tu trabajo» (Your work) panel. If
  Classroom's interface does not show the expected labels (for example, because it is in another
  language), it stops and says so instead of guessing.
- **FR-008**: alfabeta MUST read the class list (visible, hidden and archived) and, for each active
  class of the current school year and since its start (archived ones are out): the topics of
  «Trabajo de clase» and their items (materials, assignments and questions, with title, type, topic,
  posting date, due date if any, and attachments), each item's detail and the stream
  announcements. Classes hidden by the student are listed in the summary and are only synced if the
  family links them to a subject.
- **FR-008a**: An assignment's status MUST be read from its detail page, not from the
  «Trabajo de clase» listing, because they can disagree (a listing saying «Completada» (Completed)
  while the detail says the teacher marks it as not turned in).
- **FR-009**: alfabeta MUST NOT save student comments or names of other people: the extractor
  drops class and private comments and author fields. The free text the
  teacher writes (instructions, announcements, grading comment) is saved as is; if it names someone,
  alfabeta does not detect it (known limitation).
- **FR-010**: Access MUST be that of a student browsing: one class at a time, at least 2 seconds
  (with random variation) between two pages or downloads, and no evasion. On an anti-bot challenge
  (CAPTCHA, intermediate verification page, too-many-requests error), the sync of
  that source stops navigating and the family is told; the run ends `stopped` with reason
  `challenge` if it had not yet captured any class, or `partial` with that reason, applying the
  classes already captured, if it had (data-model, "Run"). On the full sync and the Mac routes, a
  Google sign-in or identity page («Demuestra que eres tú», any page of `accounts.google.com`) is an
  expired session (`session_expired`), not a challenge, and nothing is typed or pressed on it; the
  unattended runner's web route is the one exception, where its allowlisted scripted sign-in may run
  on that page (FR-032b, FR-038), and only a challenge a human would clear stops it. A page that
  passes its time limit stops the run the same way with reason `timeout` (FR-037).

**Structure of the student's folder**

- **FR-011**: Each student MUST have their own alfabeta root folder in the family's Drive, never the
  root of «Mi unidad» (My Drive), which already holds the student's content. The master is a folder
  on the Mac's disk (`storage.base`, data-model), outside the Google Drive for desktop mount.
  (Note: spec 004 moves the upload of the master to Drive from Google Drive for desktop to
  alfabeta's own Google connection, confirmed by checksum, amending constitution VII; spec 001's
  Mac upload path is rewritten when spec 004's Drive slice is built, julioarguello/alfabeta#30. This
  amendment does not rewrite it, and the runner (FR-036) already writes only through that
  connection.)
- **FR-011a**: The master is the source of the mirrors. After every sync **on the Mac** that reaches
  `apply`, and after a book provider places a topic (`book place`), alfabeta MUST bring each folder
  in `drive.mirrors` up to date from the master, one-way: it copies what is new or changed in the
  master, never deletes anything from a mirror and never copies from a mirror into the master. A
  mirror already up to date MUST receive zero writes (FR-025). A mirror that is not mounted or fails
  MUST NOT stop the sync, the master or the other mirrors: it is reported and brought up to date by
  the next sync. The summary for the family MUST say how many mirrors are up to date and how many
  failed, never their paths (FR-031). An empty list means no mirrors. The unattended runner does not
  touch the master or the mirrors (FR-036): its `apply` skips both.
- **FR-011b**: Every output alfabeta shares MUST be shared with every account its list names, and
  with no other: the student's calendar with each account in `calendar.shared_with`, with
  permission to see all event details (built by the reminders epic), and each topic notebook a skill
  creates with each account in `notebook.share_with`, as viewer. From spec 005
  (julioarguello/alfabeta#44) on, each topic's two living files are shared, as reader, with the
  account in `notebook.owner`, and with no other. An account already shared with is
  not invited again. A failed share MUST NOT undo the output; it is reported in the summary by
  count, never by address.
- **FR-012**: Inside the root, the structure MUST be common to every source:
  `<school-year>/<subject>/<YYYYMMDD> - <Tema NN - title | teacher's title | No topic>/<source>/`,
  with `classroom` and `sciencebits`
  as this epic's sources. A topic folder holds only folders (constitution 2.2.0): the sources',
  `notes/` (spec 005), `notebook/` and `exam/` (spec 002); this epic writes nothing at its root. The first level is the school year (`2026-2027`), as in
  Science Bits today. Every topic folder starts with the posting date of its first Classroom
  material (`YYYYMMDD - `), or with the day it is created if a book provider creates it first. The
  date is set when the folder is created and MUST NOT change: alfabeta MUST find an existing topic
  folder by the part of its name after the date, whatever the date, and reuse it.
- **FR-013**: Only a class linked to a configured subject is synced: alfabeta proposes
  the link from the class title stated in the configuration, the family confirms it once,
  and from then on the class identifier counts, not its title. Topic folders MUST be
  named after the book topic (`<YYYYMMDD> - Tema NN - <title>`) when the subject has a book (the
  book topics are the folders whose name contains `Tema NN - <title>`, whatever their date, that
  already have their book's subfolder in the Drive),
  and each teacher's topic MUST be matched to them as follows:
  - alfabeta proposes the match from everything it has: the number, the title in
    any of the student's languages, the content of the items and the order in which they are posted.
    Each proposal says why and with what confidence (high, medium or low).
  - The family confirms or rejects each new match once, and can change a confirmed one.
    Rejecting a match means that teacher's topic is not in the book: it keeps its
    own folder named after the teacher's title. A rejected topic is proposed again only if its title changes or a
    new book topic appears in the Drive; the family can also change a rejected
    decision.
    Decisions are kept in the student's data folder, tied to the topic's Classroom identifier,
    so that if the teacher renames it the match holds.
  - Several teacher's topics MAY go to the same book topic.
  - If a teacher's topic spans several of the book's, alfabeta proposes each item's topic from its
    content, and the family confirms it the same way.
  - A teacher's topic with no equivalent in the book (review, project, introduction) and any topic
    of a subject without a book get their own folder `<YYYYMMDD> - <teacher's title>`, with no
    `Tema NN`, which sets it apart from the book topics. In a subject without a book there is
    nothing to confirm.
  - While a match is unconfirmed, its items do not go to the book topic: they are synced in the
    teacher's topic's own folder, as if it had no equivalent in the book, and the summary asks for
    confirmation. Confirming the match moves them to the book topic's folder.
- **FR-014**: An item without a topic and an announcement MUST go to the subject's
  `<YYYYMMDD> - No topic` folder, dated by the first item placed there. There are no month folders.
- **FR-015**: Inside `classroom/`, each item MUST be prefixed with its posting date,
  `YYYYMMDD - <item title>`, and its form MUST depend on its type:
  - a **material** with a single file, no links and no description is that file; with several
    files, with links or with a description, it is a folder with its files, a `descripcion` note
    with its text if it has one and an `enlaces` note if it has links;
  - an **announcement** is a `.md` note with its text or, if it has attachments, a folder with the
    note and the attachments; it carries `aviso` after the date (`YYYYMMDD - aviso - <summary>`),
    where `<summary>` is the first words of the announcement, sanitised and cut to 60 characters;
  - an **assignment** or a **question** (including one that is an exam or a quiz) is always a folder,
    even with a single attachment, so its submission and its grading can be added without moving
    anything; its instructions or the question's text go in `enunciado.md`;
  - a **material** with no files or links, only text, is a note `YYYYMMDD - <title>.md`
    (this rule wins over the one for a material with a description).
- **FR-015a**: Inside an assignment's folder, each file MUST be prefixed with its role, with
  fixed names without accents: `enunciado - <name>` (what the teacher attaches), `correccion`
  (grade, teacher's comment and return date) and `enlaces` (videos, links and forms, with title
  and link). What the student turned in goes in a subfolder `submission/` with each file's own
  name: a submission is often several photos of a notebook, which would otherwise mix with the
  teacher's files (amended 2026-10-28; it was `entrega - <name>` beside them, then `entrega/`
  until the folder names became English, #110).
- **FR-015b**: A superseded version (an attachment the teacher edited, a repeated submission) MUST
  be kept next to the current one as `<name> (anterior YYYY-MM-DD)`.
- **FR-015c**: Names MUST be valid in the file system and in Drive, at most 255 UTF-8 bytes,
  and unique in their folder without losing any item; the teacher's titles keep
  their accents.

Example of the resulting structure (invented names):

```text
2026-2027/
├── agenda.md   agenda.json
└── <subject>/
    ├── 20261014 - Tema 02 - <book title>/
    │   ├── sciencebits/
    │   └── classroom/
    │       ├── 20261014 - Ficha de gases.pdf
    │       ├── 20261016 - Vídeos y apuntes/
    │       │   ├── Apuntes.pdf
    │       │   └── enlaces.md
    │       └── 20261020 - Problemas tema 2/
    │           ├── enunciado - Problemas.pdf
    │           ├── correccion.md
    │           └── submission/
    │               └── Respuestas.pdf
    ├── 20261021 - <teacher's title>/
    │   └── classroom/
    │       └── 20261021 - Proyecto de laboratorio.pdf
    └── 20261103 - No topic/
        └── classroom/
            └── 20261103 - aviso - Cambio de fecha del examen.md
```

**Replica of what the teacher posts and of what the student turns in**

- **FR-016**: An attachment that is a file (PDF, Office document, image) MUST be replicated as is;
  a Google document, presentation or spreadsheet MUST be replicated as a PDF.
- **FR-016a**: alfabeta MUST replicate the files the student turned in for each assignment,
  downloading them like any other attachment and without touching the submission in Classroom.
- **FR-017**: A video, a web link or a form MUST be noted in the item's `enlaces` note
  with title, date and link, without being downloaded.
- **FR-018**: A replica MUST be taken as saved only when the complete file is in its folder.
  alfabeta collects from the Mac's downloads folder only the files it requested.
- **FR-019**: An attachment that cannot be fetched MUST be noted with its link and the reason in its
  item's `enlaces` note (and in the log), without stopping the sync.

**Agenda**

- **FR-020**: Every sync MUST update, in the school-year folder, a readable agenda and another
  one for tools with every dated item of the configured subjects: subject,
  category, title, date (due, exam or posting date) or «sin fecha» ("no date"), status if it is
  something pending (pending, turned in, returned, overdue and not turned in, missing per the
  teacher), link to Classroom and to the folder holding its replica. The agenda's content MUST depend
  only on what was synced and on the family's decisions, never on the day it is generated, and the
  agenda files MUST be rewritten only if their content changes (FR-025).
- **FR-020a**: Each agenda item MUST have exactly one category from this closed list:
  - **exam**: a test, whether a Classroom assignment or something the teacher announces on the
    stream or in a material;
  - **assignment**: an assignment to turn in that is not an exam;
  - **quiz**: a Classroom question, or an assignment whose only attachment is a form
    (`kind` = `form`). Its Classroom detail page
    is only read (FR-007); the linked form or quiz is never answered or followed
    (constitution IV: that is opening a quiz);
  - **material**: what is posted with nothing to turn in (notes, practice exercises), on its
    posting date;
  - **announcement**: a stream announcement that is not an exam.

  If an item fits several, the first in this order wins: exam, quiz, assignment,
  material, announcement (a question or an assignment that is an exam is `exam`).
- **FR-020b**: An exam that alfabeta infers from a text (announcement, title or description of a
  material, in any of the student's languages) MUST be marked «detectado», with its date
  resolved relative to the posting date and the link to the item it comes from. It appears in the
  agenda as soon as Claude proposes it, without waiting for confirmation. It is an agenda entry of its
  own (an item announcing several exams gives one entry per exam): the source item keeps its own
  entry and its category. Dismissing it is a correction by the family. If it cannot resolve
  the date, it appears without a date. The family MAY correct a detected exam (date, category or
  dismissing it), and the correction MUST be kept in the following syncs.
- **FR-020c**: The status of pending items MUST be the one Classroom shows in each sync, so
  that what was posted before the first sync and already turned in appears as done. The
  readable agenda MUST open with a «Pendiente» checklist, sorted by date nearest
  first and with the «sin fecha» items last, and continue with «Hecho», with what was turned in
  checked off, sorted by due or exam date from most recent to oldest, with the undated ones
  last:

  | Status or case | List |
  |---|---|
  | `pending`, `overdue`, `missing_per_teacher` | Pendiente |
  | `turned_in`, `turned_in_late`, `returned` | Hecho |
  | assignment, quiz or exam without `status` (unknown status text, or nothing to turn in on Classroom) | Pendiente |
  | detected exam, while no capture of its class later than its date exists | Pendiente |
  | detected exam without a date, until the family corrects or dismisses it | Pendiente |
  | detected exam with a capture of its class later than its date | Hecho |
  | detected exam the family dismisses | none |
  | exam that is a Classroom assignment or question, in `pending`, `overdue` or without `status`, with a capture of its class later than its date (wins over the rows above; `missing_per_teacher` stays in Pendiente) | Hecho |
  | `material`, `announcement` | Publicado (informational section by posting date, from most recent to oldest, after «Hecho») |

  "Later than its date" compares against the exam's instant or, if it only has a date, against the
  end of that day in `Europe/Madrid`. No rule uses the day the agenda is generated: they all depend
  on the captures and the decisions (FR-020).
- **FR-021**: Dates MUST be shown as Classroom shows them, in `Europe/Madrid` time.
  Classroom does not show the year and uses relative dates («Mañana, 8:00» (Tomorrow, 8:00)): the
  year is inferred from the school year (September to December, the first year; January to August,
  the second; a capture taken outside that school year stops the run with `invalid_config`)
  and relative dates are resolved against the moment the page that shows them was read, not the
  start of its capture nor that of the run that applies it: each detail page carries its own read
  instant (`seen_at`), and a page without one uses its capture's. A bare time («8:00»,
  «Fecha de entrega: 23:59») is on the day that page was read. The posting date MUST come from the
  creation date (stream or detail), never from the
  «última modificación» (last modified) the listing sometimes shows.

**Repeatable and schedulable**

- **FR-021a**: A student's full sync MUST be launched with a single request to Claude that
  invokes the `classroom-sync` skill (e.g. «sincroniza alfabeta para <student>», "sync alfabeta for
  <student>") and MUST be schedulable (e.g. daily) on the family's Mac. A scheduled run that finds
  the student's session expired, an anti-bot challenge or the Drive not mounted stops navigating and
  tells the family, with the same rule as an interactive one: before capturing any class (or with the
  Drive not mounted), without writing to the student's folder; midway, it applies the classes already
  captured as `partial`. The notice is the result of the scheduled task in the Claude desktop
  app, plus a line in the log. If a scheduled task cannot use the
  browser or download files without approval (spike S2), the scheduled run is limited to that
  notice («toca sincronizar», "time to sync") and the family launches the sync with the single
  request; that reduced mode also meets this requirement. For a student with the unattended runner
  enabled, `[schedule]` drives the runner's to-do read (FR-032), not a desktop task, so the full
  sync — which still needs the Mac for attachments and replicas — is launched on demand with the
  single request, or scheduled on the Mac for a time `[schedule]` does not name; the runner keeps
  the agenda current between full syncs. The runner's notice reaches the family with the Mac off
  (FR-037).
- **FR-021b**: What needs no judgement (state, identifiers, names, structure, agenda,
  collecting downloads) MUST give the same result on every repetition. What does need it
  (proposing topic matches, detecting exams in a text) MUST be recorded with its
  reason, and once confirmed by the family it is not decided again. An exam candidate that Claude
  judges announces none is also recorded (`dismissed_candidate`) and is not judged again
  unless its text changes.

**Books in the same structure**

- **FR-022**: The Science Bits skill MUST read the per-student configuration and leave its files in
  the `sciencebits` subfolder of the topic's folder.
- **FR-023**: alfabeta MUST NOT read from or write to the previous cloud (Dropbox). What was captured
  there before this epic stays as it is; if it is wanted in the new structure, it is captured again.

**Incremental sync and log**

- **FR-024**: Every item and every attachment MUST have a stable identifier derived from Classroom.
  Repeating a sync MUST NOT duplicate anything.
- **FR-025**: A sync without changes MUST NOT write anything to the student's
  folder, their state or their decisions. "Without changes" means that Classroom does not change and
  that no due or exam date falls between the previous capture and this one: if one does, the
  entry changes list (FR-020c) and that is a change. It writes only that run's own
  records: its log line, its captures, its plan, its lock file, the attachments it
  collects into the data folder (which `apply` deletes once placed or found identical) and the
  deletion of its captures older than `kept_captures` (never in the student's folder). An unattended
  runner run without changes writes only the same own records in its data home; it stores a new
  secret version only if the token or session actually changed (FR-033), and uploads the agenda only
  if its hash changed (FR-036).
- **FR-026**: alfabeta MUST detect and apply new items, edited attachments, new or
  repeated submissions, returns and moved dates. An already replicated attachment is downloaded again
  only if Classroom shows its item was modified after the last replica, if its name or its type
  changes, or in the periodic full review (`full_review_days`; template value: 7). The
  full review counts from the last run in the log that performed one (the first
  sync is one); if it finds the
  same bytes it writes nothing outside its own records (FR-025). The superseded version is kept
  according to FR-015b.
- **FR-027**: An item withdrawn from Classroom MUST be kept, marked as withdrawn in the log
  and mentioned in the summary. It is marked as withdrawn only if its class's capture is complete:
  a cut-short capture (expired session, error) withdraws nothing. alfabeta MUST NOT delete anything
  from the student's folder.
- **FR-028**: Every sync MUST leave a log entry with start, end, subjects walked and
  items added, changed, withdrawn or not fetched, and mirrors up to date or failed (FR-011a), and
  end with a summary for the family.
- **FR-029**: The failure of a subject or of an attachment MUST NOT abort the rest. If it is
  interrupted, the next sync continues without duplicating.
- **FR-030**: Two syncs of the same student MUST NOT run at once: the lock is taken
  at the start and held for the whole run, including the browser part. Every step of the
  run renews it; if `lock_idle_minutes` pass without renewing it (the run died), it is
  released on its own and a `stopped` line is left in the log. Since all students share one
  browser and one downloads folder, the browser part and the downloads of two students, or of
  two alfabeta skills (the Classroom one and a book's), MUST NOT run at once either. If the Drive
  folder is not available, alfabeta MUST stop without
  writing replicas anywhere else (only its log line, FR-021a). For a student with the unattended
  runner enabled, the student's lock is the lease in the single data home (FR-035) and binds the
  runner and any family session alike; the runner runs off the Mac, so it takes no lock on the
  Mac's browser.

**Privacy**

- **FR-031**: The name, the email or any data identifying the student MUST NOT appear in a
  URL that alfabeta builds, in the log or in an error message. Paths are shown
  relative to the student's root folder, and the absolute path of the root or of a mirror is never
  shown, because the Google Drive for desktop mount path carries the account's email.

**Reading Classroom with nobody present (User Story 7)**

- **FR-032**: alfabeta MUST be able to read Classroom for a student with nobody present and without
  the operator's Mac or browser: a job scheduled at the weekday times of `[schedule]`, in the
  operator's Google Cloud project for alfabeta (the one spec 004 and spec 005 use; constitution IX),
  driven by alfabeta's own code (never Claude, never the Claude extension, never the operator's
  Chrome), in one of two routes decided by a spike (FR-032a, FR-032b; research R15 to R17). It is
  enabled per student by configuration; while it is off, FR-006 and FR-021a apply unchanged. It is
  built only once its spikes pass; if both routes fail, it is not built and the family keeps the Mac
  route (FR-021a) and the guardian email summaries.
- **FR-032a**: The **token route** (primary) MUST read Classroom as a Google first-party client:
  the family signs in by hand once to seed a long-lived sign-in token for the school account into
  the vault (FR-033), and the runner exchanges it for short-lived access tokens and makes read-only
  calls. Read-only MUST be enforced by requesting read-only scope only (constitution IV). Spike S4
  MUST prove, with one read-only call for the real account, that this reaches the student's
  Classroom despite the school's block on third-party clients (`docs/classroom-investigacion.md`);
  if it does not, the token route is not built. The spec records its accepted risks: it poses as a
  first-party app (against Google's terms); shows as a new device on the account; may be blocked at
  the account-policy level; and its stored token is **account-wide and bypasses the second factor**
  (read-only is only the scope requested from the derived short-lived tokens, not a property of the
  stored secret), so the stored secret is at least as sensitive as the password and a vault read —
  by the project's administrators (FR-033, constitution II) or in a breach — exposes the whole
  account, not read-only Classroom.
- **FR-032b**: The **web route** (fallback) MUST read the to-do pages (FR-034) in a headless browser
  with the read-only guard of FR-038, using the browser session the family started by hand, kept in
  the vault (FR-033). When a run lands on a Google sign-in page because the session has expired, a
  deterministic script MUST sign in once with the password and second-factor seed in the vault, then
  continue; a sign-in that needs a challenge a human would clear MUST stop (FR-037), never evade it.
  Spike S5 MUST measure whether this route signs in and reads at all without evasion, and how often
  the school session expires; if it cannot without evasion, the web route is not built.
- **FR-033**: The runner MUST sign in only with secrets the family placed in the vault, and MUST
  hold the minimum for the route in force: the sign-in token for the token route; for the web route,
  the stored browser session and, separately, the password and its second-factor seed used only to
  sign in again when the session has expired. Two limits hold whatever the route: Claude MUST NOT
  run a sign-in or type a credential (it writes the deterministic sign-in script; the scheduled job
  runs it), and no stealth tooling, debug-port hiding, fingerprint spoofing or CAPTCHA solving is
  used. The vault is the secret store of the family's cloud project; each secret is readable by the
  runner's identity, the family, and the project's administrators (constitution II), with versions,
  and never in the repository, the configuration, a log, an error message or Claude's context. The
  secret the runner renews is the one it mints — the token, or the web route's stored session — and
  only when it actually changed (FR-025); the password and second-factor seed are seeded by the
  family and the runner never rewrites them. Only the configured school account is used. The family
  can revoke any of them at any moment by changing the credential or signing the account out, and
  the run stops when the secret it needs stops working. Because the token-route secret is as
  sensitive as the password (FR-032a), the cloud project MUST keep an audit log of every read of a
  vault secret, and the family MUST be told the first time a new device or first-party sign-in is
  registered on the student's account, so a misuse of the stored token is visible.
- **FR-033a**: Every secret the runner holds MUST be named as a separate vault entry, with where it
  lives, who seeds it, who can read it and how it is refreshed:
  - **token route**: the first-party sign-in token (seeded once by `runner session login`, renewed
    by the runner when the exchange returns a new one);
  - **web route**: the stored browser session (seeded and renewed by the runner, destroyed when
    superseded, FR-033); the account password and the second-factor seed (each seeded once by the
    family directly into the vault — never by `runner session login`, which stores no password —
    and never rewritten by the runner);
  - **both**: the credential the runner writes the agenda to Drive with — a token for the student's
    Drive, in the vault, scoped as narrowly as spec 004 allows (ideally the alfabeta folder, not the
    whole Drive, which may amend spec 004 FR-007, julioarguello/alfabeta#30);
  - **on the Mac**: the cloud-project machine identity a Mac session uses for `runner home
    pull`/`push` and `runner session login`, kept in the Mac keychain, with access only to that
    student's vault secrets and its state folder in Drive. It is the only runner secret on the Mac.
- **FR-034**: The web route MUST read: «Tareas pendientes» (`/u/<n>/a/not-turned-in/all`), opening
  each collapsed section («Sin fecha», «Esta semana», «Próxima semana», «Más tarde») by its header
  button; «Sin entregar» (`/u/<n>/a/missing/all`), following its «Ver todo»; the detail page of
  every assignment or question those lists show, for its instructions, due date, status and
  points; and, once, the detail page of each item that was pending in the previous read and is in
  neither list now, to take its status (FR-008a) or learn that it was withdrawn (FR-027). The token
  route reads the same pending items and their dates and statuses from the API. A read is complete
  only if both lists (or the API's pages) were read to the end and every detail was read; an
  incomplete one marks nothing turned in or withdrawn. The runner MUST NOT read the stream, the
  materials of «Trabajo de clase» or the attachments, nor download anything: exams detected in a
  text (FR-020b) and the replicas stay with the full sync. The web route checks the account locally
  against `classroom.account` as the full sync does (FR-006, research R2), never putting the address
  in a URL (FR-031); the token route is already bound to the one account its token belongs to.
- **FR-035**: A student MUST have a single data home (configuration, state, decisions, log,
  captures, lease). With the runner enabled it lives in a state folder inside the alfabeta folder of
  the student's Drive (constitution II and VII: in Drive, reached through spec 004's connection,
  never part of the master and never mirrored), and any run for that student — the runner's, or a
  family session's on the Mac — takes the student's lease there before reading or writing it. Two
  copies of a student's state that can both be written MUST NOT exist. A Mac session reaches the
  home with `runner home pull`/`push` (research R19).
- **FR-036**: The runner's outputs MUST be only its data home; the agenda (FR-020), written to the
  school-year folder in Drive through alfabeta's own Google connection (spec 004, with the
  credential of FR-033a) and counted as written only when Drive confirms it; and the calendar, once
  spec 003 builds it. Its `apply` MUST skip the master folder and the mirrors, which stay with the
  full sync on the Mac. The data home keeps the hash of the agenda last written to Drive; any run,
  on the Mac or the runner, that is about to upload `agenda.*` MUST first regenerate it from the
  shared data home and upload only if that hash changed, so no path (a Mac `apply`, `book place`, a
  spec 004 upload) ever pushes a stale agenda over a newer one.
- **FR-037**: The runner MUST never wait for a person and never hang: a per-page (or per-call) and a
  per-run time limit (`[runner]` keys, data-model), and the job platform ends a run that outlives the
  per-run one. It stops with `session_expired` when the stored secret is gone or rejected (a dead
  token, or a sign-in page the web route cannot clear with the vault alone), `challenge` on a
  CAPTCHA, an «unusual traffic» or «this browser may not be secure» page, or a second factor beyond
  the stored seed, `account_blocked` on an API answer that the account is not allowed,
  `drive_write_failed` when the agenda upload is not confirmed, `store_unavailable` when the vault or
  the data home cannot be reached, `unexpected_ui` on a missing label or an unexpected response
  shape, and `timeout` past a time limit; in every case without evasion and applying only what it
  read completely (FR-010). The family gets a notice that gives the reason and never names the
  student, through a channel that works with the Mac off (research R17). A stopped run MUST NOT store
  a new secret version. The family gets one notice per stored-secret version per reason: the run
  fails (exit 1) only the first time a reason appears for the version in use, and a later run that
  stops the same way with the same version logs `stopped` and ends 0, so no new notice fires until
  the family refreshes the vault. On a `challenge` the run records a `cooldown_until` in the data
  home, `[runner] challenge_cooldown_minutes` ahead, and a run that starts before it stops at once
  without reaching Classroom; the job platform's own retries are off, so a challenge is never
  re-hit inside the same scheduled slot (research R17, plan).
- **FR-038**: The web route's browser MUST enforce the read-only rule by construction (FR-007,
  constitution IV), not by trusting the code that drives it: a script installed before any page
  script runs cancels every click, form submit and key event, and every `submit()`/`requestSubmit()`,
  whose target is not an allowlisted control (a to-do section header, «Ver todo», or the scripted
  sign-in's own fields on a Google sign-in page); and it blocks, before they leave the browser,
  every document load outside the exact set `/u/<n>/h`, `/u/<n>/a/not-turned-in/all`,
  `/u/<n>/a/missing/all`, `/u/<n>/c/<class>/a/<item>/details` and `/u/<n>/c/<class>/mc/<item>/details`
  (the other pages of FR-007 are for the full sync, not the runner), and every request to a form or
  quiz host (`docs.google.com/forms`, `forms.gle`) or a download host (`drive.usercontent.google.com`,
  any `/export`) — the runner downloads nothing (FR-034). Every blocked load, press or request is
  counted in the run's log. This holds even
  though the page's own `extract.js` tries the presses. The background requests Classroom makes to
  show those pages are allowed only as spike S6 measures them (research R18). The token route needs
  no such guard: read-only is the scope
  it requests (FR-032a).

### Key Entities *(include if feature involves data)*

- **Student**: a *tenant*. Their private configuration (display name, school year, master folder in
  the family's Drive and its mirrors, subjects, Classroom account, the accounts the calendar and the
  notebooks are shared with) and their single data home (log, sync state, the family's decisions),
  on the Mac or, with the runner enabled, in a state folder in the student's Drive (FR-035), the
  secrets in the cloud project's vault (FR-033).
- **Mirror**: a folder in another of the student's accounts' Drive, mounted on the same Mac, kept
  up to date one-way from the master folder.
- **Subject**: a course of the student, with its folder name and the Classroom class that
  corresponds to it.
- **Topic folder**: the third level of the structure, prefixed with its date. A topic folder holds
  the match with the teacher's topic, or a teacher's topic with no book equivalent; the subject's
  `No topic` folder collects what has no topic.
- **Source**: the origin of a piece of content (`classroom`, `sciencebits`) and its subfolder.
- **Classroom item**: material, assignment, question or announcement. Stable identifier, subject,
  topic, title, dates and attachments.
- **Replica**: the copy of an attachment (file or PDF), of a student's submission, of a grading or
  the note with its links, with its role (`statement`, `submission`, `grading`, `links`) and its hash
  to detect changes.
- **Agenda entry**: a dated item (or undated) and its category (exam, assignment,
  quiz, material, announcement); if it is something pending, its status; if it was inferred from a
  text, the detected mark, its origin and the family's correction if there is one.
- **Sync**: a run for one student, with its log and its summary.
- **Unattended runner**: a scheduled job in the operator's Google Cloud project for alfabeta
  (FR-032) that reads a student's pending work and updates the agenda, with nobody present (User
  Story 7), by the token route or the web route (FR-032a, FR-032b).
- **Vault**: the secret store of the family's cloud project, holding the student's secrets with
  versions (FR-033a): the token (token route) or the stored session (web route), which the runner
  mints and renews; the password and second-factor seed the family seeds directly for the web route;
  and the Drive-write token. The newest version of the minted secret is the one in use.
- **Data home**: where a student's state, decisions, log, captures and lease live; one per student,
  on the Mac (`~/.alfabeta/<student>/data/`) or, with the runner enabled, in a state folder inside
  the alfabeta folder of the student's Drive (FR-035).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After a subject's first sync, 100 % of the items in its
  «Trabajo de clase» are replicated in its folder or noted with link and reason, checked item by
  item against what the student sees in Classroom.
- **SC-002**: A second sync without changes (FR-025) modifies zero files in the student's folder
  and in its mirrors.
- **SC-003**: A moved due date, a new material or an attachment of an item that Classroom
  shows as modified appear in the folder and in the summary in the first sync after the
  change; an attachment edited only in Drive, or of an item that shows no modification mark (an
  assignment with a due date), at the latest in the periodic full review.
- **SC-004**: The family sees every exam and assignment of every subject in a single agenda
  sorted by date, each with its category, without opening Classroom.
- **SC-004a**: In the test set, 100 % of the exams announced only on the stream or in a
  material appear in the agenda as a detected exam, with a link to their origin.
- **SC-005**: For any topic with material from Classroom and from the book, both sources are in the
  same topic folder.
- **SC-006**: Registering a second student leaves the repository without any change.
- **SC-007**: The guardrail rejects 100 % of the test cases with planted real data (name,
  email, path, identifier) and accepts the template.
- **SC-008**: Zero status changes in Classroom during any sync: no submission,
  comment, marked assignment or opened quiz.
- **SC-008a**: In the test set, in 100 % of the assignment folders the name tells apart
  what is the teacher's, what the student turned in and what is the grading.
- **SC-009**: Searching the student's name and email in the log and in the messages of a
  full sync gives zero matches, and likewise in everything the unattended runner emits — its log,
  its stdout and stderr (which go to the project's logging that administrators can read), and the
  notice email — including a Google sign-in redirect URL and the account button, which can carry the
  address. The runner never logs an `accounts.google.com` URL. The command never prints
  `display_name`: only Claude uses it when talking with the family in the chat.
- **SC-010**: After a sync in which every mirror is mounted, every file in the master is in every
  mirror with the same size and modification time (a `rsync -rlt --dry-run` from the master lists
  nothing to copy).
- **SC-011**: With the runner enabled and the operator's Mac off, an assignment the student has
  pending before a scheduled run is in the agenda in Drive after that run, with its due date, and
  nobody was at any computer.
- **SC-012**: The family refreshes the vault by hand at most once every 7 days. The token route, if
  S4 proves it, needs this only when the token is revoked. For the web route, spike S5 measures how
  often the school session expires and whether the scripted sign-in renews it; if the family would
  have to sign in more often than every 7 days, the web route is not built, and if the token route
  also failed, User Story 7 is not built and the family keeps the Mac route and the guardian email
  summaries (research R17).
- **SC-013**: In the web route's tests and every real run, zero page loads, presses or form
  requests outside the allowlist reach Classroom or a form host, no evasion tooling runs, and zero
  status changes happen in Classroom (SC-008). In the token route, only read-only scope is ever
  requested.
- **SC-014**: A sign-in the runner cannot complete (the web route hits a human challenge, or the
  token is dead) ends the run within its time limit, and the family gets exactly one notice until
  the vault is refreshed.
- **SC-015**: Claude runs no sign-in and types no credential in any run; the vault holds only the
  minimum for the route in force (a token, or the stored session with the password and its
  second-factor seed) plus the Drive-write token (FR-033a), checked in the tests and in a review of
  what the runner stores.

## Assumptions

- The full sync runs on the family's Mac from the Claude desktop app, on demand or
  scheduled (FR-021a), with the Classroom session the student starts in the browser. Reading
  Classroom with nobody present runs in the family's cloud project (User Story 7), which replaces
  the local MCP design of julioarguello/alfabeta#2.
- The runner's cloud project is the operator's Google Cloud project for alfabeta, the one spec 004
  created and spec 005 also runs in (constitution IX), reused for the vault (its secret store) and
  the scheduled job; the data home is a state folder in the student's Drive (FR-035), as the
  constitution sets for a cloud run. Its OAuth client and personal-Gmail link (spec 004) are for
  Calendar and Drive on the personal account; the runner's Classroom read of the school account is a
  separate mechanism (the token or web route), which spec 004 explicitly left out. The project
  belongs to an organisation the operator administers, and that organisation's administrators can
  read its secrets, the student's stored sign-in among them (research R17). The family accepts or
  refuses that custody in the review of this amendment.
- The two routes carry risks the family accepts in this review (research R15 to R17): the token
  route poses as a Google first-party app (against Google's terms), shows as a new device on the
  account, and stores a token that is account-wide and bypasses the second factor — as sensitive as
  the password, so a vault read exposes the whole account, not read-only Classroom; the web route
  signs a minor's account in by script, which Google blocks for automated browsers and which risks a
  lockout. Both read-only in the scope the runner requests, both the student's own account, both
  without evasion; a spike proves each before it is built.
- Reading Classroom by program, today through the Claude extension and with User Story 7 with
  nobody present, is automated access to pages whose `robots.txt` disallows it, and Google's terms
  forbid automated access that violates those instructions; the account at stake is the student's
  school account (research R15). The family decides in the review of this amendment whether to
  accept that risk; the runner reads less than today's route, once per scheduled time.
- The student's school account works in the Classroom app on an Android phone (operator,
  2026-10-27), and the operator believes no device-management app was required. This is why the
  token route may reach the account where our own OAuth client was refused (research R16); spike S4
  confirms or refutes it. It is an inference, not a test of the token route.
- The school's web session is short — the operator says «como máximo una hora», not measured. It is
  why the token route (not tied to the web session) is preferred and why the web route needs a
  stored credential to sign in again (research R16).
- Observed on 2026-10-25 in the student's Classroom, read-only: the teacher's topics do not
  match the book's (one teacher's topic groups material from several book topics and another
  does not exist in the book), some subjects have numbered topics and a folder of saved exams,
  exams are announced on the stream in the class's language, there are hidden classes, and the
  student's personal Drive already has folders of their own.
- The family Drive is mounted on the Mac with Google Drive for desktop. Which personal Google account
  it is (the family confirms which when mounting it in the plan), and which folder each student's
  root lives in, is configuration.
- The student's other accounts (on 2026-10-26, the school Google Workspace for Education account)
  get the material through mirrors (FR-011a), not through Drive sharing: each one's Drive is mounted
  by Google Drive for desktop on the same Mac and its folder is listed in `drive.mirrors`. alfabeta
  does not manage Drive permissions, except the one share of each living file that spec 005 adds
  (FR-011b).
- alfabeta's own OAuth client is not available for the student's school account
  (`docs/classroom-investigacion.md`), so the full sync reads everything from what the student sees
  in the browser. The unattended runner's token route (FR-032a) tries the API as a first-party
  client instead, which may or may not reach the account — spike S4 decides, and if it does not,
  the web route reads from the browser as the full sync does.
- Topic and item titles are kept in the language the teacher writes them in.
- What goes into each topic's notebook is decided by epic 3; the proposal is the teacher's material
  and the books, without the student's submissions or gradings.
- The «Trabajo de clase» of two subjects was observed read-only (the plan's research); that of the
  other classes is walked in the first sync and FR-013 is checked against what is there.
- The Classroom interface of the student's account is in Spanish; date and status texts
  are interpreted in that language. Another interface language stops the sync (FR-007) until
  it is added.
- The plan sets the exact location of the private configuration and of the local data folder,
  always outside the repository and outside the shared folder.
- The accounts the calendar is shared with are configuration (`calendar.shared_with`, FR-011b);
  the calendar itself, its alerts and its events are built by the reminders epic. Measured
  2026-10-26: a calendar shared from a personal account can be added in the student's school
  account and shows its events. That epic also sets each category's colour; the proposal is exam red, assignment orange,
  quiz purple, material blue and announcement green, with the subject in the event title, because
  a calendar event takes a single colour. That epic also evaluates Google Tasks for assignments
  (the student marks them as done and they show in the calendar), checking which account they live
  in, whether they take a colour and whether the family can see them. That epic is also the one that
  shows "today" and "this week", which depend on the day.

## Dependencies

- The Claude desktop app with access to the Mac's files.
- Chrome with the Claude extension and the student's Classroom session in it.
- Google Drive for desktop with the family's account, already installed on the Mac, and with the
  account of each mirror mounted too.
- The `sciencebits-a-notebooklm` skill, which moves to reading the per-student configuration and
  writing to the common structure (FR-022).
- For User Story 7: the family's cloud project with a scheduled job, a secret store (the vault) and
  a private store (the data home); spec 004's connection, able to write Drive for the agenda; and,
  to seed the vault, a computer with a screen where the family signs in by hand once (to mint the
  token for the token route, or the browser session for the web route). A MAJOR amendment of
  constitution III, in this same pull request, permits the vault.
