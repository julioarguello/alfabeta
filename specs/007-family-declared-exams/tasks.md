# Tasks: Exams the family declares that Classroom does not announce

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md),
[contracts/](contracts/), [quickstart.md](quickstart.md).

**Tests**: written first, red before the code, because the constitution's gates and this project's practice ask for a
test that can fail. Every fixture is invented (constitution III).

**Format**: `[ID] [P?] [Story] Description`. **[P]**: can run in parallel, different files. **[Story]**: US1 declare ·
US2 correct and cancel · US3 match · US4 the writer · US5 prepare with nothing declared.

Each slice is one issue, one branch from `main` and one pull request, closed by `make ci` green and, where a task says
so, a mutation that turns a test red and is restored from a copy.

## Phase 1: Setup

None: no dependency, no configuration key and no folder is added.

## Phase 2: Foundational

None shared. Slice 1 and slice 2 touch different code, and each is complete alone.

---

## Phase 3: User Story 5 — prepare with nothing declared (slice 1, P1)

**Goal**: `exam build` prints both sheets with no announcement, agenda entry or date when the family names the topics.

**Independent test**: `tests/test_exam_prep.py`, with the stand-in for `nlm`; the sheets' content on a real notebook in
T009.

- [ ] T001 [P] [US5] Extend `tests/test_exam_prep.py` for the decision table of [contracts/cli.md](contracts/cli.md): no announcement and no `--topic` still refuses `no_announcement` or `no_exam`, with a message that says to name the topics and with 0 requests to the stand-in; `--topic` with no agenda exam and `--exam` prints dated files; `--topic` with no date prints `(sin fecha)` files; `--topic` with a declared-looking agenda exam takes that exam's date; a captured announcement with `--topic` uses the announced prompts; `no_topic` and `subtopics_unnamed` are unchanged. The agenda's bytes never change (SC-009).
- [ ] T002 [P] [US5] Extend `tests/test_exam_prep.py` for an undated run: the moment `EXAMEN sin fecha`, numbering by `_number`, `exam_date: null`, `announced: false`, the pack record's `exam` empty, and a second undated run replacing the same files. The three announced prompt texts are compared with their copy at the test's start, so SC-008 fails if one changes.
- [ ] T003 [US5] Add to `skills/study-pack/prompts.md` the three sections and the `{exam_name}` row of [contracts/prompts.md](contracts/prompts.md), word for word; `tests/test_exam_prep.py`'s `test_every_placeholder_of_prompts_md_is_declared_in_its_table_and_every_declared_one_is_used` must pass.
- [ ] T004 [US5] In `src/alfabeta/exam/prompts.py`, add the three headings and a function for `{exam_name}`: `Examen del <día>` with a date, `Examen sin fecha` with none.
- [ ] T005 [US5] In `src/alfabeta/exam/prep.py`, make `Exam.day`, `.announcement` and `.announced` optional, `find_exam` take whether `--topic` was given per research R2, and `_title`, `_print`, the pack record and the returned `exam_date` handle no day per research R4. Keep `no_exam` and `no_announcement` as the reasons.
- [ ] T006 [US5] In `src/alfabeta/exam/cli.py`, choose the prompts by whether the exam has an announcement and a day, pass `{topic}` and `{exam_name}`, add `announced` to the JSON, and update the module docstring's list of refusals.
- [ ] T007 [US5] Update `specs/002-study-pack/contracts/cli.md` and `specs/002-study-pack/spec.md`: drop "not built yet" from what this slice built; add `announced` to the contract. Update the section "The day before an exam" of `skills/study-pack/SKILL.md`: how to run it with no announcement, and that the family is asked which topics.
- [ ] T008 [US5] Mutation: in a copy-backed edit, make `find_exam` proceed with no `--topic`. T001's refusal test fails; restore from the copy. Record it in the pull request.
- [ ] T009 [US5] Family step, quickstart step 1: the first real run with no announcement. Record in the slice's issue only counts: branches with a section out of top-level branches, and whether both first pages carry the sentence (SC-010). No title or date.

**Checkpoint**: both sheets for any exam, from one command.

---

## Phase 4: User Story 1 — a date on paper reaches the agenda (slice 2, P1)

**Goal**: `exam create` declares an exam and the agenda shows it, marked as the family's.

**Independent test**: `exam create` on the sandbox student, reading `agenda.md` and `agenda.json`.

