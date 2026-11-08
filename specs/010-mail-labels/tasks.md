# Tasks: Gmail labels for the notices of shared notebooks

**Input**: Design documents from `specs/010-mail-labels/`

**Tests**: written first, with invented grades, subjects and addresses only (constitution III). No test calls Google.

**Organization**: one slice, one issue (julioarguello/alfabeta#215) and one code pull request after this spec's.

## Phase 1: Setup

No setup: no dependency or folder is added.

## Phase 2: Foundational — the plan

- [x] T001 Write failing tests in `tests/test_mail.py`: the label plan of an invented grade and subjects, parents first,
  in configuration order (FR-002); the prefix from `{grade}. {subject}. {topic}` and from a pattern with other text
  around; `invalid_title_pattern` when `{grade}` or `{subject}` is missing before `{topic}` (FR-003); the query's sender
  clause and quoted prefix; the exclusion of a longer subject whose words start with a shorter one's, and none between
  unrelated subjects (FR-004)
- [x] T002 Implement `src/alfabeta/mail.py`: `LabelPlan`, `FilterSpec(subject, label, query)`, `plan(config)`,
  `SENDER_CLAUSE`, and `MailError(reason)`

## Phase 3: User Story 1 and 2 - Labels, filters and existing notices, idempotent (Priority: P1)

- [x] T003 [US1] Write failing tests in `tests/test_gmail.py` with a recording transport that holds labels, filters and
  message ids like Gmail: create missing labels parents first; reuse one that differs only in case; on 409 list again
  and reuse (FR-005); create a filter only when none adds the label; `existing` with the same query after whitespace and
  case are normalised; `differs` with another, left untouched (FR-006); list ids page by page and modify in batches of
  at most 1,000, adding the label and removing `INBOX`; counts `matched` and `in_inbox` (FR-009)
- [x] T004 [US1] Write a failing test in `tests/test_gmail.py` (SC-004): every request the adapter made in T003 is a
  method and path under `users/me` on FR-008's list; a query without the sender clause, a label removal other than `INBOX`, an added
  label outside the plan, and a message fetch each raise before a request is sent
- [x] T005 [US1] Implement `src/alfabeta/google/gmail.py`: `GmailClient(transport, token, allowed_labels)` with the
  four calls of FR-008 and their guards, `GmailError(status)`, and `apply(client, plan, modify)` returning the apply
  report
- [x] T006 [US2] Write a failing test: a second `apply` over the recorded mailbox creates 0 labels and 0 filters
  (SC-002); a subject added creates only its own

## Phase 4: User Story 3 - The school account's file (Priority: P2)

- [x] T007 [US3] Write failing tests in `tests/test_mail.py`: `mail build`'s XML parses as an Atom feed with one entry
  per subject, `hasTheWord` the plan's query, `label` the label, `shouldArchive` `true`; no `@` outside the sender
  clause (SC-005); an unwritable `--out` is `invalid_out`
- [x] T008 [US3] Implement the import file in `src/alfabeta/mail.py` with `xml.etree.ElementTree`

## Phase 5: User Story 4 and the commands (Priority: P2)

- [x] T009 [US4] Write failing CLI tests: `mail plan` and `mail build` with no keychain and no network (FR-013); `mail
  apply` with no account of role `mail`, or two, is `invalid_config`; a revoked or missing token exits 2 naming the alias
  and writes nothing; a configured account without both Gmail scopes, and a 403 from Gmail, exit 2 as `missing_scope`
  and write nothing; an error after the first write exits 2 and says to run it again; no output holds the invented
  address (FR-011, FR-012); a 401 is `revoked`. US4 scenario 3: a test in `tests/test_google_accounts.py` with two
  aliases, `student` ok and the `mail` link revoked, where `google account check` reports each on its own
- [x] T010 Add the `mail` group with `plan`, `apply` and `build` to `src/alfabeta/__main__.py`; drop the three entries
  from `PLANNED` in `tests/test_cli_naming.py`
- [x] T011 Document role `mail` in a comment of `config/template.toml` and its copy
  `specs/001-classroom-sync/contracts/config-template.toml`; add the three commands to the command table of `README.md`

**Checkpoint**: `make ci` is green; the independent review finds nothing blocking; merged and checked on `main`.

## Phase 6: The real run

- [ ] T012 Gates 1 and 2: show the operator `mail plan` in Spanish and get his confirmation; he adds the `mail` account
  (a copy of the configuration first) and links it; then `mail apply` twice, recording SC-001 and SC-002 in the issue
  without an address
- [ ] T013 Gate 3: `mail build`, the family imports it in the school account (quickstart step 5); record in the issue
  whether labels were created and existing mail moved; check SC-003 at the next shared notebook
