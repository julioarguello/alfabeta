# Contract: the events alfabeta writes

What the family reads in the calendar, in Spanish. Every event restates facts from the agenda: no
advice («empieza hoy», «date prisa»), no priority alfabeta made up, no estimated effort (FR-003,
US7). `<Asignatura>` is the subject's folder name; `<título>` is the Classroom title as captured,
whitespace collapsed.

## Titles

| Event | Title |
|---|---|
| Posting | `Publicado · <Asignatura> · <título>` |
| Due date, not handed in | `Entrega · <Asignatura> · <título>` |
| Due date, handed in («Entregado», «Calificado», «Entregado con retraso») | `Entregado · <Asignatura> · <título>` |
| Exam | `Examen · <Asignatura> · <título>` |
| Any of the above whose fact left Classroom | `Retirado · ` + the title it had |

A reminder shows only the title and the time (FR-003), so the title alone says what and for which
subject; the reminder's time says when.

## Description

One line per fact that applies, in this order:

| Line | When |
|---|---|
| `Entrega: <13 oct>` or `Entrega: <13 oct, 8:00>` | A due-date event, as spec 001's agenda shows dates |
| `Examen: <13 oct>` or `Examen: <13 oct, 10:30>` | An exam event |
| `Publicado: <8 oct>` | A posting event |
| `Classroom no indica hora` | A date-only due (FR-005) |
| `Fecha deducida de «<palabras>»` | An inferred due (FR-016) |
| `Hora de la clase, no la de publicación` | A posting (FR-018) |
| `Hora según horario` · `Hora no conocida` · `Hora según Classroom` | An exam (FR-014, research R3) |
| `Detectado en un aviso de Classroom` · `Corregido por la familia` | A detected exam; the second when the family corrected it (research R8) |
| `Ya no figura en la agenda` | A «Retirado» event: the agenda no longer holds its fact, for whatever reason (research R7) |
| `Classroom: <link>` | Always; it opens with the school account (spec 001) |
| `Carpeta: <path relative to the base folder>` | When the item has a folder; the same path as in the Drive (research R11) |

## Reminders

`reminders.useDefault` is always `false`. Overrides are `popup`, one per warning
([data model, Step and Warning](../data-model.md#step-and-warning)), none on a posting event, none
while `[calendar] warnings` is `false`.

## Private extended properties

`alfabeta: "<student>"` (the opaque `--student` id), `kind: posted|due|exam`, `item: <agenda item id>`. They are how a run finds its own
events (research R5); they hold no student data.
