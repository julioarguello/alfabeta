# Feature Specification: Class notes and new material reach the topic's notebook by themselves

**Feature Branch**: `docs/44-spec-005-notes-to-notebook` (spec dir `005-notes-to-notebook`)

**Created**: 2026-10-27

**Status**: Draft

**Input**: Operator's request (translated from Spanish and condensed): "We scanned the notes, put
them in the notes folder, and then what happens? I want a trigger on any folder that sets something
off with the notebook. On one side you will have a sync task with Drive; on the other, the student
will be able to write into the notes folder. Either way, that write should set off an integration
with the notebook. That is where the magic would be."

## Context and scope

A file written into a topic folder changes nothing in the topic's notebook until someone runs the
study pack (spec 002) by hand. On 2026-10-26 the student's photos of his class notes reached the
notebook only because an operator transcribed them in a conversation and uploaded the result.

Two paths write into a topic folder:

- **classroom-sync** (spec 001) writes the teacher's material on the family's Mac, through the
  student's browser session.
- **The student** drops photos of his class notes into the topic's `apuntes/` folder, usually from
  his phone, into the Drive of his personal Gmail.

Spec 004 (julioarguello/alfabeta#30) moves the master folder out of the Google Drive for desktop
mount and writes Drive through alfabeta's own connection, one way, Mac to Drive. Once it does, a
photo uploaded from the phone stays in Drive and never reaches the Mac. This spec adds the other
direction for what the family puts into Drive, and the step from the topic folder to its notebook.
It is tracked in julioarguello/alfabeta#44.

Out of this spec:

- Generating or regenerating the study pieces (videos, practice sheet, quiz, flashcards): spec 002.
  This spec only says what new material adds.
- How Classroom is captured: spec 001.
- The Google connection, its accounts and scopes: spec 004.
- The school account's Drive. It is a one-way mirror that is never read back (constitution VII), so
  a photo the student puts there is not seen.
- The calendar.

### What was measured before writing this

| Fact | Observed with | Date |
|---|---|---|
| A Doc and a PDF in the student's Drive, shared read-only with the notebook owner, can be added to the owner's notebook as Drive sources | `nlm source add --drive` (notebooklm-mcp-cli 0.15.8) on a throwaway notebook, invented content | 2026-10-27 |
| When such a file changes in Drive, the notebook holds the new content one to two minutes after the notebook is next accessed; it does not refresh while nobody accesses it | Two edits of both files; reads every minute, then an 8-minute untouched wait (old content on the first read, new content 90 s later) | 2026-10-27 |
| `nlm source stale` reports every Drive source up to date even while the notebook holds old content | Same test | 2026-10-27 |
| Drive's change feed lists a file written through Drive for desktop 15 s after the write, with its parent folder and checksum | Drive API v3 `changes.list` from a saved start token, as the linked student account | 2026-10-27 |
| No public API adds a source to a consumer notebook; the official notebook API is for Enterprise notebooks inside a Google Cloud project | Google Cloud docs for Gemini Notebook Enterprise, read | 2026-10-27 |
| The Gemini API terms require users to be 18 or older and forbid services likely to be used by minors | ai.google.dev/gemini-api/terms, read | 2026-10-27 |
| The operator's Claude plan includes 200 USD a month of Claude API credit, in a Console workspace capped at 10 USD a month for alfabeta | Claude Console billing and spend-limit pages, company account | 2026-10-27 |

Who opens the notebook in the timing row was the owner. Whether a viewer opening it also triggers
the refresh was not measured.

## Clarifications

### Session 2026-10-27

(Pending: see the markers below.)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A photo of the notes becomes a transcription to check, without anyone running anything (Priority: P1)

The student photographs a page of his notes and uploads it to the topic's `apuntes/` folder in his
Drive. Without anyone starting anything, alfabeta transcribes it literally and leaves next to the
photo a PDF (the photo, then its text) and its Markdown, both marked as waiting for review, and
tells whoever checks transcriptions.

**Why this priority**: the notes are the most trusted source (spec 002) and the one that today
needs a person at a keyboard.

**Independent Test**: upload two invented photos of handwritten notes to a test topic's `apuntes/`
from a phone; without touching the Mac, check that a PDF and a Markdown marked for review appear
next to them and that the reviewer is told.

**Acceptance Scenarios**:

1. **Given** a photo uploaded to `apuntes/` from the phone, **When** the next run happens, **Then**
   a transcription marked for review is in the same folder and the reviewer is told which topic and
   how many pages.
2. **Given** two photos with the same content (the same file uploaded twice), **When** the run
   happens, **Then** the page is transcribed once and the duplicate is reported.
3. **Given** a transcription waiting for review, **When** any run happens, **Then** nothing of it
   reaches the notebook.
4. **Given** a page that cannot be read in places, **When** it is transcribed, **Then** those
   places are marked as unreadable or doubtful, never guessed.

---

### User Story 2 - A checked transcription reaches the notebook without adding a source (Priority: P1)

The reviewer marks the transcription as checked. alfabeta adds its pages to the topic's single
living notes file, `Apuntes · Tema NN.pdf`, in the topic folder. The notebook already has that file
as a source, so the next time someone opens the notebook it holds the new pages.

**Why this priority**: it is what the operator asked for, and the measurement on 2026-10-27 showed it
needs no unofficial tool once the source exists.

**Independent Test**: approve one transcription in a test topic whose notebook already has the
living file as a source; open the notebook and ask its chat about a word only that page holds.

**Acceptance Scenarios**:

1. **Given** a checked transcription, **When** the run happens, **Then** the living file holds its
   pages after the ones already there, in page order, and no new source is added to the notebook.
2. **Given** the notebook opened after that run, **When** two minutes pass, **Then** the notebook's
   copy of the living file holds the new pages.
3. **Given** a transcription rejected with corrections, **When** it is checked again, **Then** only
   the checked version reaches the living file.
4. **Given** a page already in the living file, **When** its photo is uploaded again, **Then** the
   page is not added twice.

---

### User Story 3 - New Classroom material reaches the notebook after each classroom-sync run (Priority: P2)

At the end of each classroom-sync run on the Mac, every new Classroom item of a topic reaches that
topic's notebook.

**Why this priority**: the teacher's material ranks second (spec 002) and classroom-sync already
runs on the Mac where the notebook tool works.

**Independent Test**: run classroom-sync twice against saved Classroom pages with one new invented
item; check that the notebook gains it once and that the second run changes nothing.

**Acceptance Scenarios**:

1. **Given** a new Classroom item in a topic, **When** classroom-sync ends, **Then** the item is in
   the topic's notebook as [NEEDS CLARIFICATION: one source per Classroom item, or appended to one
   living Classroom file per topic?].
