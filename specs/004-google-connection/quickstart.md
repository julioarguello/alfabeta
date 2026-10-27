# Quickstart: link alfabeta to Google and prove it works

Runnable validation of spec 004, end to end, on the family's Mac. Steps 1 to 4 are done once by
the operator. The commands are in [contracts/cli.md](contracts/cli.md); the records they write are
in [data-model.md](data-model.md).

## Prerequisites

- The operator's work account, with permission to create Google Cloud projects.
- The operator can sign in as the student's personal Gmail.
- The student's phone has that Gmail in the Calendar app (spec 003, FR-019).
- spec 001's package installed (`uv sync`), and the student's `config.toml` with the keys of
  [contracts/config-template.toml](contracts/config-template.toml).

## 1. Create the app (work account, once)

1. In the Google Cloud console, signed in with the work account, create a project and enable the
   **Google Calendar API** and the **Google Drive API**.
2. Configure the OAuth consent screen:
   - Audience **External**. If the console refuses it, an organisation policy blocks it; stop here
     (spec edge case).
   - Add the scopes of research R4.
   - **Publish** the app ("In production").

   Leaving it in Testing makes every token expire after 7 days.
3. Create an OAuth client of type **Desktop app** and download its JSON.
4. Store the client and delete the JSON:

   ```bash
   uv run python -m alfabeta google client set --student <id> --from ~/Downloads/client_secret_*.json
   ```

   Expected: `{"ok": true}`.

## 2. Share the family calendar with the student's Gmail (owner's Gmail, once)

In Google Calendar, signed in as the owner, open the settings of the family calendar. Share it with
the student's Gmail with **Make changes to events**.

## 3. Link the student's Gmail

```bash
uv run python -m alfabeta google link --student <id> --account student
```

1. The browser opens Google's sign-in. Choose the student's Gmail.
2. On «Google no ha verificado esta aplicación», choose to continue: the app is the family's own.
   Accept the scopes.
3. If the account is supervised, Google asks the parent to approve.

Expected: `{"ok": true, "alias": "student", ...}`.

Negative control: link again choosing the school account. Expected: exit 1 `school_account`, and
nothing stored.

## 4. Check the link

```bash
uv run python -m alfabeta google check --student <id>
```

Expected: `student: ok`, exit 0.

## 5. A reminder that rings on the student's phone (US2, SC-002)

```bash
uv run python -m alfabeta calendar probe --student <id> --minutes 10
```

Within 10 minutes the student's phone shows «Prueba alfabeta · ignorar».

1. Record the date the family saw it (spec 003, FR-019).
2. Open the same event as the owner: it shows no reminder of the student's.
3. Patch the reminder of one **existing** event the same way and read it as both accounts. This is
   research R5's first open question.
4. Delete the probe event, then insert one with the same id. Record whether the API returns a
   conflict and whether reading the id shows it `cancelled`. This is R5's second open question.
5. Clean up:

   ```bash
   uv run python -m alfabeta calendar probe-clean --student <id> --event <id>
   ```

## 6. A lost link is loud (US4, SC-003)

1. Remove alfabeta from the student's Google Account, in its security settings under third-party
   access.
2. Run `google check`. Expected:
   - `student: revoked`;
   - exit 2;
   - a macOS notification;
   - `drive push` and `calendar probe` refuse with exit 2 and write nothing.
3. Repeat step 3 to link again.

## 7. Drive: migrate, then move off the mount (US3, SC-004, SC-005)

```bash
uv run python -m alfabeta drive migrate --student <id>             # dry run: read the counts
uv run python -m alfabeta drive migrate --student <id> --apply     # only if differs = 0
```

Then:

1. Move the student's base folder out of `~/Library/CloudStorage/GoogleDrive-*` to
   `[storage] base`. alfabeta refuses to run from inside the mount.
2. Run `drive push` twice. Expected: the second run reports `uploaded: 0`.

## 8. Record the shapes the tests replay (research R8)

During steps 3 to 7, save each response the tests need, with personal values replaced by invented
ones, under `tests/fixtures/google/`, each named with its call and capture date.

## 9. The token survives a week (SC-001)

The schedule of julioarguello/alfabeta#13 runs this, not a person at the keyboard: a keychain
prompt only shows when nobody is there to answer it.

Eight days or more after step 3, the scheduled `google check` still returns `ok`:

- with no new sign-in, which proves the app is published, not in Testing;
- with 0 keychain prompts.

SC-001 counts 30 consecutive scheduled runs.
