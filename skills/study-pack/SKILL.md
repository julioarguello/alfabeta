---
name: study-pack
description: Prepares a topic's study material inside its Gemini Notebook (NotebookLM) notebook — short explainer videos in Spanish per exam block, a practice sheet, quiz and flashcards in the exam language, a bilingual glossary and a parent guide with a recomputed answer key — and prints the reports to A4 PDF in the topic's Drive folder. Use with «prepara el tema N de <asignatura>» (prepare topic N of <subject>), «el tema N ha terminado» (topic N is finished) or when Classroom shows material in a new topic.
---

# Study pack — one topic, one notebook, a few pieces

Part of the [alfabeta](https://github.com/julioarguello/alfabeta) project. The reasons behind every
choice below — sources ranked by trust, retrieval practice, a handful of pieces, language split — are
in [About preparing study material in advance](../../docs/explanation/study-material.md). This file
says what to run.

## Configuration

Read `~/.alfabeta/config.json` (template: the repo's `config.example.json`):

| Key | Used for |
|---|---|
| `student.grade` | prompts and names |
| `storage.base_dir`, `storage.tools_dir` | the topic folder; where `print-report.sh` is installed |
| `subjects` | the subject's short name |
| `study_pack.exam_language` | per subject: the language the exam is written in (`eu`, `en`, `es`) |
| `notebook.nlm_profile` | the `nlm` profile of the account that owns the notebooks |

Topic folder: `base_dir/<year>/<subject>/Tema NN - <title>/`, holding `apuntes/` (the student's class
notes), `classroom/` (the teacher's material) and `sciencebits/` (the textbook). The notebook is the
one whose title matches `notebook.title_pattern` (`nlm notebook list --profile <profile> --json`).
Never write a name, an email or an id into the repository.

## When to run

- **The topic is finished**: Classroom shows material in a new topic, judged by Classroom's dates, or
  the family says so. This is when videos are made — earlier, every new handout would regenerate them.
- **An exam is announced** for the topic: run it at once, whatever the dates say.

## Steps

1. **Read the scope.** Rank the sources: class notes > Classroom > textbook. The teacher's material
   says what is prioritised, not what is excluded. List the ideas an exam could ask, grouped in **two
   or three blocks**; separate on purpose two ideas students confuse (density and concentration were
   one such pair). Write them to `docente/bloques.md` with the files they come from, and show them to
   the family. **Once confirmed, the blocks are not decided again.**
2. **Recompute every answer key** in the teacher's sheets by hand, in Python. Each mismatch becomes a
   line of `{corrections}`; a statement missing a datum is noted too. Never repeat a wrong value in
   anything the student sees.
3. **Generate**, with the templates in [`prompts.md`](prompts.md), passing `--profile <profile>` each time:
   - one video per block (`--format explainer --language es-ES`);
   - reports: practice sheet (`--language` the exam language), glossary and parent guide (`--language es`);
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
6. **Print the parent's material** with `scripts/print-report.sh <nb> <artifact-id> <output.pdf>`
   (A4, formulas rendered by KaTeX, page numbers) into `docente/`: the parent guide and the
   glossary, each with its Markdown beside it.
7. **Remove from Studio what the student must not see.** A viewer sees every Studio artifact, so the
   parent guide (it holds the answers) and the glossary leave Studio once their PDF and Markdown are
   in `docente/` (`nlm studio delete <nb> <id> --profile <profile> --confirm`). The panel that
   designed this put the ceiling at about five pieces the student works through; Tema 01 ended with
   six to work through plus two to consult. Say so when a topic goes past it.
8. **Number and order.** Every title starts with its place in the study order — videos, practice,
   quiz, flashcards, then what is only consulted (guide, mind map) — and says what it is, what
   about and how long, in the language the student uses it in, with no date and no recipient:
   `1 · Vídeo 5 min · Materia, mezclas y disoluciones`, `5 · Test 12 galdera · Materia eta
   disoluzioak`. Studio lists by last modification, so rename from the last piece to the first
   (`nlm studio rename <id> "<title>"`). A rename to the same title does not move an item: send a
   temporary title first.
9. **Add the start note** `0 · Empieza aquí` last, so it sits on top (`nlm note create`, or
   `nlm note update` if it exists), naming the pieces by number, and **configure the tutor chat**
   (both in [`prompts.md`](prompts.md)).
10. **Print the topic** for paper: `scripts/print_pack.py topic <nb> "<topic folder>/Tema NN para
    imprimir · <title>.pdf"`. One PDF: an index of every piece (videos marked as "in the
    notebook"), then each report, the quiz with its answer key at the end, the flashcards as a
    table and the mind map drawn with Graphviz, each on a new page, in the numbered order. Run it
    after step 7, or the parent's material would print with it.
11. **Report** to the family: what is in Studio and in what order, where the printable PDF is,
    what went to `docente/`, the corrections, and what was not verified.

> [!WARNING]
> The output language that quiz and flashcards are written in is an **account-wide** setting, not a
> notebook one, and `nlm` has no flag for it. Before generating them, open the notebook in the
> browser, signed in as the owner, and set *Settings → Output language* to the exam language; after
> verifying them, set it back to *Default*. Left switched, every other notebook of that account
> answers in that language (measured 2026-10-26).

## Measured behaviour of Gemini Notebook

Measured 2026-10-26 with `notebooklm-mcp-cli` 0.15.8 on a personal Google account with a paid
plan (`nlm` reports the tier as `PRO_CONSUMER`).

| Behaviour | Consequence |
|---|---|
| `nlm` asks for English by default; reports and videos take `--language`, quiz and flashcards do not | the account-wide switch above |
| Studio is ordered by last modification; a rename keeps the title verbatim and moves the item to the top | rename in reverse order |
| Viewers are read-only and see every Studio artifact | material for the parent leaves Studio |
| 3 videos and 3 reports took about 79 % of a 5-hour usage window and about 4 % of the weekly one (`nlm usage`) | one topic per window; videos last |
| The tutor prompt worked as hints-before-answers, and in one sample attributed a note to the teacher | the prompt forbids attributing authorship |
| Videos asked for 3–4 minutes lasted 4–5; a quiz asked for 10 questions had 12 | name the real count and duration, from the download |
| `NOTEBOOKLM_HL=es` made a mind map come out in Spanish; whether it does the same for quiz and flashcards was not measured | try it before the account-wide switch |
| `nlm download flashcards -f markdown` prints the raw card structure; `-f json` is clean | `print_pack.py` reads JSON |

Whether the chat reads notes, and what the student sees as a viewer, were not settled on that date.

## Never

- Put study blocks or reminders in the calendar: it holds only facts from Classroom.
- Show the student a wrong value from a teacher's key, or name the teacher as wrong.
- Make a second notebook for the topic, or share the parent's material with the student.
- Type a password. The family signs in.
