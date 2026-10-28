# Tasks: Due-date warnings placed on the student's timetable

**Input**: Design documents from `specs/003-due-date-warnings/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: included. Constitution VI asks for tests of every module and FR-021 for fixtures at both
daylight-saving changes. Every test uses invented agendas, an invented timetable, a frozen clock and
a fake calendar; none calls Google. The real-data success criteria are quickstart steps.

**Depends on**: spec 001's agenda (`src/alfabeta/agenda.py`, julioarguello/alfabeta#8) and
configuration loader; spec 004's `HttpTransport`, `CalendarClient`, `ScopedDrive` and linked
accounts. **Gates** ([plan](plan.md#gates-outside-this-plan)): building starts after gate 1, the
delivery proof (spec 004 T021); Phase 7 needs gate 2 (julioarguello/alfabeta#120); Phase 8 needs
gate 3 (julioarguello/alfabeta#13).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1 short work · US2 long work · US3 no flood · US4 exams · US5 "for Thursday" ·
  US6 delivery seen · US7 the list and the facts

## Slices and issues

Each slice of the [plan](plan.md#vertical-slices-each-leaves-the-system-demonstrable) is one issue
and one pull request.

| Slice | Phases | Tasks |
|---|---|---|
| 1. Facts on the timetable | 1, 2, 3 | T001–T019 |
| 2. Warnings by the lead-time rule | 4 | T020–T028 |
| 3. Exams in their class, announced ahead | 5 | T029–T031 |
| 4. "For Thursday" read from the title | 6 | T032–T034 |
| 5. In every run, with delivery on record | 7 | T035–T038 |
| 6. Warnings switched on | 8 | T039 |

---

## Phase 1: Setup (slice 1)

- [ ] T001 Add the keys of `specs/003-due-date-warnings/contracts/config-template.toml` to `config/template.toml`: in `[calendar]`, `home_slot`, `break_start`, `break_end` (`"changeme"`, e.g. `"16:00"`, `"10:00"`, `"10:25"`) and `warnings = false`; a `[[timetable]]` array with `weekday`, `start`, `end`, `subject`. Add `"timetable"` to `TABLES["calendar"]` in `src/alfabeta/__main__.py`. Run `tests/test_template_covers_reads.py`.
- [ ] T002 [P] Create `src/alfabeta/calendar/__init__.py` and `tests/calendar_fakes.py`: an invented agenda builder (subjects «Mates», «Ciencias», «Euskera», invented titles and ids), an invented timetable, a frozen `Clock`, and `FakeCalendar`, an in-memory calendar that serves `list_owned`, `get`, `insert`, `update` and `delete`, keeps deleted events as `cancelled`, answers 409 to an insert of a cancelled id, and can fail one chosen id with a 500.

---

## Phase 2: Foundational (slice 1; blocks every story)

- [ ] T003 [P] Extend `tests/test_agenda.py`: every entry carries `posted`, the item's posting date as `YYYY-MM-DD`; a detected exam carries its origin item's; the document's `version` is 2; the output validates against both schema copies. Extend `tests/test_contracts.py` so the two copies of `agenda.schema.json` stay identical.
- [ ] T004 Implement `posted` (research R1): `AgendaEntry.posted: dt.date` in `src/alfabeta/model.py`, set in `src/alfabeta/agenda.py` (`_entry`, `_detected`, `_as_json`), `VERSION = 2`. Add `"posted": {"type": "string", "format": "date"}` to `required` and `properties`, and `"version": {"const": 2}`, in `specs/001-classroom-sync/contracts/agenda.schema.json` and `src/alfabeta/schemas/agenda.schema.json`. Add the `posted` row to «Agenda entry» in `specs/001-classroom-sync/data-model.md`. `tests/test_exam_prep.py` must pass unchanged.
- [ ] T005 [P] Write `tests/test_calendar_timetable.py`, configuration part. Each is a problem named by its key, never its value: a weekday outside `monday`…`sunday`; a time not `HH:MM`; `end` not after `start`; a subject that is not a `[[subjects]] folder`; two sessions of one subject on one weekday ("at most one session per subject and weekday"); a break whose end is not after its start. A valid table gives `Timetable.session(subject, day)`, or none on a weekday without that subject.
- [ ] T006 Implement `src/alfabeta/calendar/model.py` (`Session`, `Timetable`, `Placement`, `DueDate`, `Step`, `OwnedEvent`, `ItemRecord`, data-model.md), the readers in `src/alfabeta/config.py` (`StudentConfig.home_slot`, `break_span`, `warnings_on`, `timetable`, each through `READERS` with its dotted path), and the validation of T005 in `src/alfabeta/calendar/timetable.py`.
- [ ] T007 [P] Extend `tests/test_google_calendar.py`: `EventSpec.body()` carries `extendedProperties.private` `{alfabeta: "1", kind, item}`, and `_owned` compares it, so a changed `kind` is a difference; `list_owned(time_min, time_max)` sends `privateExtendedProperty=alfabeta=1`, `singleEvents=true`, `maxResults=2500` and both bounds, follows `nextPageToken`, and never sends `showDeleted`.
- [ ] T008 Implement T007 in `src/alfabeta/google/calendar.py` (research R5). `upsert` keeps working for `calendar probe`.

**Checkpoint**: the agenda carries `posted`, the timetable loads and validates, and the client lists owned events. Nothing is written to Google yet.

---

## Phase 3: User Story 7 — the facts on the timetable, beside the list the student sits down with (P1) MVP

**Goal**: every posting and due date of the agenda is a timed event in its session or at break time,
titled «Entrega ·» or «Entregado ·», with no reminders; a second run writes nothing.

**Independent test**: quickstart steps 1–4.

- [ ] T009 [P] [US7] Write `tests/test_calendar_placement.py` for research R3: a posting in its subject's session on the posting date, else at break time, labelled «Hora de la clase, no la de publicación»; a date-only due in its session, else at break time, «Classroom no indica hora»; a timed due as 30 minutes ending at the due instant, starting no earlier than 00:00 (a due at 00:15 is 00:00–00:15); a subject with no session that day, weekends and holidays included, at break time; no placement is all-day or crosses midnight; placements on 2026-10-25 and 2027-03-28 keep their wall-clock times.
- [ ] T010 [US7] Implement `place()` in `src/alfabeta/calendar/timetable.py`.
- [ ] T011 [P] [US7] Write `tests/test_calendar_events.py` for `events_for()`, per the ownership table of data-model.md: a dated assignment or quiz owns `posted` and `due`; an undated one `posted` only; a material `posted`; an announcement nothing; an exam nothing until Phase 5. Titles and description lines exactly as `contracts/events.md`; «Entregado ·» for `turned_in`, `turned_in_late` and `returned`, «Entrega ·» for any other status or none; `useDefault: false` and no overrides; the private properties; ids `event_id("alfabeta|<student>|<item>|<kind>")`. A test fails if any title or description holds a word from an advice list («empieza», «date prisa», «deberías», «recuerda», «prioridad»).
- [ ] T012 [US7] Implement `src/alfabeta/calendar/events.py`. The folder line is a Drive link when `ScopedDrive`'s cached tree resolves the entry's `folder`, else the folder's path relative to the base folder (research R11).
- [ ] T013 [P] [US7] Write `tests/test_calendar_records.py`: `data/calendar/items.json` holds per item `due`, `undated_seen_on`, `start_on`, `basis_at`, `marked`; it is written atomically with mode 0600 and only when its bytes change.
- [ ] T014 [US7] Implement `src/alfabeta/calendar/records.py` (`JsonRecordStore`).
- [ ] T015 [P] [US7] Write `tests/test_calendar_sync.py` against `FakeCalendar`:
  - without `--apply`, no write and no record; with it, the events are created;
  - a second run reports `created: 0`, `updated: 0`, `marked: 0` (SC-005);
  - a hand edit of an owned field is put back; a field alfabeta does not own is left alone;
  - an item that leaves the agenda, a due date that goes, an exam the family discarded: the event is kept, loses its reminders and is titled «Retirado ·» with its description line; never deleted;
  - a moved due date updates the same id;
  - a cancelled copy (409) is brought back with `status: confirmed`;
  - one failing event leaves the others written and exits 3; a link not `ok` writes nothing and exits 2;
  - the account written as is the one whose role is `student`; none is `no_student_account`, exit 1;
  - stdout and stderr hold no title, address, calendar id or absolute path; the JSON keys are `contracts/cli.md`'s.
- [ ] T016 [US7] Implement `CalendarSync` in `src/alfabeta/calendar/sync.py`: read the agenda (`no_agenda` if missing), list the owned events of the school year, diff the owned fields, write, mark, save the records, and report `no_session` subjects.
- [ ] T017 [US7] Implement `calendar sync [--apply]` in `src/alfabeta/calendar/cli.py`, with the Spanish lines of `contracts/cli.md`, and register the group in `src/alfabeta/__main__.py` (one import, one parser block, one dispatch line, as `exam prep` does).
- [ ] T018 [P] [US7] Write `tests/test_calendar_legacy.py`, then implement `src/alfabeta/calendar/legacy.py` and `calendar legacy [--apply]` (research R7): only events without the private property are legacy; one matches an owned event on the same `Europe/Madrid` date with the item's Classroom title contained in its title; `--apply` deletes the matched ones only; `data/calendar/legacy-<run>.json` (mode 0600) holds dates and titles, stdout only counts.
- [ ] T019 [US7] Run quickstart steps 1–4 on the Mac, with the family for SC-009. Record in the issue the counts of steps 2–4, SC-005, SC-010 and SC-009's two counts. Then spec 004 T022.

**Checkpoint**: the calendar holds every fact of the agenda on the timetable, with no reminders.

---

## Phase 4: User Stories 1, 2 and 3 — warnings by the lead-time rule (P1)

**Goal**: due-date events carry the rule's reminders when `warnings` is on; nothing past due, handed
in or already passed is warned; a run with no change writes nothing.

**Independent test**: quickstart step 5 and the DST fixtures.

- [ ] T020 [P] [US1] Write `tests/test_calendar_rule.py`, short work: posted Monday, due Tuesday 08:00 → event Tuesday 07:30–08:00 with one reminder at Monday 16:00; posted and due the same day with no home slot between `basis_at` and the bound → no warning and the item in `late`; a date-only due → its last warning at 16:00 the day before; a due at 16:10 → last warning the day before (the event starts 15:40); a due at 16:30 → a reminder of 0 minutes at 16:00 that day.
- [ ] T021 [P] [US2] Extend `tests/test_calendar_rule.py`, long work: start Thursday 2026-10-08, due Tuesday 2026-10-13 with no time → Saturday 10 and Monday 12 October at 16:00 (SC-008); `g` = 2 → one warning; `g` from 8 to 28 → `d14` unless on or before the start day, `d7`, `last`; `g` above 28 → also `d28`, moved one day later while it would ring more than 40,320 minutes before the event's start (a due at 23:59); a due on a Sunday → warnings at 16:00 on weekend days; never more than four.
- [ ] T022 [P] [US3] Extend `tests/test_calendar_rule.py`, no flood: a step not after `basis_at` is dropped; all dropped → one `catch_up` at the next home slot before the bound (FR-009); none possible → no warning and `late`; a first run on an item past due → none; handed in → none (FR-010); handed in then undone → `basis_at` reset; a moved due date → steps from the new date, `basis_at` reset (FR-011); `start_on` is the first dated run's date when `undated_seen_on` is set (FR-007); `modified_at` is never read.
- [ ] T023 [P] [US1] Write `tests/test_calendar_dst.py` (SC-007): warnings rung on both sides of 2026-10-25 and 2027-03-28 are at 16:00 local, their minutes computed from zone-aware instants across the change, and placements keep their wall-clock times.
- [ ] T024 [US1] Implement `src/alfabeta/calendar/rule.py`: `warnings()` and `reminder_minutes()` per data-model.md «Step and Warning», "0…40,320" minutes, at most four.
- [ ] T025 [US3] Extend `src/alfabeta/calendar/records.py` and `sync.py`: set `basis_at`, `start_on` and `undated_seen_on` as data-model.md says; put the reminders on due-date events when `[calendar] warnings` is `true`, none when `false` (and the «Avisos apagados» line); list `late` items and their Spanish line (FR-020). Extend `tests/test_calendar_sync.py`: a second run with warnings on, after one day of clock, writes nothing.
- [ ] T026 [P] [US3] Write `tests/test_calendar_replay.py`: on an invented state, one simulated run a day at `[schedule]`'s time (or `--at`) with no status; weekly counts of reminders, reminder days and events; `--first-run` with the statuses; the checks `past_due_warned`, `handed_in_warned`, `control`, `unwarned`, `all_day`, `cross_midnight`; a transport that fails on any request is never called.
- [ ] T027 [US3] Implement `src/alfabeta/calendar/replay.py` and `calendar replay` in `src/alfabeta/calendar/cli.py` (research R10, `contracts/cli.md`).
- [ ] T028 [US3] Run quickstart step 5 on the Mac. Record SC-001 with its control, SC-002, SC-008, SC-010 and SC-003's weekly counts in the issue, as counts and ids.

**Checkpoint**: with `warnings = true` in a test configuration, the rule's reminders are written and stable.

---

## Phase 5: User Story 4 — exams in their class, announced ahead (P2)

**Goal**: every dated exam of the agenda sits in its session or at break time, labelled, with a
warning a week before and one the evening before.

**Independent test**: quickstart step 6.

- [ ] T029 [P] [US4] Extend `tests/test_calendar_placement.py`, `test_calendar_events.py` and `test_calendar_rule.py`: an exam in its subject's session, «Hora según horario»; with no session that day, at break time, «Hora no conocida»; with a time, from that time to the end of the session that holds it, else 30 minutes, «Hora según Classroom»; title «Examen ·»; an exam in `list: done` keeps its event; reminders `d7` and `eve` with `basis_at` and `catch_up`, and `d7` dropped on or before the announcing item's posting date; an exam with no date owns no event; a discarded exam is «Retirado ·».
- [ ] T030 [US4] Implement exam events in `src/alfabeta/calendar/timetable.py`, `events.py` and `rule.py` (FR-014, FR-015, research R8).
- [ ] T031 [US4] Run quickstart step 6 and record the exams placed, by id.

---

## Phase 6: User Story 5 — "for Thursday" read from the title (P3)

**Goal**: the one form measured, a weekday with a purpose form in the title, gives a due date; nothing
else is guessed.

**Independent test**: quickstart step 7 (SC-004).

- [ ] T032 [P] [US5] Write `tests/test_calendar_infer.py` (research R9): «Ostegunerako ariketa» posted on a Monday → that week's Thursday session of its subject; «para el jueves» and «for Thursday» the same; case and accents ignored; a title naming the posting day with no purpose form → nothing; a weekday with no session of the subject → nothing; a session more than 7 days after posting → nothing; an entry with a Classroom date is never inferred; only `student.languages`' forms are read; the due event says «Fecha deducida de «…»»; nothing is stored.
- [ ] T033 [US5] Implement `src/alfabeta/calendar/infer.py` and call it from `events_for()` and `replay.py` (`inferred`).
- [ ] T034 [US5] Run quickstart step 7 and record `inferred` (SC-004).

---

## Phase 7: User Story 6 — in every run, with delivery on record (P1)

**Goal**: the sync run writes the calendar after the agenda, says every time whether delivery was
seen, and a broken link stops only the calendar.

**Independent test**: quickstart step 8. **Needs gate 2** (julioarguello/alfabeta#120).

- [ ] T035 [P] [US6] Write `tests/test_calendar_delivery.py`: `calendar delivery --account <alias> --seen-on <date>` writes `data/calendar/delivery.json` (alias → `seen_on`, mode 0600); an alias whose role is not `student` is `not_student_account`, exit 1; every `calendar sync` carries `delivery` (`seen` with the date, or `unseen`) and its Spanish line; no output says a warning was received.
- [ ] T036 [US6] Implement the delivery check in `src/alfabeta/calendar/records.py` and `cli.py` (FR-019, research R12).
- [ ] T037 [US6] Update `skills/classroom-sync/SKILL.md`: after `google check` and after the agenda is written, the run calls `calendar sync --apply`; code 2 or 3 is reported as the calendar's failure and the other outputs finish (constitution VII). The run's summary carries the calendar's and the delivery's lines.
- [ ] T038 [US6] Run quickstart step 8 on the Mac and record the delivery line and the broken-link run.

---

## Phase 8: Warnings switched on (slice 6, family step)

**Needs** slices 3, 4 and 5, gate 1 (through slice 1) and gate 3 (julioarguello/alfabeta#13).

- [ ] T039 Run quickstart step 9 with the family: `calendar delivery` with the date the family states; the operator's acceptance of SC-003's counts, quoted with its date (SC-006); `warnings = true`; after a week, the reminders written per day and, in the family's own words, whether the student's phone rang.

---

## Dependencies and order

```text
gate 1 (spec 004 T021) ─▶ Phase 1 ─▶ Phase 2 ─▶ US7 (Phase 3) ─┬─▶ US1–US3 (Phase 4) ─┬─▶ US4 (Phase 5) ──────────┐
                                                             │                      └─▶ US6 (Phase 7) ◀─ gate 2 ─┤
                                                             └─▶ US5 (Phase 6) ─────────────────────────────────┤
                                                                                     Phase 8 ◀─ gate 3 ─────────┘
```

- Phases 1–3 come first: nothing places or warns without the agenda's `posted`, the timetable and
  owned events.
- Phase 6 needs only Phase 3; Phases 5 and 7 need Phase 4.
- Within a phase, a test task [P] is written before its implementation task.

## Parallel examples

- Phase 2: T003, T005 and T007 together; then T004, T006 and T008.
- Phase 3: T009, T011, T013 and T015 together; then their implementations.
- After Phase 4: Phase 5 and Phase 7 touch different files except `cli.py`; Phase 6 can run beside
  Phase 4.

## Implementation strategy

1. **MVP = slice 1** (T001–T019): the calendar becomes a faithful, timed copy of the agenda, written
   by alfabeta as the student, with no reminders. It already replaces the connector's all-day events.
2. **Then slice 2**: the warnings, proved by replay before anyone hears one.
3. **Then slices 3 and 4**, in either order, and **slice 5** once julioarguello/alfabeta#120 is in.
4. **Slice 6** only with every gate met.
