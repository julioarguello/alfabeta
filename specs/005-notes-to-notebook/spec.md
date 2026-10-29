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
- **The student** drops photos of his class notes into the topic's `notes/` folder, usually from
  his phone, into the Drive of his personal Gmail.

Spec 004 (julioarguello/alfabeta#30) moves the master folder out of the Google Drive for desktop
mount and writes Drive through alfabeta's own connection, one way, Mac to Drive. Once it does, a
photo uploaded from the phone stays in Drive and never reaches the Mac. This spec adds the other
direction for what the family puts into Drive, and the step from the topic folder to its living
files, which runs in the cloud so it works with the Mac off; the notebook takes those files when the
Mac's refresh reads them (FR-018). It is tracked in julioarguello/alfabeta#44.

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
| Drive's change feed takes no folder filter: its only scoping parameters are `spaces` and `restrictToMyDrive` | developers.google.com/workspace/drive/api/guides/manage-changes, read | 2026-10-27 |
| The Gemini API terms require users to be 18 or older and forbid services likely to be used by minors | ai.google.dev/gemini-api/terms, read | 2026-10-27 |
| Anthropic's Usage Policy sends "products serving minors" to additional guidelines when an organisation provides "minors with the ability to directly interact with products that incorporate our API(s)"; it sets no age bar for content a customer sends | anthropic.com/legal/aup, read. Here the operator is the customer and the student never interacts with the API: he uploads photos to his Drive. That reading is ours, not Anthropic's | 2026-10-27 |
| The operator's Claude plan includes 200 USD a month of Claude API credit; a Console workspace for alfabeta, in the company organisation, is capped at 10 USD a month | Claude Console billing and spend-limit pages, company account | 2026-10-27 |
| The student's own access, as a viewer, does not make the notebook take a changed living file: about fifty minutes with the notebook open and three questions left its copy without the page. The owner's first read of the source (`nlm source content`) still returned the old copy; the next read, 76 seconds later, held the page, and the student's view answered at 10:05 UTC, under three minutes after the first read. Whether one read is enough is open (research R14) | Quickstart step 3, owner-free repeat on a test topic: `nlm source content` once a minute as the owner, the operator's report of the student's view (research.md, first table) | 2026-10-28 |
| The owner's `nlm` session on the Mac, signed in on 2026-10-26, still worked two days later; its Google cookies expire on 2027-11-30, and `nlm auth refresh --http-only` ran with no browser and left it valid | `nlm login --check` before and after the refresh, `nlm notebook list` as control; cookie names and expiry dates from `nlm`'s own browser profile, never their values | 2026-10-28 |
| A launchd job with `StartCalendarInterval` that falls due while the Mac sleeps runs once when it wakes; one with `StartInterval` skips the missed firings | `man launchd.plist` on the operator's Mac, read | 2026-10-28 |

Who opens the notebook in the timing row was the owner. Whether a viewer opening it also triggers
the refresh was not measured. Measured on 2026-10-28: it does not (rows above).

The consequence that shapes this spec: once a notebook holds a Drive file as a source, keeping its
content current needs only a write to Drive, which the cloud can do. Adding a source needs `nlm`, which only
works on the Mac. So each topic's notebook holds a few **living files** added once, and everything
that arrives later goes into them. The notebook takes a changed living file only when its owner
reads it, and that read also needs `nlm`: the Mac does it, on its own schedule and with no app open
(Clarifications, session 2026-10-28).

## Clarifications

### Session 2026-10-27

- Q: Does the notes path run with the Mac off? → A: Yes, in the cloud from the start: the operator's
  Google Cloud project for alfabeta. Constitution IX is amended in the same pull request.
- Q: Who checks a transcription, and how? → A: Nobody has to. Transcriptions are taken as good and
  reach the notebook directly. If one is checked, the student checks it. This supersedes spec 002's
  rule that a transcription becomes a source only once checked.
- Q: How does new Classroom material reach the notebook? → A: Through one living Classroom file per
  topic, kept current from the cloud like the notes. The operator expected the notebook sync to run
  in the cloud, not on the Mac; a source per item would need `nlm` on the Mac for every item.

### Session 2026-10-28

- Q: Only the owner's access makes the notebook take a changed living file, and the student opening
  it does not. Who reads the source as the owner, and when? → A: A launchd agent on the family's
  Mac, every 15 minutes, once on wake and once when the user's session starts, with no app open.
  The operator chose it among four options offered on 2026-10-28, this one being «B»: «De momento
  vamos a optar por B». The Mac being awake, with the family's user session logged in, is the
  accepted condition. The operator also asked for as little as possible to depend on the Mac and on
  starting Claude: «Quiero eliminar dependencias del mac», «necesito al máximo eliminar la
  dependencia de arrancar Claude». A cloud-held owner session — a cloud
  machine with Chrome and Chrome Remote Desktop, or an Android master token — was considered and
  declined for now; neither has been measured (research R14).
- Q: Where do the living files sit, now that a topic folder holds only folders? → A: Each in the
  folder its content comes from: `Apuntes · <topic>.pdf` in `notes/` (it was `apuntes/`) and
  `Classroom · <topic>.pdf` in `classroom/`, never at the topic folder's root, where they sat until
  then. Decided by the family on 2026-10-28 with every folder name the code decides in English
  (constitution 2.2.0, julioarguello/alfabeta#110); the cloud run's reports go in `reports/` (it
  was `Informes/`). In `classroom/` the living file is never itself a Classroom item, a file at a
  topic folder's root is reported as unexpected, and any other folder of the topic is not read.
  Tema 01's two living files, set up at its root on 2026-10-27, were moved by hand into their
  folders on 2026-10-28 (edge cases).


### Session 2026-10-29

Lessons from taking a biology topic's notes by hand, recorded for the final implementation.

- Q: Can the notes arrive some other way than photos in `notes/`? → A: Yes. The family pointed at a
  notebook the student had made with six photos as sources. `nlm source content` gives each image
  as an `lh3.googleusercontent.com` address that answers without a session; it serves a 384×512
  thumbnail, and the same address with `=s0` appended served the original 960×1280 (measured).
- Q: Is every photo the family gives a page of notes? → A: No. One of the six was a printed
  access PIN, a credential, among the notes. The notebook holding it was owned by the student's
  personal account and open to anyone with the link. The operator had it restricted, and kept the
  photo ("quizás tenga otros datos").
- Q: Who checks a transcription? → A: Nobody by hand: a doubtful reading is settled by agreement
  with another source, the topic's own first, and the source is written beside it (spec 002,
  clarification of 2026-10-29).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A photo of the notes reaches the notebook with no one at a computer (Priority: P1)

