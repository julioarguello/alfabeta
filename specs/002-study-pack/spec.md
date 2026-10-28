# Feature Specification: A topic's study material, prepared in its notebook and on paper

**Feature Branch**: `docs/21-spec-002-study-pack` (spec dir `002-study-pack`)

**Created**: 2026-10-26

**Status**: Draft

**Amended**: 2026-10-28 — the day before an exam: a theory sheet and a problems sheet, composed
from the topic's sources and printed, outside the notebook (User Story 7, julioarguello/alfabeta#97).

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

A second procedure was run by hand and checked 2026-10-28, for one exam the next day: two sheets
on paper for the day before the exam, written from the topic folder rather than by the notebook
(User Story 7, FR-029 to FR-036). Its outputs are the topic's `Teoría para el examen` and
`Problemas tipo` PDFs. They add to the spaced practice of Stories 1 and 5 and do not replace it:
the design page's case against material made only the night before still holds; these sheets
narrow what was practised to what the announcement names.

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
  the student sees repeats the wrong value or names the teacher. (Revised for the exam's problems
  sheet only, in the session below.)
- Q: Can it all be printed? → A: Yes: one A4 PDF per topic in the topic's Drive folder, with every
  piece except the videos, the mind map included; and each of the parent's documents as its own PDF.
- Q: Does any of this go in the calendar? → A: No study blocks and no reminders: the calendar holds
  only facts read from Classroom.
- Q: May an exam's calendar event point to the topic's material? → A: Yes: the description of the
  exam event that is already there carries two links, to the topic's Drive folder and to its
  notebook. No new event is created for it.

### Session 2026-10-28

Written after the family prepared one exam by hand the day before it, so the answers record what
was done and decided that day (User Story 7).

- Q: Where does an exam's scope come from? → A: From the teacher's announcement of the exam on the
  class's Classroom stream, which spec 001 reads into the agenda. If none has been captured, it is
  read on the stream before anything is written. The theory sheet's sections are the
  announcement's points, in its order.
- Q: What does the student work through the day before? → A: One theory sheet that follows the
  class notes (notes > Classroom > textbook), sized to the study slot the family has: a 90-minute
  slot took four A4 pages. Each term comes first in the subject's language, because the exam is
  written in it, then in Spanish. The sheet opens with a timed plan for the slot whose last step is
  a blank-page recall. The topic's study guide had been generated before the class notes reached
  the folder; a guide made before the notes is stale: it is not handed out, it is rebuilt from
  every source, and the theory sheet is written from every source too. That day the theory sheet
  was written; the stale guide itself was not rebuilt.
- Q: What does the student practise? → A: One problems sheet. Every problem of the teacher's
  Classroom photocopies goes into a pattern, with as few patterns as possible: one formula is
  about one pattern, and the direct and the inverse use of a formula are the same pattern; a
  pattern can also be a chain of formulas or a classification with none. For each
  pattern the sheet works the hardest problem, one the teacher assigned when there is one: the
  statement in its original language, a Spanish translation, and the solutions after a page break.
  Two photocopies fitted six patterns.
- Q: How does a number reach a sheet? → A: Every result is computed by a script, never typed. The
  script also recomputes every answer the photocopies print, compares it at the precision it is
  printed with, and the disagreements are listed with the printed and the computed value. That day
  it reported three wrong answers on the teacher's sheet (the same three the parent's guide,
  checked 2026-10-26, had found) and a worked example of the textbook that contradicts itself.
  The results came from the script, but a few unit conversions and derived figures were still
  typed; each is a result too, and the rule covers it (FR-036).
- Q: The answer read 2026-10-26 says nothing the student sees repeats a wrong value of a
  teacher's key. Does that hold for the problems sheet? → A: No; this revises it for that sheet
  only. The student
  solves these problems on the photocopy, where the wrong value is printed beside the exercise, so
  the sheet lists the printed answers that do not match, with both values, after the solutions and
  under a neutral heading that names no one. The notebook's pieces keep the earlier rule: they
  never reuse the teacher's data (FR-006), so they never show a teacher's key.
- Q: Are the two sheets pieces of the notebook? → A: No. They are files of the topic's Drive folder,
  printed like the rest of the topic but written from its sources, not generated by the notebook,
  and they are not in the topic's printed pack (FR-017).

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
and a subject with a known `language`, run the pack and check each piece against the acceptance scenarios.

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

### User Story 7 - The day before an exam, two sheets on paper (Priority: P1)

