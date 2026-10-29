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

- [ ] T001 Add the keys of `specs/003-due-date-warnings/contracts/config-template.toml` to `config/template.toml` and to its byte-identical copy `specs/001-classroom-sync/contracts/config-template.toml` (`tests/test_contracts.py` compares them): in `[calendar]`, `enabled = false`, `home_slot`, `break_start`, `break_end` (`"changeme"`, e.g. `"17:30"`, `"11:00"`, `"11:30"`) and `warnings = false`; a `[[timetable]]` array with `weekday`, `start`, `end`, `subject`. Set `TABLES["calendar"]` in `src/alfabeta/__main__.py` to every table the `calendar` verbs read: `student`, `classroom`, `storage`, `calendar`, `timetable`, `subjects`, `schedule`, `google`. Run `tests/test_template_covers_reads.py`.
- [ ] T002 [P] Create `src/alfabeta/calendar/__init__.py` and `tests/calendar_fakes.py`: an invented agenda builder (subjects «Mates», «Ciencias», «Euskera», invented titles and ids), an invented timetable, a frozen `Clock`, and `FakeCalendar`, an in-memory calendar that serves `list_owned`, `get`, `insert`, `update` and `delete`, replaces the whole event on `PUT` and merges on `PATCH`, keeps deleted events as `cancelled`, answers 409 to an insert of a cancelled id, and can fail one chosen id with a 500.

---

## Phase 2: Foundational (slice 1; blocks every story)

- [ ] T003 [P] Extend `tests/test_agenda.py`: every entry carries `posted`, the item's posting date as `YYYY-MM-DD`; a detected exam carries its origin item's; the document's `version` is 2; the output validates against both schema copies. `tests/test_contracts.py` already keeps the two copies of `agenda.schema.json` identical.
- [ ] T004 Implement `posted` (research R1): `AgendaEntry.posted: dt.date` in `src/alfabeta/model.py`, set in `src/alfabeta/agenda.py` (`_entry`, `_detected`, `_as_json`), `VERSION = 2`. Add `"posted": {"type": "string", "format": "date"}` to `required` and `properties`, and `"version": {"const": 2}`, in `specs/001-classroom-sync/contracts/agenda.schema.json` and `src/alfabeta/schemas/agenda.schema.json`. Add the `posted` row to «Agenda entry» in `specs/001-classroom-sync/data-model.md`. `tests/test_exam_prep.py` must pass unchanged.
- [ ] T005 [P] Write `tests/test_calendar_timetable.py`, configuration part. Each is a problem named by its key, never its value: a weekday outside `monday`…`sunday`; a time not `HH:MM`; `end` not after `start`; a subject that is not a `[[subjects]] folder`; two sessions of one subject on one weekday is a warning, not a problem: placement then uses the first session that day; a break whose end is not after its start. A valid table gives `Timetable.session(subject, day)`, or none on a weekday without that subject.
- [ ] T006 Implement `src/alfabeta/calendar/model.py` (`Session`, `Timetable`, `Placement`, `DueDate`, `Step`, `OwnedEvent`, `ItemRecord`, data-model.md), the readers in `src/alfabeta/config.py` (`StudentConfig.home_slot`, `break_span`, `warnings_on`, `timetable`, each through `READERS` with its dotted path), and the validation of T005 in `src/alfabeta/calendar/timetable.py`. Call that validation from `config.check()` in `src/alfabeta/config.py`, so `config check` reports it.
- [ ] T007 [P] Extend `tests/test_google_calendar.py`: `EventSpec.body()` carries `extendedProperties.private` `{alfabeta: "<student>", kind, item}`, and `_owned` compares it, so a changed `kind` is a difference; `list_owned(time_min, time_max)` sends `privateExtendedProperty=alfabeta=<student>`, `singleEvents=true`, `maxResults=2500` and both bounds, follows `nextPageToken`, and never sends `showDeleted`; the bounds are 1 September of the school year's first year and of its second, 00:00 `Europe/Madrid`; `update` sends `PATCH` with the owned fields only, so a colour set on the event survives (a `PUT` would clear it).
- [ ] T008 Implement T007 in `src/alfabeta/google/calendar.py` (research R5). `update` becomes a `PATCH`; `upsert` keeps working for `calendar probe`.

**Checkpoint**: the agenda carries `posted`, the timetable loads and validates, and the client lists owned events. Nothing is written to Google yet.

---

## Phase 3: User Story 7 — the facts on the timetable, beside the list the student sits down with (P1) MVP

**Goal**: every posting and due date of the agenda is a timed event in its session or at break time,
titled «Entrega ·» or «Entregado ·», with no reminders; a second run writes nothing.

**Independent test**: quickstart steps 1–4.

