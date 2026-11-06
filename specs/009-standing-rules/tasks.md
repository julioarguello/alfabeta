# Tasks: Standing rules per subject and per student

**Input**: Design documents from `specs/009-standing-rules/`

**Tests**: written first, with invented subjects and rules only (constitution III). No test calls a platform.

**Organization**: two slices, each with its own issue and pull request. Slice 1 is User Stories 1 to 3; slice 2 is User Story 4.

## Phase 1: Setup

No setup: no dependency, folder or command is added.

## Phase 2: Foundational (slice 1) — the keys

- [x] T001 Write failing tests in `tests/test_config.py`: `rules_both`, `rules_problems` and `rules_theory` are required strings in `[student]` and in each `[[subjects]]`; empty is valid; a missing, extra, non-string or `changeme` value is a `Problem` naming the key and never the value; `StudentConfig.rules(folder)` returns the stripped values of the student's level and of that subject alone, and spaces only count as empty; a literal string holding quotes, `\frac` and a line break arrives as written; `repr()` of the value holds no rule text
- [x] T002 Add the six keys to `config/template.toml`, naming spec 009 in its header, with `changeme` values, generic and invented example rules as literal strings in comments, among them a subject of calculation and a subject of languages, a comment saying why literal strings, and a warning that the notebook keeps its prompts and may show them to the accounts it is shared with; copy it byte for byte to `specs/001-classroom-sync/contracts/config-template.toml` (`tests/test_contracts.py` compares them)
- [x] T003 Add the empty keys to the inline configurations in `src/alfabeta/sandbox.py`, `tests/conftest.py`, `tests/test_config.py`, `tests/test_notes_cli.py`, `tests/test_guardrail.py` and any other test that writes a configuration
- [x] T004 Implement a frozen `Rules` with `repr=False` and `StudentConfig.rules(folder)` in `src/alfabeta/config.py`, reading through `_str` with string-literal paths (`tests/test_template_covers_reads.py`) and `allow_empty=True`; leave `model.Subject` as it is (research R8)
- [x] T005 Write a failing test in `tests/test_guardrail.py` with a planted multi-line rule, then add the three key names to `_IDENTIFYING_KEYS` in `src/alfabeta/guardrail.py`, which matches leaf names, splitting such a value into lines with a minimum length, since the scan matches per line and a whole multi-line value would never hit

**Checkpoint**: `config check` knows the keys, the guardrail defends them, and nothing uses them yet.

## Phase 3: User Story 1 - The exam sheets follow the subject and the student (Priority: P1)

**Goal**: `exam build` adds the rules that speak to each sheet.

**Independent Test**: with invented rules for one subject and for the student, build that subject's exam and another's, and read the prompts sent.

- [x] T006 [US1] Write failing tests in `tests/test_exam_prep.py`: with empty keys every prompt, announced or not, is byte-identical to the fill of its template and `test_the_announced_texts_are_as_they_were` still passes (SC-001); a problems rule reaches the problems sheet and not the theory sheet, and a theory rule the reverse; `both` reaches both; the order is the student's `both`, the student's kind, the subject's `both`, the subject's kind; another subject's rules never appear (SC-002); start notes gain nothing; a rule holding braces reaches the prompt as written; over two topics each sheet carries the same text; the added text pins its own hash and holds "sin citarlas" and each exception of FR-006; a renamed section is `invalid_prompt` with empty keys too
- [x] T007 [US1] Write a failing test in `tests/test_exam_prep.py`: `{rules}` over 2,000 characters on either sheet exits with code 1 and reason `rules_too_long`, its message names the sheet and the characters over and no word of the rule, and the notebook is asked for nothing; exactly 2,000 passes
- [x] T008 [US1] Add the section «Standing rules — added to a prompt» with the text of `specs/009-standing-rules/contracts/prompts.md` to `skills/study-pack/prompts.md`, its row to the placeholder table, its heading to the note on exact headings, and an exception to "a prompt that still holds a `{` is a bug" for a rule's or an announcement's own braces
- [x] T009 [US1] Implement in `src/alfabeta/exam/prompts.py` the heading constant, the 2,000-character limit on `{rules}`, and a function that always reads the section, builds the added text for a sheet's kind from a `Rules`, returns nothing when no level has text, fills `{rules}` once, and appends it with one space after the right-stripped prompt
- [x] T010 [US1] Use it in `_sheets` of `src/alfabeta/exam/cli.py`, raising `Refusal("rules_too_long", …)` on the path already caught before the notebook is asked

**Checkpoint**: the prompts carry the rules, and `make ci` is green.

## Phase 4: User Story 2 - A run says which rules it relied on (Priority: P1)

**Goal**: the result and the record name what was used, never its text.

**Independent Test**: build with rules, without rules and after changing one; read the output and the pack's record.

