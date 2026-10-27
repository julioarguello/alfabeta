# Data model: Class notes and new material reach the topic's notebook by themselves

Everything here lives in one file, `.alfabeta/estado.json`, at the root of the alfabeta folder in
the student's Drive (research R4), except the Mac's own cursor (`PullCursor`). Ids are Drive file
ids and notebook source ids: data, never in the repository or a log (constitution II, III).

## ChangeCursor

| Field | Meaning |
|---|---|
| `page_token` | `newStartPageToken` of the last run whose writes all succeeded |
| `saved_at` | When it was saved |

Saved last in a run. A run that fails before the end leaves it unchanged, and the next run reads the
same changes again.

## Arrival

One per Drive file seen under a topic folder, keyed by Drive id.

| Field | Meaning |
|---|---|
| `file_id` | Drive id |
| `topic` | Topic folder, by the part of its name after the date (constitution, Storage) |
| `kind` | `notes_photo` (an image in `apuntes/`), `notes_text` (a Markdown alfabeta wrote in `apuntes/`), `classroom_item` (anything in `classroom/`), `living_file`, `unexpected` |
| `md5` | Drive's checksum; absent for Google-native files, which use `modified_time` |
| `origin` | `alfabeta` when the file carries `appProperties.origin = "alfabeta"`, else `family` |
| `state` | See below |

**States of a notes photo**: `seen` → `transcribed` → `in_living_file`, or `duplicate` (same `md5`
as another photo) or `unreadable` (the transcription says nothing is legible) or `failed`
(transcription refused or errored; retried next run). `budget_wait` when the month's credit is spent.

**States of a Classroom item**: `seen` → `in_living_file`, or `failed`.

## NotesPage

One per transcribed photo.

| Field | Meaning |
|---|---|
| `photo_id`, `photo_md5` | The photo it transcribes |
| `pdf_id`, `markdown_id` | The transcription files next to the photo |
| `order` | Position in the living file: by the photo's name, then by upload time |
| `review` | `automatic`, `checked` (PDF renamed with « (revisada)»), `wrong` (« (mal)») |
| `model`, `usage` | The model that transcribed it and its token counts, for the report |

A corrected transcription replaces `pdf_id`/`markdown_id` and sets `review` to `automatic`.

## LivingFile

Two per topic.

| Field | Meaning |
|---|---|
| `topic` | Topic folder |
| `kind` | `notes` (`Apuntes · Tema NN.pdf`) or `classroom` (`Classroom · Tema NN.pdf`) |
| `file_id` | Drive id; never changes once set |
| `source_id` | The notebook source bound to it, set by `notebook setup` |
| `built_md5` | Checksum of the last uploaded revision; a rebuild with the same checksum is not uploaded |
| `pages` | Page count of the last build, reported above 100 (research R12) |

A topic with no `source_id` is `waiting_setup` (User Story 5, scenario 3): its arrivals are recorded
and transcribed, and its living files are built, but the report says the notebook will not see them
until setup.

## ClassroomEntry

One per Classroom item in a living Classroom file.

| Field | Meaning |
|---|---|
| `file_id`, `md5` | The item's file in `classroom/` |
| `title`, `posted` | From the item's file name, `YYYYMMDD - <title>` (constitution, Storage) |
| `address` | The item's link, for items with no pages, from the sidecar classroom-sync writes |
| `pages` | Pages copied into the living file; 0 for a link or a video |

A new `md5` for the same `file_id` replaces the item's pages in place (User Story 3, scenario 4).

## RunReport

Written only when the run changed something (User Story 4).

| Field | Meaning |
|---|---|
| `run_at` | Start of the run, `Europe/Madrid` |
| per topic | Pages added, items added, duplicates, unreadable photos, marks by the student, unexpected files, `waiting_setup`, failures, and the "what it adds" text |
| `spend` | Tokens in and out this run, and the month's spend so far, summed from the `usage` recorded in `estado.json` at the model's published price (the Console's own cost page is the authority; reading it needs an admin key this plan does not ask for) |

Logs carry topic folders and counts. The report is the family's; it is in Spanish and in Drive.

## PullCursor (on the Mac)

`data/drive/pull.json` in the student's data folder: the Mac's own `page_token` for the pull
(research R10). Independent of the cloud's cursor.
