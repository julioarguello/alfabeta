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
reads them. It also changes where in the day every event alfabeta writes is placed: no event is
all-day (FR-023). What it leaves: one colour per category (FR-020a of spec 001); the student's
checklist is Classroom's own page, not something alfabeta builds (FR-024).

Out of this spec: writing anything to Classroom; study blocks in the calendar; Google Tasks;
changing how Classroom is captured (a due date shown only as a time, "Fecha de entrega: 8:00", is
resolved against the capture's own date by spec 001, a dependency here); changing anyone's
notification settings, which only that person can do.

**Changes elsewhere once this spec is approved.** Four places say the calendar holds only
objective facts and no reminders: FR-025 of spec 002 (julioarguello/alfabeta#22), the roadmap's
Calendar section, the calendar policy line of the student's private configuration, and the
operator's standing instruction recorded outside the repository. The operator chose warnings that
restate facts (Clarifications, 2026-10-27), so the edit is narrow: "objective facts only" stays, and
each place gains "plus warnings that restate those facts". FR-025's ban on study
blocks stays whole. The two places in the repository, and the `study-pack` skill's line that
repeats FR-025, change in the pull request that approves this spec, with its plan.

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
- Q: Which account does the student open every day, and so where does the list live? → A: The
  operator left it to the design ("la que queramos"), with no new tools. Chosen: the school
  account. The list is Classroom's own «Tareas pendientes»; the student ticks with «Marcar como
  completada». Then one record holds the tick, the one the teacher sees and the one alfabeta reads
  (FR-010), and nothing new is built. Rejected:
  - Google Tasks in his personal account: a second record the teacher never sees, an app consent
    not yet tried, and Classroom would still read «Sin entregar».
  - A read-only list: nothing would ever clear it.
  Accepted cost: the teacher sees each mark, and a mark after the due date is recorded as late.
- Q: Where in the day does each event sit? → A (operator, 2026-10-27): no all-day events, because
  they go unnoticed. Postings and due dates sit in their subject's session that day; when the subject
  has no session that day, weekends and holidays included, at break time (10:00–10:25). The student
  has no phone in class, so a notification during class is seen later, and that is acceptable for
  these events. The warning that matters is the one ahead of the work: at 16:00 on the days the
  lead-time rule gives, and no fixed daily event. (The next answer turned each warning into a
  reminder on the item's own event.)
  Recorded interpretation: break time replaces "the previous day's session", which the operator
  first proposed for postings, and it applies to every event alfabeta writes.
- Q: How does a warning reach the student, if a reminder belongs to whoever sets it? → A: The
  operator: notifications only for the student; the operator wants none. The student will not set
  any. alfabeta gets its own Google connection (spec 004), authorised by the student's personal
  Gmail, and writes the events as that account. A reminder it puts on an event is then the
  student's own. The warning is a reminder on the due-date or exam event itself, at 16:00 on the
  days the lead-time rule gives. Postings carry none. There is one calendar and no warning events.
  The school account cannot be used: its administrator blocks third-party apps for under-18
  users.

### Plan, 2026-10-28

Decisions the plan took where the spec was silent or the data did not reach; each is in
[research.md](research.md).

- The last warning rings at or before its event's start: a reminder cannot ring after the event
  begins, and a due at 16:10 has its event from 15:40 (FR-006, research R4).
- Google allows at most 28 days (40,320 minutes) between a reminder and its event's start. When the
  28-days-before warning would exceed it, it rings the next day at the home slot (FR-006, research
  R4).
- FR-016 reads a weekday in the title only: the agenda, this spec's input, carries no description,
  and the one measured case is a weekday in a title (research R1, R9).
- "Exams come from the family" means the family's correction of an exam detected in Classroom (spec
  001 FR-020b). No path lets the family declare an exam Classroom does not show, and the calendar
  holds only Classroom's facts; an exam announced only orally is added by the family by hand, as a
  timed event alfabeta does not own and never changes (FR-014, research R8).
- An exam whose date carries a time starts at that time, labelled «hora según Classroom», and ends
  with the session that holds it, else 30 minutes later; no event runs past its day (FR-014,
  FR-023, research R3).
- A replay on the state the Mac holds when slice 2 is built cannot reproduce SC-001's 16 and 7:
  statuses have moved since the capture. SC-001 passes there when its own control is not 0
  (research R10).
- A linked subject with no session is the edge case's "not in the timetable mapping": events at
  break time and the run names the subject. A class not linked to a subject is not in the agenda at
  all (spec 001 proposes its link).
- An announcement gets no event of its own; the exam it announces does. A quiz is placed and warned
  like an assignment (FR-018, research R3).
- The delivery check on the student's phone (spec 004 T021) blocks building, not planning: the plan
  makes it gate 1, ahead of the first slice. A merged plan does not mean the check is done.
- What a delivery check puts in an issue or the repository is the date and the account's alias, no
  address and nothing that identifies the device (constitution III).
- An exam the family adds by hand carries no warning on the student's phone: a reminder belongs to
  the account that sets it, and the student sets none (FR-001, FR-015). Only exams in the agenda
  are warned.
- On the first run with `warnings = true`, every item's basis instant becomes that run's, so items
  whose steps passed while warnings were off get FR-009's one catch-up warning.
- An event whose fact left Classroom (a withdrawn item, a due date no longer shown, an exam the
  family discarded) is kept, loses its reminders and is titled «Retirado ·»; alfabeta deletes no
  event of its own (constitution V, research R7).

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

1. **Given** a Maths sheet posted on a Monday and due Tuesday at 08:00, and a sync on Monday before
   the home slot
   **When** warnings are computed, **Then** its due-date event (Tuesday 07:30–08:00)
   carries one reminder that rings at Monday's home slot.
2. **Given** an assignment whose status becomes «Entregado», «Calificado» or «Entregado con retraso»,
   **When** the next sync runs, **Then** its pending warnings are gone and its due-date event stays.
3. **Given** an assignment posted and due on the same day (2 measured), **When** no home slot exists
   between the sync and the due instant, **Then** no warning is written.
4. **Given** a due date without a time (6 measured), **When** warnings are computed, **Then** the
   last reminder rings at the home slot of the day before, and its due-date event says «Classroom no
   indica hora».

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
   it gets a first warning 14 days before when that day falls after the start date (28 days too
   when the window exceeds 28), one 7 days
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
2. **Given** a first run, **When** every warning of an item still ahead has a time that already
   passed, **Then** they become one warning at the next home slot (FR-009); warnings still ahead
   stay as they are.
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

**Independent Test**: the stream announcements of the capture, with the family's corrections, placed
against the timetable.

**Acceptance Scenarios**:

1. **Given** an exam on a day when its subject has exactly one session, **When** it is written,
   **Then** it sits in that session, labelled as a time taken from the timetable.
2. **Given** an exam on a day when its subject has no session, **When** it is written, **Then** it
   sits at break time, labelled as an hour not known.
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
3. **Given** an assignment with no due date and nothing inferable, **When** warnings are computed,
   **Then** it gets none, and it stays in Classroom's «Tareas pendientes» and as its posting event.

---

### User Story 6 - Nobody believes warnings arrive until someone saw one arrive (Priority: P1)

A reminder belongs to the account that sets it. It reaches nobody else, and nobody else can change
another account's notifications (Google's Calendar API reminders guide and Calendar Help 37242,
read 2026-10-27; measured the same day, FR-001). The warnings therefore exist only if alfabeta
writes as the student's personal Gmail (spec 004), and they ring only on a phone where that account
shows its calendar.

**Why this priority**: if nothing reaches him, every other story is decoration and the family stops
checking because "the calendar warns him".

**Independent Test**: a test event written as the student's Gmail with a reminder 10 minutes ahead,
watched on his phone by the family.

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

The list the student sits down with is Classroom's own «Tareas pendientes», in his school account
(Clarifications). He ticks with «Marcar como completada». alfabeta builds no list. The operator, who
cannot open the student's Classroom, sees what is pending in the calendar: every due-date event
says whether Classroom reads the work as handed in.

**Why this priority**: the only place undated work shows up after its posting day, and the only
tick the teacher also sees.

**Independent Test**: compare the due-date events of a capture, prefix by prefix, with what
«Tareas pendientes» shows the student the same day.

**Acceptance Scenarios**:

1. **Given** a dated assignment not handed in, **When** its due-date event is written, **Then** its
   title starts «Entrega ·»; **When** Classroom later reads it «Entregado», «Calificado» or
   «Entregado con retraso», **Then** the next sync retitles it «Entregado · …» and keeps it.
2. **Given** an item the student marked done, **When** the next sync runs, **Then** Classroom reads
   it «Entregado» and its warnings are removed (FR-010).
3. **Given** any event alfabeta writes, **When** it is read, **Then** it holds only facts: no advice,
   no priority alfabeta made up, no estimated effort.

### Edge Cases

- A due date in January read in December: the year is the one nearest the capture date.
- An item edited after posting («Última modificación»): the window counts from the posting date, or
  from the first sync that saw its due date if the teacher added the date later.
- Two or more items warned on the same day: each event rings on its own at 16:00; they are not
  merged.
- A public holiday or a weekend: warnings still sit at 16:00; the chromatography video's last
  warning falls on the 12 October holiday.
- Two steps of one item on the same day (a window of 2 days puts the half-window warning on the
  evening before): one warning.
- A linked subject with dated work and no session in the timetable: its warnings are still written
  (they need only the home slot); its events sit at break time and nothing is inferred for it; the
  run says which subject. (A class not linked to a subject is not in the agenda; spec 001 proposes
  its link.)
- A due time near midnight (23:59): the due-date event ends at the due instant and never runs into
  the next day.
- A school holiday on an inferred weekday: the timetable has no holiday calendar, so the inferred
  date is labelled as deduced and the family can correct it.
- Daylight-saving changes (the next one in March 2027).
- A sync that did not run: a warning for the next morning's work may not exist; the run that comes
  after says which items it could not warn about in time.

## Requirements *(mandatory)*

### Functional Requirements

**Where warnings go**

- **FR-001**: A warning MUST be a reminder on the item's own event (its due-date event, or its
  exam), set by alfabeta writing as the student's personal Gmail through its own Google connection
  (spec 004). There are no separate warning events and no second calendar. A reminder belongs to the
  account that sets it. Measured 2026-10-27: a test event that alfabeta's present writer account
  created with its own 37-minute reminder showed no notification to the student's school account
  or to the owner's account; both event pages read «Las notificaciones solo se aplican a ti», and
  the event was deleted afterwards. Not Google Tasks: a task written through the API keeps only its
  date, so it cannot ring at 16:00 (Google Tasks API reference, read 2026-10-27).