The student photographs a page of his notes and uploads it to the topic's `notes/` folder in his
Drive. Without anyone starting anything, and with the Mac off, alfabeta transcribes it literally,
leaves the transcription next to the photo as a PDF (the photo, then its text) and its Markdown, and
adds the page to the topic's living notes file. While the family's Mac is awake with the family's
session logged in, the notebook holds that page within about twenty minutes, with nobody at the Mac;
with the Mac asleep, off or logged out, it holds it shortly after the Mac wakes or the family's
session starts.

**Why this priority**: the notes are the most trusted source (spec 002) and the one that needed a
person at a keyboard on 2026-10-26.

**Independent Test**: with the Mac off, upload two invented photos of handwritten notes to a test
topic's `notes/` from a phone; after the next cloud run, switch the Mac on and, without touching
the notebook as its owner, ask its chat as the student about a word only one of the pages holds.

**Acceptance Scenarios**:

1. **Given** a photo uploaded to `notes/` from the phone with the Mac off, **When** the next cloud
   run happens, **Then** its transcription is in the same folder and its page is in the living notes
   file, after the pages already there.
2. **Given** that run and the Mac awake, **When** the Mac's next refresh reads the changed source as
   the owner, **Then** within three minutes the notebook's copy of the living file holds the page and
   the student's view answers about it, and no source was added.
3. **Given** two photos with the same content (the same file uploaded twice), **When** the run
   happens, **Then** the page is transcribed and added once and the duplicate is reported.
4. **Given** a page that cannot be read in places, **When** it is transcribed, **Then** those places
   are marked as unreadable or doubtful, never guessed.
5. **Given** any page in the living file, **When** the student or the tutor chat reads it, **Then**
   the page says it is an automatic transcription and whether the student has checked it.
6. **Given** the Mac asleep, off or logged out when a living file changes, **When** it wakes or the
   family's session starts, **Then** one refresh runs and the notebook takes the page; nobody has to
   open anything.

---

### User Story 2 - The student corrects a transcription when he finds an error (Priority: P2)

