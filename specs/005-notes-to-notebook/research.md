# Research: Class notes and new material reach the topic's notebook by themselves

Every decision below rests on a fact in the first table or on a document named in its row. A fact
with no observation behind it is written as a question and settled in the quickstart. The spec's
own table is the subset the requirements rest on; this one is the full list.

## Observed facts

| Fact | Observed with | Date |
|---|---|---|
| A Doc and a PDF in the student's Drive, shared read-only with the notebook owner, become Drive sources of the owner's notebook | `nlm source add --drive … --type doc|pdf` (notebooklm-mcp-cli 0.15.8), throwaway notebook, invented content | 2026-10-27 |
| Rewriting such a file in Drive (same file id, new revision) reaches the notebook one to two minutes after the notebook is next accessed; nothing changes while nobody accesses it | `files.update` with new media; `nlm source content` every minute, then one read after 8 minutes untouched | 2026-10-27 |
| `nlm source stale` says every Drive source is up to date even while the notebook holds old content | Same test | 2026-10-27 |
| `changes.list` from a saved `startPageToken` returns files written by the API and by Drive for desktop, each with `parents` and `md5Checksum` when `fields` asks for them; a Drive for desktop write appeared 15 s after it | Drive API v3, as the linked student account, through spec 004's OAuth client | 2026-10-27 |
| The change feed's only scoping parameters are `spaces` and `restrictToMyDrive`; there is no folder filter | developers.google.com/workspace/drive/api/guides/manage-changes, read | 2026-10-27 |
| Drive push channels last at most one day (`files`) or one week (`changes`), have no automatic renewal, need a public HTTPS endpoint, and carry no change details | developers.google.com/workspace/drive/api/guides/push, read | 2026-10-27 |
| Cloud Run, Cloud Scheduler (3 jobs a month per billing account) and Secret Manager (6 active versions, 10,000 accesses a month) have free tiers counted per billing account; the free tier needs a billing account | Google Cloud free-tier and pricing pages, read | 2026-10-27 |
| The desktop app's scheduled tasks run only while the app is open and the Mac awake; a missed run gets one catch-up | code.claude.com/docs/en/desktop-scheduled-tasks, read | 2026-10-27 |
| `nlm` keeps browser cookies on the Mac and its documentation advises against server deployments | `docs/AUTHENTICATION.md` and `docs/REMOTE_MCP.md` of the `nlm` project, read | 2026-10-27 |
| Claude takes JPEG, PNG, GIF and WebP up to 10 MB each; an image costs ⌈w/28⌉×⌈h/28⌉ visual tokens on the high-resolution tier (long edge up to 2,576 px, larger images downscaled); a 1126×1500 photo is 2,214 | platform.claude.com/docs/en/build-with-claude/vision, read | 2026-10-27 |
| Anthropic does not use images sent to the API to train models | Same page, FAQ | 2026-10-27 |
| Anthropic's Usage Policy applies additional guidelines to products that let minors "directly interact" with products built on the API | anthropic.com/legal/aup, read | 2026-10-27 |
| The Max plan's 200 USD monthly API credit reaches the Console organisation Server Startup; its workspace `alfabeta` has a 10 USD monthly limit and no key | Claude Console billing and spend-limit pages, company account | 2026-10-27 |
| The operator checked the transcription of four pages of notes made on 2026-10-26 against the photos and accepted it; it is one Markdown with a `## Página N` section per photo, each embedding the photo by name | This project's conversation of 2026-10-26; the Markdown is in the topic's `apuntes/` | 2026-10-26 |
| Tema 01's notebook holds those notes as two plain sources titled «Apuntes · Apuntes de clase · T01.md» and «… .pdf» | `nlm source add` output of 2026-10-26 | 2026-10-26 |
| Spec 001 places a Classroom item as `YYYYMMDD - <title>.<ext>`, as a `.md` note, or as a folder with its files, `descripcion.md` and `enlaces.md`; assignments are folders with `enunciado - <name>` and `enunciado.md` | `specs/001-classroom-sync/tasks.md` T027 and `data-model.md` | 2026-10-27 |