- [ ] T010 [P] [US1] Extend `tests/test_decisions.py`: a declaration is `confirmed` with origin `declared-<n>` and target `subject`, `date`, `title`; `<n>` is "one more than the `declared_exam` records ever written"; `decision propose`, `decision confirm` and `decision update-target` do not take its type; the same subject and date in force writes nothing.
- [ ] T011 [P] [US1] Extend `tests/test_agenda.py`: an unmatched declared entry per the table of [data-model.md](data-model.md); the line of `agenda.md` with no link, no folder and, with no title, no empty part; «Pendiente» until any class's capture is later than the date, then «Hecho», with no dependence on today; an agenda with no declared exam byte for byte equal apart from the schema's key and version (SC-006); the output validates against both schema copies.
- [ ] T012 [P] [US1] Add tests of the command beside `tests/test_decisions.py`, in-process through `main(argv)`: JSON per [contracts/cli.md](contracts/cli.md); `no_subject`, `invalid_date` outside the school year, exit 1 and nothing written; `weekend` and `past` do not refuse; a missing base folder keeps the decision and gives `agenda_written: false`; a Classroom exam on that day gives `created: false` and no declaration; no title or date on stderr or in `data/log.jsonl`, by a planted marker (SC-007).
- [ ] T013 [US1] Add `DECLARED_EXAM` and `EXAM_MATCH` to `DecisionType` and `declared: bool = False` to `AgendaEntry` in `src/alfabeta/model.py`; take both new types out of `PROPOSABLE` in `src/alfabeta/decisions.py`.
- [ ] T014 [US1] Add `DecisionStore.declare` to `src/alfabeta/decisions.py` per research R5.
- [ ] T015 [US1] Add to `src/alfabeta/agenda.py` the declared entries, `DECLARED = "declarado por la familia"`, a `_line` that leaves out an empty title, link or folder, the list by any capture per research R10, and `_as_json`'s new key. Add `declared` to `src/alfabeta/schemas/agenda.schema.json` and `specs/001-classroom-sync/contracts/agenda.schema.json`, with the version per research R9.
- [ ] T016 [US1] Add `exam create` to `build_parser` and its handler to `src/alfabeta/__main__.py`, dispatched before `exam_cli.cmd_exam_prep`, under the lock as `_cmd_decisions`, rewriting the agenda as `_cmd_agenda`. Drop `("exam", "create")` from `PLANNED` in `tests/test_cli_naming.py`.

---

## Phase 5: User Story 2 — correct or cancel (slice 2, P1)

**Goal**: `decision update-exam` takes a declared id.

**Independent test**: declare, move, cancel and restore on the sandbox student, reading the agenda after each.

- [ ] T017 [P] [US2] Extend `tests/test_decisions.py` and `tests/test_agenda.py`: `--date` keeps the id and reads «corregido»; a correction merges with the one before; `--discard` takes it out and keeps the record; a date on a discarded exam brings it back; `--category` exits 1; a date another declared exam in force holds exits 1; a date outside the school year exits 1; each rewrites the agenda.
- [ ] T018 [US2] Extend `DecisionStore.correct` in `src/alfabeta/decisions.py` per research R6, and `_cmd_decisions` in `src/alfabeta/__main__.py` to rewrite the agenda after a declared id's correction.

---

## Phase 6: User Story 3 — one line when the teacher posts it (slice 2, P1)

**Goal**: a declared exam and the teacher's post on that day are one entry, under the declared id, for good.

**Independent test**: invented captures of the three kinds of post, on the same day, on another and with no date.

