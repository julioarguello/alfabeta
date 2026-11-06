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
| 1 | The student's real configuration gains the keys in the same step that brings the code to the family's checkout | Old code refuses them as extra and new code refuses their absence, and the scheduled sync loads the same tables | Slice 1's last tasks, a family step |
| 2 | The first real `exam build` with rules, read on paper (SC-005) | The added text and the length limit are unmeasured | Slice 1's last task, a family step |

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

**Constraints**: a rule's text is a minor's data: only the notebook's account and Claude see it, and a run's output, record and
messages carry a fingerprint. Every prompt with empty keys stays byte-identical, and the hashes of
`test_the_announced_texts_are_as_they_were` do not change.

**Scale/Scope**: one student, about a dozen subjects; 39 lines of real configuration, most of them empty.

## Constitution Check

| Principle | How this holds |
|---|---|
| I. The student is configuration | Rules are configuration. No branch names a subject or a student; `exam build` treats a rule as opaque text. |
| II. Three layers | Template with `changeme` and generic examples in comments; real values outside the repository; a missing, extra or unset key stops as any other. |
| III. Minors' data | Text goes only to the notebook owner's account and Claude. Output and record hold level, kind and fingerprint. `Problem` names the key, never the value. |
| IV. Read-only | Nothing touches a school platform. |
| V. Idempotent sync | Sync does not read the keys (FR-013). `config check` does, so it needs gate 1. |
| VI. One source, tested provider | No new provider; the `nlm` stand-in serves. |
| VII. Optional outputs | Empty means no rule, and today's prompts. |
| VIII. Local time | No dates added. |
| IX. Simplicity | No new command, file format, parser or dependency. See below. |
| X. Schemes lead | A rule cannot reorder a scheme: FR-006 keeps what the constitution requires, and the theory prompts' scheme clause stays. |

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
src/alfabeta/sandbox.py                 its inline configuration gains the keys
src/alfabeta/exam/prompts.py            RULES heading, with_rules(), fingerprint
src/alfabeta/exam/cli.py                _sheets adds them; result and stderr name them
src/alfabeta/exam/prep.py               Sheet.rules, the piece's `rules`
skills/study-pack/prompts.md            «Standing rules — added to a prompt»
skills/study-pack/SKILL.md              reads the keys, adds the section, reports
specs/002-study-pack/spec.md, contracts/cli.md    FR-034's default; `rules` in the result
README.md, docs/explanation/study-material.md     one line each
tests/test_config.py, tests/test_exam_prep.py
```

## Complexity Tracking

No violation to justify. Three kinds per level is more keys than two, which could copy a rule for both into each: copying is
what goes stale (FR-005), and an empty key costs one line.