## R1 — Where each part runs

- **Decision**: three places.
  - **Cloud, every 15 minutes**: read the change feed, transcribe, rebuild living files, write the
    report (FR-001, FR-003 to FR-013).
  - **Mac, in each scheduled sync**: bring into the master what Drive holds and the master lacks
    (FR-002), check that the cloud ran recently (FR-017), and run classroom-sync, which puts
    Classroom items into Drive (spec 001, spec 004 `drive push`).
  - **Mac, once per topic**: create both living files and add them to the notebook as sources (User
    Story 5), because only `nlm` can add a source.
- **Rationale**: the spec's clarification and constitution IX (1.6.0). After setup the cloud only
  writes to Drive, which the notebook follows (first table, row 2).
- **Alternatives**: everything on the Mac, rejected by the operator; `nlm` in the cloud, rejected by
  its own documentation.

## R2 — Detecting arrivals: poll the change feed

- **Decision**: Cloud Scheduler starts the Cloud Run job every 15 minutes. The job builds spec 004's
  folder allowlist, reads `changes.list` from its saved cursor through `ScopedDrive`, follows
  `nextPageToken`, and keeps only changes whose `parents` are in the allowlist; a new folder whose
  parent is in it joins it in the same pass. Every other change is dropped inside the adapter before
  the caller sees it (spec 004 FR-009a, amended). The cursor is saved only after the run's writes
  succeed, and only if the token moved or something was written.
- **First run and first sight of a topic**: with no cursor, the job takes `getStartPageToken`
  first, then lists the whole tree under the allowlist once, so material that existed before the
  cursor is taken in (FR-004). A Markdown in `apuntes/` that embeds a photo by name, in a section of
  its own, is that photo's transcription (Tema 01's form, first table): no Claude call.
- **Rationale**: four polls an hour meet SC-001 (one hour) with margin, need no public endpoint, and
  use one Scheduler job.
- **Alternatives**: push channels (first table): a public endpoint, renewal at most weekly, and a
  `changes.list` call anyway. Rejected. Workspace Events API for Drive: developer preview,
  unavailable for accounts outside the operator's domain. Rejected.

## R3 — The cloud's own link and secrets

- **Decision**: the operator links the student's Gmail a second time on the Mac with spec 004's
  flow and client, asking only for the Drive scope, with
  `alfabeta google link --student <id> --account student --scopes drive --print-token`. The command
  writes the refresh token, with the client id and secret, as one JSON to standard output and keeps
  nothing locally; the operator pipes it straight into `gcloud secrets versions add <name>
  --data-file=-`. Nobody types or copies it, and it is never on disk. The Mac's own token stays in the
  keychain.
- **Three secrets, mounted as files** into the job by Cloud Run: the Google link (token and
  client), the Claude API key of the workspace `alfabeta`, and the student's configuration. A
  `FileTokenStore` implements spec 004's `TokenStore` over the mounted files. At 15 minutes the job
  runs about 2,900 times a month; three secrets read once per run stay inside the 10,000 free
  accesses.
- **Rationale**: constitution II (1.6.0): each place holds its own secrets, none copied. Revoking the
  cloud's link leaves the Mac working, and the reverse.
- **Alternatives**: a service account cannot act as a consumer Gmail. Copying the Mac's token:
  forbidden by II.

## R4 — The cloud run's state

- **Decision**: one JSON file `estado.json` in a folder `.alfabeta` at the root of the alfabeta
  folder, read and written through `ScopedDrive`. It holds the cursor and the record of every file
  (data model). Two writers exist: the cloud run, and `notebook setup` on the Mac, which records the
  source ids. Both read `headRevisionId` at start, re-read it immediately before writing, and on a
  difference stop without writing and retry once from the start. The job runs with one task, at most
  one execution at a time, and a 10-minute timeout, shorter than the 15-minute period.