- [x] T011 [US2] Write failing tests in `tests/test_exam_prep.py`, updating the exact result of `test_both_sheets_are_asked_titled_and_printed_into_exam`: the result's `rules` lists per sheet `sheet`, `used` and an 8-character `fingerprint`, and is `[]` with none; a changed rule changes the fingerprint and touches no earlier piece (FR-012); each exam piece in `data/study-pack.json` holds `rules`, that `used` and `fingerprint` or `null`; a word planted in every rule appears nowhere in stdout, stderr or the record (SC-003); stderr has the lines of `specs/009-standing-rules/contracts/cli.md`
- [x] T012 [US2] Add the fingerprint (first 8 hexadecimal characters of the SHA-256 of the added text) and the `used` names to `src/alfabeta/exam/prompts.py`, carry them on `Sheet` in `src/alfabeta/exam/prep.py`, set `repr=False` on `Sheet.prompt`, which now holds rules, and write `rules` in the piece's record
- [x] T013 [US2] In `src/alfabeta/exam/cli.py`, print the stderr line before the notebook is asked, and emit top-level `rules` in the one JSON at the end

**Checkpoint**: a run shows what it used.

## Phase 5: User Story 3 - The study pack follows the same rules (Priority: P2)

**Goal**: the skill reads the same keys for its prompts and its judgement steps.

**Independent Test**: follow the skill on an invented topic with invented rules; the practice sheet's prompt carries them, and the report names them.

- [x] T014 [US3] In `skills/study-pack/SKILL.md`, add the keys to the configuration table, and say when to read them; which piece takes which kind, with guide 0 and the built-in study guide taking none and the rules shaping `{plan}` instead (`specs/009-standing-rules/contracts/prompts.md`); that a video's focus takes what fits; the 2,000-character limit; that the limits of FR-006 bind its judgement steps; that a standing fact in a rule is not asked again, while which subtopics an exam covers and a question on the notes still are; that a rule is never copied into `bloques.md` or the topic's folder, which mirrors to other Drives; that its report names levels and kinds and never the text; and that a piece's status output, which can hold its prompt, is never quoted
- [x] T015 [US3] Add a line to `skills/classroom-sync/SKILL.md` and `skills/sciencebits-a-notebooklm/SKILL.md` saying they ignore the rule keys, and a test in `tests/test_config.py` that only `src/alfabeta/exam/cli.py` calls `rules(` (FR-013)
- [x] T016 [US3] Write a test, in the file that holds the skill's text checks or `tests/test_exam_prep.py`, that `skills/study-pack/SKILL.md` names the three keys and the section's exact heading, so a rename fails

**Checkpoint**: the study pack follows the rules.

## Phase 6: Polish (slice 1)

- [x] T017 [P] Update `specs/002-study-pack/spec.md` (FR-029: the text added after filling; FR-034: "as few patterns as possible" is the default a subject rule may change) and `specs/002-study-pack/contracts/cli.md` (`rules`, `rules_too_long`)
- [x] T018 [P] Add one line each to `README.md` and `docs/explanation/study-material.md`: what a rule is and where it lives
- [x] T019 Run `make ci`, read its result, and confirm that no real rule is in the diff
- [x] T020 After the merge, outside any time in the student's `[schedule]`, and with no pull in the family's checkout between the merge and this step, run the sequence of research R9 on that checkout (`tools.repository`): `lock take`, stopping on `lock_busy`; copy `config.toml` with user-only permissions; `notebook agent uninstall`; add the empty keys through a copy that parses and keeps every other value; `git pull --ff-only`; `config check`; on failure restore the copy and the previous commit; `notebook agent install` only if the uninstall reported `removed`; `lock release`; report the outcome by key, never by value (plan gate 1)
- [ ] T021 With the family's confirmation, write the real rules, as literal strings through a checked copy, none describing a difficulty yet; run the first real `exam build` with rules; read the printed sheets; make a quiz with an invented rule; look for the prompt on the sheet and on the quiz as a viewer of the notebook; and record the finding with no personal data (SC-005, plan gate 2)

## Phase 7: User Story 4 - The family gives a rule once (Priority: P2, slice 2)

**Goal**: a rule said in the chat lands in its key, after confirmation.

**Independent Test**: state an invented rule in a session, confirm it, and check that it is in the student's configuration, that nothing reached the repository, and that a later run uses it.

- [ ] T022 [US4] In `skills/study-pack/SKILL.md`, turn "Never create the configuration or write to it" into that rule with one exception: a rule the family confirmed, in its one key, after showing them the text, level and kind; say that an exam sheet's new numbers are unchecked (spec 002 FR-036) and point such a rule to the practice sheet
- [ ] T023 [US4] In `skills/study-pack/SKILL.md`, give the write's route (FR-011): a literal string in a copy; parse it; compare every other value; run `config check` on it; replace the file atomically only then, with the original left in place on any failure; name the key in the report and never the text

## Dependencies & Execution Order

- Phase 2 blocks everything. US1 comes before US2, which reports what US1 adds. US3 needs only Phase 2 and T008.
- T020 and T021 come after slice 1's merge, in that order.
- Slice 2 needs only the keys, so it can wait, and the family can edit a key by hand meanwhile.

## Parallel Opportunities

T017 and T018 touch different files from each other. Within a story, tests come first and the code depends on them, so nothing else runs in parallel.

## Implementation Strategy

Slice 1 alone gives what an exam needs. Stop after T021 to judge the rules on paper before anything else, and prepare no second subject on rules that have not been read.
