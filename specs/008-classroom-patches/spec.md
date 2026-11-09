# Feature Specification: Patches over what Classroom gives

**Feature Branch**: `docs/184-spec-008-patches` (spec dir `008-classroom-patches`)

**Created**: 2026-11-05

**Status**: Draft

**Input**: Operator's request (translated from Spanish), julioarguello/alfabeta#184: "you could
complement the Classroom material with what I gave you: if Classroom has a note saying do such
exercises, you put the download of what is there, but you can also accompany the solutions, or
complement with the statements when they do not come in the task" («si en Classroom hay una nota que
dice hacer tales ejercicios… también puedes acompañar las soluciones o complementar con los enunciados
cuando no vengan en la tarea»); "it is important that you unify it" («es importante que lo unifiques»);
and "I would feel more comfortable with patches over what you download from Classroom" («me sentiría
más cómodo con parches sobre lo que te bajas de Classroom»).

## Context and scope

Spec 001 replicates what the teacher posts, as it is. That leaves three gaps a student meets when he
sits down with a task:

- The task names a book page and shows nothing, so he cannot read what he is asked unless he has the
  book in front of him.
- The solutions come in another file, or never.
- A printed answer can be wrong. On one real school year's material, recalculating the printed answers
  found errors in the teacher's sheets, in a book's worked examples and in a summer booklet.

The family holds some of what is missing, and alfabeta can calculate some of the rest. This is a
capability of its own, as class notes are in spec 005: not to copy Classroom but to **complete and
correct** it, without ever changing what the teacher gave.

### What was done by hand first

On 2026-11-05 the family handed over photos of book pages and a PDF of solutions for a class's tasks.
They were matched to their tasks, every solution was recalculated, each exercise was put with its
solution, and one PDF per task was printed. The numbers here describe that one run:

| Measured by hand | Result |
|---|---|
| Tasks in that class citing the book with no image of the exercises | 4 of 23 items |
| Tasks in another class meeting the same test | 0 of 13 items |
| Solutions the family handed over, recalculated | 36, none wrong |
| Exercises that came with the pages and that no task set | 46 |

### In this spec

- Recognising and reporting a task that lacks its statement.
- A `patches/` subfolder inside a task's folder, and what a patch must say about itself.
- One document per task, joining each exercise with its solution.
- What happens to patches when the task moves or the teacher changes it.

### Out of this spec

- Writing anything to Classroom (constitution IV).
- Exam dates the family declares: that is spec 007, julioarguello/alfabeta#183.
- Standing rules per subject or per student, such as how finely to classify a subject's problems: those
  belong to spec 009, julioarguello/alfabeta#187, not to this mechanism.
- Bringing attachments Drive holds back: julioarguello/alfabeta#182.

### Changes elsewhere

| Where | What changes |
|---|---|
| Spec 001 | User Story 8 and FR-039 to FR-044, merged briefly as a `family/` folder, are withdrawn in favour of this spec; the numbers stay free. FR-011a's shared school-year folder shows patches to the other accounts. |
| Spec 001 placement | Moving an item moves its `patches/` too (FR-006 here). |
| Spec 002 | Study material may read a task's document as that task's material (FR-011 here). |
| Constitution, Technical constraints › Storage | Names the `patches` folder beside `submission`, through the amendment process. |
| `skills/classroom-sync/SKILL.md` | Its report lists the tasks lacking a statement. |

## Clarifications

### Session 2026-11-05

- Q: How is a statement Classroom does not carry recognised? → A: By the family's own test: the task
  sends the student to a book («do 21 to 24 of page 61») and attaches no image of those exercises.
- Q: A folder apart for what the family hands over, or inside what Classroom gives? → A: Inside, as
  patches over each task. A separate tree would need a direct analogy with Classroom's and would send
  the student to two places. A first version named the folder `family/`; the operator preferred
  patches, because the name should say what it does rather than who gave it, and because some patches
  do not come from the family at all.
- Q: What name? → A: `patches`. The operator weighed `amendments` (not a good word) and `homework`
  (which already means the tasks themselves), and chose `patches`.
- Q: Statement and solutions arrive in different files. What does the student get? → A: One document
  per task, each exercise followed by its solution, each part saying where it came from.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Knowing which tasks lack their statement (Priority: P1)

The family reads, after a sync, which tasks send the student to the book without showing the exercises,
with a link to each and the exercises it cites. They know exactly which pages to photograph.

**Why this priority**: it needs no patch to be useful, and it says what to go and fetch.

**Independent Test**: with invented tasks, one citing a page with no attachment, one citing a page and
attaching it, one with no book reference, sync and check that only the first is listed.

**Acceptance Scenarios**:

1. **Given** a task whose text cites book exercises and which has no attachment showing them, **When** it
   is synced, **Then** the report lists it with its link and the exercises it cites.
2. **Given** a task that cites the book and attaches the page, or one with no book reference, **When** it
   is synced, **Then** it is not listed.
3. **Given** a listed task whose exercises a patch now covers, **When** the report is written again,
   **Then** the task is no longer listed.
4. **Given** a task covered only in part, **When** the report is written, **Then** it stays listed with
   the exercises still missing.

---

### User Story 2 - One document per task, with each exercise and its solution (Priority: P1)

The family hands over photos and solutions, in whatever files they have. Each lands beside the task it
completes, and the student opens one document for that task: what the teacher asked, then each exercise
with its solution.

**Why this priority**: it is what the student sits down with.

**Independent Test**: hand over an invented photo for a task lacking its statement and an invented
solutions file for a task with a sheet. Check that each sits in its task's `patches/`, that the teacher's
replicas did not change, and that one document per task holds each exercise with its solution and the
source of each part.

**Acceptance Scenarios**:

1. **Given** a photo of a cited page, **When** it is matched to the task, **Then** it sits in that task's
   `patches/`, and the teacher's replicas are unchanged.
2. **Given** statements and solutions in different files, **When** the document is built, **Then** each
   exercise appears followed by its solution, each part naming its source.
3. **Given** a solution that does not match its recalculation, **When** the document is built, **Then** it
   shows both values and says so.
4. **Given** an exercise with no solution handed over, **When** the document is built, **Then** it carries
   a calculated solution marked as such, or says it has none; it is never left out in silence.
5. **Given** exercises in a file that no task set, **When** they are kept, **Then** they are told apart as
   practice and never mixed with what was set.
6. **Given** a file the family did not point at, in the same folder as those they did, **When** material
   is taken, **Then** that file is neither read, moved nor listed.

---

### User Story 3 - Correcting what the teacher's material prints wrong (Priority: P2)

A printed answer that does not match its recalculation becomes a patch on that item, so the student who
gets another result knows he may be right, and what the teacher's sheet says stays visible.

**Why this priority**: it needs the first two. It also shows why the source belongs to each patch: these
corrections do not come from the family.

**Independent Test**: with an invented sheet printing one wrong answer, build the item's document and check
that it shows the printed value, the recalculated one and the warning, and that the sheet itself did not
change.

**Acceptance Scenarios**:

1. **Given** a printed answer that does not match, **When** the patch is written, **Then** it says which
   exercise, both values and how the second was obtained, and the replica is unchanged.
2. **Given** a statement whose data do not allow an answer, **When** it is recorded, **Then** it is reported
   as a doubt for the teacher, and no answer is invented.
3. **Given** a correction, **When** the student reads it, **Then** it tells him that what the teacher said in
   class is not known here, and to ask.

---

### User Story 4 - Patches follow their task (Priority: P2)

A task can move (a topic matched later, a topic split in subtopics) and the teacher can change it. Its
patches stay with it, and the family learns when one may have gone stale.

**Why this priority**: without it a patch is left behind in a folder nobody opens.

**Independent Test**: patch an invented task, confirm a topic match that moves it and check its `patches/`
moved with it. Then change the task's text and check the report says its patches should be looked at.

**Acceptance Scenarios**:

1. **Given** a patched task whose folder changes, **When** `classroom apply` runs, **Then** its `patches/`
   moves with it, without a second copy.
2. **Given** a patched task the teacher changes, **When** it is synced, **Then** the replica is placed as
   usual, the patches stay, and the report says they and the document should be reviewed.
3. **Given** the teacher later attaches the statement, **When** it is synced, **Then** both remain, and the
   task is no longer listed as lacking it.
4. **Given** a patched task the teacher withdraws, **When** it is synced, **Then** the patches are kept like
   any withdrawn item, never deleted.
5. **Given** patches in place, **When** `classroom apply` runs twice, **Then** the second reports 0 added and
   0 changed, and the patches are unchanged.

### Edge Cases

- A book reference in a sentence that sets no work («the book explains this on page 40»): judging it is
  Claude's, as with an exam candidate; a wrong listing costs the family one look.
- A book reference only inside an attachment's text: out of the test.
- A photo that also shows people, or anything other than the exercises: what reaches the student's folders is
  cropped to the exercises, and the document carries only their text.
- A photo whose page number cannot be read: it is matched by its exercises' content when that is possible, and
  the document says the page was deduced.
- A photo with unsure digits or exponents: the reading is marked `[?]`, and a solution that depends on it says
  which reading it used. It is never guessed in silence.