An exam is announced. From what the announcement says it covers, alfabeta writes two A4 PDFs into
the topic's Drive folder: a theory sheet the student works through in the study slot, following a
plan printed on it, and a problems sheet with one worked problem for each kind of problem the
teacher's photocopies hold. Every number on them comes from a script, and every answer the
photocopies print has been checked against it.

**Why this priority**: the notebook's pieces are for practice spread over days; the day before an
exam the student has one slot, and needs what the announcement names, in the order it names
it, on paper.

**Independent Test**: with a test topic folder holding an announcement, class notes, a textbook
chapter and two photocopies, one of them with a known wrong answer, one worked example that
contradicts itself and one statement missing a datum, build both sheets for a 90-minute slot and
check each against the acceptance scenarios.

**Acceptance Scenarios**:

1. **Given** an announcement that lists three points, **When** the theory sheet is built, **Then**
   its sections are those three points in the announcement's order.
2. **Given** an exam with no captured announcement, **When** the sheets are asked for, **Then** the
   announcement is read on the class's stream before either sheet is written.
3. **Given** a study slot, **When** the theory sheet is built, **Then** it fits the pages that slot
   allows (four for 90 minutes, measured once) and opens with a plan that divides the slot by
   section with clock times, whose last step is a blank-page recall.
4. **Given** a term the class material writes in the subject's language, **When** it appears on
   either sheet, **Then** it is written first in that language, then in Spanish.
5. **Given** a study guide generated before the class notes reached the topic folder, **When** the
   sheets are asked for, **Then** that guide is not handed out, it is rebuilt, and the theory
   sheet is written from every source.
6. **Given** the teacher's photocopies, **When** the problems sheet is built, **Then** every exercise
   is in exactly one pattern, exercises printed on two photocopies are named as repeats, and each
   pattern has one worked problem, one the teacher assigned when the pattern has one.
7. **Given** a worked problem, **When** it is read, **Then** its statement is in its original
   language followed by a Spanish translation, and its solution comes only after a page break.
8. **Given** a printed answer that differs from the computed one by more than half a unit of its
   last digit, **When** the problems sheet is built, **Then** a table after the solutions gives the
   exercise, the printed value, the computed value and what went wrong, and names no one.

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
- An exam is announced only in class, so the stream has no announcement: the family gives the
  scope, and the theory sheet says where it came from (FR-030).
- A printed answer differs from the computed one only because its solution rounded before the end
  (observed 2026-10-28: 9,32 % printed, 9,33 % computed): the solution says so; it is not a wrong
  answer (FR-036).
- A statement lacks a datum that the same page gives elsewhere (observed 2026-10-28: a mass where a
  volume was needed, and the density in a worked example beside it): the solution uses it and says
  where it came from, and the table lists the exercise with its result under each reading (FR-036).
- The notes, the teacher's sheets and the textbook name one quantity in different words, or give
  one name two meanings (observed 2026-10-28: «masa-kontzentrazioa» as a percentage on a sheet and in
  g/L in the book): the theory sheet shows each wording and how to tell them apart (FR-032).

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

**The exam eve**

- **FR-029**: For a known exam (FR-022), alfabeta MUST write two sheets into the topic's Drive
  folder, each one A4 PDF printed as FR-018 asks: `Teoría para el examen · TNN (<day> <month>).pdf`
  and `Problemas tipo · TNN (<day> <month>).pdf`, with the topic's number and the exam's date.
  They are written from the topic folder's sources, not generated by the notebook; they are not
  pieces of the notebook and not part of the topic's printed pack (FR-017). Their text is in
  Spanish, terms aside (FR-032).
- **FR-030**: The exam's scope MUST come from the teacher's announcement of the exam on the class's
  Classroom stream. When the agenda holds none for the exam, it MUST be read on the stream before
  either sheet is written; when the stream has none either, the family gives the scope. The theory
  sheet quotes the announcement in its language with its date, its sections are the announcement's
  points in the announcement's order, and it says what of the topic the announcement leaves out.
- **FR-031**: The theory sheet MUST follow the class notes, completed by Classroom and then the
  textbook (FR-002), and MUST fit the study slot the family gives (measured 2026-10-28: four A4
  pages for 90 minutes). It opens with a plan that divides the slot by section, with clock times
  and a short break, and whose last step is a blank-page recall: write from memory, in the
  subject's language, what the sheet holds that the exam asks to reproduce, then correct it against
  the sheet. Each section carries a way to test it without looking, with its answers.
