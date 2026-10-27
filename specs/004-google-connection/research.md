# Research: alfabeta's own Google connection

Every decision below names what it rests on. Pages were read on 2026-10-27; "measured" means seen in
the family's accounts the same day.

## Observed facts

| Fact | Where it comes from |
|---|---|
| A reminder set by the account that writes an event does not reach other readers of the calendar | Measured 2026-10-27: test event with a 37-minute reminder written by the chat connector's account; the student's school account and the owner's account showed none, and both event pages read «Las notificaciones solo se aplican a ti» |
| Reminders are per authenticated user; at most 5 overrides per event; 0 to 40,320 minutes | Calendar API, `concepts/reminders` and `v3/reference/events` |
| An External app in Testing gets refresh tokens that expire after 7 days unless it only asks for basic profile scopes | Google Identity, `protocols/oauth2` |
| A refresh token also dies when revoked, after 6 months unused, beyond 100 tokens per account and client, or on a password change if it holds Gmail scopes | same page |
| An app for personal use (fewer than 100 users, all known to the developer) can run unverified, showing the unverified-app screen | Google Cloud help 13464323 and 7454865; restricted-scope verification page |
| `drive` is a restricted scope; `drive.file` reaches only files the app created or the user opened with it | Google Cloud help 13464325; Drive API `api-specific-auth` |
| An Internal app admits only accounts of its organisation; a personal Gmail needs External | Google Cloud help 15549945 and 13464323 |
| In Spain a person manages their own Google Account from 14 | Google Accounts help 1350409 |
| The student's folder lives today inside the Drive that Google Drive for desktop mounts | The student's configuration (`accounts.drive`, `storage`) and the `drive.root` key of spec 001's template |
| The chat's Google Calendar connector holds one Google account at a time | Anthropic help 10166901 ("the Google account you've connected"); third-party guides agree. No official multi-account path found |
| Google classes `calendar.events` as sensitive and `drive` as restricted; `openid` and `userinfo.email` as non-sensitive | Measured 2026-10-27, the app's Data Access page in the Cloud console |
| An External app in a Workspace organisation can be published unverified: status «In production», 100-user cap, «requires verification» banner; `github.com` is accepted as an authorised domain for the home page and the privacy link | Measured 2026-10-27, the app's Audience and Branding pages |
| The student's personal Gmail is supervised with Family Link: signing in to the app asks a parent to approve with a passkey before the consent screen; the unverified-app screen then appears and can be passed | Measured 2026-10-27, three link attempts; the first ended on another family account's consent screen and was cancelled with nothing stored |
| A reminder set as the student's Gmail (one, at the event's start) shows on that event for the student's account and not for the owner's | Measured 2026-10-27, probe event read in Calendar as both accounts |

## R1 — Runtime dependencies: the standard library

- **Decision**: call Google's REST endpoints with `urllib.request`, run the sign-in with
  `http.server` on a loopback port, and use `hashlib` and `secrets`. No Google client library.
- **Rationale**: spec 001 ships with no runtime dependency, and constitution IX asks for simplicity.
  The calls alfabeta needs are few: token exchange and refresh, `calendarList.get`,
  `events.insert/patch/get/delete`, `files.list/get/create`, and one upload form. Each is one HTTP
  request with a JSON body. A missing field or an HTTP error is easier to see in code alfabeta owns.
- **Alternatives**: `google-auth-oauthlib` plus `google-api-python-client`, which handle the flow and
  discovery for us but bring about twenty transitive packages and generated clients that are hard to
  stub. They can be adopted later behind the same port (R8) if the hand-written calls grow.

## R2 — Sign-in: installed-app flow on loopback with PKCE

- **Decision**: a Desktop OAuth client. `google link` opens the browser at Google's authorisation
  URL, with:
  - `redirect_uri=http://127.0.0.1:<free port>`;
  - `code_challenge` (S256) and a random `state`;
  - `access_type=offline` and `prompt=consent`, so a refresh token is always returned.

  A one-shot local server receives the code, checks `state`, and exchanges it for tokens.
- **No `login_hint`**: it would put the student's address in a URL (constitution III). The operator
  picks the account on Google's own screen.
- **Which account was linked** is checked after the exchange, from the `id_token` the token
  response carries when `openid email` are granted. Its `email` claim is the account's address,
  with no further call. alfabeta compares it locally with the address the private configuration
  holds for that alias, and with the school account's domain (FR-006). On a mismatch it revokes the
  new token and stores nothing.
- `calendarList.get` was considered and rejected: it needs `calendar`, `calendar.readonly` or a
  `calendar.calendarlist*` scope, not `calendar.events` (Calendar API reference, read 2026-10-27).
  The check would fail with 403 on the first real link.
- **Alternatives**: the out-of-band copy-paste flow, which Google retired; the device-code flow,
  which does not offer Calendar or Drive scopes.

## R3 — Secrets: the macOS keychain through `security -i`

- **Decision**: one generic-password item per linked account and one for the client:
  - service `alfabeta.google`;
  - account `<student-id>/<alias>`, and `<student-id>/client` for the client.

  Commands go to `security -i` on its standard input, so the token never appears in a process's
  arguments, where `ps` could read it.
- **Rationale**: the constitution puts tokens in the system keychain (II). A refresh token is the
  only long-lived credential. The client secret of a Desktop app is not truly secret (Google says
  so for installed apps), but it is kept the same way so nothing in the configuration needs
  protecting.