Checking is optional. If the student finds an error, he marks that transcription from his phone. The
family is told, and a corrected transcription replaces the page in the living file. A correction is
either a new photo of the page, named like the first one with « (corregida)» before the extension,
uploaded by the student from his phone, or the family editing the transcription's Markdown in Drive.

**Why this priority**: transcriptions are taken as good; this is the way back when one is not.

**Independent Test**: mark one transcription of a test topic; check that the family is told and
that, once corrected, the living file holds the corrected page only once.

**Acceptance Scenarios**:

1. **Given** a transcription the student marks as wrong, **When** the run happens, **Then** the page
   in the living file says it is under correction and the family is told which topic and page.
2. **Given** a photo named like an earlier one plus « (corregida)», or an edit of a transcription's
   Markdown, **When** the run happens, **Then** the corrected transcription replaces the page in
   place, and the page no longer says it is under correction.
3. **Given** a transcription the student marks as checked, **When** the run happens, **Then** the
   page in the living file says it was checked by the student.

---

### User Story 3 - New Classroom material reaches the notebook with no one at a computer (Priority: P2)

When classroom-sync has put a new Classroom item of a topic into Drive, the next cloud run adds it
to that topic's living Classroom file, `Classroom · <topic>.pdf`: a cover page with the item's
title and posting date, then the item's own pages and images. An item is what spec 001 places: a
single file `YYYYMMDD - <title>.<ext>`, a text note `.md`, or a folder `YYYYMMDD - <title>/` with
its files, `descripcion.md` and `enlaces.md`.

**Why this priority**: the teacher's material ranks second (spec 002), and without this the
notebook only learns of it when someone runs the study pack.

**Independent Test**: put one invented Classroom item into a test topic's `classroom/` folder in
Drive; after the next run and the Mac's next refresh, ask the notebook as the student about a fact
only that item holds; run again and check that nothing changed.

**Acceptance Scenarios**:

1. **Given** a new Classroom item in a topic's `classroom/` folder in Drive, **When** the next cloud
   run happens, **Then** the living Classroom file holds its cover page and pages, and no source was
   added.
2. **Given** a second run with nothing new, **When** it ends, **Then** the living file is unchanged.
3. **Given** an item with only links (a folder with `descripcion.md` and `enlaces.md`), **When** it
   is added, **Then** its cover page carries its title, date, description and addresses, and the
   report says it holds no other pages.
4. **Given** an item folder with a PDF, a Word file and `descripcion.md`, **When** it is added,
   **Then** it is one entry: one cover page, the description, then each file's pages.
5. **Given** an item edited by the teacher, **When** classroom-sync brings the new version, **Then**
   its pages in the living file are replaced in place, not added again.
6. **Given** an assignment folder with `enunciado - <name>`, a `submission/` subfolder and `correccion.md`,
   **When** it is added, **Then** only the statement's pages enter the living file; the student's
   work and its grading do not.

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

1. **Given** a run that changed nothing, **When** it ends, **Then** no report is written.
2. **Given** a run that added material the topic's study guide does not cover, **When** it ends,
   **Then** the report names what is missing and says that regenerating spends quota and is the
   family's decision.
3. **Given** a failure that repeats on every run (a photo Claude keeps refusing, a spent budget),
   **When** the runs go on, **Then** it is reported once, when it starts, and once when it clears.

---

### User Story 5 - A topic's notebook gets its living files once (Priority: P3)

When a topic's notebook is created, its two living files are created with it, empty but for a cover
page, and added to the notebook as Drive sources. That is the only step that changes a notebook's
sources; the other use of the notebook tool on the Mac only reads them (FR-018).

**Why this priority**: it happens once per topic and can be done by hand until it is automated.

**Independent Test**: create a test topic; check that the notebook has exactly one living notes
source and one living Classroom source, and that a second run adds nothing.

**Acceptance Scenarios**:

1. **Given** a topic with a notebook and no living sources, **When** the setup runs on the Mac,
   **Then** both living files exist, in the topic's `notes/` and `classroom/`, and are sources of the
   notebook.
2. **Given** a topic whose notebook already holds notes or Classroom material as plain file sources
   (Tema 01 of 2026-2027 holds its notes that way since 2026-10-26), **When** the living files are
   set up, **Then** that material is moved into them, the plain sources are listed for the family to
   remove, and nothing is removed by alfabeta.
