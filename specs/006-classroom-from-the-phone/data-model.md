# Data model: Classroom read on the Mac with no app open (spec 006)

Entities of the spec's Key Entities, with their fields, rules and transitions. Spec 001's capture,
lock, plan and log stay as its data model says; this file lists only what spec 006 adds or changes.

## Read profile

A browser profile kept for one student's read.

| Field | Rule |
|---|---|
| path | `<data folder>/<student>/classroom-profile/`, mode `0700`; never inside the Drive mount or the repository |
| browser | the installed Google Chrome (`BrowserInstall`); the sign-in window and the read use the same one (FR-002) |
| holder | none, the sign-in window, or the read; never two at once: the browser lock (FR-024a), and Chrome's own `SingletonLock` refused as `lock_busy` |

Holds the school session after the family signs in (a secret, constitution II). alfabeta never
reads its files; it only passes its path to Chrome or Playwright.

## Sign-in wait

One wait for the family, inside one run.

| Field | Rule |
|---|---|
| run | the run id of the lock (`ALFABETA_RUN`) |
| started_at, until | instants; `until` = `started_at` + `[schedule] wait_minutes` |
| ended_by | `address` (the window reached Classroom), `closed` (the family closed it), `timeout` |
| outcome | `signed_in`, `session_expired`, `challenge` |
| waited_seconds | goes to the log line |

Transitions: `waiting` → (`address` \| `closed` \| `timeout`) → one session check →
`signed_in` \| `session_expired` \| `challenge`. A check that finds another account is
`session_expired` with `other_account: true` (FR-006). The window's address is never a field.

## Read allowlist

| Field | Rule |
|---|---|
| names | the call names S8 records as needed and query-only (research R3); a constant in the code |
| recorded_on | the date of the recording; changed only by a new recording in a pull request |

A request whose names are not all in `names` is blocked and counted under `blocked.calls`.

## Call record (spike S8 only)

`method`, `host`, `path`, `names`, `response_tag`, `page_kind`. Never a body, a cookie, a query
value other than the names, or an id. Kept outside the repository.

## Capture (spec 001's, minor version)

The read writes spec 001's capture (`contracts/capture.schema.json`) with these additions, all
optional, so captures by the extractor stay valid:

| Field (on `items[].detail`) | Type | Rule |
|---|---|---|
| `posted_at` | ISO instant | from the call's published time |
| `modified_at` | ISO instant or null | from the call's update time, when it differs from `posted_at` |
| `due_at` | ISO instant or date, or null | a date when no time was set (research R7) |
| `status` | `ItemStatus` value or null | from the submission's bucket, by the table below |
| `grade`, `max_points` | strings or null | as the call gives them |
| `returned_at` | ISO instant or null | |
| `stream[].created_at` | ISO instant | |
| `source` (top level) | `extractor` or `calls` | which route made the capture |

The normaliser (spec 001's `capture.py`) uses a structured field when present and the text field
otherwise; a capture by calls leaves the `*_text` fields `null`. Item and class ids are the URL's
`<xB64>` in both routes (base64 of the decimal id, no padding).

### Status from the call's bucket

Filled from spike S9's comparison, not from the peer project (research R7). Until then:

| Bucket (peer's reading) | `ItemStatus` | Confirmed on this account |
|---|---|---|
| assigned | `pending` | no |
| missing | `overdue` | no |
| turned in | `turned_in` | no |
| done late | `turned_in_late` | no |
| returned, graded, graded late | `returned` | no |
| excused | none (left `null`, listed) | no |
| teacher marked as missing | `missing_per_teacher` — no field seen yet | no |

## Read result

| Field | Rule |
|---|---|
| started_by | `schedule`, `launcher`, `command` (FR-020) |
| outcome | spec 001's `ok`, `partial` or `stopped`, with the stop reason (`session_expired`, `challenge`, `unexpected_ui`, `timeout`, `lock_busy`) |
| counts | classes read, new and changed items, attachments brought and not brought, decisions left pending (FR-014) |
| blocked | `presses`, `loads`, `calls`, `forms`, `other` (FR-005) |
| waited_seconds | from the sign-in wait, if any |

One log line per read (FR-020) and one result email (FR-014) carry these, and nothing else.

## Notice

| Kind | Fields | Rule |
|---|---|---|
| `sign_in_waiting` | student id, `until` (local time), link (research R10) | sent within a minute of the wait starting (FR-013) |
| `read_ended` | student id, the read result's counts and stop reason, `other_account` | one per read (FR-014) |

Spanish text; no name, address or Classroom title (SC-006). Sent from the account whose alias is
`[classroom] notice_account`, role `family`, to itself.

## Seam

| Seam | Port | Today |
|---|---|---|
| secrets | `TokenStore` | keychain |
| scheduler | `Scheduler` | launchd |
| remote view | `RemoteView` | Chrome Remote Desktop |
| local notification | `Notifier` | macOS |
| mirrors | spec 001's mirror step | Google Drive for desktop |