- [ ] T009 [P] [US7] Write `tests/test_calendar_placement.py` for research R3: a posting in its subject's session on the posting date, else at break time, labelled «Hora de la clase, no la de publicación»; a date-only due in its session, else at break time, «Classroom no indica hora»; a timed due as 30 minutes ending at the due instant, starting no earlier than 00:00 (a due at 00:15 is 00:00–00:15); a subject with no session that day, weekends and holidays included, at break time; no placement is all-day or crosses midnight, every one clamped to 00:00–24:00 of its day; placements on 2026-10-25 and 2027-03-28 keep their wall-clock times.
- [ ] T010 [US7] Implement `place()` in `src/alfabeta/calendar/timetable.py`.
- [ ] T011 [P] [US7] Write `tests/test_calendar_events.py` for `events_for()`, per the ownership table of data-model.md: a dated assignment or quiz owns `posted` and `due`; an undated one `posted` only; a material `posted`; an announcement nothing; an exam nothing until Phase 5. Titles and description lines exactly as `contracts/events.md`; «Entregado ·» for `turned_in`, `turned_in_late` and `returned`, «Entrega ·» for any other status or none; `useDefault: false` and no overrides; the private properties; ids `event_id("alfabeta|<student>|<item>|<kind>")`. A test fails if any title or description holds a word from an advice list («empieza», «date prisa», «deberías», «recuerda», «prioridad»).
- [ ] T012 [US7] Implement `src/alfabeta/calendar/events.py`. The folder line is the entry's `folder`, the path relative to the student's base folder, never a Drive link (research R11).
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
  - stdout and stderr hold no title, address, calendar id or absolute path; the JSON carries `ok`, `applied`, `created`, `updated`, `marked`, `unchanged` and `no_session` of `contracts/cli.md` (T025 adds `warnings_on` and `late`, T036 `delivery`).
- [ ] T016 [US7] Implement `CalendarSync` in `src/alfabeta/calendar/sync.py`: with `[calendar] enabled = false` do nothing and report `disabled` (exit 0); called alone, take the student's lock for a run of its own (data-model.md «Run line»); read the agenda (`no_agenda` if missing, `old_agenda` if its `version` is below 2), list the owned events of the school year, diff the owned fields, write, mark, save the records, report `no_session` subjects, and with `--apply` append the `type: calendar` line of data-model.md «Run line» to `data/log.jsonl` (constitution V). Extend `tests/test_calendar_sync.py`: one line per applied run, none for a dry run, no title in it.
- [ ] T017 [US7] Implement `calendar sync [--apply]` in `src/alfabeta/calendar/cli.py`, with the Spanish lines of `contracts/cli.md`. Extend the existing `calendar` group of `src/alfabeta/__main__.py` (it holds `probe` and `probe-clean`): add the new verbs, add them to the `--student` loop, and replace the group's fall-through dispatch with one branch per verb.
- [ ] T018 [US7] Write `tests/test_calendar_legacy.py`, then implement `src/alfabeta/calendar/legacy.py` and `calendar legacy [--apply --report <file>]` (research R7). Selected: only events with no alfabeta property, all-day, and `created` before `first_apply_at`; a timed event, or one created later, is never selected. Matched: one owned event on the same `Europe/Madrid` date with the item's Classroom title contained in its title. `--apply` deletes only the events the given report lists as `matched` and that still match when re-read. `data/calendar/legacy-<run>.json` (mode 0600) holds dates and titles; stdout only counts. `sync.py` records `first_apply_at` on the first applied run.
- [ ] T019 [US7] Run quickstart steps 1–4 on the Mac, with the family for SC-009. Record in the issue step 1's two checks by hand (the calendar's sharing equals `calendar.shared_with`; the private configuration's calendar policy line), the counts of steps 2–4, SC-005, SC-010 and SC-009's counts. Spec 004 T022 is done before step 3's first `--apply`. Update `docs/privacy.md`, in both its languages: alfabeta lists its own events, and on the family's reviewed command deletes the old all-day duplicates the chat connector wrote.

**Checkpoint**: the calendar holds every fact of the agenda on the timetable, with no reminders.

---

## Phase 4: User Stories 1, 2 and 3 — warnings by the lead-time rule (P1)

**Goal**: due-date events carry the rule's reminders when `warnings` is on; nothing past due, handed
in or already passed is warned; a run with no change writes nothing.

**Independent test**: quickstart step 5 and the DST fixtures.

