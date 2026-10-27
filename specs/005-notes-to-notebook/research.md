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
| The Max plan's 200 USD monthly API credit reaches the Console organisation Server Startup; its workspace `alfabeta` has a 10 USD monthly limit | Claude Console billing and spend-limit pages, company account | 2026-10-27 |
| The Mac's key of the workspace `alfabeta` is in the keychain; `GET /v1/models` answers 200 with it | `claude key set`, then a request printing only the status | 2026-10-27 |
| `notebook setup` on Tema 01 created both living files in the topic folder, shared each read-only with the notebook owner and nothing else in the folder with anyone, and added two sources (10 to 12); a second run answered `unchanged` twice and added nothing. The four photos were adopted from the checked Markdown with no Claude call | `notebook setup --topic "FiQui/20261001 - Tema 01 - …"`, then the files' `permissions` and `nlm source list` | 2026-10-27 |
| Drive accepts two `properties has { … }` clauses joined with `and` | The look-ups before create of the same setup, no error | 2026-10-27 |
| A Drive PDF source listed by `nlm source list --json` has an empty `url`, type `pdf`, and the Drive file's name as its title, `.pdf` included, whatever `--title` said | Same notebook, after setup | 2026-10-27 |
| Listing the whole alfabeta folder (384 items, 168 folders) takes 171 Drive requests and 73 s from the Mac | `ScopedDrive.open` with a counting transport | 2026-10-27 |
| Step 3 on a test topic (an invented page drawn in a handwriting font): `notes run` wrote the page's Markdown and PDF next to the photo, the transcription equal to what was written, and one page headed «Transcripción automática» in the living file, `pages_added: 1`, 0.0065 USD. The notebook answered a question about the page's invented word, with a citation, on its first query. A second run reported no topic and left the living file's revision and checksum unchanged | `notebook setup` and `notes run` on `FiQui/20261027 - Tema 99 - Prueba alfabeta (borrar)`, `nlm notebook query` now and two minutes later, `headRevisionId` before and after | 2026-10-27 |
| Step 2 on the four photos of 2026-10-26: Haiku 5.5 invents readings that change the meaning (an «ez dira» crossed out read as «eratzen»); Opus 5.5 invents a crossing-out where there is a wavy underline and adds boxes; Sonnet 5.5 keeps the layout, misreads one letter twice («dituten», «daitezke» for «duten», «daiteke») and marks its doubts. `claude-sonnet-5-5` stays. Each photo cost 2,466 tokens in and 326 to 553 out (effort `low`), about 0.009 USD a page at 2 and 10 USD per million tokens in and out | Quickstart step 2, each output compared with the checked Markdown and the photo | 2026-10-27 |
| The operator checked the transcription of four pages of notes made on 2026-10-26 against the photos and accepted it; it is one Markdown with a `## Página N` section per photo, each embedding the photo by name | This project's conversation of 2026-10-26; the Markdown is in the topic's `apuntes/` | 2026-10-26 |
| Tema 01's notebook holds those notes as two plain sources titled «Apuntes · Apuntes de clase · T01.md» and «… .pdf» | `nlm source add` output of 2026-10-26 | 2026-10-26 |
| Spec 001 places a Classroom item as `YYYYMMDD - <title>.<ext>`, as a `.md` note, or as a folder with its files, `descripcion.md` and `enlaces.md`; assignments are folders with `enunciado - <name>` and `enunciado.md`, plus the student's `entrega - <name>` and the grading `correccion.md` | `specs/001-classroom-sync/tasks.md` T027 and `data-model.md` | 2026-10-27 |
| A material without a topic goes to the notebook of its subject's most recent topic | `specs/002-study-pack/spec.md` FR-023 | 2026-10-27 |

## R1 — Where each part runs

