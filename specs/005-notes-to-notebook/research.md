# Research: Class notes and new material reach the topic's notebook by themselves

Every decision below rests on a fact in the first table or on a document named in its row. A fact
with no observation behind it is written as a question and settled in the quickstart.

## Observed facts

| Fact | Observed with | Date |
|---|---|---|
| A Doc and a PDF in the student's Drive, shared read-only with the notebook owner, become Drive sources of the owner's notebook | `nlm source add --drive … --type doc|pdf` (notebooklm-mcp-cli 0.15.8), throwaway notebook, invented content | 2026-10-27 |
| Rewriting such a file in Drive (same file id, new revision) reaches the notebook one to two minutes after the notebook is next accessed; nothing changes while nobody accesses it | `files.update` with new media; `nlm source content` every minute, then one read after 8 minutes untouched | 2026-10-27 |
| `nlm source stale` says every Drive source is up to date even while the notebook holds old content | Same test | 2026-10-27 |
| `changes.list` from a saved `startPageToken` returns files written by the API and by Drive for desktop, each with `parents` and `md5Checksum` when `fields` asks for them; a Drive for desktop write appeared 15 s after it | Drive API v3, as the linked student account, through spec 004's OAuth client | 2026-10-27 |
| Drive push channels last at most one day (`files`) or one week (`changes`), have no automatic renewal, need a public HTTPS endpoint, and carry no change details | developers.google.com/workspace/drive/api/guides/push, read | 2026-10-27 |
| Cloud Run, Cloud Scheduler (3 jobs per billing account) and Secret Manager have free tiers; the free tier needs a billing account | Google Cloud free-tier and pricing pages, read | 2026-10-27 |
| The desktop app's scheduled tasks run only while the app is open and the Mac awake; a missed run gets one catch-up | code.claude.com/docs/en/desktop-scheduled-tasks, read | 2026-10-27 |
| `nlm` keeps browser cookies on the Mac and its documentation advises against server deployments | `docs/AUTHENTICATION.md` and `docs/REMOTE_MCP.md` of the `nlm` project, read | 2026-10-27 |
| A Claude image costs ⌈w/28⌉×⌈h/28⌉ visual tokens on the high-resolution tier (long edge up to 2,576 px); a 1126×1500 photo is 2,214 | platform.claude.com/docs/en/build-with-claude/vision, read | 2026-10-27 |
| Anthropic does not use images sent to the API to train models | Same page, FAQ | 2026-10-27 |
| The Max plan's 200 USD monthly API credit reaches the Console organisation Server Startup; its workspace `alfabeta` has a 10 USD monthly limit and no key | Claude Console billing and spend-limit pages, company account | 2026-10-27 |
| The operator checked the transcription of four pages of notes made on 2026-10-26 against the photos and accepted it | This project's conversation of 2026-10-26; the Markdown is in the topic's `apuntes/` | 2026-10-26 |

## R1 — Where each part runs

- **Decision**: three places.
  - **Cloud, every 15 minutes**: read the change feed, transcribe, rebuild living files, write the
    report (FR-001, FR-003 to FR-012).
  - **Mac, in each scheduled sync**: bring what the family added in Drive into the master (FR-002),
    and run classroom-sync, which puts Classroom items into Drive (spec 001, spec 004 `drive push`).
  - **Mac, once per topic**: create the notebook and add its two living files as sources (User
    Story 5), because only `nlm` can add a source.
- **Rationale**: the spec's clarification and constitution IX (1.6.0). The cloud never needs `nlm`:
  after setup it only writes to Drive, which the notebook follows (first table, row 2).
- **Alternatives**: everything on the Mac, rejected by the operator; `nlm` in the cloud, rejected by
  its own documentation.

## R2 — Detecting arrivals: poll the change feed

