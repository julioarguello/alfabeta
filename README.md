# alfabeta

**Claude skills so Generation Alpha can study with AI, and so their families can help them without losing the afternoon.**

It turns the school's digital textbooks into real study material (navigable PDFs + Markdown in
Spanish, Basque and English), files it in your cloud storage by school year, subject and topic, and creates a
[Gemini Notebook](https://notebook.google.com) (formerly NotebookLM) notebook per topic to ask questions, generate
audio overviews, flashcards or quizzes. Coming soon: sync with Google Classroom and a study plan in the
calendar.

## Why «alfabeta»?

It is a pun with four layers:

| | |
|---|---|
| **alfabeto** (alphabet) | It is about learning. The first thing you learn is the alphabet; this is the alphabet of studying with AI. |
| **generación Alfa** (Generation Alpha) | Who it is made for: those born since 2010, the first generation to study with AI from secondary school onwards. |
| **beta** | Always in testing. It is a living project, remade with every topic, every subject and every school year. |
| **poda alfa-beta** (alpha-beta pruning) | A geeky nod: the classic AI algorithm with which machines learned to play chess by discarding what is not worth looking at. Exactly what we want: study what matters. |

## What is here

| Skill | Status | What it does |
|---|---|---|
| [`sciencebits-a-notebooklm`](skills/sciencebits-a-notebooklm/SKILL.md) | ✅ works | Captures a Science Bits topic (every screen and every button), generates a PDF with a clickable table of contents + Markdown per language, saves it to your cloud storage and creates the Gemini Notebook notebook. |
| `classroom-sync` | 🧪 proof of concept | Google Classroom assignments, due dates and materials → topic folder + notebook. See the [roadmap](docs/roadmap.md). |
| `plan-de-estudio` | 💡 idea | Assignments and exams → Google Calendar with review sessions. |

## Requirements

- [Claude](https://claude.ai) with the **desktop app** (built-in browser and access to your Mac).
- **Desktop Commander** connector (commands on the Mac).
- For Gemini Notebook: [`notebooklm-mcp-cli`](https://github.com/jacob-bd/notebooklm-mcp-cli)
  (`uv tool install notebooklm-mcp-cli` and `nlm login`).
- Python 3 with `reportlab`, `beautifulsoup4` and `pypdf` (Claude's VM already ships them).

## Installation

1. Copy `config.example.json` to `~/.alfabeta/config.json` and fill it in (name, school year, folders, subjects).
2. Copy the `skills/sciencebits-a-notebooklm/scripts/` folder to the `storage.tools_dir` path in your config.
3. In Claude, add the skill by uploading `skills/sciencebits-a-notebooklm/` (or ask Claude «instala la skill
   sciencebits-a-notebooklm de github.com/julioarguello/alfabeta» — "install the sciencebits-a-notebooklm skill
   from github.com/julioarguello/alfabeta").
4. Ask it: **«hazme el siguiente tema de física»** ("do the next physics topic for me").

## Important notices

- **Personal and educational use.** It captures only what the platform already shows the student with their own
  account, so they can study. Do not redistribute the material: it belongs to its authors (Science Bits, the teachers…).
- **It does not touch exams.** Assessment lessons are never opened, so no attempts are spent and no grades are changed.
- **Gemini Notebook has no public API.** `notebooklm-mcp-cli` uses internal APIs and your Google account's
  cookies; it may break and its use may not fit Google's terms. Use it at your own
  risk (or turn it off with `notebook.enabled: false` and add the files by hand).
- **Privacy.** No student data goes into the repo: everything personal lives in `~/.alfabeta/config.json`.

## License

[MIT](LICENSE).