- **FR-032**: On both sheets every term MUST appear first in the subject's language, as the class
  material writes it, and then in Spanish. Where the notes, the teacher's sheets and the textbook
  use different words for one thing, or one word for two things, the theory sheet shows each and
  how to tell them apart.
- **FR-033**: A study guide or theory sheet made before the topic's class notes reached its folder
  is stale: it MUST NOT be handed out for the exam and MUST be rebuilt from every source (the
  study guide as in FR-004), even though the pack record (FR-024) holds it. The theory sheet is
  always written from every source.
- **FR-034**: The problems sheet MUST put every exercise of the teacher's Classroom photocopies,
  worked examples included, into a pattern, using as few patterns as possible: one formula is about
  one pattern, and solving the same formula for another unknown (direct or inverse) is the same
  pattern; a chain of formulas, or a classification with none, can also be one. It names the
  photocopies with their dates, maps each pattern to its exercises, names the exercises printed on
  two photocopies and marks those the teacher assigned.
- **FR-035**: For each pattern the problems sheet MUST work one problem, the hardest, preferring one
  the teacher assigned, and say why it is the hardest; it may name a second one of the same pattern
  for spare time. Each worked problem gives its statement in its original language followed by a
  Spanish translation. The sheet gives the order and about how long each pattern takes, and every
  solution comes after a page break, at the end.
- **FR-036**: Every result printed on either sheet MUST come from a script's output and none may be
  typed, a unit conversion of a datum included; the data of the statements, and fixed
  equivalences such as 1 L = 1000 mL, are copied. The same script MUST recompute
  every answer the photocopies print and compare it at the printed precision: equal when within
  half a unit of the last digit printed. After the solutions, a table under a neutral heading lists
  each disagreement with the exercise, the printed value, the computed value and what went wrong,
  and each statement missing a datum with its result under each reading; it names no one. A
  disagreement that goes away when the intermediate values are rounded as the printed solution
  rounds them is noted beside that solution, not in the table. Outside the table, a wrong printed
  value appears only in the worked solution of that same exercise, with its cause (see
  Clarifications).

### Key Entities

- **Topic**: a school year, subject and topic folder, with its notebook and the subject's language.
- **Block**: an idea the exam can ask; title, the files it comes from, confirmed or not.
- **Piece**: something in the notebook: kind (video, report, quiz, flashcards, mind map, note),
  number, title, language, audience (student or parent), verification result.
- **Correction**: an exercise of a teacher's sheet whose recomputed result differs from the sheet,
  or whose statement lacks a datum.
- **Pack record**: per topic, the blocks, the pieces with their moment, the materials each «HOY»
  piece covers, and the corrections, with dates (FR-024).
- **Exam sheet**: one A4 PDF for one exam in the topic's Drive folder, theory or problems; not a
  piece of the notebook (FR-029).
- **Pattern**: one way of solving that a group of the photocopies' exercises shares: a formula
  used directly or inversely, a chain of them, or a classification; its exercises, the ones the
  teacher assigned, and its hardest (FR-034, FR-035).

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
- **SC-010**: In every problems sheet, every exercise of every photocopy of the topic appears in
  exactly one pattern, and every pattern has exactly one worked problem.
- **SC-011**: No result on an exam sheet differs from the script's output, every answer the
  photocopies print has been compared with it, and every disagreement beyond the printed precision
  is in the problems sheet's table.
- **SC-012**: A theory sheet fits the pages of its slot (measured once, 2026-10-28: four A4 pages
  for a 90-minute slot), and its sections follow the announcement's points one to one.

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
- The study slot of an exam sheet is given by the family each time: the configuration has no key
  for it (`[schedule]` holds the sync's times). Four pages for 90 minutes was measured once.
- When the exam sheets are written, relative to the exam, is the family's call: the one run,
  observed 2026-10-28, wrote them on the morning of the day before, for that afternoon's slot.
  Whether they should also become sources of the notebook is not decided; that day they went only
  to the topic's Drive folder.

## Dependencies

- Spec 001 (`classroom-sync`): the topic folders, and the agenda that carries new topics and
  announced exams (FR-020, FR-022), including an exam announced only on the stream, with a link to
  the announcement (its User Story 2); and the stream's announcements saved with their text (its
  User Story 6, julioarguello/alfabeta#12), from which the exam sheets take their scope (FR-030).
- `nlm` (`notebooklm-mcp-cli`), `pandoc`, Graphviz and Google Chrome on the machine that runs it.
- A browser session of the notebook's owner for the one setting `nlm` cannot change: the output
  language of quiz and flashcards is account-wide (FR-007). The run drives that session itself.
