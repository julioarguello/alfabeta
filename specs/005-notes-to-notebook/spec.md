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

- **classroom-sync** (spec 001) captures the teacher's material on the family's Mac, through the
  student's browser session, and writes it to the master folder and to Drive (spec 004).
- **The student** drops photos of his class notes into the topic's `apuntes/` folder, usually from
  his phone, into the Drive of his personal Gmail.

Spec 004 (julioarguello/alfabeta#30) moves the master folder out of the Google Drive for desktop
mount and writes Drive through alfabeta's own connection, one way, Mac to Drive. Once it does, a
photo uploaded from the phone stays in Drive and never reaches the Mac. This spec adds the other
direction for what the family puts into Drive, and the step from the topic folder to its notebook,
which runs in the cloud so it works with the Mac off. It is tracked in julioarguello/alfabeta#44.

Out of this spec:

- Generating or regenerating the study pieces (videos, practice sheet, quiz, flashcards): spec 002.
  This spec only says what new material adds.
- How Classroom is captured: spec 001. Capture stays on the Mac, because the school blocks the
  Classroom API for minors and only the student's browser session reads it.
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
| `nlm`'s own documentation advises against running it on a server: copied cookies expire early or are rejected | `docs/REMOTE_MCP.md` of the `nlm` project, read | 2026-10-27 |
| The desktop app's scheduled tasks run only while the app is open and the Mac awake | Claude Code docs, desktop scheduled tasks, read; spec 001 research R1 | 2026-10-27 |
| The Gemini API terms require users to be 18 or older and forbid services likely to be used by minors | ai.google.dev/gemini-api/terms, read | 2026-10-27 |
| The operator's Claude plan includes 200 USD a month of Claude API credit; a Console workspace for alfabeta, in the company organisation, is capped at 10 USD a month | Claude Console billing and spend-limit pages, company account | 2026-10-27 |

Who opens the notebook in the timing row was the owner. Whether a viewer opening it also triggers
the refresh was not measured.

The consequence that shapes this spec: once a notebook holds a Drive file as a source, keeping it
current needs only a write to Drive, which the cloud can do. Adding a source needs `nlm`, which only
works on the Mac. So each topic's notebook holds a few **living files** added once, and everything
that arrives later goes into them.

## Clarifications

### Session 2026-10-27

- Q: Does the notes path run with the Mac off? → A: Yes, in the cloud from the start: the operator's
  company Google Cloud project. Constitution IX is amended in the same pull request.
- Q: Who checks a transcription, and how? → A: Nobody has to. Transcriptions are taken as good and
  reach the notebook directly. If one is checked, the student checks it. This supersedes spec 002's
  rule that a transcription becomes a source only once checked.
- Q: How does new Classroom material reach the notebook? → A: Through one living Classroom file per
  topic, kept current from the cloud like the notes. The operator expected the notebook sync to run
  in the cloud, not on the Mac; a source per item would need `nlm` on the Mac for every item.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A photo of the notes reaches the notebook with no one at a computer (Priority: P1)

The student photographs a page of his notes and uploads it to the topic's `apuntes/` folder in his
Drive. Without anyone starting anything, and with the Mac off, alfabeta transcribes it literally,
leaves the transcription next to the photo as a PDF (the photo, then its text) and its Markdown, and
adds the page to the topic's living notes file. The next time the notebook is opened, it holds that
page.

**Why this priority**: the notes are the most trusted source (spec 002) and the one that needed a
person at a keyboard on 2026-10-26.

**Independent Test**: with the Mac off, upload two invented photos of handwritten notes to a test
topic's `apuntes/` from a phone; after the next run, open the notebook and ask its chat about a word
only one of the pages holds.

**Acceptance Scenarios**:

1. **Given** a photo uploaded to `apuntes/` from the phone with the Mac off, **When** the next cloud
   run happens, **Then** its transcription is in the same folder and its page is in the living notes
   file, after the pages already there.
2. **Given** that run, **When** the notebook is opened, **Then** within two minutes the notebook's
   copy of the living file holds the page, and no source was added.
3. **Given** two photos with the same content (the same file uploaded twice), **When** the run
   happens, **Then** the page is transcribed and added once and the duplicate is reported.
4. **Given** a page that cannot be read in places, **When** it is transcribed, **Then** those places
   are marked as unreadable or doubtful, never guessed.
5. **Given** any page in the living file, **When** the student or the tutor chat reads it, **Then**
   the page says it is an automatic transcription and whether the student has checked it.

---

### User Story 2 - The student corrects a transcription when he finds an error (Priority: P2)

Checking is optional. If the student finds an error, he marks that transcription from his phone. The
family is told, and a corrected transcription replaces the page in the living file.

**Why this priority**: transcriptions are taken as good; this is the way back when one is not.

**Independent Test**: mark one transcription of a test topic; check that the family is told and
that, once corrected, the living file holds the corrected page only once.

**Acceptance Scenarios**:

1. **Given** a transcription the student marks as wrong, **When** the run happens, **Then** the page
   in the living file says it is under correction and the family is told which topic and page.
2. **Given** a corrected transcription, **When** the run happens, **Then** it replaces the page in
   place, and the page no longer says it is under correction.
3. **Given** a transcription the student marks as checked, **When** the run happens, **Then** the
   page in the living file says it was checked by the student.

---

### User Story 3 - New Classroom material reaches the notebook with no one at a computer (Priority: P2)

When classroom-sync has put a new Classroom item of a topic into Drive, the next cloud run adds it
to that topic's living Classroom file, `Classroom · Tema NN.pdf`: a cover page with the item's
title and posting date, then the item's own pages and images.

**Why this priority**: the teacher's material ranks second (spec 002), and without this the
notebook only learns of it when someone runs the study pack.

**Independent Test**: put one invented Classroom item into a test topic's `classroom/` folder in
Drive; after the next run, open the notebook and ask about a fact only that item holds; run again
and check that nothing changed.

**Acceptance Scenarios**:

1. **Given** a new Classroom item in a topic's `classroom/` folder in Drive, **When** the next cloud
   run happens, **Then** the living Classroom file holds its cover page and pages, and no source was
   added.
2. **Given** a second run with nothing new, **When** it ends, **Then** the living file is unchanged.
3. **Given** an item that is not a document (a link or a video), **When** it is added, **Then** its
   cover page carries its title, date and address, and the report says it holds no pages.
4. **Given** an item edited by the teacher, **When** classroom-sync brings the new version, **Then**
   its pages in the living file are replaced in place, not added again.

---

### User Story 4 - The family learns what changed and what it adds (Priority: P2)

After a run that changed something, the family reads, in Spanish, what reached each notebook, what
the student marked, what failed, and what the new material adds to the topic's study pack: an idea
the pieces do not cover, a definition they state differently. Nothing is regenerated.

**Why this priority**: adding material changes no video, quiz or guide (spec 002), so without this
report the student studies a pack that silently misses what the notes stress.

**Independent Test**: add notes that hold an idea the pack does not cover; check that the report
names that idea and the piece that misses it.

**Acceptance Scenarios**:

1. **Given** a run that changed nothing, **When** it ends, **Then** no report is sent.
2. **Given** a run that added material the pack does not cover, **When** it ends, **Then** the report
   names what is missing and says that regenerating spends quota and is the family's decision.

---

### User Story 5 - A topic's notebook gets its living files once (Priority: P3)

When a topic's notebook is created, its two living files are created with it, empty but for a cover
page, and added to the notebook as Drive sources. That is the only step that needs the notebook tool
on the Mac.

**Why this priority**: it happens once per topic and can be done by hand until it is automated.

**Independent Test**: create a test topic; check that the notebook has exactly one living notes
source and one living Classroom source, and that a second run adds nothing.

**Acceptance Scenarios**:

1. **Given** a topic with a notebook and no living sources, **When** the setup runs on the Mac,
   **Then** both living files exist in the topic folder and are sources of the notebook.
2. **Given** a topic whose notebook already holds notes or Classroom material as plain file sources
   (Tema 01 of 2026-2027 holds its notes that way since 2026-10-26), **When** the living files are
   set up, **Then** that material is moved into them, the plain sources are listed for the family to
   remove, and nothing is removed by alfabeta.
3. **Given** the cloud run finds a topic with no living sources, **When** it ends, **Then** the
   report says that topic waits for the setup on the Mac, and its material waits in its folder.

---

### Edge Cases

- **A living file is deleted or moved in Drive.** Google's announcement says the notebook then drops
  the source (not measured). alfabeta never deletes or moves it; if it is missing, the run reports it
  and does not recreate a second source.
- **Nobody opens the notebook.** Its copy of a living file stays old until it is opened, which is
  harmless: whoever studies opens it first.
- **A photo is put outside `apuntes/`**, or in the school Drive: it is not transcribed. The first is
  reported as an unexpected file; the second cannot be seen.
- **A photo is rotated, blurred or not of notes.** It is transcribed with its doubtful parts marked,
  or reported as not readable and left out of the living file.
- **A photo is deleted after its page reached the living file.** The page stays; the family is told
  (constitution V).
- **The AI budget is spent** for the month: transcription and the "what it adds" report stop,
  everything else continues, and the family is told.
- **A living file grows past what the notebook accepts for one source.** Reported before the limit
  is reached; splitting a living file is a decision for the family.
- **The cloud run cannot reach Drive** (link revoked, spec 004): it writes nothing and the family is
  told on a channel that does not need that link (spec 004, FR-014).

## Requirements *(mandatory)*

### Functional Requirements

**Detecting what arrives**

- **FR-001**: alfabeta MUST learn of every file added or changed under the alfabeta folder in the
  student's Drive, whatever wrote it (phone, web, Drive for desktop, classroom-sync), from Drive's
  own record of changes, keeping its position in that record between runs so nothing is missed or
  read twice.
- **FR-002**: A file the family adds in Drive under a topic folder MUST also be brought into the
  master folder on the Mac on the Mac's next run, so the master stays complete once spec 004 leaves
  the Drive for desktop mount. This adds a Drive-to-master direction for what the family adds, which
  constitution VII did not have; it is amended in the same pull request as this spec.
- **FR-003**: Each file MUST have one record: its Drive id, checksum, kind, topic, and state. Two runs
  with no change MUST write nothing (constitution V).

**Transcribing the notes**

- **FR-004**: Every image in a topic's `apuntes/` MUST be transcribed literally, keeping spelling and
  language, with the conventions the notes of 2026-10-26 used: text written between lines, crossed
  out text, doubtful readings, drawings described, boxed text. The result is a PDF (the photo, then
  its text) and its Markdown, named in Spanish, next to the photo.
- **FR-005**: An image with the same checksum as one already transcribed MUST NOT be transcribed
  again; it is reported as a duplicate.
- **FR-006**: A transcription MUST reach the notebook without anyone checking it. Every page says it
  is an automatic transcription, and whether the student checked it or marked it as wrong.
- **FR-007**: The student MUST be able to mark a transcription as checked or as wrong from his phone,
  in Drive, without any other tool. A page marked wrong stays in the living file, labelled as under
  correction, until a corrected transcription replaces it.

**Reaching the notebook**

- **FR-008**: Each topic MUST have two living files in its folder in Drive, `Apuntes · Tema NN.pdf`
  and `Classroom · Tema NN.pdf`, each added once to the topic's notebook as a Drive source. Material
  that arrives later goes into them; no other source is added for it.
- **FR-009**: Notes pages go into the living notes file in page order. Each Classroom item goes into
  the living Classroom file as a cover page (title, posting date, address if it has one) followed by
  its own pages and images, in posting order. A changed item or page is replaced in place.
- **FR-010**: alfabeta MUST NOT delete, rename or move a living file, nor remove a source from a
  notebook. A missing living file is reported and is not silently recreated.
- **FR-011**: Adding material MUST NOT regenerate any study piece. The run reports what the new
  material adds to the pack (User Story 4).

**Reporting**

- **FR-012**: A run that changed something MUST report, in Spanish, per topic: pages and items that
  reached the notebook, transcriptions marked by the student, duplicates, unexpected files, topics
  waiting for setup, and failures. Logs name topics and counts, never the student (constitution
  III).

**Where it runs and what it may spend**

- **FR-013**: Detection, transcription and the living files (FR-001, FR-003 to FR-011) MUST run in the
  cloud, in the operator's company Google Cloud project, on a schedule that does not depend on the
  family's Mac. The Drive-to-master copy (FR-002), Classroom capture (spec 001) and the one-off
  notebook setup (User Story 5) stay on the Mac. Constitution IX is amended in the same pull request.
- **FR-014**: The AI that transcribes and writes the "what it adds" report MUST be paid from the
  operator's Claude plan API credit, in the alfabeta workspace and under its monthly spend limit.
  When the limit is reached, those two steps stop and the family is told; nothing else stops.
- **FR-015**: Photos and transcriptions MUST go only to the services the family configured: the
  student's Drive, the notebook owner's notebook, the operator's Google Cloud project, and Claude
  (constitution III). No model whose terms exclude minors is used.
- **FR-016**: The cloud run MUST hold its Google authorisation and its Claude key as secrets of that
  project, never in the repository, the configuration, a log or an error message (constitution II).

### Key Entities

- **Arrival**: a file seen in Drive's record of changes: its Drive id, topic, kind and checksum.
- **Notes page**: one photo and its literal transcription, with its state: automatic, checked by
  the student, or marked wrong.
- **Living file**: one notes file and one Classroom file per topic, each a PDF in the topic folder,
  with its Drive id and the notebook source it is bound to.
- **Classroom entry**: a Classroom item as the living Classroom file holds it: its cover page, its
  pages, and the Drive file it came from.
- **Change cursor**: the position in Drive's record of changes the last cloud run reached.
- **Run report**: what changed per topic, in Spanish, plus failures.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A photo uploaded from the phone with the Mac off is in the topic's living notes file
  within one hour, on every attempt over two weeks of real use.
- **SC-002**: After that, the notebook answers a question only that page can answer within five
  minutes of being opened.
- **SC-003**: A Classroom item that classroom-sync put into Drive is in the living Classroom file
  within one hour of the upload.
- **SC-004**: Two consecutive runs with nothing new write nothing to Drive, the master folder or any
  notebook.
- **SC-005**: Over a school term, no notebook gains a source other than its two living files and the
  sources the study pack (spec 002) adds by hand.
- **SC-006**: Over 30 runs, each Classroom item and each notes page appears in its living file
  exactly once.
- **SC-007**: The month's spend on AI stays under the workspace limit, and the report states what it
  was.
- **SC-008**: A search of the logs, reports and repository for the student's name or address finds
  nothing.

## Assumptions

- The student uploads photos to the topic's `apuntes/` folder in the Drive of his personal Gmail,
  the master. The school Drive is a mirror and is never read (constitution VII).
- The notebook owner's account can read the student's alfabeta folder in Drive; the notebook needs
  that to hold a Drive source.
- A Drive-backed PDF keeps refreshing the way it did on 2026-10-27. If Google changes it, the living
  files fall back to being refreshed as sources by the Mac run.
- The transcription quality of the API model is at least that of the transcription of 2026-10-26,
  which the operator checked against the photos. Measured in the plan, on those photos.
- At about 4 to 8 pages per topic and two subjects, transcription spends 1 to 3 USD a month,
  estimated from the published image-token formula and model prices, not measured.
- The cloud run stays within the project's free tier; a billing account is still required to use it.

## Dependencies

- Spec 004 (julioarguello/alfabeta#30): Drive access as the student, the folder allowlist, and the
  move of the master folder out of the Drive for desktop mount. FR-002 must exist before that move,
  or photos from the phone stop reaching the master.
- Spec 001: classroom-sync, which puts each Classroom item into the topic's `classroom/` folder in
  Drive.
- Spec 002: the study pack, which ranks the notes first and owns regeneration. Its User Story 6 and
  FR-004 required a checked transcription; this spec supersedes that (Clarifications).
- The operator: sharing the student's alfabeta folder with the notebook owner, a billing account on
  the company Google Cloud project, and an API key in the alfabeta Console workspace (created
  2026-10-27, no key yet).
