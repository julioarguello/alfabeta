# Contract: the Classroom read on the Mac (`classroom sign-in|capture|refresh|status`, `classroom agent`)

These follow spec 001's [command contract](../../001-classroom-sync/contracts/cli.md): `--home`
before the subcommand, `--student <id>` resolved once, JSON on stdout, messages for people on
stderr in English with the local time on each line (constitution 2.12.0), and no message, log line or URL with a name, an email address, a Classroom
title, a token or an absolute path. `classroom sign-in`, `capture`, `refresh` and `status` take the
student's lock and the browser lock before they touch the read profile, or go on inside them when
`ALFABETA_RUN` names the run that holds them (FR-024a); all but `classroom status` stop with
`lock_busy` when another run holds them, and `classroom status` then reports a read under way and
loads no page (FR-024). The `classroom agent` commands do not touch the profile and take no lock.
`classroom sign-in`, `capture`, `refresh` and `agent install` run only when `[classroom]
profile_read = true` and otherwise end with `disabled` (1); `classroom status` then reports
`session: unknown` and loads no page; `classroom agent uninstall` works whatever the switch says.

| Subcommand | What it does | Writes to | Output | Codes |
|---|---|---|---|---|
| `classroom sign-in --student <id>` | Opens the sign-in window in the read profile (research R5), sends the notice and the macOS notification, waits as FR-010 says, closes the window, checks the session once (FR-021) | the run log's wait (inside a refresh, the refresh's line) | JSON `{ok, outcome: signed_in\|session_expired\|challenge, ended_by: address\|closed\|timeout, waited_seconds, other_account, notice_sent}` | 0 `signed_in` · 1 with `reason` `session_expired`, `challenge`, `lock_busy` or `disabled` |
| `classroom capture --student <id> [--subject <folder>]…` | The guarded read (research R1, R3, R4, R7, R8) of every active class, or of the classes linked to the named subjects; records the captured classes in the lock (FR-023); never opens a window | `captures/`, the attachments it listed in the collect folder of `download collect`, the lock | JSON `{ok, outcome: ok\|partial\|stopped, reason, classes:{read, failed}, items:{new, changed, unchanged, skipped}, attachments:{brought, not_brought}, blocked:{presses, loads, calls, forms, other}}` | 0 `ok` · 3 `partial`: some classes read, with the `reason` of those that were not (`unexpected_ui`, or `session_expired` midway, FR-009) · 1 `stopped` with `reason` (`session_expired`, `challenge`, `unexpected_ui` on the course list, `lock_busy`, `disabled`) |
| `classroom refresh --student <id>` | `classroom sign-in` when the session is not alive, `classroom capture`, `classroom plan`, `classroom apply` under one lock; one result email; one log line with `started_by` (FR-022, FR-020) | everything the four steps write | JSON `{ok, started_by, outcome, reason, waited_seconds, capture:{…}, apply:{added, changed, pending_decisions}, blocked:{…}, result_sent}` | as `classroom capture`; `lock_busy` (1) when another read runs, after bringing a waiting sign-in window to the front (FR-017); 0 with `outcome: skipped` and `reason: outside_hours` when launchd starts it after a missed time (FR-015), logged, no email |
| `classroom status --student <id>` | Says whether the profile's session is alive (one guarded page load and the account check), and when the last read ran and how it ended; with the lock held, loads no page (FR-024) | the lock only (taken and released) | JSON `{ok, session: alive\|expired\|other_account\|unknown, read_under_way, last_read:{at, outcome, reason}}` | 0 always, unless the configuration fails |
| `classroom agent install --student <id>` | Writes the launchd agent that runs `classroom refresh --student <id>` with `ALFABETA_STARTED_BY=schedule` at each `[schedule]` time (research R11), and loads it; rewrites it only when it changes. *(Amendment 2026-11-17: no launcher is built, FR-016.)* | `~/Library/LaunchAgents/` | JSON `{ok, agent: installed\|unchanged, label, times}` (a count, no path) | 0 · 1 `invalid_config` (no `[schedule]` time, or one not `HH:MM`), `disabled` (`profile_read` off), `no_uv`, `docker_unavailable` (no `docker` on the PATH), `no_repository`, `launchctl_failed` (nothing left installed) |
| `classroom agent uninstall --student <id>` | Unloads and removes it, whatever the configuration says | the same | JSON `{ok, agent: removed\|unchanged, label, removed}` | 0 |

### The container read (amendment of 2026-11-17)

| Subcommand | What it does | Writes to | Output | Codes |
|---|---|---|---|---|
| `classroom password set --student <id>` | Asks for the school account's password at a prompt that does not echo it (a terminal only) and stores it in the keychain; clears the `wrong_password` mark (FR-031) | the keychain, the mark | JSON `{ok, stored}` | 0 · 1 `invalid_config` (no terminal, an empty or cancelled answer, or the keychain refused it) · 1 `lock_busy` (asked first, so the lock is held only to write) |
| `classroom password delete --student <id>` | Removes the password and the mark | the keychain, the mark | JSON `{ok, removed}` | 0 · 1 `lock_busy` |
| `classroom refresh --student <id>` (container read) | The container read (plan, run flow of the amendment): Docker, the scripted sign-in when needed, the capture, `download collect`, `classroom plan`, the attachments pass over the plan's downloads, `classroom apply`; sends no email | as above, plus the `wrong_password` mark | JSON `{ok, started_by, outcome, reason, capture:{read, failed, collected, attachments:{brought, not_brought, refused}}, apply:{added, changed, pending_decisions}, blocked:{…}}`, never the account | 0 `ok` · 3 `partial` · 0 with `outcome: skipped` and `reason: outside_hours` when launchd starts it after a missed time (FR-015) · 1 `stopped` with `reason` `rejected`, `challenge`, `second_factor`, `other_sign_in`, `wrong_password`, `no_password`, `session_expired`, `unexpected_ui`, `unreachable`, `docker_unavailable`, `docker_low_memory` (Docker's available memory, read before anything signs in, is under the floor of FR-028), `browser_crashed` (the page died; with classes already read it is the `reason` of a `partial`), `lock_busy` or `disabled`; `timeout` when the read outlives its limit (the container is killed by name) or a step does; or the `reason` of a spec 001 step that failed (`ok: false`, or no JSON and a non-zero exit), such as `drive_not_mounted` |

Inside Claude Code (`CLAUDECODE` set) `classroom refresh` never passes the password: it reads with a
live session or stops with `session_expired`, with no notification (FR-027). On a stop it shows the
macOS notification of FR-032. `started_by` is read from `ALFABETA_STARTED_BY` as above (`schedule`
or absent = `command`; the launcher is not built with the container read).

Stop reasons are spec 001's (`session_expired`, `challenge`, `unexpected_ui`, `timeout`,
`lock_busy`), plus `disabled` and `outside_hours` here, and for the container read `rejected`,
`second_factor`, `other_sign_in`, `wrong_password`, `no_password`, `unreachable`,
`docker_unavailable`, `docker_low_memory` and `browser_crashed` (the table above); `log write-stop` keeps spec 001's list. Codes follow `.claude/rules/python-cli-output.md` §8: 0 success, 1 failure with its `reason`, 3 partial as in spec 005; 2 stays argparse's. `--started-by` is not an option: `classroom
refresh` reads `ALFABETA_STARTED_BY` (`schedule` from the agent's plist, `launcher` from the
launcher; absent = `command`), run plumbing as `ALFABETA_RUN` is.
