# Feature Specification: Gmail labels for the notices of shared notebooks

**Feature Branch**: `docs/215-spec-010-mail-labels` (spec dir `010-mail-labels`)

**Created**: 2026-11-08

**Status**: Draft

**Input**: Operator's request (translated from Spanish), julioarguello/alfabeta#215: "in the student's own mail, where
they arrive — there are two, the school one and the personal one, in both — alfabeta should create nested labels: the
first level Alfabeta, the second the course, and below it each subject. The emails where the resources and the notebook
are shared should fall there. These mails should skip the inbox."

## Context and scope

Each topic gets a Gemini Notebook notebook, shared as viewer with every account in `[notebook] share_with` (spec 002,
constitution VII). Google mails every invited account a notice. Over a school year that is one notice per topic and per
account, a dozen subjects, in two inboxes, and they bury the mail the student has to read.

### What reaches the student's mailboxes today

| Notice | Sender | Subject | Carries the subject? | Reaches the student? |
|---|---|---|---|---|
| A notebook shared with you | `GeminiNotebook-noreply` at `google.com` (until early 2026 `NotebookLM-noreply` at `google.com`) | `<prefix>: <notebook title>`, the prefix in the recipient's language | Yes: the title is `<grade>. <Subject>. Tema NN - <title>` | Yes, every account in `share_with` |
| A request to access a notebook | the same senders | `Share Request for <notebook title>` | Yes | No: only the notebook's owner |
| A Drive item shared with you | `drive-shares-dm-noreply` at `google.com` | `<kind> shared with you: "<file name>"` | No: a file name such as «<n> · Vídeo · …» | No: alfabeta shares Drive files only with the notebook's owner (spec 005 FR-009) |

Read 2026-11-08 from one sample of each in a family account (research R1). So this spec classifies the notebook
notices. A Drive notice cannot be told apart by subject and none reaches the student; it stays out until a spec shares
Drive items with the student.

### Two accounts, two routes

- **The personal Gmail** is already linked to alfabeta's app (spec 004). It gets Gmail access through a second link of
  the same account (FR-007), and alfabeta creates the labels and filters itself and moves the notices already there.
- **The school account** cannot be linked: its administrator blocks third-party apps for users under 18 (spec 004
  FR-006). alfabeta writes a filter file in Gmail's own import format, and the family imports it by hand in that
  account's Gmail settings (FR-010).

Out of this spec:

- Classroom's own mails (from the school's teachers), Calendar notices, and any mail alfabeta did not cause.
- Reading a message. alfabeta lists message ids by a fixed query and changes their labels; it never fetches a message,
  its headers or its body (FR-008).
- Deleting a label, a filter or a message. alfabeta only adds.
- Doing the school account's import on the family's behalf in the browser (constitution III, and the extension's
  navigation ends the school session, spec 001 research R16).

## Clarifications

### Session 2026-11-08

- Q: Which shape of label: `Alfabeta/<course>/<subject>` or `Alfabeta <course>/<subject>`, and is the course the grade
  or the school year? → A: `Alfabeta/<grade>/<subject folder>`, e.g. `Alfabeta/3º ESO/Lengua` (invented example
  values). One top-level label that stays across years; the grade is what each notebook's title already says.
- Q: Filters act only on mail that arrives after them. Move the notices already in the inbox too, which needs a wider
  permission (modify messages) without reading them? → A: Yes, move them.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Notebook notices land under the subject's label and skip the inbox (Priority: P1)

**Why this priority**: it is the request.

**Independent Test**: on an invented configuration, `mail plan` lists one label per subject under the grade and one
filter per subject; on the linked account, `mail apply` creates them, and the next notebook shared with that account
lands under its subject's label, out of the inbox.

**Acceptance Scenarios**:

1. **Given** a configuration with grade `1º ESO` and subjects `Mates` and `Lengua`, **When** `mail plan` runs, **Then**
   it lists the labels `Alfabeta`, `Alfabeta/1º ESO`, `Alfabeta/1º ESO/Mates`, `Alfabeta/1º ESO/Lengua`, and for each
   subject one filter whose query names the notebook senders and the title prefix `1º ESO. Mates.` (or `Lengua.`), and
   whose action adds that label and removes the inbox.
2. **Given** a linked mail account, **When** `mail apply` runs, **Then** every planned label and filter exists in that
   mailbox, and the report says which were created and which already existed.
