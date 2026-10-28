# Data model: Class notes and new material reach the topic's notebook by themselves

The cloud run's records live in one file, `.alfabeta/state.json`, at the root of the alfabeta
folder in the student's Drive (research R4; constitution II, 1.6.0). Its own log, which also holds
the change cursor, is `.alfabeta/last-run.json` (research R2, R13). The pull into the master
and its cursor belong to spec 004 (FR-011a). Ids are Drive file ids and notebook source ids: data,
never in the repository or a log. Logs carry opaque indexes and counts, never a name, an id or a
path.

## RunLog (`.alfabeta/last-run.json`)

Written at the end of every run: the run's own log (constitution V), the one write an idle run makes.

| Field | Meaning |
|---|---|
| `started`, `ended`, `result`, `ran_on` | This run; `result` is `ok`, `partial` or `failed`; `ran_on` is `cloud` or `mac` |
| `last_ok_ended` | `ended` of the last `ok` or `partial` run with `ran_on = cloud`, kept across failed runs and Mac runs; the Mac reads it (FR-017) |
| `page_token` | The change cursor: `newStartPageToken` of the last run whose writes all succeeded; a failed run keeps the previous one, so the next run reads the same changes again. Absent means first run (research R2's listing) |

`state.json` is written only when a record changes (SC-004).

## Topic

Keyed by the topic folder's Drive id, never by name (two subjects each have a `Sin tema`). Holds
the folder's name after its date, `<topic>`, used in living file names.

## Arrival

One per Drive file seen under a topic folder, keyed by Drive id.

| Field | Meaning |
|---|---|
| `file_id` | Drive id |
| `topic` | Topic folder id |
| `kind` | `notes_photo` (an image in `apuntes/`), `notes_transcript` (a transcription PDF in `apuntes/`), `notes_text` (a transcription Markdown in `apuntes/`, alfabeta's or adopted), `classroom_item` (a file, note or folder in `classroom/`), `living_file`, `unexpected` |
| `own` | true for every file alfabeta wrote (transcriptions, living files, state, run log, reports, temporary conversions): a change to it is consumed, never an arrival (research R2), except a new name of a `notes_transcript` (a mark) and a checksum of a `notes_text` that differs from the one alfabeta recorded (a correction) |
| `for` | `properties.alfabeta_for` of an own file: the photo or item it was made from; a run looks it up before creating (research R4) |
| `version` | Drive's `md5Checksum`, or `modifiedTime` for a Google-native file; "a new version" means either changed |
| `state` | See below |

**States of a notes photo**: `seen` → `transcribed` → `in_living_file`; or `duplicate` (same
`version` as another photo), `unsupported` (not JPEG, PNG or WebP, or over 10 MB), `unreadable` (the
transcription says nothing is legible), `failed` (retried on the next three runs, then
`failed_final` until the photo changes), `budget_wait` (retried on the first run of each day), `gone`
(removed or trashed in Drive; its page stays, constitution V).

**States of a Classroom item**: `seen` → `in_living_file`; or `failed`, `gone`.

A state change is reported once; a state that persists is not reported again (FR-013).

## NotesPage

One per transcribed photo.

| Field | Meaning |
|---|---|
| `photo_id`, `photo_version` | The photo it transcribes |
| `pdf_id`, `markdown_id`, `markdown_version` | `<photo name> · transcripción.pdf` and `.md` next to the photo; for an adopted Markdown, its section, and a PDF written for it |
| `order` | Position in the living file: the order pages were first seen; a correction keeps it |
| `review` | `automatic`, `checked` (PDF renamed with « (revisada)»), `wrong` (« (mal)») |
| `source` | `claude` or `adopted` (an existing Markdown, research R2) |
| `model`, `usage` | The model and its token counts, for the report; empty when adopted |

A correction (research R7) keeps the page's `order`: a photo named like `photo_id`'s plus
« (corregida)» replaces `photo_id` and its transcription; a new `markdown_version` re-renders the
page from the Markdown. Either sets `review` back to `automatic`.

## LivingFile

Two per topic.

| Field | Meaning |
|---|---|
| `topic` | Topic folder id |
| `kind` | `notes` (`Apuntes · <topic>.pdf`) or `classroom` (`Classroom · <topic>.pdf`) |
| `file_id` | Drive id; set only by `notebook setup`, never changes once set |
| `source_id` | The notebook source bound to it, set by `notebook setup` |
| `built_md5` | Checksum of the last uploaded revision; a rebuild with the same checksum is not uploaded |
| `pages` | Page count of the last build, reported above `[notes] warn_pages` |
| `health` | `ok`, or `missing` (deleted, trashed or moved out of its topic folder): reported, never recreated |

A topic with no `file_id` is `waiting_setup`: its photos are transcribed and recorded, no living
file is created, and the report says so.

## RefreshRecord (on the Mac: `notebook-refresh.json` in the student's data folder)

Written only by `notebook refresh` (FR-018), only when a field changes; never in Drive, the
repository or a log (research R14).

| Field | Meaning |
|---|---|
| per `source_id` | `read_md5`: the living file's `built_md5` when the owner last read that source; `read_at`: when |
| `session` | `ok` or `signed_out`: whether the owner's `nlm` session worked on the last pass, after at most one `nlm auth refresh` |
| `session_since` | When `session` took its value; the notice of FR-019 goes out when it turns `signed_out`, never on a pass that finds it already so |

A source with no `read_md5` is read on the next pass. A source whose living file is `missing` is
not read; FR-011's report covers it.

## ClassroomEntry

One per Classroom item, keyed by the item: the Drive id of its file, note or folder. A material in
`Sin tema` belongs to the living Classroom file of its subject's most recent topic, the topic folder
with the latest date when the material is first seen, and stays there (spec 002 FR-023); an
announcement (`aviso`) is not an entry. An item moved to another topic folder moves to that topic's
file.

| Field | Meaning |
|---|---|
| `item_id`, `item_version` | The item; for a folder, the latest `version` of anything inside |
| `title`, `posted` | From the item's name, `YYYYMMDD - <title>` (constitution, Storage) |
| `description`, `addresses` | From `descripcion.md` and `enlaces.md`, when the item is a folder |
| `parts` | Each file inside, in name order, with how it is rendered: `pdf`, `export` (Google-native), `office` (copied to the Google type in `.alfabeta/conversions/`, exported, the copy trashed), `text` (Markdown), `image`, `named` (only on the cover). Never parts: any file whose name starts with `entrega - ` or `correccion`, whatever follows (spec 001's `submission` and `grading`, constitution III), and any `<name> (anterior YYYY-MM-DD)` (a previous version, replaced by the current one) |
| `pages` | Pages in the living file |

A new `item_version` replaces the entry's pages in place.

## RunReport

Written only when the run changed something (User Story 4).

| Field | Meaning |
|---|---|
| `run_at` | Start of the run, `Europe/Madrid` |
| per topic | State changes since the last report: pages added, items added, duplicates, unsupported, unreadable, gone, marks by the student, unexpected files, `waiting_setup`, living files `missing` or over the page count, failures, and the "what it adds" text |
| `spend` | Tokens in and out this run, and the month's spend so far from the spend ledger |

The report is in Spanish, in Drive.

## SpendLedger (in `state.json`)

One row per month: tokens in and out of every Claude call, transcriptions and "what it adds" alike,
and their cost at `[notes] price_in` and `price_out`. The Console's cost page is the authority;
reading it needs an admin key this plan does not ask for.
