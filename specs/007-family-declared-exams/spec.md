# Feature Specification: Exams the family declares that Classroom does not announce

**Feature Branch**: `docs/183-spec-007-family-exams` (spec dir `007-family-declared-exams`)

**Created**: 2026-11-05

**Status**: Draft

**Input**: Operator's session, condensed: exam dates often reach the family on paper rather than in
Classroom. Give the family a command to declare such an exam with its subject and date, its source
shown as the family's, so that it enters the agenda; match it when the teacher later posts the same
exam, so it does not appear twice; say how the calendar writer treats it, given that spec 003's
writer is not built yet; and say how a correction or a cancellation works. Added by the operator in
review: an exam can be prepared with nothing declared (translated: "I want to prepare an exam without
it having to be declared"; «yo quiero preparar un examen sin que pueda estar declarado»). Tracked in
julioarguello/alfabeta#183.

## Context and scope

Spec 001 reads exams out of Classroom, and the family can correct one that was detected there
(FR-020b, `decision update-exam`). Spec 003 places the agenda's exams on the calendar and says, in
its Plan clarifications, that no path lets the family declare an exam Classroom does not show. An
exam announced only on paper or in class has no way in.

### What was measured before writing this

One exam round, with its dates on a sheet the family holds and none of them in Classroom:

| Exams on the sheet | State of the agenda after a full sync | What the family could do |
|---|---|---|
| 1 | A detected exam with no date, in a material that names the month | Give it a date with `decision update-exam` |
| 2 | A detected exam with no date, from a notice that may belong to an earlier exam | Nothing safe: a date there may correct the wrong exam |
| 4 | No entry at all | Nothing |

All seven were written to the family calendar by hand, through the chat's Calendar connector, as
events with no reminders. alfabeta does not own those events and never changes them (spec 003,
research R8). Spec 004 T022 later takes the connector's account off that calendar, which ends this
route for the chat.

### In scope

- A command that declares an exam, and the agenda entry it produces.
- Correcting and cancelling a declared exam.
- Matching a declared exam with the teacher's later post of the same exam.
- What spec 003's calendar writer does with a declared exam, as changes to that spec's design.
- Preparing an exam's sheets with no announcement and no declaration, as a change to spec 002 FR-030.

### Out of scope

- Building the calendar writer. Spec 003 slices 1 to 3 (julioarguello/alfabeta#134,
  julioarguello/alfabeta#135, julioarguello/alfabeta#136) build it; this spec only adds what it
  reads.
- A way to state an exam's scope more finely than by naming its topics.
- Reading paper: the family types the subject and the date; alfabeta reads no photo of a sheet.
- Assignments or anything else that is not an exam.
- Writing to Classroom (constitution IV).

## Clarifications

### Session 2026-11-08

| # | Question | Answer | Applies to |
|---|---|---|---|
| Q9 | The family names the topics but says the scope is narrower, «what is in his class notes». What happens to the topics' material the notes never touch? | It goes on the sheets marked DUDOSO, with its source, never left out and never taught as in scope (#213) | FR-027a |

### Session 2026-11-05

The operator accepted the first draft's proposal for Q1 to Q5 and Q7, changed Q6, and answered Q8. No
question is open.

| # | Question | Answer | Applies to |
|---|---|---|---|
| Q1 | The calendar holds only objective facts from Classroom (spec 002 FR-025). May it also hold an exam the family declares, labelled as the family's? | Yes: an exam date on a teacher's sheet is an objective fact, and its source is named on the event | User Story 4, FR-016 to FR-021 |
| Q2 | Does a sheet ever give the hour, and does an exam ever fall outside its subject's session? | Date only. The event sits in the subject's session («Hora según horario»), else at break time («Hora no conocida») | FR-002, FR-017 |
| Q3 | When the teacher posts an exam of that subject on another date, does Classroom win by itself? | No: both stay, and the agenda says they differ, until the family decides. The notice covers dates up to 14 days apart, a number nothing has measured | FR-012 |
| Q4 | A detected exam of that subject has no date, and the family declares a date. Is that the same exam? | Not by itself: the measured notices may belong to an earlier exam. Both stay, with a notice, until the family gives the detected one a date or discards it | FR-012 |
| Q5 | When the writer starts, what happens to the events written by hand? | alfabeta never touches them. Its run lists the ones that look like a declared exam, and the family deletes those by hand | FR-021 |
| Q6 | A declared exam has no announcement, so `exam build` refuses it. Should the family be able to prepare it anyway? | Yes, and with no declaration either. The family names the topics; the sheets cover all of them and say no announcement backs them | User Story 5, FR-025 to FR-029 |
| Q7 | Is a visible duplicate acceptable when the teacher later posts the same exam, so that matching is unnecessary? | No: they are matched (FR-011). Once the writer runs, a duplicate is two events and two sets of warnings for one exam | User Story 3, FR-011 |
| Q8 | Must an exam be preparable when the family does not know its date? | Yes. Where a date would go, the files and the sheets say «sin fecha» | FR-025 to FR-028 |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A date on paper reaches the agenda (Priority: P1)

The family holds a sheet with an exam date Classroom does not show. They run one command with the
subject and the date, and the exam is in `agenda.md`, in «Pendiente», sorted by its date, and it says
that the family declared it.

**Why this priority**: it is the whole gap. Six of the seven measured exams could not get a date in
the agenda at all, or not safely.

**Independent Test**: on the sandbox student, declare an exam for a subject with no exam in the
agenda, then read `agenda.md` and `agenda.json`. It needs neither the calendar nor a new capture.

**Acceptance Scenarios**:

1. **Given** a configured subject, a date in the school year and the run's lock (Claude takes it when the
   family asks in the chat), **When** the family runs
   `exam create --student <id> --subject <folder> --date YYYY-MM-DD`, **Then** the agenda holds one
   exam entry of that subject on that date, marked «declarado por la familia», with no Classroom
   link, and the answer gives its id (`declared-1`).
2. **Given** an exam the family already declared, **When** they run the same command again, **Then**
   nothing is written and the answer gives the existing id.
3. **Given** a subject that is not a configured one, or a date outside the school year, **When** the
   command runs, **Then** it writes nothing and exits 1 saying which of the two is wrong.
4. **Given** a declared exam whose date has passed, **When** a capture later than that date exists,
   **Then** the entry moves to «Hecho», as a detected exam does.

---

### User Story 2 - The family corrects or cancels what it declared (Priority: P1)

The teacher moves the exam, or the family read the sheet wrong, or the exam is cancelled. The family
uses the correction command it already has.

**Why this priority**: a wrong date in the agenda is worse than none, and paper changes with no
trace anywhere alfabeta reads.

**Independent Test**: on the sandbox student, declare an exam, move it, cancel it, restore it, and
read the agenda after each step.

**Acceptance Scenarios**:

1. **Given** a declared exam, **When** the family runs
   `decision update-exam --student <id> --origin declared-1 --date YYYY-MM-DD`, **Then** the same
   entry shows the new date, keeps its id and also reads «corregido».
2. **Given** a declared exam, **When** the family runs
   `decision update-exam --student <id> --origin declared-1 --discard`, **Then** it leaves the agenda,
   and its record stays.
3. **Given** a discarded declared exam, **When** the family corrects its date, **Then** it returns
   under the same id, as a discarded detected exam does (spec 001).
4. **Given** a declared exam, **When** the family asks to change its category, **Then** the command
   refuses and exits 1: a declared exam is an exam or it is cancelled.
5. **Given** a cancelled declared exam, **When** the family declares that subject and date again, **Then**
   a new id is created, and the cancelled one stays as it is.

---

### User Story 3 - The teacher posts it later, and it does not appear twice (Priority: P1)

Weeks after the sheet, the teacher posts the same exam in Classroom: an assignment titled as a test,
or a stream post or material that a run detects as an exam. The agenda keeps one line, and that line
gains what Classroom knows.

**Why this priority**: without it the feature makes the agenda worse: two lines and, later, two
events and two sets of warnings for one exam (Q7).

**Independent Test**: invented captures in which a declared exam's teacher post appears as each of
the three kinds, on the same day, on another day and with no date; run the sync and count the exam
entries of that subject.

**Acceptance Scenarios**:

1. **Given** a declared exam, **When** a run finds an exam entry of that subject on that same day,
   **Then** the agenda holds one entry, with the declared exam's id, marked «declarado por la
   familia», carrying the teacher's title, the Classroom link and the folder.
2. **Given** that matched entry, **When** the teacher moves the exam in Classroom, **Then** the entry
   follows the new date, under the same id.
3. **Given** that matched entry, **When** the teacher's post leaves Classroom, **Then** the entry
   goes back to the family's own date and title, with no Classroom link, and the run says so.
4. **Given** a declared exam, **When** a run finds an exam of that subject with no date, or up to 14
   days away, **Then** both entries stay and a notice at the top of `agenda.md` says they differ.
5. **Given** that notice, **When** the family gives the Classroom exam the declared date, **Then**
   the next rebuild of the agenda makes the two one entry, and the notice goes.
6. **Given** an exam of that subject already in the agenda on that day, **When** the family declares
   it, **Then** nothing is created and the answer names the entry that already holds it.

---

### User Story 4 - The calendar writer treats it as an exam, and says whose it is (Priority: P2)

Once spec 003's writer exists, a declared exam gets the same event and the same warnings as any
other exam. Unlike an event added by hand, it rings on the student's phone, because alfabeta sets the
reminder as the student's account (spec 003 FR-001).

**Why this priority**: it is what the seven events written by hand lacked, but it cannot ship before
the writer does, and the agenda alone already gives the family a record.

**Independent Test**: spec 003's `calendar replay` over an agenda holding a declared exam: read its
event, its warnings, and what a date correction, a match and a cancellation do to them. Before the
writer exists, the agenda's entry is checked against spec 003's data model only.

**Acceptance Scenarios**:

1. **Given** a declared exam and no writer yet, **When** anything runs, **Then** alfabeta writes
   nothing to the calendar for it, and the family's hand-written events stay as they are.
2. **Given** a declared exam and the writer, **When** the calendar is synced, **Then** the exam has
   one event titled `Examen · <Asignatura> · <título>`, placed as spec 003 FR-014 says, whose
   description says «Declarado por la familia».
3. **Given** that event, **When** the date is corrected or the teacher's post is matched, **Then**
   the same event moves or gains the Classroom link, and it is never «Retirado ·» (FR-018 names the one
   other event a match can retire).
4. **Given** a cancelled declared exam, **When** the calendar is synced, **Then** its event stays,
   loses its reminders and is titled «Retirado ·» (spec 003 research R7).
5. **Given** events the family wrote by hand on the day of a declared exam, **When** the writer first
   places that exam, **Then** those events are untouched and the run names how many it found.

---

### User Story 5 - An exam can be prepared with nothing declared and nothing announced (Priority: P1)

The family knows an exam is coming. The teacher posted no announcement, the family may not have
declared it, and its date may not be known. They run `exam build` naming the topics, and the two sheets
print over all of them. Today
the command refuses: `no_exam` when the agenda holds none that day, `no_announcement` when it holds one
with no captured announcement.

**Why this priority**: the sheets matter most for the exams that reach the family on paper, and those
are exactly the ones the command refuses. It needs nothing from User Stories 1 to 4 and can ship first.

**Independent Test**: the refusals and what is passed to the notebook, with the stand-in for `nlm` of
spec 002's tests. What the sheets say needs a real notebook, as spec 002 User Story 7 says.

**Acceptance Scenarios**:

1. **Given** no exam of the subject in the agenda, **When** the family runs
   `exam build --student <id> --subject <folder> --exam YYYY-MM-DD --topic <folder>`, **Then** both
   sheets print in the topic's `exam/` folder under that date, and the agenda and the calendar do not
   change.
2. **Given** a declared exam with no announcement, **When** the family runs the command with `--topic`,
   **Then** both sheets print for that exam's date.
3. **Given** no captured announcement, **When** the command runs with no `--topic`, **Then** it refuses
   with `no_announcement`, says to name the topics, and asks the notebook for nothing.
4. **Given** no exam of the subject to come in the agenda, **When** the family runs
   `exam build --student <id> --subject <folder> --topic <folder>` with no date, **Then** both sheets
   print, and the files and the sheets say «sin fecha» where the date would go.
5. **Given** no announcement, **When** the theory sheet prints, **Then** it opens saying that no
   announcement backs it and it covers the whole of the topics named, its sections follow the student's
   scheme, and it leaves out nothing.
6. **Given** a captured announcement, **When** the command runs, **Then** it behaves as today.
7. **Given** no exam of the subject in the agenda, **When** the command runs with no `--topic`, **Then**
   it refuses with `no_exam`, says to name the topics, and asks the notebook for nothing.
8. **Given** another exam of the subject to come in the agenda, **When** the family runs
   `exam build --student <id> --subject <folder> --topic <folder> --undated`, **Then** both sheets print
   «sin fecha» over that topic, and that other exam and its announcement play no part.
9. **Given** no announcement and two whole topics, **When** the family names both with `--topic`, **Then**
   each topic's notebook gets its two sheets and an equal part of the slot.

### Edge Cases

- **The base folder is not there** (Drive not mounted): the declaration is recorded and the command
  says the agenda was not rewritten; the next `agenda build` or `classroom apply` writes it.
- **A subject with no linked class**: the declaration is accepted if the subject is configured. A
  subject the teacher does not use Classroom for is the plainest case of this feature.
- **A date on a weekend**: accepted, and the answer says so, because it restates the weekday. Holidays
  are not known (spec 003 has no holiday calendar).
- **A date in the past**: accepted, and the answer says so. It reads «Hecho» once a later capture
  exists, and it gets no warning (spec 003 FR-005 and R4).
- **Two exams of one subject on one day**: one entry. The timetable has no subject twice on one day
  (spec 003, Assumptions), and the agenda still says there is an exam that day.
- **Two declared exams brought onto one day by a correction**: the correction is refused and exits 1;
  the family cancels one.
- **Two declared exams brought onto one day by the teacher moving a matched one**: nothing the family did
  can be refused, so both entries stay and a notice says so; the family cancels one.
- **Two matches of one declared exam that part ways** (the teacher moves one of them): the one that no
  longer shares the entry's day stops being matched, appears on its own, and FR-012's notice can fire.
- **A matched first entry that loses its date**: the family's date stands, so the entry keeps a date and
  its event is never «Retirado ·».
- **A wrong subject or title**: there is no correction of those. The family cancels and declares
  again, with a new id; once the writer runs, that leaves one «Retirado ·» event.
- **A second teacher post of a matched exam on the same day** (an assignment and a stream post): it
  joins the same entry; the first one matched keeps giving the title and the link.
- **A Classroom exam that already had its event**, joined to a declared exam by a correction or by the
  teacher: its event becomes «Retirado ·», with no reminders. If the Classroom exam was on the same day all
  along (the family corrected the declared one onto it), that event sits beside the live one; accepted, because
  it is rare and alfabeta deletes no event of its own.
- **A match that was wrong**: the family discards the declared exam, and Classroom's own entry comes
  back alone (FR-014).
- **The declared exam is the subject's next one and has no announcement, and a later exam has one**:
  with no `--exam` the command means the next one, so it refuses without `--topic` and prepares that
  exam with it. The family names the later exam with `--exam`.
- **An announcement arrives after the sheets printed**: nothing is regenerated by itself. The family
  runs the command again, and the announcement then sets the scope.
- **Another exam of the subject to come in the agenda, and the family prepares a different one with no date**:
  `--undated` says so. With no `--undated` and no `--exam`, the command means the agenda's next exam, and its
  announcement, if it has one, sets the scope.
- **A date becomes known after sheets printed «sin fecha»**: the family may run the command again with
  `--exam`. That prints dated files beside the undated ones, which stay until the family removes them.
  A second run with no date replaces the undated files, as a second run on one date does today.
- **A detected exam with no date and a captured announcement**: with `--topic` and no date, its
  announcement is not used, because nothing says it is this exam (Q4). Giving that exam a date with
  `decision update-exam` makes it the exam the command finds, with its announcement.
- **No problem photocopies in the notebook** (a subject the teacher does not use Classroom for): the
  problems sheet says so in a sentence and invents no problem. Problems solved in the notes still
  appear, with «Enunciado no disponible» when no source holds their statement (spec 002 FR-034).
- **The family scopes the exam to the class notes, and a topic holds more**: a Classroom item or a textbook
  lesson of a topic named that the notes never touch goes on the sheets as DUDOSO, with its source (FR-027a);
  it is not dropped to fit.
- **The topics named hold more than the slot allows**: the sheet prints and the command reports its page
  count, as spec 002 FR-031 already does; it is not cut to fit, because no source says what is out.
- **The family stops declaring and keeps writing by hand**: nothing changes; a hand-written event is
  still an event alfabeta does not own (spec 003, Plan clarifications).

## Requirements *(mandatory)*

### Functional Requirements

**Declaring**

- **FR-001**: alfabeta MUST offer this command, which records one declared exam as a decision of the
  family, in force at once and never a proposal of Claude's:
  `exam create --student <id> --subject <folder> --date YYYY-MM-DD [--title <text>] [--dry-run]`.
  Its `--subject` is a `[[subjects]] folder`, as in `exam build`. `--dry-run` gives the same answer and writes
  nothing (`.claude/rules/python-cli.md` §10), so a date can be checked before it is recorded.
- **FR-002**: The date MUST be a full date with no time and inside the configured school year (Q2).
  Anything else, a malformed value included, writes nothing and exits 1, and the message names the option,
  never its value. `decision update-exam --date` MUST parse its value the same way for any origin, and
  check the school year for a declared exam.
- **FR-003**: Each declared exam MUST have a stable id, `declared-<n>`, numbered per student and never
  reused, not even after a cancellation. It does not depend on the subject or the date, so a
  correction never changes it (constitution V).
- **FR-004**: A declared exam is **active** while it is in force and not cancelled. Its **effective date** is
  the one its entry shows (data model). Declaring a subject and date that an active declared exam holds
  as its effective date MUST write nothing and give the existing id, with exit 0. So MUST declaring a day
  on which the agenda already holds an exam of that subject from Classroom; the answer names that entry
  and no declared exam exists. A cancelled exam holds nothing, so declaring its date again makes a new id.
- **FR-005**: The answer MUST restate the subject, the date and its weekday, so a mistyped date
  shows, and MUST say when the date falls on a weekend or has passed. These do not refuse it.
- **FR-006**: The agenda MUST be rewritten before the command ends, by the same rule as `agenda build`
  (only if its bytes change). If the base folder is missing, the decision stays recorded and the
  command says the agenda was not rewritten.

**The agenda entry**

- **FR-007**: A declared exam MUST be one agenda entry: `category` exam, its id as `item`, its subject
  and date, the title the family gave or none (no title is invented), and a mark that its source is
  the family. `agenda.md` MUST read, with no Classroom link while no teacher post matches it:
  `<fecha> · <Asignatura> · examen · <título> · declarado por la familia`.
- **FR-008**: Its list MUST follow spec 001 FR-020c, with no dependence on the day the agenda is
  generated: «Pendiente» while no capture of any of the student's classes is later than its date,
  «Hecho» once one is, and none once it is cancelled. Any class counts, because no single class holds
  the fact and the subject may have none linked.

**Correcting and cancelling**

- **FR-009**: `decision update-exam` MUST accept a declared exam's id as `--origin`, with `--date` and
  `--discard` meaning what they mean for a detected exam: a correction that prevails and adds to the
  one before, a discard that takes it out of the agenda, and a date on a discarded exam that brings it
  back. `--category` on a declared exam MUST exit 1. The entry MUST read «corregido» after a date
  correction. The agenda MUST be rewritten as in FR-006.
- **FR-010**: Nothing is deleted: a correction or a cancellation keeps the earlier record as
  superseded, as every decision does (spec 001 data model; constitution V).

**Matching**

- **FR-011**: Whenever a run builds the agenda, a declared exam in force MUST be matched with every
  exam entry from Classroom of the same subject on the same day in `Europe/Madrid`, whether it is a
  Classroom item or a detected exam, and however it reached that day. The match MUST be recorded as a
  decision the first time and hold from then on, so a second run writes nothing. A matched Classroom
  entry MUST NOT appear on its own. The one entry:
  - keeps the declared exam's id and its «declarado por la familia» mark;
  - takes from the first entry matched its title, its Classroom link, its folder, its time if it has
    one, and its status;
  - takes its list from spec 001 FR-020c, applied to that status and to the entry's own date, with
    FR-008's any capture: a family's later date keeps it in «Pendiente» after Classroom's old date passes;
  - takes from a detected exam among them, preferring one whose item has a captured announcement, its
    `origin`, so `exam build` finds the announcement as it does today;
  - takes its date from Classroom, unless the family corrected the declared exam after the match, in
    which case the correction prevails as in spec 001 FR-020b, and a notice says Classroom differs; with no
    Classroom date, the family's date stands;
  - stops being matched with a Classroom entry that no longer shares its day, other than the first, which
    it follows. That entry appears on its own, and FR-012 applies.
- **FR-012**: A Classroom exam of the same subject that is not on that day MUST NOT be matched by
  itself. While both are in «Pendiente», and the Classroom exam has no date or a date up to 14 days
  from the declared one, a notice at the top of `agenda.md` MUST say so (spec 001's notice: a line
  while a condition holds, never in `agenda.json`), such as «Examen de `<Asignatura>`: la familia dijo
  `<fecha>` y Classroom dice `<fecha>`». The family settles it with what exists: giving the detected
  exam the declared date joins them (FR-011); discarding either leaves the other.
- **FR-013**: A matched entry whose Classroom entries all leave the agenda (withdrawn, discarded by the
  family, corrected into another category) MUST go back to the family's own date and title with no
  Classroom link, under the same id, and the run's summary MUST say so. The family's fact stands until
  the family cancels it.
- **FR-014**: Discarding a matched declared exam MUST cancel only the family's declaration: the match
  ends, and Classroom's own entries return under their own ids. A Classroom item the family cannot
  discard stays a fact of the agenda (spec 001 FR-020b offers no such correction).
- **FR-015**: Only an active declared exam MUST be matched or take part in a notice. Two active declared
  exams of one subject that a teacher's move puts on one day MUST stay two entries, with a notice.

**The calendar writer** (spec 003's design, no calendar code here)

- **FR-016**: The writer MUST treat a declared exam as an agenda entry with `category` exam: it owns
  one `exam` event while it has a date, and nothing in spec 003 reads a separate list. Until the writer
  exists nothing writes it to the calendar; this spec's agenda slice does not wait for the writer, nor
  the writer for it.
- **FR-017**: Its placement MUST be spec 003 FR-014's: its subject's session that day, «Hora según
  horario»; else break time, «Hora no conocida»; once a matched entry has a time, that time, «Hora según
  Classroom». No event is all-day (spec 003 FR-023).
- **FR-018**: Its event MUST be titled as any exam's, `Examen · <Asignatura> · <título>`, or
  `Examen · <Asignatura>` with no title. Its description MUST carry «Declarado por la familia» and,
  only once matched, the Classroom line. The event's identity comes from the declared exam's id, so a
  correction or a match moves or rewrites that one event. The one «Retirado ·» a match can leave is a Classroom
  exam's own earlier event, when the exam that already had it joins a declared exam: the agenda no longer lists
  that item, and spec 003 research R7 keeps the event, with no reminders.
- **FR-019**: Its warnings MUST be spec 003 FR-015's, with the declaration's date as the start date
  that drops a warning, as an announcement's posting date does (spec 003 research R8), and the same
  bound and catch-up. Delivery is not promised before spec 003 FR-019's check is on record.
- **FR-020**: A cancelled declared exam's event MUST stay, lose its reminders and be titled
  «Retirado ·», per spec 003 research R7; a date correction on it brings it back.
- **FR-021**: The writer MUST NOT change, adopt or delete an event it does not own, and
  `calendar delete-legacy` keeps selecting only what spec 003 research R7 says, which excludes timed
  events. When it first creates a declared exam's event, the writer MUST count the events with no
  alfabeta mark and «examen» in their title, ignoring case, on that day, print only the count, and keep their date and
  title in the run's report in the data folder. The family deletes those by hand (Q5). A declared exam with
  no Classroom link matches no legacy event, because it has no Classroom title to compare.

**Privacy and running**

- **FR-022**: The family's title and the date MUST stay in the decisions, the agenda and the calendar.
  They MUST NOT reach a log line, an error message, a URL, an issue or a pull request: logs use the
  opaque id (constitution III). The tests hold invented subjects, dates and titles only.
- **FR-023**: Every `exam create` and every declared exam's correction MUST follow the run lock's rule
  of the `decision` commands. No new configuration key is read.
- **FR-024**: Two runs in a row with no change in Classroom and no new decision MUST write nothing for
  declared exams: no decision, no agenda bytes and, once the writer exists, no event (constitution V).

**Preparing an exam with no announcement** (a change to spec 002 FR-030)

- **FR-025**: `exam build` MUST NOT need an announcement, an agenda entry or a date when the family
  names the exam's topics with `--topic`: naming them is the family's statement of the scope. With no `--exam` it
  still means the subject's next exam in the agenda; the preparation is undated when the agenda holds none to
  come, or when the family says `--undated` (Q8), which needs `--topic`, excludes `--exam`, and ignores the
  agenda and its announcements. With no announcement, `--topic` MAY
  name several topics of any kind: each topic's notebook gets its sheets and an equal part of the slot. With
  an announcement, spec 002 FR-045's limit to subtopics of one topic stands.
- **FR-026**: With no announcement and no `--topic` it MUST keep refusing with `no_announcement`,
  because the subject's most recent topic is a guess at the scope that only an announcement can
  excuse; when the agenda holds no such exam, with `no_exam`. Each message says to name the topics, and
  the notebook is asked for nothing.
- **FR-027**: With no announcement the scope MUST be the whole of the topics named. Nothing is left out (FR-027a),
  because no source says it is out (spec 002, Clarifications). The theory sheet's sections MUST follow
  the student's scheme, or the order of the sources where the notes hold none (constitution X). The scheme
  leads the structure and the wording, not the facts: a fact in the notes that the photocopies or the book
  contradict is taught as the source states it, and the sheet says his page says otherwise, unless the
  notes insist on it, or the sources disagree with each other: then the notes' version stays, the section says
  nothing against it, and a last part titled «Para la familia» gives both versions (constitution X, spec 002
  FR-046). A branch no source explains is named, not developed, and goes there too (constitution X). The
  corrections `notebook/bloques.md` already holds, external references' and the family's rulings included, MUST
  reach the prompts, which `exam build` reads itself, and the sheet tells the student about each. Both
  sheets MUST say on their first page, in Spanish, that no announcement backs them and the scope is not
  confirmed; no announcement is invented or quoted.
- **FR-027a**: With no announcement, when the family's words narrow the topics named, for example «what is in
  his class notes», a part of those topics the notes never touch, a Classroom item or a textbook lesson, MUST be
  neither left out nor taught as in scope (Q9). The sheets MUST mark each such part DUDOSO, name its source and
  say the exam may not include it. DUDOSO means the scope is unconfirmed, never optional: the part stays on its
  nearest branch (constitution X), and it is not FR-049's mark of spec 002, because a Classroom item is a class
  source. The family's narrower scope is a source for what enters, not for what is out (spec 002, «an exclusion
  needs a source»). `notebook/bloques.md` lists those parts one line each, with its source and the family's
  words, under a heading «Dudoso, con su fuente» at the same or a higher level than «Correcciones a los
  apuntes», never under it, and whose text never holds those words, so no line of it reaches
  `{notes_corrections}`. `exam build` does not read that heading yet (T031). Until it does, the family may add a
  subject standing rule (spec 009) naming each part and its source, and remove it after the exam; while it
  stands it reaches every piece of the subject made, not only the exam sheets.
- **FR-028**: Preparing an exam MUST NOT declare it: it writes no decision and no agenda entry and owns
  no event. A date only names the printed files and the sheets' day.
- **FR-028a**: An undated preparation MUST say «sin fecha» where the date would go: the files are
  `exam/Teoría para el examen · TNN[X] (sin fecha).pdf` and `exam/Problemas tipo · TNN[X] (sin fecha).pdf`,
  the notebook's pieces belong to the moment «EXAMEN sin fecha», and neither sheet names a day. The
  answer's exam date and the pack record's are empty; no date is invented, not even the day it was made.
- **FR-029**: A captured announcement MUST keep setting the scope exactly as spec 002 FR-030 says, also
  when `--topic` is given. The command's answer MUST say, at its top level, whether an announcement backed the sheets. It is the
  one change to an announced exam's answer.

### Key Entities

- **Declared exam**: the family's statement that an exam exists. Id `declared-<n>`, subject folder,
  date, optional title, the date it was declared. A decision in force from the moment it is made.
- **Exam match**: a recorded link from one Classroom exam entry (an item, or `<item>#exam-<k>`) to one
  declared exam. Many entries may point to one declared exam; it ends when the declared exam is
  cancelled, or when that entry leaves the agenda.
- **Agenda entry** (spec 001): gains the mark that its source is the family. Its `classroom_link` is
  empty until matched; its `detected` and `origin` stay as they are, true and set only once matched
  with a detected exam, so spec 001's rule that an entry has an origin exactly when it is detected
  holds. A declared exam's `posted` (research R9) is its declaration date.
- **Notice** (spec 001 and spec 005): the line at the top of `agenda.md` saying a declared exam and a
  Classroom exam of the subject differ. Not an entry.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Asked in the chat, Claude puts an exam from a sheet in the agenda with one command under the
  run's lock, as with every `decision` command, and the agenda shows it, marked as the family's, when that
  command ends.
- **SC-002**: With invented fixtures of the measured round (seven exams: one detected with no date in
  a material, two detected with no date in older notices, four with no entry), all seven have a dated
  entry after their declaration, and the detected ones with no date have not been changed by it.
- **SC-003**: In fixtures where the teacher posts a declared exam as an assignment titled as a test,
  as a stream post detected as an exam, and as a material detected as an exam, on the declared day,
  the agenda holds exactly one exam entry of that subject on that day in every case. Control: with
  matching disabled, it holds two.
- **SC-004**: Across declaration, date correction, match, teacher's move and loss of the teacher's
  post, the entry's id never changes. Once the writer exists, the same sequence in `calendar replay`
  gives one event per declared exam, and that event reads «Retirado ·» only after a cancellation.
- **SC-005**: A second run with no change writes no decision, no agenda bytes and no event.
- **SC-006**: An agenda with no declared exam is byte for byte what it is today, apart from any version
  or key the schema gains, so the feature costs nothing to a family that never uses it.
- **SC-007**: No log line, error message or run report outside the data folder holds a declared exam's
  title or date; a test plants a marker title and looks for it.
- **SC-008**: `exam build` gives the same answers as today for every exam with a captured announcement,
  apart from the new `announced` key, and a declared exam matched with a detected one finds that
  announcement, also when two detected exams share the day and only one has it.
- **SC-009**: With no announcement, no agenda entry and no date, the family gets both sheets from one
  command that names the topics, with the agenda's bytes unchanged. Without the topics, the notebook
  receives no request at all (a test counts them with the stand-in).
- **SC-010**: On the first real run with no announcement, on a topic with a correction in `bloques.md`, the sheet
  teaches the source's fact, each top-level branch of the topic's scheme has
  a section on the theory sheet, the first page of both sheets says no announcement backs them, any branch no source explains is in
  «Para la familia», and the problems sheet holds only problems from the sources, or says it has none. The family reads this on the
  printed sheets; nothing measures it before that run.

## Assumptions

- The family reads the sheet and types what it says; a misread is corrected with FR-009. alfabeta
  checks only that the subject is configured and the date is in the school year.
- The family, or Claude in the family's chat at the Mac, runs the command. Nothing here adds a path
  from the phone or for the student, and it adds no account.
- An exam is one sitting of one subject on one day; a second exam the same day is rare enough to be
  one entry (Edge Cases).
- The 14 days of FR-012 are not measured (Q3): only long enough to catch a moved exam without warning
  about next month's exam.
- A cloud run reads the same decisions as the Mac, so a declared exam reaches its agenda as a correction
  does today. Whichever spec builds a cloud rebuild of the agenda also records matches (FR-011). Drive, and with it every account the school-year folder is shared with, receives `agenda.md` with the next run that uploads, not at once.
- `exam create` names a noun and a verb the vocabulary already has (`.claude/rules/cli-naming.md`):
  `create` is "make one object". The `exam` group's meaning widens from the sheets to the exam. It is
  not a `create-exam` leaf of the `decision` group, because a noun with two verbs may not join them as
  suffixes, and the correction keeps the built `decision update-exam` rather than a second command for
  the same act.

## Dependencies

- Spec 001: the agenda, its decisions, `decision update-exam`, `agenda build` and the notices.
- Spec 003 slices 1 to 3, for User Story 4 only. User Stories 1 to 3 need nothing from it.
- Spec 002 FR-030, which this spec changes for an exam with no announcement. Prompts with no announcement
  are new: nothing has measured how the notebook does on them (SC-010).
- `tests/test_cli_naming.py`: `exam create` is in `PLANNED` with this spec, so the grammar test holds
  from this pull request on.

## Changes elsewhere once this spec is approved

The specs and the sentences on the calendar's policy change in this pull request, as spec 003's own did.
What a person or an agent would act on today lands with the slice that builds it, so `main` never
instructs a command that refuses (research R12).

| Where | Change |
|---|---|
| Applied here. Spec 003: Plan clarifications («"Exams come from the family" means…»), FR-014's last sentence, Key Entities' Exam, last Assumption | A family can declare an exam (this spec); a hand-written event stays out of alfabeta's reach |
| Applied here. Spec 003: research R7 and R8; tasks T003 and T004 (a note on the order); data model `posted` and the ownership table; `contracts/events.md` (the «Classroom: <link>» line is no longer "always"; add «Declarado por la familia»); `contracts/cli.md` (FR-021's count) | The writer's design for a declared exam; its building is this spec's slice 3 |
| Applied here. Spec 002 FR-025 and its Clarification on the calendar; the line of `skills/study-pack/SKILL.md` that repeats it; `README.md`; `docs/roadmap.md`; `docs/explanation/study-material.md` | "Facts from Classroom" gains "and exams the family declares, labelled as such". The ban on study blocks stays whole |
| Applied here. Spec 001 FR-020b, FR-020c's table; data model (Decision, Agenda entry, language of names); `contracts/cli.md` (`decision update-exam`'s origin, and a pointer to this spec's contract) | The declared exam as a decision and an entry, marked as designed and not built |
| With slice 2. `contracts/agenda.schema.json` and its copy, whose `classroom_link` may be empty and whose new key marks the source (research R9: version 2 always carries `posted`); `skills/classroom-sync/SKILL.md` | `agenda.md`'s line prints the Classroom link only when there is one; how the family's request becomes the command, and the notices relayed in the summary |
| Applied here. Spec 002: FR-030, FR-046 (a family's answer against the notes moves the line to «Correcciones a los apuntes»), the requirement that names the sheets' files, Clarifications on the exam's scope and on the `exam/` folder, User Story 7's scenario 2, the Edge Case and Assumption on exams announced only in class, `contracts/cli.md` | An exam with no announcement or date is prepared when the family names its topics (FR-025 to FR-029), marked as designed and not built |
| With slice 1. `skills/study-pack/prompts.md`, the section of `skills/study-pack/SKILL.md` on the day before an exam and its lines on `bloques.md` | The new prompts, how to run the command with no announcement, and the format of «Correcciones a los apuntes» |
| Applied here. Constitution, Technical constraints › Storage («the date goes in each file's name») | 2.6.0 → 2.7.0, MINOR, because it allows what the sentence forbade: the exam's date when it is known, else «sin fecha» |
| Outside the repository | The calendar policy line of the student's private configuration, and the operator's standing instruction, as spec 003 already records for its own change |