- [ ] T020 [P] [US1] Write `tests/test_calendar_rule.py`, short work: posted Monday, a sync Monday at 15:00, due Tuesday 08:00 → event Tuesday 07:30–08:00 with one reminder at Monday 16:00; posted and due the same day with no home slot between `basis_at` and the bound → no warning and the item in `late`; a date-only due → its last warning at 16:00 the day before; a due at 16:10 → last warning the day before (the event starts 15:40); a due at 16:30 → a reminder of 0 minutes at 16:00 that day.
- [ ] T021 [US2] Extend `tests/test_calendar_rule.py`, long work: start Thursday 2026-11-05, due Tuesday 2026-11-10 with no time → Saturday 7 and Monday 9 November at 16:00 (the shape of SC-008, on invented dates); `g` = 2 → one warning; `g` from 8 to 28 → `d14` unless on or before the start day, `d7`, `last`; `g` above 28 → also `d28`, moved one day later while it would ring more than 40,320 minutes before the event's start (a due at 23:59); a due on a Sunday → warnings at 16:00 on weekend days; never more than four.
- [ ] T022 [US3] Extend `tests/test_calendar_rule.py`, no flood: a step not after `basis_at` is dropped; a first run after `d14` and `d7` passed keeps only `last`, the next home slot (FR-009); `last` passed too → no warning and `late`; a first run on an item past due → none; handed in → none (FR-010); handed in then undone → `basis_at` reset; a moved due date → steps from the new date, `basis_at` reset (FR-011); `start_on` is the first dated run's date when `undated_seen_on` is set (FR-007); `modified_at` is never read. The first run with `warnings = true` sets every open item's `basis_at` to that run, so an item whose earlier steps passed while warnings were off keeps only `last`.
- [ ] T023 [P] [US1] Write `tests/test_calendar_dst.py` (SC-007): warnings rung on both sides of 2026-10-25 and 2027-03-28 are at 16:00 local, their minutes computed from zone-aware instants across the change, and placements keep their wall-clock times.
- [ ] T024 [US1] Implement `src/alfabeta/calendar/rule.py`: `warnings()` and `reminder_minutes()` per data-model.md «Step and Warning», "0…40,320" minutes, at most four.
- [ ] T025 [US3] Extend `src/alfabeta/calendar/records.py` and `sync.py`: set `basis_at`, `start_on` and `undated_seen_on` as data-model.md says; put the reminders on due-date events when `[calendar] warnings` is `true`, none when `false` (and the «Avisos apagados» line); list `late` items and their Spanish line (FR-020). Extend `tests/test_calendar_sync.py`: a second run with warnings on, after one day of clock, writes nothing. `config check` warns when a weekday's `[schedule]` time is after `home_slot` (research R10).
- [ ] T026 [P] [US3] Write `tests/test_calendar_replay.py`: on an invented state, one simulated run a day at `[schedule]`'s time (or `--at`) with no status; weekly counts of reminders, reminder days and events; `--first-run` with the statuses; the checks `past_due_warned`, `handed_in_warned`, `control` (items past due or handed in that would get at least one step with no cutoff, no handed-in exclusion and no `basis_at` drop), `unwarned`, `all_day`, `cross_midnight`; a transport that fails on any request is never called.
- [ ] T027 [US3] Implement `src/alfabeta/calendar/replay.py` and `calendar replay` in `src/alfabeta/calendar/cli.py` (research R10, `contracts/cli.md`).
- [ ] T028 [US3] Run quickstart step 5 on the Mac. Record SC-001 with its control, SC-002, SC-008, SC-010 and SC-003's weekly counts in the issue, as counts.

**Checkpoint**: with `warnings = true` in a test configuration, the rule's reminders are written and stable.

---

## Phase 5: User Story 4 — exams in their class, announced ahead (P2)

**Goal**: every dated exam of the agenda sits in its session or at break time, labelled, with a
warning a week before and one the evening before.

**Independent test**: quickstart step 6.

- [ ] T029 [P] [US4] Extend `tests/test_calendar_placement.py`, `test_calendar_events.py` and `test_calendar_rule.py`: an exam in its subject's session, «Hora según horario»; with no session that day, at break time, «Hora no conocida»; with a time, from that time to the end of the session that holds it, else 30 minutes, «Hora según Classroom»; title «Examen ·»; an exam in `list: done` keeps its event; reminders `d7` and `eve` with `basis_at`; an exam at 17:00 first seen at 09:00 that day gets one `catch_up` at 16:00; and `d7` dropped on or before the announcing item's posting date; an exam with no date owns no event; a discarded exam is «Retirado ·»; an exam at 23:59 is 23:59–24:00 and never crosses midnight; a detected exam's description says «Detectado en un aviso de Classroom» (and «Corregido por la familia» when corrected); a detected entry corrected into another category owns no event.
- [ ] T030 [US4] Implement exam events in `src/alfabeta/calendar/timetable.py`, `events.py` and `rule.py` (FR-014, FR-015, research R8).
- [ ] T031 [US4] Run quickstart step 6 and record how many exams were placed, in the session or at break time.

---

## Phase 6: User Story 5 — "for Thursday" read from the title (P3)

**Goal**: the one form measured, a weekday with a purpose form in the title, gives a due date; nothing
else is guessed.

