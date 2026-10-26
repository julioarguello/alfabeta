# Research: Classroom → family Drive (spec 001)

Phase 0 of the plan. Each decision carries its reason and the alternatives rejected. The observed
facts cite where they come from; nothing below names the student, the teachers or real identifiers.

## Observed facts

Observed on 2026-10-25 in the student's Classroom, in Chrome (Claude extension), read-only: the class
list, «Trabajo de clase» (Classwork) of two subjects, one task detail page, the stream of one class,
«Tareas pendientes» (To-do) and the root of the student's personal Drive.

| Fact | Observed in |
|---|---|
| About a dozen visible classes and several hidden ones; titles in several languages that include the grade level and the group, with formats that vary by teacher | Classroom home page |
| A subject with a Science Bits book does not appear among the visible classes | Home page; left as a question for the configuration (a hidden class?) |
| The teacher's topics do not match the book's: one teacher's topic, with another number and in another language, gathers material from one book topic and from other content; another teacher's topic (an introductory one) does not exist in the book | «Trabajo de clase» of a subject with a book |
| Another subject numbers topics and tasks («N. título», «N.M título» — "N. title", "N.M title") and has topics that are not units (preparation for an initial test, saved exams, «Sin tema» (No topic)) | «Trabajo de clase» of a subject without a book |
| Types: «Tarea» (Assignment), «Material» (Material) and «Pregunta» (Question) | Both «Trabajo de clase» pages |
| The listing shows a single date per item: «Fecha de entrega: 13 oct» (Due: 13 Oct), «Sin fecha de entrega» (No due date), «Publicado: 22 oct» (Posted: 22 Oct) or «Última modificación: 1 oct» (Last modified: 1 Oct); never the year; sometimes relative («Mañana, 8:00» — Tomorrow, 8:00) | Both «Trabajo de clase» pages |
| The listing marks as «Completada» (Completed) a task whose detail says «Calificado» (Graded) and «El profesor ha indicado que falta esto» (The teacher has marked this as missing) | Listing and detail of the same task |
| A task's detail shows author, posting date, points, due date, instructions and the «Tu trabajo» (Your work) panel with its status and the «Añadir o crear» (Add or create) and «Volver a entregar» (Resubmit) buttons; no numeric grade was seen | Detail page of a graded task |
| The detail URL carries stable class and item identifiers: `/u/<n>/c/<class>/a/<item>/details` | Address bar |
| Expanding a material shows its description and its attachments; an attached PDF links to `drive.google.com` | «Trabajo de clase», expanded material |
| The stream shows each post with its exact «Fecha de creación» (Creation date) and free-text announcements; one announces, in another of the class's languages, an exam with its weekday and date, and the list of contents it covers | Stream of a subject with a book |
| «Tareas pendientes» has the tabs «Asignado» (Assigned), «Sin entregar» (Missing) and «Hecho» (Done), and collapsed sections (no date, this week, next week, later) | To-do page |
| The same Chrome holds several Google accounts; the `/u/<n>` index of the school account is not fixed | Account button at `/u/1` to `/u/5` |
| The student's personal Drive already has folders of their own in the root of «Mi unidad» (My Drive) | Root of «Mi unidad» |
| Google Drive for desktop is installed, but the student's personal account is not mounted | `~/Library/CloudStorage/` |

## Decisions

### R1. How it repeats: skill + deterministic scripts + scheduled task

- **Decision**: a `classroom-sync` skill that Claude follows (like the Science Bits one) and that
  orchestrates deterministic Python scripts. The daily schedule uses the scheduled tasks of the
  Claude desktop app, with a self-contained prompt that invokes the skill.
- **Reason**: the mechanical part (state, identifiers, names, structure, agenda, collecting
  downloads) gives the same result on every repetition if scripts do it (FR-021b). What needs
  judgement (matching topics, detecting an exam in an announcement in another language) Claude does
  within the same run, with no API keys or separate cost, and it is recorded so it is not repeated.
