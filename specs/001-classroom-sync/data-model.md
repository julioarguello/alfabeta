# Data Model: spec 001

Domain entities (immutable dataclasses in `src/alfabeta/model.py`) and the files where they
persist. Classroom identifiers are opaque: they are stored, in messages they only appear abbreviated and they never
appear in the repository.

## Language of names

Technical names (entities, fields, values, files outside the Drive) are English. What the student
and the family read stays Spanish. Where a technical value becomes a name in the Drive or in
`agenda.md`, this is the name the student sees:

| Technical name | Name the student sees |
|---|---|
| Attachment `role` `statement` | `enunciado - <name>` |
| Attachment `role` `submission` | `submission/<name>`: the file's own name, in the assignment's `submission/` subfolder |
| Attachment `role` `grading` | `correccion.md` |
| Attachment `role` `links` | `enlaces.md` |
| Attachment `role` `description` | `descripcion.md` |
| Attachment `role` `material` | the material file's own name |
| Attachment `role` `announcement` | `YYYYMMDD - aviso - <summary>.md` |
| Agenda `list` `pending` | «Pendiente» |
| Agenda `list` `done` | «Hecho» |
| Agenda `list` `posted` | «Publicado» |
| Agenda `category` `exam` · `assignment` · `quiz` · `material` · `announcement` | «examen» · «entrega» · «cuestionario» · «material» · «aviso» |
| Item `status` `pending` · `turned_in` · `turned_in_late` · `returned` · `overdue` · `missing_per_teacher` | «pendiente» · «entregada» · «entregada tarde» · «devuelta» · «vencida» · «falta según el profesor» |
| Agenda entry `detected: true` | «detectado» |
| Agenda entry `corrected: true` | «corregido» |
| Agenda entry `date: null` | «sin fecha» |
| Attachment not fetched, noted in `enlaces.md` | «no traído» |
| Summary for the family (stderr of `apply`, relayed by Claude) | in Spanish; an unchanged run says «sin cambios» |
| Book topic folder | `YYYYMMDD - Tema NN - <title>` |
| Teacher's topic folder with no book equivalent, or with its match not yet confirmed | `YYYYMMDD - <teacher's title>` |
| Folder for what Classroom posts with no topic | `YYYYMMDD - No topic` |
| Classroom item in `classroom/` | `YYYYMMDD - <title>` |
| Previous version of a replica | `<name> (anterior YYYY-MM-DD)` |

A topic folder's `YYYYMMDD` is the posting date of the first Classroom item placed in it, or the
day a book provider creates it if it comes first. It is set when the folder is created and never
changes: a folder is found by the part of its name after `YYYYMMDD - `, whatever the date.

## Student

Private configuration in `~/.alfabeta/<student>/config.toml` (contract:
[config-template.toml](contracts/config-template.toml)). The fields use the template's names.

| Field | Type | Rule |
|---|---|---|
| `id` | text | Opaque alias the family chooses, never the student's name; lowercase ASCII; name of their folder in `~/.alfabeta/`; passed with `--student` |
| `student.display_name` | text | Claude uses it to address the family in the chat; the `python -m alfabeta` command never prints it, and it never goes to the log, to URLs or to the Drive (SC-009) |
| `student.school_year` | text `YYYY-YYYY` | First level of the structure |
| `student.grade_level` | text | For notebook names (epic 3): it is the `<grade level>` of «`<grade level>. <Subject>. Tema NN - <title>`» |
| `student.languages` | list | Languages that titles and announcements may come in |
| `classroom.account` | email address | Compared locally with the account button; never goes in a URL |
| `storage.base` | path | The student's base folder on the Mac, the master; must exist and stay outside the Google Drive for desktop mount (spec 004 R7); never shown |
| `drive.root` | text | The alfabeta folder's path inside the student's My Drive (spec 004); never the root of «Mi unidad» (My Drive) |
| `drive.mirrors` | list of paths | One-way mirrors of the base folder in the student's other accounts' mounted Drives (FR-011a); may be empty; none may be inside the base folder, contain it, or be the root of «Mi unidad»; never shown |
| `calendar.shared_with` | list of email addresses | Accounts the calendar is shared with, each with permission to see all event details (FR-011b); may be empty; never goes in a URL or the log |
| `downloads.folder` | path | Where Chrome leaves its downloads |
| `sync.full_review_days` | integer ≥ 1 | Every how many days all attachments are downloaded again |
| `sync.lock_idle_minutes` | integer ≥ 1 | After how many minutes without renewal the lock of a dead run is released |
| `sync.kept_captures` | integer ≥ 1 | Captures kept per class |
| `tools.folder` | path | Where the skills copy their working scripts; outside Dropbox and the shared folder |
| `tools.repository` | path | Clone of alfabeta from which the skills run `uv run --project <repository> python -m alfabeta` on the Mac |
| `sciencebits.url` | URL | Science Bits class page |
| `sciencebits.languages` | list | Languages each topic is captured in; the first one gives the folder's title |
| `notebook.enabled` | boolean | Whether each topic's notebook is created |
| `notebook.share_with` | list of email addresses | Accounts each topic notebook is shared with as viewer (FR-011b); may be empty; never goes in a URL or the log |
| `subjects` | list of `Subject` | At least one |
| `schedule.monday` … `schedule.sunday` | time `HH:MM` or empty | Time of the scheduled task on that weekday; empty = no run that day, all empty = on demand only. With `runner.enabled`, the times of the runner's job instead (FR-032) |
| `runner.enabled` | boolean | Whether the unattended runner reads this student's pending work (User Story 7); `false` leaves FR-006 and FR-021a unchanged. A local pointer so the Mac finds the job; the job gets its project and secret names from its environment, not this file. These `[runner]` keys are added to the config contract and the template by T087 when User Story 7 is built; they are not in the template yet, so an existing config is unaffected |
| `runner.route` | `token` · `web` · empty | The route the spike settled (FR-032a, FR-032b); `""` when disabled |
| `runner.session_secret` | text | Base name of the student's vault secrets; the runner derives one entry per purpose (FR-033a: the token or stored session, `-password`, `-totp`, `-drive`); never a value; `""` when disabled |
| `runner.state_folder` | text | Name of the state folder inside the alfabeta Drive folder that holds the single data home (FR-035; constitution II/VII — in Drive, not a separate store, never mirrored); `""` when disabled |
| `runner.page_timeout_seconds` / `runner.run_timeout_seconds` | integer ≥ 1 | Per-page and whole-run time limits (FR-037); the job timeout is set above `run_timeout_seconds` |
| `runner.challenge_cooldown_minutes` | integer ≥ 1 | After a `challenge`, how long before a run reaches Classroom again; the run records a `cooldown_until` in the data home (FR-037) |

## Subject

| Field | Type | Rule |
|---|---|---|
| `folder` | text | Name of the subject's folder (e.g. `FyQ`) |
| `classroom_class` | text | Title of the class in Classroom; only for proposing the link |
| `book` | text or empty | Book provider (`sciencebits`) and name of its subfolder |
| `book_class` | text or empty | Name of the class on the book's platform (e.g. the Science Bits one) |
| `language` | language code | Language the subject is taught and examined in, as in `[student] languages` (spec 002 FR-005) |

`[sciencebits] url` and `languages` accept `""` and `[]` when no subject has `book = "sciencebits"`.

Book topics are not configured: they are the subject's folders whose name contains
`Tema NN - <title>`, whatever their date prefix, that already hold their book's subfolder in the
Drive.

The effective link between a subject and its class is a `Decision` of type `class_link`,
tied to the class id; the title only serves to propose it.

## Source

Protocol in `src/alfabeta/sources.py`: `name` (the subfolder: `classroom` or the value of `book`) and
normalized `items()`. Implementations: `ClassroomSource` (the extractor's captures) and
`BookSource` (directory with the result of a book provider).

## Decision (in `data/decisions.json`)

| Field | Type | Rule |
|---|---|---|
| `type` | `class_link` · `topic_match` · `item_match` · `detected_exam` (Claude's proposal) · `dismissed_candidate` (Claude judges that an exam candidate announces none; origin = the item) · `exam_correction` (from the family) | Claude proposes `item_match` for each item of a teacher's topic that spans several book topics, and it prevails over its topic's decision |
| `origin` | Classroom id (class, topic or item); for `detected_exam` and `exam_correction`, `<item>#exam-<k>`, where Claude assigns `k` = 1, 2… when proposing (the classifier gives a single candidate per item) | Unique key per `(type, origin)` among the non-superseded ones; a repeated proposal does not write |
| `target` | subject, topic folder, exam (`date`, `reason`), correction (`date`, `category`, `discarded`) | |
| `reason` | text | What led to the proposal or to the correction |
| `confidence` | `high` · `medium` · `low` | Only in proposals |
| `state` | `proposed` → `confirmed` · `rejected`; `confirmed` or `rejected` → `superseded` | Only `confirmed` counts, except `detected_exam` (it appears in the agenda as detected) and `dismissed_candidate` (the candidate stops being pending), which count from the moment they are `proposed`; the family can reject a `dismissed_candidate` and the candidate returns to pending. A `(type, origin)` with a non-superseded decision is not proposed again; a `rejected` one, only if its origin shows a modification after the rejection. `detected_exam` is not rejected: it is discarded with an `exam_correction` |
| `date` | date | Of the last transition |
| `origin_hash` | SHA-256 or empty | Of the text a `detected_exam` or a `dismissed_candidate` was deduced from: an announcement's text, or a material's title and description joined by a line break; `plan.json` gives this hash with each `exam_candidate`; if the text changes, the candidate returns to pending and the previous decision becomes `superseded`, unless the family corrected it (`exam_correction`) |

