# Contract: `notes`, `notebook` and `drive pull` subcommands, and the cloud entry point

These follow spec 001's [command contract](../../001-classroom-sync/contracts/cli.md) and spec
004's [Google subcommands](../../004-google-connection/contracts/cli.md): `--home` before the
subcommand, `--student <id>` resolved once, JSON on stdout, messages for people on stderr, and no
message with an address, a token, a key or an absolute path.

| Subcommand | Runs on | What it does | Writes to | Output | Codes |
|---|---|---|---|---|---|
| `notes run --student <id>` | Cloud (and the Mac, for slice 1) | One pass of research R2: read the change feed, transcribe new photos, apply the student's marks, rebuild changed living files, write the report, save the cursor | Drive (`apuntes/`, living files, `Informes/`, `.alfabeta/estado.json`) | JSON `{ok, topics:[{topic, pages_added, items_added, duplicates, unreadable, marks, unexpected, waiting_setup, failed}], spend}` (counts only) | 0 · 2 Google link not usable · 3 partial failure · 4 budget spent (everything but transcription done) |
| `notebook setup --student <id> --topic <folder>` | Mac | Research R9: create both living files if missing, add each to the topic's notebook as a Drive source, record the source ids; list plain file sources holding notes or Classroom material for the family to remove | Drive, the notebook, `estado.json` | JSON `{ok, notes_source, classroom_source, plain_sources_to_remove}` (counts and states, no ids) | 0 · 1 `no_notebook` · 2 link not usable · 5 `nlm` not signed in |
| `drive pull --student <id>` | Mac, in every sync | Research R10: download into the master every family file under a topic folder that the master lacks | master folder, `data/drive/pull.json` | JSON `{ok, pulled, skipped}` | 0 · 2 link not usable · 3 partial failure |

**Cloud entry point**: the container's command is `python -m alfabeta --home /config notes run
--student <id>`. `/config` is a read-only mount holding the student's configuration as a secret; the
job's environment names nothing personal.

**Exit codes added**: 4 the month's AI budget is spent (FR-014), 5 the notebook tool is not signed
in. Codes 2 to 5 make a scheduled run report failure.

**Preconditions `notes run` checks before calling anything**:

- the Google link is usable (spec 004 `google check`);
- `estado.json`'s revision is the one it read at start, before it writes it (research R4);
- the Claude key is present; if it is not, transcription is skipped and reported, everything else
  runs.
