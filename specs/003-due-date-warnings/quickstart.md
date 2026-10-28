# Quickstart: proving the warnings on the real calendar

Run on the family's Mac, from the repository clone, after each slice's pull request is merged. The
commands are `uv run python -m alfabeta --home ~/.alfabeta <command> --student <id>`; below they
are shortened to `alfabeta <command>`. Record each result in the slice's issue as counts and opaque
ids only: no title, name, address or calendar id.

## Prerequisites

- Spec 001's agenda exists: `<storage.base>/<school_year>/agenda.json`, version 2 (slice 1).
- Spec 004's link of the student's Gmail is `ok`: `alfabeta google check`.
- **Gate 1** for slice 1 on: the family has watched a reminder set as the student's Gmail ring on
  the student's own phone, and stated the date, the device and the account in their own words
  (spec 004 T021). A pre-written answer is not a measurement.
- The student's phone shows the family calendar through the student's personal Gmail only. If it
  also shows it through the school account, every event appears twice there; the family removes one
  of the two on the phone (FR-019).

## 1. The timetable (slice 1)

The family transcribes the school timetable once into the private configuration
([contracts/config-template.toml](contracts/config-template.toml)): one `[[timetable]]` table per
session, `home_slot`, the break, and `warnings = false`.

```bash
alfabeta config check
```

Expect no problem. A subject with two sessions on one weekday, or a session whose subject is not a
`[[subjects]]` folder, is reported by its key.

Two checks by hand, recorded with their date:

- The calendar's sharing settings in Google Calendar list exactly the accounts of
  `calendar.shared_with`, each able to see all event details, and no other (spec 001 FR-011b,
  constitution VII). alfabeta cannot read sharing with the student's link (research R13).
- The calendar policy line of the student's private configuration reads "objective facts from
  Classroom, plus warnings that restate those facts" (spec, «Changes elsewhere»).

## 2. A dry run (slice 1)

```bash
alfabeta calendar sync
```

Expect `applied: false` and counts of what would be created. `no_session` lists the subjects with
dated work and no session; each is either added to the timetable or accepted (its events sit at
break time).

## 3. Facts on the timetable (slice 1)

```bash
alfabeta calendar sync --apply
alfabeta calendar sync --apply
```

- The first run creates the events. The second reports `created: 0`, `updated: 0`, `marked: 0`
  (SC-005).
- In Google Calendar: no all-day event from alfabeta, none crossing midnight (SC-010); postings and
  date-only dues in their session or at 10:00–10:25; a timed due ending at its time.
- **SC-009**, with the student, the same day: every «Entrega ·» event is, item by item, what
  Classroom's «Tareas pendientes» shows as pending with a date («Asignado» with a date, and «Sin
  entregar»). Record the two counts and any item id that differs.

## 4. The legacy events (slice 1)

```bash
alfabeta calendar legacy
```

Read `matched` and `unmatched`; the private report `data/calendar/legacy-<run>.json` lists them.
Step 3 gave each legacy event its owned twin. Then:

```bash
alfabeta calendar legacy --apply
```

Expect `deleted` equal to `matched`. The family decides about each unmatched event by hand. Then
the operator does spec 004 T022: the chat connector's account leaves the calendar's sharing.

## 5. The rule, replayed (slice 2)

```bash
alfabeta calendar replay --first-run 2026-10-26
alfabeta calendar replay --from 2026-09-07 --to 2026-10-26
```

- **SC-001**: the first-run replay reports `past_due_warned: 0` and `handed_in_warned: 0`, and its
  `control` counts are not 0. They were 16 and 7 on the capture of 2026-10-26; the state's statuses
  have moved since, so record its own numbers beside those (research R10).
- **SC-002**: the day-by-day replay's `unwarned` holds only the items posted and due with no home
  slot in between (2 measured).
- **SC-008**: the chromatography item rings on Saturday 10 and Monday 12 October at 16:00 and on no
  day from 13 October.
- **SC-003**: the weekly counts of reminders, days with a reminder and events go to the operator
  (slice 6).
- **SC-010**: `all_day: 0` and `cross_midnight: 0`.

## 6. Exams (slice 3)

```bash
alfabeta calendar sync --apply
```

The exams the stream announced sit in their subject's session, «Hora según horario», or at break
time, «Hora no conocida». Their two warnings are proved by the tests and counted in step 5's
replay; they are written only once slice 6 switches warnings on.

## 7. "For Thursday" (slice 4)

```bash
alfabeta calendar replay --from 2026-09-07 --to 2026-10-26
```

**SC-004**: `inferred` holds exactly one item, the Physics «Ostegunerako» assignment, placed at
that Thursday's Physics session.

## 8. In every run (slice 5)

- Run the Classroom sync as the family does. Its summary carries the calendar's line and the
  delivery line, «Entrega de avisos no comprobada…» until step 9's record.
- Revoke the link (spec 004 quickstart step 6) and run again: the calendar reports code 2 and the Mac
  notification of julioarguello/alfabeta#120 appears; the folder and the agenda still update. Link
  again.

## 9. Warnings switched on (slice 6)

Only when gate 3's daily sync runs (julioarguello/alfabeta#13).

1. The family records the delivery check they saw in gate 1, in their own words:

   ```bash
   alfabeta calendar delivery --account <alias> --seen-on <date>
   ```

2. The operator reads step 5's weekly counts and accepts them (SC-003). The acceptance is quoted
   in the slice's issue with its date.
3. Set `warnings = true` in the private configuration, then `alfabeta calendar sync --apply`.
4. After a week: record the reminders written per day (from the run's JSON) and, in the family's
   words, whether the student's phone rang for them. Nothing is recorded as received unless someone
   saw it (FR-019).
