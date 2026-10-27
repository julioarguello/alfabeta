# Implementation Plan: Class notes and new material reach the topic's notebook by themselves

**Branch**: `docs/44-spec-005-notes-to-notebook` | **Date**: 2026-10-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-notes-to-notebook/spec.md`

## Summary

Each topic's notebook holds two living PDFs in Drive, `Apuntes · <topic>.pdf` and
`Classroom · <topic>.pdf`, added once as Drive sources from the Mac. A Cloud Run job in the
operator's Google Cloud project for alfabeta wakes every 15 minutes, reads Drive's change feed, transcribes new
photos of the notes with the Claude API, and rebuilds the living file that changed. The notebook
follows the rewritten file the next time it is opened, so the cloud never needs the unofficial
notebook tool. On the Mac, each sync brings into the master what Drive holds and the master lacks,
and warns when the cloud has stopped running.

## Technical Context

**Language/Version**: Python 3.12, inside spec 001's package `src/alfabeta`.

**Primary Dependencies**: `reportlab` and `pypdf` at runtime, pinned, to draw and copy PDF pages
(research R6). Google and Claude are called with `urllib.request` through spec 004's
`HttpTransport`. Development: spec 001's `ruff`, strict `pyright` and `pytest`.

**Storage**:

- configuration: `[notes]` and `[cloud]` keys ([contracts/config-template.toml](contracts/config-template.toml));
- secrets: three Secret Manager secrets mounted as files into the cloud run (its own OAuth client
  and token, its own Claude key, the configuration); the keychain for the Mac's own (research R3);
- records: `.alfabeta/state.json` and the run log `.alfabeta/last-run.json`, which holds
  the change cursor, in the student's Drive (research R2, R4, R13).

**Testing**: `pytest` with spec 004's recorded-response transport for Drive and a recorded Claude
response with invented content; a fake `NotebookSources` for `nlm`. Image fixtures are drawn by the
test suite, never photos of real notes. The live proof is [quickstart.md](quickstart.md).

**Target Platform**: Cloud Run job (Linux container) for `notes run`; macOS for `notebook setup`, the
cloud link and the staleness check.

**Project Type**: subcommands of spec 001's local command (`python -m alfabeta`), plus a container
that runs one of them.

**Performance Goals**: a page in the living file within an hour of upload (SC-001); four runs an
hour leave three quarters of the hour as margin.

**Constraints**:

- nothing personal in URLs, logs, the repository or the container's environment;
- every Drive call inside the alfabeta folder (spec 004 FR-009a);
- no source added or removed by the cloud; nothing of the family's deleted anywhere (alfabeta's own
  temporary Office conversions go to Drive's trash at once, research R6);
- idempotent runs: unchanged input, zero writes (SC-004);
- spend under the workspace limit (FR-015).

**Scale/Scope**: one student, two subjects, about 4 to 8 note pages and a dozen Classroom items per
topic.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Checked against
constitution 1.6.0, amended in this pull request.

| Principle | How the plan meets it | Status |
|---|---|---|
| I. The student is configuration | Project, region, schedule, secret names and model are config keys; the code knows no student, topic or account | Pass |
| II. Three layers (1.6.0) | Template keys in the repo; values in the private config, mounted into the job as a secret; the Mac's client, token and Claude key in the keychain; the cloud's own OAuth client, token and Claude key in the project's secret store, downloaded or minted straight into it, so nothing is copied between places; the cloud's records in the state folder in Drive that II names | Pass |
| III. Minors' data | Photos go to the student's Drive, the owner's notebook (by Drive sharing), the project and Claude, all listed in III (1.6.0); the student's work and grading (`entrega`, `correccion.md`) never enter a living file; no model whose terms exclude minors; the job's environment names no student; logs carry opaque indexes and counts; fixtures are invented and drawn | Pass |
| IV. Read-only on school platforms | Nothing here reads or writes Classroom; it reads what classroom-sync put into Drive | Pass |
| V. Idempotent, incremental | Records keyed by Drive id and checksum; cursor saved last; deterministic rebuilds compared by checksum before upload; nothing deleted, a vanished photo is reported | Pass |
| VI. One isolated, tested provider | Drive behind spec 004's adapter, Claude behind one `Transcriber` port, `nlm` behind one `NotebookSources` port; each with recorded or fake responses | Pass |
| VII. Outputs degrade on their own (1.6.0) | A spent budget stops transcription only; a missing setup stops only that topic's notebook; the master receives everything Drive holds under a topic folder, the family's files and the cloud's, so the mirrors do too; state and reports stay in Drive | Pass |
| VIII. `Europe/Madrid` | The schedule and the report's times are in `Europe/Madrid` | Pass |
| IX. Simplicity | The cloud part is the need spec 005 names (1.6.0); one job, one schedule, no store beyond Drive; two dependencies justified | Pass, with the exceptions in Complexity Tracking |

Re-checked after Phase 1: unchanged.

## Project Structure

### Documentation (this feature)

```text
specs/005-notes-to-notebook/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   └── config-template.toml
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (additions to the layout of specs 001 and 004)

