# Research: Gmail labels for the notices of shared notebooks

## R1 — Which notices, from whom, with what subject

- **Read**: 2026-11-08, Gmail search in a family account (not the student's), one message of each kind, sender and
  subject only.
  - A notebook shared: sender `GeminiNotebook-noreply` at `google.com`, display name `<owner> (via Gemini Notebook)`, subject
    `Notebook shared with you: <notebook title>`, dated 2026-10-26, the title being one of alfabeta's
    (`<grade>. <Subject>. Tema NN - <title>`).
  - A request for access: the same sender, subject `Share Request for <notebook title>`, sent to the owner only.
  - The same notices before the product's rename (February 2026): sender `NotebookLM-noreply` at `google.com`, same subjects.
  - A Drive item: sender `drive-shares-dm-noreply` at `google.com`, display name `<sharer> (vía Google Drive)`, subject
    `Elemento compartido contigo: "<file name>"`; in English `Document shared with you: "<file name>"`.
- **Code read**: the only Drive share in `src/` is `share_reader`, called by `notes/setup.py` with the notebook owner's
  address (spec 005 FR-009). Notebooks are shared by the skills with `nlm share invite … --role viewer` to every account
  in `[notebook] share_with` (`skills/sciencebits-a-notebooklm/SKILL.md`, study-pack).
- **Decision**: classify only the notebook notices, by sender and title. Senders: `GeminiNotebook-noreply` at `google.com`,
  `NotebookLM-noreply` at `google.com`.
- **Rejected**: matching the subject's English prefix ("Notebook shared with you"): Google writes it in the recipient's
  language, while the sender and the title do not change. Drive notices: no subject in them, and none reaches the
  student.

## R2 — The query, measured

- **Measured** 2026-11-08 in the same account with the one real notice of R1:
  `from:<sender> subject:"<grade>. <Subject>."` matched it; the same query with another grade
  (one grade up) or another subject matched nothing. So `º` is kept as part of the grade's token, and the quoted phrase
  keeps the subject apart.
- Gmail ignores punctuation inside a quoted phrase, so the phrase of a subject whose name starts another's (invented:
  `Mates` and `Mates Avanzadas`) also matches the longer one. **Decision**: exclude, in the shorter one's query, every
  longer prefix that starts with its words (FR-004). Not measured: no such pair exists in a real configuration yet; a unit
  test covers the query text.
- A filter's `criteria.query` takes the search box's syntax (Gmail API `users.settings.filters` reference). Whether
  Gmail stores it unchanged is measured by the second real `mail apply` (SC-002): if it normalises it, FR-006 reports
  `differs` instead of duplicating, and a follow-up adjusts the comparison.

## R3 — Scopes and a separate link

- Gmail API scopes (Google's table, read 2026-11-08): `gmail.labels` non-sensitive; `gmail.settings.basic` and
  `gmail.modify` restricted. Filters need `gmail.settings.basic`. Listing message ids by query and changing their labels
  need `gmail.modify` (`gmail.metadata` refuses a query). `gmail.modify` also covers labels, so `gmail.labels` is not
  asked for.
- Restricted scopes under the personal-use allowance show the unverified-app screen and need no verification (spec 004
  FR-003); the app already holds the restricted `drive`.
- Google's OAuth documentation lists, among the reasons a refresh token stops working, "the user changed passwords and
  the refresh token contains Gmail scopes". **Decision**: a second link of the same Gmail, role `mail`, alias of the
  family's choosing, its own token. A password change then takes only the mail link; Calendar and Drive keep working.
  Spec 004 already allows two tokens of one account and one client (its edge case on spec 005's cloud link).
- **Rejected**: adding the Gmail scopes to the student's link (one token, but a password change would stop the
  calendar's reminders and the Drive upload); linking for one run and revoking after (one fewer standing secret, but a
  supervised sign-in every time a subject changes, and spec 004's check and keep-alive already cover a standing link).

## R4 — The school account

- Spec 004 FR-006 refuses it: the school blocks unconfigured third-party apps for under-18 users.
- Gmail's settings export and import filters as an Atom feed: `<entry>` with `<category term='filter'/>` and
  `<apps:property name='…' value='…'/>` for `from`, `subject`, `hasTheWord`, `label`, `shouldArchive` and others
  (namespace `http://schemas.google.com/apps/2006`). Seen in exports of personal accounts and in open-source tools that
  write them (gmailctl). **Decision**: `mail build` writes that file with `hasTheWord` holding the whole query, so both
  accounts get the same filter.
- Not established: whether the import creates a missing label (one public report says nested labels need their parents),
  and whether it offers to apply to existing mail. The quickstart lists the labels to create by hand if the import
  leaves them out, and step 5 records what happened.
- **Rejected**: doing the import through the browser on the family's behalf (constitution III; the extension's navigation
  ends the school session, spec 001 research R16); forwarding the school account's notices to the personal Gmail
  (another standing rule in a minor's school account, and the student would still see them twice).

## R5 — Idempotence without an id of our own

- Gmail labels have no client-chosen id; names are unique without regard to case, and creating an existing name answers
  409. **Decision**: list, match by case-folded name, create what is missing parents first, and on 409 list again.
- Filters cannot be updated, only created and deleted, and carry no description. **Decision**: a filter is the subject's
  when its action adds the subject's label id. Same query: `existing`; another query: `differs`, left alone (FR-006).
  alfabeta never deletes, so a family's hand-made filter on the same label is never lost.
- Existing notices: `messages.list` (≤ 500 ids a page) with the subject's query, then `messages.batchModify` (≤ 1,000
  ids a call) adding the label and removing `INBOX`, which is a no-op on a notice already done. A second list with
  `in:inbox` added, made before the change, gives the count that leaves the inbox.
