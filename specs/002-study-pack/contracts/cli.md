# Contract: `exam prep`

This follows spec 001's [command contract](../../001-classroom-sync/contracts/cli.md) and spec
005's [subcommands](../../005-notes-to-notebook/contracts/cli.md): `--home` before the subcommand,
`--student <id>` resolved once, JSON on stdout, messages for people on stderr, and no message with
an address, a Drive id, a notebook id or an absolute path. It implements spec 002's User Story 7
(FR-029 to FR-037); the code is julioarguello/alfabeta#106.

| Subcommand | Runs on | What it does | Writes to | Output | Codes |
|---|---|---|---|---|---|
| `exam prep --student <id> --subject <folder> [--exam YYYY-MM-DD] [--slot HH:MM-HH:MM]` | Mac | Asks the exam topic's notebook for the theory sheet and the problems sheet with the fixed prompts, regenerating the study guide first when it is stale, and prints both into the topic folder | the notebook (two reports; the study guide when stale), the topic folder, the mirrors | JSON `{ok, exam_date, topic, guide_regenerated, slot_minutes, pages_allowed, sheets:[{kind, printed, pages}]}`; `kind` is `theory` or `problems`, `topic` an opaque index, never a name or id | 0 · 1 `notebook_disabled`, `no_exam`, `no_announcement`, `no_notebook` · 3 a report never completed or did not print · 5 `nlm` not usable |

**Arguments**:

- `--subject`: the subject's `[[subjects]] folder`.
- `--exam`: the exam's date. Without it, the subject's next exam in the agenda, today included.
- `--slot`: the study slot. Its length sets the theory sheet's pages, four per 90 minutes rounded
  up (measured once, 2026-10-28), and its clock times go into the plan. Without it, 90 minutes and
  a plan in minutes from the start.

**What it does, in order** (each step runs only if the one before succeeded):

1. Checks the configuration as `config check` does. With `notebook.enabled = false` it stops:
   `notebook_disabled`, code 1.
2. Checks that `nlm` is signed in for `notebook.nlm_profile`, and that this is `nlm`'s default
   profile, which `nlm download` reads; otherwise code 5, saying which.
3. Finds the exam: an `exam` item of the subject in spec 001's agenda, on `--exam` or the next one;
   none is `no_exam`. Takes its announcement's captured text and date; none is `no_announcement`.
   Both are code 1, and nothing has been asked of the notebook.
4. Finds the topic: the folder the announcement was placed in, or else the subject's most recent
   topic folder (FR-023), saying so on stderr; then its notebook, by `notebook.title_pattern`. No
   notebook is `no_notebook`, code 1.
5. Compares the newest `apuntes/* · transcripción.md` with the creation time of the topic's study
   guide (`nlm studio status --full --json`). When the transcription is newer, or there is no
   guide, it generates one (`--format 'Study Guide' --language es`), waits for it, and deletes the
   old one, so one guide is live (FR-033).
6. Asks for the two reports, `nlm report create <nb> --format "Create Your Own" --language es
   --prompt <prompt> --profile <profile> -y`, with the prompts «Theory sheet — for an exam» and
   «Problems sheet — for an exam» of [`prompts.md`](../../../skills/study-pack/prompts.md), every
   placeholder filled. It waits as the pack does (`nlm studio status`). A report that never
   completes is code 3; the other one is still printed.
7. Titles each one as a piece of the moment `EXAMEN <weekday>` (FR-014):
   `EXAMEN <weekday> 1 · Teoría para el examen · <topic>` and
   `EXAMEN <weekday> 2 · Problemas tipo · <topic>`.
8. Downloads each report and prints it with `print_pack.py report` into the topic folder as
   `Teoría para el examen · TNN (<D> <mmm>).pdf` and `Problemas tipo · TNN (<D> <mmm>).pdf`, with a
   page break before the problems sheet's «Soluciones» heading. Then it refreshes the mirrors as
   the pack's step 9 does; a mirror that fails is counted and stops nothing.
9. Counts the theory sheet's pages against `pages_allowed`. A longer sheet is printed and reported
   on stderr; it is not regenerated.

**Exit codes**: 0 ok · 1 usage or validation · 3 partial failure · 5 the notebook tool is not
usable. When several apply, the highest wins, as in spec 005.

**Not in this command**:

- Running by itself when an exam is close: the unattended runner of spec 001 (User Story 7).
- A check of the sheets' numbers by a model that executes code. It would sit between steps 6 and 8,
  for that step alone (FR-036).
- An exam announced only in class, which has no captured text.