- **Decision**: three places.
  - **Cloud, every 15 minutes**: read the change feed, transcribe, rebuild living files, write the
    report (FR-001, FR-003 to FR-008, FR-010 to FR-013, as FR-014 lists).
  - **Mac, in each scheduled sync**: bring into the master what Drive holds and the master lacks
    (FR-002, owned by spec 004's FR-011a), check that the cloud ran recently (FR-017), and run
    classroom-sync, which puts
    Classroom items into Drive (spec 001, spec 004 `drive push`).
  - **Mac, once per topic**: create both living files and add them to the notebook as sources (User
    Story 5), because only `nlm` can add a source.
- **Rationale**: the spec's clarification and constitution IX (1.6.0). After setup the cloud only
  writes to Drive, which the notebook follows (first table, row 2).
- **Alternatives**: everything on the Mac, rejected by the operator; `nlm` in the cloud, rejected by
  its own documentation.

## R2 — Detecting arrivals: poll the change feed

- **Decision**: Cloud Scheduler starts the Cloud Run job every 15 minutes. The job builds spec 004's
  folder allowlist and reads `changes.list` from its cursor through `ScopedDrive.changes`, following
  `nextPageToken`. The adapter receives the set of file ids the state records and lets through a
  change whose parents are in the allowlist, or whose file id is recorded (so a recorded file that
  was removed or moved out still arrives, as `gone`); it drops everything else before returning and
  logs nothing about it (spec 004 FR-009a, amended). A folder that joins the allowlist is listed
  whole once, so content moved in with it is taken in.
- **Fields**: the feed asks only for `nextPageToken,newStartPageToken,changes(fileId,removed,
  file(name,mimeType,parents,md5Checksum,modifiedTime,trashed))`; the name is read only for changes
  the adapter keeps.
- **Echoes**: every write the cloud makes (state, run log, transcriptions, living files, reports,
  temporary conversions) comes back through the next feed page. A change to a file id the state
  records as alfabeta's own is consumed: never an arrival, never a reason to write. Two changes to
  own files are the family's and do arrive: a new name of a transcription PDF (a mark) and a new
  checksum of a transcription Markdown (a correction).
- **The cursor lives in the run log**, `.alfabeta/last-run.json`, written at the end of every
  run as the run's own log (constitution V). `state.json` is written only when a record changes, so
  an idle run, whose token moves because of its own previous run log, writes only the run log
  (SC-004).
- **First run**: with no cursor, the job takes `getStartPageToken` first, then lists the whole tree
  under the allowlist once (FR-004). A Markdown in `apuntes/` that embeds a photo by name, in a
  section of its own, is that photo's transcription (Tema 01's form, first table): no Claude call.
- **Rationale**: four polls an hour meet SC-001 (one hour) with margin, need no public endpoint, and
  use one Scheduler job.
- **Alternatives**: push channels (first table): a public endpoint, renewal at most weekly, and a
  `changes.list` call anyway. Rejected. Workspace Events API for Drive: developer preview,
  unavailable for accounts outside the operator's domain. Rejected.

## R3 — The cloud's own link and secrets

