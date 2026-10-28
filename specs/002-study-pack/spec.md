# Feature Specification: A topic's study material, prepared in its notebook and on paper

**Feature Branch**: `docs/21-spec-002-study-pack` (spec dir `002-study-pack`)

**Created**: 2026-10-26

**Status**: Draft

**Input**: Operator's description (translated from Spanish and condensed): "Prepare in advance the
material the student needs, to cut the time spent preparing exams. Short explainer videos in
Spanish; if the subject is taught in Basque or English, explain in Spanish and give the terms in
that language. Sources: the textbook, what the teacher posts in Classroom, and the student's own
class notes. The parent is the 'teacher' at home, knows no Basque, and needs material in Spanish.
Name every generated piece so it is obvious what it is. Do not overwhelm the student. One notebook
per topic. Make videos when Classroom moves to a new topic. And be able to print all of it, mind
maps included, filed in the Drive."

## Context and scope

This is the third epic that [spec 001](../001-classroom-sync/spec.md) names, «Prepárame el tema»
("prepare the topic for me"), tracked in julioarguello/alfabeta#21. It takes the
topic folder that the textbook capture and `classroom-sync` (spec 001) fill, and turns it into
material to study from: inside the topic's Gemini Notebook notebook for the student, in a
`docente/` folder for the parent, and in one printable document for paper.