3. **Given** the cloud run finds a topic with no living sources, **When** it ends, **Then** its
   photos are transcribed and recorded, no living file is created, and the report says the topic
   waits for the setup on the Mac. The setup builds both files from what was recorded.
4. **Given** a topic whose `notes/` already holds a Markdown that embeds a photo by name (Tema 01
   since 2026-10-26), **When** the topic is first seen, **Then** that Markdown's section is taken as
   the photo's transcription and Claude is not called for it.

---

### Edge Cases

- **A living file is trashed, moved or deleted in Drive.** Google's announcement says the notebook
  then drops the source (not measured for a trash, a deletion or a move out of the student's Drive;
  a move between two folders of the topic kept it, next edge case). alfabeta never deletes or moves it; each run checks that
  each recorded living file is still in its own folder of the topic (`notes/` for the notes file,
  `classroom/` for the Classroom file) and not trashed, and if not, reports it and does not
  recreate a second file or source. Put back in its folder, it is healthy again on the next check,
  and a page transcribed meanwhile reaches it on that pass.
- **A living file set up at the topic's root, before 2026-10-28.** Moved by hand once into its
  folder (julioarguello/alfabeta#110); until then it is reported missing. Tema 01's two, moved in
  the Drive for desktop mount, kept their ids, which the notebook sources are bound to, and the
  notebook kept reading both (measured once, 2026-10-28, research).
- **The Mac is asleep, off or logged out.** The notebook's copy of a living file stays old until the
  Mac's next refresh after it wakes or the family's session starts, and the student may meet the old
  copy meanwhile: opening the notebook as the student does not refresh it (measured 2026-10-28). The
  operator accepted this condition (Clarifications, session 2026-10-28).
- **The owner's `nlm` session stops working.** The refresh tries to renew it (research R14); if the
  session still does not work, it stops, the family is told once on the Mac (FR-019), and the owner
  signs in again with `nlm login`. Nothing else stops: Drive keeps receiving pages.
- **A photo is put outside `notes/`**, or in the school Drive: it is not transcribed. At the topic
  folder's root or deeper in `notes/` it is reported as an unexpected file; in `notebook/`, `exam/`
  or `sciencebits/` it is not read; in the school Drive it cannot be seen.
- **A photo in a format the transcription does not take** (anything but JPEG, PNG or WebP, such as
  HEIC, or a scanned PDF), or over 10 MB: it is reported as not supported, with what to upload
  instead, and is not retried until it changes.
- **A photo is rotated, blurred or not of notes.** It is transcribed with its doubtful parts marked,
  or reported as not readable and left out of the living file.
- **A photo is deleted after its page reached the living file.** The page stays; the family is told
  (constitution V).
- **The AI budget is spent** for the month: transcription and the "what it adds" report wait,
  everything else continues, and the family is told once.
- **A living file passes the configured page count**: reported before any notebook limit is
  reached; splitting a living file is a decision for the family.
- **Two topics share a name** (each subject has its own `No topic`): topics are told apart by their
  folder, never by name alone.
- **The cloud run cannot reach Drive or keeps failing** (its link revoked, spec 004): it writes
  nothing, and the family learns it on a channel that does not need that link (FR-017).

## Requirements *(mandatory)*

### Functional Requirements

**Detecting what arrives**

- **FR-001**: alfabeta MUST learn of every file added, changed, renamed or removed under the
  alfabeta folder in the student's Drive, whatever wrote it (phone, web, Drive for desktop,
  classroom-sync), from Drive's own record of changes, keeping its position in that record between
  runs so nothing is missed or read twice. Changes outside the alfabeta folder are dropped before
  anything else happens and nothing about them is kept or logged (spec 004 FR-009a, as amended),
  except the fact that a recorded file left the folder or was removed. A change to a file alfabeta
  itself wrote (its records, run log, transcriptions, living files, reports, temporary conversions)
  is never an arrival, with two exceptions that are the family's: a new name of a transcription PDF
  (a mark, FR-008) and a new checksum of a transcription Markdown (a correction).
- **FR-002**: Whatever Drive holds under a topic folder MUST reach the master, the family's files and
  the cloud run's alike (constitution VII, 1.6.0). This spec depends on spec 004's FR-011a, added in
  this pull request, which owns that pull and its rule.