## Classroom item

| Field | Type | Rule |
|---|---|---|
| `id` | Classroom id | From the detail URL; stable |
| `class_id` | Classroom id | |
| `topic_id` | topic id or empty | Empty → `No topic` folder; without a confirmed match → the teacher's topic's own folder |
| `type` | `assignment` · `material` · `question` · `announcement` | |
| `title` | text | As the teacher writes it |
| `posted_at` | date | From «Fecha de creación» (creation date); never from «Última modificación» (last modified) |
| `modified_at` | date or empty | From «Última modificación»; triggers a new download of its attachments |
| `due_at` | date-time or empty | Resolved by `DateResolver` relative to the instant its detail page was read (`seen_at`), or to the capture instant if the page has none (FR-021) |
| `seen_at` | date-time or empty | When its detail page was read; from the capture's `detail.seen_at` |
| `status` | `pending` · `turned_in` · `turned_in_late` · `returned` · `overdue` · `missing_per_teacher` · empty | From the detail (table below); assignments and questions only |
| `description` | text | Instructions or the announcement's text |
| `attachments` | list of `Attachment` | |
| `submission` | list of `Attachment` | Files the student turned in |
| `withdrawn_at` | date or empty | Kept in the state: the first complete capture of its class that no longer showed it; never set for an `announcement` (the stream is read from one page); cleared when a capture shows it again (FR-027). While it is set, the item and the exams detected from it are not in the agenda |
| `grading` | `Grading` or empty | |

