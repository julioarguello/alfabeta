# Contract: `exam prep`

This follows spec 001's [command contract](../../001-classroom-sync/contracts/cli.md) and spec
005's [subcommands](../../005-notes-to-notebook/contracts/cli.md): `--home` before the subcommand,
`--student <id>` resolved once, JSON on stdout, messages for people on stderr, and no message with
an address, a Drive id, a notebook id or an absolute path. It implements spec 002's User Story 7
(FR-029 to FR-037); the code is julioarguello/alfabeta#106.

| Subcommand | Runs on | What it does | Writes to | Output | Codes |
|---|---|---|---|---|---|
| `exam prep --student <id> --subject <folder> [--exam YYYY-MM-DD] [--slot HH:MM-HH:MM] [--topic <folder>]` | Mac | Asks the exam topic's notebook for the theory sheet and the problems sheet with the fixed prompts, regenerating the study guide first when it predates the class notes, and prints both into the topic's `exam/` folder | the notebook (two reports; the study guide when stale; the start note), the pack record (FR-024), the refresh record of spec 005, the topic's `exam/` folder (created when missing), the mirrors | JSON `{ok, exam_date, topic, guide_regenerated, slot_minutes, pages_allowed, sheets:[{kind, printed, pages}]}`; `kind` is `theory` or `problems`, `topic` an opaque index, never a name or id | 0 · 1 `notebook_disabled`, `no_exam`, `no_announcement`, `no_notebook` · 3 a report never completed or did not print · 5 `nlm` not usable |

**Arguments**:

- `--subject`: the subject's `[[subjects]] folder`.
- `--exam`: the exam's date. Without it, the subject's next exam in the agenda, today included.
- `--slot`: the study slot. Its length sets the theory sheet's pages, four per 90 minutes rounded
  up (measured once, 2026-10-28), and its clock times go into the plan. Without it, 90 minutes and
  a plan in minutes from the start.
- `--topic`: the exam's topic folder. Without it, the subject's most recent topic folder (FR-023),
  named on stderr. The announcement does not give the topic: spec 001 files every announcement in
  the subject's `<YYYYMMDD> - Sin tema` folder (its FR-014).

**What it does, in order.** Steps 1 to 4 ask the notebook for nothing; a refusal there prints
nothing. From step 5 on, a failure is code 3 and stops nothing after it: a refresh or a guide that
fails still lets both sheets be asked for, and the output says the guide may be stale; a report
that fails does not stop the other.

1. Checks the configuration as `config check` does. With `notebook.enabled = false` it stops:
   `notebook_disabled`, code 1.
2. Checks that `nlm` is signed in for `notebook.nlm_profile`, and that this is `nlm`'s default
   profile, which `nlm download` reads; otherwise code 5, saying which.
3. Finds the exam: an `exam` item of the subject in spec 001's agenda, on `--exam` or the next one;
   none is `no_exam`. Reads its announcement: the `<YYYYMMDD> - aviso - <summary>.md` note spec 001
   writes for it (its FR-015), text and date. An exam with no announcement, including one
   spec 001 detected in a material or an assignment (its FR-020b), is `no_announcement`. Both are
   code 1.
4. Finds the topic (`--topic`, or the most recent one) and its notebook, by
   `notebook.title_pattern`. No notebook is `no_notebook`, code 1.
5. Brings the notebook's class-notes source up to date as `notebook refresh` does (spec 005
   FR-018): when the topic's living notes file's `built_md5` differs from the refresh record's
   `read_md5`, it reads the source once, which spec 005's research R14 has not shown to be enough,
   and waits two minutes, since a Drive source took one to two minutes to catch up (spec 005,
   measured 2026-10-27). Then it compares the time Drive gives for
   the living notes file's last revision with the study guide's creation time
   (`nlm studio status --full --json`). When the revision is later, or there is no guide, it
   generates one (`--format 'Study Guide' --language es`), waits for it, and deletes the previous
   one, so one guide is live (FR-033). A topic whose living files are not set up yet skips the
   comparison and says so.
6. Asks for the two reports, `nlm report create <nb> --format "Create Your Own" --language es
   --prompt <prompt> --profile <profile> -y`, with the prompts «Theory sheet — for an exam» and
   «Problems sheet — for an exam» of [`prompts.md`](../../../skills/study-pack/prompts.md), every
   placeholder filled. It waits as the pack does (`nlm studio status`). A report that never
   completes is code 3; the other one is still printed.
7. Titles them as pieces of the moment `EXAMEN <weekday>` (FR-014), numbered after the pieces that
   moment already holds: `EXAMEN <weekday> <n> · Teoría para el examen · <topic>` and
   `EXAMEN <weekday> <n+1> · Problemas tipo · <topic>`, renamed from the last to the first as the
   pack's step 8 does. Then it rewrites the start note «0 · Empieza aquí» last, naming the theory
   sheet as today's task (FR-015), and records both pieces and any regenerated guide in the pack
   record (FR-024).
8. Downloads each report and prints it with `print_pack.py report` into the topic's `exam/`
   folder, created when missing and with no date in its name, as
   `exam/Teoría para el examen · TNN (<D> <mmm>).pdf` and
   `exam/Problemas tipo · TNN (<D> <mmm>).pdf`; a second exam on the same topic sits beside the
   first, told apart by the date in those names. The problems sheet gets a page break before its
   «Soluciones» heading, through an option of `print_pack.py report` that
   julioarguello/alfabeta#106 adds. Then it refreshes the mirrors as the pack's step 9 does; a
   mirror that fails is counted and stops nothing.
9. Counts the theory sheet's pages against `pages_allowed`. A longer sheet is printed and reported
   on stderr; it is not regenerated. Nothing else of either sheet is checked: not its language,
   not its numbers (FR-009, FR-036).

**Exit codes**: 0 ok · 1 usage or validation · 3 partial failure · 5 the notebook tool is not
usable. When several apply, the highest wins, as in spec 005.

**Not in this command**:

- Running by itself when an exam is close: the unattended runner of spec 001 (User Story 7).
- A check of the sheets' numbers by a model that executes code. It would sit between steps 6 and 8,
  for that step alone (FR-036).
- An exam with no announcement: one announced only in class, or detected in a material or an
  assignment.
