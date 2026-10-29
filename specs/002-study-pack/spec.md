# Feature Specification: A topic's study material, prepared in its notebook and on paper

**Feature Branch**: `docs/21-spec-002-study-pack` (spec dir `002-study-pack`)

**Created**: 2026-10-26

**Status**: Draft

**Amended**: 2026-10-28 — the day before an exam: alfabeta's `exam prep` asks the topic's notebook
for a theory sheet and a problems sheet and prints them (User Story 7, julioarguello/alfabeta#97;
the command is julioarguello/alfabeta#106).

**Amended**: 2026-10-28 — confirmed blocks are provisional until the teacher's announcement of the
exam: a point it names that no block covers gets one video, and a video's exclusions need a source
(FR-001, FR-022, User Story 1; julioarguello/alfabeta#121).

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
material to study from: inside the topic's Gemini Notebook notebook for the student, in the
topic's `notebook/` folder in Drive, the parent's material included, and in one printable document
for paper.

The procedure was run by hand on one topic on 2026-10-26, as the `study-pack` skill
(julioarguello/alfabeta#20). This spec states what that procedure must guarantee so it can run
without someone watching; the measurements behind each requirement are in
[About preparing study material in advance](../../docs/explanation/study-material.md) and in the
skill's own table of measured behaviour.

A second procedure was run by hand and checked 2026-10-28, for one exam the next day: two sheets
on paper for the day before the exam, a theory sheet and a problems sheet (the topic's
`Teoría para el examen` and `Problemas tipo` PDFs). An agent wrote them that day from the topic
folder; the operator then decided that alfabeta makes them by itself, with its own command
`exam prep` asking the topic's notebook (User Story 7, FR-029 to FR-037, and the
[command contract](contracts/cli.md)). They add to the spaced practice of Stories 1 and 5 and do
not replace it: the design page's case against material made only the night before still holds;
these sheets narrow what was practised to what the announcement names.

Out of this spec: writing to Classroom or to the textbook platform, the calendar beyond the facts
spec 001 puts there and the two links of FR-026, audio overviews, and recognising handwriting in the class-note
photos (it is a dependency, not a requirement here). Running `exam prep` by itself when an exam is
close belongs to the unattended runner (spec 001 User Story 7) and is later work.

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
  Everything for the parent in Spanish. (The exam's problems sheet aside: FR-029.)
- Q: How many notebooks per topic? → A: One. The parent's material does not go into it.
- Q: What is a block, and how many videos? → A: A block is an idea the exam can ask, grouped so two
  ideas students confuse stay apart. Two or three blocks per topic, one video each, a few minutes
  long.
- Q: What may a video be told not to explain? → A: The other blocks, and what a source says is out
  of the exam — the teacher's announcement, the teacher — with that source named. Never a textbook
  lesson, a notes page or a Classroom item because the teacher's sheets do not practise it. Measured
  2026-10-28 on one topic: the blocks were cut from the weight of the handouts before the notes and
  the announcement arrived; a video's prompt excluded an idea the textbook gives a whole lesson and
  the mind map a first-level branch, and the announcement named it as one of its three points.
- Q: What happens when the announcement arrives after the blocks were confirmed? → A: Its points
  are compared with the blocks; a point no block covers gets one video for that point, numbered
  after the existing pieces. Nothing else is made again: the exception to FR-001's freeze is one
  video per uncovered point, not a new pack. The two-or-three count yields to the announcement: a
  pair split under FR-003 never takes the slot of a point the teacher named.
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

Written after an exam was prepared by hand the day before it. The first answers record what was
done that day; the last three, what the operator decided once it was done (User Story 7).

- Q: Where does an exam's scope come from? → A: From the teacher's announcement of the exam on the
  class's Classroom stream, whose text and date spec 001 captures. The theory sheet's sections are
  the announcement's points, in its order.
- Q: What does the student work through the day before? → A: One theory sheet that follows the
  class notes (notes > Classroom > textbook), sized to the study slot the family has: a 90-minute
  slot took four A4 pages. Each term comes first in the subject's language, because the exam is
  written in it, then in Spanish. The sheet opens with a timed plan for the slot whose last step is
  a blank-page recall. A study guide generated before the class notes reached the folder is stale
  and is regenerated before anything is printed; that day the topic's guide was stale and was not
  regenerated.
- Q: What does the student practise? → A: One problems sheet. Every problem of the teacher's
  Classroom photocopies goes into a pattern, with as few patterns as possible: one formula is
  about one pattern, and the direct and the inverse use of a formula are the same pattern; a
  pattern can also be a chain of formulas or a classification with none. For each pattern the
  sheet works the hardest problem, one the teacher assigned when there is one: the statement in
  its original language, a Spanish translation, and the solutions after a page break. Two
  photocopies fitted six patterns.
- Q: How did the numbers reach that day's sheets? → A: The agent that wrote them computed every
  result with a script, though a few unit conversions and derived figures were still typed. The
  script recomputed every answer the photocopies print, at the precision it is printed with, and
  reported three wrong answers on the teacher's sheet and a worked example of the textbook that
  contradicts itself; each disagreement was listed with the printed and the computed value.
- Q: The answer read 2026-10-26 says nothing the student sees repeats a wrong value of a
  teacher's key. Does that hold for the problems sheet? → A: No; this revises it for that sheet
  only. The student solves these problems on the photocopy, where the wrong value is printed
  beside the exercise, so the sheet lists the printed answers that do not match, with both values,
  after the solutions and under a neutral heading that names no one. Every other piece keeps the
  earlier rule; the practice sheet never reuses the teacher's data (FR-006), so it never shows a
  teacher's key.
- Q: Who prepares the two sheets after that day? → A: alfabeta, by itself, through the topic's
  notebook. The operator does not want to prepare an exam in front of Claude, but to have their own
  tool do it unattended, and chose that alfabeta's command `exam prep` asks the notebook for the two
  sheets as reports with fixed prompts and prints them, with no Claude and no Claude API («Sí, haz
  tu recomendación. Y actualiza el README con estos comandos que tendríamos en alfabeta»). The two
  sheets are therefore pieces of the notebook, in the moment «EXAMEN» (FR-014), and each is also
  printed on its own into the topic's `exam/` folder.
- Q: Where in the topic folder do the printed sheets go? → A: In its `exam/` subfolder, whose name
  carries no date; the exam's date stays in each file's name, so a second exam on the same topic
  sits beside the first. The operator set this when deciding the topic folders' layout, with every
  directory name the code decides in English, because the project is public; file names keep their
  language. The constitution was amended the same day to match (2.2.0, julioarguello/alfabeta#110).
  That day's two PDFs were moved there by hand.
- Q: Who computes the numbers, then? → A: The notebook, as an accepted risk. The operator accepted
  it because the parent's guide checked 2026-10-26 got right the three answers the teacher's sheet
  printed wrong. That guide's prompt carried those corrections, recomputed beforehand (the
  `{corrections}` of the parent-guide prompt), so whether the notebook finds a wrong printed
  answer by itself has not been measured: the first run of `exam prep` measures it. A check by a
  model that executes code may later be added for that step alone (FR-036).
- Q: What if notebooks are switched off, or `nlm` does not work? → A: The command refuses before it
  asks the notebook for anything, with a message that says why, and prints nothing: the notebook is
  an optional output that can break (constitution VII).
- Q: Where does the rest of the pack go, now that a topic folder holds only folders? → A: In the
  topic's `notebook/` folder, named after the product, like `classroom/` and `sciencebits/`:
  everything the notebook generates, the videos copied from it, the printed topic, the blocks and
  the parent's documents. It replaces `docente/` and the files the pack left at the topic's root.
  There is no separate folder for the parent: the practice sheet already carries its solutions.
  «cuaderno» was rejected, because for a student it means their own notes. The operator decided
  it with the exam sheets' folder (constitution 2.2.0, julioarguello/alfabeta#110); the class notes
  are in `notes/` (it was `apuntes/`).

### Session 2026-10-29

- Q: When the student's notes hold schemes, what shape does the study material take? → A: The
  schemes' shape. The blocks, their order and their names are the scheme's branches, in the
  student's words; the textbook and Classroom are hung from those branches, and every piece says
  which branch it covers. The operator asked for it after seeing the physics-and-chemistry Tema 01
  pack laid out in the textbook's order leave the student lost, and made it constitutional
  (constitution 2.3.0, principle X; julioarguello/alfabeta#128). The source ranking of FR-002 is
  unchanged: it decides what the exam asks, the schemes decide how the material is laid out.
- Q: Who checks the transcription of the student's notes? → A: Nobody by hand. The operator said
  there will be no human reviewer: each doubtful reading is settled by agreement with another
  source — the topic's own first (textbook in both languages, the other pages of the notes,
  Classroom), an external reference only if none settles it — and the source is written beside the
  word. A word no source settles stays marked with the sources tried.
- Q: What does the student open first? → A: «0 · Guía de estudio». The operator asked that the
  material be in order and that 0 be the study guide, telling him very briefly how to use each video
  (taking notes), what is expected of him once the session is over, with times that are not
  aggressive, and breaks (FR-015). The separate start note goes.
- Q: Where does the theory go, then? → A: Not in the guide. Seeing the first guide (plan plus
  content) the operator found it too dense — "se va a agobiar" — and asked for the guide to hold
  only how to study, pointing at the other pieces, and for a summary to study from, condensing the
  student's notes: «Resumen de tus apuntes», on the notes' schemes, one short part per
  session (FR-015).
- Q: How does the student reach the videos, when a viewer may not see them in the notebook? → A:
  Through Drive, always. The operator checked on the student's account that the notebook showed
  every piece but the three videos, and asked that the guide link each video straight to its copy
  in the topic's `notebook/` folder in Drive, whether the notebook shows it or not, so he never
  gets lost (FR-039).
- Q: What went wrong generating the pack by hand on 2026-10-29? → A: Four things, measured on
  one biology topic. (1) Asking the notebook to copy the guide's plan verbatim worked two times out
  of five: the other three came back rewritten — one replaced every piece with sources, added a
  calculus of energy expenditure and turned the four Drive links into one generic address (FR-040).
  (2) The summary, made before the textbook in Basque was a source, gave as Basque terms the
  Spanish words the student had written in his notes («Estómago (*estamago*)», «Hígado
  (*higado*)») and kept an unsettled reading («*gurin gastrikoak*»); the quiz carried one invented
  word (FR-041). (3) The student's account saw every Studio piece but none of the three videos,
  not even the oldest — the guide's Drive links are how he reaches them (FR-039). (4) Classroom held
  nothing for the subject and no exam was announced, so the blocks came from the notes' schemes
  alone and every textbook lesson without a branch stayed a question for the family; the operator
  capped the whole topic at two hours of study, two 45-minute blocks with a 15-minute break
  (FR-042).

## User Scenarios & Testing *(mandatory)*

The actors are **the family** (the parent who launches alfabeta and helps at home, reading Spanish
only), **the student** (a viewer of the topic's notebook) and **the teachers** (never interact).

### User Story 1 - An announced exam gets its full pack, checked before anyone sees it (Priority: P1)

An exam is announced. As soon as it is known, alfabeta proposes the topic's blocks from its folder,
taking the announcement's points, in its order, when it has them; once they are confirmed it makes,
in the topic's notebook, one explainer video per block, a practice sheet, a quiz and flashcards in
the subject's language, a study guide and a mind map. When the blocks were confirmed before the
announcement, it compares the announcement's points with them and makes one video for each point
no block covers, and nothing else. It checks every piece before showing it: the language of the
whole text, every number, and that the practice problems do not reuse the teacher's data.

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
6. **Given** blocks confirmed before the announcement, **When** the announcement names a point no
   block covers, **Then** the notebook gains one video for that point, numbered after the existing
   pieces, and no other piece is made again.
7. **Given** a proposed video whose exclusion names a textbook lesson, a notes page or a Classroom
   item with no source saying it is out of the exam, **When** the blocks are shown to the family,
   **Then** that item is shown as a question, not written into the exclusion.

---

### User Story 2 - The parent's material, in Spanish and out of the notebook (Priority: P1)

The parent opens the topic's `notebook/` folder and finds, in Spanish, the blocks with the files
they came from, a guide with questions to ask at home and the expected answers, the teacher's
answer key recomputed with every mismatch marked, and a glossary in the subject's language, Spanish
and English. None of it is in the Gemini notebook, where the student studies; the `notebook/`
folder also holds what the student uses, and the family chose no separate folder for the parent.

**Why this priority**: the parent cannot help without it, and a wrong key discourages the student.

**Independent Test**: with the same test topic, check that `notebook/` holds the four documents as
PDF and Markdown, that the known wrong answer is marked with its correct value, and that the
Gemini notebook lists none of them.

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

The family prints the topic. In the topic's `notebook/` folder in Drive there is one A4 PDF with
an index of every piece (videos marked as "in the notebook") and then each piece on a new page in
the numbered order: the practice sheet, the quiz with its answers at the end, the flashcards as a
table, the study guide and the mind map drawn as a diagram. Formulas print as formulas.

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

The family drops photos of the student's class notes into the topic's `notes/` folder. They are
transcribed literally, the transcription is checked by someone who can read the notes, and only
then does it become a source of the notebook — the most trusted one: when the notes show what was
taught, the blocks follow them.

**Why this priority**: the notes are the best evidence of what the exam asks, but turning photos
of handwriting into a usable source had not been tried when this was written.

**Independent Test**: with photos in `notes/` that stress an idea the textbook barely covers,
check that the proposed blocks include it.

**Acceptance Scenarios**:

1. **Given** photos in `notes/` with a checked transcription, **When** the pack runs, **Then**
   the transcription is a source of the notebook and the proposed blocks cite it.
2. **Given** photos whose transcription nobody has checked, **When** the pack runs, **Then** they
   are not a source and the family is told.

> Superseded on 2026-10-27 by spec 005 (julioarguello/alfabeta#44): transcriptions reach the
> notebook without a check, each page saying it is automatic and whether the student checked it,
> and only through the topic's living notes file: the pack adds no source of its own for them.
> The ranking of the notes first is unchanged.

---

### User Story 7 - The day before an exam, two sheets on paper (Priority: P1)

An exam is announced. The family runs one command: alfabeta asks the topic's notebook, with fixed
prompts, for two reports — a theory sheet the student works through in the study slot, following a
plan printed on it, and a problems sheet with one worked problem for each kind of problem the
teacher's photocopies hold — and prints each into the topic's `exam/` folder. Nobody writes them
by hand, and no Claude is involved.

**Why this priority**: the notebook's pieces are for practice spread over days; the day before an
exam the student has one slot, and needs what the announcement names, in the order it names it, on
paper.

**Independent Test**: run the command against a test notebook whose sources hold an announcement,
class notes, a textbook chapter and two photocopies, one of them with a known wrong answer and one
worked example that contradicts itself, for a 90-minute slot; then read the two PDFs against the
acceptance scenarios. It needs a real notebook: the command's own tests use a stand-in for `nlm`
and cannot judge what the notebook writes.

**Acceptance Scenarios**:

1. **Given** an announcement that lists three points, **When** the command runs, **Then** the
   theory sheet's sections are those three points in the announcement's order.
2. **Given** an exam whose announcement has not been captured, **When** the command runs, **Then**
   it refuses, says so, and asks the notebook for nothing.
3. **Given** notebooks switched off in the configuration, or `nlm` signed out or failing, **When**
   the command starts, **Then** it refuses with a message that names the cause, and prints nothing.
4. **Given** a study slot, **When** the theory sheet is printed, **Then** it fits the pages that
   slot allows (four for 90 minutes, measured once) and opens with a plan that divides the slot by
   section, whose last step is a blank-page recall; a longer sheet is printed and reported.
5. **Given** a term the class material writes in the subject's language, **When** it appears on
   either sheet, **Then** it is written first in that language, then in Spanish.
6. **Given** a study guide made before the last revision of the topic's living notes file,
   **When** the command runs, **Then** the guide is regenerated before anything is printed.
7. **Given** the teacher's photocopies, **When** the problems sheet is read, **Then** every
   exercise is in exactly one pattern, exercises printed on two photocopies are named as repeats,
   each pattern has one worked problem (one the teacher assigned when the pattern has one), each
   statement is in its original language followed by a Spanish translation, and the solutions come
   only after a page break.
8. **Given** a photocopy with a known wrong printed answer, **When** the problems sheet is read,
   **Then** a table after the solutions lists it with the printed and the right value, and names
   no one.

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
- An exam is announced only in class, or spec 001 detected it in a material or an assignment, so
  there is no announcement: the command refuses it (FR-030); how the family would give such an
  exam's scope is not designed (Assumptions).
- The exam is on an earlier topic than the subject's most recent one: the family names the topic,
  since the announcement does not give it (FR-030).
- The notebook's theory sheet runs longer than the slot allows: it is printed, and the command
  reports its page count; it is not regenerated (FR-031).
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
  material, textbook; not spec 005's living files, which repeat them), naming for each block the
  files it comes from, and MUST NOT generate until they are confirmed — the mind map excepted: it
  takes no focus, so it reads the sources, not the blocks, and the proposal maps its first-level
  branches like the textbook's lessons and the notes' pages. When the teacher's announcement of
  the exam exists, its points, in its order, are the proposed blocks. Once
  confirmed, the blocks of a topic are not proposed again, with one exception: an announcement
  that arrives later reopens them for the points it names that no block covers (FR-022). A
  video's exclusion MUST name only the other blocks and what a source says is out of the exam,
  with that source; a textbook lesson, a notes page or a Classroom item is never excluded for not
  being practised in the teacher's sheets.
- **FR-002**: When sources disagree about what the exam asks, the class notes MUST win over
  Classroom and Classroom over the textbook.
- **FR-003**: Two ideas that the teacher's material or the parent's guide name as a typical
  confusion MUST fall in different blocks; a point of the announcement that holds such a pair is
  two blocks.

**Generation**

- **FR-004**: The pack MUST hold, in the topic's single notebook: one explainer video per block, a
  practice sheet, a quiz, flashcards, a study guide and a mind map. Class notes become a source
  as their literal transcription (spec 005, which superseded the check this requirement asked for).
- **FR-005**: Videos and the study guide MUST be in Spanish, giving each key term also in the
  subject's language (the one it is taught and examined in) as the class material writes it.
  Practice sheet, quiz and flashcards MUST be in the subject's language, configured per subject.
  The exam's problems sheet is the exception (FR-029).
- **FR-006**: The practice sheet MUST go from a fully worked example to partly worked ones to
  problems without help, with the solutions in a separate section at the end, and MUST NOT reuse
  any numeric data of the teacher's sheets.
- **FR-007**: Any change to a setting of the notebook account that affects other notebooks MUST be
  undone before the run ends, whether it succeeds or fails.
- **FR-008**: A run MUST NOT create a second notebook for a topic.

**Verification**

- **FR-009**: Before the family is told the pack is ready, alfabeta MUST check the language of
  every piece's whole text (for a video, its on-screen text), recompute every numeric answer, and,
  for the practice sheet, compare its data with the teacher's sheets. The exam sheets of
  `exam prep` are the one exception: nothing checks them before they print but their page count,
  neither their language nor their numbers, which the notebook computes (FR-036).
- **FR-010**: A piece that fails verification MUST NOT be in the notebook when the run ends; it is
  regenerated or reported.
- **FR-011**: Every teacher's answer key in the topic's `classroom/` (not in spec 005's living
  Classroom file, which repeats them) MUST be recomputed; each mismatch, and each statement
  missing a datum, is recorded for the parent's guide.

**The parent's material**

- **FR-012**: The topic's `notebook/` folder MUST hold, in Spanish: the confirmed blocks with their
  sources; a parent's guide with questions to ask at home and the teacher's sheets translated and
  recomputed, each mismatch marked neutrally; and a glossary (the subject's language, Spanish, English,
  one-line definition, formula). The guide and the glossary as PDF and Markdown.
- **FR-013**: None of the parent's material may be visible in the notebook when the run ends.

**Order and names**

- **FR-014**: Every piece's title MUST be in Spanish and start with its moment — `HOY`, `Ayer`,
  `REPASO SEMANA` or `EXAMEN <weekday>` — followed by its number within that moment when there are
  several; it says what the piece is, what it is about and, for a video or quiz, its measured length
  or question count, with no date and no recipient. A piece in the subject's language says so.
- **FR-015**: When a run ends, the notebook's list MUST open with «0 · Guía de estudio», a report
  that numbers every other piece in study order, says how to use each video (notes taken on the
  student's own scheme), gives each session its minutes and a break, and says what the student can
  do when the session ends, and holds no theory; and among the pieces «Resumen de tus apuntes»,
  the notes condensed on their schemes, one short part per block session. The guide replaces the note «0 · Empieza aquí» (2026-10-29). `exam prep`
  (FR-029) still writes that note until it follows this requirement. No title and no note may
  present a piece as optional.
- **FR-016**: The notebook's chat MUST be set to answer as a tutor: a hint before the answer,
  Spanish explanations with the exam's terms, the source order of FR-002, and no attribution of a
  source to a person.

**Printing**

- **FR-017**: alfabeta MUST write one A4 PDF per topic into the topic's `notebook/`, holding an
  index of every piece in the notebook's order, then the start note, then every piece except
  videos, each on a new page: the
  quiz with its answers after its questions, the flashcards as a table, the mind map as a diagram
  that fits one page.
- **FR-018**: Formulas MUST print as typeset formulas, and lists and tables as such.
- **FR-019**: Each of the parent's documents in `notebook/` MUST also print as its own PDF.

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
  no answer within one day, it makes it with the proposed blocks and says so. When the blocks were
  confirmed before the announcement, it MUST compare the announcement's points with them and make
  one explainer video per point no block covers, numbered after the existing pieces, and MUST NOT
  make any other piece again. The family is told how many afternoons remain before the exam.
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

- **FR-029**: alfabeta MUST provide a command, `exam prep` ([contract](contracts/cli.md)), that for
  a known exam (FR-022) asks the topic's notebook for two reports with fixed prompts, a theory
  sheet and a problems sheet, titles them as pieces of the moment `EXAMEN <weekday>` (FR-014),
  numbered after the pieces that moment already holds, rewrites the start note (FR-015), records
  them (FR-024), and prints each as its own A4 PDF (FR-018) into the topic's `exam/` folder,
  whose name carries no date: `exam/Teoría para el examen · TNN (<D> <mmm>).pdf` and
  `exam/Problemas tipo · TNN (<D> <mmm>).pdf`, with the topic's number and the exam's date. The prompts are fixed texts of the repository, filled
  only with the exam's date, its announcement and that announcement's date, the study slot and the
  pages it allows, the subject's folder and language, and the grade level. Both reports are asked
  for in Spanish, terms and statements aside (FR-032, FR-035), with the report's own language
  option, so the account-wide setting of FR-007 is not touched. That makes the problems sheet an
  exception to FR-005, which puts practice in the subject's language: it is the sheet the parent
  reviews with the student, as observed 2026-10-28. No agent writes either sheet.
- **FR-030**: The exam's scope MUST come from the teacher's announcement of the exam, as spec 001
  captures it (text and date). The topic is the one the family names, or else the subject's most
  recent topic (FR-023): spec 001 files announcements outside any topic. The theory sheet quotes the
  announcement in its language with its date, its sections are the announcement's points in the
  announcement's order, and it says what of the topic the announcement leaves out. When the exam has
  no captured announcement, including an exam spec 001 detected in a material or an assignment, the
  command MUST refuse and ask the notebook for nothing.
- **FR-031**: The theory-sheet prompt MUST ask the notebook to follow the class notes, completed by
  Classroom and then the textbook (FR-002), and to fit the study slot (measured 2026-10-28: four
  A4 pages for 90 minutes). The sheet opens with a plan that divides the slot by section, with
  clock times and a short break, and whose last step is a blank-page recall: write from memory, in
  the subject's language, what the sheet holds that the exam asks to reproduce, then correct it
  against the sheet. Each section carries a way to test it without looking, with its answers. The
  command reports the printed page count against the slot; a longer sheet is printed and
  reported, not regenerated.
- **FR-032**: On both sheets every term MUST appear first in the subject's language, as the class
  material writes it, and then in Spanish. Where the notes, the teacher's sheets and the textbook
  use different words for one thing, or one word for two things, the theory sheet shows each and
  how to tell them apart.
- **FR-033**: The command MUST first bring the notebook's class-notes source up to date, as spec
  005's refresh does. When the topic's living notes file was last revised after the topic's study
  guide was made, the command MUST regenerate the guide (FR-004), even though the pack record
  (FR-024) holds it, before anything is printed. A guide made before the notes is never handed out
  for an exam.
- **FR-034**: The problems-sheet prompt MUST ask the notebook to put every exercise of the
  teacher's Classroom photocopies, worked examples included, into a pattern, using as few patterns
  as possible: one formula is about one pattern, and solving the same formula for another unknown
  (direct or inverse) is the same pattern; a chain of formulas, or a classification with none, can
  also be one. The sheet names the photocopies with their dates, maps each pattern to its
  exercises, names the exercises printed on two photocopies and marks those the teacher assigned.
- **FR-035**: For each pattern the problems sheet MUST work one problem, the hardest, preferring one
  the teacher assigned, and say why it is the hardest; it may name a second one of the same pattern
  for spare time. Each worked problem gives its statement in its original language followed by a
  Spanish translation. The sheet gives the order and about how long each pattern takes, and every
  solution comes after a page break, at the end.
- **FR-036**: The notebook computes every number of both sheets. This is an accepted risk
  (see Clarifications) and the one exception to FR-009 and SC-001. The
  problems-sheet prompt MUST ask the notebook to recompute every answer the photocopies print and
  compare it at the printed precision, equal when within half a unit of the last digit printed,
  and to list after the solutions, in a table under a neutral heading that names no one, each
  disagreement with the exercise, the printed value, the computed value and what went wrong, and
  each statement missing a datum with its result under each reading. A difference that only comes
  from rounding before the end is noted beside its solution, not in the table. Outside the table,
  a wrong printed value appears only in the worked solution of that same exercise, with its cause.
  A check of the sheets' numbers by a model that executes code MAY later be inserted between
  generation and printing, for that step alone.
- **FR-037**: Before it asks the notebook for anything, the command MUST refuse, with a message
  that names the cause and its exit code, and print nothing, when notebooks are switched off in the
  configuration, when `nlm` is signed out or failing, and when the exam, its announcement or the
  topic's notebook is not found (constitution VII). A report that fails later is reported, and the
  other one is still printed.

- **FR-039**: The study guide MUST link every video to its copy in the student's Drive (the topic's
  `notebook/` folder, step 9 of the skill), with a direct link to the file, and the folder itself
  once, whether or not the notebook shows the video to a viewer (measured 2026-10-29: the
  student's account saw every Studio piece except the three videos). The copy is made, and its link
  read, before the guide is generated.

- **FR-040**: A piece whose text alfabeta writes (the study guide's plan) MUST be checked line by
  line against that text after it is downloaded, links included, and generated again until it
  matches, at most three times; if it still does not match, the run says so and the family is
  told, rather than leaving a rewritten guide in the notebook. Measured 2026-10-29: two of five
  verbatim requests came back verbatim.
- **FR-041**: Every term in the subject's language that a piece gives the student MUST come from the
  textbook in that language or from the teacher's material; a word from the notes is used as such
  a term only when one of those confirms it. So the textbook in the subject's language MUST be a
  source of the notebook before the summary, the quiz, the flashcards, the glossary or the parent
  guide are generated, and each is checked for words in another language given as the subject's.
- **FR-042**: The guide's plan MUST fit the whole topic in two hours at most: study blocks of 45
  minutes with a 15-minute break between them (an hour and a half of study), done in one day or
  two; block A the videos with the student's own scheme and its comparison, block B the practice,
  quiz and flashcards (the operator, 2026-10-29).

**Structure from the student's schemes**

- **FR-038**: When the topic's class notes hold a scheme (a tree, a concept map, a chain of arrows,
  a labelled drawing), the proposed blocks MUST be its branches, in its order and with the
  student's names for them, and `bloques.md` MUST name, for each block, the scheme and branch it
  comes from. What the textbook or Classroom teaches and no branch holds MUST be hung from the
  nearest branch or listed apart, never used to reorder the blocks; a branch no source explains is
  a question for the family. Every piece's title or opening line, the start note and the printed
  index MUST name the branch each piece covers. Notes without a scheme leave FR-001 as it is
  (constitution X).

### Key Entities

- **Topic**: a school year, subject and topic folder, with its notebook and the subject's language.
- **Block**: an idea the exam can ask; title, the files it comes from, confirmed or not.
- **Piece**: something in the notebook: kind (video, report, quiz, flashcards, mind map, note),
  number, title, language, audience (student or parent), verification result.
- **Correction**: an exercise of a teacher's sheet whose recomputed result differs from the sheet,
  or whose statement lacks a datum.
- **Pack record**: per topic, the blocks, the pieces with their moment, the materials each «HOY»
  piece covers, and the corrections, with dates (FR-024).
- **Exam sheet**: one of the two reports `exam prep` asks the notebook for, theory or problems: a
  piece of the moment «EXAMEN», also printed as its own A4 PDF in the topic's `exam/` folder
  (FR-029).
- **Pattern**: one way of solving that a group of the photocopies' exercises shares: a formula
  used directly or inversely, a chain of them, or a classification; its exercises, the ones the
  teacher assigned, and its hardest (FR-034, FR-035).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: No numeric answer the student sees differs from its recomputation, across every
  piece of every pack, the exam sheets aside (FR-036).
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
- **SC-011**: On a test topic whose photocopy prints a known wrong answer, the problems sheet's
  table lists it with the right value; and no exam sheet is printed when notebooks are switched off
  or `nlm` is not usable when the command starts.
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
- The study slot of an exam sheet is given on the command line each time: the configuration has no
  key for it (`[schedule]` holds the sync's times). Four pages for 90 minutes was measured once.
- When the exam sheets are made, relative to the exam, is the family's call: the one run,
  observed 2026-10-28, made them on the morning of the day before, for that afternoon's slot.
- Whether the notebook's reports follow the fixed prompts closely enough — every exercise in a
  pattern, the terms first in the subject's language, the page count, the table of wrong printed
  answers — has not been measured: the sheets observed 2026-10-28 were written by an agent, not by
  the notebook. The first run of `exam prep` is that measurement, and the prompts are unmeasured
  until then.
- The teacher's photocopies are sources of the topic's notebook (spec 005's Classroom living file,
  or added as sources); a photocopy that is not cannot be mapped.
- An exam announced only in class, or detected in a material or an assignment, has no announcement
  text, so the command refuses it; how the family
  would give such an exam's scope is not designed.
- The quota cost of `exam prep` (two reports, three when the guide is regenerated) has not been
  measured; SC-006 measured a whole pack.

## Dependencies

- Spec 001 (`classroom-sync`): the topic folders, and the agenda that carries new topics and
  announced exams (FR-020, FR-022), including an exam announced only on the stream, with a link to
  the announcement (its User Story 2); and the stream's announcements saved with their text and
  creation date (its User Story 6), from which the exam sheets take their scope (FR-030).
- `nlm` (`notebooklm-mcp-cli`), `pandoc`, Graphviz and Google Chrome on the machine that runs it.
- A browser session of the notebook's owner for the one setting `nlm` cannot change: the output
  language of quiz and flashcards is account-wide (FR-007). The run drives that session itself.