### Status from the detail texts

| «Tu trabajo» (your work) text | Detail notice | `status` |
|---|---|---|
| «Asignado» (assigned), «Falta» (missing) or «Sin entregar» (not turned in) and a future due date or no date | — | `pending` |
| «Asignado», «Falta» or «Sin entregar» and a past due date | — | `overdue` |
| «Entregado» (turned in) | — | `turned_in` |
| «Entregado con retraso» (turned in late; its own status since 2026-10-27) | — | `turned_in_late` |
| «Calificado» (graded) or «Devuelto» (returned) | — | `returned` |
| any | «El profesor ha indicado que falta esto» (the teacher marked this as missing) | `missing_per_teacher` (overrides everything above) |
| other text | — | the run records it as unknown and leaves `status` empty |

The "past/future" comparison uses the instant that detail page was read (`seen_at`), or the
capture instant if it has none — the same instant the due date is resolved against (FR-021), so an
item read at 00:01 whose due is «8:00» is not judged overdue against the previous day.

A `todo` capture (the unattended runner, FR-034) updates only `status`, `due_at`, `seen_at` and
`description` of an item, and may create an item it had not seen; it never sets `topic_id`,
`attachments`, `submission` or `grading`, and never withdraws an item except one on its `recheck`
list whose detail says it no longer exists. Topic, attachments and withdrawal from the listing stay
with the full sync. For FR-020c's "a capture of its class later than its date", a `todo` capture
counts as a capture of the item's class (it read that item's detail). The `partial`/`complete` rule
of a `todo` capture is the capture's own `complete` flag, not per class.

