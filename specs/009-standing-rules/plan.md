# Implementation Plan: Standing rules per subject and per student

**Branch**: `docs/187-spec-009-standing-rules` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/009-standing-rules/spec.md`

## Summary

Two slices, each able to ship alone in this order:

1. **The rules reach the prompts** (User Stories 1 to 3). Six kinds of new configuration key, `exam build` adds them after
   the prompt it has filled and reports what it added, and the study-pack skill reads the same keys.
2. **The family gives a rule once** (User Story 4). An instruction to the skill, with no code: it proposes a rule, the family
   confirms, and it writes that key alone. Until then the family edits the key by hand.

Nothing here is built by this pull request.

## Gates outside this plan

| # | Gate | Why | Tracked in |
|---|---|---|---|
| 1 | The student's real configuration gains the keys in the same sequence that brings the code to the family's checkout (research R9); no pull in that checkout between slice 1's merge and that sequence | Old code refuses them as extra and new code refuses their absence, in the scheduled sync and in the refresh agent, which fails silently | Slice 1, T020 |
| 2 | The first real `exam build` with rules, read on paper, with a viewer's view of the notebook checked (SC-005) | The added text and the length limit are unmeasured, and the notebook keeps the prompt with the piece | Slice 1, T021 |

## Technical Context

**Language/Version**: Python 3.12, inside spec 001's package `src/alfabeta`.

**Primary Dependencies**: none new; `hashlib` for the fingerprint.

**Storage**:

- `~/.alfabeta/<student>/config.toml`: six keys, [data-model.md](data-model.md);
- `data/study-pack.json` (the pack record): one new key per exam sheet, `rules`;
- `skills/study-pack/prompts.md`: one new section, found by its exact heading.

**Testing**: `pytest` with invented subjects and rules and the stand-in for `nlm` of `tests/test_exam_prep.py`. No test calls a
platform (constitution VI). What a rule does to a sheet is judged on a real notebook only (gate 2).

**Target Platform**: macOS, the family's Mac.

**Project Type**: command-line tool plus skills.

**Performance Goals**: none; a run gains a few reads of its own configuration.

**Constraints**: a rule's text is a minor's data: it goes to the notebook's account and Claude, the notebook may show it to the
accounts it is shared with (gate 2), and a run's output, record and messages carry a fingerprint. Every prompt with empty keys stays byte-identical, and the hashes of
`test_the_announced_texts_are_as_they_were` do not change.

**Scale/Scope**: one student, about a dozen subjects; 39 lines of real configuration, most of them empty.

## Constitution Check

| Principle | How this holds |
|---|---|
| I. The student is configuration | Rules are configuration. No branch names a subject or a student; `exam build` treats a rule as opaque text. |
| II. Three layers | Template with `changeme` and generic examples in comments; real values outside the repository; a missing, extra or unset key stops as any other. |
| III. Minors' data | Text goes only to the notebook's account and Claude, and whether its viewers can read a stored prompt is gate 2. Output and record hold level, kind and fingerprint. `Problem` names the key, never the value. The guardrail treats the keys as identifying. |
| IV. Read-only | Nothing touches a school platform. |
| V. Idempotent sync | No sync command reads the keys, and its skill ignores them (FR-013). `config check` validates them, so it needs gate 1. |
| VI. One source, tested provider | No new provider; the `nlm` stand-in serves. |
| VII. Optional outputs | Empty means no rule, and today's prompts. |
| VIII. Local time | No dates added. |
| IX. Simplicity | No new command, file format, parser or dependency. See below. |
| X. Schemes lead | The added text names the schemes among what no rule overrides (FR-006). Whether the notebook obeys is gate 2. |

No amendment: "Student configuration" in II already covers per-student parameters, and Technical constraints › Configuration
already gives template mirroring.

## Project Structure

### Documentation (this feature)

```text
specs/009-standing-rules/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   └── prompts.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (slice 1)

```text
config/template.toml                    six keys, generic examples in comments
specs/001-classroom-sync/contracts/config-template.toml    byte-identical copy (test_contracts)
src/alfabeta/config.py                  StudentConfig.rules(folder), Rules
src/alfabeta/guardrail.py               the rule keys are identifying, matched line by line
src/alfabeta/sandbox.py                 its inline configuration gains the keys
src/alfabeta/exam/prompts.py            RULES heading, with_rules(), fingerprint
src/alfabeta/exam/cli.py                _sheets adds them; result and stderr name them
src/alfabeta/exam/prep.py               Sheet.rules, the piece's `rules`
skills/study-pack/prompts.md            «Standing rules — added to a prompt»
skills/study-pack/SKILL.md              reads the keys, adds the section, reports
skills/classroom-sync/SKILL.md, skills/sciencebits-a-notebooklm/SKILL.md    ignore the keys
specs/002-study-pack/spec.md, contracts/cli.md    FR-029, FR-034; `rules` in the result
README.md, docs/explanation/study-material.md     one line each
tests/test_config.py, tests/test_exam_prep.py, tests/test_guardrail.py, tests/conftest.py, tests/test_notes_cli.py
```

## Complexity Tracking

No violation to justify. Three kinds per level is more keys than two, which could copy a rule for both into each: copying is
what goes stale (FR-005), and an empty key costs one line.