3. **Given** a notice already in that inbox for a notebook of `Mates`, **When** `mail apply` runs, **Then** it carries
   the label `Alfabeta/1º ESO/Mates` and is no longer in the inbox.

---

### User Story 2 - Running it again changes nothing (Priority: P1)

**Why this priority**: the family re-runs it when a subject or the grade changes; a second filter per subject would
label twice and clutter the settings.

**Independent Test**: run `mail apply` twice against a recorded mailbox.

**Acceptance Scenarios**:

1. **Given** a mailbox where a previous run created everything, **When** `mail apply` runs again, **Then** it creates no
   label and no filter, and reports them all as existing.
2. **Given** a subject added to the configuration, **When** `mail apply` runs, **Then** it creates that subject's label
   and filter only.
3. **Given** a label that already exists with the same name in another case, **When** `mail apply` runs, **Then** that
   label is reused, not duplicated.

---

### User Story 3 - The school account gets a file to import (Priority: P2)

**Why this priority**: half of the request, but it needs the family's hands, so it follows the API route.

**Independent Test**: `mail build --out <file>` on an invented configuration, then the file parsed as Gmail's filter
export format.

**Acceptance Scenarios**:

1. **Given** the configuration, **When** `mail build --out <file>` runs, **Then** the file holds one filter per subject
   with the same query, label and archive action as the plan, and nothing else: no address of the student.
2. **Given** that file imported in the school account with "apply to existing mail" ticked, **When** the family looks
   at the labels, **Then** the notices of each subject are under its label and out of the inbox (measured once, quickstart
   step 5).

---

### User Story 4 - A lost or narrow Gmail link is said, and nothing else breaks (Priority: P2)

**Why this priority**: a password change on the student's Gmail revokes every token that holds a Gmail scope (research
R3); it must not take the calendar and Drive with it.

**Independent Test**: revoke the mail link, run `google account check` and `mail apply`; then run a sync.

**Acceptance Scenarios**:

1. **Given** a revoked mail link, **When** `mail apply` runs, **Then** it changes nothing, exits 2, and says which alias
   to link again.
2. **Given** a mail link that lacks a scope `mail apply` needs, **When** it runs, **Then** it exits 2 with reason
   `missing_scope` and says to link that alias again.
3. **Given** a revoked mail link, **When** a sync runs, **Then** the student's link (Calendar, Drive) still works, and the
   failed mail link shows in `google account check` like any other (spec 004 FR-013, FR-014).

---

### Edge Cases

- **Two subjects where one's name starts the other's** (invented: `Mates` and `Mates Avanzadas`): Gmail matches a quoted
  phrase ignoring punctuation, so `1º ESO. Mates.` also matches `1º ESO. Mates Avanzadas. …`. The shorter subject's
  query excludes the longer one's prefix (FR-004).
- **A notice in another language**: the subject's prefix is localised by Google, the title is not; the query matches
  the title only.
- **The grade changes** (a new school year): the new grade's labels and filters are added; last year's stay, still
  holding last year's notices. Nothing is deleted.
- **A filter whose query Gmail stored differently**: a filter that adds an alfabeta label but whose query differs from
  the plan is reported as `differs` and left alone, never deleted or duplicated (FR-006).
- **A subject removed from the configuration**: its label and filter stay; the report does not list them.
- **More than 500 matching notices**: they are listed page by page and moved in batches of at most 1,000.
- **The notebook's title pattern does not start with the grade and the subject**: `mail plan` refuses, since no query
  can tell the subjects apart (FR-003).

## Requirements *(mandatory)*

### Functional Requirements

**What is classified**

- **FR-001**: alfabeta MUST classify the notices of a notebook shared with the student: mail from the notebook senders
  of research R1 whose subject holds the title prefix of one configured subject. Nothing else.
- **FR-002**: Labels MUST be `Alfabeta`, `Alfabeta/<grade>` and `Alfabeta/<grade>/<subject folder>`, with the grade of
  `[student] grade_level` and each `[[subjects]] folder`, in that nesting (Gmail nests on `/`). One label per subject.
- **FR-003**: A subject's title prefix MUST come from `[notebook] title_pattern`, cut before `{topic}` and filled with the
  grade and the subject's folder (`{grade}. {subject}. {topic}` gives `<grade>. <subject>.`). A pattern that does not
  hold `{grade}` and `{subject}` before `{topic}` is refused as `invalid_title_pattern`.
