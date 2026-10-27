# Contract: `google` and `drive` subcommands of `python -m alfabeta`

These subcommands follow spec 001's [command contract](../../001-classroom-sync/contracts/cli.md):

- `--home` comes before the subcommand, and `--student <id>` is resolved once.
- JSON goes to stdout and messages for people to stderr.
- No message shows an address, a token, a client secret or an absolute path. Accounts are named by
  their alias.

| Subcommand | What it does | Writes to | Output | Codes |
|---|---|---|---|---|
| `google client set --student <id> --from <file>` | Reads the client id and secret from the JSON Google offers for a Desktop client and stores both in the keychain. Prints a reminder to delete the file. | keychain | JSON `{ok}` | 0 · 1 `bad_client_file` |
| `google link --student <id> --account <alias>` | Runs R2's flow in the browser and validates the account (data model). Stores the refresh token, replacing any earlier one. | keychain, `data/google/accounts.json` | JSON `{ok, alias, scopes}` | 0 · 1 `wrong_account`, `school_account`, `missing_scope`, `denied`, `no_client` |
| `google check --student <id>` | Refreshes every linked account's token and reports each status (data model, AuthCheck). On anything but `ok`, raises the macOS notification of R9. | log line | JSON `{ok, accounts:[{alias, status}]}` | 0 if all `ok` · 2 if any is not |
| `google unlink --student <id> --account <alias>` | Revokes the token at Google and removes it from the keychain. | keychain | JSON `{ok}` | 0 |
| `calendar probe --student <id> --minutes <n>` | Creates one test event, «Prueba alfabeta · ignorar», as the student, `n` minutes ahead with one reminder at its start. Reads it back as the student and prints its id. | the family calendar | JSON `{ok, event}` | 0 · 2 if the link is not `ok` |
| `calendar probe-clean --student <id> --event <id>` | Deletes the probe event. | the family calendar | JSON `{ok}` | 0 |
| `drive migrate --student <id> [--apply]` | R6's migration. A dry run by default; `--apply` acts only when `differs` is empty. | `data/google/migration-<run>.json`; with `--apply`, Drive and `uploads.jsonl` | JSON `{ok, adopted, to_upload, differs, native, only_in_drive}` (counts) | 0 · 1 `differs_present` with `--apply` · 2 link not `ok` |
| `drive push --student <id>` | Uploads every file whose size or md5 differs from its latest upload record, and confirms each one (FR-012). Called by the sync runs. | Drive, `uploads.jsonl` | JSON `{ok, uploaded, failed}` | 0 · 3 if any upload failed (others still done) · 2 link not `ok` |
| `drive pull --student <id>` | Added by spec 005. FR-011a: pulls into the master what Drive holds under a topic folder and the master lacks or holds an older pulled version of. Called first by every sync run. | master folder, `uploads.jsonl`, `data/google/pull.json` | JSON `{ok, pulled, beside, recorded}` (counts) | 0 · 2 link not `ok` · 3 if any file failed |

**Exit codes**: 0 ok · 1 usage or validation error · 2 a Google link is not usable · 3 partial
failure. Codes 2 and 3 make a scheduled run report failure (FR-013).

**Preconditions every Google subcommand checks before calling Google**:

- the base folder is outside `~/Library/CloudStorage/GoogleDrive-*` (FR-011; only `drive push`
  enforces it);
- the client is in the keychain;
- the account's token is in the keychain.
