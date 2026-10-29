# Contract: `calendar` subcommands of `python -m alfabeta`

These follow spec 001's [command contract](../../001-classroom-sync/contracts/cli.md) and spec 004's
[Google subcommands](../../004-google-connection/contracts/cli.md):

- `--home` comes before the subcommand, and `--student <id>` is resolved once;
- JSON goes to stdout and lines for people, in Spanish, to stderr;
- no message shows an address, a token, the calendar id, an event title or an absolute path. Items
  are named by their agenda id abbreviated as spec 001's messages abbreviate Classroom ids, subjects
  by their folder.

| Subcommand | What it does | Writes to | Output | Codes |
|---|---|---|---|---|
| `calendar sync --student <id> [--apply]` | Reads the agenda and the records, lists the owned events, and computes what to create, update and mark. Without `--apply` it writes nothing (a dry run). With it, writes the differences and the records | the family calendar, `data/calendar/items.json`, a `type: calendar` line in `data/log.jsonl` | JSON `{ok, applied, created, updated, marked, unchanged, warnings_on, delivery, late:[item], no_session:[subject]}` | 0 (also `disabled` when `[calendar] enabled` is false) · 1 `no_agenda`, `old_agenda`, `no_student_account`, config problem · 2 link not `ok` · 3 some writes failed (the others done) |
| `calendar replay --student <id> --from <date> --to <date> [--at HH:MM]` | Research R10's day-by-day simulation. Never calls Google, writes nothing | — | JSON `{ok, weeks:[{week, reminders, reminder_days, events}], checks:{past_due_warned, handed_in_warned, control:{past_due, handed_in}, unwarned:[item], inferred:[item], all_day, cross_midnight}}`. `control` counts the warnings the same run would write without FR-005 and FR-010, so a check that cannot fire shows | 0 · 1 |
| `calendar replay --student <id> --first-run <date>` | One simulated first run on that date with today's statuses (SC-001) | — | the same JSON for that one run | 0 · 1 |
| `calendar delivery --student <id> --account <alias> --seen-on <date>` | Records the date the family saw a reminder, set as that account, ring on the student's phone (FR-019) | `data/calendar/delivery.json` | JSON `{ok, alias, seen_on}` | 0 · 1 `not_student_account` |
| `calendar sharing --student <id> --checked-on <date>` | Records that the family checked the calendar's sharing against `calendar.shared_with` by hand (research R13) | `data/calendar/sharing.json` | JSON `{ok, checked_on}` | 0 |
| `calendar legacy --student <id> [--apply --report <file>]` | Research R7: selects the school year's all-day events without alfabeta's property created before its first applied run, and matches each to an owned event of the same fact. With `--apply`, deletes only the events the reviewed report lists as matched and that still match | `data/calendar/legacy-<run>.json`; with `--apply`, the family calendar and a `type: calendar_legacy` line in `data/log.jsonl` | JSON `{ok, matched, unmatched, deleted}` (counts) | 0 · 2 link not `ok` · 3 a deletion failed |

`calendar probe` and `calendar probe-clean` stay as spec 004 defines them.

**The run**: spec 001's sync calls `google check` first (spec 004 T016) and, after the agenda is
written, `calendar sync --apply` (slice 5). Code 2 or 3 makes the run report the calendar as failed
and lets every other output finish (constitution VII).

**Lines for the family** (stderr), each only when it applies:

- `Avisos apagados: los eventos se escriben sin recordatorios.`
- `Entrega de avisos no comprobada en el móvil del estudiante.` or `Entrega de avisos comprobada el <fecha>.`
- `<n> tareas vistas demasiado tarde para avisar.`
- `Sin clase en el horario: <asignatura>, <asignatura>.`
- `<n> eventos marcados «Retirado».`
- `Comprobar con quién se comparte el calendario.` (no check on record, or `calendar.shared_with` changed since)
