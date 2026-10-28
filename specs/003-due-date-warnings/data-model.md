# Data model: Due-date warnings placed on the student's timetable

Configuration lives in the student's private `config.toml`, records in the data folder
`~/.alfabeta/<student>/data/calendar/`, and the events in the family calendar. Nothing here is in
the repository except the template keys. Times are `Europe/Madrid`.

## Agenda input

`<storage.base>/<school_year>/agenda.json`, spec 001's
[contract](../001-classroom-sync/contracts/agenda.schema.json), version 2 with this spec
([research R1](research.md#r1--the-input-the-agenda-plus-one-key)).

| Field | Used for |
|---|---|
| `posted` (new) | `YYYY-MM-DD`, the item's posting date; a detected exam takes its origin's. FR-007's start date, the posting event's day |
| `item`, `category`, `subject`, `title` | Identity, kind of events, timetable subject, event title |
| `date`, `date_only` | The due date or exam date; a posting date for a material |
| `status`, `list` | FR-010 (handed in) and an exam that took place |
| `classroom_link`, `folder` | The event's description |

## Session and Timetable (configuration)

| Field | Where | Rule |
|---|---|---|
| `weekday` | `[[timetable]] weekday` | `monday` … `sunday` |
| `start`, `end` | `[[timetable]] start`, `end` | `HH:MM`, `end` after `start`, same day |
| `subject` | `[[timetable]] subject` | A `[[subjects]] folder`; at most one session per subject and weekday |
| `home_slot` | `[calendar] home_slot` | `HH:MM`, every day of the week (FR-008) |
| `break_start`, `break_end` | `[calendar]` | `HH:MM`, the break every day (FR-023) |
| `warnings` | `[calendar] warnings` | `true` writes reminders; `false` writes events only (research R12) |

`Timetable.session(subject, day)` returns that subject's session on that weekday or none. Times
are approximate, as the timetable says; they place events, they are never a due hour.

## Placement

`Placement(start, end, label)`: a timed span within one day, from
[research R3](research.md#r3--placement). `label` is none for a timed due, else one of these, shown
as [contracts/events.md](contracts/events.md) writes it:

| `label` | Line in the description |
|---|---|
| `class_hour` | «Hora de la clase, no la de publicación» |
| `no_time_given` | «Classroom no indica hora» |
| `inferred` | «Fecha deducida de «…»» |
| `timetable_hour` | «Hora según horario» |
| `hour_unknown` | «Hora no conocida» |
| `classroom_hour` | «Hora según Classroom» |

## DueDate

| Field | Rule |
|---|---|
| `day` | A date |
| `time` | A time, or none: FR-005 never invents one |
| `source` | `classroom` (the agenda's date) · `inferred` (FR-016, with the words) |

Its **instant** is `day` at `time`; a date-only due has instead a **cutoff**, the start of `day`.

## Step and Warning

| Field | Rule |
|---|---|
| `step` | `d28` · `d14` · `d7` · `half` · `last` (due dates, FR-006); `d7` · `eve` (exams, FR-015); `catch_up` (FR-009) |
| `day` | The day it rings, at `home_slot` |
| `ring_at` | `day` at `home_slot`, zone-aware |
| `minutes` | `event start − ring_at`, whole minutes, 0…40,320 |

Rules, in order ([research R4](research.md#r4--the-rules-arithmetic)):

1. `last` is the last home slot at or before the event's start and strictly before the due instant
   or cutoff.
2. `g = due day − start day`. From 2 to 7, `half = due day − ⌈g/2⌉`. From 8, `d14` and `d7`; above
   28, `d28`, moved one day later while its minutes exceed 40,320.
3. A step other than `last` on or before the start day is dropped; two steps on one day are one.
4. A step whose `ring_at` is not after the item's `basis_at` is dropped. If all are dropped and a
   home slot lies after `basis_at` and within the bound, that slot is the one `catch_up` step.
5. Handed in (`turned_in`, `turned_in_late`, `returned`) or marked «Retirado»: no steps.
6. At most four steps remain; spec 004's `EventSpec` refuses a fifth.

## OwnedEvent

| Field | Rule |
|---|---|
| `kind` | `posted` · `due` · `exam` |
| `id` | `event_id("alfabeta|<student>|<item>|<kind>")`, spec 004's base32hex |
| `summary` | [contracts/events.md](contracts/events.md); never advice, never a made-up priority |
| `description` | Facts and links, in Spanish ([contracts/events.md](contracts/events.md)) |
| `start`, `end` | The placement, `timeZone: "Europe/Madrid"` |
| `reminders` | `useDefault: false`; the warnings' minutes, or none |
| `extendedProperties.private` | `alfabeta: "1"`, `kind`, `item` |

Which entries own which events:

| Entry | `posted` | `due` | `exam` |
|---|---|---|---|
| `assignment`, `quiz` with a date (or an inferred one) | yes | yes | — |
| `assignment`, `quiz` with no date | yes | — | — |
| `material` | yes | — | — |
| `announcement` | — | — | — |
| `exam` with a date | — | — | yes |
| `exam` with no date | — | — | — |

## ItemRecord (`data/calendar/items.json`)

| Field | Rule |
|---|---|
| `due` | The last due value a run saw (ISO, or null) |
| `undated_seen_on` | The date of the first run that saw the item with no due date, or null |
| `start_on` | FR-007: `posted`, or the date of the first run that saw the due date when `undated_seen_on` is set |
| `basis_at` | The instant of the run that first saw the current `due` while not handed in |
| `marked` | The fact that went, if the event is «Retirado» (`withdrawn`, `no_due`, `discarded`), else null |

Written atomically, mode 0600, only when its bytes change.

## DeliveryCheck (`data/calendar/delivery.json`)

| Field | Rule |
|---|---|
| `<alias>` | The account's alias (`[google.accounts.<alias>]`, role `student`) |
| `seen_on` | The date the family saw a reminder ring on the student's phone, as they state it |

Only `calendar delivery` writes it. Every run reads it and says `seen` with the date or `unseen`.

## Run line (`data/log.jsonl`, spec 001's log)

`calendar sync --apply` and `calendar legacy --apply` each append one line, as `book place` and
`log notebook` do: `type: calendar` (or `calendar_legacy`), `at`, `run`, `result` (`ok` ·
`partial` · `stopped`), `reason` if not `ok` (`link_<status>`, `no_agenda`, `write_failed`), the
counts `created`, `updated`, `marked`, `unchanged`, `failed` (legacy: `matched`, `unmatched`,
`deleted`), `warnings_on` and `delivery` (`seen` · `unseen`). Counts and ids only, never a title
(constitution V, III). A dry run writes no line.

## LegacyReport (`data/calendar/legacy-<run>.json`)

Lists `matched` (each legacy event with the owned event of the same fact) and `unmatched`. Dates and
titles live only in this private file; the command prints counts.

## State transitions

```text
Due-date event:  none ──agenda has a date──▶ «Entrega ·» (reminders per the rule)
                 «Entrega ·» ──status handed in──▶ «Entregado ·» (no reminders)
                 «Entregado ·» ──student undoes the mark──▶ «Entrega ·» (basis_at reset)
                 any ──date moves──▶ same id, new placement, basis_at reset
                 any ──item withdrawn or date gone──▶ «Retirado ·» (no reminders, kept)
Warnings switch: false (events only) ──slice 6, gates 1–4──▶ true
Delivery:        unseen ──calendar delivery──▶ seen <date>
Legacy event:    present ──legacy --apply, matched──▶ deleted; unmatched ──▶ left for the family
```
