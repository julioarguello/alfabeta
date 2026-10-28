---
name: study-pack
description: Prepares a topic's study material inside its Gemini Notebook (NotebookLM) notebook — short explainer videos in Spanish per exam block, a practice sheet, quiz and flashcards in the subject's language, a bilingual glossary and a parent guide with a recomputed answer key — and prints the reports to A4 PDF in the topic's Drive folder; the day before an exam, it writes a theory sheet and a problems sheet from the topic's sources and prints them. Use with «prepara el tema N de <asignatura>» (prepare topic N of <subject>), «el tema N ha terminado» (topic N is finished), «prepara el examen de <asignatura>» (prepare the exam of <subject>) or when Classroom shows material in a new topic.
---

# Study pack — one topic, one notebook, a few pieces

Part of the [alfabeta](https://github.com/julioarguello/alfabeta) project. The reasons behind every
choice below — sources ranked by trust, retrieval practice, a handful of pieces, language split — are
in [About preparing study material in advance](../../docs/explanation/study-material.md). This file
says what to run.

## Configuration

Receive the student's id, or ask for it; never guess it. Read `~/.alfabeta/<student>/config.toml`
(template: the repo's `config/template.toml`), then check it on the Mac with
`uv run --project <tools.repository> python -m alfabeta config check --student <student>`. If it
fails, say which keys and stop. Never create the configuration or write to it.

| Key | Used for |
|---|---|
| `student.grade_level`, `student.school_year` | prompts and names; the topic folder's first level |
| `storage.base` | the topic folder |
| `drive.mirrors` | the folders refreshed after the videos are copied (step 9); never shown, only counted |
| `tools.repository` | the clone every command and script runs from |
| `[[subjects]]` `folder`, `language` | the subject's folder, and the language it is taught and examined in (`es`, `en`…) |
| `notebook.title_pattern`, `notebook.nlm_profile` | the topic's notebook; the `nlm` profile of the account that owns it |

Topic folder: `<storage.base>/<school_year>/<subject>/<YYYYMMDD> - Tema NN - <title>/`, found by
`*Tema NN - *` whatever its date, holding `apuntes/` (the student's class notes), `classroom/` (the
teacher's material) and `sciencebits/` (the textbook). The notebook is the one whose title matches
`notebook.title_pattern` (`nlm notebook list --profile <profile> --json`), with `<profile>` =
`notebook.nlm_profile`. `nlm download` takes no profile and reads nlm's default one
(`nlm config get auth.default_profile`; measured 2026-10-28 with nlm 0.15.8): when it is not
`<profile>`, say so and stop before any download, as `print_pack.py` does. Never write a name, an
email or an id into the repository.

## When to run

- **The topic is finished**: Classroom shows material in a new topic, judged by Classroom's dates, or
  the family says so. This is when videos are made — earlier, every new handout would regenerate them.
- **An exam is announced** for the topic: run it at once, whatever the dates say.
- **The day before an exam**, or when the family asks for the exam's sheets: the two sheets of
  [The day before an exam](#the-day-before-an-exam-two-sheets-on-paper). They need no notebook,
  unless the study guide is stale (its step 2), and can run without the steps below.

## Steps

1. **Read the scope.** Rank the sources: class notes > Classroom > textbook. The teacher's material
   says what is prioritised, not what is excluded. List the ideas an exam could ask, grouped in **two
   or three blocks**; separate on purpose two ideas students confuse (density and concentration were
   one such pair). Write them to `docente/bloques.md` with the files they come from, and show them to
   the family. **Once confirmed, the blocks are not decided again.** Photos in `apuntes/` become a
   source only as a literal transcription that someone who reads the notes has checked.
2. **Recompute every answer key** in the teacher's sheets by hand, in Python. Each mismatch becomes a
   line of `{corrections}`; a statement missing a datum is noted too. Never repeat a wrong value in
   anything the student sees, except the exam's problems sheet (see
   [The day before an exam](#the-day-before-an-exam-two-sheets-on-paper)).
3. **Generate**, with the templates in [`prompts.md`](prompts.md), passing `--profile <profile>` each time:
   - one video per block (`--format explainer --language es-ES`);
   - reports: study guide (`--format 'Study Guide' --language es`), practice sheet (`--language` the
     subject's language), glossary and parent guide (`--language es`);
   - quiz and flashcards, after the language switch below;
   - a mind map: `NOTEBOOKLM_HL=es nlm mindmap create <nb> -y` (it takes no focus, so it covers what
     the sources stress, which may not be every block).

   Launch the videos last, or alone: they cost the most quota.
4. **Wait** with `nlm studio status <nb> --profile <profile> --full --json` until every artifact is
   `completed` (measured 2026-10-26: about an hour for three videos). Do not create a second notebook.
5. **Verify each artifact before anyone sees it.**
   - Download it (`nlm download report|quiz|flashcards|video <nb> --id <id> -o <file>`).
   - Language: the whole text, not the title.
   - Recompute every number in the practice sheet, the quiz and the parent guide.
   - Compare the practice sheet's problems with the teacher's sheets: **no problem may reuse their
     data.** The model reuses them even when told not to (measured 2026-10-26: 7 of 11 practice
     problems were the teacher's, with the same numbers). Regenerate if it does.
   - Videos: duration (`ffprobe`) and a few frames (`ffmpeg -ss <s> -frames:v 1`). The audio
     language cannot be checked this way; say so.
6. **Print the parent's material** with
   `<tools.repository>/skills/study-pack/scripts/print-report.sh <nb> <artifact-id> <output.pdf> --student <student>`
   (A4, formulas rendered by KaTeX, page numbers) into `docente/`: the parent guide and the
   glossary, each with its Markdown beside it.
7. **Remove from Studio what the student must not see.** A viewer sees every Studio artifact, so the
   parent guide (it holds the answers) and the glossary leave Studio once their PDF and Markdown are
   in `docente/` (`nlm studio delete <nb> <id> --profile <profile> --confirm`). Until this step a
   viewer can see them: run it as soon as step 6 ends. Few pieces is a design hypothesis (see the
   design page); Tema 01 ended with six to work through plus two to consult. Say so when a topic
   goes past that.
8. **Number and order.** Every title starts with its place in the study order — videos, practice,
   quiz, flashcards, then what is only consulted (guide, mind map) — and says what it is, what
   about and how long, in Spanish — the constitution asks it of everything the family reads, and the
   parent reads the printed index — with no date and no recipient; a piece in the subject's language
   says so: `1 · Vídeo 5 min · Materia, mezclas y disoluciones`, `5 · Test 12 preguntas en euskera ·
   Materia y disoluciones`. Studio lists by last modification, so rename from the last piece to the first
   (`nlm studio rename <id> "<title>"`). A rename to the same title does not move an item: send a
   temporary title first.
9. **Copy every video to the topic folder** (`nlm download video <nb> --id <id> -o "<topic
   folder>/<title>.mp4"`), then refresh each folder of `drive.mirrors` from the master
   (`rsync -rlt --exclude .DS_Store "<storage.base>/" "<mirror>/"`, never `--delete`; a mirror that
   fails is counted and stops nothing): a viewer may not see the videos in the notebook (table below). **Add the start note** `0 · Empieza aquí` last, so it sits on top
   (`nlm note create`, or `nlm note update` if it exists), naming the pieces by number and linking
   the topic folder in each of the student's Drives, and **configure the tutor chat**
   (both in [`prompts.md`](prompts.md)).
10. **Print the topic** for paper: `uv run --project <tools.repository> python
    <tools.repository>/skills/study-pack/scripts/print_pack.py topic <nb> "<topic folder>/Tema NN para
    imprimir · <title>.pdf" --student <student>`. One PDF: an index of every piece (videos marked as "in the
    notebook"), the start note, then each report, the quiz with its answer key at the end, the flashcards as a
    table and the mind map drawn with Graphviz, each on a new page, in the numbered order. Run it
    after step 7, or the parent's material would print with it.
11. **Report** to the family: what is in Studio and in what order, where the printable PDF is,
    what went to `docente/`, the corrections, and what was not verified.

> [!WARNING]
> The output language that quiz and flashcards are written in is an **account-wide** setting, not a
> notebook one, and `nlm` has no flag for it. Before generating them, open the notebook in the
> browser, signed in as the owner, note the current value of *Settings → Output language*, and set
> it to the subject's language; after verifying them, set it back to the value you noted, even when the
> run failed. Left switched, every other notebook of that account answers in that language (measured
> 2026-10-26).

## The day before an exam: two sheets on paper

Spec 002, User Story 7 (FR-029 to FR-036). Ask the family for the study slot (`16:15–17:45`, say):
the configuration has no key for it. Nothing here touches the notebook but the rebuild of a stale
study guide (step 2). Work in the session's scratchpad; the files below are the exam's, not code,
and stay out of the repository.

1. **Read the scope.** Find the exam in the agenda (`classroom-sync`, category `exam`) and read the
   announcement it links; with none, read the class's stream as `classroom-sync` reads Classroom,
   before writing anything, and with nothing there either ask the family. The announcement's
   points, in its order, are the theory sheet's sections. Quote it in its language with its date
   and say what of the topic it leaves out.
2. **Read the sources** in order of trust: `apuntes/` (the living file `Apuntes de clase · TNN.md`),
   then `classroom/`, then `sciencebits/`. Compare dates: a study guide in the topic folder made
   before the notes' transcriptions is stale. Do not hand it out: rebuild it (step 3, then reprint
   the topic, step 10), and write the theory sheet from the sources.
3. **Map the problems.** List every exercise of the photocopies in `classroom/`, worked examples
   included, and put each in a pattern, as few patterns as you can: one formula is one pattern, and
   its direct and inverse uses are the same one; a chain of formulas, or a classification with no
   formula, can be one too. Note the exercises printed on two photocopies and mark those the
   teacher assigned (the assignment's text in Classroom says which). Per pattern, pick the hardest,
   an assigned one when there is one, and a second one for spare time.
4. **Write `solve.py`**, which computes every number, unit conversions included:
   - `put(key, value, decimals)` for every result a sheet will print, rounded to `decimals` and
     written to `values.json`;
   - `check(exercise, what, computed, printed, unit, decimals)` for every answer a photocopy prints:
     equal when `abs(computed - printed) <= 0.5 * 10**-d`, with `d` the decimals printed; the
     disagreements go to `mismatch.json`, and the run ends with `N checked, M disagree`.

   Then sort each disagreement. Recompute it with the intermediate values rounded as the printed
   solution rounds them: if it agrees, it is a rounding note beside that solution; if not, it goes
   in the table. A statement missing a datum goes in the table too, with its result under each
   reading.
5. **Write the two sheets** in Markdown, with `⟨key⟩` wherever a result goes, never the number:
   - **Theory**, `<Subject> · Examen del <weekday D> de <month> — Teoría y plan de estudio`:
     «Qué entra» with the announcement quoted; the plan as a table `Hora | Qué | Cómo`, one row per
     section, a five-minute break and a last row of about fifteen minutes for the blank page (write
     from memory, in the subject's language, then correct and circle what failed); then one section
     per point of the announcement. In each, every term in the subject's language first, then in
     Spanish; the notes' wording where it differs from the book's, and the same word used for two
     things; the traps; a test to do without looking, with its answers. Point to the problems sheet
     for problems. Four pages held a 90-minute slot.
   - **Problems**, `<Subject> · Examen del <D> de <month> — Problemas tipo`: the photocopies with
     their name and date; the assigned exercises marked ★; the map `Patrón | Problemas | El más
     difícil`; the repeats; the order, about ten minutes per pattern; one section per pattern with
     the statement quoted in its language, its Spanish translation, why it is the hardest and the
     spare-time one; `<div class="newpage"></div>`; «Soluciones»; last, «Soluciones impresas que no
     cuadran» as `Problema | Impreso | Calculado | Qué pasa`. That table names no one; outside it,
     a wrong printed value appears only in the solution of its own exercise, with its cause.
6. **Write `build.py`** and run it as `python3 -I build.py <tools.repository> <out-dir>`. It reads
   `teoria.md`, `problemas.md` and `values.json` from its own folder, fills each `⟨key⟩` and stops
   on a missing one, writes decimals with a comma (`{,}` inside `$…$`, or KaTeX spaces it as
   punctuation), and renders A4 with `render` imported from
   `skills/study-pack/scripts/print_pack.py`, which has no subcommand for a single page. Name them
   `Teoría para el examen · TNN (<D mmm>).pdf` and `Problemas tipo · TNN (<D mmm>).pdf`.
7. **Look at every page** (`pdftoppm -r 60 -png <pdf> <prefix>`, then read the images): the page
   count against the slot, no `⟨` left, tables and formulas whole. Read every number of the
   Markdown that is not a placeholder: each must be data of a statement, a fixed equivalence
   (1 L = 1000 mL), a time or an exercise number. A converted datum is a result: move it to
   `solve.py`. Copy both PDFs into the topic folder and refresh `drive.mirrors` as in step 9.
8. **Report** where the two PDFs are, each disagreement with its printed and computed value, and
   what was not verified.

Measured on 2026-10-28, on one exam of one topic:

| Behaviour | Consequence |
|---|---|
| A 90-minute slot took four A4 pages of theory | size the theory sheet to the slot |
| Two photocopies fitted six patterns; five exercises were printed on both | a map of patterns, not a list of exercises |
| The check reported five disagreements: three wrong answers on the teacher's sheet (the same three the parent's guide, checked 2026-10-26, had found), a worked example of the textbook that contradicts itself, and one rounding before the end; solving found one statement missing a datum | the table after the solutions, and the rounding rule of step 4 |
| The topic's study guide had been generated two days earlier, before the class notes reached the folder; only the theory sheet was written, and the stale guide stayed in the notebook and the printed topic | never hand out a guide made before the notes, and rebuild it |
| `build.py` stops on a missing value, and nothing in it notices a result typed into the Markdown; the sheets of that day had a few typed unit conversions and derived figures | the reading of step 7, which that day's run did not do |

## Measured behaviour of Gemini Notebook

Measured 2026-10-26 with `notebooklm-mcp-cli` 0.15.8 on a personal Google account with a paid
plan (`nlm` reports the tier as `PRO_CONSUMER`).

| Behaviour | Consequence |
|---|---|
| `nlm` asks for English by default; reports and videos take `--language`, quiz and flashcards do not | the account-wide switch above |
| Studio is ordered by last modification; a rename keeps the title verbatim and moves the item to the top | rename in reverse order |
| Viewers are read-only and see every Studio artifact except videos: of five video overviews in one notebook, both viewer accounts saw only the oldest, in the list and by direct link; regenerating the hidden ones did not help | material for the parent leaves Studio; every video is also downloaded to the topic folder, and the start note links that folder |
| 3 videos and 3 reports took about 79 % of a 5-hour usage window and about 4 % of the weekly one (`nlm usage`) | one topic per window; videos last |
| The tutor prompt worked as hints-before-answers, and in one sample attributed a note to the teacher | the prompt forbids attributing authorship |
| Videos asked for 3–4 minutes lasted 4–5; a quiz asked for 10 questions had 12 | name the real count and duration, from the download |
| `NOTEBOOKLM_HL=es` made a mind map come out in Spanish; whether it does the same for quiz and flashcards was not measured | try it before the account-wide switch |
| `nlm download flashcards -f markdown` prints the raw card structure; `-f json` is clean | `print_pack.py` reads JSON |

Whether the chat reads notes, and what the student sees as a viewer, were not settled on that date.

## Never

- Put study blocks or reminders in the calendar: it holds only facts from Classroom.
- Show the student a wrong value from a teacher's key anywhere but the exam's problems sheet (its
  table of printed answers that do not match, and the solution of that same exercise), or name the
  teacher as wrong.
- Type a result on an exam sheet: it comes from `values.json`.
- Make a second notebook for the topic, or share the parent's material with the student.
- Type a password. The family signs in.