2. **Given** a second run with nothing new, **When** it ends, **Then** the notebook is unchanged.
3. **Given** the notebook tool's session has expired, **When** classroom-sync ends, **Then** the
   folder is complete, the notebook step is reported as failed with what to run, and the next run
   catches up.

---

### User Story 4 - The family learns what changed and what it adds (Priority: P2)

After a run that changed something, the family reads, in Spanish, what reached each notebook, what
waits for review, what failed, and what the new material adds to the topic's study pack: an idea the
pieces do not cover, a definition they state differently. Nothing is regenerated.

**Why this priority**: adding a source changes no video, quiz or guide (spec 002), so without this
report the student studies a pack that silently misses what the notes stress.

**Independent Test**: approve a transcription that holds an idea the pack does not cover; check that
the report names that idea and the piece that misses it.

**Acceptance Scenarios**:

1. **Given** a run that changed nothing, **When** it ends, **Then** no report is sent.
2. **Given** a run that added notes the pack does not cover, **When** it ends, **Then** the report
   names what is missing and says that regenerating spends quota and is the family's decision.

---

### User Story 5 - A topic's notebook gets its living notes file once (Priority: P3)

When a topic's notebook is created, its `apuntes/` folder and an empty living notes file are created
with it, and the file is added to the notebook as a source. That is the only step that needs the
unofficial notebook tool on the Mac.

