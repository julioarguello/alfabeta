# Research: Due-date warnings placed on the student's timetable

Phase 0 of [plan.md](plan.md). Each decision names what it rests on. The spec's own measurements
(the capture of 2026-10-26, the panel of 2026-10-27) are not repeated here.

## Observed facts

| Fact | Where it comes from |
|---|---|
| `agenda.json` entries carry `item`, `subject` (the subject's folder), `list`, `category`, `title`, `date`, `date_only`, `status`, `detected`, `origin`, `corrected`, `classroom_link`, `folder`. No posting date for an assignment, no description text, no class id | Read on `main` ad69353, 2026-10-28: `src/alfabeta/agenda.py` `_as_json`, `specs/001-classroom-sync/contracts/agenda.schema.json` |
| A class is linked to a subject by class id, through a `class_link` decision; the agenda resolves it to the subject's folder and leaves out the items of unlinked classes | Same commit: `model.DecisionType.CLASS_LINK`, `AgendaBuilder._items` |
| No decision type lets the family declare an exam that Classroom does not show. `exam_correction` only corrects an exam detected from a Classroom text | Same commit: `model.DecisionType`, `decisions.py` |
| The data folder keeps the last 10 captures per class (`sync.kept_captures`), so there is no day-by-day history of statuses | Same commit: `config/template.toml` |
| `EventSpec` has no extended properties; `CalendarClient` has `get`, `insert`, `update`, `delete`, `upsert`, and no listing; `MAX_REMINDERS = 5`, `MAX_REMINDER_MINUTES = 40320` (28 days) | Same commit: `src/alfabeta/google/calendar.py` |
| `events.list` filters on private extended properties as `propertyName=value`; returns at most 2,500 events a page; leaves out cancelled events unless `showDeleted=true`; `calendar.events` authorises it | Calendar API reference, `events/list`, read 2026-10-28 |
| Reading or changing a calendar's sharing (`acl.list`) needs `calendar`, `calendar.acls` or `calendar.acls.readonly`; the student's link holds `calendar.events` only | Calendar API reference, `acl/list`, read 2026-10-28; spec 004 R4 |
| An event created by another account takes a reminder set as the student; a deleted id comes back from `get` as `cancelled`, an insert of it gets 409, and an update with `status: confirmed` restores it | Spec 004 research, Observed facts, measured 2026-10-27 |
| The family calendar already holds all-day events written through the chat connector's account; the spec 004 probe patched one of them and restored it | Same row of spec 004's research |
| Delivery of a reminder set as the student's Gmail to the student's phone is unverified | Spec 004 research, Observed facts, corrected twice on 2026-10-27 (julioarguello/alfabeta#38, #39) |
| Spec 002 FR-026 puts two links in an exam event's description; spec 002 has no plan yet | `specs/002-study-pack/spec.md`, same commit |

## R1 — The input: the agenda, plus one key

- **Decision**: read `agenda.json`, spec 001's contract for this epic. Add one key per entry,
  `posted`, the item's posting date (`YYYY-MM-DD`), and bump `version` to 2. A detected exam takes
  its origin item's posting date. The key is added to `agenda.py`, both copies of the schema (the
  contract in `specs/001-classroom-sync/contracts/` and the package's `src/alfabeta/schemas/`) and
  spec 001's data model, in slice 1.
- **Rationale**: FR-007's start date is the posting date. For a material or an announcement the
  agenda's `date` already is it; for an assignment, a quiz or an exam it is not there. The agenda is
  regenerated on every run from the state, so the new version replaces the old one the next run.
  Spec 002's `exam prep` reads entries by key, so an added key changes nothing for it.
- **FR-016 reads the title only.** The agenda carries no description, and the one measured case is a
  title. Adding the first line of every description to the agenda for a form never measured there
  would put more of the teacher's text in a second file for no case. Recorded in the spec's
  Clarifications (Plan, 2026-10-28).
- **Alternatives**: read `data/state.json` items directly, which ties this spec to spec 001's
  internal store; build the agenda in process with `AgendaBuilder`, which also lacks the posting
  date and would need spec 001's decisions and captures loaded here.

## R2 — The timetable and the class mapping

- **Decision**: FR-013's mapping of classes to subjects is spec 001's `class_link` decision, already
  by class id. The timetable is a `[[timetable]]` array of sessions, each `weekday`, `start`, `end`
  and `subject`, where `subject` is a `[[subjects]]` folder. `[calendar]` gains `home_slot`
  (the student's own time), `break_start` and `break_end` (the school's break), `warnings`
  (`false`) and `enabled` (`false`): every value lives in the private configuration.
- **Validation** (a configuration problem named by its key, never its value, as spec 001's loader
  does): weekday is one of the seven English names; times are `HH:MM`; `end` after `start`; the
  subject is a configured folder; two sessions of one subject on one weekday are a warning, not an error,
  and placement uses the first (the spec's assumption holds for 2026–2027; another student's
  timetable must still load, principle I); the break and every session
  end the same day.
- **Rationale**: the agenda already speaks in subject folders; a second mapping by class id would be
  a second declaration of the same fact. A linked subject with no session is valid: its events sit
  at break time and each run names the subject (the spec's edge case). The items of an unlinked class
  are not in the agenda at all.

## R3 — Placement

Every event is timed in `Europe/Madrid`, never all-day, and never crosses midnight: every
placement is clamped to start no earlier than 00:00 and end no later than 24:00 of its day (an exam
at 23:59 is 23:59–24:00).

| What | Where | Label in the description |
|---|---|---|
| A posting (material, assignment, quiz) | Its subject's session on the posting date; else break time | «Hora de la clase, no la de publicación» |
| A due date without a time, and an inferred one | Its subject's session on the due date; else break time | «Classroom no indica hora» (inferred: «Fecha deducida de «…»») |
| A due date with a time | 30 minutes ending at the due instant, starting no earlier than 00:00 that day | none: the time is Classroom's |
| An exam without a time | Its subject's session that day; else break time | «Hora según horario» · «Hora no conocida» |
| An exam with a time (a Classroom item's date, or a detected exam's) | From that time to the end of its subject's session if the session holds that time; else 30 minutes, ending no later than 24:00 | «Hora según Classroom» |

- **Announcements get no event.** FR-018 names material and assignments; an announcement's fact for
  the calendar is the exam it may announce, which gets its own event. A quiz is placed and warned
  like an assignment: it has a due date and a status.
- **An exam with a time** is a case FR-014 does not name: a detected exam's date can carry a time
  when the announcement or the family's correction gives one. Placing it at the stated time keeps
  the fact; recorded in the spec's Clarifications (Plan, 2026-10-28).
- **The holiday case**: the timetable has no holiday calendar, so a session on a public holiday is
  still a session. The event says it is the timetable's hour, and the family can see the day.

## R4 — The rule's arithmetic

- **Ring instants**: each step of FR-006 and FR-015 is a day `d`; its instant is `d` at
  `home_slot` in `Europe/Madrid`, built with `ZoneInfo`, never with an offset.
- **The bound**: a reminder cannot ring after its event starts, and a timed due's event starts 30
  minutes before the due instant. The last step is therefore the last home slot at or before the
  event's start and strictly before the due instant (FR-005's cutoff for a date-only due). Without
  this, a due at 16:10 would put the last warning at 16:00 inside its own event. Recorded in the
  spec's Clarifications.
- **The 28-day limit**: Google allows at most 40,320 minutes (28 days) between a reminder and its
  event's start. The 28-days-before step exceeds it whenever the event starts after the home slot on
  the due day. That step then moves to the next day's home slot. Recorded in the spec's
  Clarifications; no other step comes near the limit.
- **Minutes**: `reminder minutes = (event start − ring instant)` in whole minutes, both instants
  zone-aware. A step across a daylight-saving change still rings at 16:00 local. Fixtures at
  2026-10-25 and 2027-03-28 cover both directions (SC-007).
- **The basis instant** makes reminders a function of the item, not of the clock (FR-012, SC-005).
  Each item's record keeps `basis_at`, the instant of the run that first saw its current due date
  while not handed in. A step whose instant is not after `basis_at` is dropped. If every step is
  dropped and a home slot lies between `basis_at` and the bound, that one home slot is the item's
  only warning (FR-009); if none does, the item has no warning and that run names it (FR-020). A
  later run computes the same set, so it writes nothing.
- `basis_at` is set again when the due date changes (FR-011) and when the item goes from handed in
  back to not handed in (the student undid «Marcar como completada»), so steps that passed in
  between are not put back.
- **The start date** (FR-007) is `posted`, unless the item's record shows a run that saw it with no
  due date: then it is the date of the first run that saw the due date. «Última modificación» is not
  read. A first run has no earlier record, so it uses `posted`.

## R5 — Identity, ownership and one listing per run

- **Decision**: each event's id is `event_id("alfabeta|<student>|<item>|<kind>")` (spec 004's
  base32hex of SHA-256), `kind` one of `posted`, `due`, `exam`. Each event carries
  `extendedProperties.private` `{alfabeta: "<student>", kind, item}`. A run lists its owned events of
  the school year with one paged `events.list` (`privateExtendedProperty=alfabeta=<student>`,
  `singleEvents`, 2,500 a page), compares the owned fields locally, and writes only the ones that
  differ: insert a missing one (a 409 is a cancelled copy, brought back with `status: confirmed`,
  spec 004 R5), patch a different one.
- **The school year's bounds** for the listing: from 1 September of `student.school_year`'s first
  year to 1 September of its second, 00:00 `Europe/Madrid`, as spec 001's dates read a year.
- **Patch, not update.** Spec 004's `CalendarClient.update` sends `PUT`, which replaces the whole
  event and would clear a colour the family set. Slice 1 changes it to `PATCH` with the owned fields
  only, as spec 004 T018–T019 first specified; bringing back a cancelled copy patches `status` too.
- **Rationale**: `upsert`'s one `get` per event would be several hundred reads a run by spring. One listing reads the
  same and costs one request a page. The private property also tells an owned event from a legacy
  or family one without trusting titles.
- **The owned fields** are spec 004's (summary, description, start, end, reminders) plus the private
  property. A hand edit of an owned field is overwritten by the next run; a field alfabeta does not
  own (colour, attendees, the family's own notes in another event) is never touched.
- **The student id in the key and in the property** keeps two students apart if their
  configurations ever named one calendar (I): a run lists, compares and marks only its own
  student's events. It is the opaque id of `--student`, never a name.

## R6 — The records

- **Decision**: `data/calendar/items.json` holds, per item id, `due` (the last due value seen, ISO or
  null), `start_on`, `basis_at`, `undated_seen_on` and `marked`, plus the instant of the first
  applied run (`first_apply_at`, research R7). `data/calendar/delivery.json` holds, per
  account alias, the date the family saw a reminder ring on the student's phone (FR-019). Both are
  written atomically with mode 0600, and only when their bytes change.
- **Rationale**: the agenda carries no history and carries no timestamp by design; the facts FR-007
  and R4 need (when a due date was first seen) belong to the calendar, so they live with it. They
  are data (constitution II), never configuration.
- **A cloud run later** (spec 001 FR-036) would keep these records in its shared data home; this
  plan writes them on the Mac only.

## R7 — What disappears, and the legacy events

- **An item that leaves the agenda** (withdrawn from Classroom, spec 001 FR-027), **a due date
  Classroom no longer shows**, and **an exam the family discarded**: the owned event stays, loses its
  reminders, and its title starts «Retirado ·». The description says only «Ya no figura en la agenda»: the agenda drops withdrawn items, discarded
  exams and detected exams waiting for the family's re-confirmation alike, without saying why, so
  naming a reason would state a fact alfabeta does not have. A detected exam that comes back gets its
  event and reminders back. The run counts
  them. Nothing is deleted (V).
- **A moved due date** moves the same event (same id) and recomputes its reminders (FR-011).
- **Legacy events**: the events the chat connector wrote before spec 004. `calendar legacy` selects
  only events of the school year that hold all three marks: no alfabeta property, all-day (a
  `start.date`, no `start.dateTime`), and `created` before alfabeta's first applied run
  (`first_apply_at`). A timed event, or one created later, is never selected, so an event the
  family adds by hand after that run is out of reach. A selected event matches when one owned event
  holds the same fact: the same date in `Europe/Madrid` and the item's Classroom title contained in
  its title. Dates and titles go only to `data/calendar/legacy-<run>.json`; the command prints counts.
- **The family reviews before anything goes.** `--apply` takes the report the family read
  (`--report legacy-<run>.json`) and deletes only the events it lists as `matched` and that still
  match; it re-reads each one first. Unmatched ones are never touched. No run calls it.
- **Alternatives**: delete every event without the property, which would remove what the family adds
  by hand; leave the legacy events, which shows every fact twice and keeps all-day events FR-023
  forbids; ask the operator to delete them by hand, which the operator declined for this project.

## R8 — Exams

- **Decision**: an exam is an agenda entry with `category: exam`: a Classroom item whose title names
  a test, or an exam detected from a stream or material text, with the family's correction
  prevailing (spec 001 FR-020b). An entry in `list: done` (the exam took place) keeps its event and
  has no reminders left to ring.
- **FR-014's "and from the family"** means the family's correction of a detected exam. No path lets
  the family declare an exam that Classroom does not show (Observed facts), and the calendar's
  standing rule is that it holds only facts from Classroom. An exam announced only orally therefore
  reaches the calendar only if the family adds it by hand, as an event alfabeta does not own and
  never touches. Recorded in the spec's Clarifications (Plan, 2026-10-28).
- **A detected exam says so**: its description carries «Detectado en un aviso de Classroom», and
  «Corregido por la familia» when corrected, as `agenda.md` marks it «detectado». A detected entry
  owns an `exam` event only when its category is `exam`; corrected into another category it owns
  none, because its origin item already owns its own events.
- **Its warnings** (FR-015): 7 days before and the evening before, at the home slot, with R4's bound,
  basis and catch-up. The start date for dropping a step is the posting date of the item that
  announced it.

## R9 — Reading "for Thursday" (FR-016)

- **Decision**: the title only (R1). A purpose form with a weekday, per language of
  `student.languages`: Basque `<weekday>rako` (`ostegunerako`), Spanish `para el <weekday>`, English
  `for <weekday>`, case- and accent-insensitive. Each language's weekday names are a table in the
  code. The subject must have a session that weekday; the result is the next session of it strictly
  after the posting date and within 7 days. Anything else infers nothing.
- **Rationale**: the measured case is one title; the three wrong candidates were "today" in a
  description and a title naming the day it was posted with no purpose form. Requiring the purpose
  form and the session rules them out (SC-004).
- **An inferred date** is a date-only due: placed in that session, warned with FR-005's cutoff, and
  its description says «Fecha deducida de «<words>»». It is recomputed each run from the title;
  nothing is stored.

## R10 — Replay

- **Decision**: `calendar replay --from <date> --to <date>` simulates one run a day at the sync time
  `[schedule]` gives that weekday (or `--at HH:MM`), over the agenda's entries, and never calls Google.
  Each simulated day sees the entries whose `posted` is on or before it (the agenda holds no posting
  hour, so an item posted that day counts as seen by that day's run, an optimistic assumption), with no status (the past statuses are not kept,
  Observed facts). `--first-run <date>` instead simulates one run on that date with today's
  statuses. It prints weekly counts of reminders, of days with a reminder and of all events (SC-003),
  plus the checks of SC-001, SC-002, SC-004, SC-008 and SC-010, by opaque id.
- **Rationale**: the success criteria are measured on the real capture, which cannot be a test
  fixture (III). A replay on the Mac measures them and keeps the result to counts and ids. The tests
  run the same code on invented agendas.
- **The reference numbers move.** `--first-run 2026-10-26` takes the items posted by that date with
  the statuses the state holds when the replay runs, which are later than the capture's. SC-001
  passes when `past_due_warned` and `handed_in_warned` are 0 and the `control` counts are not: the
  control proves the check can fire. The capture's 16 and 7 are recorded beside the state's own
  control counts, not required to match them. SC-002, SC-004 and SC-008 do not depend on statuses,
  so they reproduce.

- **The sync's hour matters.** A replay simulates the runs at `[schedule]`'s times, so a time after
  `home_slot` loses every next-morning warning. `config check` warns when a weekday's `[schedule]`
  time is after `home_slot`, and quickstart step 5 passes `--at` explicitly.

## R11 — Output and the family's words

- **Decision**: JSON on stdout with counts and opaque ids; one Spanish line per fact the family must
  act on, on stderr: subjects with dated work and no session, items seen too late for any warning,
  events marked «Retirado ·», and the delivery state («Entrega de avisos no comprobada» until a
  check is on record). No title, address, calendar id or path is printed.
- **Event text** is in Spanish ([contracts/events.md](contracts/events.md)), restates facts only, and
  carries the Classroom link and the item's folder as its path relative to the student's base
  folder, the same path the folder has in the Drive. Not a Drive link: a link depends on the Drive's
  live state (`ScopedDrive` walks the tree each run), so a late upload would rewrite the event with
  no change in Classroom (FR-012) and a Drive error would block the calendar (VII).

## R12 — The switch and the delivery check

- **Decision**: `[calendar] warnings = false` in the template. While false, events are written with
  no reminders and the run says the warnings are off. `calendar delivery --account <alias> --seen-on
  <date>` records the family's check; every run states whether a check is on record. The code does
  not refuse to write reminders without one (US6, scenario 1): gate 1 and slice 6 order the steps,
  and the run's line keeps the gap visible.
- **What the family records** is what they saw, in their own words. In an issue or the repository:
  the date and the account's alias only, no address and nothing that identifies the device; the
  device and the account's details stay in the private data folder (constitution III). An alias is
  never a name: it says the account's role (`student`). A pre-written answer is not a measurement (spec 004's correction of 2026-10-27).

## R13 — Neighbouring specs

- **Spec 002 FR-025** says alfabeta writes no reminders. This spec changes that to "no study blocks;
  warnings that restate facts only". The edit is made with this plan, as are the roadmap's Calendar
  section and the `study-pack` skill's line, so that `main` never holds two contradicting specs.
- **Spec 002 FR-026** (two links in an exam event's description) needs this spec's writer: the
  description is an owned field, so a link another writer adds is overwritten by the next run. When
  spec 002 is planned, it passes its links to `events_for()`; this plan builds no hook for a plan that
  does not exist.
- **Spec 001 FR-011b and constitution VII** (the calendar shared with every account in
  `calendar.shared_with`, and with no other): the student's link cannot read or change sharing
  (Observed facts), and spec 004 R5 keeps sharing a step the operator does by hand. The check is
  therefore the family's, by hand, in quickstart step 1: the calendar's sharing settings list
  exactly the accounts of `calendar.shared_with`, each able to see all event details, recorded
  with its date (T019). `calendar sharing --checked-on <date>` records that check with a hash of
  `calendar.shared_with`; every run says «Comprobar con quién se comparte el calendario» while the
  list's hash differs from the recorded one, so a change to the list asks for the check again.
  Adding `calendar.acls.readonly` so a run could check it would mean linking
  the student's Gmail again, with a parent's approval, for a list that changes about once a year;
  not chosen.
- **Spec 001 FR-020a** (one colour per category) stays out, as the spec says.
- **Spec 004 T022** (the chat connector's account leaves the calendar's sharing) comes before the
  first `calendar sync --apply`: legacy selection takes only events created before that run, so a
  connector event written later could never be cleaned up.