- **Rationale**: no new service and no new client code. The re-check narrows the race to the
  instants between check and write; with one cloud execution at a time and setup run by hand, that
  window is where a conflict can happen, and the retry absorbs it.
- **Cloud data folder**: the job copies the mounted configuration to a writable temporary home and
  runs `--home` there, so spec 004's records (`accounts.json`, `drive.json`) are written and lost with
  the container. The allowlist is rebuilt every run, as spec 004 already does.
- **Alternatives**: Firestore or Cloud Storage: a second service and permission set for one small
  JSON file. Rejected under IX.

## R5 — Transcribing a photo

- **Decision**: one Claude Messages API call per photo, image first, then the instructions: literal
  transcription with the conventions of 2026-10-26 (text between lines `^(…)`, crossed out `~~…~~`,
  doubtful `[?]`, unreadable `[ilegible]`, drawings `[dibujo: …]`, boxed `[recuadro]`), the photo's
  language kept, Spanish only for the frame. The answer is Markdown. JPEG, PNG and WebP up to 10 MB
  are sent as they are (Claude downscales larger images itself); any other format is reported as not
  supported. The model is chosen in quickstart step 2 on the four photos of 2026-10-26; until then
  `claude-sonnet-5-5`.
- **Failures**: a refused or errored call is retried on the next three runs, then reported and left
  until the photo changes. A credit or spend-limit refusal puts every pending photo in `budget_wait`,
  retried on the first run of each day, reported once when it starts and once when it clears.
- **Cost**: about 2,214 image tokens plus 1,500 of instructions in, about 1,000 out per photo: 0.015
  USD (Sonnet 5.5) to 0.03 USD (Opus 5.5) a page at published prices. Estimated, not measured; step 2
  measures it from the API's `usage`. Prices live in the configuration (`[notes] price_in`,
  `price_out`), declared once.
- **Minors**: the operator is Anthropic's customer, and the student never interacts with the API;
  he uploads photos to his Drive. On our reading of the Usage Policy (first table) that is not a
  product serving minors. The reading is ours, stated as such in the spec.
- **Alternatives**: the Gemini API, excluded by its terms. Transcribing in the desktop app: needs
  the Mac on.

## R6 — Building the living files

- **Decision**: each living file is rebuilt whole from the records on every run that changes its
  content, and uploaded as a new revision of the same Drive file id. Rebuilds are deterministic
  (fixed metadata and creation date), so an unchanged rebuild is detected by checksum and not
  uploaded (SC-004). Names: `Apuntes · <topic>.pdf` and `Classroom · <topic>.pdf`, `<topic>` being the
  topic folder's name after its date. Topics are keyed by folder id, so two subjects' `Sin tema`
  never collide.
  - Notes: a cover page, then per page the photo and its transcription, headed «Transcripción
    automática», «Revisada por el alumno» or «En corrección».
  - Classroom: a cover page, then per item (a file, a `.md` note or a folder, first table) one entry:
    a cover page with title, posting date, the text of `descripcion.md` and the addresses of
    `enlaces.md`, then each file's pages. A PDF is copied page by page; a Google-native file is
    exported to PDF through Drive; an Office file is copied by Drive into the Google type and
    exported, and the copy is put in Drive's trash at once (it was never the family's); a Markdown is
    set as text; an image is one page; anything else is named on the cover page.
- **Dependencies**: `reportlab` to draw pages and `pypdf` to copy pages, both pure Python and pinned.
- **Who creates them**: only `notebook setup`. A run that finds a topic without living files records
  and transcribes, and builds nothing (spec User Story 5, scenario 3). A run checks each recorded
  living file's parent and `trashed` before writing; a missing one is reported, never recreated.
- **Alternatives**: a Google Doc as the living file, through Drive's HTML import: images in imported
  HTML need public URLs. Rejected.