- [ ] T019 [P] [US3] Add `tests/test_declared.py`: one entry for an assignment titled as a test, a stream post and a material detected as an exam on the declared day, each with the declared id and the first match's title, link, folder, status and list (SC-003); a second post that day joins it; the teacher's move carries the entry (US3 scenario 2); every Classroom entry leaving returns the family's date and title with no link; a discard returns Classroom's entries under their own ids; a family correction after a match prevails, with a notice; a second run writes nothing (SC-005).
- [ ] T020 [P] [US3] Extend `tests/test_declared.py` for the notices of [data-model.md](data-model.md): another date up to 14 days away, at 14 and at 15; no date; both in «Pendiente» only; a cancelled exam takes no part; the family dating the detected exam joins them and the notice goes; the detected exam's own date is never changed by a declaration (SC-002). Check `agenda.json` never carries a notice.
- [ ] T021 [P] [US3] Extend `tests/test_exam_prep.py`: a declared exam matched with a detected exam whose announcement is captured finds it; unmatched with no `--topic`, it refuses `no_announcement` (SC-008).
- [ ] T022 [US3] Add `src/alfabeta/declared.py`, pure: the matches to record and to end, the merged entry and the notices, comparing days in `Europe/Madrid`. Use it from `AgendaBuilder` in `src/alfabeta/agenda.py`.
- [ ] T023 [US3] Record matches before each rebuild, under the lock, in `_cmd_agenda`, the `classroom apply` path and `exam create` in `src/alfabeta/__main__.py`, and add the fallback line of FR-013 to `_summary`. Add an instant-of-record order test so a correction before a match does not prevail over Classroom.
- [ ] T024 [US3] Update `skills/classroom-sync/SKILL.md`: how the family's «hay examen de X el D» becomes the command under the lock, the notices relayed in the summary, and how to settle them. Drop "not built yet" from what this slice built in `specs/001-classroom-sync/spec.md`, `data-model.md` and `contracts/cli.md`.
- [ ] T025 [US3] Mutation: in a copy-backed edit, disable the match in `declared.py`. T019's one-entry test fails with two entries (SC-003's control); restore from the copy. Record it in the pull request.
- [ ] T026 [US3] Quickstart steps 2 and 3 on the sandbox student, then the real student's next sync with a teacher's post if one arrives; record only counts.

**Checkpoint**: paper exams in the agenda, corrected and cancelled, never twice.

---

## Phase 7: User Story 4 — the writer (slice 3, P2)

**Goal**: a declared exam's event, warnings and the count of hand-written events.

**Needs**: slice 2, and spec 003 slices 1 to 3 (julioarguello/alfabeta#134, julioarguello/alfabeta#135, julioarguello/alfabeta#136). File names follow what spec 003 builds.

**Independent test**: `calendar replay` over an invented agenda holding a declared exam.

- [ ] T027 [P] [US4] Extend `tests/test_calendar_events.py`, `tests/test_calendar_placement.py` and `tests/test_calendar_rule.py`: a declared entry owns one `exam` event per the ownership table of `specs/003-due-date-warnings/data-model.md`, matched or not, with the same id throughout; the title with and with no family title; `Declarado por la familia` and, only with a link, `Classroom:`; session and break placement with their labels; `d7` dropped on or before the declaration's date; a cancelled one «Retirado ·» with no reminders; a date on it brings it back (SC-004).
- [ ] T028 [P] [US4] Add a test with a fake transport: the first creation of a declared exam's event reads that day's events once and counts those with no alfabeta mark and «examen» in their title; a later run reads nothing more; no such event is written or deleted; `hand_events` is a count, and dates and titles go only to `data/calendar/hand-<run>.json`. `calendar delete-legacy` still does not select a timed event.
- [ ] T029 [US4] Implement it in spec 003's `src/alfabeta/calendar/` (`events.py`, `rule.py` and the sync), and set `posted` per `specs/003-due-date-warnings/data-model.md` in `src/alfabeta/agenda.py`.
- [ ] T030 [US4] Drop "not built yet" in `specs/003-due-date-warnings/`, and run quickstart step 4. Tell the family to delete the counted events by hand; record the count only.

**Checkpoint**: the paper exam rings on the student's phone once spec 003's delivery check is on record.

---

## Dependencies

- Slice 1 (T001–T009) depends on nothing. T009 needs a real notebook and the family.
- Slice 2 (T010–T026): US1 first; US2 and US3 need US1. T021 assumes slice 1's refusals, so slice 2 follows slice 1.
- Slice 3 (T027–T030): after slice 2 and julioarguello/alfabeta#136.

## Parallel examples

- Slice 1's tests: T001 and T002 are one file, one after the other; the code T003, T004 then T005, T006.
- Slice 2's tests: T010, T011 and T012 together; T019, T020 and T021 together.
- Slice 3's tests: T027 and T028 together.

## Implementation strategy

Slice 1 alone is the first deliverable: it needs no other change, and it gives the family both sheets for an exam
that reached them on paper. Slice 2 gives them the agenda and is useful with no calendar. Slice 3 waits for the writer.

Task counts: US5 9 · US1 7 · US2 2 · US3 8 · US4 4. Total 30.