- **FR-003**: Each file MUST have one record: its Drive id, checksum (or modification time for a
  Google-native file), kind, topic folder, and state. Two runs with no change MUST write nothing
  but the run's own log, which also holds the change cursor (constitution V).
- **FR-004**: The first run, and the first sight of a topic, MUST take in what the topic folder
  already holds, not only what changes afterwards; so must a folder that joins the alfabeta folder
  with content in it. A Markdown in `notes/` that embeds a photo by name is taken as that photo's
  transcription, with no call to Claude.

**Transcribing the notes**

- **FR-005**: Every JPEG, PNG or WebP image in a topic's `notes/` MUST be transcribed literally,
  keeping spelling and language, with the conventions the notes of 2026-10-26 used: text written
  between lines, crossed out text, doubtful readings, unreadable parts, drawings described, boxed
  text. The result is a PDF (the photo, then its text) and its Markdown next to the photo, named
  `<photo name> · transcripción.pdf` and `.md`; an adopted transcription gets its PDF the same way.
  Other formats are reported as not supported.
- **FR-006**: An image with the same checksum as one already transcribed MUST NOT be transcribed
  again; it is reported as a duplicate. A transcription that fails is retried at most three times,
  then reported and left until the photo changes.
- **FR-007**: A transcription MUST reach the notebook without anyone checking it. Every page says it
  is an automatic transcription, and whether the student checked it or marked it as wrong.
- **FR-008**: The student MUST be able to mark a transcription as checked (« (revisada)») or as
  wrong (« (mal)») by renaming its PDF in Drive from his phone. A page marked wrong stays in the
  living file, labelled as under correction, until a correction (User Story 2) replaces it; then
  alfabeta writes the corrected PDF under its name without the mark.

**Reaching the notebook**

- **FR-009**: Each topic MUST have two living files in Drive, `Apuntes · <topic>.pdf` in its
  `notes/` and `Classroom · <topic>.pdf` in its `classroom/`, where `<topic>` is the topic folder's
  name after its date; neither sits at the topic folder's root (constitution 2.2.0), and the setup
  makes the folder when the topic has none yet. Only the setup on the Mac creates them, shares each
  read-only with the account in `[notebook] owner` (the one
  that owns the notebooks) and with no other, and adds each, once, to the topic's notebook as a
  Drive source. Material that arrives later goes into them; no other source is added for it.
- **FR-010**: Notes pages go into the living notes file in the order they were first seen. Each
  Classroom item, whether a file, a note or a folder (User Story 3), goes into the living Classroom
  file as one entry: a cover page (title, posting date, description and addresses from
  `descripcion.md` and `enlaces.md`), then the pages of each of its files: entries in posting
  order, files in name order. A PDF is copied page by page; a Google-native or Office file is
  converted to PDF through Drive; a Markdown note is set as text; an image is one page; anything
  else is named on the cover page. The student's own work and its grading (spec 001's roles
  `submission` and `grading`: everything in a `submission/` subfolder or a legacy `entrega/` one,
  and every file whose name starts with `entrega - ` or `correccion`, whatever follows) are never
  put into a living file (constitution III). A previous version spec 001
  keeps beside an edited one (`<name> (anterior YYYY-MM-DD)`) is never put in either: the current
  version replaces the old pages in place. An announcement note (`aviso`) is not material and is left
  out. A material in `No topic` goes into the living Classroom file of its subject's most recent
  topic, the topic folder whose date is latest when the material is first seen, and stays there
  (spec 002 FR-023). An item moved to another topic leaves the first living file and enters the
  second.
- **FR-011**: alfabeta MUST NOT delete, rename or move a living file, nor remove a source from a
  notebook. A living file that is missing, trashed or outside its own folder of the topic
  (`notes/` or `classroom/`) is reported and is not recreated.
- **FR-012**: Adding material MUST NOT regenerate any study piece. The run reports what the new
  material adds against the topic's study guide (User Story 4).
- **FR-018**: After a living file changes, the notebook owner's account MUST read that file's
  notebook source, through `nlm` on the family's Mac, on the pass that sees the change and again on
  the next pass, so the notebook takes the new revision (whether one read is enough is open,
  research R14);
  the student's own access does not (measured 2026-10-28). A launchd agent of the Mac runs this
  refresh every `[notebook] refresh_minutes`, once on wake and once when the user's session starts,
  with no app open and no one at the Mac. A refresh compares each living file's last built checksum, which the cloud run records, with
  the checksum the owner last read, and reads only the sources that differ or await their confirming
  read: with nothing changed it reads one record, lists no Drive folder and touches no notebook. It never adds, removes or renames a source (FR-011).