## Attachment

| Field | Type | Rule |
|---|---|---|
| `id` | Drive id, YouTube URL or URL | Stable |
| `kind` | `file` · `google_doc` · `video` · `link` · `form` | The last three are not downloaded |
| `name` | text | Name shown |
| `role` | `statement` · `submission` · `material` | |

## Replica (in `data/state.json`)

| Field | Type | Rule |
|---|---|---|
| `source` | source name | `classroom` or the book's |
| `item`, `attachment` | ids | Unique key |
| `role` | `statement` · `submission` · `grading` · `links` · `description` · `material` · `announcement` | Name prefix in assignment folders |
| `path` | path relative to `storage.base` | Computed by `Placer`; name of 255 UTF-8 bytes at most |
| `hash` | SHA-256 | Changes → new version; the previous one becomes `<name> (anterior YYYY-MM-DD)` |
| `version` | integer | Starts at 1 |
| `modified_seen` | date or empty | The item's modification mark when the replica was made |
| `withdrawn_at` | date or empty | The item is no longer in a complete capture of its class; the replica is kept |

Besides the replicas, `state.json` keeps each item's last normalized version (`Item`,
with its due date), which is rewritten only if it changes. Its category is not kept: the
`Classifier` gives it again from the item and the student's languages, so a change of
`[student] languages` reaches every item at once. The `captured_at` of each class's last capture is not
stored in the state: it is read from the most recent one in `data/captures/` (at least one always remains,
`kept_captures` ≥ 1), which is part of the run's own records (FR-025). The agenda
and the rules of FR-020c come from both.

## Grading

`grading_state` (`graded`, `returned`), `grade` (text or empty: only if Classroom shows it to the
student), `max_points`, `teacher_comment`, `returned_at` (from the capture's `returned_text`,
or empty if Classroom does not show it). It describes the return; the assignment's status
is still the one in `Item.status`. It is written as `correccion.md` in the assignment's
folder.

## Agenda entry

Contract: [agenda.schema.json](contracts/agenda.schema.json).

| Field | Type | Rule |
|---|---|---|
| `item` | id | A detected exam is `<item>#exam-<k>`; its origin item keeps its own entry |
| `subject` | text | The subject's folder |
| `list` | `pending` · `done` · `posted` | Per the FR-020c table; material and announcement go to `posted` |
| `date_only` | boolean | `true` if Classroom gives no time |
| `category` | `exam` · `assignment` · `quiz` · `material` · `announcement` | Exactly one; precedence exam > quiz > assignment > material > announcement. An assignment or question is an `exam` when its title names a test in one of the student's languages |
| `title` | text | A detected exam's is its origin's |
| `date` | date-time, date or empty | Empty → at the end of «Pendiente». Due date of an assignment, quiz or exam; posting date of a material or announcement; a detected exam's from its decision, the family's correction prevailing |
| `status` | as in Item, or empty for material and announcement | |
| `detected` | boolean | `true` if the exam comes from a text |
| `origin` | id of the item it was deduced from | Only if `detected` |
| `corrected` | boolean | `true` if the family corrected it |
| `classroom_link` | URL | Without `/u/<n>` (the index is not stable); the readable agenda says to open it with the school account. An announcement, and an exam detected from one, links to its class's stream: no page of a single post was measured |
| `folder` | relative path or empty | The folder all the item's replicas share (what the student turned in counts from its assignment's folder); a detected exam takes its origin's. Empty if the item has no replica |

