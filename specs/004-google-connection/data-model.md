# Data model: alfabeta's own Google connection

Configuration lives in the student's private `config.toml`. Secrets are kept in the keychain, and
records in the data folder `~/.alfabeta/<student>/data/`. Nothing here is in the repository except
the template keys.

## GoogleApp (configuration + keychain)

| Field | Where | Rule |
|---|---|---|
| `project_label` | config `[google]` | Free text for the operator, e.g. "alfabeta (work account)". Never an id |
| client id, client secret | keychain `alfabeta.google` / `<student>/client` | Set by `google client set` from the JSON Google offers for download. That file is then deleted by the operator |
| publishing status | not stored | `google check` warns if a refresh token was issued less than 8 days ago and the run sees `invalid_grant`, the Testing symptom |

## LinkedAccount

| Field | Where | Rule |
|---|---|---|
| `alias` | config `[google.accounts.<alias>]` | Lowercase ASCII, the only name logs and reports use |
| `role` | same | `student` (only value this spec defines) |
| `address` | same | The account's address, kept only in the private config. It is used to check that linking chose the right account, and never printed |
| `scopes` | same | Exactly R4's list. A difference with the granted scopes is a `missing_scope` status |
| `linked_on` | data `google/accounts.json` | Date of the last successful link |
| refresh token | keychain `alfabeta.google` / `<student>/<alias>` | Replaced on re-link, never added |

Validation at link time:

1. The `email` claim of the token response's `id_token` equals `address`.
2. Its domain is not the school account's domain (`accounts.school`).
3. The granted scopes include every scope in `scopes`.

If any check fails, the token is revoked and nothing is stored.

## AuthCheck (per run, per account)

`ok` · `revoked` · `expired` (`invalid_grant`) · `missing_scope` · `no_token` · `network`. Written to
the run's log line by alias. Every status except `ok` and `network` stops the outputs that need that
account. `network` lets the run retry later and is reported the same way.

## DriveRoot

| Field | Rule |
|---|---|
| `path` | config `[drive] root`: the folder's path inside the student's My Drive, e.g. `alfabeta` |
| `root_id` | Resolved on the first run and stored in `data/google/drive.json`. Checked every run: still a folder, not trashed |
| `folder_ids` | Every folder under the root, rebuilt per run from `files.list`. The allowlist of FR-009a |

## UploadRecord (`data/google/uploads.jsonl`, one line per confirmed file)

| Field | Rule |
|---|---|
| `rel_path` | Path relative to the student's base folder (never absolute) |
| `drive_id` | The file's Drive id |
| `size`, `md5` | Confirmed equal on both sides |
| `run` | The run that confirmed it |
| `how` | `uploaded` or `adopted` (migration) |

A file's latest line wins. A local file whose size or md5 differs from its latest line is uploaded
as a new version of the same Drive file (`files.update` with media), never as a second file.

## MigrationReport (`data/google/migration-<run>.json`)

Lists: `adopted`, `to_upload`, `differs`, `native`, `only_in_drive`. `only_in_drive` holds files the
Mac does not have; migration reports them and never deletes them. Counts are printed; names are
written only to this private file.

## State transitions

```text
LinkedAccount: none ──link──▶ linked ──check ok──▶ linked
                               │  └─check fails──▶ broken ──link again──▶ linked
                               └─revoked by the account──▶ broken
Migration: not run ──dry-run──▶ reported ──apply (only if differs is empty)──▶ done
Base folder: inside Drive mount ──operator moves it──▶ outside (required once migration is done)
```
