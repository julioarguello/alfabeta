# Research: Exams the family declares that Classroom does not announce

No technical unknown stood open after the spec's clarifications. Each entry records a choice the spec
left to the plan, read against the code on `main` at the plan's date.

## R1 — The command's name and place

- **Decision**: `exam create`, handled in `__main__.py` beside `_cmd_decisions` and dispatched before
  `exam_cli.cmd_exam_prep`, which today takes the whole `exam` group.
- **Rationale**: `create` is already in the vocabulary, "make one object"; `exam` names the noun. The
  command needs the lock and the agenda rewrite that live in `__main__.py`, not `exam/cli.py`'s
  notebook dependencies.
- **Alternatives**: a leaf `create-exam` under `decision`: with `update-exam` it would give one noun two
  suffixed verbs, which `cli-naming.md` forbids. update and delete leaves under `exam`: a second way to do what
  `decision update-exam` does, and a delete promises a removal that does not happen (constitution V).

## R2 — How `exam build` decides

- **Decision**: `find_exam` takes whether `--topic` was given, and returns an `Exam` whose `day`,
  `announcement` and `announced` may be empty:

  | Announcement found on the exam's day | `--topic` | Result |
  |---|---|---|
  | yes | either | As today |
  | no, and an agenda exam on that day | no | Refuses `no_announcement` |
  | no, and no agenda exam on that day | no | Refuses `no_exam` |
  | no | yes | Proceeds with no announcement, for `--exam`, else the next exam in the agenda, else undated |
  | not looked at | `--undated` with it | Proceeds undated, whatever the agenda holds |

  `topic_folders` learns whether an announcement exists: without one, `--topic` may name several topics of any
  kind, each with its notebook and an equal part of the slot. A paper exam can span whole topics, and the
  family's «the topics» meant that. With an announcement, `no_topic` stands, as
  `test_topics_that_are_not_distinct_subtopics_of_one_topic_are_refused` holds.

- **Rationale**: naming a topic is a new statement by the family. The default "most recent topic" stays
  behind an announcement, so a command typed with no thought never prints a whole-topic sheet by chance.
  `--undated` exists because with a dated exam of the subject to come, Q8's preparation would be unreachable, and
  that exam's announcement would override the topics named. It is in `tests/test_cli_naming.py`'s `PLANNED_OPTIONS`.
- **Alternatives**: a flag such as `--no-announcement`: one more word for what `--topic` already says when the
  exam has none.
- **Checked against the tests**: the `no_exam` and `no_announcement` refusals of `tests/test_exam_prep.py`
  pass no `--topic`, so they keep holding. `no_topic` and `subtopics_unnamed` do not change.

## R3 — The prompts with no announcement

- **Decision**: three new sections in `skills/study-pack/prompts.md`
  ([contracts/prompts.md](contracts/prompts.md)), and one placeholder, `{exam_name}`. The three existing
  texts do not change.
- **Rationale**: the announced theory prompt is built around `{scope}` («Qué entra», sections in the
  announcement's order, what does not enter). It also says «mañana», which a preparation days ahead or
  undated makes false. The rest of the new text follows it, with two differences. Constitution X's last
  bullet is written in: «Mandan los apuntes» alone would teach a wrong fact on a whole-topic sheet, since
  `exam build` read no `bloques.md`. So the new prompts tell the notebook the rule of FR-046, and take
  `{notes_corrections}`, which holds what the notebook could not know: corrections from an external reference. A
  deterministic read passes that section's lines verbatim, because no Claude is in this run. What the notes insist
  on or the sources disagree on goes to a last part, «Para la familia», since the printed sheet is the one channel
  this command has; a branch no source explains goes there too. A family's ruling reaches the sheet because
  FR-046 now moves the answered line to «Correcciones a los apuntes». And `{part}` gets its own variant, because the announced one refers to points of an
  announcement that does not exist here.
- **Not measured**: how the notebook does on them. Gate 1 of the plan is that measurement.
- **Alternatives**: filling `{scope}` with a sentence saying there is none: the prompt would then order
  sections by an announcement's points, and copy a false «anuncio».

## R4 — What an undated preparation is called

- **Decision**: «sin fecha» where the date goes: the file's `(<D> <mmm>)`, the moment «EXAMEN sin fecha»,
  and the title «Examen sin fecha». The pack record's `exam` and the answer's `exam_date` are empty.
- **Rationale**: `exam/` holds a second exam on a topic by its date in the name (spec 002, Clarifications).
  One undated pair per topic is the honest limit: a second undated run replaces it, as a second run on one
  date does today, and a dated run sits beside it.
- **Alternatives**: the day it was made: a date in a file's name that is not the exam's would be read as
  the exam's.
- **Constitution**: Storage says the date goes in each file's name. Amended to "the exam's date when it is
  known, else «sin fecha»" (2.7.0, MINOR: it allows what the sentence forbade, and an undated pair per topic
  gives up what the date guaranteed).

## R5 — A declaration is a decision

- **Decision**: a new `DecisionType.DECLARED_EXAM`, origin `declared-<n>`, target `subject`, `date` and
  `title`, in `confirmed` from its first line. `<n>` is one more than the number of such records ever
  written, superseded ones included. It is not in `PROPOSABLE`.
- **Rationale**: `decisions.json` already holds what only the family says, keeps its history and feeds the
  agenda builder. Its `(type, origin)` key gives the stable id. Keeping it out of `PROPOSABLE` makes
  `decision propose`, `decision confirm` and `decision update-target` refuse it by their own checks.