- **Alternatives**: (a) only a prompt to Claude, no scripts: not repeatable, each run decides
  differently; (b) a standalone script with Playwright and its own profile: it runs without Claude
  but loses the judgement and forces us to hold a minor's session; that is the local MCP epic
  (issue #2).
- **Risk to measure first (spike S2)**: whether a scheduled task can use the browser with the
  student's session and download files (captures and attachments) without anyone approving each
  download at that moment. The tool's documentation says the task runs while the app is open and with
  a self-contained prompt; it says nothing about the browser or downloads. If it cannot, the
  scheduled run is limited to a notice and the family launches it with a command.
  Measured 2026-10-26 with a one-off scheduled task of the desktop app (saved in Auto permission
  mode, fired at 11:20, nobody at the keyboard; evidence outside the repo):
  - the Claude in Chrome tools were available, Classroom loaded with the school session (12
    classes, interface in Spanish) and no tool-permission prompt reached the run;
  - a detached process started from one tool call was still alive in a later call, adopted by
    the system (parent PID 1) and beating every 2 s, so the watcher of R6 survives a scheduled run
    as well as an interactive one (measured interactively on 2026-10-25);
  - a `blob:` download from Classroom arrived, but its final name appeared about 42 s after the
    click; the cause was not observed, and whether a dialog showed in that window was not recorded.

  The test task was deleted afterwards. Still open: the download dialog of R12.
- **Second risk, measured during S3: the school session does not last.** On 2026-10-25 and
  2026-10-26 the school account at `/u/<n>` was sent three times to Google's «confirm your
  identity» page (`accounts.google.com/…/confirmidentifier`). The last time, the operator had signed in
  shortly before 09:15 and the session was gone by 10:35. With the session gone, the hidden iframe of R3 loads
  the sign-in page, so its document becomes cross-origin: the extractor must treat a cross-origin
  iframe as «session expired» and stop with that reason. Whether this is a school policy, and how
  long a session lasts, was not measured; a daily unattended run depends on it. The next session,
  opened at 10:38 the same day, was still alive at 13:25, so the lifetime varies.

### R2. Browser: Chrome with the Claude extension

- **Decision**: Chrome with the Claude extension, which is what the operator prefers and where the
  family's sessions already are.
- **Account selection**: the school account is located by walking `/u/0…/u/9` and comparing the
  email on the account button with the one in the configuration, locally. Never
  `authuser=<email>` in a URL (FR-031). The index found is stored in the run's log, not in the
  configuration or the state.
- **Alternative**: the app's built-in browser. The extractor would be the same JavaScript, but the
  direct download already failed in it (issue #1); it is left for a later epic that tests it.

### R3. Extraction: a JavaScript extractor over the viewing pages

- **Decision**: `extract.js` is injected with the browser's JavaScript tool and returns JSON: the
  class list (visible, hidden, archived), topics and items from «Trabajo de clase», each item's
  detail (status, dates, modification mark, attachments, student submission, grading) and the
  stream's posts. It navigates only to the home page, «Trabajo de clase», the stream and the detail
  page of assignments, materials and questions; it never follows a link to a form or quiz and never
  clicks the «Tu trabajo» panel. It waits at least 2 s (with jitter) between pages.
- **How it walks the pages (decided with S3)**: the script stays injected in the tab on the home
  page and loads each page it reads in a **hidden same-origin iframe** (off screen, 1200×800),
  waiting until the iframe's document shows the expected labels, with a timeout and one retry. It
  never navigates the tab itself, so the injected script is not lost. Rejected: a `fetch` of the
  detail page returns HTTP 200 and about 0.8 MB of HTML that holds none of the content (no status,
  no «Tu trabajo», no modification mark), because Classroom renders it with JavaScript; and
  re-injection by Claude on each page costs one tool call per item.
- **Complete capture or not**: each capture says whether it reached the end of the class
  (`complete`). A truncated capture withdraws no items (FR-027).
- **Stops**: if it finds an anti-bot challenge (CAPTCHA, verification page, «demasiadas peticiones»
  — too many requests) or does not find the expected Spanish UI labels, it returns a stop mark
  instead of data and the skill ends the run with a reason.
- **Reason**: the reliable status is on the detail page (observed fact); the listing serves only to
  discover items and their «Última modificación» mark. The extension hides base64-looking values in
  its output, so the extractor returns the identifiers already split out of the URL.
- **Alternatives**: reading the Classroom web app's internal calls (more stable, undocumented): left
  for the local MCP.

Measured 2026-10-25 against the student's Classroom in Chrome (Claude extension, school account,
interface in Spanish), read-only, with no title, name or identifier printed (spike S3):

| Fact | How it was read |
|---|---|
| Classwork: `/u/<n>/w/<class>/t/all`; assignment `/u/<n>/c/<class>/a/<item>/details`; material `/u/<n>/c/<class>/m/<item>/details`; question `/u/<n>/c/<class>/mc/<item>/details` (an `/a/` link to a question is served at `/mc/`); student's work `/u/<n>/c/<class>/sp/<student>/all/default` | `href` patterns on the home and classwork pages, and the iframe's `location.pathname` |
| The identifier in the URL is the item's numeric id encoded in base64; the classwork rows carry the numeric id in `data-stream-item-id` and the type in `data-stream-item-type` (`1` assignment, `5` material, `2` question) | Decoding one URL id against its row's `data-stream-item-id`; types counted per class |
| Attachments to Google files link to `docs.google.com/<type>/d/<id>/edit` | Links on one material's detail page |
| The assignment detail page shows a modification mark with the shape «(Última modificación: N oct)» | Text of one assignment's detail page |
| Reading a question's detail page does not change «Tu trabajo»: the student's work page gave the same text hash before and after | Hash of `/sp/<student>/all/default` around one question's detail load |
| A page in the hidden iframe was ready in 1.0–1.2 s (classwork, material, question, stream); one question load timed out at 25 s and succeeded on the retry | `performance.now()` around each iframe load |
| 12 classes and 93 items in total; the largest class has 21 items | Classwork of every class, through the iframe | Downloading Drive attachments (spike S1, first technical risk)

- **Problem**: the direct download `drive.google.com/uc?export=download` failed in the built-in
  browser (issue #1). Attachments link to `drive.google.com`.
- **Decision**: try in this order, with the school account's session and a real attachment, and keep
  the first one that leaves the complete file in the downloads folder:
  1. `drive.usercontent.google.com/download?id=<id>&export=download&authuser=<n>`;
  2. for Google Docs, Slides and Sheets, `docs.google.com/<type>/d/<id>/export?format=pdf&authuser=<n>`;
  3. the Drive viewer's download button.

  Measured 2026-10-26 against four real attachments of one class (two PDFs, one PNG, one uploaded
  `.pptx`, all Drive files of type `file`), with the operator present: method 1, loaded in a
  hidden `iframe` from a Classroom page with the school account's `authuser`, left all four complete
  in the downloads folder within 2 s, under their original names; a name already present got
  « (1)» before the extension. Not covered: Google Docs, Slides and Sheets (method 2), since the
  class had none, and whether Chrome showed the dialog of R12 (the operator reported none).
- **When to download** (item and attachment ids with their own rules, per the URL patterns recorded
  in S3): the first time, and afterwards only if the item shows a modification later than the last
  replica, if the attachment's name or type changes, or in the periodic full review
  (`[sync] full_review_days`; template value: 7). The date of the last full review is that of the
  last log line with `full_review: true`, not a state field: a review that finds the same bytes does
  not rewrite the state. That avoids hundreds of downloads a day (FR-010, FR-026) and meets
  principle V.
- **Collection**: `downloads collect` (over the `[downloads] folder` folder) moves each expected file
  and ignores Chrome's half-downloaded `.crdownload` files, checks that it is complete and leaves it
  ready to place (FR-018). It collects only what it requested.

### R5. Dates without a year, and relative dates

- **Decision**: a single date resolver: the year inferred from the school year (September to
  December, first year; January to August, second), relative dates («Hoy» — Today, «Mañana» —
  Tomorrow, weekdays) against the capture time (`captured_at`), not that of the run that applies it,
  all in `Europe/Madrid` with `zoneinfo`. The posting date comes from the «Fecha de creación» of the
  stream or the detail page, never from «Última modificación».
- **Tests**: a table of cases, including the year change (December/January), clock changes and a
  capture applied the next day.

### R6. State, lock and idempotency

- **If the watcher does not survive the tool call (S2)**: the lock becomes a lease file holding the
  time of its last renewal; each subcommand takes the `flock` only while it runs, checks that the
  lease belongs to its run and renews it; a lease left unrenewed for `lock_idle_minutes` can be taken,
  and whoever takes it writes the previous run's `stopped` line with reason `idle`. The subcommands in
  `contracts/cli.md` and their outputs do not change; only the watcher disappears.
- **Decision**: one JSON state file per student in their local data folder, written atomically
  (temporary file and rename) and only if it changes, with one record per item and per replica:
  Classroom identifier, role, relative path, hash (SHA-256), version and modification mark seen. Each
  run's log goes in JSON Lines in the same folder, together with the `/u/<n>` index used, which does
  not go to the state.
- **Lock**: `lock take` opens with `fcntl.flock` `data/lock` (the student's) and
  `<home>/.browser.lock` (the Mac's: all students share Chrome and the downloads folder), and a
  watcher process holds them for the whole run. Every subcommand renews the lock, and `lock renew`
  renews it during the browser's long stretches (between classes, between batches of downloads, at
  each poll of a Science Bits capture); if `lock_idle_minutes` pass without a renewal, the watcher
  assumes the run died, releases both and writes a `stopped` line with reason `idle`. If the watcher
  dies, the system releases the `flock`s. A busy lock stops the run with its own reason (FR-030).
- **Stops before apply**: `log stop --reason <r>` writes the `stopped` line of a run that stops in
  the browser (expired session, challenge, unexpected UI) or before it (Drive not mounted). A busy
  lock is logged by `lock take` itself, and a stop in `plan` or `apply` by those commands themselves.
- **Reason**: standard library, human-readable, enough for hundreds of items per school year. A
  second run with no changes compares hashes and writes nothing (FR-025).
- **Alternative**: SQLite. More robust at high volume; unnecessary here (constitution IX).

### R7. Claude's judgement: class links, matches and detected exams

- **Decision**: the scripts prepare the list of what needs a decision (unlinked classes, unmatched
  topics, posts with exam cues) and Claude proposes, with reason and confidence (high, medium, low),
  following the skill. The family confirms, rejects, corrects (date, category, or dismissing an exam)
  or changes (an already confirmed match). Decisions go to `data/decisions.json`, tied to the
  Classroom identifier. A confirmed decision is not proposed again (FR-021b); changing it moves it to
  `superseded` and creates the new one.
- **Unconfirmed**: the items of an unmatched topic go to their month folder; a detected exam enters
  the agenda marked `detected` until the family confirms or corrects it.

### R8. Tests against synthetic pages

- **Decision**: real pages are saved only outside the repository (`data/raw-captures/`). What enters
  `tests/fixtures/classroom/` is **synthetic** pages: `anonymize` keeps the structure (tags, CSS
  classes, hierarchy) and the UI labels on an allowlist («Trabajo de clase», «Fecha de entrega»,
  «Tu trabajo»…), and invents every remaining text and attribute: titles, descriptions, dates, file
  names, ids and accessible text. It refuses to write if any input text outside that list survives.
- **Reason**: the material belongs to its authors and is not redistributed (constitution IV), and no
  fixture holds material or data of a real student (III). The structure is all the extractor's tests
  need.
- **Check**: the personal-data guardrail (FR-005) also runs over the synthetic pages. No test and no
  CI job calls Classroom (constitution VI).
- **Label allowlist (from S3)**: the UI labels seen on 2026-10-25 on the pages the extractor reads
  (page text and `aria-label`s, compared against a candidate list; the interface in Spanish):
  - navigation: «Trabajo de clase», «Tablón», «Personas», «Ver tu trabajo»;
  - classwork listing: «Tarea», «Material», «Pregunta», «Sin tema», «Fecha de entrega»,
    «Sin fecha de entrega», «Publicado», «Última modificación»;
  - detail pages: «Tu trabajo», «Asignado», «Entregado», «Sin entregar», «Añadir o crear»,
    «Marcar como completado», «Entregar», «Tu respuesta», «puntos», «Comentarios de la clase»,
    «Comentarios privados»;
  - stream: «Próximas entregas», «Ver todo», «ha publicado», «publicado una nueva tarea»;
  - date shapes: «N oct», «N sept», «Hoy».
- **Open question for the data model**: «Sin entregar» appeared as the status of a question's
  «Tu trabajo» panel and on the student's work page. The status table in `data-model.md` maps
  «Asignado» and «Falta» but not «Sin entregar»; whether it maps like «Falta» is not measured.
- **How long a class takes (from S3)**: about 4 s per item (1.0–1.2 s for the iframe, the 2 s minimum
  wait with jitter, and the time to read the panel), so about 2 minutes for the largest class
  measured on 2026-10-25 (21 items) and under 7 minutes for every class of that day (93 items).
- **`lock_idle_minutes` stays at 30**: the longest stretch without a renewal is in the Science Bits
  skill, whose `nlm source add … --wait --wait-timeout 300` blocks up to 5 minutes per file; in the
  Classroom skill it is one class (about 2 minutes), renewing between classes. T017 copies the
  contract's value to `config/template.toml`.

### R9. Per-student configuration: TOML with a mirror template, outside the repo

- **Decision**: the template is `config/template.toml` in the repository, with every key, `changeme`
  values and one comment per key. Each student's real configuration is
  `~/.alfabeta/<student>/config.toml`, a copy of the template with the values filled in. What
  alfabeta writes (decisions, state, log, lock, plan, captures) goes in
  `~/.alfabeta/<student>/data/`.
- **Location**: `~/.alfabeta/` is the declared location, not a silent default: if it does not exist,
  alfabeta stops and says so. The global `--home` option replaces it (tests). The student is chosen
  with `--student <id>`, resolved only once at the command's entry point.
- **Validation**: the set of keys (with their types) of the real configuration must equal the
  template's; a key that is missing, extra, of another type or containing `changeme` stops the run
  and names the key (FR-003). A test also checks that every key the code reads is in the template.
- **Why TOML**: it allows comments (the template documents each key) and is read with the standard
  library (`tomllib`). What alfabeta writes goes in JSON, also standard.
- **Alternatives**: a `.env` per student (cannot express lists or the subject map); JSON for the
  configuration too (no comments); YAML (a new dependency). The existing `config.example.json` file
  goes away.

### R10. Code: one package with one command, and thin skills

- **Decision**: a Python package `alfabeta` in `src/alfabeta/` with a single command
  (`python -m alfabeta <subcommand>`, the standard library's argparse) that groups the deterministic
  logic. The skills (`skills/classroom-sync/`, `skills/sciencebits-a-notebooklm/`) contain the
  `SKILL.md` Claude follows and the JavaScript that runs in the browser, and call that command.
- **Sources**: a `Source` Protocol with `ClassroomSource` and `BookSource`; each replica's subfolder
  is the name of its source (`classroom`, or the subject's `book` value).
- **Runtime validation**: `capture.py` checks each capture's essential keys by hand (standard
  library); the full schemas are checked in tests with `jsonschema` (a development dependency). The
  schemas live in `src/alfabeta/schemas/`, a copy of `contracts/`.
- **Reason**: a single place for the naming, structure and state rules that Classroom and the books
  share; `src/` and `tests/` are the two roots the type checker and the linter expect.
- **Dependencies**: none at runtime. Development: `ruff`, `pyright` (strict mode, with ruff's
  annotation rules), `pytest` and `jsonschema`, managed with `uv` (`pyproject.toml`, `uv.lock`,
  `.python-version` = 3.12). A single gate, `make ci`, identical locally and in CI.

### R11. Tests of the JavaScript extractor

- **Decision**: `extract.js` is tested with `node --test` and `jsdom` against the synthetic pages
  (R8). It is the only Node development dependency, declared in `package.json`, and the `make ci`
  gate runs it. The tests check the output's keys by hand; the full schema is checked in Python over
  the test JSON captures.
- **Checkable read-only behaviour**: a test installs click, form-submit and navigation listeners on
  the synthetic page and checks that the extractor clicks no button in the «Tu trabajo» panel,
  submits nothing and navigates to no form or quiz.
- **Design**: the extractor only reads the DOM and returns the texts as displayed («Fecha de
  entrega: 13 oct»); all interpretation (dates, statuses, categories) lives in Python and is tested
  there.

### R12. From the browser to disk

- **Decision**: the extractor does not return the JSON to the conversation: it downloads it as a file
  (`alfabeta-capture-<run>-<class>-<stamp>.json`, with the `run` Claude passes it when injecting it)
  to the downloads folder, just as the Science Bits capture downloads its zips, and
  `python -m alfabeta downloads collect` moves it to `data/captures/`.
- **Reason**: hundreds of items per class must not pass through Claude's context; a file can be
  saved, compared and used as a test.
- **Open risk, against the unattended requirement**: a run must not wait for anyone to approve
  anything in the browser. Measured 2026-10-26 in the operator's Chrome (Claude extension, school
  account), downloads of a `blob:` file created by a script:
  - from `example.com`, the file arrived with no dialog;
  - from `classroom.google.com`, Chrome showed the «descargar varios archivos» (download multiple
    files) dialog and held the download until the operator accepted it, although the operator saw
    `classroom.google.com` under «Se permite» (Allowed) in «Descargas automáticas» (Automatic
    downloads). Whether that setting belongs to the same Chrome profile as the extension was not
    measured;
  - one probe arrived within the same minute while a dialog was showing, and two earlier probes never
    arrived; which download each dialog belonged to was not recorded.

  Measured 2026-10-26 in a manual import of every class (85 attachment downloads, one hidden `iframe`
  every 3 s pointing at `drive.usercontent.google.com/download` or a `docs.google.com/…/export`):
  84 files arrived complete, but the operator had to confirm Chrome's dialog, so these origins hold
  the download, not Classroom. One video of a few hundred MB never arrived; Drive answers large files
  with a confirmation page instead of the file. Tried: list `drive.usercontent.google.com` and `docs.google.com` under «Descargas automáticas» →
  «Se permite» as part of the installation, but it did not work: on 2026-10-26, right after the
  operator added both origins, two downloads fired 1.5 s apart from a Classroom page arrived within
  2 s and the operator still saw the dialog. Arrival time therefore does not show the absence of
  the dialog. Whether the setting was made in the same Chrome profile as the extension is not known. Rejected: downloading with `curl` outside the browser, because it
  needs the school session's cookies, a secret no tool may handle (constitution, minors' data).

  Putting every page of a run in **one** file (S3 saved six pages as one 6.8 MB JSON) leaves at most
  one download per run, but on 2026-10-26 even that single download needed the dialog. Until the
  dialog is explained and removed, a download from Classroom is not an unattended transport; S2
  (T011) answers it for scheduled runs, and the alternatives are a receiver on `127.0.0.1` or
  returning the JSON in parts through the browser tool.

### R13. Personal-data guardrail

- **Decision**: `python -m alfabeta guardrail` checks the files in the change (pre-commit hook) or
  the whole repository (CI). Generic detectors: emails (except `example.org` and `example.com`),
  user paths, and identifiers shaped like Classroom, Drive or notebook ids (UUID) (dependency lock
  files excluded: `uv.lock` and `package-lock.json`). Placeholders between `<…>` and the synthetic
  `synth-<n>` ids of the test pages do not count. Named detectors: the identifying values of the real
  configurations present on the Mac (the student's `id`, `display_name`, `account`, `root`,
  `classroom_class`) and the Classroom and Drive ids stored in their `data/decisions.json` and
  `data/state.json`, never displaying them; book topic titles are not personal data and are not
  searched for. Because the repository is public, whatever is in a commit is already published: on
  top of the tree, T000 (by hand, before the guardrail exists) and T059 (`guardrail --history`) run
  the detectors over the history (`git log --all -p`).
- **Id shapes**: the exact Classroom and Drive shapes come from the URL patterns S3 records; a long
  code identifier (`snake_case`, `camelCase`, test file names) does not count.
- **Exit codes**: 0 clean; 1 finding (file and line, without repeating the data); 2 the generic
  detectors checked no file; 3 a detector misses the defect the guardrail itself plants in memory on
  every run. With no real configurations on the machine (CI, another contributor) the named
  detectors do not run: this is said on stderr and does not change the exit code.
- **Tests**: cases that must fire and cases that must not, with invented data, including a `uv.lock`,
  placeholder paths `/Users/<someone>/`, `synth-<n>` ids and non-identifying configuration keys
  (`school_year`, `languages`).

### R14. What this epic does not need

- **Keychain**: no secret of its own. The Classroom session lives in Chrome and the Gemini Notebook
  session in `nlm`; alfabeta stores no cookies or tokens. The secrets layer is planned for and left
  empty.
- **Numeric grade**: not seen in a graded task's detail; `grading` stores the grading state, the
  grade if Classroom shows it to the student, and the comment (spec, story 6).
