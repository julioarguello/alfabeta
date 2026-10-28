# Implementation Plan: Due-date warnings placed on the student's timetable

**Branch**: `docs/28-due-date-warnings-plan` | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-due-date-warnings/spec.md`

## Summary

alfabeta writes the family calendar itself, as the student's personal Gmail, through spec 004's
connection. It reads spec 001's agenda (`agenda.json`), places every posting, due date and exam in
its subject's timetable session that day or at break time, and puts the lead-time rule's warnings on
the due-date and exam events as reminders at the home slot. Nothing is all-day, nothing advises,
and a run with no change in Classroom writes nothing.

The plan adds one subpackage, `src/alfabeta/calendar/`, a `calendar` command group, a few template
keys and one key in the agenda. It reuses spec 004's `CalendarClient`, adding a listing of the
events alfabeta owns.

## Gates outside this plan

Building starts only after gate 1. Warnings are switched on only after all four.

| # | Gate | Why | Tracked in |
|---|---|---|---|
| 1 | **Delivery proof.** The family watches a reminder that alfabeta set as the student's Gmail ring on the student's own phone, and records the date, the device and the account in their own words | Spec 004 never proved it: the probe's "it rang" came from a pre-written answer button, on a phone without the student's account (julioarguello/alfabeta#38 and #39, spec 004 research, Observed facts). Without it every story here is decoration (US6) | Spec 004 T021, an issue opened under julioarguello/alfabeta#30 with this plan's issues. It blocks slice 1 |
| 2 | **A lost link is loud.** A run that cannot use the student's link says so on the Mac and stops only the Google outputs | A warning that stops silently is worse than none: the family stops checking, trusting the calendar to warn | Spec 004 T014–T016, julioarguello/alfabeta#120. It blocks slice 5, which puts the calendar in the run |
| 3 | **A daily sync** before the home slot | A warning for work due the next morning exists only if a sync ran in between (FR-020) | julioarguello/alfabeta#13. It blocks slice 6 |
| 4 | **The operator accepts the volume**: the replay's weekly counts (SC-003) | One flood teaches the student that warnings are noise (US3) | Slice 6, a family step |

## Technical Context

**Language/Version**: Python 3.12, inside spec 001's package `src/alfabeta`.

**Primary Dependencies**: none new. `zoneinfo` for `Europe/Madrid`, `tomllib` through spec 001's
configuration loader, and spec 004's `HttpTransport`, `CalendarClient` and `ScopedDrive`.
Development: spec 001's `ruff`, strict `pyright` and `pytest`.

**Storage**:

- configuration: new keys in `[calendar]` and a `[[timetable]]` array in the student's
  `config.toml` ([contracts/config-template.toml](contracts/config-template.toml));
- input: `<storage.base>/<school_year>/agenda.json`, gaining one key, `posted`
  ([data-model.md](data-model.md#agenda-input));
- records: `~/.alfabeta/<student>/data/calendar/` (`items.json`, `delivery.json`,
  `legacy-<run>.json`);
- output: the family calendar (`calendar.id`), written as the linked account whose role is
  `student`.

**Testing**: `pytest` with invented agendas, an invented timetable, a frozen clock and a fake
transport. Fixtures at both daylight-saving changes (2026-10-25 and 2027-03-28). No test calls
Google. The success criteria measured on the real capture (SC-001…SC-004, SC-008, SC-010) run as
quickstart steps on the Mac with `calendar replay`, which prints counts and opaque ids only.

**Target Platform**: macOS, the family's Mac. The cloud runner of spec 001 US7 may call the same
command later (spec 001 FR-036); this plan does not build that.

**Project Type**: subcommands of spec 001's local command (`python -m alfabeta calendar …`).

**Performance Goals**: one paged listing per run, and only the writes that differ. About 200 events
a school year at the measured rate (93 items in 7 weeks).

**Constraints**:

- no all-day event, no event that crosses midnight (FR-023, SC-010);
- reminders explicit, never the calendar's defaults, at most four per event, each within Google's
  limit of 40,320 minutes (FR-004, FR-012a);
- times in `Europe/Madrid` from zone-aware instants, no hand-made offsets (FR-021, VIII);
- nothing personal in the repository, logs or output: items by opaque id, subjects by their folder
  name (FR-022, III);
- alfabeta never deletes an event it did not write, except on the operator's command for the legacy
  events of research R7, and never deletes one of its own because its fact left Classroom (V).

**Scale/Scope**: one student, one calendar, designed for several (I).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Checked against
constitution 2.2.0.

| Principle | How the plan meets it | Status |
|---|---|---|
| I. The student is configuration | The timetable, home slot, break, calendar and accounts are config keys under `--student <id>`. Weekday names and purpose forms per language are language data, not a student's | Pass |
| II. Three layers | Template keys in the repo; values in the private config; event ids and item records in `data/calendar/`; tokens stay in spec 004's keychain entries | Pass |
| III. Minors' data | Output and logs name items by Classroom id and subjects by folder. Event titles and descriptions go only to the family's own calendar. Fixtures are invented. The delivery check records only a date and an alias | Pass |
| IV. Read-only on school platforms | Nothing here reads or writes Classroom: the input is the agenda file. The checklist is Classroom's own page, ticked by the student (FR-024) | Pass |
| V. Idempotent, incremental | Deterministic event ids per item and kind. Reminders are a function of the item and its recorded basis instant, never of the run's clock. A run writes only what differs (SC-005). An event whose fact left Classroom is marked and loses its reminders, never deleted. The legacy events: [research R7](research.md#r7--what-disappears-and-the-legacy-events) and Complexity Tracking | Pass, one justified exception |
| VI. One isolated, tested provider | The calendar is an output, not a source. Its pure parts (placement, rule, inference, titles) have no I/O; the writer is spec 004's adapter behind `HttpTransport` | Pass |
| VII. Outputs degrade on their own | `calendar sync` runs after the agenda is written. A broken link or a Calendar error stops only the calendar and is reported (gate 2); the folder, the agenda and the mirrors are untouched | Pass |
| VIII. `Europe/Madrid` | Instants are built with `ZoneInfo("Europe/Madrid")`; reminder minutes are differences of instants; events carry `timeZone: "Europe/Madrid"`; tests at both changes | Pass |
| IX. Simplicity | Standard library only; no new dependency; one subpackage; one key added to an existing contract | Pass |

Re-checked after Phase 1: unchanged. The agenda change is additive, so spec 002's `exam prep`, which
reads the agenda by key, is unaffected ([research R1](research.md#r1--the-input-the-agenda-plus-one-key)).

## Project Structure

### Documentation (this feature)

```text
specs/003-due-date-warnings/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   ├── config-template.toml
│   └── events.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (additions to the layout of specs 001 and 004)

