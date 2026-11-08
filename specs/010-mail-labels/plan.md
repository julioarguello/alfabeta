# Implementation Plan: Gmail labels for the notices of shared notebooks

**Branch**: `docs/215-spec-010-mail-labels` | **Date**: 2026-11-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/010-mail-labels/spec.md`

## Summary

One slice: a pure planner (labels, filters, queries) from the configuration, a Gmail adapter limited to FR-008's
requests, and three commands, `mail plan`, `mail apply` and `mail build`. Then the real run: the family adds and links
the mail account, `mail apply` on the personal Gmail, and the family imports `mail build`'s file in the school account.

Nothing here is built by this pull request.

## Gates outside this plan

| # | Gate | Why | Tracked in |
|---|---|---|---|
| 1 | The operator confirms in the chat the labels and filters `mail plan` prints before the first real `mail apply` | Labels and filters are standing settings of a minor's mailbox | T012 |
| 2 | The operator adds the `mail` account to the student's configuration and links it (supervised sign-in) | A configuration change and a new authorisation are the family's | T012 |
| 3 | The family imports the filter file in the school account and reports what the import did with labels and existing mail | No route reaches that account | T013 |

## Technical Context

**Language/Version**: Python 3.12, inside `src/alfabeta`.

**Primary Dependencies**: none new; `xml.etree.ElementTree` for the import file, the existing `HttpTransport`.

**Storage**: none new. The mail link's token in the keychain as spec 004 stores every link.

**Testing**: `pytest` with invented grades, subjects and a recording transport that answers like Gmail. No test calls
Google (constitution VI). SC-004's request allowlist is a test.

**Target Platform**: macOS, the family's Mac.

**Project Type**: command-line tool.

**Performance Goals**: none; a dozen labels and filters, a few hundred notices.

**Constraints**: no address, message id or message content in any output (FR-011); the adapter refuses any request off
FR-008's list.

**Scale/Scope**: one student, two mailboxes, about a dozen subjects.

## Constitution Check

| Principle | How this holds |
|---|---|
| I. The student is configuration | Labels come from the grade and the subjects' folders; no branch names a subject or a student. |
| II. Three layers | No new key; the template documents role `mail` in a comment; the token in the keychain. |
| III. Minors' data | The family links the account itself. alfabeta never reads a message: it lists ids by a fixed query and changes labels, and a test holds it to that (FR-008). Outputs carry labels and counts only. The mailbox is the student's own Google account, a service the family uses and supervises. The stored `gmail.modify` token could read every message of a minor's mailbox; only alfabeta's adapter and its test (FR-008) keep it to labels, which is the same kind of self-limit as spec 004 FR-009a on the whole Drive. |
| IV. Read-only on the school's platforms | Gmail is not the school's learning platform, and the school account is touched by no tool: the family imports a file by hand. |
| V. Idempotent | FR-005, FR-006, FR-009: a second run creates nothing. |
| VI. One source, tested provider | One adapter, `google/gmail.py`, tested with a recording transport. |
| VII. Optional outputs | The mailbox labels are their own output; a failed mail link stops nothing else (US4). |
| VIII. Local time | No dates. |
| IX. Simplicity | No state file: Gmail holds what exists. Three commands, two of them offline. |
| X. Schemes lead | Not concerned. |

No amendment. Principle III's list of what alfabeta keeps is unchanged: it keeps no mail.

## Project Structure

### Documentation (this feature)

```text
specs/010-mail-labels/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/cli.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code

```text
src/alfabeta/mail.py                    planner: labels, prefixes, queries, filters; the import file
src/alfabeta/google/gmail.py            adapter: FR-008's requests only
src/alfabeta/__main__.py                `mail plan|apply|build`
config/template.toml                    a comment on role `mail` (+ the byte-identical copy in spec 001 contracts)
specs/004-google-connection/spec.md     FR-005 names role `mail` (this pull request)
tests/test_mail.py, tests/test_gmail.py, tests/test_cli_naming.py
README.md                               the three commands in the command table
```

## Complexity Tracking

No violation to justify. The second link of one account is one more keychain entry and one more refresh per run; it buys
that a password change leaves Calendar and Drive working (research R3).