- **Decision**: the cloud gets its own OAuth client, a second Desktop client in the same project.
  The operator downloads its JSON from Google and, on the Mac, runs
  `alfabeta google link --student <id> --account student --client-file <that JSON> --scopes drive --print-token`.
  The command uses that client (never the keychain's), always adds `openid` and `email` so spec
  004's account check can run, validates the grant against the scopes it asked for, writes
  `{client_id, client_secret, refresh_token}` as one JSON line to standard output, keeps nothing, and
  refuses to run when standard output is a terminal. The operator pipes it into
  `gcloud secrets versions add <google_link_secret> --data-file=-` and deletes the downloaded JSON
  at once: the one exception constitution II (1.6.0) names.
  The Mac's own client and token never leave the keychain, and the cloud's never enter it.
- **Claude**: two API keys in the workspace `alfabeta`, each created in the Console for one place:
  one stored in the Mac's keychain with `alfabeta claude key set` (read from standard input, like
  spec 004's `google client set`), one in the cloud's secret store.
- **Three secrets, mounted as files** into the job: the Google link, the Claude key, and the
  student's configuration. The job's service account may read exactly these three. A
  `FileTokenStore` implements spec 004's `TokenStore` over the mounted files. The student id is read
  from the configuration secret, so the job's environment and logs name no student. At 15 minutes
  the job runs about 2,900 times a month; three secrets read once per run stay inside the 10,000 free
  accesses.
- **Rationale**: constitution II (1.6.0): each place holds its own secrets, none copied. Revoking one
  place's link or key leaves the other working.
- **Alternatives**: a service account cannot act as a consumer Gmail. Reusing the Mac's client:
  copies its secret, forbidden by II.

## R4 — The cloud run's state

- **Decision**: one JSON file `state.json` in a folder `.alfabeta` at the root of the alfabeta
  folder, read and written through `ScopedDrive`. It holds the record of every file and the month's
  spend ledger (data model); the cursor is in the run log (R2). Two writers exist: the cloud run, and
  `notebook setup` on the Mac, and `notes run` started by hand on the Mac. All three read
  `headRevisionId` at start, re-read it immediately before writing, and on a difference stop without
  writing and retry once from the start.
- **Look up before create** (public `properties`, not `appProperties`, which Drive keeps private to
  one app, and the Mac and the cloud are two OAuth clients): every file a run creates carries
  `properties.alfabeta_for = <the
  photo's or item's Drive id>`. Before creating a transcription or a conversion, a run looks for a
  file with that property in the same folder and updates it instead. A run that crashed after an
  upload, or two overlapping runs, therefore never leave two transcriptions of one photo
  (constitution V). Living files are updated by file id and never created by a run.
- **Overlap**: the job has one task, task retries set to 0, and a 10-minute timeout, shorter than the
  15-minute period, so one execution has ended before the next starts unless the Scheduler fires
  late; the revision check covers that case. Setup on the Mac is run by hand.
- **Cloud data folder**: the job copies the mounted configuration to a writable temporary home and
  runs `--home` there, so spec 004's records (`accounts.json`, `drive.json`) are written and lost with
  the container. The allowlist is rebuilt every run, as spec 004 already does.
- **Alternatives**: Firestore or Cloud Storage: a second service and permission set for one small
  JSON file. Rejected under IX.

## R5 — Transcribing a photo

- **Unreadable**: the instructions ask for the single line `[ilegible: página completa]` when nothing
  on the photo can be read; that answer is the `unreadable` state, and the page is left out.
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
- **Cost**: measured in quickstart step 2 (first table): 2,466 tokens in and 326 to 553 out per photo
  at effort `low`, about 0.009 USD a page with Sonnet 5.5 at 2 and 10 USD per million tokens in and out. Prices live in the configuration
  (`[notes] price_in`, `price_out`), declared once.
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
  topic folder's name after its date. Topics are keyed by folder id.
  - Notes: a cover page, then per page, in the order pages were first seen, the photo and its
    transcription, headed «Transcripción automática», «Revisada por el alumno» or «En corrección».
  - Classroom: a cover page, then per item (a file, a `.md` note or a folder, first table) one entry:
    a cover page with title, posting date, the text of `descripcion.md` and the addresses of
    `enlaces.md`, then each file's pages. A PDF is copied page by page; a Google-native file is
    exported to PDF through Drive; an Office file is copied by Drive into the Google type in
    `.alfabeta/conversions/`, exported, and that copy put in Drive's trash at once (it was never the
    family's); a Markdown is set as text; an image is one page; anything else is named on the cover
    page.
  - **Never in a living file**: every file whose name starts with `entrega - ` or `correccion`,
    whatever follows (spec 001's roles `submission` and `grading`, including their
    `(anterior YYYY-MM-DD)` versions): the student's own work and its grading (constitution III). An
    assignment enters with its statement only.
  - **Previous versions**: a file named `<name> (anterior YYYY-MM-DD)` (spec 001 FR-015b) is never a
    part; the current version replaces the item's pages in place.
  - **Announcements** (`… aviso …` notes in `Sin tema`) are not material and stay out (spec 002
    FR-023 routes material only).
  - **`Sin tema`**: its materials go into the living Classroom file of the subject's most recent
    topic, the topic folder whose date is latest when the material is first seen, and stay there,
    as spec 002 FR-023 sends them to that topic's notebook. An item moved by classroom-sync to
    another topic leaves the first file and enters the second.
- **Dependencies**: `reportlab` to draw pages and `pypdf` to copy pages, pinned. `pypdf` is pure
  Python; `reportlab` 5.1.0 pulls Pillow, which ships binary wheels, and charset-normalizer
  (`uv add`, 2026-10-27).
- **Who creates them**: only `notebook setup`. A run that finds a topic without living files records
  and transcribes, and builds nothing (spec User Story 5, scenario 3). A run checks each recorded
  living file's parent and `trashed` before writing; a missing one is reported, never recreated.
- **Alternatives**: a Google Doc as the living file, through Drive's HTML import: images in imported
  HTML need public URLs. Rejected.

## R7 — The student's marks and corrections

- **Decision**: a page's PDF is `<photo name> · transcripción.pdf`, also for an adopted Markdown.
  Marks are renames of it: « (revisada)» or « (mal)» before the extension. A correction is either a
  photo named like the original plus « (corregida)», which replaces that page's photo and
  transcription in place, or an edit of the page's Markdown in Drive (its checksum changes), which
  re-renders the page from the edited text without calling Claude. After a correction alfabeta
  writes the new PDF under the name without a mark; the latest event wins.
- **Rationale**: the Drive phone app renames and uploads; nothing else to install (FR-008).

## R8 — The report and "what it adds"

- **Decision**: a run that changed something writes `Informe AAAAMMDD-HHMM.md` into `Informes/` at the
  root of the alfabeta folder, in Spanish. "What it adds" is one Claude call per changed topic,
  given the new pages and the text of the study guide section of the topic's printable PDF, which
  the study-pack skill writes as `Tema NN para imprimir · <title>.pdf` in the topic folder
  (`skills/study-pack/SKILL.md`, step 10), extracted with `pypdf`; skipped with a line when that PDF
  is missing or the budget is spent. Every call's `usage` goes into the month's spend ledger. The
  Mac's sync lists `Informes/` through `ScopedDrive` and adds one agenda line per report it has not
  listed before.
- **Rationale**: Drive is the one channel the cloud and the family share.
- **Alternatives**: email needs a Gmail scope no spec asks for (spec 004 R9). Rejected.

## R9 — Setting up a topic, and Tema 01

- **Decision**: `notebook setup --topic <subject>/<folder>` on the Mac finds the topic's notebook by
  `[notebook] title_pattern` (`nlm notebook list`), creates both living files from what is recorded
  when no file id is recorded, adds each with `nlm source add --drive <id> --type pdf`, and records
  the file and source ids in `state.json` (R4's check). It shares each living file read-only with
  the notebook owner's account, and nothing else (the measurement of 2026-10-27 shared exactly the
  files), the account in `[notebook] owner`. Before building, it runs the same recording pass as `notes run` for that topic, so Tema
  01's adopted Markdown is in the first build. It lists the notebook's other sources whose
  title starts with «Apuntes ·» or «Classroom ·» and whose id is not a recorded living source
  (Tema 01's two, first table) for the family to remove by hand; alfabeta removes nothing (FR-011).

## R10 — Bringing Drive's files into the master

- **Decision**: owned by spec 004's FR-011a, added in this pull request: the pull exists because spec
  004 leaves the mount, and its rule is an upload-record rule. This spec relies on it and adds
  nothing to it.

## R11 — Deploying and watching the cloud run

- **Notifier in the cloud**: spec 004's account check calls a `Notifier`; the cloud injects one that
  only logs, because `osascript` exists only on the Mac.
- **Decision**: one container image built from the repository by Cloud Build, a Cloud Run job (one
  task, task retries 0, 10-minute timeout) in a Tier 1 European region chosen at setup, one
  Scheduler job in time zone `Europe/Madrid` (constitution VIII), and a service account allowed to
  read exactly the three secrets of R3. The project alerts the operator by email when an execution
  fails (a Cloud Monitoring alert policy). A spent budget is not a failure: the job exits 0 and
  reports it. A missing Claude key in the cloud is a failure (exit 3): the alert fires.
- **To verify at setup, recorded in this table when read**: Cloud Build's and Artifact Registry's
  free allowances cover one image; Cloud Logging and Monitoring alerting cost nothing at this
  volume; the region is Tier 1; the company billing account's three free Scheduler jobs are not
  already used. Until then constitution IX's "within its free tier" is a stated aim, checked in
  quickstart step 5.

## R12 — Limits of a notebook source

- **Question, not a fact**: how large a single source may be. Google's help states limits per
  source; they were not read for this plan. The run reports a living file over `[notes] warn_pages`
  pages; quickstart step 7 reads the current limit.

## R13 — When the cloud run fails

- **Decision**: two channels that do not need the cloud's Google link: the project's alert to the
  operator (R11), and the Mac's sync. Every cloud run ends by writing `.alfabeta/last-run.json`
  (its own log: start, end, result, `ran_on`, `last_ok_ended`, the cursor). Only a run with
  `ran_on = cloud` moves `last_ok_ended`. The Mac's sync reads it with the Mac's own link and writes an agenda line and a macOS notification
  (spec 004's `notify`) when it is older than `[notes] cloud_stale_hours`.
- **Known gap**: with the Mac off and the alert email unread, a failure is seen when a page does not
  arrive.