## Run (in `data/log.jsonl`)

One line per run: `started_at`, `ended_at`, `mode` (`interactive` · `scheduled` · `unattended`, from `lock take --mode`; `unattended` is the runner of User Story 7, with no Claude in the run, so it proposes nothing), the `/u/<n>` index used (`account_index`, from the classes capture),
`classes` visited, counters `added`, `changed`, `withdrawn`, `not_fetched` (with a reason per
item, without student data), `unknown_statuses`, `pending_decisions`, `full_review`
(boolean: the next full review is counted from the last line that has it), `result` (`ok` ·
`partial` · `stopped`) and `reason` (of the stop or of a `partial` one. A stop in the browser —session expired, challenge or unexpected interface— before capturing any class leaves the run `stopped` without writing to the student's folder; after capturing at least one, `apply` applies those already captured, leaves the class of the `stop` capture unapplied and the result is `partial` with that reason. The same in both modes. Drive not mounted, lock busy or invalid configuration always stop before writing) (`session_expired`, `challenge`,
`unexpected_ui`, `timeout`, `drive_not_mounted`, `lock_busy`, `lock_not_held`,
`invalid_config`, `idle`, and, for the unattended runner, `account_blocked` (the API refuses the
account), `drive_write_failed` (the agenda upload was not confirmed) and `store_unavailable` (the
vault or the data home could not be reached)). A runner's line also carries `session_version` (the
number of the stored secret's version it used, never its value; a later run that stops with the
same reason and the same version ends 0 without reaching Classroom and without a new notice, and a
stopped run stores no new version, FR-037) and `blocked` (the count of page loads, presses and
requests the web-route guard blocked, FR-038; absent on the token route). Each line carries the
`run` of its lock. The `apply` line also carries
`mirrors`: `{up_to_date, failed}`, counts of the configured mirrors (FR-011a), never their paths.
`book place` writes a shorter
line: `type: book`, `at`, `run`, `source`, `subject`, `topic`, `result` (`placed` · `unchanged`) and `mirrors`.
Its replicas are keyed `<book>|Tema NN|<file name>`, with `role` `material`.
`log notebook` writes another: `type: notebook`, `at`, `run`, `topic` and `result` (`created` ·
`unchanged` · `failed` · `disabled`), with `reason` if it fails (short text, without student data), and
`shares`: `{invited, already, failed}`, counts of the accounts in `notebook.share_with` (FR-011b),
never their addresses. `unchanged`: the notebook already existed and
no source was missing.

## Transitions

- Decision: `proposed` → `confirmed` | `rejected`; `confirmed` or `rejected` → `superseded`
  when the family changes it. A `detected_exam` or `dismissed_candidate` counts while `proposed`, so
  it also goes `proposed` → `superseded` when the text it came from changes (contracts/cli.md). A rejected one generates a new proposal only if its origin shows a
  modification after the rejection; for a topic, if its title changes or a new book topic
  appears in the Drive.
- Replica: `new` → `current` → (`superseded` → `previous`) | (`withdrawn`). Never `deleted`. A
  match change moves the replica without changing its version.
- Agenda entry: the status is recomputed in every run from the Classroom detail; a
  family correction of a detected exam prevails over what was detected.