**Why this priority**: it happens once per topic and can be done by hand until it is automated.

**Independent Test**: create a test topic; check that the notebook has exactly one living notes
source and that a second run adds nothing.

**Acceptance Scenarios**:

1. **Given** a topic with a notebook and no living notes source, **When** the run happens on the
   Mac, **Then** the living file exists and is a source of the notebook.
2. **Given** Tema 01 of 2026-2027, whose checked notes were uploaded on 2026-10-26 as plain file
   sources, **When** the living file is set up, **Then** its content replaces those two sources and
   the family is told.

---

### Edge Cases

- **The living file is deleted or moved in Drive.** Google's announcement says the notebook then
  drops the source (not measured). alfabeta never deletes or moves it; if it is missing, the run
  reports it and does not recreate a second source.
- **Nobody opens the notebook.** Its copy of the living file stays old until it is opened, which is
  harmless: whoever studies opens it first.
- **A photo is put outside `apuntes/`**, or in the school Drive: it is not transcribed. The first is
  reported as an unexpected file; the second cannot be seen.
- **A photo is rotated, blurred or not of notes.** It is transcribed with its doubtful parts marked,
  or reported as not readable; a reviewer decides.
- **A photo is deleted after its page reached the living file.** The page stays; the family is told
  (constitution V).
- **The AI budget is spent** for the month: transcription stops, nothing else stops, and the family
  is told.
- **The notebook reaches its source limit.** The living file exists so notes never add sources; the
  limit for Classroom items is reported before it is reached.
- **The Mac is off** when the student uploads photos: see FR-013.

## Requirements *(mandatory)*

### Functional Requirements

**Detecting what arrives**

- **FR-001**: alfabeta MUST learn of every file added or changed under the alfabeta folder in the
  student's Drive, whatever wrote it (phone, web, Drive for desktop, alfabeta), from Drive's own
  record of changes, keeping its position in that record between runs so nothing is missed or read
  twice.
- **FR-002**: A file the family adds in Drive under a topic folder MUST be brought into the master
  folder, so the master stays complete once spec 004 leaves the Drive for desktop mount. This adds
  a Drive-to-master direction for files the family adds, which constitution VII does not have; the
  constitution is amended in the same pull request as this spec.
- **FR-003**: Each file MUST have one record: its Drive id, checksum, kind, and state (new,
  transcribed, waiting for review, checked, in the notebook, failed). Two runs with no change MUST
  write nothing (constitution V).

**Transcribing the notes**

- **FR-004**: Every image in a topic's `apuntes/` MUST be transcribed literally, keeping spelling and
  language, with the conventions the notes of 2026-10-26 used: text written between lines, crossed
  out text, doubtful readings, drawings described, boxed text. The result is a PDF (each photo, then
  its text) and its Markdown, named in Spanish and marked as waiting for review.
- **FR-005**: An image with the same checksum as one already transcribed MUST NOT be transcribed
  again; it is reported as a duplicate.
- **FR-006**: A transcription MUST NOT reach the notebook until it is checked (spec 002, User
  Story 6).
- **FR-007**: A transcription counts as checked when [NEEDS CLARIFICATION: who checks the notes and
  how they say so — the student, who reads them, by renaming the file in Drive from his phone; any
  family member answering in the Claude app; or something else?].

**Reaching the notebook**

- **FR-008**: Each topic MUST have one living notes file, `Apuntes · Tema NN.pdf`, in its folder in
  Drive, added once to the topic's notebook as a Drive source. Checked transcriptions are appended
  to it in page order. Notes never add another source.
- **FR-009**: alfabeta MUST NOT delete, rename or move a living file. A missing living file is
  reported and is not silently recreated.