```text
src/alfabeta/notes/
├── __init__.py
├── model.py          # Arrival, NotesPage, LivingFile, ClassroomEntry, ChangeCursor, RunReport (no I/O)
├── state.py          # StateStore port + DriveNotesStateStore over .alfabeta/state.json with the revision check
├── changes.py        # ChangeFeed port + DriveChangeFeed: changes.list paging, allowlist filter, kinds
├── transcribe.py     # Transcriber port + ClaudeTranscriber (Messages API through HttpTransport)
├── secrets.py        # FileTokenStore: spec 004's TokenStore over the files the cloud mounts
├── pdf.py            # PdfBuilder: deterministic living files with reportlab and pypdf
├── sources.py        # NotebookSources port + NlmSources (`nlm source add --drive`), Mac only
├── run.py            # notes run: one reconciliation pass
├── setup.py          # notebook setup
├── watch.py          # the Mac's check that the cloud ran recently (FR-017)
└── report.py         # RunReport → Informes/*.md, and "what it adds"
deploy/notes-cloud-run/
├── Dockerfile
└── README.md         # points to docs/how-to/notes-cloud-run.md
docs/how-to/notes-cloud-run.md
tests/
├── fixtures/notes/   # recorded change pages and Claude answers, invented values, named <call>-<date>.json
└── test_notes_*.py   # one per module
```

**Structure Decision**: a subpackage beside spec 004's `google/`, reusing its transport, OAuth refresh
and scoped Drive adapter. The container runs the same package, so the Mac and the cloud cannot
drift.

## Class design (by layer)

Facts the design rests on: [research.md](research.md#observed-facts).

| Layer | Names | Responsibility |
|---|---|---|
| Domain | `Arrival`, `NotesPage`, `LivingFile`, `ClassroomEntry`, `ChangeCursor`, `RunReport` | Values, states and transitions from the [data model](data-model.md); no I/O |
| Ports | `ChangeFeed`, `StateStore`, `Transcriber`, `PdfBuilder`, `NotebookSources`, `Clock` | What the core needs from the outside |
| Adapters | `DriveChangeFeed`, `DriveNotesStateStore`, `ClaudeTranscriber`, `ReportlabPdfBuilder`, `NlmSources`, `FileTokenStore` | Each implements one port; Drive ones wrap spec 004's `ScopedDrive` |
| Services | `run_notes`, `setup_topic`, `check_cloud`, `write_report` | One per subcommand or sync step; return results the CLI prints |
| CLI | `notes run`, `notebook setup`, `google link --client-file … --print-token` in `__main__.py` | Arguments, JSON out, exit codes ([contracts/cli.md](contracts/cli.md)) |

## Vertical slices (each leaves the system demonstrable)

The first slice's acceptance criterion is quickstart step 3: one photo, one page, the notebook
answers. Ports are written for it, not for the end state.

1. **A photo becomes a page, run on the Mac.** Covers US1 (scenarios 2 to 5), US5 (scenarios 1, 3
   and 4) and FR-004. `notebook setup` and `notes run` for notes only, with `changes`, `state`,
   `transcribe`, `pdf`, `sources`. Done when quickstart steps 1 to 3 pass.
2. **The same pass in the cloud.** Covers US1 scenario 1, FR-014 and FR-017. The cloud's own link,
   `FileTokenStore`, the container, the job, the Scheduler job, the alert, the Mac's staleness check
   and the how-to. Done when quickstart step 5 passes with the Mac off.
3. **Classroom items in their living file.** Covers US3 and FR-010. Done when quickstart step 6
   passes.
4. **Marks, corrections, report and budget.** Covers US2, US4, FR-013 and FR-015. Done when quickstart steps 4
   and 7 pass.
5. **Drive's files reach the master.** FR-002, built as spec 004's FR-011a (its tasks T029a and
   T029b). Done when a photo uploaded from the phone and its transcription are in the master after
   the next sync, and the next `drive push` uploads nothing. Must ship before spec 004 moves the
   master out of the Drive for desktop mount.
6. **Tema 01 and real use.** US5 scenario 2 on the real topic, then quickstart step 8.

Slice 5 lives in spec 004 and can run in parallel with slices 1 to 4.

## Complexity Tracking

| Departure | Why it is needed | Simpler alternative rejected because |
|---|---|---|
| A cloud job in the operator's Google Cloud project for alfabeta | The operator wants notes to reach the notebook with the Mac off; the desktop app's tasks need it open (research, first table) | Mac only: rejected by the operator in clarify; constitution IX amended to 1.6.0 |
| A second OAuth client and refresh token for the student, and a second Claude key, in Secret Manager | The cloud cannot read the Mac's keychain; constitution II (1.6.0) forbids copying a secret between places (research R3) | A service account cannot act as a consumer Gmail |
| One account-wide Drive read: the change feed | Drive v3's change feed takes no folder filter (research, first table); polling each folder instead costs one listing per folder per run | Spec 004 FR-009a amended: the adapter drops every change outside the allowlist before returning, keeps and logs nothing about it, and the scope test covers the feed |
| The cloud's records in Drive instead of a database | One small JSON, two writers guarded by a revision check (research R4); constitution II (1.6.0) names the place | Firestore or Cloud Storage: a second service and permission set |
| `reportlab` and `pypdf` at runtime | The standard library cannot draw or merge PDFs, and the notebook follows a PDF in Drive (research R6) | A Google Doc living file needs images at public URLs |
| Two places that call Claude (transcription, "what it adds") under one budget | The report is what tells the family the pack is missing what the notes stress (US4) | No report: the student studies a pack that silently misses the notes |