- **FR-002**: Reminders MUST ring for the student only. The operator reads the same calendar with no
  notifications, by the operator's choice. Delivery is checked on the student's phone (FR-019).
- **FR-003**: Event titles MUST restate facts only, because a reminder shows the event's title and
  time and nothing else. A due date reads «Entrega · Física y Química · Zuen kromatografiaren
  bideoa». The description adds the due day and hour when Classroom gives them, and the item's
  folder in the Drive. No advice wording («empieza hoy», «date prisa»).
- **FR-004**: A posting event MUST carry no reminder. A due-date or exam event carries only the
  reminders of FR-006 and FR-015, written explicitly, never the calendar's defaults.

**When**

- **FR-005**: No warning MAY exist after its item's due instant. A due date without a time MUST stay
  a date: no due hour is invented (Classroom's help does not say what time it means). The time its
  event is drawn at (FR-023) is not a due hour, and the event says «Classroom no indica hora». For
  computing warnings, its cutoff is the start of the due date, so its last warning is the day
  before.
- **FR-006**: Warnings MUST follow the window `g` = due date − start date (FR-007), in days, every
  warning at the home slot (FR-008):
  - last: the last home slot strictly before the due instant (or the cutoff of FR-005) and no
    later than the start of the item's event (FR-023);
  - `g` from 2 to 7: also one on due date − ⌈g/2⌉;
  - `g` of 8 or more: also one on due date − 14 and one on due date − 7, plus due date − 28 when `g`
    exceeds 28, moved to the next day while it would ring more than 40,320 minutes before the
    event's start (Google's limit);
  - any warning other than the last that falls on or before the start date is dropped; two steps of
    one item on the same day are one warning.
  - Worked example, the chromatography video (start Thursday 8 October, due 13 October, no time,
    `g` = 5): Saturday 10 October and Monday 12 October, both at 16:00.