- **Decision**: a Cloud Scheduler job starts a Cloud Run job every 15 minutes. The job reads
  `changes.list` from the cursor it saved, follows `nextPageToken`, keeps only files whose parent
  chain is inside the alfabeta folder (spec 004's allowlist), and saves `newStartPageToken` only
  after the run's writes succeed. A crashed run reads the same changes again; every step is keyed
  by file id and checksum, so repeating it writes nothing new.
- **Rationale**: four polls an hour meet SC-001 (one hour) with margin, need no public endpoint, and
  cost one Scheduler job of the three free ones.
- **Alternatives**: push channels (first table, row 5): a public endpoint, renewal at most weekly,
  and a `changes.list` call anyway; the gain is minutes the spec does not ask for. Rejected.
  Workspace Events API for Drive: developer preview, unavailable for accounts outside the
  operator's domain. Rejected.

## R3 — Secrets for the cloud run

- **Decision**: the cloud run links the student's Gmail a second time, with spec 004's same flow and
  client, and keeps that refresh token, the OAuth client and the Claude API key in Secret Manager in
  the alfabeta project. The Mac's token stays in the Mac's keychain. Each place holds its own token,
  so revoking one does not break the other, and neither token is copied.
- **Rationale**: spec 004 FR-007 puts the Mac's token in the keychain and nowhere else; copying it to
  the cloud would make two places hold one secret. Google allows many refresh tokens per account and
  client (spec 004 edge cases: 100), and each link replaces only its own.
- **Consequence**: spec 004's FR-007 reads "the system keychain"; this spec's FR-016 adds the
  project's secret store for the cloud's own token. Recorded in the plan's complexity table.
- **Alternatives**: a service account cannot act as a consumer Gmail. Rejected.

## R4 — Where the cloud run keeps its state

- **Decision**: in Drive, as one JSON file `estado.json` inside a folder `.alfabeta` at the root of
  the alfabeta folder, read and written through spec 004's scoped Drive adapter. It holds the change
  cursor and the record of every file (data model). The Mac's pull (FR-002) skips `.alfabeta`, and
  the mirrors never receive it because the master never holds it.
- **Rationale**: no new Google service, no new client code, and the record sits next to the files it
  describes. One writer (the cloud run), so no locking beyond Drive's revision check: the run reads
  the file's `headRevisionId` at start and refuses to write if it changed (a second run overlapping).
- **Alternatives**: Firestore or Cloud Storage: a second service, a second permission set and a
  client for each, for one small JSON file. Rejected under IX.

## R5 — Transcribing a photo

- **Decision**: one Claude Messages API call per photo, from the workspace `alfabeta`, with the
  image first and then the instructions: literal transcription, the conventions of 2026-10-26 (text
  between lines `^(…)`, crossed out `~~…~~`, doubtful `[?]`, unreadable `[ilegible]`, drawings
  `[dibujo: …]`, boxed `[recuadro]`), the photo's language kept, and Spanish only for the frame. The
  answer is Markdown. The model is chosen in quickstart step 2 by transcribing the four photos of
  2026-10-26 with each candidate and comparing against the checked Markdown; until then the default
  is `claude-sonnet-5-5`.
- **Cost**: about 2,214 image tokens plus about 1,500 of instructions in, about 1,000 out per photo;
  at the published prices, 0.015 USD (Sonnet 5.5) to 0.03 USD (Opus 5.5) a page. Estimated, not
  measured; step 2 measures it from the API's `usage`.
- **Budget**: a request refused for credit or for the workspace limit stops transcription for that
  run and is reported (FR-014). Photos wait in their folder.
- **Alternatives**: the Gemini API is excluded by its terms (minors). Transcribing in the desktop
  app needs the Mac on. Rejected.

## R6 — Building the living files

- **Decision**: each living file is rebuilt whole from the records on every run that changes it,
  then uploaded as a new revision of the same Drive file (`files.update`, same id). Rebuilding is
  deterministic: same records, same bytes, so an unchanged rebuild is detected by checksum and not
  uploaded (SC-004).
  - `Apuntes · Tema NN.pdf`: a cover page, then per page the photo and its transcription, each page
    headed «Transcripción automática», «Revisada por el alumno» or «En corrección».
  - `Classroom · Tema NN.pdf`: a cover page, then per item a cover page (title, posting date,
    address if any) and the item's own pages. A PDF is copied page by page; a Google-native file
    is exported to PDF through Drive; an item with no pages is its cover page alone.
- **Dependencies**: `reportlab` to draw pages and `pypdf` to copy pages from PDFs, both pure Python
  and pinned. The standard library cannot draw or merge PDFs. Recorded in the complexity table.
- **Rationale**: the notebook follows a file id (first table, row 2). A whole rebuild is simpler than
  editing a PDF in place, and a topic's files are a few dozen pages.
- **Alternatives**: a Google Doc as the living file, written through Drive's HTML import: images in
  imported HTML need public URLs. Rejected.

## R7 — The student's marks

- **Decision**: the student renames a transcription's PDF in Drive from his phone, adding
  « (revisada)» or « (mal)» before the extension. A rename arrives in the change feed like any change.
  A corrected transcription is a new photo of the same page or a Markdown edited by the family; it
  replaces the page and clears « (mal)».
- **Rationale**: Drive's phone app can rename; nothing else needs installing (FR-007).

## R8 — The report

- **Decision**: a run that changed something writes `Informe AAAAMMDD-HHMM.md` into `Informes/` at the
  root of the alfabeta folder, in Spanish, and the Mac's next sync adds a line to the agenda pointing
  at it. "What it adds" is one Claude call per changed topic, given the new pages and the text of the
  topic's study guide, asking which ideas the guide does not cover; it is skipped when the topic has
  no study guide or the budget is spent.
- **Rationale**: Drive is the one channel the cloud and the family share. The study guide is the
  pack's summary of what the pieces cover (spec 002).
- **Alternatives**: email needs a Gmail scope no spec asks for (spec 004 R9). Rejected.

## R9 — Setting up a topic, and Tema 01

- **Decision**: `notebook setup` on the Mac creates both living files (cover page only) in the topic
  folder through spec 004's Drive adapter, then adds each to the notebook with
  `nlm source add --drive <id> --type pdf`, and stores both ids in `estado.json`. A topic that holds
  material as plain file sources (Tema 01's notes since 2026-10-26) is listed for the family to remove
  those sources by hand; alfabeta removes nothing (FR-010).

## R10 — Bringing family files into the master

- **Decision**: every file alfabeta writes to Drive carries `appProperties.origin = "alfabeta"`. The
  Mac's pull reads the change feed from its own cursor, kept in the Mac's data folder, and downloads
  into the master every file under a topic folder that lacks that property and is not in
  `.alfabeta`. It never deletes in the master.
- **Rationale**: the property tells a family file from alfabeta's own without a second record.
- **Open**: whether files written by Drive for desktop before spec 004's migration carry no
  property. They do not: the migration adopts them by checksum, and the pull skips a file whose
  checksum the master already holds.

## R11 — Deploying the cloud run

- **Decision**: one container image built from the repository by Cloud Build (`gcloud run jobs
  deploy --source`), in a Tier 1 European region chosen at setup, with the job's service account
  allowed to read exactly three secrets. The repository holds the container definition and a
  how-to; the project id, region and secret names are configuration.
- **To verify at setup**: that Cloud Build's free minutes cover a build; that the chosen region is
  Tier 1 for the free tier.

## R12 — Limits of a notebook source

- **Question, not a fact**: how large a single source may be. Google's help states limits per
  source; they were not read for this plan. The run reports a living file over 100 pages so the
  family can decide before any limit; quickstart step 7 reads the current limit.