- **FR-019**: When the owner's `nlm` session does not work, even after renewing it once with
  `nlm auth refresh --http-only` (research R14; the unattended pass never renews through a browser,
  which only `notebook refresh --browser`, started by the family, does), the
  refresh MUST stop and tell the family on the Mac: a macOS notification when the session turns
  failing, given again only after it has worked in between, and an agenda line from the Mac's sync
  while it stays failing. Drive keeps receiving pages meanwhile.

**Reporting**

- **FR-013**: A run that changed something MUST report, in Spanish, per topic: pages and items that
  reached the living file, transcriptions marked by the student, duplicates, unsupported or unreadable
  photos, removed files, unexpected files, topics waiting for setup, living files over the page
  count, and failures. A repeating failure is reported when it starts and when it clears, not on
  every run. Logs carry opaque indexes and counts, never a name, a Drive id or a path
  (constitution III).

**Where it runs and what it may spend**

- **FR-014**: Detection, transcription, updating the living files and the report (FR-001, FR-003 to
  FR-008, FR-010 to FR-013) MUST run in the cloud, in the operator's Google Cloud project for
  alfabeta, on a schedule that does not depend on the family's Mac; the same pass can also be run on
  the Mac by hand. The pull into the master (FR-002), Classroom capture (spec 001), creating the
  living files and their sources (FR-009, User Story 5) and the owner's refresh (FR-018) stay on the
  Mac. Constitution IX is amended in the same pull request.
- **FR-015**: The AI that transcribes and writes the "what it adds" report MUST be paid from the
  operator's Claude plan API credit, in the alfabeta workspace and under its monthly spend limit.
  When the limit is reached, those two steps wait and the family is told once; nothing else stops.
- **FR-016**: Photos and transcriptions MUST go only to the services the family configured: the
  student's Drive, the notebook owner's notebook, the operator's Google Cloud project for alfabeta,
  and Claude through the alfabeta workspace (constitution III, 1.6.0). No model whose terms exclude
  minors is used, and the student never interacts with the model directly.
- **FR-016a**: Before a photo is transcribed, alfabeta MUST decide whether it is a page of notes. A
  photo that is not (a credential, a document, a person) is never transcribed, never added to a
  notebook and never shared; the family is told which file it is, without its content, and
  alfabeta never deletes it (2026-10-29: a printed access PIN among six photos). If it sits in a
  topic folder of Drive, the copy constitution VII makes to the master and the mirrors is the only
  one, and the report says so, so the family can move it out.
- **FR-016b**: When the notes come from a notebook the family points at, alfabeta MUST read its
  sharing first and report, before anything else, a notebook open by link that holds the student's
  notes or a non-note photo; the sharing is changed only on the family's word, by the family or
  with the family signed in as the owner, and alfabeta checks the result from an account that is not a collaborator (2026-10-29: the
  outside account answered `PERMISSION_DENIED` after the change).
- **FR-016c**: Every doubtful reading of a transcription MUST be settled by agreement with another
  source — the topic's textbook in the subject's language and in Spanish, the notes' other pages,
  Classroom, then an external reference — with that source beside the settled word; a word no
  source settles stays marked with the sources tried. There is no human reviewer.
- **FR-017**: The cloud run MUST hold its own Google link, made with an OAuth client of its own, and
  its own Claude key in that project's secret store, readable only by the run's service account,
  never in the repository, the configuration, a log or an error message. The Mac keeps its own
  client, token and key; nothing is copied between them (constitution II, 1.6.0). Its failures MUST reach the family without that link: the
  project alerts the operator when a run fails, and the Mac's sync warns in the agenda when the
  cloud's last successful run, which every run records as its own log, is older than
  `[notes] cloud_stale_hours`. A run started by hand on the Mac does not count as the cloud's.

### Key Entities

- **Arrival**: a file seen in Drive's record of changes: its Drive id, topic folder, kind and
  checksum.
- **Notes page**: one photo and its literal transcription, with its state: automatic, checked by
  the student, or marked wrong.
- **Living file**: one notes file and one Classroom file per topic, each a PDF in its own folder
  of the topic (`notes/` or `classroom/`), with its Drive id and the notebook source it is bound to.