- **FR-007**: The start date MUST be the posting date, or the date of the first sync that saw the due
  date if the teacher added it later. «Última modificación» MUST NOT move it.
- **FR-008**: The home slot MUST be one time for every day of the week, weekends and holidays
  included, read from the student's private configuration; the operator set it to 16:00.
- **FR-009**: When every reminder computed for an item still ahead falls in the past (first run,
  late sync), the item MUST get one reminder at the next home slot before the bound of FR-006 (its due instant or cutoff, and its event's start).

**What changes them**

- **FR-010**: A status of «Entregado», «Calificado» or «Entregado con retraso» MUST remove the item's
  pending warnings and keep its due-date event. Any other status, or none, keeps them: status is not
  a reliable "done" (work handed in on paper reads «Sin entregar»).
- **FR-011**: A moved or removed due date MUST recompute or remove the item's warnings.
- **FR-012**: Every event MUST have a stable identity per item, and its reminders are a function of
  the item and of the instant its current due date was first seen, so a run with no change in
  Classroom creates, moves, deletes and edits nothing.
- **FR-012a**: An event takes at most the number of reminders Google allows per event (spec 004
  verifies it); the rule of FR-006 never needs more than four.

**The timetable**

- **FR-013**: The timetable MUST live in the student's private configuration as sessions (weekday,
  start, end, subject), with Classroom classes mapped to subjects by class identifier, never by
  name (two of the twelve class names are not subject names). The repository holds only a template.