- **Unattended access**: an item created by the `security` tool is readable by that same tool
  without a prompt. The keychain may still ask once when a scheduled process first reads it, and a
  prompt nobody answers hangs the run. The measure is quickstart step 9, run by the schedule, with
  0 prompts expected.
- **Alternatives**:
  - the `keyring` package: a runtime dependency for one platform call;
  - a file with mode 0600 in the data folder: the constitution allows it, but the keychain is
    stronger and is already where the family's other credentials live.

## R4 — Scopes

- **Decision**:
  - `https://www.googleapis.com/auth/calendar.events`, to write events and the student's own
    reminders;
  - `https://www.googleapis.com/auth/drive`, decided in clarify;
  - plus `openid` and `email`, which put the linked account's address in the `id_token` (R2). They
    are needed, not optional.
- **Rationale**: the narrowest set that does the job. Adding a scope later means linking again
  (FR-005).

## R5 — Calendar writes

- **Decision**: write events with ids alfabeta chooses. Each id is a deterministic base32hex
  string of the item's stable key, which the Calendar API accepts as `id` on insert. A rerun then
  finds the same event instead of creating a second one. Before any patch, alfabeta reads the
  event and writes only if a field it owns differs (SC-005). Reminders are always
  `useDefault: false` with explicit overrides, so the student's calendar defaults never add or
  remove one (spec 003, FR-004).
- **The family calendar keeps its owner** (the operator's Gmail). The operator shares it with the
  student's Gmail as "Make changes to events", by hand, once (quickstart). Then the chat
  connector's account is removed from the calendar's sharing (FR-008b).
- **Risks to measure** (quickstart step 5):
  - Whether an event created by another writer, such as the existing events, can carry reminders
    set by the student's account. The probe also patches one existing event, then reads it as both
    accounts.
  - Whether a deleted event's id can be inserted again. The reference says an id "must be unique
    per calendar" and that deleted events stay as `cancelled` for a while; it does not say what an
    insert with that id does. The design therefore treats a conflict on insert as "the event
    exists, possibly cancelled": it reads it and updates it with `status: confirmed`. The probe
    measures this by deleting the probe event and inserting the same id again.

## R6 — Drive: whole-Drive scope, self-limited to the alfabeta folder

- **Decision**: a `ScopedDrive` adapter resolves the alfabeta folder's id once, from the
  configured path, by listing folders by name from the Drive root. It then builds the set of folder
  ids under it. Every call must name a parent or file id inside that set, or the adapter raises
  before any HTTP request. A unit test drives every public method with an outside id and expects
  the refusal; a second test plants a call that bypasses the adapter and expects the import guard
  to fail (FR-009a).
- **Uploads**: multipart for files up to 5 MB, resumable above. Each upload asks for `id`, `size`
  and `md5Checksum`, and counts as done only if both match the local file (FR-012). A file Drive
  stores as a Google-native document has no `md5Checksum`; alfabeta never creates those, and
  migration reports any it finds as "native, not compared".
- **Migration** (FR-010) walks the local tree and the Drive tree under the root and matches them by
  relative path:
  - same size and checksum: adopt the Drive id;
  - missing in Drive: upload;
  - differing: report, change nothing.

  It deletes nothing. `--dry-run` is the default; `--apply` acts.
- **Alternatives**: `drive.file` with a rebuilt tree, rejected in clarify.

## R7 — Leaving Google Drive for desktop

- **Fact**: in streaming mode Drive for desktop mounts the whole «Mi unidad». A single folder
  cannot be excluded from it.
- **Decision**: after a clean migration, the student's base folder moves out of the mount, to
  `~/alfabeta/<student>/` by default. alfabeta stops writing inside
  `~/Library/CloudStorage/GoogleDrive-*`. Drive for desktop can keep running for anything else the
  family uses it for.
- **Check**: every run refuses a base folder under that path (FR-011). Moving the folder is a
  quickstart step for the operator; alfabeta never moves it.
- **Consequence**: spec 001's `drive.root` key changes meaning, from a path in the mount to the
  folder's path in Drive. The local folder gets its own key. Recorded in
  [contracts/config-template.toml](contracts/config-template.toml).

## R8 — Testability: one HTTP port, recorded shapes

- **Decision**:
  - All Google traffic goes through an `HttpTransport` protocol. Tests inject a fake that serves
    responses recorded from real calls during the quickstart, with personal values replaced.
  - Each recorded file names the call and the date it was captured.
  - No test calls Google.
  - The live checks are the quickstart's.
- **Rationale**: a stub of a system nobody has seen work is a claim. The quickstart's first real
  run is where the shapes come from.

## R9 — When a link fails, a second channel

- **Decision**: three channels, in order:
  1. The run's own report and a non-zero exit code. A scheduled run reports a failure.
  2. A macOS notification on the family's Mac, through `osascript`, which needs no Google link.
  3. A line at the top of the agenda in the student's folder (spec 001), which the family reads.
- **Not chosen**:
  - An email: it needs a Gmail scope or a Gmail connector, which no spec asks for.
  - An event written as another account: it would need the operator linked, which FR-004 avoids.
- **Known gap**: if nobody looks at the Mac or the agenda, a failure is only seen when someone
  notices a reminder did not ring. The quickstart says so.

## R10 — Every token used on every run

- **Decision**: `google check` refreshes the access token of every linked account at the start of
  each run, which also counts as use (FR-015). A run that skips Google outputs still runs the check.
