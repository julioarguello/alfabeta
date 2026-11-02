# Quickstart: proving the Classroom read on the Mac (spec 006)

The live proof of each slice of the [plan](plan.md#vertical-slices-each-leaves-the-system-demonstrable).
Commands and outputs are in [contracts/cli.md](contracts/cli.md); fields in
[data-model.md](data-model.md). Each step records its date and result in research.md, never a
name, an address or a Classroom title.

## Prerequisites

- Spikes S7, S8 and S9 passed and recorded ([research.md](research.md#spikes-before-the-build)).
- `[classroom] profile_read = true` and `notice_account` set in the student's configuration;
  `config check --student <id>` clean.
- For steps 6 to 8: the `family` account linked with `google account link` (spec 004 as amended),
  and Chrome Remote Desktop to the Mac set up on the family's phone.

## Steps

1. **Offline** (slice 1, anyone): `make ci`. The guard test reports the planted press, form link
   and write call blocked and counted, and the fake server received none of them.
2. **A read with the app closed** (slice 2; family sign-in): the family signs the school account
   in once (step 4, or by hand in the window S7 left). Close the Claude app, start
   `python -m alfabeta classroom capture --student <id>` from a terminal after a two-minute delay,
   and lock the screen before it starts. Expected: exit 0, every class `read`,
   `blocked.calls` and `blocked.presses` counted, no window seen on unlocking.
3. **Compared and idempotent** (slice 2; the family's usual run the same day): compare the capture
   with the extractor's capture of the same classes (ids, types, topics, statuses, attachments,
   stream posts; SC-005). Then `classroom plan` and `classroom apply` twice: the second writes
   nothing (SC-005, constitution V).
4. **Sign-in at the Mac** (slice 3; family): with the session expired,
   `python -m alfabeta classroom sign-in --student <id>`. A Chrome window opens on Google's sign-in;
   the family signs in; the window closes by itself; output `signed_in`, `ended_by: address`.
   Repeat with a different Google account: `session_expired`, `other_account: true`. Repeat and do
   nothing: `timeout` after `wait_minutes`.
5. **The whole read** (slice 4): `python -m alfabeta classroom refresh --student <id>` with the app
   closed; while it waits for the sign-in, run it again: `lock_busy` and the window comes to the
   front (FR-017). One log line with `started_by: command`.
6. **The notices** (slice 5; family phone): repeat step 5 with the session expired. The notice
   reaches the phone within a minute and carries one link (research R10); the result email arrives
   when the read ends. Neither names the student, an address or a title.
7. **Scheduled, screen locked** (slice 6; family): `python -m alfabeta classroom agent install
   --student <id>` with a `[schedule]` time a few minutes ahead; close the app, lock the screen,
   leave the Mac. The read starts on time, the notice arrives, the family signs in through the
   remote view, the topic folders update. Then `classroom agent uninstall`.
8. **Ten school days from the phone** (slice 7; family): SC-001 and SC-002 — at least 9 of 10
   scheduled reads update the folders with nobody at the Mac; the median from opening the link to
   the end of the sign-in under 2 minutes.
