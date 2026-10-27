# Feature Specification: Due-date warnings placed on the student's timetable

**Feature Branch**: `docs/28-spec-003-due-date-warnings` (spec dir `003-due-date-warnings`)

**Created**: 2026-10-27

**Status**: Draft

**Input**: Operator's description (translated from Spanish and condensed): "Improve the calendar.
The student's timetable is an input to put things in their slot instead of all day. Detect each
assignment's due date and create warnings ahead of it. Rule: the longer the gap between the day the
teacher posts it and the due date, the harder the work, so the earlier the warning. Think it
through and put it to a panel. We cannot afford one more incident."

## Context and scope

This is the reminders epic that [spec 001](../001-classroom-sync/spec.md) deferred ("the agenda
moves to a calendar with alerts"), tracked in julioarguello/alfabeta#28. It takes the due dates,
statuses and exam announcements that `classroom-sync` captures and the student's school timetable,
and writes warnings into the student's calendar so that each assignment is announced at a moment he
can act on it, early enough for the size of the work, and never after it stopped mattering.

Every number below comes from the Classroom capture of 2026-10-26 (93 items in 12 classes) or from
the timetable, unless it says otherwise. The design was put to a panel of three advisors and a
devil's advocate on 2026-10-27; their disagreements are kept in the clarification questions, not
settled here.

What this spec takes from spec 001's reminders epic: the warnings, the timetable, and which account
reads them, and a daily list of pending work that stands in for its "today / this week" views.
What it leaves: one colour per category (FR-020a of spec 001).

Out of this spec: writing anything to Classroom; study blocks in the calendar; Google Tasks as the
carrier of warnings (it may carry the daily list, FR-024);
changing how Classroom is captured (a due date shown only as a time, "Fecha de entrega: 8:00", is
resolved against the capture's own date by spec 001, a dependency here); changing anyone's
notification settings, which only that person can do.

**Changes elsewhere once this spec is approved.** Four places say the calendar holds only
objective facts and no reminders: FR-025 of spec 002 (julioarguello/alfabeta#22), the roadmap's
Calendar section, the calendar policy line of the student's private configuration, and the
operator's standing instruction recorded outside the repository. The operator chose warnings that
restate facts (Clarifications, 2026-10-27), so the edit is narrow: "objective facts only" stays, and
each place gains "plus warnings and a daily list that restate those facts". FR-025's ban on study
blocks stays whole.

## Clarifications

### Session 2026-10-27

- Q: Which miss is this spec meant to prevent? → A: The Physics and Chemistry group video about
  chromatography: posted Thursday 8 October, due 13 October with no time, a window of 5 days that
  ran over a long weekend (Monday 12 October is a public holiday). The capture of 2026-10-26 already
  reads it «Calificado», so only a replay can test it (SC-008).
- Q: Who reads the warnings? → A: The student and the operator, each on their own account.
- Q: May a warning advise («Empieza hoy») or only restate a fact? → A: Only restate a fact: what is
  due, when, and how many days are left. No advice wording.
- Q: Windows of 2 to 7 days: only the evening-before warning, or also one at about half the window?
  → A: Also one at about half the window, as the operator's rule says.
- Q: At what time is the student home, per weekday? → A: Not needed: every warning at 16:00, every
  day. The operator added a need in the same answer: a list he can open any day and sit down with
  ("venga, ¿qué tengo que hacer?"), beside the warnings (User Story 7).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Short work is announced the evening before, at home (Priority: P1)

Most assignments are due within a week of being posted: 17 of the 20 that carry a due date, 7 of
them the next day (all Maths sheets due at 08:00 before the next Maths class). The student gets one
warning at a time he is home, before the work is due, and none once it no longer matters.

**Why this priority**: it is most of the work and most of the misses: 9 of the 20 dated items read
«Sin entregar» (missing), all with gaps of a week or less.

**Independent Test**: replay the capture of 2026-10-26 as if each item had been seen the day it was
posted, and read the warnings produced for the short-gap items.

**Acceptance Scenarios**:

1. **Given** a Maths sheet posted on a Monday and due Tuesday at 08:00, and a sync on Monday
   afternoon, **When** warnings are computed, **Then** one warning sits at Monday's home slot,
   naming the subject, the work, and "mañana 8:00".
2. **Given** an assignment whose status becomes «Entregado», «Calificado» or «Entregado con retraso»,
   **When** the next sync runs, **Then** its pending warnings are gone and its due-date event stays.
3. **Given** an assignment posted and due on the same day (2 measured), **When** no home slot exists
   between the sync and the due instant, **Then** no warning is written.
4. **Given** a due date without a time (6 measured), **When** warnings are computed, **Then** the
   last warning sits at the home slot of the day before, and no due hour appears anywhere.

---

### User Story 2 - Long work gets an early start (Priority: P1)

Three assignments had windows of 25, 55 and 58 days: a group project in Technology, a personal plan
in PE due on a Sunday, a board-game project in Art. The family's rule: the longer the window, the
earlier the first warning.

**Why this priority**: a long window is where the planning fallacy bites; nothing else in the
calendar reminds him until the due date.

**Independent Test**: replay the three long items and list the warnings and their dates.

**Acceptance Scenarios**:

1. **Given** an assignment with a window of 8 days or more, **When** warnings are computed, **Then**
   it gets a first warning 14 days before (28 days too when the window exceeds 28), one 7 days
   before, and the last one before the due instant (FR-006).
2. **Given** an assignment with a window of 2 to 7 days, **When** warnings are computed, **Then** it
   gets one warning at about half the window and the last one before the due instant (FR-006).
3. **Given** a project due on a Sunday, **When** warnings are computed, **Then** its warnings sit at
   16:00 on the days the rule gives, weekend days included.

---

### User Story 3 - A first run, a late sync or a change never floods him (Priority: P1)

A first run on the capture of 2026-10-26 with the draft design produced 29 warnings, 21 of them
moved to the run day, 16 for work already past due and 7 for work already handed in.

**Why this priority**: one flood teaches the student that warnings are noise, which costs every
later warning.

**Independent Test**: run on the capture of 2026-10-26 as a first run, then again with no change,
then with one due date moved.

**Acceptance Scenarios**:

1. **Given** a first run, **When** an item's due instant has passed, **Then** it gets no warning.
2. **Given** a first run, **When** an item still ahead has several warnings whose time already
   passed, **Then** they become one warning at the next home slot.
3. **Given** a second run with nothing changed, **When** it ends, **Then** no event was created,
   moved or deleted.
4. **Given** a teacher who moves a due date, **When** the next sync runs, **Then** the item's
   warnings are recomputed from the new date and the old ones are gone.

---

### User Story 4 - An exam sits in its class, and is announced ahead (Priority: P2)

Exams happen in class. Three of the four known exams were announced on the Classroom stream, the
fourth by the family.

**Why this priority**: the timetable can say when an exam happens, which an all-day event cannot;
the study pack (spec 002) already reacts to an exam.

**Independent Test**: the three stream announcements of the capture and the family's exam, placed
against the timetable.

**Acceptance Scenarios**:

1. **Given** an exam on a day when its subject has exactly one session, **When** it is written,
   **Then** it sits in that session, labelled as a time taken from the timetable.
2. **Given** an exam on a day when its subject has no session or more than one, **When** it is
   written, **Then** it is all-day.
3. **Given** a known exam, **When** warnings are computed, **Then** there is one a week before and
   one the evening before.

---

### User Story 5 - "For Thursday" is read with the timetable, and nothing else is guessed (Priority: P3)

Of the 37 assignments with no due date, one says when it is due in its title: Physics, posted on a
Monday, "Ostegunerako ariketa" (Basque: "exercise for Thursday").

**Why this priority**: a single measured case. A broader reading of the texts found three more
candidates, all of them wrong: two uses of "today" in a long description, and a Spanish title that
names the class day it was posted.

**Independent Test**: run the inference over the 37 undated items of the capture.

**Acceptance Scenarios**:

1. **Given** the Physics title above, **When** due dates are inferred, **Then** the due date is the
   next Thursday session of Physics after the posting date, and the event says it was deduced and
   from which words.
2. **Given** a title that names the day it was posted, **When** due dates are inferred, **Then**
   nothing is inferred.
3. **Given** an assignment with no due date and nothing inferable, **When** the week's summary is
   written, **Then** it is listed there, and it gets no warning.

---

### User Story 6 - Nobody believes warnings arrive until someone saw one arrive (Priority: P1)

A reminder written by the account that creates an event reaches nobody else; each reader gets only
the notification defaults of their own account for that calendar, and nobody else can change them
(Google's Calendar API reminders guide and Calendar Help 37242, read 2026-10-27). Whether either of
the student's accounts notifies him of this calendar has not been measured.

**Why this priority**: if nothing reaches him, every other story is decoration and the family stops
checking because "the calendar warns him".

**Independent Test**: a test warning and an all-day test event on the calendar, watched on each
reader's phone by the family.

**Acceptance Scenarios**:

1. **Given** a reader not yet checked, **When** warnings would be written, **Then** they are written
   but the run says, every time, that delivery to that reader has not been seen.
2. **Given** a test event, **When** the family sees its notification on the reader's phone, **Then**
   the date and the account are recorded.

---

### User Story 7 - A list he sits down with, any day (Priority: P1)

The operator's words (2026-10-27): something he can look at every day and say "right, I sit down,
what do I have to do". Warnings say *when* something is close; the list says *what* is pending, all
of it. Warnings reach him only on days something is close, and the 31 pending assignments with no
due date never get one.

**Why this priority**: it is the one place the student and the operator look at together, and the
only place undated work shows up after its posting day.

**Independent Test**: build the list from the capture of 2026-10-26 and compare it, line by line,
with the statuses Classroom showed that day.

**Acceptance Scenarios**:

1. **Given** a capture, **When** the list is built, **Then** it holds every assignment not handed
   in, in three groups: due ahead, nearest first; past due and still not handed in according to
   Classroom; no due date, newest first. Each line gives subject, title as Classroom writes it, due
   date and hour when Classroom gives them, and Classroom's status.
2. **Given** an item whose status becomes «Entregado», «Calificado» or «Entregado con retraso»,
   **When** the next sync runs, **Then** it leaves the list.
3. **Given** the list, **When** it is read, **Then** it holds only facts: no advice, no priority
   alfabeta made up, no estimated effort.

### Edge Cases

- A due date in January read in December: the year is the one nearest the capture date.
- An item edited after posting («Última modificación»): the window counts from the posting date, or
  from the first sync that saw its due date if the teacher added the date later.
- Two or more warnings on the same day: one event lists them all, nearest due date first.
- A public holiday or a weekend: warnings still sit at 16:00; the chromatography video's last
  warning falls on the 12 October holiday.
- Two steps of one item on the same day (a window of 2 days puts the half-window warning on the
  evening before): one warning.
- A class with dated work that is not in the timetable mapping: its warnings are still written
  (they need only the home slot); its exams are all-day and nothing is inferred for it; the run says
  which class.
- A school holiday on an inferred weekday: the timetable has no holiday calendar, so the inferred
  date is labelled as deduced and the family can correct it.
- Daylight-saving changes (the next one in March 2027).
- A sync that did not run: a warning for the next morning's work may not exist; the run that comes
  after says which items it could not warn about in time.

## Requirements *(mandatory)*

### Functional Requirements

**Where warnings go**

- **FR-001**: Warnings MUST be timed events in the student's calendar, in Spanish. Not Google Tasks:
  a task written through the API keeps only its date, so it cannot carry a 16:00 warning (Google
  Tasks API reference, read 2026-10-27).
- **FR-002**: Warnings and the daily list (FR-023) MUST reach two readers, each through their own
  account: the student and the operator. Delivery is checked per reader (FR-019).
- **FR-003**: A warning MUST restate facts only: the subject, the work as Classroom titles it, the
  due day (and hour when Classroom gives one), the days left, and a link to the item's folder in the
  Drive. Example: «Entrega en 3 días (martes 13 oct): Física y Química · Zuen kromatografiaren
  bideoa». No advice wording («empieza hoy», «date prisa»).
- **FR-004**: All warnings of one day MUST be one event at 16:00 listing every item, nearest due
  first.

**When**

- **FR-005**: No warning MAY exist after its item's due instant. A due date without a time MUST stay
  a date: no due hour is invented (Classroom's help does not say what time it means). For computing
  warnings only, its cutoff is the start of the due date, so its last warning is the day before.
- **FR-006**: Warnings MUST follow the window `g` = due date − start date (FR-007), in days, every
  warning at the home slot (FR-008):
  - last: the last home slot strictly before the due instant (or the cutoff of FR-005);
  - `g` from 2 to 7: also one on due date − ⌈g/2⌉;
  - `g` of 8 or more: also one on due date − 14 and one on due date − 7, plus due date − 28 when `g`
    exceeds 28;
  - any warning other than the last that falls on or before the start date is dropped; two steps of
    one item on the same day are one warning.
  - Worked example, the chromatography video (start Thursday 8 October, due 13 October, no time,
    `g` = 5): Saturday 10 October and Monday 12 October, both at 16:00.
- **FR-007**: The start date MUST be the posting date, or the date of the first sync that saw the due
  date if the teacher added it later. «Última modificación» MUST NOT move it.
- **FR-008**: The home slot MUST be one time for every day of the week, weekends and holidays
  included, read from the student's private configuration; the operator set it to 16:00.
- **FR-009**: When warnings for an item still ahead are already in the past (first run, late sync),
  they MUST become one warning at the next home slot.

**What changes them**

- **FR-010**: A status of «Entregado», «Calificado» or «Entregado con retraso» MUST remove the item's
  pending warnings and keep its due-date event. Any other status, or none, keeps them: status is not
  a reliable "done" (work handed in on paper reads «Sin entregar»).
- **FR-011**: A moved or removed due date MUST recompute or remove the item's warnings.
- **FR-012**: Every warning MUST have a stable identity per item and step, so a run with no change in
  Classroom creates, moves and deletes nothing.

**The timetable**

- **FR-013**: The timetable MUST live in the student's private configuration as sessions (weekday,
  start, end, subject), with Classroom classes mapped to subjects by class identifier, never by
  name (two of the twelve class names are not subject names). The repository holds only a template.
- **FR-014**: An exam MUST sit in its subject's session when the subject has exactly one session that
  day, labelled «hora según horario»; otherwise it is all-day. Exams come from stream announcements
  and from the family.
- **FR-015**: A known exam MUST get a warning 7 days before and one at the home slot of the day
  before.

**Due dates**

- **FR-016**: The due date MUST come from Classroom's due-date field. Only when it is empty, a due
  date MAY be inferred, and only when all hold: a weekday or date with a purpose form in the title
  or first line («-rako» in Basque, «para el» in Spanish, «for» in English); the subject has a session
  that weekday; it falls strictly after the posting date and within 7 days. The result is the next
  session of that subject, and the event says it was deduced and from which words.
- **FR-017**: Assignments with no due date MUST get no warning; they appear in the daily list
  (FR-023).
- **FR-018**: Posting events (material and assignments, all-day on the posting date) MUST stay as they
  are: they are the only calendar presence of the 37 undated assignments, and the constitution makes
  what is posted part of the agenda.

**Running and verifying**

- **FR-019**: Delivery to a reader MUST be considered unseen until the family watched a timed and an
  all-day test event arrive on that reader's phone; the check is recorded with its date and account,
  and each run says which readers are unchecked. alfabeta never states that a warning was received.
- **FR-020**: A warning for work due the next morning exists only if a sync ran between the posting
  and that evening's home slot. The run MUST say which items were first seen too late for any
  warning.
- **FR-021**: Times MUST be computed in `Europe/Madrid` with no hand-made offsets; tests MUST cover
  both daylight-saving changes with fixtures. A live check across a change waits for March 2027.
- **FR-022**: Nothing personal enters the repository: the timetable, the mapping, the home slot and
  the delivery checks live in the student's private configuration or data folder.

**The daily list**

- **FR-023**: Every sync MUST rebuild a list of the assignments not handed in, grouped and ordered as
  User Story 7 says, facts only, readable by both readers (FR-002).
- **FR-024**: The list's form, using only tools the family already has: [NEEDS CLARIFICATION:
  which account does the student open every day, and which of these is the list?
  (a) Classroom's own «Tareas pendientes» in the school account, ticked with the student's own
  «Marcar como completada», which alfabeta then reads as handed in (FR-010); alfabeta writes nothing
  new, and its daily 16:00 event adds only what that page lacks (exams, inferred dates).
  (b) Google Tasks in the student's personal account, written by alfabeta and ticked by him in Tasks
  or in his Calendar; alfabeta reads the ticks and restates them in the daily event for the
  operator. Needs a consent the student gives once, not yet tried.
  (c) Read-only: the body of the daily 16:00 event.]

  Measured 2026-10-27 in the school account, read only:
  - Classroom keeps a calendar per class with every item that has a due date. The school account
    also shows alfabeta's calendar. A due date with no time appears there as all-day.
  - «Tareas pendientes» grouped the pending work as: Asignado, 32 with no due date and 3 dated;
    Sin entregar, 11.
  - Google Tasks is enabled in the school account and empty. alfabeta cannot write to it: the school
    blocks third-party apps for under-18 users (Workspace admin help, read 2026-10-27).

  Documented, read 2026-10-27:
  - «Marcar como completada» turns the status into «Entregado», and the student can undo it. Work
    marked after the due date is recorded as late (Classroom Help 6020285).
  - A task created through the Tasks API keeps its date only. A task with a date shows in Google
    Calendar and can be ticked there (Calendar Help 9901136).

### Key Entities

- **Session**: one slot of the timetable — weekday, start, end, subject. Times are approximate (the
  timetable says so).
- **Class mapping**: a Classroom class identifier → a timetable subject.
- **Due date**: date, optional time, and where it came from (Classroom's field, inferred from named
  words, the family).
- **Warning**: item, step (start, a week before, last…), date and home slot, wording, stable identity.
- **Exam**: subject, date, source (stream post or family), placed session if any.
- **Home slot**: one time of day for every day (16:00).
- **Reader**: an account that reads the calendar, and the date its delivery was seen, if ever.
- **Daily list**: the assignments not handed in on the day of a sync, in three groups, each line a
  Classroom fact.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first run on the capture of 2026-10-26 writes 0 warnings for items past due and 0 for
  items handed in. Control: with FR-005 and FR-010 disabled, the same run writes 16 and 7.
- **SC-002**: Replaying the capture day by day, every dated item not handed in gets at least one
  warning before its due instant, except items posted and due with no home slot between (2
  measured), which the run names.
- **SC-003**: Replaying the capture from 7 September to 26 October gives at most one warning event
  per day, and the weekly count of days with a warning is reported; the operator accepts it before
  warnings are switched on (the panel measured about 3 a week with a draft rule set that had no
  half-window warning).
- **SC-004**: Inference over the 37 undated items of the capture yields exactly one due date, the
  Physics «Ostegunerako» one, at that Thursday's Physics session, and nothing else.
- **SC-005**: A second run with no change creates, moves and deletes 0 events.
- **SC-006**: Before warnings are on for a reader, a delivery check for that reader is on record.
- **SC-007**: Fixtures at both daylight-saving changes give the same wall-clock times as on any other
  day.
- **SC-008**: The chromatography video (Clarifications), replayed with a sync on 8 or 9 October,
  gets warnings on Saturday 10 and Monday 12 October at 16:00 and none on or after 13 October. Only a
  replay can test it: the capture of 2026-10-26 already reads it «Calificado». In live use the same
  outcome depends on a daily sync (julioarguello/alfabeta#13).
- **SC-009**: The daily list built from a capture has, group by group, the same items that
  Classroom's «Tareas pendientes» shows the student on the same day. The count of each group is
  reported, and no item Classroom reads as handed in appears.

## Assumptions

- Classroom shows due dates only in the forms measured on 2026-10-26: "D mon", "D mon, HH:MM", and a
  bare time that spec 001 resolves to the capture's date.
- The timetable holds for the whole school year; a change means editing the configuration.
- One home slot, 16:00 every day, by the operator's choice. On Monday and Tuesday classes end at
  16:00, so those warnings arrive as he leaves school.
- Of the 31 pending assignments with no due date in the capture of 2026-10-26, 21 were posted before
  12 October. Some of them may have been done on paper and never marked in Classroom, which the
  daily list cannot tell unless someone ticks them (FR-024).
- Classroom may already send the student its own "due within 24 hours" notification (Classroom Help
  6141557); whether it is on for his account has not been measured. Its existence does not change
  what this spec writes.
- Exams announced only orally reach the calendar only when the family declares them.

## Dependencies

- `classroom-sync` (spec 001): the capture, including stream exam posts and the bare-time due form.
- A scheduled sync, julioarguello/alfabeta#13, at least daily and before the earliest home slot.
- The family, to transcribe the timetable once, map the classes, and watch the delivery check on
  the student's phone; the operator checks his own account.