- **FR-010**: New Classroom material MUST reach the notebook at the end of each classroom-sync run,
  each item once (constitution V). How it is held is the question in User Story 3.
- **FR-011**: Adding or updating a source MUST NOT regenerate any study piece. The run reports what
  the new material adds to the pack (User Story 4).

**Reporting**

- **FR-012**: A run that changed something MUST report, in Spanish, per topic: pages waiting for
  review, pages and items that reached the notebook, duplicates, unexpected files and failures. Logs
  name topics and counts, never the student (constitution III).

**Where it runs and what it may spend**

- **FR-013**: The notes path (User Stories 1, 2 and 4) MUST run [NEEDS CLARIFICATION: only on the
  family's Mac, at a schedule while it is on, as constitution IX says; or also with the Mac off, in
  the operator's company Google Cloud project, which amends IX?]. classroom-sync and the one-off
  notebook setup stay on the Mac in either case, because they need the student's browser session and
  the notebook tool.
- **FR-014**: The AI that transcribes MUST be the operator's Claude plan's API credit, in the
  alfabeta workspace and under its monthly spend limit. When the limit is reached, transcription
  stops and the family is told; nothing else stops.
- **FR-015**: Photos and transcriptions MUST go only to the services the family configured: the
  student's Drive, the notebook owner's notebook, and Claude (constitution III). No model whose
  terms exclude minors is used.

### Key Entities

- **Arrival**: a file seen in Drive's record of changes — its Drive id, topic, kind and checksum.
- **Notes page**: one photo and its literal transcription, with its review state and who checked it.
- **Living notes file**: one per topic, a PDF in the topic folder; its Drive id and the notebook
  source id it is bound to.
- **Notebook entry**: a Classroom item or a living file as the notebook holds it, with the run that
  put it there.
- **Change cursor**: the position in Drive's record of changes the last run reached.
- **Run report**: what changed per topic, in Spanish, plus failures.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A photo uploaded from the phone has a transcription waiting for review within one
  hour, with no one touching a computer, on every attempt over two weeks of real use.
- **SC-002**: After a transcription is checked, the notebook answers a question only that page can
  answer within five minutes of being opened.
- **SC-003**: Over a school term, no transcription that was not checked appears in any notebook.
- **SC-004**: Two consecutive runs with nothing new write nothing to Drive, the master folder or any
  notebook.
- **SC-005**: Over 30 classroom-sync runs, each Classroom item appears in its notebook exactly once.
- **SC-006**: A topic's notes add no source to its notebook beyond the one living notes file.
- **SC-007**: The month's spend on transcription stays under the workspace limit, and the report
  states what it was.
- **SC-008**: A search of the logs, reports and repository for the student's name or address finds
  nothing.

## Assumptions

- The student uploads photos to the topic's `apuntes/` folder in the Drive of his personal Gmail,
  the master. The school Drive is a mirror and is never read (constitution VII).
- The notebook owner's account can read the student's alfabeta folder in Drive; the notebook needs
  that to hold a Drive source.
- A Drive-backed PDF keeps refreshing the way it did on 2026-10-27. If Google changes it, the living
  file falls back to being replaced as a source by the Mac run.
- The transcription quality of the API model is at least that of the transcription of 2026-10-26,
  which the operator checked against the photos. Measured in the plan, on those photos.
- At about 4 to 8 pages per topic and two subjects, transcription spends 1 to 3 USD a month,
  estimated from the published image-token formula and model prices, not measured.

## Dependencies

- Spec 004 (julioarguello/alfabeta#30): Drive access as the student, the folder allowlist, and the
  move of the master folder out of the Drive for desktop mount. FR-002 must exist before that move,
  or photos from the phone stop reaching the master.
- Spec 001: classroom-sync, whose run ends with FR-010.
- Spec 002: the study pack, which ranks the notes first and owns regeneration.
- The operator: sharing the student's alfabeta folder with the notebook owner, and the Claude
  Console workspace for alfabeta (created 2026-10-27, no key yet).
