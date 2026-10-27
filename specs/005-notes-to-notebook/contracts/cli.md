# Contract: `notes run`, `notebook setup`, the cloud link, and the cloud entry point

These follow spec 001's [command contract](../../001-classroom-sync/contracts/cli.md) and spec
004's [Google subcommands](../../004-google-connection/contracts/cli.md): `--home` before the
subcommand, `--student <id>` resolved once, JSON on stdout, messages for people on stderr, and no
message with an address, a token, a key, a Drive id or an absolute path. The pull into the master,
`drive pull`, is spec 004's (FR-011a).

| Subcommand | Runs on | What it does | Writes to | Output | Codes |
|---|---|---|---|---|---|
| `notes run --student <id>` | Cloud, and the Mac by hand | One pass of research R2: read the change feed (or list the tree on a first run), transcribe new photos, apply marks and corrections, update changed living files, write the report and the run log | Drive (`apuntes/`, living files, `Informes/`, `.alfabeta/`) | JSON `{ok, topics:[{topic, pages_added, items_added, duplicates, unsupported, unreadable, gone, marks, unexpected, waiting_setup, missing_living_files, over_page_count, links_only, failed}], budget_wait, no_key, spend}`; `no_key` is true when this place holds no Claude key and photos wait; `topic` is an opaque index, never a name or id | 0 (also when the budget is spent: `budget_wait > 0`) · 2 Google link not usable · 3 partial failure, or no Claude key in the cloud |
| `notebook setup --student <id> --topic <subject>/<folder>` | Mac | Research R9: find the notebook by `[notebook] title_pattern`; create both living files when no file id is recorded; add each to the notebook as a Drive source; record the ids; list other sources titled «Apuntes ·…» or «Classroom ·…» that are not a recorded living source | Drive, the notebook, `state.json` | JSON `{ok, notes_source, classroom_source, plain_sources_to_remove}` (states and counts) | 0 · 1 `no_notebook` · 2 link not usable · 5 `nlm` not signed in |
| `claude key set --student <id>` | Mac, once | Reads the Mac's own Claude API key of the workspace `alfabeta` from standard input and stores it in the keychain, like spec 004's `google client set`; refuses an empty key | keychain | JSON `{ok}` | 0 · 1 `empty_key` |
| `google link --student <id> --account <alias> --client-file <json> --scopes drive --print-token` | Mac, once | Spec 004's flow with the client in `<json>` (never the keychain's), asking for the listed scopes plus `openid` and `email`, validated against what was asked; writes `{client_id, client_secret, refresh_token}` as one JSON line to stdout for a pipe into the cloud's secret store, and keeps nothing (research R3). Refuses when stdout is a terminal | nothing | the JSON line | 0 · 1 `stdout_is_terminal` and spec 004's link codes |

**Cloud entry point**: the container copies the mounted configuration (`/secrets/config/config.toml`)
to a writable temporary home, reads the student id from it, and runs
`python -m alfabeta --home <tmp> notes run --student <id>`. The Google link and the Claude key are
read from `/secrets/google/link.json` and `/secrets/claude/key` by a file-backed `TokenStore`. The
job's environment names no student.

**Exit codes**: 0 ok · 1 usage or validation · 2 a Google link is not usable · 3 partial failure ·
5 the notebook tool is not signed in. When several apply, the highest wins. A spent budget is not a
failure: transcription waits, the run exits 0 and the report says so. A missing Claude key exits 0
on the Mac (transcription skipped and reported) and 3 in the cloud, so the alert fires. Codes 2, 3
and 5 make a scheduled run report failure.

**Preconditions `notes run` checks before calling anything**:

- the Google link is usable (spec 004 `google check`, against the file-backed store in the cloud);
- `state.json`'s revision is the one it read at start, re-checked immediately before it writes
  (research R4).
