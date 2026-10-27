# Implementation Plan: alfabeta's own Google connection (Calendar and Drive)

**Branch**: `docs/30-spec-004-google-connection` | **Date**: 2026-10-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-google-connection/spec.md`

## Summary

alfabeta gets its own app in a Google Cloud project that the operator creates with the work
account. The app is External and published. The student's personal Gmail is linked once, through
Google's sign-in in the browser. From then on alfabeta acts as that account with no conversation
open:

- **Calendar:** reminders it sets ring only for the student (spec 003).
- **Drive:** it writes and verifies each file itself, adopting the tree Drive for desktop created,
  and limits itself to the alfabeta folder.

Refresh tokens and the client secret live in the macOS keychain. Every run checks every link first
and reports a broken one on three channels.

## Technical Context

**Language/Version**: Python 3.12, inside spec 001's package `src/alfabeta`.

**Primary Dependencies**: none at runtime, the same as spec 001. Google's REST endpoints are called
with `urllib.request`, the sign-in uses `http.server`, and secrets go through the macOS `security`
command (research R1, R3). Development: spec 001's `ruff`, strict `pyright` and `pytest`.

**Storage**:

- configuration: `[google]`, `[drive]` and `[storage]` keys in the student's `config.toml`;
- secrets: the keychain;
- records: `~/.alfabeta/<student>/data/google/` (`accounts.json`, `drive.json`, `uploads.jsonl`,
  migration reports).

**Testing**: `pytest` with an injected `HttpTransport` fake that replays responses recorded during
the quickstart (research R8). No test calls Google. The live proof is [quickstart.md](quickstart.md).

**Target Platform**: macOS (the keychain and `osascript`), the family's Mac.

**Project Type**: subcommands of spec 001's local command (`python -m alfabeta`).

**Performance Goals**: none of its own. The migration walks one student's tree, hundreds of files,
once.

**Constraints**:

- nothing personal in URLs, logs or the repository;
- no credential typed by a tool;
- Drive calls only inside the alfabeta folder;
- idempotent uploads and event writes;
- the base folder outside the Drive for desktop mount.

**Scale/Scope**: one student, one linked account, designed for several.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Checked against
constitution 1.3.0, amended in this pull request.

| Principle | How the plan meets it | Status |
|---|---|---|
| I. The student is configuration | Accounts, addresses, the Drive root and the project label are config keys under `--student <id>`; the code knows none of them | Pass |
| II. Three layers | Template keys in the repo ([contracts/config-template.toml](contracts/config-template.toml)); values in the private config; tokens and client secret in the keychain; records in `data/` | Pass |
| III. Minors' data | No `login_hint`, so no address in a URL. Accounts are named by alias in output. The address is compared locally and never printed. Test responses have invented values. Data goes only to the family's own Google account | Pass |
| IV. Read-only on school platforms | The school account is refused at linking; nothing here touches Classroom | Pass |
| V. Idempotent, incremental | Deterministic event ids; patch only on difference; uploads keyed by path with size and md5; migration adopts before uploading and deletes nothing | Pass |
| VI. One isolated, tested provider | Google sits behind one transport port and three adapters (OAuth, Calendar, Drive), tested against recorded shapes | Pass |
| VII. Outputs degrade on their own (1.3.0) | A broken link stops only the outputs that need it; Drive counts a file only when Drive confirms it; the folder on the Mac stays the base output | Pass |
| VIII. `Europe/Madrid` | Events are written with `timeZone: "Europe/Madrid"`; the reminders' minutes are computed by spec 003 from zone-aware instants | Pass |
| IX. Simplicity | Standard library only; one transport, three adapters; no generated clients | Pass, with one justified exception (Complexity Tracking) |

Re-checked after Phase 1: unchanged.

## Project Structure

### Documentation (this feature)

```text
specs/004-google-connection/
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

### Source Code (additions to spec 001's layout)

