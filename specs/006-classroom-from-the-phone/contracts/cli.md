# Contract: the Classroom read on the Mac (`classroom sign-in|capture|refresh|status`, `classroom agent`)

These follow spec 001's [command contract](../../001-classroom-sync/contracts/cli.md): `--home`
before the subcommand, `--student <id>` resolved once, JSON on stdout, messages for people on
stderr in Spanish, and no message, log line or URL with a name, an email address, a Classroom
title, a token or an absolute path. Every command but `classroom status` takes the student's lock
and the browser lock first, or goes on inside them when `ALFABETA_RUN` names the run that holds
them (FR-024a). Each runs only when `[classroom] profile_read = true`; otherwise it ends with
`disabled`.

| Subcommand | What it does | Writes to | Output | Codes |
|---|---|---|---|---|
| `classroom sign-in --student <id>` | Opens the sign-in window in the read profile (research R5), sends the notice and the macOS notification, waits as FR-010 says, closes the window, checks the session once (FR-021) | the run log's wait (inside a refresh, the refresh's line) | JSON `{ok, outcome: signed_in\|session_expired\|challenge, ended_by: address\|closed\|timeout, waited_seconds, other_account, notice_sent}` | 0 `signed_in` · 1 `session_expired` · 4 `challenge` · 6 `lock_busy` |
| `classroom capture --student <id> [--subject <folder>]…` | The guarded read (research R1, R3, R4, R7, R8) of every active class, or of the classes linked to the named subjects; records the captured classes in the lock (FR-023); never opens a window | `captures/`, the attachments it listed in the collect folder of `download collect`, the lock | JSON `{ok, outcome: ok\|partial\|stopped, reason, classes:{read, failed}, items:{new, changed, unchanged, skipped}, attachments:{brought, not_brought}, blocked:{presses, loads, calls, forms, other}}` | 0 `ok` · 1 `session_expired` · 3 `partial` or `unexpected_ui` on a class · 4 `challenge` · 6 `lock_busy` |
| `classroom refresh --student <id>` | `classroom sign-in` when the session is not alive, `classroom capture`, `classroom plan`, `classroom apply` under one lock; one result email; one log line with `started_by` (FR-022, FR-020) | everything the four steps write | JSON `{ok, started_by, outcome, reason, waited_seconds, capture:{…}, apply:{added, changed, pending_decisions}, blocked:{…}, result_sent}` | as `classroom capture`, plus 6 `lock_busy` when another read runs (it then brings a waiting sign-in window to the front, FR-017) and 7 `outside_hours` when launchd starts it after a missed time (FR-015) |
| `classroom status --student <id>` | Says whether the profile's session is alive (one guarded page load and the account check), and when the last read ran and how it ended; with the lock held, loads no page (FR-024) | the lock only (taken and released) | JSON `{ok, session: alive\|expired\|other_account\|unknown, read_under_way, last_read:{at, outcome, reason}}` | 0 always, unless the configuration fails |
| `classroom agent install --student <id>` | Writes the launchd agent that runs `classroom refresh --student <id>` at each `[schedule]` time, and the launcher (research R11); loads the agent | `~/Library/LaunchAgents/`, the launcher bundle | JSON `{ok, times, launcher}` (counts and states, no path) | 0 · 1 `config` (no `[schedule]` time, or spec 001's runner on for this student) |
| `classroom agent uninstall --student <id>` | Unloads and removes both | the same | JSON `{ok, removed}` | 0 |

Stop reasons are spec 001's (`session_expired`, `challenge`, `unexpected_ui`, `timeout`,
`lock_busy`), plus `disabled` and `outside_hours` here. `--started-by` is not an option: `classroom
refresh` reads `ALFABETA_STARTED_BY` (`schedule` from the agent's plist, `launcher` from the
launcher; absent = `command`), run plumbing as `ALFABETA_RUN` is.