- **Alternatives**: a file of its own, which would need its own atomic writes, history and lock.

## R6 — Correcting and cancelling

- **Decision**: `DecisionStore.correct` accepts an origin with a declared exam in force, and the rest of its
  rule holds: a correction merges with the one before; a date on a discarded exam brings it back.
  `--category` on a declared id exits 1, and so does a date another active declared exam holds as its effective
  date (FR-004). `--date` is parsed in the handler, so a malformed value exits 1 and is not echoed (FR-002); the
  parser's `type=` today exits 2 and prints it.
- **Rationale**: the family has one correction command, and `exam_correction` already means this.
- **Consequence**: `decision update-exam` rewrites the agenda for a declared id (FR-009). A detected exam's
  correction keeps prevailing "in the following runs", unchanged.

## R7 — Which id survives a match, and why it is recorded

- **Decision**: the declared id survives. A match is an `exam_match` decision, origin the Classroom entry's
  id, target `declared`, written by the commands that rebuild the agenda, before they rebuild it.
- **Rationale**:
  - Spec 003's event id comes from `item`, and research R7 there titles «Retirado ·» an event whose item
    leaves the agenda. If the Classroom id survived, every match would leave a «Retirado ·» event beside a
    live exam, on the same day. With the declared id the one event moves.
  - A rule recomputed on each run would break the pair when the teacher moves the exam, leaving the family's
    old date as a second exam. Recorded, the entry follows the teacher (US3, scenario 2).
  - `AgendaBuilder` stays a pure function of the state and the decisions (spec 001 FR-020).
  - A match other than the first ends when its entry no longer shares the merged entry's day, or a moved
    Classroom date would hide behind a stale one (constitution V).
- **Checked against the consumers**:
  - `exam build` finds the announcement through the entry's `origin`. Today it tries every entry of the day;
    the merged entry has one, so it takes a detected exam whose item has an `#announcement` replica when
    there is one (SC-008).
  - `AgendaEntry.__post_init__` requires an origin exactly when `detected`: the merged entry takes both or
    neither.
- **Alternatives**: the Classroom id, for the reason above; `calendar` code re-keying the event: Google's
  event ids do not change, and the writer is not built.

## R8 — The notices, and the 14 days

- **Decision**: `declared.py` computes the notices for `AgendaBuilder`, added to the lines it already takes.
  One line per pair, while both are in «Pendiente»: a Classroom exam of the subject with no date, or a date
  up to 14 days from the declared one and not the same day.
- **Rationale**: spec 001's notice is exactly "a line while a condition holds", and never reaches `agenda.json`.
  The bound keeps next month's exam from raising a false alarm.
- **Not measured**: 14 days is a judgment (Q3). If it proves wrong it changes one constant.

## R9 — The agenda's schema

- **Decision**: a required boolean `declared`, and `classroom_link` documented as possibly empty. `agenda.md`'s
  line prints the link and the folder only when there are any, and drops an empty title.
- **Version and `posted`**: version 2 always carries `posted`, so spec 003's T016 gate stays right in either order.
  If this slice lands first, it also does spec 003's T003 and T004 and marks them, and `declared` goes in version 2.
  If T004 landed first, `declared` takes version 3. Either way a declared entry's `posted` is the day it was declared. `tests/test_contracts.py` keeps the two copies identical.
- **Consumers read**: `exam/prep.py` reads `category`, `subject`, `date` and `origin`, so a new key is harmless.

## R10 — When a declared exam is done

- **Decision**: «Hecho» once any capture of any class is later than its date, by `later_than`.
- **Rationale**: spec 001's rule uses the item's class because the item lives there. A declared exam has no
  class, and may belong to a subject with none linked. Any capture proves the same thing, and no rule uses
  the day the agenda is generated.
- **Matched entries**: spec 001 FR-020c applied to the first match's status and the entry's own date, with the same
  any capture (FR-011). Taking the list from the Classroom entry would show a family's later date in «Hecho» once
  Classroom's old date passed, and keep a first match with no date in «Pendiente» for ever.

## R11 — The writer (slice 3, written into spec 003 now)

- **Decision**:
  - ownership: a declared entry with a date owns one `exam` event, whether or not it is matched;
  - its `posted` is the declaration's date, which drops a `d7` on or before it, as an announcement's does;
  - its description gains `Declarado por la familia`, and the `Classroom:` line appears only with a link;
  - a label for its time follows spec 003 FR-014, and needs nothing new (Q2);
  - `calendar delete-legacy`'s match on the Classroom title never fires for an entry with no link: an empty
    title is contained in every title, which would select any all-day event that day (spec 003 research R7);
  - the count of FR-021 reads the events of that day once, when the writer first creates the declared
    exam's event, and writes `data/calendar/hand-<run>.json`.
- **Rationale**: once, not on each run: spec 003 keeps to one paged listing per run, and a second count of the
  same events tells the family nothing. It is a report and never a selection: `calendar delete-legacy`
  keeps its three marks, which exclude timed events.
- **Interim**: until the writer exists, the family may keep adding events by hand. After spec 004 T022 the chat
  connector cannot, as that task intends; the family can still add them in Google Calendar.

## R12 — What lands in this pull request

- **Decision**: specs and the calendar-policy sentences change here, as spec 003's own did. What describes
  behaviour a skill or a person would act on today (`skills/*/SKILL.md` on commands, `prompts.md`, the schema,
  code) lands with the slice that builds it, so `main` never instructs a command that refuses.
- **Rationale**: a skill is run by an agent that believes it; a spec is read as a design.
