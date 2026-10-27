# Data model: Class notes and new material reach the topic's notebook by themselves

The cloud run's records live in one file, `.alfabeta/estado.json`, at the root of the alfabeta
folder in the student's Drive (research R4; constitution II, 1.6.0). Its own log is
`.alfabeta/ultima-ejecucion.json` (research R13). The Mac's pull cursor lives in the Mac's data
folder. Ids are Drive file ids and notebook source ids: data, never in the repository or a log.

## ChangeCursor

| Field | Meaning |
|---|---|
| `page_token` | `newStartPageToken` of the last run whose writes all succeeded |
| `saved_at` | When it was saved |

Saved last, and only when the token moved or the run wrote something (SC-004). A run that fails
before the end leaves it unchanged, and the next run reads the same changes again. No cursor means
first run: research R2's listing.

## RunLog (`.alfabeta/ultima-ejecucion.json`)

`started`, `ended`, `result` (`ok`, `partial`, `failed`), written at the end of every run. The Mac
reads `ended` of the last `ok` or `partial` run (FR-017).

## Topic

Keyed by the topic folder's Drive id, never by name (two subjects each have a `Sin tema`). Holds
the folder's name after its date, `<topic>`, used in living file names.

## Arrival

One per Drive file seen under a topic folder, keyed by Drive id.

| Field | Meaning |
|---|---|
| `file_id` | Drive id |
| `topic` | Topic folder id |
| `kind` | `notes_photo` (an image in `apuntes/`), `notes_transcript` (a transcription PDF alfabeta wrote in `apuntes/`), `notes_text` (a transcription Markdown in `apuntes/`, alfabeta's or adopted), `classroom_item` (a file, note or folder in `classroom/`), `living_file`, `unexpected` |
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
| `pdf_id`, `markdown_id`, `markdown_version` | The transcription files next to the photo; for an adopted Markdown, its section |
| `order` | Position in the living file: by the photo's name, then by upload time |
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

## ClassroomEntry

One per Classroom item, keyed by the item: the Drive id of its file, note or folder.

| Field | Meaning |
|---|---|
| `item_id`, `item_version` | The item; for a folder, the latest `version` of anything inside |
| `title`, `posted` | From the item's name, `YYYYMMDD - <title>` (constitution, Storage) |
| `description`, `addresses` | From `descripcion.md` and `enlaces.md`, when the item is a folder |
| `parts` | Each file inside, in name order, with how it is rendered: `pdf`, `export` (Google-native), `office` (copied to the Google type, exported, the copy trashed), `text` (Markdown), `image`, `named` (only on the cover) |
| `pages` | Pages in the living file |

A new `item_version` replaces the entry's pages in place.

## RunReport

Written only when the run changed something (User Story 4).

| Field | Meaning |
|---|---|
| `run_at` | Start of the run, `Europe/Madrid` |
| per topic | State changes since the last report: pages added, items added, duplicates, unsupported, unreadable, gone, marks by the student, unexpected files, `waiting_setup`, living files `missing` or over the page count, failures, and the "what it adds" text |
| `spend` | Tokens in and out this run, and the month's spend so far, summed from the recorded `usage` at `[notes] price_in` and `price_out` (the Console's cost page is the authority; reading it needs an admin key this plan does not ask for) |

Logs carry topic folder ids and counts. The report is in Spanish, in Drive.

## PullCursor (on the Mac)

`data/drive/pull.json` in the student's data folder: the Mac's own `page_token` for the pull
(research R10). Independent of the cloud's cursor.
