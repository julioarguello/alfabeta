# alfabeta

**Claude skills so a secondary-school student can study with AI, and their family can help without
losing the afternoon.**

alfabeta organises what a student needs for each topic into one folder per topic in the family's
cloud storage, and builds one [Gemini Notebook](https://notebook.google.com) (formerly NotebookLM)
per topic to study from. The skills run in the [Claude](https://claude.ai) desktop app. The one that
run are the [Science Bits](https://learning-bits.com) textbook capture and the study pack; the
[Google Classroom](https://classroom.google.com) sync, the use of the student's own class notes and
the calendar are designed in [epic #1](https://github.com/julioarguello/alfabeta/issues/1)
and in [About preparing study material in advance](docs/explanation/study-material.md).

**If you are a family** that wants to use it, read [What it does](#what-it-does) and then
[Get started](#get-started). **If you want to understand or change how study material is chosen and
generated**, go to [About preparing study material in advance](docs/explanation/study-material.md).
**If you want to contribute code**, start from the [specification](specs/001-classroom-sync/spec.md)
and the [constitution](.specify/memory/constitution.md).

| Section | You are… |
|---|---|
| [What it does](#what-it-does) | deciding whether this is for you |
| [How it fits together](#how-it-fits-together) | wondering where each file and notebook comes from |
| [Get started](#get-started) | ready to capture your first topic |
| [Ground rules](#ground-rules) | worried about privacy, exams or the platforms' terms |
| [Documentation](#documentation) | looking for something that is not on this page |

---

## What it does

| Component | Where it is | What it does |
|---|---|---|
| `sciencebits-a-notebooklm` | Skill in [`skills/sciencebits-a-notebooklm/`](skills/sciencebits-a-notebooklm/SKILL.md) | Captures a Science Bits topic screen by screen, builds a navigable PDF and a Markdown file per language (Spanish, Basque, English), files them by school year, subject and topic, and creates the topic's notebook. |
| `classroom-sync` | Specification in [`specs/001-classroom-sync/`](specs/001-classroom-sync/spec.md); implementation tracked in [epic #1](https://github.com/julioarguello/alfabeta/issues/1) | Is designed to copy the teacher's material from Classroom into the same topic folders, read-only, and keep an agenda of assignments and exams. |
| `study-pack` | Skill in [`skills/study-pack/`](skills/study-pack/SKILL.md); the reasons in [About preparing study material in advance](docs/explanation/study-material.md) | Prepares a few pieces per finished topic inside its notebook — short explainer videos, practice, quiz and flashcards in the exam's language — and prints a glossary and a guide with a recomputed answer key for the parent to A4 PDF. |
| Calendar | Design in the [roadmap](docs/roadmap.md#calendar) | One calendar per student, holding only objective facts from Classroom — assignments, exams, posted material — never study blocks. |

## How it fits together

Target layout, from [specification 001](specs/001-classroom-sync/plan.md) and the
[study-pack design](docs/explanation/study-material.md). The Science Bits skill writes its files
straight into the topic folder.

```
class notes (photos) ─┐
Google Classroom ─────┼──► <school year>/<subject>/Tema NN - <title>/ ──► one notebook per topic ──► the student
Science Bits ─────────┘     {apuntes, classroom, sciencebits}                 (shared as viewer)
                                              │
                                              └──► calendar: assignments, exams, posted material
```

When the three sources disagree about **what will be asked**, the design ranks the student's notes
over Classroom, and Classroom over the textbook. The textbook still explains best; it is just the
worst guide to the exam. The reasons, and the evidence behind them, are in
[the explanation page](docs/explanation/study-material.md#three-sources-one-order-of-trust).

In the design, the notebooks belong to a parent's personal Google account and are shared with the
student, so the family can share them freely and the adult account avoids the platform's 18+ limit
on cinematic video.

## Get started

> [!TIP]
> **TL;DR** — clone the repository, install the notebook CLI, write your private configuration, add
> the skill to Claude, then ask for a topic.
>
> ```bash
> git clone https://github.com/julioarguello/alfabeta && cd alfabeta
> uv tool install notebooklm-mcp-cli
> nlm login
> mkdir -p ~/.alfabeta && cp config.example.json ~/.alfabeta/config.json
> ```
>
> The configuration holds names and folders only; never put a password in it.

### Prerequisites

| You need | Why |
|---|---|
| The [Claude desktop app](https://claude.ai/download) | The skill drives the app's built-in browser |
| The [Desktop Commander](https://github.com/wonderwhy-er/DesktopCommanderMCP) connector in Claude | The skill reads your configuration and runs commands on your Mac through it |
| [`notebooklm-mcp-cli`](https://github.com/jacob-bd/notebooklm-mcp-cli) (`nlm`), installed with [uv](https://docs.astral.sh/uv/) | Gemini Notebook has no public API; `nlm` talks to it from the command line |
| [pandoc](https://pandoc.org/installing.html) and [Google Chrome](https://www.google.com/chrome/) | The study pack renders reports to PDF with them |
| A folder synced to your cloud storage | The skill writes each topic under `storage.base_dir`; the Classroom sync will need [Google Drive for desktop](https://www.google.com/drive/download/) |

Nothing extra is needed for Python: `build.py` runs in Claude's VM, which ships `reportlab`,
`beautifulsoup4` and `pypdf`.

### Set up

1. Copy `config.example.json` to `~/.alfabeta/config.json` and fill in `student` (name, grade, month
   the school year starts), `storage` (`base_dir`, `tools_dir`), `subjects`, `notebook`
   and `study_pack.exam_language`. It stays outside the repository.
2. Sign `nlm` in (`nlm login`) with the Google account that will own the notebooks. The Science
   Bits skill uses `nlm`'s default profile; the study pack uses the one named in
   `notebook.nlm_profile`, so write `default` there unless you keep a separate profile.
3. Copy `skills/sciencebits-a-notebooklm/scripts/` and `skills/study-pack/scripts/` to the
   `storage.tools_dir` folder of your configuration.
4. Add the skills to Claude by uploading `skills/sciencebits-a-notebooklm/` and
   `skills/study-pack/`, or ask Claude «instala la skill sciencebits-a-notebooklm de
   github.com/julioarguello/alfabeta» ("install the sciencebits-a-notebooklm skill from
   github.com/julioarguello/alfabeta").
5. Ask Claude: **«hazme el siguiente tema de física»** ("do the next physics topic for me"). The
   student signs in to Science Bits when asked; no tool ever types a password.

> [!WARNING]
> **For the Classroom sync**: in the Chrome profile it uses, switch off *Ask where to save each file
> before downloading*. Otherwise every download waits for a click and an unattended run stalls
> ([measured](specs/001-classroom-sync/research.md#r12-from-the-browser-to-disk)).

## Ground rules

- **Read-only on school platforms.** alfabeta never turns anything in, comments, marks work as done,
  or opens assessments or quizzes, in Classroom or in Science Bits — so no attempts are spent and no
  grades change.
- **Personal and educational use.** It captures only what the platform already shows the student.
  The material belongs to its authors; do not redistribute it.
- **The student is a minor.** Only the minimum data, never in the repository, URLs, logs, issues or
  pull requests. A student is configuration, not code: a second student is a second configuration
  file. Test data is invented.
- **Gemini Notebook has no public API.** `nlm` uses internal endpoints and your account's session; it
  may break, and its use may not fit Google's terms. Use it at your own risk, or turn notebooks off
  with `notebook.enabled: false` and add the files by hand.
- **Generated material is checked, not trusted.** The study pack recomputes every numeric answer
  before it reaches the student — a teacher's answer key has been wrong before
  ([example](docs/explanation/study-material.md#three-sources-one-order-of-trust)).

## Why «alfabeta»?

A pun in four layers:

| | |
|---|---|
| **alfabeto** (alphabet) | It is about learning; this is the alphabet of studying with AI. |
| **generación Alfa** (Generation Alpha) | Who it is for: those born from 2010, the first to study with AI from secondary school. |
| **beta** | Always in testing, remade with every topic, subject and school year. |
| **poda alfa-beta** (alpha-beta pruning) | The classic game-search algorithm that discards what is not worth looking at. Exactly the point: study what matters. |

## Documentation

| Page | Kind | Read it when |
|---|---|---|
| [About preparing study material in advance](docs/explanation/study-material.md) | Explanation | you want the evidence, the cases and the measurements behind the study design |
| [Roadmap](docs/roadmap.md) | Plan | you want to know what gets built next |
| [Classroom research](docs/classroom-investigacion.md) | Explanation | you wonder why there is no Classroom API |
| [Specification 001](specs/001-classroom-sync/spec.md) and its [research notes](specs/001-classroom-sync/research.md) | Specification | you are building or reviewing the Classroom sync |
| [Constitution](.specify/memory/constitution.md) | Principles | you are about to change how the project works |

## License

[MIT](LICENSE).
