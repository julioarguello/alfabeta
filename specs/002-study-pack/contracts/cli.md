# Contract: `exam prep`

This follows spec 001's [command contract](../../001-classroom-sync/contracts/cli.md) and spec
005's [subcommands](../../005-notes-to-notebook/contracts/cli.md): `--home` before the subcommand,
`--student <id>` resolved once, JSON on stdout, messages for people on stderr, and no message with
an address, a Drive id, a notebook id or an absolute path. It implements spec 002's User Story 7
(FR-029 to FR-037); the code is julioarguello/alfabeta#106.

| Subcommand | Runs on | What it does | Writes to | Output | Codes |
|---|---|---|---|---|---|
| `exam prep --student <id> --subject <folder> [--exam YYYY-MM-DD] [--slot HH:MM-HH:MM] [--topic <folder>]...` | Mac | Asks the exam topic's notebook for the theory sheet and the problems sheet with the fixed prompts, regenerating the study guide first when it predates the class notes, and prints both into the topic's `exam/` folder | the notebook (two reports; the study guide when stale; the start note), the pack record (FR-024), the refresh record of spec 005, the topic's `exam/` folder (created when missing), the mirrors | JSON `{ok, exam_date, topics:[{topic, guide_regenerated, slot_minutes, pages_allowed, sheets:[{kind, printed, pages}]}]}`, one entry per `--topic` (one without it); `kind` is `theory` or `problems`, `topic` an opaque index, never a name or id | 0 · 1 `notebook_disabled`, `subtopics_unnamed`, `no_exam`, `no_announcement`, `no_notebook` · 3 a step from 5 on failed: a report never completed or did not print, the guide, Drive or a mirror · 5 `nlm` not usable |

**Arguments**:

- `--subject`: the subject's `[[subjects]] folder`.
- `--exam`: the exam's date. Without it, the subject's next exam in the agenda, today included.
- `--slot`: the study slot. Its length sets the theory sheet's pages, four per 90 minutes rounded
  up (measured once, 2026-10-28), and its clock times go into the plan. Without it, 90 minutes and
  a plan in minutes from the start.