- **FR-014**: An exam MUST sit in its subject's session that day, labelled «hora según horario»;
  when the subject has no session that day, at break time, labelled «hora no conocida»; when its date
  carries a time, at that time, labelled «hora según Classroom». Exams come from Classroom: items and
  stream announcements, with the family's corrections (spec 001 FR-020b).
- **FR-015**: A known exam MUST get a warning 7 days before and one at the home slot of the day
  before.

**Due dates**

- **FR-016**: The due date MUST come from Classroom's due-date field. Only when it is empty, a due
  date MAY be inferred, and only when all hold: a weekday with a purpose form in the title
  («-rako» in Basque, «para el» in Spanish, «for» in English); the subject has a session
  that weekday; it falls strictly after the posting date and within 7 days. The result is the next
  session of that subject on that weekday, and the event says it was deduced and from which words.
- **FR-017**: Assignments with no due date MUST get no warning; they stay in Classroom's «Tareas
  pendientes» and as their posting event.
- **FR-018**: Posting events (material, assignments and quizzes; not announcements) MUST stay,
  placed by FR-023 on the posting date: they are the only calendar presence of the undated
  assignments, and the constitution makes what is posted part of the agenda. The time is the
  class's, not the moment of posting, which the capture does not hold; the event says so.

**Running and verifying**

- **FR-019**: Delivery MUST be considered unseen until the family watched a reminder that alfabeta
  set as the student's Gmail ring on his phone. The check is recorded with its date, and each run
  says whether it is on record. alfabeta never states that a warning was received. If the calendar
  also shows in his school account on that phone, each event appears twice; one of the two
  subscriptions is removed on the phone.
- **FR-020**: A warning for work due the next morning exists only if a sync ran between the posting
  and that evening's home slot. The run MUST say which items were first seen too late for any
  warning.
- **FR-021**: Times MUST be computed in `Europe/Madrid` with no hand-made offsets; tests MUST cover
  both daylight-saving changes with fixtures. A live check across a change waits for March 2027.
- **FR-022**: Nothing personal enters the repository: the timetable, the mapping, the home slot and
  the delivery checks live in the student's private configuration or data folder.

**Placement and the checklist**

- **FR-023**: No event alfabeta writes MAY be all-day. A posting, a due date without a time, and an
  exam without a time sit in their subject's session that day; when the subject has no session that
  day (weekends and holidays included), at break time (configured; 10:00–10:25 in the timetable of
  2026–2027). A due date with a time sits in a 30-minute event that ends at that time. An exam with a
  time starts at that time and ends with the session that holds it, else 30 minutes later. No event
  starts before 00:00 or ends after 24:00 of its day. Warnings sit at the home slot (FR-008).
- **FR-024**: The student's checklist MUST be Classroom's «Tareas pendientes» in his school account,
  ticked with his own «Marcar como completada». alfabeta never marks anything (constitution:
  read-only on Classroom) and writes no task anywhere. Google Tasks and any new surface are out
  (Clarifications). Each due-date event's title MUST say whether Classroom reads the work as
  handed in: «Entrega · …» while it does not, «Entregado · …» once it does.

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
- **Warning**: a reminder on an item's due-date or exam event — step (28, 14 or 7 days before, half
  the window, the evening before), the instant it rings (a home slot), set as the student.