```text
src/alfabeta/calendar/
├── __init__.py
├── model.py        # Session, Timetable, Placement, DueDate, Step, OwnedEvent, ItemRecord: values, no I/O
├── timetable.py    # the [[timetable]] and [calendar] keys → Timetable; placement of an entry (FR-013, FR-014, FR-023)
├── rule.py         # the lead-time rule → ring instants and reminder minutes (FR-005…FR-009, FR-012a, FR-015)
├── infer.py        # a due date from the title's purpose form (FR-016)
├── events.py       # agenda entry → the events it owns, titles and descriptions in Spanish (FR-003, FR-018, FR-024)
├── records.py      # data/calendar/items.json and delivery.json (FR-007, FR-019)
├── sync.py         # list owned events, diff, write, mark, report (FR-010, FR-011, FR-012, FR-020)
├── replay.py       # day-by-day simulation over the state, counts only (SC-001…SC-004, SC-008, SC-010)
├── legacy.py       # events the chat connector wrote: report, and matched deletion on command
└── cli.py          # `calendar sync|replay|delivery|legacy`
src/alfabeta/google/calendar.py   # gains list_owned() and the private extended property on EventSpec
src/alfabeta/agenda.py            # gains `posted` per entry; agenda.json version 2
tests/
└── test_calendar_*.py            # one per module, plus the DST fixtures and the SC-005 second-run test
```

**Structure Decision**: a subpackage of spec 001's package, like `notes/` and `exam/`. It needs the
configuration loader, the agenda, the data folder and spec 004's adapters; a separate package would
duplicate them. The domain package is `alfabeta.calendar`; spec 004's adapter stays
`alfabeta.google.calendar`.

## Class design (by layer)