- **FR-004**: Each subject MUST have one filter. Its query is `from:(<senders joined by OR>) subject:"<prefix>"`, plus
  `-subject:"<prefix of S>"` for every other subject S whose prefix starts with this one's words. Its action adds the
  subject's label and removes `INBOX`; nothing else (no mark as read, no category, no forward).

**The personal Gmail, through the API**

- **FR-005**: `mail apply` MUST create the labels that are missing, parents first, matching existing labels by name
  without regard to case; a label Gmail reports as existing (409) is read again and reused.
- **FR-006**: `mail apply` MUST create a subject's filter only when no filter adds that subject's label. A filter that
  adds it with the same query (whitespace collapsed, case ignored) is `existing`; with another query it is `differs`, is
  reported, and is left as it is.
- **FR-007**: The Gmail access MUST be a separate link of the student's Gmail, with role `mail`, its own alias and its
  own token (amends spec 004 FR-005). Its scopes are `gmail.settings.basic` (filters), `gmail.modify` (labels, and the
  labels of existing notices), `openid` and `email`; nothing else. Linking it is spec 004's `google account link`; the
  link is checked and kept in use by `google account check` like any other (spec 004 FR-013, FR-015).
- **FR-008**: The Gmail adapter MUST call only: list and create labels; list and create filters; list message ids with
  a query that starts with the fixed sender clause of FR-004; and modify those messages' labels, adding only an alfabeta
  label and removing only `INBOX`. It never fetches a message, a thread, an attachment or a history, and a test asserts
  every request it makes against that list (as spec 004 FR-009a does for Drive).
- **FR-009**: When the mail link holds `gmail.modify`, `mail apply` MUST also label the notices already in the mailbox
  (spam and trash excluded) that match each subject's query, and take them out of the inbox. The report gives, per
  subject, how many matched and how many were in the inbox. Without that scope it skips this step and says so.

**The school account, by hand**

- **FR-010**: `mail build --out <file>` MUST write Gmail's filter export format (an Atom feed, one entry per subject,
  properties `hasTheWord` = the query, `label` = the label, `shouldArchive` = `true`) with the same filters as the plan.
  It needs no link and touches no account. The family imports it in the school account's Gmail settings (quickstart).

**Output and failure**

- **FR-011**: No command MUST print, log or write an address of the student or the content of a message. The output
  names labels, subjects and counts.
- **FR-012**: A link that fails (`revoked`, `expired`, `no_token`) or lacks a scope (`missing_scope`, also from a 403 the
  API answers) MUST stop `mail apply` before it writes anything, with exit 2 and the alias to link again. A failure
  after the first write reports what was written.
- **FR-013**: `mail plan` and `mail build` MUST work with no network and no link.

### Key Entities

- **Label plan**: the ordered label names of FR-002.
- **Filter plan**: per subject, its label and query (FR-004).
- **Mail link**: a linked account with role `mail` (spec 004 data model, LinkedAccount).
- **Apply report**: per label `created` or `existing`; per filter `created`, `existing` or `differs`; per subject
  `matched` and `in_inbox`, or `skipped` with its reason.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After `mail apply` on the personal Gmail, the inbox holds 0 notebook notices of a configured subject, and
  each such notice carries exactly its subject's label.
- **SC-002**: A second `mail apply` creates 0 labels and 0 filters.
- **SC-003**: The next notebook shared after the run lands under its label with no one acting, out of the inbox, in both
  accounts (the school account after its import).
- **SC-004**: Every request the adapter makes in the tests is on FR-008's list; a test planting a message fetch fails.
- **SC-005**: A search of the outputs, the log and the filter file for the student's addresses finds nothing.

## Assumptions

- The student's personal Gmail is supervised; the operator approves the second link with his own sign-in, as for spec
  004. Whether the supervision allows the restricted Gmail scopes is unknown until the link (quickstart step 2).
- The app stays under Google's personal-use allowance (spec 004 FR-003): restricted scopes show the unverified-app
  screen and need no verification.
- Gmail's filter import is open to the school account's users. Whether it creates a missing label, and offers to apply
  the filters to existing mail, is measured on the first import (quickstart step 5).

## Dependencies

- Spec 004: the app, `google account link`, the keychain, `google account check`.
- Spec 002 and the notebook skills: the notebook titles and `share_with`.
- The operator: to add the `mail` account to the student's configuration, link it, and import the file in the school
  account.