- **Classroom entry**: a Classroom item (a file, a note or a folder) as the living Classroom file
  holds it: its cover page, its pages, and the Drive files it came from.
- **Change cursor**: the position in Drive's record of changes the last cloud run reached, and when.
- **Run report**: what changed per topic, in Spanish, plus failures.
- **Refresh record**: on the Mac only, per notebook source, the living file checksum the owner last
  read, and whether the owner's `nlm` session worked on the last refresh.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A photo uploaded from the phone with the Mac off is in the topic's living notes file
  within one hour, on every attempt over two weeks of real use.
- **SC-002**: After that, with the Mac awake and nobody touching the notebook as its owner, the
  student's view of the notebook answers a question only that page can answer within 20 minutes of
  the page reaching the living file: one refresh interval at the template's `refresh_minutes = 15`,
  plus the owner's read and the notebook taking the page, under three minutes on 2026-10-28, plus
  margin. With the Mac asleep, off or logged out, within 20 minutes of it waking or of the family's
  session starting.
- **SC-003**: A Classroom item that classroom-sync put into Drive is in the living Classroom file
  within one hour of the upload.
- **SC-004**: Two consecutive runs with nothing new write nothing to Drive, the master folder or any
  notebook, apart from the run's own log.
- **SC-005**: Over a school term, no notebook gains a source other than its two living files and the
  sources the study pack (spec 002) adds by hand.
- **SC-006**: Over 30 runs, each Classroom item and each notes page appears in its living file
  exactly once.
- **SC-007**: The month's spend on AI stays under the workspace limit, and the report states what it
  was.
- **SC-008**: A search of the logs, the run log and the repository for the student's name or address
  finds nothing, and every report passes the guardrail's detectors before it is written.

## Assumptions

- The student uploads photos to the topic's `notes/` folder in the Drive of his personal Gmail,
  the master. The school Drive is a mirror and is never read (constitution VII).
- The notebook owner's account needs read access to each living file, and to nothing else (FR-009),
  as on 2026-10-27; never the whole folder with the student's work and grades. Whether the
  notebook's viewers also need it was not measured; quickstart step 3 checks. On 2026-10-28 the
  student, a viewer who owns the files in Drive, saw a refreshed page; other viewers were not
  measured.
- A Drive-backed PDF keeps refreshing the way it did on 2026-10-27 and 2026-10-28: when the owner
  reads it. If Google changes it, the living files fall back to being refreshed as sources by the
  Mac run.
- The family's Mac is awake for part of each day, with the family's user session logged in, since a
  launchd agent of that user runs only inside it; while the Mac sleeps or nobody is logged in, the
  notebook waits (the operator's choice, Clarifications, session 2026-10-28).
- The owner's `nlm` session on the Mac keeps working for weeks, renewed by `nlm auth refresh` when
  it fails (two days measured on 2026-10-28). Quickstart step 8 counts renewals and FR-019's
  notices.
- The transcription quality of the API model is at least that of the transcription of 2026-10-26,
  which the operator checked against the photos. Measured in the plan, on those photos.
- At about 4 to 8 pages per topic and two subjects, transcription spends 1 to 3 USD a month,
  estimated from the published image-token formula and model prices, not measured.
- The cloud run stays within the project's free tier; a billing account is still required to use it.

## Dependencies

- Spec 004 (julioarguello/alfabeta#30): Drive access as the student, the folder allowlist, and the
  move of the master folder out of the Drive for desktop mount. This pull request amends its FR-007
  (the cloud's own link and secrets), FR-009a (the change feed) and the edge case on refresh tokens,
  and adds FR-011a (the pull into the master), which must ship before that move.
- Spec 001: classroom-sync, which puts each Classroom item into the topic's `classroom/` folder in
  Drive.
- Spec 002: the study pack, which ranks the notes first and owns regeneration. Its User Story 6 and
  FR-004 required a checked transcription; this spec supersedes that (Clarifications).
- The operator: a billing account on
  the operator's Google Cloud project for alfabeta, a second OAuth client there for the cloud run,
  and two API keys in the alfabeta Console workspace, one for the Mac and one for the cloud (the
  workspace was created 2026-10-27, with no key yet).
- Spec 001: this pull request amends its FR-011b and its assumption that alfabeta manages no Drive
  permissions, so that the living files' one share (FR-009) is named there too.