**Independent test**: quickstart step 7 (SC-004).

- [ ] T032 [P] [US5] Write `tests/test_calendar_infer.py` (research R9): an invented «Ostiralerako lana» posted on a Tuesday → that week's Friday session of its subject; the `-rako` form of every Basque weekday; «para el viernes» and «for Friday» the same; case and accents ignored; a title naming the posting day with no purpose form → nothing; a weekday with no session of the subject → nothing; a session more than 7 days after posting → nothing; an entry with a Classroom date is never inferred; only `student.languages`' forms are read; the due event says «Fecha deducida de «…»»; the record holds `due` with `source: inferred` and `start_on` = `posted`; a later Classroom date replaces it.
- [ ] T033 [US5] Implement `src/alfabeta/calendar/infer.py` and call it from `events_for()` and `replay.py` (`inferred`).
- [ ] T034 [US5] Run quickstart step 7 and record how many items `inferred` holds (SC-004).

---

## Phase 7: User Story 6 — in every run, with delivery on record (P1)

**Goal**: the sync run writes the calendar after the agenda, says every time whether delivery was
seen, and a broken link stops only the calendar.

**Independent test**: quickstart step 8. **Needs gate 2** (julioarguello/alfabeta#120).

- [ ] T035 [P] [US6] Write `tests/test_calendar_delivery.py`: `calendar delivery --account <alias> --seen-on <date>` writes `data/calendar/delivery.json` (alias → `seen_on`, mode 0600); an alias whose role is not `student` is `not_student_account`, exit 1; every `calendar sync` carries `delivery` (`seen` with the date, or `unseen`) and its Spanish line; no output says a warning was received. `calendar sharing --checked-on <date>` writes `data/calendar/sharing.json` with the date and the SHA-256 of the sorted `calendar.shared_with`, never the addresses; every run says «Comprobar con quién se comparte el calendario» while no check is on record or the list's hash differs.
- [ ] T036 [US6] Implement the delivery check and the sharing check in `src/alfabeta/calendar/records.py` and `cli.py` (FR-019, research R12, R13).
- [ ] T037 [US6] Update `skills/classroom-sync/SKILL.md`: after `google check` and after the agenda is written, the run calls `calendar sync --apply` when `[calendar] enabled` is true; code 2 or 3 is reported as the calendar's failure and the other outputs finish (constitution VII). The run's summary carries the calendar's and the delivery's lines.
- [ ] T038 [US6] Run quickstart step 8 on the Mac and record the delivery line and the broken-link run.

---

## Phase 8: Warnings switched on (slice 6, family step)

**Needs** slices 3, 4 and 5, gate 1 (through slice 1) and gate 3 (julioarguello/alfabeta#13).

- [ ] T039 Run quickstart step 9 with the family: `calendar delivery` with the date the family states; `calendar sharing` with the date of step 1's check; the replay of step 5 run again, at `--at 15:00` and with no `--at` (the configured `[schedule]` times), now that exams (slice 3) and inferred dues (slice 4) are in, and the operator's acceptance of those counts, quoted with its date (SC-003, SC-006); `warnings = true`; after a week, the reminders written per day and, in the family's own words, whether the student's phone rang.

---

## Dependencies and order

```text
gate 1 (spec 004 T021) ─▶ Phase 1 ─▶ Phase 2 ─▶ US7 (Phase 3) ─▶ US1–US3 (Phase 4) ─┬─▶ US4 (Phase 5) ─────────┐
                                                                                 ├─▶ US5 (Phase 6) ─────────┤
                                                              gate 2 (#120) ─────┴─▶ US6 (Phase 7) ─────────┤
                                                                                   Phase 8 ◀─ gate 3 (#13) ─┘
```

- Phases 1–3 come first: nothing places or warns without the agenda's `posted`, the timetable and
  owned events.
- Phases 5, 6 and 7 need Phase 4: Phase 6's proof is a replay, and an inferred due is warned by the rule.
- Within a phase, a test task [P] is written before its implementation task.

## Parallel examples

- Phase 2: T003, T005 and T007 together; then T004, T006 and T008.
- Phase 3: T009, T011, T013 and T015 together; then their implementations.
- After Phase 4: Phases 5, 6 and 7 touch mostly different files; `cli.py` and `events.py` are shared, so their pull requests go one after another. 

## Implementation strategy

1. **MVP = slice 1** (T001–T019): the calendar becomes a faithful, timed copy of the agenda, written
   by alfabeta as the student, with no reminders. It already replaces the connector's all-day events.
2. **Then slice 2**: the warnings, proved by replay before anyone hears one.
3. **Then slices 3, 4 and 5**, in any order; slice 5 also needs julioarguello/alfabeta#120.
4. **Slice 6** only with every gate met.
