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
| [Commands](#commands) | looking for the command that does one thing |
| [Ground rules](#ground-rules) | worried about privacy, exams or the platforms' terms |
| [Documentation](#documentation) | looking for something that is not on this page |

---

## What it does

| Component | Where it is | What it does |
|---|---|---|
| `sciencebits-a-notebooklm` | Skill in [`skills/sciencebits-a-notebooklm/`](skills/sciencebits-a-notebooklm/SKILL.md) | Captures a Science Bits topic screen by screen, builds a navigable PDF and a Markdown file per language (Spanish, Basque, English), files them by school year, subject and topic, and creates the topic's notebook. |
| `classroom-sync` | Specification in [`specs/001-classroom-sync/`](specs/001-classroom-sync/spec.md); implementation tracked in [epic #1](https://github.com/julioarguello/alfabeta/issues/1) | Is designed to copy the teacher's material from Classroom into the same topic folders, read-only, and keep an agenda of assignments and exams. |
| `study-pack` | Skill in [`skills/study-pack/`](skills/study-pack/SKILL.md); the reasons in [About preparing study material in advance](docs/explanation/study-material.md) | Prepares a few pieces per finished topic inside its notebook — short explainer videos, practice, quiz and flashcards in the subject's language — prints a glossary and a guide with a recomputed answer key for the parent, and prints the whole topic as one A4 PDF. |
| Calendar | Design in the [roadmap](docs/roadmap.md#calendar) | One calendar per student, holding only objective facts from Classroom — assignments, exams, posted material — never study blocks. |

## How it fits together

Target layout, from [specification 001](specs/001-classroom-sync/plan.md) and the
[study-pack design](docs/explanation/study-material.md). The Science Bits skill writes its files
into the topic folder's `sciencebits/`.

```
class notes (photos) ─┐
Google Classroom ─────┼──► <school year>/<subject>/YYYYMMDD - Tema NN - <title>/ ──► one notebook per topic ──► each listed account
Science Bits ─────────┘     {notes, classroom, sciencebits, notebook, exam}              (shared as viewer)
                                              │
                                              ├──► one-way mirrors in the student's other accounts' Drives
                                              └──► calendar: assignments, exams, posted material ──► each listed account
```

Every topic folder starts with the date the teacher posted its first material, so the student sees
each topic in time. A teacher's topic that is not in the textbook carries the teacher's title
instead of `Tema NN - <title>`, and what Classroom posts with no topic goes in `YYYYMMDD - No topic`.
Each Classroom file inside `classroom/` starts with its own posting date, `YYYYMMDD - <title>`.
A topic folder holds only folders, each named in English for where its content comes from:
`notes/` (the photos of the class notes, their transcriptions and the living file the notebook
reads), `classroom/` (the teacher's material and its living file), `sciencebits/` (the textbook) and
`notebook/` (what the notebook generates: videos, study guide, practice sheet, the printed topic,
the parent's material); `exam/` holds the sheets for the day before an exam.

When the three sources disagree about **what will be asked**, the design ranks the student's notes
over Classroom, and Classroom over the textbook. The textbook still explains best; it is just the
worst guide to the exam. The reasons, and the evidence behind them, are in
[the explanation page](docs/explanation/study-material.md#three-sources-one-order-of-trust).

In the design, the notebooks belong to a parent's personal Google account and are shared as viewer
with every account the configuration lists (`notebook.share_with`), so the family can share them
freely and the adult account avoids the platform's 18+ limit on cinematic video. The calendar is
shared the same way (`calendar.shared_with`), and the topic folders reach the student's other
accounts as one-way mirrors of the master folder (`drive.mirrors`). Measured 2026-10-26: a school
Google Workspace for Education domain allowed a notebook and a calendar owned by a personal Gmail
account to be shared with the school account and opened there.

## Get started

> [!TIP]
> **TL;DR** — clone the repository, install the notebook CLI, write the student's private
> configuration, add the skill to Claude, then ask for a topic.
>
> ```bash
> git clone https://github.com/julioarguello/alfabeta && cd alfabeta
> uv tool install notebooklm-mcp-cli
> nlm login
> mkdir -p ~/.alfabeta/<student> && cp config/template.toml ~/.alfabeta/<student>/config.toml
> uv run python -m alfabeta config check --student <student>
> ```
>
> The configuration holds names and folders only; never put a password in it.

### Prerequisites

| You need | Why |
|---|---|
| The [Claude desktop app](https://claude.ai/download) | The skill drives the app's built-in browser |
| The [Desktop Commander](https://github.com/wonderwhy-er/DesktopCommanderMCP) connector in Claude | The skill reads your configuration and runs commands on your Mac through it |
| [`notebooklm-mcp-cli`](https://github.com/jacob-bd/notebooklm-mcp-cli) (`nlm`), installed with [uv](https://docs.astral.sh/uv/) | Gemini Notebook has no public API; `nlm` talks to it from the command line |
| [pandoc](https://pandoc.org/installing.html), [Graphviz](https://graphviz.org/download/) and [Google Chrome](https://www.google.com/chrome/) | The study pack renders reports and mind maps to PDF with them |
| A folder synced to your cloud storage | The skills write each topic under `storage.base` and copy it to each folder in `drive.mirrors`; the Classroom sync will need [Google Drive for desktop](https://www.google.com/drive/download/) |

Nothing extra is needed for Python: `build.py` and its `render.py` run in Claude's VM, which ships
`reportlab`, `beautifulsoup4` and `pypdf`.

### Set up

1. Pick a short lowercase id for the student, never their name, and copy `config/template.toml` to
   `~/.alfabeta/<student>/config.toml`. Change every `changeme` value; the comment above each key
   says what it holds. `uv run python -m alfabeta config check --student <student>` lists every key
   still missing or invalid, by name and never by value, and each skill runs that check before it
   starts. The file stays outside the repository; a second student is a second folder with its own
   `config.toml`.
2. Sign `nlm` in (`nlm login`) with the Google account that will own the notebooks. Both skills
   pass `nlm` the profile named in `notebook.nlm_profile`, so write `default` there unless you keep a
   separate profile. If you do, make it `nlm`'s default as well
   (`nlm config set auth.default_profile <profile>`): `nlm download` takes no profile, and the study
   pack stops before downloading from another account.
3. Write the path of this clone in `tools.repository`; the Science Bits skill copies its
   `skills/sciencebits-a-notebooklm/scripts/` from it to the `tools.folder` of the configuration on each run. The study pack's scripts run from the clone.
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

## Commands

What a family runs, from the clone: `uv run python -m alfabeta <command>`. Every command takes
`--student <id>` and prints no name, address or id.

| Command | What it does | When |
|---|---|---|
| `config check --student <id>` | Lists every key of the student's configuration still missing or invalid, by name | after editing the configuration; every skill runs it first |
| `google client set --student <id> --from <file>` | Stores alfabeta's own Google client in the keychain | once |
| `google link --student <id> --account <alias>` | Links one Google account through Google's own sign-in | once per account |
| `google check --student <id>` | Refreshes every linked account and says which one no longer works | when a run reports a link problem |
| `google unlink --student <id> --account <alias>` | Revokes one account's link | to remove an account |
| `claude key set --student <id>` | Stores the Claude API key that transcribes the photos of class notes | once per Mac |
| `notebook setup --student <id> --topic <subject>/<folder>` | Adds the topic's two living files, class notes and Classroom, to its notebook | once per topic |
| `notes run --student <id>` | Turns the photos of class notes not yet transcribed into pages of the topic's living file | after photos are added; it also runs in the cloud |
| `exam prep --student <id> --subject <folder> [--exam YYYY-MM-DD] [--slot HH:MM-HH:MM] [--topic <folder>]` | Asks the topic's notebook for a theory sheet and a problems sheet for the exam, and prints both into the topic's `exam/` folder; refuses, saying why, when notebooks are off or `nlm` does not work | the day before an exam, from [#106](https://github.com/julioarguello/alfabeta/issues/106) on |

The Classroom sync is a skill, not a command: ask Claude «trae lo nuevo de Classroom» ("bring from
Classroom what is not here yet"), and it runs the commands it needs.

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
  with `notebook.enabled = false` and add the files by hand.
- **Generated material is checked, not trusted.** The study pack recomputes every numeric answer
  before it reaches the student — a teacher's answer key has been wrong before
  ([example](docs/explanation/study-material.md#three-sources-one-order-of-trust)). The exam sheets
  of `exam prep`, from [#106](https://github.com/julioarguello/alfabeta/issues/106) on, are the
  exception: the notebook computes their numbers, an accepted risk
  ([spec 002](specs/002-study-pack/spec.md), FR-036).

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