Facts the design rests on: [research.md](research.md#observed-facts).

| Layer | Names | Responsibility |
|---|---|---|
| Domain | `Session`, `Timetable`, `Placement`, `DueDate`, `Step`, `OwnedEvent`, `ItemRecord` | Values from the [data model](data-model.md); no I/O, no clock |
| Rules | `place()`, `warnings()`, `reminder_minutes()`, `infer_due()`, `events_for()` | Pure functions of an agenda entry, the timetable, the item's record and the home slot |
| Ports | `HttpTransport`, `Clock`, `RecordStore` | What the services need from outside |
| Adapters | `CalendarClient` (spec 004, gains `list_owned`), `ScopedDrive` (spec 004, read only: a folder's link), `JsonRecordStore` | Each wraps one store or API |
| Services | `CalendarSync`, `Replay`, `LegacyReport` | Orchestrate per command; return results the CLI prints |
| CLI | `calendar sync`, `replay`, `delivery`, `legacy` in `calendar/cli.py`, registered in `__main__.py` | Arguments, JSON out, Spanish lines for the family, exit codes ([contracts/cli.md](contracts/cli.md)) |

Changes to other specs' files, each named in the task that makes it:

- `google/calendar.py` (spec 004): `EventSpec` gains `extendedProperties.private` (`alfabeta`,
  `kind`, `item`), part of the owned fields; `CalendarClient` gains `list_owned(time_min,
  time_max)`, one paged `events.list` filtered by `privateExtendedProperty=alfabeta=1`
  ([research R5](research.md#r5--identity-ownership-and-one-listing-per-run)).
- `agenda.py`, both copies of `agenda.schema.json` and spec 001's data model: `posted` per entry,
  `version` 2.
- `config/template.toml` and `__main__.py`'s `TABLES["calendar"]`: the keys of
  [contracts/config-template.toml](contracts/config-template.toml).
- `skills/classroom-sync/SKILL.md`: the run calls `calendar sync --apply` after the agenda is
  written (slice 5).

## Vertical slices (each leaves the system demonstrable)

Each slice is one issue under julioarguello/alfabeta#28 and one pull request. Its acceptance comes
before its code; its proof is a quickstart step.

1. **Facts on the timetable.** Covers US7 and FR-003, FR-004, FR-012, FR-013, FR-018, FR-022, FR-023,
   FR-024, SC-005, SC-009, SC-010. The agenda's `posted`, the timetable keys, placement, owned events,
   `calendar sync` (a dry run unless `--apply`) and `calendar legacy`. Postings and due dates are
   written with no reminders, and every due-date event reads «Entrega ·» or «Entregado ·». Done
   when quickstart steps 1–4 pass. Blocked by gate 1.
2. **Warnings by the lead-time rule.** Covers US1, US2, US3 and FR-005…FR-011, FR-012a, FR-020,
   FR-021, SC-001, SC-002, SC-003, SC-007, SC-008. The rule, the item records, the `warnings` switch
   and `calendar replay`. Done when step 5's replay gives SC-001, SC-002 and SC-008, and the DST
   fixtures pass. Blocked by slice 1.
3. **Exams in their class, announced ahead.** Covers US4 and FR-014, FR-015. Exam events in the
   session or at break time with their label, and their two warnings. Done when step 6 shows the
   stream's exams placed. Blocked by slice 2.
4. **"For Thursday" read from the title.** Covers US5 and FR-016, FR-017, SC-004. Done when step 7's
   replay infers exactly one date. Blocked by slice 1.
5. **In every run, with delivery on record.** Covers US6 and FR-002, FR-019. `calendar delivery`,
   the delivery line of every run, and the sync run calling `calendar sync --apply` after the agenda
   and after `google check`. Done when step 8 shows the run's delivery line and a broken link
   stopping only the calendar. Blocked by slice 2 and gate 2 (julioarguello/alfabeta#120).
6. **Warnings switched on.** The family step of SC-003 and SC-006: the operator accepts the replay's
   counts, the delivery check is on record, and `warnings = true` is set. Done when step 9's first
   week of live use is recorded. Blocked by slices 3, 4 and 5, and gate 3
   (julioarguello/alfabeta#13); gate 1 reaches it through slice 1.

## Complexity Tracking

| Departure | Why it is needed | Simpler alternative rejected because |
|---|---|---|
| A change to another spec's contract (`agenda.json` gains `posted`, version 2) | FR-007's start date is the posting date, which the agenda does not carry for an assignment | Reading `data/state.json` couples the calendar to spec 001's internal state, which the agenda exists to hide; spec 001 names the agenda as this epic's input |
| A deletion path (`calendar legacy --apply`) in a project whose principle V forbids deleting what left the origin | The family calendar holds all-day events that the chat connector wrote before spec 004; they break FR-023 and would show every fact twice | Deleting them by hand is the operator's work, which the operator declined for this project; deleting every foreign event would remove what the family added. Only events matched one-to-one to an owned event of the same fact go, on command, never in a run |