## R7 — The student's marks and corrections

- **Decision**: marks are renames of the transcription PDF: « (revisada)» or « (mal)» before the
  extension. A correction is either a photo named like the original plus « (corregida)», which
  replaces that page's photo and transcription, or an edit of the page's Markdown in Drive (its
  checksum changes), which re-renders the page from the edited text without calling Claude. Either
  clears « (mal)» by renaming the PDF back.
- **Rationale**: the Drive phone app renames and uploads; nothing else to install (FR-008).

## R8 — The report and "what it adds"

- **Decision**: a run that changed something writes `Informe AAAAMMDD-HHMM.md` into `Informes/` at the
  root of the alfabeta folder, in Spanish. "What it adds" is one Claude call per changed topic,
  given the new pages and the text of the study guide section of the topic's printable PDF
  (`Tema NN para imprimir · <title>.pdf`, spec 002), extracted with `pypdf`; skipped with a line when
  the topic has no printable PDF or the budget is spent. The Mac's sync lists `Informes/` through
  `ScopedDrive` and puts one agenda line per report it has not listed before.
- **Rationale**: Drive is the one channel the cloud and the family share.
- **Alternatives**: email needs a Gmail scope no spec asks for (spec 004 R9). Rejected.

## R9 — Setting up a topic, and Tema 01

- **Decision**: `notebook setup` on the Mac creates both living files from what is recorded, adds
  each with `nlm source add --drive <id> --type pdf`, and records the source ids in `estado.json`
  (R4's check). It creates a file only when no file id is recorded. It lists the notebook's plain
  sources whose title starts with «Apuntes ·» or «Classroom ·» (Tema 01's, first table) for the
  family to remove by hand; alfabeta removes nothing (FR-011).

## R10 — Bringing Drive's files into the master

- **Decision**: the Mac's pull reads the change feed from its own cursor (`data/drive/pull.json`)
  and downloads into the master every file under a topic folder that is not in `.alfabeta/` and
  that spec 004's `uploads.jsonl` does not already record by Drive id. That covers the family's files
  and the cloud's transcriptions and living files, so the mirrors receive them (constitution VII,
  1.6.0). Each downloaded file gets an `UploadRecord` with `how = "adopted"`, so spec 004's next
  `drive push` uploads nothing for it. A path that already exists in the master is never overwritten:
  the file is reported, and written beside it with « (de Drive)» before the extension.
- **Rationale**: the upload records already say which files came from the Mac; no marker on files
  is needed.

## R11 — Deploying and watching the cloud run

- **Decision**: one container image built from the repository by Cloud Build, a Cloud Run job (one
  task, one execution at a time, 10-minute timeout) in a Tier 1 European region chosen at setup, one
  Scheduler job, and the job's service account allowed to read exactly the three secrets of R3.
  The project alerts the operator by email when an execution fails (Cloud Monitoring alert policy).
  A spent budget is not a failure: the job exits 0 and reports it.
- **To verify at setup**: Cloud Build's free minutes cover a build; the region is Tier 1; the
  company billing account's three free Scheduler jobs are not already used.

## R12 — Limits of a notebook source

- **Question, not a fact**: how large a single source may be. Google's help states limits per
  source; they were not read for this plan. The run reports a living file over `[notes] warn_pages`
  pages; quickstart step 7 reads the current limit.

## R13 — When the cloud run fails

- **Decision**: two channels that do not need the cloud's Google link: the project's alert to the
  operator (R11), and the Mac's sync. Every cloud run ends by writing
  `.alfabeta/ultima-ejecucion.json` (start, end, result): the run's own log, the one write
  constitution V allows a run with no change. The Mac's sync reads it with the Mac's own link and
  writes an agenda line and a macOS notification when the last successful cloud run is more than
  two hours old (spec 004 R9's channels).
- **Known gap**: with the Mac off and the alert email unread, a failure is seen when a page does not
  arrive.
