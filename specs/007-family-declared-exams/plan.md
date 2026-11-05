# Implementation Plan: Exams the family declares that Classroom does not announce

**Branch**: `docs/183-spec-007-family-exams` | **Date**: 2026-11-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-family-declared-exams/spec.md`

## Summary

Three slices, shipped in this order. Slices 1 and 2 stand alone; the `posted` key is shared with spec 003 T004, and whichever lands second sets it for what the other added (research R9):

1. **Prepare with nothing declared** (User Story 5). `exam build` stops needing an announcement, an
   agenda entry or a date when the family names the topics. New prompts for that case; the prompts of
   an announced exam stay byte for byte.
2. **Declare, correct, match** (User Stories 1 to 3). `exam create` records a decision of the family.
   The agenda builder shows it, joined with the teacher's later post under the declared id, and the
   built `decision update-exam` corrects or cancels it.
3. **The writer treats it as an exam** (User Story 4). Small additions to spec 003's event rules, built
   after spec 003's slice 3 (julioarguello/alfabeta#136).

The design for slice 3 is written into spec 003's own documents in this pull request. Nothing here is
built by this pull request.

## Gates outside this plan

| # | Gate | Why | Tracked in |
|---|---|---|---|
| 1 | The first real `exam build` with no announcement, read by the family on paper (SC-010) | The new prompts are unmeasured, as the announced ones were before their first run | Slice 1's last task, a family step |
| 2 | Spec 003 slices 1 to 3 | Slice 3 changes a writer that does not exist yet | julioarguello/alfabeta#134, julioarguello/alfabeta#135, julioarguello/alfabeta#136 |

## Technical Context

**Language/Version**: Python 3.12, inside spec 001's package `src/alfabeta`.

**Primary Dependencies**: none new.

**Storage**:

- `data/decisions.json`: two new decision types, and `exam_correction` over a declared exam's id
  ([data-model.md](data-model.md));
- `<storage.base>/<school_year>/agenda.json` and `agenda.md`: one new key, `declared`, and an empty
  `classroom_link` for an exam no teacher post backs;
- no configuration key is added or read anew (FR-023);
- `data/study-pack.json` (the pack record): `exam` may be empty.

**Testing**: `pytest` with invented subjects, dates and titles, the stand-in for `nlm` of
`tests/test_exam_prep.py`, and the saved sandbox captures. No test calls a platform (constitution VI).
What the sheets say is judged on a real notebook only, by the family (gate 1).

**Target Platform**: macOS, the family's Mac. A later cloud run reads the same decisions (constitution
VII); this plan builds nothing for it.

**Project Type**: subcommands of spec 001's local command.

**Performance Goals**: not applicable; a handful of declared exams a term. Slice 3 adds one read of a
day's events the first time a declared exam is placed (research R11).

**Constraints**:

- an agenda with no declared exam stays byte for byte, apart from the schema's key and version (SC-006);
- an agenda's content depends only on captures and decisions, never on the day it is generated (spec
  001 FR-020);
- a second run with no change writes nothing (FR-024);
- no family title or date in a log line, an error message or a repository file (FR-022);
- the prompts of an announced exam do not change (SC-008).

**Scale/Scope**: one student, designed for several (constitution I).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Checked against constitution
2.6.0, amended by this spec to 2.7.0.

| Principle | How the plan meets it | Status |
|---|---|---|
| I. The student is configuration | The subject is a configured folder under `--student`; the code holds no subject, date or exam | Pass |
| II. Three layers | The declaration lives in the data folder, its entry in the student's folder; the repository holds invented fixtures and no new template key | Pass |
| III. Minors' data | Logs and error messages carry the opaque `declared-<n>`, never a title or date (FR-022, SC-007). The title goes only to the family's folder and calendar | Pass |
| IV. Read-only on school platforms | Nothing here reads or writes Classroom beyond the sync that exists | Pass |
| V. Idempotent, incremental | `declared-<n>` is stable, never reused and independent of the date (FR-003). A match is recorded once. A cancelled exam's record and event stay; nothing is deleted | Pass |
| VI. One isolated, tested provider | No new source. The family's declaration is a decision, not a provider. Tests use invented data | Pass |
| VII. Outputs degrade on their own | The agenda slice does not need the calendar. A missing base folder keeps the decision and says the agenda was not rewritten (FR-006) | Pass |
| VIII. `Europe/Madrid` | «The same day» is compared in `Europe/Madrid` from zone-aware values, with `dates.MADRID` | Pass |
| IX. Simplicity | No dependency, no configuration, no new surface: one command, two decision types, one agenda key, and three prompts | Pass |
| X. Schemes lead | With no announcement the theory sheet's sections are the scheme's branches, or the sources' order where no scheme exists. A fact the sources contradict is taught as they state it, and the sheet says so, unless the notes insist (FR-027); the new prompt asks for this itself, since `exam build` reads no `bloques.md`. The problems sheet stays out of X, as today | Pass |
| Technical constraints › Storage | «the date goes in each file's name» cannot hold with no date. Amended to 2.7.0 (MINOR) in this pull request | Pass, with the amendment |
| Development workflow | The spec is approved in this documentation-only pull request; each slice gets its issue and pull request | Pass |

Re-checked after Phase 1: no change. No exception needs the complexity table.

## Project Structure

### Documentation (this feature)

```text
specs/007-family-declared-exams/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── tasks.md
├── contracts/
│   ├── cli.md         # exam create; what changes in decision update-exam and exam build
│   └── prompts.md     # the texts that join skills/study-pack/prompts.md in slice 1
└── checklists/requirements.md
```

### Source Code (repository root)

```text
src/alfabeta/
├── exam/prep.py        # slice 1: find_exam, Exam with no announcement or day, names
├── exam/cli.py         # slice 1: which prompts; slice 2: exam create's dispatch stays out of here
├── exam/prompts.py     # slice 1: the new headings and {exam_name}
├── model.py            # slice 2: two DecisionType values, AgendaEntry.declared
├── decisions.py        # slice 2: declare, correct over a declared id, record matches
├── declared.py         # slice 2, new and pure: which matches to record, the notices, the merged entry
├── agenda.py           # slice 2: declared entries, the line with no link, list by any capture
├── __main__.py         # slice 2: exam create, and the agenda rewrite after it and after a correction
├── schemas/agenda.schema.json        # slice 2, with its copy in spec 001's contracts
└── calendar/           # slice 3, once spec 003 builds it
skills/study-pack/prompts.md          # slice 1
skills/study-pack/SKILL.md            # slice 1
skills/classroom-sync/SKILL.md        # slice 2
tests/test_exam_prep.py, tests/test_decisions.py, tests/test_agenda.py, tests/test_declared.py, tests/test_contracts.py
tests/test_cli_naming.py              # slice 2 drops `exam create` from PLANNED
```

**Structure Decision**: no new subpackage. `declared.py` holds the pure rules so the builder stays what
it is, a function of the state and the decisions, and the writing of a match stays with the commands
that hold the lock.

## Slices and order

| Slice | Stories | Needs | Delivers |
|---|---|---|---|
| 1 | US5 | nothing | Both sheets for any exam, from one command naming the topics |
| 2 | US1, US2, US3 | nothing | Paper exams in the agenda, corrected and cancelled, and never twice |
| 3 | US4 | slice 2 and julioarguello/alfabeta#136 | The event, its warnings, the count of hand-written events |

Slice 1 comes first because it is independent and it is what the next exam needs. Slice 2 changes the
`agenda.json` that `exam build` reads; slice 1's rules do not read the new key, so either order would
work.

## Complexity Tracking

Nothing to justify.
