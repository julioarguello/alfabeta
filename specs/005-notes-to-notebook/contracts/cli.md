# Contract: `notes`, `notebook` and `drive pull` subcommands, the cloud link, and the cloud entry point

These follow spec 001's [command contract](../../001-classroom-sync/contracts/cli.md) and spec
004's [Google subcommands](../../004-google-connection/contracts/cli.md): `--home` before the
subcommand, `--student <id>` resolved once, JSON on stdout, messages for people on stderr, and no
message with an address, a token, a key or an absolute path.

| Subcommand | Runs on | What it does | Writes to | Output | Codes |
|---|---|---|---|---|---|
| `notes run --student <id>` | Cloud (and the Mac, for slice 1) | One pass of research R2: read the change feed (or list the tree on a first run), transcribe new photos, apply marks and corrections, rebuild changed living files, write the report and the run log, save the cursor | Drive (`apuntes/`, living files, `Informes/`, `.alfabeta/`) | JSON `{ok, topics:[{topic, pages_added, items_added, duplicates, unsupported, unreadable, gone, marks, unexpected, waiting_setup, missing_living_files, failed}], budget_wait, spend}` (counts only; `topic` is an opaque index, not a name) | 0 (also when the budget is spent: `budget_wait > 0`) · 2 Google link not usable · 3 partial failure |
| `notebook setup --student <id> --topic <folder>` | Mac | Research R9: create both living files when no file id is recorded, add each to the topic's notebook as a Drive source, record the ids; list plain sources whose titles start with «Apuntes ·» or «Classroom ·» for the family to remove | Drive, the notebook, `estado.json` | JSON `{ok, notes_source, classroom_source, plain_sources_to_remove}` (states and counts, no ids) | 0 · 1 `no_notebook` · 2 link not usable · 5 `nlm` not signed in |
| `drive pull --student <id>` | Mac, in every sync | Research R10: download into the master every file under a topic folder that `uploads.jsonl` does not record, outside `.alfabeta/`; record each as `adopted`; never overwrite; then check the cloud's run log (FR-017) | master folder, `data/drive/pull.json`, `uploads.jsonl`, the agenda | JSON `{ok, pulled, beside, cloud_last_ok_hours}` | 0 · 2 link not usable · 3 partial failure |
| `google link --student <id> --account <alias> --scopes drive --print-token` | Mac, once | Spec 004's flow, asking only for the listed scopes; writes `{client_id, client_secret, refresh_token}` as one JSON line to stdout for a pipe into the cloud's secret store, and keeps nothing (research R3). Refuses to run when stdout is a terminal | nothing | the JSON line | 0 · 1 `stdout_is_terminal` and spec 004's link codes |

**Cloud entry point**: the container copies the mounted configuration (`/secrets/config/config.toml`)
to a writable temporary home and runs `python -m alfabeta --home <tmp> notes run --student <id>`. The
Google link and the Claude key are read from `/secrets/google/link.json` and
`/secrets/claude/key` by a file-backed `TokenStore`. The job's environment names nothing personal.

**Exit codes**: 0 ok · 1 usage or validation · 2 a Google link is not usable · 3 partial failure ·
5 the notebook tool is not signed in. When several apply, the highest wins. A spent budget or a
missing Claude key is not a failure: transcription waits, the run exits 0 and the report says so.
Codes 2, 3 and 5 make a scheduled run report failure.

**Preconditions `notes run` checks before calling anything**:

- the Google link is usable (spec 004 `google check`, against the file-backed store in the cloud);
- `estado.json`'s revision is the one it read at start, re-checked immediately before it writes
  (research R4).
