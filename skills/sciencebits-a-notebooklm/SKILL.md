---
name: sciencebits-a-notebooklm
description: Turns a topic of a Science Bits digital textbook (learning-bits.com) into navigable PDFs + Markdown (one per configured language), places them in the topic's folder of the student's base folder and creates its notebook in Gemini Notebook (NotebookLM). Use with "el siguiente tema" (the next topic) or "hazme el tema N de física/bio" (do topic N of physics/bio for me).
---

# Science Bits → PDF + Markdown → the topic's folder → Gemini Notebook

Part of the [alfabeta](https://github.com/julioarguello/alfabeta) project.

## Configuration
Receive the student's id, or ask for it; never guess it. Read `~/.alfabeta/<student>/config.toml` (template: the
repo's `config/template.toml`; ignore its `rules_*` keys, spec 009 FR-013), then check it with
`uv run --project <tools.repository> python -m alfabeta config check --student <student>`. If it fails, say which
keys and stop. Never create the configuration or write to it. It provides:
`student.display_name`, `student.grade_level`, `student.school_year`, `storage.base` (the master folder),
`drive.share_with` (list), `tools.folder` (`$H`), `tools.repository` (the clone), `downloads.folder`, the `[[subjects]]`
with `book = "sciencebits"` (`folder` is the subject's short name, `book_class` its class in Science Bits),
`sciencebits.url`, `sciencebits.languages` (the first one gives the topic folder's title), `notebook.enabled`,
`notebook.title_pattern`, `notebook.nlm_profile` and `notebook.share_with` (list).
The lists may be `[]`. Never print a `share_with` address or the absolute path of `storage.base`: say "2 accounts"
(the Drive for desktop path carries the account's email).

Result per topic:
- `TemaNN_<LANG>.pdf` and `.md` in the topic folder's `sciencebits/` (see Names). Each PDF: cover, clickable table
  of contents (lessons and sections), bookmarks, one screenshot per screen (and per button that changes the content)
  and the selectable text below it. The `.md` carries the same structured text (lesson → section → screen).
- Nothing copied to other accounts: those in `drive.share_with` see the files in the shared school-year folder.
- If `notebook.enabled`: a Gemini Notebook notebook with those files as sources, each once, shared as editor with
  every account in `notebook.share_with` (spec 001 FR-011b), and its link in the topic folder's `notebook/«Abrir el cuaderno.pdf»`
  (spec 002 FR-047).
- A line in the student's run log for the placement and another for the notebook step, whatever its result.

Work from start to finish without asking for confirmation at each step. Only ask if the topic is ambiguous or
someone has to sign in (Science Bits or Google).

## alfabeta commands
Run every `python -m alfabeta` command with the Bash tool, as
`uv run --project <tools.repository> python -m alfabeta <command> --student <student> …`. Below, `alfabeta <command>`
is short for that. The skill needs a Bash tool that runs on the Mac: in a session whose Bash runs in a virtual machine,
which only sees `downloads.folder`, say so and stop.

**The run's lock.** Before opening Science Bits, `alfabeta lock take --student <student> --mode interactive` (`--mode
scheduled` when a scheduled task launches this skill); it answers `{"ok": true, "run": "<run>"}`. Every later
alfabeta command carries that run inline, `ALFABETA_RUN=<run> uv run …`, because each tool call is a new shell. The
lock is the student's and the Mac's browser's: a Classroom sync and this skill never run at once, since they share
the browser and the downloads folder. If `lock take` answers `lock_busy`, say another run is in progress and stop.
Renew it with `alfabeta lock renew` on every poll of the capture, between the build steps, while waiting for
someone to sign in, and before each source `nlm` uploads: after `sync.lock_idle_minutes` without a renewal it is
released and the run stops as `idle`. Release it with `alfabeta lock release` at the end. A run that stops before
placing a unit (the session expired and nobody signs in again, a challenge page, an interface the steps do not
describe, a timeout) stops the collector, restores the window's size and closes the run's tab (step 10), keeps what
earlier units placed, and ends with
`alfabeta log write-stop --reason session_expired|challenge|unexpected_ui|timeout`, which also releases the lock.

## Tools (in `$H`, copied from `scripts/`)
- `discover_lessons.js` — on the classes page: what the teacher shows of a unit in each language, and the queue.
- `orchestrator.js` — captures that queue in the background; downloads one zip per lesson.
- `watch.py` — copies each zip downloaded to `downloads.folder` since it started into `raw/`. A zip already there
  belongs to an earlier capture and is left alone.
- `build.py` — generates PDF + `.md` per language from `raw/`, with the topic's texts from `--config`; `render.py`,
  beside it, draws them, with the DejaVu fonts in `fonts/`.

Environment, all on the family's Mac: the Bash tool for commands (the `uv` project of `tools.repository` holds
reportlab, beautifulsoup4 and pypdf, so `build.py` runs under `uv run`; `watch.py` needs only `python3`); Claude in
Chrome (`mcp__claude-in-chrome__*`; read the `chrome-browser` skill first) for Science Bits; the `nlm` CLI
(`notebooklm-mcp-cli`) for the notebook, every command with `--profile <notebook.nlm_profile>` (`login` included).
Measured 2026-10-28 with nlm 0.15.8: only `nlm download` and `nlm config` take no profile, and nlm reads none from
the environment.

## Names
- School year: `student.school_year`, e.g. `2026-2027`.
- Subject: the `folder` of the `[[subjects]]` entry with `book = "sciencebits"` whose `book_class` is the class in
  Science Bits. If none matches, say so and stop: the family adds it to the configuration.
- Topic: one per unit of the book, never by Classroom's topic titles (the operator's decision, 2026-11-05: they do
  not delimit a unit). `Tema NN - <title>`, two-digit `NN`, with the title in the first of `sciencebits.languages`,
  read on that language's classes page even when the unit is hidden there. Its folder is
  `<storage.base>/<school_year>/<subject>/<YYYYMMDD> - Tema NN - <title>`, as the constitution names it; e.g.
  `2026-2027/<subject>/20261001 - Tema 01 - <title>`. `book place` finds it and never changes its date: the folder
  of the subject named `Tema NN - <title>` after its date, whatever the date and the title (of two, the one that
  already holds `sciencebits/`), and only if there is none, a new one dated today. Never create a topic folder by
  hand: an undated or re-dated duplicate splits the topic in two.
- Folders without `Tema NN` (`<date> - <teacher's title>`, `<date> - No topic`) are Classroom's; leave them alone.
- "The next topic" = the one after the highest `NN` among the subject's topic folders (`Tema NN - <title>` after
  the date) that already hold `sciencebits/` (not the order of units in the Science Bits class). Several new units
  in one run continue from there, in the class's order.

## Steps

Steps 1–3 and 10 run once. Steps 4–9 run once per unit, one unit at a time, each with its own work folder and its
own collector: every unit's lessons are numbered from `L1`, so in one `raw/` a later unit would overwrite an earlier
one's lessons.

Each tool call is a new shell and the configured paths start with `~`, which double quotes do not expand: write `$H`,
`$WORK` and every configured path as absolute paths in each command. `pkill -f` with a `~` in its pattern matches
nothing, and the collector would then go on copying the next unit's zips.

1. **Prepare.** Take the lock (alfabeta commands). `cp -R <tools.repository>/skills/sciencebits-a-notebooklm/scripts/.
   $H/`, so `$H` holds this version of the scripts and their fonts.
2. **Open Science Bits.** In a new tab of Claude in Chrome, `navigate` to `sciencebits.url`, and bring Chrome to the
   front with `osascript -e 'tell application "Google Chrome" to activate'`. If the login page or "Your session has expired" shows up: ask the family to sign in on that tab, ticking
   "Remember me on this device", with `osascript -e 'display notification "<what is needed>" with title "alfabeta"'`
   and in the conversation, and wait for their "ready", with `alfabeta lock renew --wait 100` in a background loop of
   at most an hour (`for i in {1..36}`), stopped once they answer. Never type credentials.
   The family sets three things in that Chrome profile, never you: for learning-bits.com, «Automatic downloads →
   Allow» (measured 2026-10-29: without it only the first lesson zip arrived and the rest waited for it) and
   «Pop-ups and redirects → Allow» (so the student can open lessons himself; the capture does not depend on it, since
   discovery stubs `window.open` and the capture uses an iframe); and «Ask where to save each file» off (measured
   2026-10-26: it opens a dialog per download).
3. **Read the units, in every language.** What the teacher shows differs by language and by lesson (measured
   2026-11-05: three units open in `eu` alone, «Oculta por el docente» in `es` and `en`), so never judge from one
   language. For each of `sciencebits.languages`, `navigate` to the same URL with `/intranet/<language>/` (e.g.
   `/intranet/en/`), open the `book_class` class in the list if it is not the open one, and run with `javascript_tool`:
   `await new Promise(r=>setTimeout(r,2500)); [...document.querySelectorAll('a.btn-acceder')].map(a=>({unit:a.closest('.box-center-unidad')?.textContent.replace(/\s+/g,' ').trim(),shown:!a.classList.contains('desactivado'),tip:a.getAttribute('data-original-title')}))`
   A hidden unit is listed too, with its title and a tooltip such as «Oculta por el docente», «Irakasleak ezkutatua»
   or «Hidden by the teacher». A unit hidden in every language is left out and reported; never force it. Note each
   unit's title per language, and which language shows it.
4. **Discover the lessons.** First, once per unit, `WORK=<downloads.folder>/alfabeta_work/<Subject>_TemaNN` with
   `raw/` and `out/`, both empty: move what an earlier attempt left to `$WORK/previous-<YYYYMMDDHHMMSS>/`, never delete
   it, because `book place` copies every file in `out/`. Then, on the classes page of a language that shows the unit,
   run in a single `javascript_tool` call `window.__UNIT={name:'<the unit's title on this page>',langs:[<the languages step 3 found showing it>]};` +
   the contents of `discover_lessons.js` (measured 2026-11-05: reading three units in one call took about 15 s; if the
   call times out, repeat it once, then stop as `unexpected_ui`). It answers per language `lessons`, `hidden`, `assessments` and `unread`,
   and leaves the queue in `window.__SB`, which only that tab holds: from here until the capture ends, do not navigate
   it. A language with no `lessons` is skipped and reported, never forced; `queued: 0` means the unit is left out. Two
   answers mean the page was not read, not that the teacher hid anything, and stop the run as `unexpected_ui`: any
   `unread` row, and all four lists empty in a language. `error`:
   `unit_not_shown_on_this_page` (go to a language that shows it), `ambiguous_unit` (a longer `name`),
   `SESSION_EXPIRED` (step 2, then this call again), `no_load` (once more, then stop as `unexpected_ui`),
   `language_without_assessment_words` (the script cannot tell that language's assessments, which must never open, so
   stop as `unexpected_ui` and tell the family).
   **Assessments**: never opened, started or clicked; `discover_lessons.js` lists them and leaves them out.
5. **Capture.** Start the collector with the Bash tool in the background, before the capture and only once:
   `caffeinate -i python3 -u $H/watch.py $WORK/raw <downloads.folder> > $WORK/watch.log 2>&1`. If it dies, start it
   again and relaunch the lessons missing from `raw/`: it ignores what was downloaded before it started.
   Bring Chrome to the front again (step 2; `nlm login` in an earlier unit may have opened another window) and keep
   this tab in front until the capture ends. `resize_window` changes the whole window and has no reset, so on the first
   unit read `[outerWidth, outerHeight]` with `javascript_tool` and keep it for step 10. Then `resize_window` the tab to
   width 1280, height 800, and run the contents of `orchestrator.js` with `javascript_tool`.
   **Poll back to back**, one `javascript_tool` call at a time, each waiting in the page, with `alfabeta lock renew` in
   a Bash call in the same message and nothing long in between:
   `await new Promise(r=>setTimeout(r,30000)); ({cur:window.__orch.current,done:window.__orch.done,stopped:window.__orch.stopped,n:document.getElementById('__fr')?.contentWindow.__job?.n,res:window.__orch.results.map(r=>r.tag+':'+r.n+(r.err?'!'+r.err:''))})`
   Measured 2026-11-05: with waits of about ten minutes between polls the capture all but stopped (11 screens in 20
   minutes); with consecutive polls of 30–35 s it ran about a lesson a minute. `browser_batch` of six such polls timed
   out, so never batch them. Tell the family how long it will take and that nobody should open Science Bits on another
   device. After the first two lessons, check `$WORK/watch.log` and `raw/`: if their zips are not there, the browser is
   holding the downloads (step 2).
   - `SESSION_EXPIRED` in `stopped` → step 2, then step 4's call again and not its folders, since `raw/` keeps what was
     collected and the collector keeps running (signing in reloads the tab), keep only what is missing with
     `window.__SB.queue=window.__SB.queue.filter(q=>[<missing tags>].includes(q.lang+'_'+q.id))`, and run
     `orchestrator.js` again.
   - `HIDDEN` → the lesson's page says it is not available, most likely because the teacher hid it after step 4 (such a
     page is not yet measured); the others go on. Report it; never force it.
   - Other `n:0`/errors → relaunch them the same way at the end. Check one zip with `items` per lesson and language.
   When `done` is true and every zip is in `raw/`, stop the collector: `pkill -f "watch.py $WORK/raw"`.
6. **Build.** `$WORK/unit.json`:
   `{"prefix":"TemaNN","langs":{"<language>":{"unit":"Tema N · …","course":"<the subject's full name> · <grade_level>"},…}}`, one
   entry per captured language, each title in its language, e.g. `"es"` and `"en"`. The topic's texts come only from
   this file: without `--config`, or without one of its keys, `build.py` stops and names the key.
   `uv run --project <tools.repository> python $H/build.py $WORK/raw $WORK/out --config $WORK/unit.json <captured
   languages>`.
7. **Verify.** pypdf, under the same `uv run`: pages, bookmarks, table-of-contents links, extractable text. Review the
   `.md`. If a lesson has few screens compared with its index (`menu` in meta.json), capture it again. `alfabeta lock
   renew` between these steps.
8. **Place.** `alfabeta book place --student <student> --subject <subject> --topic "Tema NN - <title>" --origin
   "$WORK/out"` copies `out/` into the topic folder's `sciencebits/` (see Names), keeping a changed file's previous
   version, and writes its line in the run log; what it does and refuses is its row in
   the repository's `specs/001-classroom-sync/contracts/cli.md`. From its JSON keep the `topic_folder` (relative to
   `storage.base`; `folder` is the `sciencebits/` inside it) and the files it `placed` (step 9 needs them). If it exits 1, restore
   the window's size, close the run's tab and say what happened; then end with `alfabeta log write-stop --reason drive_not_mounted` (or
   `lock_not_held`) for those two reasons, and with `alfabeta lock release` for the others: `ambiguous_topic` (two
   folders of the subject are topic `Tema NN`: the family merges them, never you), `no_book` (no `[[subjects]]` entry
   with that folder, or it has no book), `invalid_topic`, `no_origin`, `nothing_to_place`, `name_clash` (two files
   would get one name), and `write_failed`, which records what it copied, so running it again completes it.
9. **Gemini Notebook.** If `notebook.enabled` is false: `alfabeta log write-notebook --student <student> --topic "Tema NN -
   <title>" --result disabled`, and go on. Otherwise, with `caffeinate -i` on what takes long, and never printing an
   address (the share step's command prints none; never run `nlm share status` yourself, which lists them):
   - `nlm login --check`; if it fails, `nlm login --storage protected` in the background (a separate Chrome with no
     profile: this is expected). Ask the user to sign in, confirm the two-step verification and **not close the window**;
     `alfabeta lock renew` while you wait.
   - `nlm notebook list --json`; reuse the topic's notebook or create it with `notebook.title_pattern` (`{grade}` is
     `student.grade_level`, `{subject}` the subject's folder, `{topic}` the topic folder's name after its date;
     `--json`).
   - **Sources, each once.** `nlm source list <id> --json` gives each source's `id` and `title`. For each file of
     `$WORK/out`, skip it if a source has its file name as title and step 8 did not list it in `placed`; else
     `alfabeta lock renew`, then `nlm source add <id> --file "<file>" --wait --wait-timeout 300`, without `--title`, which
     would rename the source and break this comparison.
     A file step 8 placed again had changed: once its new source is added, remove the old one, the source with that
     title listed before the add, with `nlm source delete <source id> --confirm`, so the notebook answers from the
     new version and holds it once. If a run stopped between step 8 and that replacement, the next run's step 8
     reports the file unchanged and the old source stays: delete it by hand and run this step again. Measured
     2026-11-05: `source add --file` registers the source under the file's own name, so repeating the step adds
     nothing. Read in nlm 0.15.8's source on 2026-10-28, not yet measured against a notebook: `source delete
     --confirm` skips its prompt.
   - **Share.** `alfabeta notebook share --student <student> --topic "<subject>/<topic folder>"`, with the topic
     folder's full name (date included): it makes every account in `notebook.share_with` an **editor** of the
     notebook, inviting a missing one and raising a viewer, and never removes anybody (spec 001 FR-011c). Never
     invite by hand with `nlm share invite`, and never `nlm share public`. Its JSON carries `invited`, `raised`,
     `already` and `failed` (one entry per account that failed, by position). A failed account does not undo the
     notebook: note it and report it, by count. Measured 2026-10-26: the school domain allows a notebook owned by a
     personal Gmail account to be shared with the school account, and it opens there; if the school's admin changes
     that, the account fails as `refused` and the summary says so.
   - **Link.** A shared notebook is not listed for the student until opened once by its link (measured
     2026-10-31; spec 002 FR-047), so leave the link where the student looks: `uv run --project
     <tools.repository> python <tools.repository>/skills/study-pack/scripts/print_pack.py link <id>
     "<storage.base>/<topic_folder>/notebook/Abrir el cuaderno.pdf" --student <student>`, with step 8's
     `topic_folder`; the path must be absolute (it reads the link from `nlm notebook get` and
     needs no default profile). Run it on every run that finds the notebook shared with an account of
     `notebook.share_with`, now or before: it writes the page only when absent or carrying another link. If it
     fails, the notebook stays; the summary says the notebook's link was not left in the folder, and the next run
     leaves it. The other accounts see the page through the shared school-year folder; nothing is copied.
   - Test: `nlm notebook query <id> "<short question>"`.
   - `alfabeta log write-notebook --student <student> --topic "Tema NN - <title>" --result created|unchanged --shares
     <invited>,<already>,<failed>`: `unchanged` when the notebook already existed and no source was added or
     replaced, `created` otherwise; the three counts are over `notebook.share_with`, from the share step's JSON: `invited` plus
     `raised`, `already`, and the length of `failed`.
   - If `nlm` fails: `uv tool upgrade notebooklm-mcp-cli` once; if it still fails, `alfabeta log write-notebook … --result
     failed --reason "<what failed, in a few words, with no id or address>" --shares <invited>,<already>,<failed>`
     with the counts reached so far, and tell the family the topic is in its folder but the notebook step failed.
     What step 8 placed stays as it is.
10. **Close.** Move every `sb_*.zip` from `downloads.folder` to
    `<downloads.folder>/alfabeta_work/collected-<YYYYMMDDHHMMSS>/`, never delete them; `resize_window` back to the size step 5 kept, close
    the run's tab, `alfabeta lock release`, and summarise per unit: folder, notebook link, accounts it is
    shared with (by count) and any failed invite, whether the link page was left in `notebook/`, screens per language
    and what was left out: per language, the hidden lessons, and the languages and units the teacher does not show.

## Limits
- Do not decrypt the `/seculogged/` XML files or force the disabled "Versión PDF" (PDF version): capture what the student sees.
- Videos are not captured (they remain as "[Vídeo (ver en la plataforma)]").
- Personal and educational use; do not redistribute the material.
