# Contract: the commands of spec 007

This follows spec 001's [command contract](../../001-classroom-sync/contracts/cli.md): `--home` before the
subcommand, `--student <id>` resolved once, JSON on stdout, messages for people on stderr, and no message with a
date, a title, an address or an absolute path. The names follow `.claude/rules/cli-naming.md`.

## `exam create` (new, slice 2)

| Subcommand | What it does | Writes to | Output | Codes |
|---|---|---|---|---|
| `exam create --student <id> --subject <folder> --date YYYY-MM-DD [--title <text>]` | Declares an exam, unless the agenda already holds it, and rewrites the agenda. Needs the run's lock, as `decision update-exam` does: run with no lease it exits 1 `lock_not_held`. Claude takes the lock when the family asks in the chat | `data/decisions.json`; `agenda.json` and `agenda.md` if their bytes change | JSON below | 0 · 1 `no_subject`, `invalid_date` (malformed or outside the school year; the value is not echoed), a lock error |

```json
{"ok": true, "created": true, "item": "declared-1", "subject": "<folder>", "date": "YYYY-MM-DD",
 "weekday": "<día>", "weekend": false, "past": false, "agenda_written": true}
```

- `created: false` with `item` the id that holds it: an active declared exam, or a Classroom entry's id.
- `agenda_written: false` with a line on stderr when the base folder is missing; the decision is kept.
- `weekend` and `past` do not refuse. `past` compares with today in `Europe/Madrid` and reaches only this answer.

## `decision update-exam` (built, wider in slice 2)

`decision update-exam --student <id> --origin <id> (--date YYYY-MM-DD | --category <c> | --discard)`.

| With `--origin` a declared id | Result |
|---|---|
| `--date` | Records the correction, records or ends matches, and rewrites the agenda. Exit 1 `invalid_decision` if another active declared exam holds that subject and date, or the date is outside the school year |
| `--discard` | Takes it out of the agenda, ends its matches and rewrites the agenda |
| `--category` | Exit 1 `invalid_decision`: a declared exam is an exam or it is cancelled |

For a detected exam it behaves as today, with two additions: a date that puts a detected exam on an active declared
exam's day joins them at the next rebuild of the agenda, and for any origin `--date` is parsed in the handler, so a
malformed value exits 1 `invalid_decision` instead of 2, and is not echoed.

## `exam build` (built, wider in slice 1)

`exam build --student <id> --subject <folder> [--exam YYYY-MM-DD] [--slot HH:MM-HH:MM] [--topic <folder>]...`.
No new option. Which exam and which scope:

| An announcement on the exam's day | `--topic` | Result |
|---|---|---|
| Yes | Either | As spec 002's [contract](../../002-study-pack/contracts/cli.md) |
| No, an agenda exam that day | None | Exit 1 `no_announcement`; the message says to name the topics |
| No, no agenda exam that day | None | Exit 1 `no_exam`; the message says to name the topics |
| No | Given | Proceeds with the prompts of [prompts.md](prompts.md) over the topics named |

The exam's day is `--exam`, else the subject's next exam in the agenda, else there is none.

With no announcement `--topic` may be given several times, for topics of any kind; each gets its notebook, its sheets
and an equal part of the slot.

Output: spec 002's, plus a top-level `announced` (boolean). `exam_date` is `null` with no day.

Files with no day: `exam/Teoría para el examen · TNN[X] (sin fecha).pdf` and
`exam/Problemas tipo · TNN[X] (sin fecha).pdf`. Pieces in the notebook: `EXAMEN sin fecha <n> · …`.

## `calendar sync` (spec 003, in slice 3)

The first time it creates a declared exam's event, it counts the events of that day with no alfabeta mark and
«examen» in their title, ignoring case. Its JSON gains `hand_events`, a count; the dates and titles go only to
`data/calendar/hand-<run>.json`, and it changes none of those events.
