---
name: sciencebits-a-notebooklm
description: Turns a topic of a Science Bits digital textbook (learning-bits.com) into navigable PDFs + Markdown (one per configured language), places them in the topic's folder of the student's base folder and creates its notebook in Gemini Notebook (NotebookLM). Use with "el siguiente tema" (the next topic) or "hazme el tema N de física/bio" (do topic N of physics/bio for me).
---

# Science Bits → PDF + Markdown → the topic's folder → Gemini Notebook

Part of the [alfabeta](https://github.com/julioarguello/alfabeta) project.

## Configuration
Receive the student's id, or ask for it; never guess it. Read `~/.alfabeta/<student>/config.toml` (template: the
repo's `config/template.toml`) with Desktop Commander, then check it on the Mac with
`uv run --project <tools.repository> python -m alfabeta config check --student <student>`. If it fails, say which
keys and stop. Never create the configuration or write to it. It provides:
`student.display_name`, `student.grade_level`, `student.school_year`, `storage.base` (the master folder),
`drive.mirrors` (list), `tools.folder` (`$H`), `tools.repository` (the clone), `downloads.folder`, the `[[subjects]]`
with `book = "sciencebits"` (`folder` is the subject's short name, `book_class` its class in Science Bits),
`sciencebits.url`, `sciencebits.languages` (the first one gives the topic folder's title), `notebook.enabled`,
`notebook.title_pattern`, `notebook.nlm_profile` and `notebook.share_with` (list).
The lists may be `[]`. Never print a mirror's path or a `share_with` address: say "mirror 2" or "2 accounts" (the
paths carry the account's email).

Result per topic:
- `TemaNN_<LANG>.pdf` and `.md` in the topic folder's `sciencebits/` (see Names). Each PDF: cover, clickable table
  of contents (lessons and sections), bookmarks, one screenshot per screen (and per button that changes the content)
  and the selectable text below it. The `.md` carries the same structured text (lesson → section → screen).
- The same files in every folder of `drive.mirrors`, one-way copies of `storage.base`.
- If `notebook.enabled`: a Gemini Notebook notebook with those files as sources, each once, shared as viewer with
  every account in `notebook.share_with`.
- A line in the student's run log for the placement and another for the notebook step, whatever its result.

Work from start to finish without asking for confirmation at each step. Only ask if the topic is ambiguous or
someone has to sign in (Science Bits or Google).

## alfabeta commands
Run every `python -m alfabeta` command on the Mac through Desktop Commander, as
`uv run --project <tools.repository> python -m alfabeta <command> --student <student> …`, never in the virtual
machine (it only sees `downloads.folder`). Below, `alfabeta <command>` is short for that.

**The run's lock.** Before opening Science Bits, `alfabeta lock take --student <student> --mode interactive` (`--mode
scheduled` when a scheduled task launches this skill); it answers `{"ok": true, "run": "<run>"}`. Every later
alfabeta command carries that run inline, `ALFABETA_RUN=<run> uv run …`, because each tool call is a new shell. The
lock is the student's and the Mac's browser's: a Classroom sync and this skill never run at once, since they share
the browser and the downloads folder. If `lock take` answers `lock_busy`, say another run is in progress and stop.
Renew it with `alfabeta lock renew` on every poll of the capture, between the build steps, while waiting for
someone to sign in, and before each source `nlm` uploads: after `sync.lock_idle_minutes` without a renewal it is
released and the run stops as `idle`. Release it with `alfabeta lock release` at the end. A run that stops before
placing anything (the session expired and nobody signs in again, a challenge page, an interface the steps do not
describe, a timeout) stops the collector, `resize_window preset desktop`, and ends with
`alfabeta log stop --reason session_expired|challenge|unexpected_ui|timeout`, which also releases the lock.

## Tools (in `$H`, copied from `scripts/`)
- `discover_lessons.js` — on the unit page: `sem`, `rest` and `lessonId` of each lesson.
- `orchestrator.js` — captures a queue of lessons/languages in the background; downloads one zip per lesson.
- `watch.py` — on the Mac, copies each zip downloaded to `downloads.folder` into `raw/` (the built-in browser's downloads sometimes
  stay as hidden temporary files `.…claudefordesktop.…` that the app deletes within minutes).
- `build.py` — generates PDF + `.md` per language from `raw/`, with the topic's texts from `--config`; `render.py`,
  beside it, draws them.

Environments: built-in browser (`…Claude_Browser__*`; load the `built-in-browser` skill first); Desktop
Commander for commands on the Mac; `device_bash` (VM with python3, reportlab, bs4, pypdf, DejaVu fonts) with
`downloads.folder` connected, where `build.py` runs; the `nlm` CLI (`notebooklm-mcp-cli`) for the notebook, every
command with `--profile <notebook.nlm_profile>` (`login` included). Measured 2026-10-28 with nlm 0.15.8: only
`nlm download` and `nlm config` take no profile, and nlm reads none from the environment.

## Names
- School year: `student.school_year`, e.g. `2026-2027`.
- Subject: the `folder` of the `[[subjects]]` entry with `book = "sciencebits"` whose `book_class` is the class in
  Science Bits. If none matches, say so and stop: the family adds it to the configuration.
- Topic: `Tema NN - <title>`, two-digit `NN`, with the title in the first of `sciencebits.languages`. Its folder is
  `<storage.base>/<school_year>/<subject>/<YYYYMMDD> - Tema NN - <title>`, as the constitution names it; e.g.
  `2026-2027/<subject>/20261001 - Tema 01 - <title>`. `book place` finds it and never changes its date: the folder
  of the subject named `Tema NN - <title>` after its date, whatever the date and the title (of two, the one that
  already holds `sciencebits/`), and only if there is none, a new one dated today. Never create a topic folder by
  hand: an undated or re-dated duplicate splits the topic in two.
- Folders without `Tema NN` (`<date> - <teacher's title>`, `<date> - No topic`) are Classroom's; leave them alone.
- "The next topic" = the one after the highest `NN` among the subject's topic folders (`Tema NN - <title>` after
  the date) that already hold `sciencebits/` (not the order of units in the Science Bits class).

## Steps

1. **Prepare.** `WORK=<downloads.folder>/alfabeta_work/<Subject>_TemaNN` with `raw/`, `out/`, `tools/`. Copy
   `<tools.repository>/skills/sciencebits-a-notebooklm/scripts/*` to `$H`, so it holds this version of the scripts,
   and `$H/*` to `$WORK/tools`. Take the lock (alfabeta commands). Start the collector and leave it running:
   `start_process("python3 -u $WORK/tools/watch.py $WORK/raw <downloads.folder>", timeout_ms=3000)`.
2. **Open Science Bits.** `preview_start(sciencebits.url)` (if it asks for permission: `request_access` scope "site").
   If the login page or "Your session has expired" shows up: ask the user to sign in in the browser pane,
   ticking "Remember me on this device", and wait for their "ready". Never type credentials.
3. **Find the topic.** `get_page_text` lists classes and units. With `find`, locate "Acceder a la unidad" (Go to the
   unit) and navigate to that URL. Note the title in each of `sciencebits.languages` (same URL with
   `/intranet/<language>/`, e.g. `/intranet/en/`).
4. **Discover lessons.** On the unit page run `discover_lessons.js` with `javascript_tool`.
   Do it before capturing: do not navigate while the capture is running (`preview_start` may reuse the tab).
5. **Capture.** Go back to the classes page and apply `resize_window(width=1280, height=800)`. Queue:
   `sciencebits.languages` in order, ids `L1…Ln`, no assessment lessons. Run in a single call
   `window.__SB={sem, rest, queue:[{lang, id, lessonId},…]};` + the contents of `orchestrator.js`.
   Poll `window.__orch` with short calls (<40 s): `results`, `current`, `stopped`,
   `document.getElementById('__fr')?.contentWindow.__job?.n`; between polls, `alfabeta lock renew`, then
   `device_bash "sleep 170; ls …/raw"`.
   ~3–5 min per lesson. Tell the user how long it will take and that nobody should open Science Bits on another device.
   - `SESSION_EXPIRED` → ask them to sign in again and relaunch what is missing.
   - `NOT_AVAILABLE` → that language does not exist for the unit (units edited by the teacher); skip it.
   - **Assessments**: never open or start them; they are left out.
   - Other `n:0`/errors → relaunch them at the end. Check one zip with `items` per lesson and language.
6. **Build.** `$WORK/unit.json`:
   `{"prefix":"TemaNN","langs":{"<language>":{"unit":"Tema N · …","course":"<the subject's full name> · <grade_level>"},…}}`, one
   entry per captured language, each title in its language, e.g. `"es"` and `"en"`. The topic's texts come only from
   this file: without `--config`, or without one of its keys, `build.py` stops and names the key.
   In `device_bash`: `python3 tools/build.py raw out --config unit.json <captured languages>`.
7. **Verify.** pypdf: pages, bookmarks, table-of-contents links, extractable text. Review the `.md`. If a lesson
   has few screens compared with its index (`menu` in meta.json), capture it again. `alfabeta lock renew` between
   these steps.
8. **Place.** `alfabeta book place --student <student> --subject <subject> --topic "Tema NN - <title>" --origin
   "$WORK/out"` copies `out/` into the topic folder's `sciencebits/` (see Names), keeping a changed file's previous
   version, brings the mirrors up to date and writes its line in the run log; what it does and refuses is its row in
   the repository's `specs/001-classroom-sync/contracts/cli.md`. From its JSON keep the `folder` (relative to
   `storage.base`), the files it `placed` (step 9 needs them) and `mirrors` (`up_to_date`, `failed`: a mirror that is
   not mounted or fails is caught up by the next run). If it exits 1, stop the collector, `resize_window preset
   desktop` and say what happened; then end with `alfabeta log stop --reason drive_not_mounted` (or
   `lock_not_held`) for those two reasons, and with `alfabeta lock release` for the others: `ambiguous_topic` (two
   folders of the subject are topic `Tema NN`: the family merges them, never you), `no_book` (no `[[subjects]]` entry
   with that folder, or it has no book), `invalid_topic`, `no_origin`, `nothing_to_place`, `name_clash` (two files
   would get one name), and `write_failed`, which records what it copied, so running it again completes it.
9. **Gemini Notebook.** If `notebook.enabled` is false: `alfabeta log notebook --student <student> --topic "Tema NN -
   <title>" --result disabled`, and go to step 10. Otherwise:
   - `nlm login --check`; if it fails, `nlm login --storage protected` in the background (a separate Chrome with no
     profile: this is expected). Ask the user to sign in, confirm the two-step verification and **not close the window**;
     `alfabeta lock renew` while you wait.
   - `nlm notebook list --json`; reuse the topic's notebook or create it with `notebook.title_pattern` (`{grade}` is
     `student.grade_level`, `{subject}` the subject's folder, `{topic}` the topic folder's name after its date;
     `--json`).
   - **Sources, each once.** `nlm source list <id> --json` gives each source's `id` and `title`. For each file of
     `$WORK/out`, skip it if a source has its file name as title and step 8 did not list it in `placed`; else
     `alfabeta lock renew`, then `nlm source add <id> --file "<file>" --wait --wait-timeout 300`, without `--title`.
     A file step 8 placed again had changed: once its new source is added, remove the old one, the source with that
     title listed before the add, with `nlm source delete <source id> --confirm`, so the notebook answers from the
     new version and holds it once. If a run stopped between step 8 and that replacement, the next run's step 8
     reports the file unchanged and the old source stays: delete it by hand and run this step again. Read in nlm
     0.15.8's source on 2026-10-28, not yet measured against a notebook: `source add --file` registers the source
     under the file's own name and `--title` renames it afterwards, and `source delete --confirm` skips its prompt;
     repeating the step therefore adds nothing.
   - **Share.** `nlm share status <id> --json`; for each account in `notebook.share_with` not yet listed:
     `nlm share invite <id> <account> --role viewer`. Never `nlm share public`. A failed invite does not undo the
     notebook: note it and report it. Measured 2026-10-26: the school domain allows a notebook owned by a personal
     Gmail account to be shared with the school account as viewer, and it opens there; if the school's admin
     changes that, the invite fails and the summary says so.
   - Test: `nlm notebook query <id> "<short question>"`.
   - `alfabeta log notebook --student <student> --topic "Tema NN - <title>" --result created|unchanged --shares
     <invited>,<already>,<failed>`: `unchanged` when the notebook already existed and no source was added or
     replaced, `created` otherwise; the three counts are over `notebook.share_with` (invited now, already listed,
     failed).
   - If `nlm` fails: `uv tool upgrade notebooklm-mcp-cli` once; if it still fails, `alfabeta log notebook … --result
     failed --reason "<what failed, in a few words, with no id or address>" --shares <invited>,<already>,<failed>`
     with the counts reached so far, and tell the family the topic is in its folder but the notebook step failed.
     What step 8 placed stays as it is.
10. **Close.** Stop the collector, `resize_window preset desktop`, `alfabeta lock release`, and summarise: folder,
    mirrors up to date and failed (by count), notebook link, accounts it is shared with (by count) and any failed
    invite, screens per language and what was left out.

## Limits
- Do not decrypt the `/seculogged/` XML files or force the disabled "Versión PDF" (PDF version): capture what the student sees.
- Videos are not captured (they remain as "[Vídeo (ver en la plataforma)]").
- Personal and educational use; do not redistribute the material.