- **Exam**: subject, date, source (a Classroom item, a stream post, the family's correction), placed
  session if any.
- **Home slot**: one time of day for every day (16:00).
- **Reader**: an account that reads the calendar. Only the student's Gmail has reminders, and the
  date its delivery was seen is recorded.
- **Placement**: where an event is drawn — its subject's session that day, else break time,
  or the due time for a timed due date. Never all-day.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first run on the capture of 2026-10-26 writes 0 warnings for items past due and 0 for
  items handed in. Control: with FR-005 and FR-010 disabled, the same run writes 16 and 7 on that
  capture; a replay on a later state, whose statuses have moved, passes when its own control is not
  0 (research R10).
- **SC-002**: Replaying the capture day by day, every dated item not handed in gets at least one
  warning before its due instant, except items posted and due with no home slot between (2
  measured), which the run names.
- **SC-003**: Replaying the capture from 7 September to 26 October reports the weekly counts of
  reminders, of days with a reminder and of all events; the operator
  accepts them before warnings are switched on (measured 2026-10-27 on that capture with these
  rules: 3.1 warning days a week).
- **SC-004**: Inference over the 37 undated items of the capture yields exactly one due date, the
  Physics «Ostegunerako» one, at that Thursday's Physics session, and nothing else.
- **SC-005**: A second run with no change creates, moves and deletes 0 events.
- **SC-006**: Before reminders are switched on, the delivery check of FR-019 is on record.
- **SC-007**: Fixtures at both daylight-saving changes give the same wall-clock times as on any other
  day.
- **SC-008**: The chromatography video (Clarifications), replayed with a sync on 8 or 9 October,
  gets warnings on Saturday 10 and Monday 12 October at 16:00 and none on or after 13 October. Only a
  replay can test it: the capture of 2026-10-26 already reads it «Calificado». In live use the same
  outcome depends on a daily sync (julioarguello/alfabeta#13).
- **SC-009**: The due-date events titled «Entrega ·» whose date is Classroom's are, item by item,
  the dated work of the linked classes that Classroom's «Tareas pendientes» shows as pending
  («Asignado» with a date, and «Sin entregar») on the same day. Not counted: inferred dues (FR-016),
  exams («Examen ·»), classes not linked to a subject, and items Classroom reads «falta según el
  profesor», which are listed apart.
- **SC-010**: A replay of the capture writes 0 all-day events and 0 events that cross midnight.

## Assumptions

- Classroom shows due dates only in the forms measured on 2026-10-26: "D mon", "D mon, HH:MM", and a
  bare time that spec 001 resolves to the capture's date.
- The timetable holds for the whole school year; a change means editing the configuration.
- One home slot, 16:00 every day, by the operator's choice. On Monday and Tuesday classes end at
  16:00, so those warnings arrive as he leaves school.
- Break time is 10:00–10:25 every day, as the timetable gives it. No subject has two sessions on one
  day in the timetable of 2026–2027, so "its session that day" is never ambiguous.
- Classroom's own class calendars in the school account keep showing a due date without a time as
  all-day; alfabeta cannot change them.
- Of the 31 pending assignments with no due date in the capture of 2026-10-26, 21 were posted before
  12 October. Some of them may have been done on paper and never marked in Classroom, which the
  calendar cannot tell unless the student ticks them in Classroom (FR-024).
- Classroom may already send the student its own "due within 24 hours" notification (Classroom Help
  6141557); whether it is on for his account has not been measured. Its existence does not change
  what this spec writes.
- Exams announced only orally reach the calendar only when the family declares them.

## Dependencies

- `classroom-sync` (spec 001): the capture, including stream exam posts and the bare-time due form.
- Spec 004, alfabeta's own Google connection: the student's Gmail authorises it once, and alfabeta
  writes the calendar as that account.
- A scheduled sync, julioarguello/alfabeta#13, at least daily and before the earliest home slot.
- The student's phone shows his personal Gmail's calendar in the Calendar app.
- The family, to transcribe the timetable once, map the classes, and watch the delivery check on
  the student's phone; the operator checks his own account.
