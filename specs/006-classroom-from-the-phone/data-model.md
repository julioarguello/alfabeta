# Data model: Classroom read on the Mac with no app open (spec 006)

Entities of the spec's Key Entities, with their fields, rules and transitions. Spec 001's capture,
lock, plan and log stay as its data model says; this file lists only what spec 006 adds or changes.

## Read profile

A browser profile kept for one student's read.

| Field | Rule |
|---|---|
| path | `data/classroom-profile/` in the student's data folder, mode `0700`; never inside the Drive mount or the repository |
| browser | the installed Google Chrome (`BrowserInstall`); the sign-in window and the read use the same one (FR-002) |
| holder | none, the sign-in window, or the read; never two at once: the browser lock (FR-024a), and Chrome's own `SingletonLock` refused as `lock_busy` |

Holds the school session after the family signs in (a secret, constitution II). alfabeta never
reads its files; it only passes its path to Chrome or Playwright (the sign-in window's address
comes over the pipe of research R5, not from a file).

## Stored password (amendment 2026-11-17)

The school account's password, for the scripted sign-in (FR-027, FR-031).

| Field | Rule |
|---|---|
| where | the macOS keychain, service `alfabeta.classroom`, account `<student>`: never spec 004's `alfabeta.google` service, so it cannot overwrite a Google link |
| set by | `classroom password set`, at a prompt that does not echo it, only from a terminal |
| read by | `classroom refresh`, only when a sign-in is needed and never inside Claude Code; passed to the container on stdin |

## `wrong_password` mark (amendment 2026-11-17)

A file `data/classroom-wrong-password` in the student's data folder holding only the date it was
set. Set when the container read stops with `wrong_password`; cleared by `classroom password set`
and `classroom password delete`. While it exists the container is started with `signin: false`.

## Read container (amendment 2026-11-17)

| Field | Rule |
|---|---|
| image | built from the repository root with `-f docker/classroom/Dockerfile`, labelled with the hash of its inputs (`Dockerfile`, `read.py`, the extractor); rebuilt when the hash changes |
| mounts | the read profile `data/classroom-profile/` (the student's data folder, `0700`), which stays between reads, and an out folder under `data/` (`classroom-out-<run>/`, and `classroom-out-<run>-attachments/` for the attachments pass, whose files the host moves to `data/inbox/`); the container itself is removed at the end (`--rm`) |
| stdin | one JSON line `{account, password, signin}`; `password` is `null` when none is needed or stored |
| stdout | one JSON line per event: sign-in page loads by host and path (no query), each class captured, each attachment, the final counts and stop code; never the account or the password |
| stop codes | `rejected`, `challenge`, `second_factor`, `other_sign_in`, `wrong_password`, `no_password`, `session_expired`, `unexpected_ui`, `unreachable`, `browser_crashed` (the page's `crash` event, or an error whose first line is Playwright's `Target crashed` or `Page crashed` — that of a call during the read, or of one last read of the page when the read stops); `docker_unavailable` and `docker_low_memory` from the host |
| memory | `MemTotal` and `MemAvailable` of Docker's machine in MB, read before the first pass through one short container of the image (`cat /proc/meminfo`, nothing mounted, no network); kept in the run's log line as `memory: {total_mb, available_mb}`, or `null` when it could not be read (the read goes on), and absent when the run stopped before asking; under FR-028's floor the read is not started (`docker_low_memory`) |

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
| names | the call names S8 records as needed and query-only, plus the one R3 admits by name (`t51ITc`, research R3); a constant in the code |
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

Filled from spike S9's comparison, not from the peer project (research R7). *(2026-11-20, S9 on
two classes: the bucket is the small number at `[2, 0, 20]` of `Zj93ge`'s answer; the rows seen are
confirmed; the rest stay unconfirmed.)*

| Bucket (peer's reading; number seen in S9) | `ItemStatus` | Confirmed on this account |
|---|---|---|
| assigned (1) | `pending` | yes, S9 («Asignado») |
| missing (2) | `overdue` | yes, S9 («Sin entregar») |
| turned in (3) | `turned_in` | yes, S9 («Entregado») |
| done late (4) | `turned_in_late` | yes, S9 («Entregado con retraso») |
| returned, graded, graded late (5 seen: graded) | `returned` | not settled: the one graded item (5) also carried the teacher's «missing» notice, read `missing_per_teacher` today *(2026-11-23: graded items without the notice seen too; the mark overrides the bucket, R7)* |
| excused | none (left `null`, listed) | no |
| teacher marked as missing | `missing_per_teacher` — no field located in `Zj93ge` (one item) *(2026-11-23: `[32]` = 3 of the item's entry, on every marked item and no other of 12 classes)* | no *(2026-11-23: yes, S9's third measurement)* |

*(2026-11-20, family decision, #283: the teacher's mark overrides the bucket, as in spec 001, and
its appearance raises an event, once; research R7. Since 2026-11-23 that event is an email to the
family, FR-033.)*

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
| `missing_marked` *(2026-11-23)* | student id; per item newly marked, its subject folder («sin asignatura» if none) and the link to its page in Classroom (ids only, no `/u/<n>`) | one per read that finds a mark not in the sent-marks record, none otherwise (FR-033) |

Spanish text; no name, address or Classroom title (SC-006). Sent from the account whose alias is
`[classroom] notice_account`, role `family`, to itself.

**Sent marks** *(2026-11-23, FR-033)*: per student, in its data folder (user-only), the opaque ids
of the items whose teacher's «missing» mark was emailed. An id is added after the email is sent
and removed when a capture holds the item without the mark. Nothing else is kept.

## Seam

| Seam | Port | Today |
|---|---|---|
| secrets | `TokenStore` | keychain |
| scheduler | `Scheduler` | launchd |
| remote view | `RemoteView` | Chrome Remote Desktop |
| local notification | `Notifier` | macOS |
| shares | spec 001's share step (FR-011a) | the Drive API, through alfabeta's own connection |