The procedure was run by hand on one topic on 2026-10-26, as the `study-pack` skill
(julioarguello/alfabeta#20). This spec states what that procedure must guarantee so it can run
without someone watching; the measurements behind each requirement are in
[About preparing study material in advance](../../docs/explanation/study-material.md) and in the
skill's own table of measured behaviour.

Out of this spec: writing to Classroom or to the textbook platform, the calendar beyond the facts
spec 001 puts there and the two links of FR-026, audio overviews, and recognising handwriting in the class-note
photos (it is a dependency, not a requirement here).

## Clarifications

### Session 2026-10-26

- Q: When are the videos made? → A: When Classroom shows material in a new topic, judged by
  Classroom's posting dates; the previous topic is then finished. An announced exam makes the pack
  at once, whatever the dates say. Revised by the operator the same day: the goal is study day by
  day, so material is made as the teacher's content arrives, not only when a topic ends; detecting
  the end of a topic is not deterministic, so err on making too much rather than too little; an
  announced exam is a clear trigger to make more, early enough to be used; and nothing for the
  student is labelled optional, because what is optional does not get done. Settled in three
  moments that need no end-of-topic detection: «HOY» on every new material, «REPASO SEMANA» on a
  fixed weekday, «EXAMEN» as soon as an exam is known (FR-020 to FR-023).
- Q: Which source wins when they disagree about what the exam asks? → A: The student's class notes,
  then Classroom, then the textbook. The teacher's material prioritises scope; it does not limit it.
- Q: In which language is each piece? → A: Explanations, videos and the study guide in Spanish, with
  each key term also in the subject's language. Practice, quiz and flashcards in the subject's language.
  Everything for the parent in Spanish.
- Q: How many notebooks per topic? → A: One. The parent's material does not go into it.
- Q: What is a block, and how many videos? → A: A block is an idea the exam can ask, grouped so two
  ideas students confuse stay apart. Two or three blocks per topic, one video each, a few minutes
  long.
- Q: How does the student know where to start? → A: Every piece is numbered in study order and its
  title says what it is, what about and how long; a note numbered 0 says what to do first. Titles
  are in Spanish, as the constitution asks of everything the family reads, even when the piece's
  content is in the subject's language.
- Q: What happens with a teacher's answer key that is wrong? → A: Every numeric answer is
  recomputed. The parent's guide shows the correct value next to the sheet's, neutrally; nothing
  the student sees repeats the wrong value or names the teacher.
- Q: Can it all be printed? → A: Yes: one A4 PDF per topic in the topic's Drive folder, with every
  piece except the videos, the mind map included; and each of the parent's documents as its own PDF.
- Q: Does any of this go in the calendar? → A: No study blocks and no reminders: the calendar holds
  only facts read from Classroom.
- Q: May an exam's calendar event point to the topic's material? → A: Yes: the description of the
  exam event that is already there carries two links, to the topic's Drive folder and to its
  notebook. No new event is created for it.

## User Scenarios & Testing *(mandatory)*

The actors are **the family** (the parent who launches alfabeta and helps at home, reading Spanish
only), **the student** (a viewer of the topic's notebook) and **the teachers** (never interact).

### User Story 1 - An announced exam gets its full pack, checked before anyone sees it (Priority: P1)

An exam is announced. As soon as it is known, alfabeta proposes the topic's blocks from its folder;
once they are confirmed it makes, in the topic's notebook, one explainer video per block, a
practice sheet, a quiz and
flashcards in the subject's language, a study guide and a mind map. It checks every piece before
showing it: the language of the whole text, every number, and that the practice problems do not
reuse the teacher's data.

**Why this priority**: an exam is the clearest deadline the student has, and the one signal that
needs no guessing.

**Independent Test**: with a test topic folder holding a teacher's sheet with a known wrong answer
and a known language, run the pack and check each piece against the acceptance scenarios.

**Acceptance Scenarios**:

1. **Given** a topic folder and confirmed blocks, **When** the pack runs, **Then** the notebook has
   one video per block, a practice sheet, a quiz, flashcards, a study guide and a mind map.
2. **Given** a subject taught in Basque, **When** the pack runs, **Then** the
   practice sheet, quiz and flashcards are entirely in Basque and the videos and study guide in
   Spanish.
3. **Given** a generated practice sheet that reuses a problem's data from the teacher's sheet,
   **When** it is verified, **Then** it is regenerated, and the family is never pointed at it.
4. **Given** a piece with a numeric answer that does not match its recomputation, **When** it is
   verified, **Then** it is not in the notebook when the run ends and the family is told which
   answer failed.
5. **Given** a run that changed the notebook account's output language, **When** it ends, by
   success or by failure, **Then** the setting is back to what it was before the run.

---

### User Story 2 - The parent's material, in Spanish and out of the student's sight (Priority: P1)

The parent opens the topic's `docente/` folder and finds, in Spanish, the blocks with the files
they came from, a guide with questions to ask at home and the expected answers, the teacher's
answer key recomputed with every mismatch marked, and a glossary in the subject's language, Spanish
and English. None of it is in the notebook.

**Why this priority**: the parent cannot help without it, and a wrong key discourages the student.

**Independent Test**: with the same test topic, check that `docente/` holds the four documents as
PDF and Markdown, that the known wrong answer is marked with its correct value, and that the
notebook lists none of them.

**Acceptance Scenarios**:

1. **Given** a teacher's sheet with answers, **When** the pack runs, **Then** the parent's guide
   lists each exercise translated to Spanish with its recomputed result, and marks each mismatch
   with both values.
2. **Given** an exercise whose statement lacks a datum, **When** the pack runs, **Then** the
   parent's guide says so instead of inventing it.
3. **Given** the pack has finished, **When** the student opens the notebook as a viewer,
   **Then** neither the parent's guide nor the glossary is listed.

---

### User Story 3 - The student opens the notebook and knows what to do today (Priority: P1)

The student opens the topic's notebook. The first item is a note numbered 0 that says, in one
line, the one thing to do today and how long it takes; directly under it is that piece. Every
title says which moment it belongs to (today, yesterday, the weekly review, the exam), what it is,
what about and how long, and none of them invites skipping it. The chat answers as a tutor: a hint
before the answer, explanations in Spanish with the terms in the subject's language.

**Why this priority**: a notebook the student does not know how to use is not used.

**Independent Test**: open the notebook as the student and read the list top to bottom.

**Acceptance Scenarios**:

1. **Given** a run has finished, **When** the notebook is opened, **Then** the note is first,
   names one task with its duration, and the piece it names is second.
2. **Given** any piece, **When** its title is read, **Then** it carries its moment, its number
   within that moment when there are several, its kind, its subject and, for a video or a quiz, its
   real length or number of questions.
3. **Given** every title and the note, **When** they are read, **Then** none says «opcional»,
   «extra», «si quieres» or anything that presents the piece as skippable.
4. **Given** a question in the chat, **When** the student asks for an exercise's solution,
   **Then** the tutor gives a hint first and does not attribute any source to a person.

---

### User Story 4 - The whole topic on paper (Priority: P2)

The family prints the topic. In the topic's Drive folder there is one A4 PDF with an index of
every piece (videos marked as "in the notebook") and then each piece on a new page in the numbered
order: the practice sheet, the quiz with its answers at the end, the flashcards as a table, the
study guide and the mind map drawn as a diagram. Formulas print as formulas.

**Why this priority**: the parent prints what the student works on, and the platform has no print
view for a report or a mind map (the operator found that exporting a report to Google Docs lost
characters, 2026-10-26).

**Independent Test**: build the PDF for the test topic and check the index against the notebook's
list, the page each piece starts on, a formula and the mind map's legibility at print size.

**Acceptance Scenarios**:

1. **Given** a finished pack, **When** the topic is printed, **Then** the PDF's index lists every
   piece of the notebook in the same order and with the same titles.
2. **Given** the printed PDF, **When** it is read, **Then** each piece starts on a new page and the
   quiz's answers come after its questions.
3. **Given** a mind map, **When** it is printed, **Then** it fits one A4 page and its labels are
   readable.

---

### User Story 5 - Something to do every day the teacher posts, and a review every week (Priority: P2)

After each Classroom sync, every new material the teacher posted becomes a small piece for today in
its topic's notebook: a short quiz and a few flashcards in the subject's language, about that material
alone, titled «HOY» with how long it takes. What was «HOY» yesterday becomes «Ayer». Once a week, on
a fixed day, a «REPASO SEMANA» brings one short video per idea that arrived that week and a quiz
that mixes the week with earlier ones; that week's «Ayer» pieces then leave the list. Nothing
waits for a topic to end.

**Why this priority**: it is what makes the study daily instead of a rush before the exam, and it
needs the daily Classroom sync of spec 001 to exist.

**Independent Test**: feed the agenda of spec 001 with a material on Monday, another on Wednesday,
nothing on Thursday and an exam announced on Thursday; run the syncs and the weekly day, and read
the notebook's list after each.

**Acceptance Scenarios**:

1. **Given** a sync that brings a new material, **When** it ends, **Then** the notebook of that
   material's topic has a «HOY» quiz and «HOY» flashcards about that material only, under the note,
   and the previous «HOY» pieces are titled «Ayer».
2. **Given** a sync that brings nothing new, **When** it ends, **Then** no piece is made and the
   note names the oldest piece not yet done (the latest «HOY», «Ayer» or the review).
3. **Given** a material already covered by a «HOY» piece, **When** it is synced again, **Then** no
   second piece is made for it.
4. **Given** the weekly review day, **When** its run ends, **Then** there is one video per idea
   that arrived that week, a quiz mixing the week with earlier weeks, and none of that week's
   «Ayer» pieces.
5. **Given** a material without a topic in Classroom, **When** it is synced, **Then** its «HOY»
   piece goes to the notebook of its subject's most recent topic and the family is told.
6. **Given** an exam announced or declared, **When** the sync ends, **Then** the exam's blocks are
   proposed at once (Story 1) and the exam event carries the two links of FR-026.

---

### User Story 6 - The student's class notes lead (Priority: P3)

The family drops photos of the student's class notes into the topic's `apuntes/` folder. They are
transcribed literally, the transcription is checked by someone who can read the notes, and only
then does it become a source of the notebook — the most trusted one: when the notes show what was
taught, the blocks follow them.

**Why this priority**: the notes are the best evidence of what the exam asks, but turning photos
of handwriting into a usable source had not been tried when this was written.

**Independent Test**: with photos in `apuntes/` that stress an idea the textbook barely covers,
check that the proposed blocks include it.

**Acceptance Scenarios**:

1. **Given** photos in `apuntes/` with a checked transcription, **When** the pack runs, **Then**
   the transcription is a source of the notebook and the proposed blocks cite it.
2. **Given** photos whose transcription nobody has checked, **When** the pack runs, **Then** they
   are not a source and the family is told.

> Superseded on 2026-10-27 by spec 005 (julioarguello/alfabeta#44): transcriptions reach the
> notebook without a check, each page saying it is automatic and whether the student checked it,
> and only through the topic's living notes file: the pack adds no source of its own for them.
> The ranking of the notes first is unchanged.

---

### Edge Cases

- The notebook account is at its usage limit: the run stops before generating, says when the
  window resets, and changes nothing.
- A generation fails or never completes: the piece is reported missing; the others are kept.
- The family has already renamed or deleted a piece by hand: the pack does not recreate it unless
  asked.
- The teacher posts more material into a topic whose pack exists (Story 5, scenario 2).
- A topic has no calculations: its videos have no worked example and its practice sheet holds
  questions instead of problems.
- A subject is taught in Spanish: practice, quiz and flashcards are in Spanish, and the glossary
  keeps Spanish and English.
- The mind map leaves out a block: it is reported; it is not regenerated, because its content
  cannot be steered.

## Requirements *(mandatory)*

### Functional Requirements

**Scope and sources**

- **FR-001**: alfabeta MUST propose a topic's blocks from its folder (class notes, Classroom
  material, textbook), naming for each block the files it comes from, and MUST NOT generate until
  they are confirmed. Once confirmed, the blocks of a topic are not proposed again.
- **FR-002**: When sources disagree about what the exam asks, the class notes MUST win over
  Classroom and Classroom over the textbook.
- **FR-003**: Two ideas that the teacher's material or the parent's guide name as a typical
  confusion MUST fall in different blocks.

**Generation**

- **FR-004**: The pack MUST hold, in the topic's single notebook: one explainer video per block, a
  practice sheet, a quiz, flashcards, a study guide and a mind map. Class notes become a source
  as their literal transcription (spec 005, which superseded the check this requirement asked for).
- **FR-005**: Videos and the study guide MUST be in Spanish, giving each key term also in the
  subject's language (the one it is taught and examined in) as the class material writes it.
  Practice sheet, quiz and flashcards MUST be in the subject's language, configured per subject.
- **FR-006**: The practice sheet MUST go from a fully worked example to partly worked ones to
  problems without help, with the solutions in a separate section at the end, and MUST NOT reuse
  any numeric data of the teacher's sheets.
- **FR-007**: Any change to a setting of the notebook account that affects other notebooks MUST be
  undone before the run ends, whether it succeeds or fails.
- **FR-008**: A run MUST NOT create a second notebook for a topic.

**Verification**

- **FR-009**: Before the family is told the pack is ready, alfabeta MUST check the language of
  every piece's whole text (for a video, its on-screen text), recompute every numeric answer, and,
  for the practice sheet, compare its data with the teacher's sheets.
- **FR-010**: A piece that fails verification MUST NOT be in the notebook when the run ends; it is
  regenerated or reported.
- **FR-011**: Every teacher's answer key in the topic folder MUST be recomputed; each mismatch, and
  each statement missing a datum, is recorded for the parent's guide.

**The parent's material**

- **FR-012**: `docente/` in the topic folder MUST hold, in Spanish: the confirmed blocks with their
  sources; a parent's guide with questions to ask at home and the teacher's sheets translated and
  recomputed, each mismatch marked neutrally; and a glossary (the subject's language, Spanish, English,
  one-line definition, formula). The guide and the glossary as PDF and Markdown.
- **FR-013**: None of the parent's material may be visible in the notebook when the run ends.

**Order and names**

- **FR-014**: Every piece's title MUST be in Spanish and start with its moment — `HOY`, `Ayer`,
  `REPASO SEMANA` or `EXAMEN <weekday>` — followed by its number within that moment when there are
  several; it says what the piece is, what it is about and, for a video or quiz, its measured length
  or question count, with no date and no recipient. A piece in the subject's language says so.
- **FR-015**: When a run ends, the notebook's list MUST open with the note «0 · Empieza aquí»,
  rewritten by every run to name the one thing to do today with its duration, and directly under it
  the piece the note names. No title and no note may present a piece as optional.
- **FR-016**: The notebook's chat MUST be set to answer as a tutor: a hint before the answer,
  Spanish explanations with the exam's terms, the source order of FR-002, and no attribution of a
  source to a person.

**Printing**

- **FR-017**: alfabeta MUST write one A4 PDF per topic into the topic's folder, holding an index of
  every piece in the notebook's order, then the start note, then every piece except videos, each
  on a new page: the
  quiz with its answers after its questions, the flashcards as a table, the mind map as a diagram
  that fits one page.
- **FR-018**: Formulas MUST print as typeset formulas, and lists and tables as such.
- **FR-019**: Each document of `docente/` MUST also print as its own PDF.

**Trigger and record**

- **FR-020**: Each sync that brings a new teacher's material to a subject MUST make, in the notebook
  of that material's topic, a «HOY» piece about that material alone: a quiz of about five questions
  and about five flashcards in the subject's language. The previous «HOY» pieces are retitled «Ayer».
  No video is made at this moment. A material already covered never gets a second «HOY» piece.
- **FR-021**: On a fixed weekday, set in the configuration, alfabeta MUST make a «REPASO SEMANA» per
  notebook that received material that week: one explainer video per idea that arrived, and a quiz
  mixing that week with earlier ones. Once it is verified, that week's «Ayer» pieces are deleted.
- **FR-022**: As soon as an exam is known — from the Classroom agenda or declared by the family —
  alfabeta MUST propose the topic's blocks and make the exam pack of Story 1 on confirmation; with
  no answer within one day, it makes it with the proposed blocks and says so. The family is told
  how many afternoons remain before the exam.
- **FR-023**: No step may depend on detecting that a topic has ended. A material without a topic in
  Classroom goes to the notebook of its subject's most recent topic, and the family is told.
- **FR-024**: alfabeta MUST keep, per topic, a record: blocks, each piece with its notebook id,
  moment, title, language, verification result and date, the materials each «HOY» piece covers,
  and the corrections found. A later run reads it to avoid regenerating what exists.

**Boundaries**

- **FR-025**: alfabeta MUST NOT write study blocks or reminders into the calendar, and MUST NOT
  create events for the material.
- **FR-026**: When a topic has an exam event, its description MUST carry a link
  to the topic's Drive folder and one to its notebook, written once and not duplicated by later
  runs.
- **FR-027**: Nothing about the student MAY enter the repository: prompts, names, ids and paths
  come from the private configuration.
- **FR-028**: alfabeta MUST NOT type a password; the family signs in.

### Key Entities

- **Topic**: a school year, subject and topic folder, with its notebook and its subject's language.
- **Block**: an idea the exam can ask; title, the files it comes from, confirmed or not.
- **Piece**: something in the notebook: kind (video, report, quiz, flashcards, mind map, note),
  number, title, language, audience (student or parent), verification result.
- **Correction**: an exercise of a teacher's sheet whose recomputed result differs from the sheet,
  or whose statement lacks a datum.
- **Pack record**: per topic, the blocks, the pieces with their moment, the materials each «HOY»
  piece covers, and the corrections, with dates (FR-024).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: No numeric answer the student sees differs from its recomputation, across every
  piece of every pack.
- **SC-002**: Every text piece intended for the subject's language contains no paragraph in another
  language, and every Spanish text piece gives each key term in the subject's language. (A video's
  audio cannot be checked by the run; its on-screen text is.)
- **SC-003**: When a run ends, the notebook account's output language is what it was before the
  run, in every run, including failed ones.
- **SC-004**: When a run ends, the note is first, the piece it names is second, and no piece of
  the parent's material is listed.
- **SC-005**: The printed PDF lists every non-video piece of the notebook, in the same order, each
  starting on a new page.
- **SC-006**: An exam pack fits in one 5-hour usage window of the notebook account (measured
  2026-10-26: about 80 % for three videos and three reports).
- **SC-007**: From an exam being known to its pack being ready, the family intervenes at most
  twice: to confirm the blocks and, if a checked transcription of the
  class notes is missing, to check it. Every other step runs without them.
- **SC-008**: Every sync that brings new material ends with a «HOY» piece for it in its notebook,
  and every weekly review day ends with its «REPASO SEMANA»; no «HOY» piece is made twice for the
  same material.
- **SC-009**: No title and no note in any notebook says «opcional», «extra» or «si quieres».

## Assumptions

- The topic folder exists with its sources, filled by the textbook capture and by `classroom-sync`.
- The notebook is owned by a parent's personal Google account on a paid plan and shared with the
  student as viewer.
- The notebook platform has no public API; the tool that reaches it may break, in which case the
  run stops and says so.
- The study guide, mind map and quiz are generated from the whole notebook; the platform does not
  let a mind map be steered, so it may leave a block out.
- How many pieces the student can face is a hypothesis: the design page proposes few, citing
  choice-overload research, and the first topic ended with six to work through and two to consult.
  The family decides whether to trim.
- While a run lasts, a piece not yet verified, or the parent's material, may be visible to a viewer
  for some minutes: the platform shows a viewer every piece as soon as it exists. FR-009, FR-010
  and FR-013 hold at the end of the run, not during it.
- What a viewer sees has not been checked from the student's account; the requirements on what
  the student sees assume a viewer sees the same list as the owner.
- «HOY» needs the daily Classroom sync of spec 001; until it runs unattended, a «HOY» piece exists
  only on the days someone runs the sync.
- The quota cost of «HOY» pieces and weekly reviews across several subjects has not been measured;
  quiz and flashcards cost less than videos, which is why «HOY» makes no video.
- The weekly review day defaults to Friday.

## Dependencies

- Spec 001 (`classroom-sync`): the topic folders, and the agenda that carries new topics and
  announced exams (FR-020, FR-022).
- `nlm` (`notebooklm-mcp-cli`), `pandoc`, Graphviz and Google Chrome on the machine that runs it.
- A browser session of the notebook's owner for the one setting `nlm` cannot change: the output
  language of quiz and flashcards is account-wide (FR-007). The run drives that session itself.
