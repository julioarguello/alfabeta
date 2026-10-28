---
name: study-pack
description: Prepares a topic's study material inside its Gemini Notebook (NotebookLM) notebook — short explainer videos in Spanish per exam block, a practice sheet, quiz and flashcards in the subject's language, a bilingual glossary and a parent guide with a recomputed answer key — and prints the reports to A4 PDF in the topic's Drive folder; the day before an exam, alfabeta's `exam prep` asks the notebook for a theory sheet and a problems sheet and prints them. Use with «prepara el tema N de <asignatura>» (prepare topic N of <subject>), «el tema N ha terminado» (topic N is finished), «prepara el examen de <asignatura>» (prepare the exam of <subject>) or when Classroom shows material in a new topic.
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
- **The day before an exam**, or when the family asks for the exam's sheets: alfabeta's own
  command, in [The day before an exam](#the-day-before-an-exam-two-sheets-on-paper). It needs none
  of the steps below.

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

Spec 002, User Story 7 (FR-029 to FR-037), and its [command contract](../../specs/002-study-pack/contracts/cli.md).
From julioarguello/alfabeta#106 on, alfabeta makes both sheets by itself, with no Claude:

```bash
uv run --project <tools.repository> python -m alfabeta exam prep --student <student> --subject <folder> [--exam YYYY-MM-DD] [--slot HH:MM-HH:MM] [--topic <folder>]
```

It takes the scope from the teacher's announcement that `classroom-sync` captured, regenerates the
topic's study guide when it was made before the class notes, asks the notebook for the two reports with the
prompts «Theory sheet — for an exam» and «Problems sheet — for an exam» of [`prompts.md`](prompts.md),
titles them `EXAMEN <weekday> <n> · Teoría para el examen · <topic>` and `… <n+1> · Problemas tipo · …`,
numbered after the moment's existing pieces, rewrites the start note last, and prints them into the topic folder as `Teoría para el examen · TNN (<D> <mmm>).pdf` and
`Problemas tipo · TNN (<D> <mmm>).pdf`. It refuses, saying why, when notebooks are off
(`notebook.enabled = false`), `nlm` is signed out or failing, or the exam, its announcement or the
notebook is missing. The notebook computes every number on both sheets: an accepted risk, and the
one place where nothing recomputes them (spec 002 FR-036).

Until that command exists, the family can make the same two reports by hand, with no agent:
`nlm report create <nb> --format "Create Your Own" --language es --prompt "<prompt>" --profile
<profile> -y`, one per prompt with every placeholder filled, printed with `print-report.sh`
(step 6) under those file names. That path skips what the command adds: regenerating a stale
guide, the titles, the start note, the pack record and the page break before «Soluciones».

How it was first done, as observed 2026-10-28 on one exam of one topic: an agent wrote both sheets from the
topic folder, every result computed by a script it wrote, and the family then decided that
alfabeta makes them through the notebook. What that run measured:

| Behaviour | Consequence |
|---|---|
| A 90-minute slot took four A4 pages of theory | `{pages}`: four per 90 minutes |
| Two photocopies fitted six patterns; five exercises were printed on both | a map of patterns, not a list of exercises |
| The check reported five disagreements: three wrong answers on the teacher's sheet (the same three that step 2 had computed and passed, as checked 2026-10-26, to the parent's guide as `{corrections}`; whether the notebook finds them by itself is unmeasured), a worked example of the textbook that contradicts itself, and one rounding before the end; solving found one statement missing a datum | the table «Soluciones impresas que no cuadran», and the rounding rule in the prompt |
| The topic's study guide had been generated two days earlier, before the class notes reached the folder | the command regenerates a guide made before the notes |
| Nothing measured how the notebook does on these two prompts | the first run of `exam prep` is that measurement |

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
- Write an exam sheet by hand: `exam prep` asks the notebook for it.
- Make a second notebook for the topic, or share the parent's material with the student.
- Type a password. The family signs in.