- `--topic`: the exam's topic folder, or once per subtopic when the exam covers several subtopics
  of a textbook topic (FR-045): each gets its own two sheets from its own notebook, an equal part of
  the slot, and the announcement's points its blocks cover. Without it, the subject's most recent
  topic folder (FR-023), named on stderr; when that folder is a subtopic, the command refuses with
  `subtopics_unnamed` (code 1, nothing asked of a notebook) and asks for one `--topic` per subtopic
  the exam covers, since the announcement does not say which. The announcement does not give the topic: spec 001 files every announcement in
  the subject's `<YYYYMMDD> - No topic` folder (its FR-014).

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
   writes for it (its FR-015), text and date, found through the `announcement` replica that
   `data/state.json` records for the item the exam was detected in (the entry's `origin`). An exam
   with no announcement, including one
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
   generates one (`--format 'Study Guide' --language es`) and waits for it. The guide is the
   report the pack record names or, failing that, the latest-made completed report whose title
   contains «Guía de estudio» or «Study Guide» (any case, accent optional) and does not start with
   `0 ·`: piece 0 is the plan (FR-015), never compared, retitled or deleted. The new guide takes
   that guide's title, and every report taken for a guide is deleted, so one is live (FR-033). A
   topic whose living files are not set up yet skips the comparison and says so; one whose living
   notes file is not where `notebook setup` put it (spec 005's `health = missing`) skips it too,
   and that is code 3, the guide possibly stale.
6. Asks for the two reports, `nlm report create <nb> --format "Create Your Own" --language es
   --prompt <prompt> --profile <profile> -y`, with the prompts «Theory sheet — for an exam» and
   «Problems sheet — for an exam» of [`prompts.md`](../../../skills/study-pack/prompts.md), every
   placeholder filled. It waits as the pack does (`nlm studio status`). A report that never
   completes is code 3; the other one is still printed.
7. Titles them as pieces of the moment `EXAMEN <weekday>` (FR-014), numbered after the pieces that
   moment already holds: `EXAMEN <weekday> <n> · Teoría para el examen · <topic>` and
   `EXAMEN <weekday> <n+1> · Problemas tipo · <topic>`, renamed from the last to the first as the
   pack's step 8 does. Then it writes the start note «EXAMEN <weekday> · Empieza aquí» last (rewriting it on a second
   run for the same exam, and leaving a note «0 · …» as it is), with «Start note —
   for an exam» of [`prompts.md`](../../../skills/study-pack/prompts.md), naming the theory sheet as
   today's task (FR-015), and records both pieces and any regenerated guide in the pack record
   (FR-024). A second run for the same exam asks for two new reports, numbered after these, and
   prints over the same two files.
8. Downloads each report and prints it with `print_pack.py report` into the topic's `exam/`
   folder, created when missing and with no date in its name, as
   `exam/Teoría para el examen · TNN (<D> <mmm>).pdf` and
   `exam/Problemas tipo · TNN (<D> <mmm>).pdf`; a second exam on the same topic sits beside the
   first, told apart by the date in those names. A teacher's topic with no `Tema NN` is named by
   its folder's name after the date in place of `TNN`, cut so the whole name fits 255 UTF-8 bytes
   with the date kept. The problems sheet gets a page break before its «Soluciones» heading,
   `print_pack.py report --break-before Soluciones`; a sheet with no such heading prints without
   it, says so on stderr, and the run is not code 3 for it. Then it refreshes
   the mirrors as the pack's step 9 does; a mirror that fails or is not mounted is counted, stops
   nothing and makes the run code 3.
9. Counts the theory sheet's pages against `pages_allowed`. A longer sheet is printed and reported
   on stderr; it is not regenerated. Nothing else of either sheet is checked: not its language,
   not its numbers (FR-009, FR-036).

**Records**, in the student's data folder (`~/.alfabeta/<id>/data/`), readable by its user alone,
never in Drive or the repository:

- the pack record (FR-024), `study-pack.json`: under `topics`, keyed by the topic folder's path
  under `storage.base`, `guide` (`id`, `made`: the live study guide and the day it was made) and
  `pieces` (`id`; `kind`, `exam_theory` or `exam_problems`; `moment`; `title`; `language`;
  `verification`, `pages_only` for an exam sheet; `exam`, the exam's date; `made`);
- spec 005's refresh record, `notebook-refresh.json`: under `sources`, per source id, `read_md5`,
  `reads` and `read_at` (spec 005 data-model, RefreshRecord).

**Exit codes**: 0 ok · 1 usage or validation · 3 partial failure · 5 the notebook tool is not
usable. Steps 1 to 4 stop at the first refusal, in their order; from step 5 on, when several
apply, the highest wins, as in spec 005. An argument argparse cannot read (`--exam notadate`) is
its own code 2, as in spec 001. Code 1 also covers `invalid_config`, `no_subject`, `invalid_slot`,
`no_topic`, `unreadable_agenda` and `unreadable_state` (spec 001's `agenda.json` or
`data/state.json` is not readable JSON), `unknown_language` (a subject `language` code with no
Spanish name in `src/alfabeta/exam/prompts.py`) and `invalid_prompt` (a heading of `prompts.md`
the command reads is missing or renamed); code 5 is `no_nlm`, `nlm_signed_out`, `nlm_failed` or
`nlm_not_default`.

**Not in this command**:

- Running by itself when an exam is close: the unattended runner of spec 001 (User Story 7).
- A check of the sheets' numbers by a model that executes code. It would sit between steps 6 and 8,
  for that step alone (FR-036).
- An exam with no announcement: one announced only in class, or detected in a material or an
  assignment.