- An exercise that different tasks set: it appears in each, from the same patch.
- A file solving several tasks: each exercise goes to the task that sets it.
- Exercises from a page no task cites: kept as practice beside the nearest task of the same topic, labelled so.
- An announcement or a material, not an assignment, with a wrong printed answer: patched the same way. «Task» in
  this spec means any item with its own folder.
- A family's solution that is correct in another form: it counts as matching, and the family's form is shown.

## Requirements *(mandatory)*

### Functional Requirements

**Recognising what is missing**

- **FR-001**: A task whose text cites book exercises and which has no attachment showing them MUST be reported as
  lacking its statement, with its link and the exercises it cites. A reference inside an attachment's text is out
  of this test.
- **FR-002**: The report MUST stop listing a task once a patch or the teacher's attachment covers all its cited
  exercises, and MUST keep listing those still missing.

**Patches**

- **FR-003**: Whatever completes or corrects a task MUST live in a `patches/` subfolder of that task's folder,
  beside `submission/`. A task with none has no such folder.
- **FR-004**: Each patch MUST state what it amends (the task, and the exercises when it is narrower), its kind
  (statement, solution, correction or practice) and its source (family or calculated). The source belongs to the
  patch, never to the folder.
- **FR-005**: A patch MUST NOT change a replica. `classroom apply` MUST NOT overwrite, quarantine or count patches
  as replicas; the accounts the school-year folder is shared with (spec 001 FR-011a) see them where they are.
- **FR-006**: When a task's folder changes, its `patches/` MUST move with it, with no second copy left behind.
- **FR-007**: When the teacher changes a patched task, the report MUST say that its patches and its document should
  be reviewed. Patches are never removed by a sync.

**Taking the family's material**

- **FR-008**: Only the files the family points at MUST be taken. Other files in the same folder MUST be neither
  read, moved nor listed, and the family's originals stay where they were.
- **FR-009**: Matching a file to a task is proposed and recorded like any other decision. An unsure reading of a
  photo MUST be marked `[?]`.

**The task's document**

- **FR-010**: Each patched task MUST get one document holding the teacher's words for what was set and, per exercise,
  its statement and its solution, each part naming its source: teacher, family or calculated. Every calculated
  solution and every family solution that is a calculation MUST be recomputed; a difference MUST show both values,
  and an exercise with no solution MUST say so.
- **FR-011**: Study material MAY read a task's document as that task's material. A correction prevails over the
  printed answer it corrects, and the order among sources (constitution X, spec 002) does not change.

**What patches never do**

- **FR-012**: Patches MUST NOT change what alfabeta reports as Classroom's: no date, status or exam in the agenda or
  the calendar comes from one, and nothing is written to Classroom (constitution IV).
- **FR-013**: A family's files are a minor's data: they MUST stay out of the repository, logs and issues
  (constitution III). What reaches the student's folders MUST carry only the exercises, never whatever else a photo
  shows.

### Key Entities

- **Patch**: one file in a task's `patches/`, with what it amends, its kind and its source. Not a replica: Classroom
  is never its source.
- **Task's document**: the one document joining a task's exercises and solutions, built from the replica and its
  patches, and built again when either changes.
- **Task lacking its statement**: a task that cites exercises it does not show; a report line, not a stored fact.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a fixture, every task citing book exercises with no attachment showing them is listed and no other
  task is. A real run's listing matches the family's own count of such tasks.
- **SC-002**: In a task's document, every exercise set has its statement or says it lacks one, and every solution
  that is a calculation has been recomputed.
- **SC-003**: The teacher's replicas are byte-identical before and after patching, and a second `classroom apply`
  reports 0 added and 0 changed with patches in place.
- **SC-004**: After a move of a patched task, none of its patches remains in the old folder.
- **SC-005**: The student needs to open one document to have a task's statements and solutions, whatever number of
  files they came from.
- **SC-006**: No family file not pointed at is read, and no personal data reaches the repository (the guardrail).

## Assumptions

- The family hands over material by pointing at it in chat; a dedicated command is for the plan to decide.
- Practice no task sets stays beside the nearest task of its topic, labelled as practice. This is a default taken
  from the 2026-11-05 run, and the operator has not ruled on it; a topic-level place is the alternative.
- Solutions the family hands over may have been produced by another tool; they are recomputed all the same.
- Reading a photo needs a person's eye or Claude's: no local recognition is assumed.
- A subject with no exercises to calculate (a language's essay, say) gets statements and solutions as given, with
  nothing recomputed; the document says so.

## Dependencies

- Spec 001: the item's folder, placement, shares and the sync report.
- Spec 002: study material reading the document (FR-011).
- Constitution III and IV: minors' data, and read-only on the school's platforms.