```text
src/alfabeta/google/
├── __init__.py
├── transport.py      # HttpTransport protocol + UrllibTransport (the only module that opens sockets)
├── keychain.py       # TokenStore protocol + KeychainStore over `security -i`
├── oauth.py          # loopback + PKCE sign-in, token refresh, revoke, account validation
├── accounts.py       # LinkedAccount, AuthCheck, `google link/check/unlink/client set`
├── calendar.py       # CalendarClient: get/insert/patch/delete with deterministic ids and explicit reminders
├── drive.py          # ScopedDrive: root resolution, folder allowlist, list, upload (multipart/resumable), md5 check
├── migrate.py        # migration plan and apply; uploads.jsonl
└── notify.py         # macOS notification and the agenda's failure line (R9)
tests/
├── fixtures/google/  # recorded responses, invented values, each named with its call and capture date
└── test_google_*.py  # one per module, plus the FR-009a scope test and the "no socket outside transport" test
```

**Structure Decision**: a subpackage of spec 001's single package. It needs spec 001's
configuration loading, log, lock and agenda. Without them it would duplicate those pieces.

## Class design (by layer)

Facts the design rests on: [research.md](research.md#observed-facts).

| Layer | Names | Responsibility |
|---|---|---|
| Domain | `LinkedAccount`, `AuthStatus`, `UploadRecord`, `MigrationPlan`, `DriveRoot` | Values and rules from the [data model](data-model.md); no I/O |
| Ports | `HttpTransport`, `TokenStore`, `Notifier`, `Clock` | What the core needs from the outside |
| Adapters | `UrllibTransport`, `KeychainStore`, `GoogleOAuth`, `CalendarClient`, `ScopedDrive`, `MacNotifier` | Each implements one port or wraps the transport for one Google API |
| Services | `link_account`, `check_accounts`, `plan_migration`, `apply_migration`, `push_files` | Orchestrate adapters per command; return results the CLI prints |
| CLI | `google …`, `calendar probe…`, `drive …` in `__main__.py` | Arguments, JSON out, exit codes ([contracts/cli.md](contracts/cli.md)) |

## Vertical slices (each leaves the system demonstrable)

The first slice's acceptance criterion comes before its ports. Each slice is proved by its
quickstart steps.

1. **Link and check.** Covers US1 and US4. `google client set`, `link`, `check`, `unlink`, through
   `transport`, `keychain`, `oauth` and `accounts`. Done when quickstart steps 1–4 and 6 pass on the
   real accounts.
2. **A reminder that rings.** Covers US2 and unblocks spec 003. `calendar probe` and `probe-clean`
   through `CalendarClient`. Done when step 5 is seen on the phone and recorded.
3. **Drive migration.** Covers US3 and FR-009a, FR-010. `drive migrate`, dry run then apply,
   through `ScopedDrive` and `migrate`. Done when step 7's report shows `differs: 0` and the apply
   uploads only `to_upload`.
4. **Drive in every run.** Covers FR-011 to FR-015. `drive push`, the mount check, `notify`, and
   `google check` at the start of spec 001's runs. Done when two consecutive pushes report
   `uploaded: 0`, and when a revoked link shows in the notification and the agenda.

Spec 003's calendar writes reuse slice 2's `CalendarClient`. Spec 001's replicas reach Drive through
slice 4.

## Complexity Tracking

| Departure | Why it is needed | Simpler alternative rejected because |
|---|---|---|
| The whole-Drive scope (`drive`, restricted) over a minor's account | The operator chose to adopt the tree Drive for desktop created (clarify, 2026-10-27) | `drive.file` cannot see that tree. Mitigation: `ScopedDrive` allowlist plus a test that every method refuses an outside id (FR-009a) |
| macOS-only secret store and notifications | The family runs alfabeta on a Mac; the constitution names the system keychain | A portable store (a file, `keyring`) adds either a weaker secret or a dependency for no second platform |
