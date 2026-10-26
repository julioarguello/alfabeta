---
name: sciencebits-a-notebooklm
description: Turns a topic of a Science Bits digital textbook (learning-bits.com) into navigable PDFs + Markdown (ES/EU/EN), saves them to the user's cloud storage and creates its notebook in Gemini Notebook (NotebookLM). Use with "el siguiente tema" (the next topic) or "hazme el tema N de física/bio" (do topic N of physics/bio for me).
---

# Science Bits → PDF + Markdown → cloud storage → Gemini Notebook

Part of the [alfabeta](https://github.com/julioarguello/alfabeta) project.

## Configuration
Read `~/.alfabeta/config.json` (see the repo's `config.example.json`) with Desktop Commander. It provides:
`student.name`, `student.grade`, `storage.base_dir`, `storage.tools_dir` (`$H`), `storage.topic_folder_pattern`,
`subjects` (Science Bits class → short name), `languages`, `notebook.enabled`, `notebook.title_pattern`.
If it does not exist, ask for that data once and create it. Never write personal data outside that file.

Result per topic:
- `TemaNN_<LANG>.pdf` and `.md` in the topic folder (see Names). Each PDF: cover, clickable table of contents
  (lessons and sections), bookmarks, one screenshot per screen (and per button that changes the content) and
  the selectable text below it. The `.md` carries the same structured text (lesson → section → screen).
- If `notebook.enabled`: a Gemini Notebook notebook with those files as sources.

Work from start to finish without asking for confirmation at each step. Only ask if the topic is ambiguous or
someone has to sign in (Science Bits or Google).

## Tools (in `$H`, copied from `scripts/`)
- `discover_lessons.js` — on the unit page: `sem`, `rest` and `lessonId` of each lesson.
- `orchestrator.js` — captures a queue of lessons/languages in the background; downloads one zip per lesson.
- `watch.py` — on the Mac, copies each downloaded zip to `raw/` (the built-in browser's downloads sometimes
  stay as hidden temporary files `.…claudefordesktop.…` that the app deletes within minutes).
- `build.py` — generates PDF + `.md` per language from `raw/`.

Environments: built-in browser (`…Claude_Browser__*`; load the `built-in-browser` skill first); Desktop
Commander for commands on the Mac; `device_bash` (VM with python3, reportlab, bs4, pypdf, DejaVu fonts) with
`~/Downloads` connected, where `build.py` runs; the `nlm` CLI (`notebooklm-mcp-cli`) for the notebook.

## Names
- School year from `school_year_starts_month` → e.g. `2026-2027`.
- Subject: `subjects[<class in Science Bits>]`; if missing, ask for the short name once and save it in the config.
- Topic folder: `base_dir/<topic_folder_pattern>`, e.g. `2026-2027/FiQui/20261001 - Tema 01 - Sustancias puras y
  mezclas`. Every topic folder starts with a `YYYYMMDD - ` date (the posting date of the topic's first Classroom
  material), and that date is never changed. To find the folder of topic NN, look in `<year>/<subject>/` for a
  folder matching `*Tema NN - *` (two-digit `NN`), whatever its date, and reuse it. Only if none matches, create
  one with `{date}` = today as `YYYYMMDD`. Never create a second folder for a topic that already has one: an
  undated or re-dated duplicate splits the topic in two.
- Folders without `Tema NN` (`<date> - <teacher's title>`, `<date> - Sin tema`) are Classroom's; leave them alone.
- "The next topic" = the one after the highest `NN` among the subject's folders matching `*Tema NN - *`, ignoring
  the date prefix (and the order of units in the Science Bits class).

## Steps

1. **Prepare.** `WORK=~/Downloads/alfabeta_work/<Subject>_TemaNN` with `raw/`, `out/`, `tools/`. Copy `$H/*` to
   `$WORK/tools`. Start the collector and leave it running:
   `start_process("python3 -u $WORK/tools/watch.py $WORK/raw", timeout_ms=3000)`.
2. **Open Science Bits.** `preview_start(sciencebits.url)` (if it asks for permission: `request_access` scope "site").
   If the login page or "Your session has expired" shows up: ask the user to sign in in the browser pane,
   ticking "Remember me on this device", and wait for their "ready". Never type credentials.
3. **Find the topic.** `get_page_text` lists classes and units. With `find`, locate "Acceder a la unidad" (Go to the
   unit) and navigate to that URL. Note the title in each language (same URL with `/intranet/eu/` and `/intranet/en/`).
4. **Discover lessons.** On the unit page run `discover_lessons.js` with `javascript_tool`.
   Do it before capturing: do not navigate while the capture is running (`preview_start` may reuse the tab).
5. **Capture.** Go back to the classes page and apply `resize_window(width=1280, height=800)`. Queue: languages in
   order, ids `L1…Ln`, no assessment lessons. Run in a single call
   `window.__SB={sem, rest, queue:[{lang, id, lessonId},…]};` + the contents of `orchestrator.js`.
   Poll `window.__orch` with short calls (<40 s): `results`, `current`, `stopped`,
   `document.getElementById('__fr')?.contentWindow.__job?.n`; between polls, `device_bash "sleep 170; ls …/raw"`.
   ~3–5 min per lesson. Tell the user how long it will take and that nobody should open Science Bits on another device.
   - `SESSION_EXPIRED` → ask them to sign in again and relaunch what is missing.
   - `NOT_AVAILABLE` → that language does not exist for the unit (units edited by the teacher); skip it.
   - **Assessments**: never open or start them; they are left out.
   - Other `n:0`/errors → relaunch them at the end. Check one zip with `items` per lesson and language.
6. **Build.** `$WORK/unit.json`:
   `{"prefix":"TemaNN","langs":{"es":{"unit":"Tema N · …","course":"Física y Química · <grade>"},"eu":{…},"en":{…}}}`.
   In `device_bash`: `python3 tools/build.py raw out --config unit.json <captured languages>`.
7. **Verify.** pypdf: pages, bookmarks, table-of-contents links, extractable text. Review the `.md`. If a lesson
   has few screens compared with its index (`menu` in meta.json), capture it again.
8. **Save.** Find the topic folder by `*Tema NN - *` (see Names); only if there is none, `mkdir -p` it with
   today's date. Copy `out/*` into it.
9. **Gemini Notebook** (if `notebook.enabled`):
   - `nlm login --check`; if it fails, `nlm login --storage protected` in the background (a separate Chrome with no
     profile: this is expected). Ask the user to sign in, confirm the two-step verification and **not close the window**.
   - `nlm notebook list`; reuse the topic's notebook or create it with `title_pattern` (`--json`).
   - `nlm source add <id> --file "<file>" --wait --wait-timeout 300` for each PDF and `.md`.
   - Test: `nlm notebook query <id> "<short question>"`.
   - If `nlm` fails: `uv tool upgrade notebooklm-mcp-cli` once; if it still fails, leave the files and tell the user.
10. **Close.** Stop the collector, `resize_window preset desktop`, and summarise: folder, notebook link,
    screens per language and what was left out.

## Limits
- Do not decrypt the `/seculogged/` XML files or force the disabled "Versión PDF" (PDF version): capture what the student sees.
- Videos are not captured (they remain as "[Vídeo (ver en la plataforma)]").
- Personal and educational use; do not redistribute the material.
