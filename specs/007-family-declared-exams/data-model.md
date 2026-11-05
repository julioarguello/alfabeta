# Data model: Exams the family declares that Classroom does not announce

Everything here extends spec 001's [data model](../001-classroom-sync/data-model.md). Examples are invented.

## Decisions (`data/decisions.json`)

### `declared_exam`

| Field | Rule |
|---|---|
| `origin` | `declared-<n>`, one more than the `declared_exam` records ever written. Never reused |
| `target.subject` | A `[[subjects]] folder` |
| `target.date` | `YYYY-MM-DD`, inside the school year |
| `target.title` | The family's text, or empty |
| `state` | `confirmed` from the first line; `superseded` only if a later format needs it. Cancelling is a correction, not a state |
| `date` | The day it was declared. It is the entry's `posted` (research R9) |
| `reason`, `confidence` | `declared by the family`, none |

Not in `PROPOSABLE`, so Claude cannot propose it and `decision confirm` does not take it.

### `exam_correction` over a declared exam

As over a detected exam, with its origin the declared id: `target.date`, or `target.discarded = "true"`.
Corrections merge; a date on a discarded exam brings it back. `target.category` is refused.

### Active, and the effective date

A declared exam is **active** while it is in force and its corrections have not discarded it. A cancelled exam is
in force but not active: it holds no date, is not matched and takes part in no notice. Its **effective date** is the
`date` of the table under «Agenda entry». FR-004, the correction's check and the match all use these two.

### `exam_match`

| Field | Rule |
|---|---|
| `origin` | The Classroom exam entry's id: an item, or `<item>#exam-<k>` |
| `target.declared` | The declared id |
| `state` | `confirmed`; `superseded` when the match ends |
| `date` | The day it was recorded |

One in force per Classroom entry; several may point to one declared exam. The first in file order gives the
merged entry its title, link, folder and status. Not in `PROPOSABLE`.

**Recording** (`declared.py`, called under the lock by every command that rebuilds the agenda: `agenda build`,
`classroom apply`, `exam create`, `decision update-exam`):

1. Build the Classroom exam entries, as today.
2. Supersede a match whose Classroom entry is no longer an exam of the agenda, whose declared exam is no longer
   active, or which is not the first and whose entry no longer shares the effective date's day.
3. For each active declared exam, record a match with every entry of its subject on its effective date's day in
   `Europe/Madrid` that has none.

The same run's second pass, and the next run with no change, write nothing (FR-024).

## Agenda entry

One new key beside spec 003's `posted`, in `agenda.schema.json`:

| Field | Rule |
|---|---|
| `declared` | `true` when the family declared the exam |

Its version: research R9.

For a declared entry:

| Field | Unmatched | Matched |
|---|---|---|
| `item` | `declared-<n>` | `declared-<n>` |
| `subject` | The declaration's | The declaration's |
| `category` | `exam` | `exam` |
| `title` | The family's, or empty | The first match's |
| `date` | The family's, with its corrections | A correction later in the file than the match, else the first match's, else, when that has no date, the family's |
| `date_only` | `true` | The date's own |
| `posted` | The day it was declared | The day it was declared |
| `status` | Empty | The first match's |
| `list` | R10: `pending` until any capture is later than the date, then `done` | Spec 001 FR-020c on the first match's status and this entry's `date`, with any capture (R10): handed in is `done`, `missing_per_teacher` stays `pending` |
| `detected`, `origin` | `false`, empty | `true` and the source item when a detected exam is among the matches, preferring one whose item has an `#announcement` replica; otherwise `false`, empty |
| `corrected` | `true` after a date correction | `true` after a date correction, or if a match carries one |
| `classroom_link`, `folder` | Empty | The first match's |
| `declared` | `true` | `true` |

An entry with a match is not listed on its own. A discarded declared exam has no entry, and its matches end, so
Classroom's entries return under their own ids (FR-014).

`agenda.md`, with parts that are empty left out:
`<fecha> · <Asignatura> · examen · <título> · <estado> · detectado · corregido · declarado por la familia · [Classroom](…) · [carpeta](…)`.

## Notices

Lines at the top of `agenda.md`, never in `agenda.json`, while the exams named are in «Pendiente»:

| Condition | Line |
|---|---|
| A Classroom exam of the subject with another date, up to 14 days away | `Examen de <Asignatura>: la familia dijo <fecha> y Classroom dice <fecha>.` |
| A Classroom exam of the subject with no date | `Examen de <Asignatura>: la familia dijo <fecha> y Classroom anuncia uno sin fecha.` |
| A matched entry whose family correction differs from Classroom's date | `Examen de <Asignatura>: la familia corrigió a <fecha> y Classroom dice <fecha>.` |
| Two active declared exams of the subject on one day, after a teacher's move | `Examen de <Asignatura>: hay dos declarados el <fecha>.` |

A notice holds the date, like the rest of `agenda.md`, in the family's folder only.

## Exam (`exam build`)

`day`, `announcement` and `announced` may each be empty; `announcement` and `announced` are empty together.

| Field | With no value |
|---|---|
| `day` | «sin fecha» in the file's name and the moment; `exam_date` and the pack record's `exam` are empty |
| `announcement` | The prompts of [contracts/prompts.md](contracts/prompts.md); the answer says `announced: false` |

## State transitions of a declared exam

| From | Event | To |
|---|---|---|
| Nothing | `exam create` | Declared |
| Declared | `decision update-exam --date` | Declared, «corregido» |
| Declared | A Classroom exam of the subject on that day | Matched |
| Matched | The teacher moves it, or `decision update-exam --date` | Matched |
| Matched | Every Classroom entry leaves the agenda | Declared |
| Declared or Matched | `decision update-exam --discard` | Cancelled |
| Cancelled | `decision update-exam --date` | Declared |
