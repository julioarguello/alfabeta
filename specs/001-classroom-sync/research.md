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

Observed on 2026-10-27 in a manual, read-only read of the school account (no title, name or
identifier recorded here):

| Fact | Observed in |
|---|---|
| Two assignments of one subject, posted that morning, were not in the capture of 2026-10-26 | «Tareas pendientes», compared with that capture |
| «Tareas pendientes» is `/u/<n>/a/not-turned-in/all`, with the sections «Sin fecha», «Esta semana», «Próxima semana» and «Más tarde», each collapsed and opened by its header button | To-do page |
| «Sin entregar» is `/u/<n>/a/missing/all`, with a «Ver todo» (see all) button | To-do page, «Sin entregar» tab |
| An assignment's detail page `/u/<n>/c/<class>/a/<item>/details` gives its instructions and «Fecha de entrega: Mañana, 8:00» | Detail page |
| The to-do pages and the detail pages were enough to know what is pending and when it is due | The manual read as a whole |
| The capture of 2026-10-26 placed a bare «8:00» (today at 8:00) on the wrong day | That capture, compared with the detail page in the read of 2026-10-27 |
| Google showed «Demuestra que eres tú» (`accounts.google.com/…/confirmidentifier`) before Classroom opened, in a browser where the school account was already signed in | Address bar |

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
- **2026-10-27: the operator excludes their Mac and their browser from the unattended read.** The
  scheduled task of the desktop app needs the Mac on, the app open and the operator's Chrome with
  the student's session. For a student with the runner enabled, the scheduled read moves to the
  unattended runner (R15 to R19); this decision stays for the full sync and for students without
  the runner.

### R2. Browser: Chrome with the Claude extension

- **Decision**: Chrome with the Claude extension, which is what the operator prefers and where the
  family's sessions already are.
- **Account selection**: the school account is located by walking `/u/0…/u/9` and comparing the
  email on the account button with the one in the configuration, locally. Never
  `authuser=<email>` in a URL (FR-031). The index found is stored in the run's log, not in the
  configuration or the state.
- **Alternative**: the app's built-in browser. The extractor would be the same JavaScript, but the
  direct download already failed in it (issue #1); it is left for a later epic that tests it. It
  also lives on the Mac, so it cannot be the browser of a read without the Mac (R17).
- **The unattended runner (2026-10-27)**: its own headless Chromium, driven by alfabeta's code with
  Playwright, runs the same `extract.js` in a `todo` mode (R15 to R19). Its profile holds only the
  school account, so `/u/0` is expected, and the account button is still compared locally.

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
| 12 classes and 93 items in total; the largest class has 21 items | Classwork of every class, through the iframe |

### R4. Downloading Drive attachments (spike S1, first technical risk)

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
  « (1)» before the extension. Method 2 measured 2026-10-26 in the
  manual import of every class: 14 of 14 Google files (8 Docs, 6 Slides) exported with
  `docs.google.com/<type>/d/<id>/export` (`/export/pdf` for Slides) arrived as valid PDFs
  (`%PDF-` header). Not covered: Sheets, since no class had one. Large videos are the open case
  of R12. The dialog the operator saw was Chrome's «Guardar como» (R12).
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

- **First real run, measured 2026-10-27** (operator's Chrome, extension profile, school account,
  one class with 13 items, read only; no title, name or id printed):
  - The class list was captured and downloaded as a file with no dialog, and `downloads collect`
    took it.
  - In the hidden iframe, a page's content was readable 4–13 s after loading started, but the
    iframe's `load` event sometimes came after more than 30 s. The loader now polls from the start
    and waits for what each page kind must show (its rows; its title and date; its posts).
  - The school account's session expired twice the same afternoon, the second time less than
    30 minutes after the operator signed in. Once expired, every iframe lands on Google's sign-in
    page, which, being another origin, reads as an empty frame: the loader now stops the class with
    `session_expired` instead of waiting out its timeout. How long the session lasts was not
    measured, and it decides whether an unattended run (#13) can work.
  - The lock was released as `idle` after 30 minutes without a renewal during the browser part. The
    watcher worked as designed; the skill must call `lock renew` between browser steps.
  - An item posted the day before shows «Ayer» as its date; the extractor accepts «Hoy» and «Ayer».
- **Second real run, measured 2026-10-27** (same class, same bench): the whole class (13 items and
  the stream) was captured in 75 s, the session still valid, `complete: true`. A dry plan in a
  scratch copy showed every attachment named «Archivo adjunto: <tipo>: <name>»: that is the
  anchor's aria-label, and with it no download would ever match its expected name. The extractor
  now drops the prefix. The synthetic pages had not shown it because the anonymiser replaced the
  whole label; it now keeps the prefix and the kinds seen («PDF», «Imagen», «Microsoft Word»,
  «Microsoft PowerPoint», «vídeo de YouTube»).
- **First apply, measured 2026-10-27** (FiQui, with the family's go-ahead): the 26 October import's
  `classroom/` folders were moved to a local quarantine, then 16 replicas were placed and a second
  `apply` reported 0 added, 0 changed. The 9 downloaded files are byte-identical to the imported
  ones. The descriptions had lost their line breaks: the extractor read `textContent`, which joins
  the lines a `<br>` separates; it now ends a line at a `<br>` or a block element.

### R5. Dates without a year, and relative dates

- **Decision**: a single date resolver: the year inferred from the school year (September to
  December, first year; January to August, second), relative dates («Hoy» — Today, «Mañana» —
  Tomorrow, weekdays) against the capture time (`captured_at`), not that of the run that applies it,
  all in `Europe/Madrid` with `zoneinfo`. The posting date comes from the «Fecha de creación» of the
  stream or the detail page, never from «Última modificación».
- **Tests**: a table of cases, including the year change (December/January), clock changes and a
  capture applied the next day.
- **Per page, not per capture (2026-10-27)**: the capture of 2026-10-26 placed a bare «8:00» on the
  wrong day, and a read that crosses midnight would resolve «Mañana» against the wrong day if it
  used the capture's single `captured_at`. Each detail page now carries its own `seen_at`, and the
  resolver uses it; `captured_at` is only the fallback for a page without one. The resolver on
  `main` already reads a bare time as the day of the instant it is given (`src/alfabeta/dates.py`);
  what changes is which instant `capture.py` gives it.

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
- **Unconfirmed**: the items of an unmatched topic go to the teacher's topic's own
  `<YYYYMMDD> - <teacher's title>` folder (constitution 1.3.0; it was the month folder); a detected exam enters
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
- **«Sin entregar»** appeared as the status of a question's «Tu trabajo» panel and on the student's
  work page. Decided by the operator on 2026-10-27: it means nothing was turned in, so it maps like
  «Asignado» and «Falta» (`pending` before the due date, `overdue` after it).
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
  84 files arrived complete, but the operator had to answer a dialog for them. One video of a few
  hundred MB never arrived; Drive answers large files with a confirmation page instead of the file.

  **Cause, identified the same day**: the dialog was Chrome's «Guardar como» (Save as), shown because
  «Preguntar dónde guardar cada archivo antes de descargarlo» was on in the extension's Chrome
  profile. It was not the automatic-downloads prompt: the description of it above came from wording
  offered to the operator, not from what they saw. Allowing `drive.usercontent.google.com` and
  `docs.google.com` in «Descargas automáticas» did not remove it; switching that setting off did.
  After the change, two downloads fired 1.5 s apart from a Classroom page arrived within 5 s and the
  operator confirmed no window appeared. Arrival time alone proves nothing: with the setting on, a
  quickly answered dialog arrives just as fast.

  **Installation requirement** (the extension's Chrome profile): «Preguntar dónde guardar cada
  archivo» off, and the download location set to the folder in `[downloads] folder`. With that, a
  download from Classroom is an unattended transport, in one file per run or one per attachment.
  Rejected: downloading with `curl` outside the browser, because it needs the school session's
  cookies, a secret no tool may handle (constitution, minors' data). Still open: large Drive files
  (the confirmation page). Constitution 2.0.0 lets the unattended runner keep the sign-in secret as a
  secret inside its own browser (R15); the runner downloads nothing (spec FR-034), so this
  rejection still holds for attachments.

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
  empty. The unattended runner (R15) is the exception: its stored session is alfabeta's first
  Classroom secret, kept in the cloud project's secret store, not in the keychain.
- **Numeric grade**: not seen in a graded task's detail; `grading` stores the grading state, the
  grade if Classroom shows it to the student, and the comment (spec, story 6).

### R15. Signing in for a run with nobody present: a vault, and two routes

- **Proposal (operator, 2026-10-27)**: a browser alfabeta drives by itself, headless and not the
  operator's Chrome, with the student's credentials kept in a vault so that it can sign in alone.
  On the constitution: «me da igual que rompa la constitución, pues la cambiamos». On the
  mechanism: «no te quiero condicionar, dime tú», and «no me importa hacer esa prueba» to the
  recommendation below.
- **Decision**: a vault, and constitution III amended (MAJOR, 2.0.0) to allow it. Two routes,
  because the session the operator pictured is too short to reuse (R16) and the thing he pictured —
  scripted web sign-in from a password — is what Google refuses:
  - **Primary, the token route.** The family signs in by hand once to mint a long-lived sign-in
    token for the school account; the vault holds the token, and the runner exchanges it for
    short-lived access tokens and reads Classroom read-only, as a Google first-party client. It is
    not tied to the web session, so it escapes R16.
  - **Fallback, the scripted web sign-in.** The vault holds the password and the second-factor
    seed; a deterministic script signs the headless browser in when the stored session has expired,
    and the runner reads the to-do pages (R18). Documented with its risks; built only if the token
    route fails and the spike shows it works without evasion.
- **The two hard limits, which hold whatever the constitution says**:
  1. Claude never runs a sign-in and never types a credential. The login is a deterministic script
     (Playwright for the web route; a token exchange for the token route) that Claude writes and
     the scheduled job runs. This is a limit of the tool, not of the constitution.
  2. No evasion: no stealth tooling, no debug-port hiding, no fingerprint spoofing, no CAPTCHA
     solving (constitution IV). A sign-in that cannot succeed without any of these stops, and the
     family is told. `puppeteer-extra-plugin-stealth` has been unmaintained since 2023 and is
     reported detected; debug-mode browsers are reported detected. The spec does not plan around
     them.
- **Why the password alone was not enough, and the session alone was not enough**: Google blocks
  sign-in from automated browsers and says the browser must not offer automation features (Google
  Developers Blog, "Guidance to developers affected by our effort to block less secure browsers and
  applications", August 2020; the block started on 2021-01-04; Google account help lists "being
  controlled through software automation" among the reasons it refuses a sign-in). So a scripted
  web sign-in may never work without the evasion limit 2 forbids: the web route is a fallback, and
  its spike (S5) may kill it. A hand-signed session, with no re-login, is ruled out because the
  school session is «como máximo una hora» (operator; R16): the family cannot sign in hourly. The
  token route avoids both the automated sign-in page and the short session, which is why it leads.
- **The token route, in more detail** (research only; untested against the account):
  - The known technique is `gpsoauth`: a one-time human sign-in at Google's embedded-setup page
    yields a master token for the account, from which short-lived access tokens are drawn, as the
    Android first-party clients do (used by `gkeepapi`, Home Assistant). The vault holds the master
    token, not the password.
  - Why it may reach Classroom where our own client did not: the school's blocks recorded in
    `docs/classroom-investigacion.md` (OAuth Playground «Servicio no permitido»; our own OAuth
    client `access_not_configured`) target developer tools and third-party clients. The student's
    account works in the Classroom app on an Android phone (operator, 2026-10-27), believed
    unmanaged, which is the first-party-client case. This is an inference, not a test.
  - Why it may fail: the API block may be at the account-policy level (the admin message was «El
    administrador de tu institución debe revisar»), which a first-party token would hit too; mobile
    management may reject an unmanaged sign-in; the Classroom Android app may call a private
    endpoint, not `classroom.googleapis.com`. Spike S4 settles it with one read-only call.
  - Accepted risks (the family decides in the review): it poses as a Google first-party app, which
    is against Google's terms; the sign-in shows as a new Android device on the account; and the
    stored master token is **account-wide and bypasses the second factor** — read-only is only the
    scope the runner requests from the short-lived tokens it derives, not a property of the stored
    secret. So the stored token is at least as sensitive as the password: if the vault is read (by
    the project's administrators, R17, or in a breach) the exposure is the whole account, not
    read-only Classroom. The family accepts custody of a secret as sensitive as the password.
- **What the vault stores**: the student's secrets in the family's cloud project's secret store
  (R17), encrypted at rest, with versions; the newest is in use. For the token route, the sign-in
  token; for the web route, the stored session plus the password and second-factor seed the family
  seeds (FR-033a). The runner's identity may read them and add versions to the one it mints; the
  family may read and revoke all of them; and — unavoidably — the project's administrators can read
  them too (constitution II, R17), which is why the family picks a project they trust. None of it
  enters the repository, the configuration, a log, an error message or Claude's context. The minted
  secret's renewed value is stored as a new version and the older ones destroyed; the password and
  seed are never rewritten by the runner.
- **How the family seeds it (spike S4/S5)**: `runner session login` on a computer with a screen —
  for the token route, it runs the embedded-setup sign-in and stores the master token; for the web
  route, it starts the runner's Chromium with a fresh profile and no automation attached, the family
  signs in, and it stores the browser's storage state. Not: copying the session out of the family's
  everyday Chrome, which Chrome may bind to that device (R16).
- **Terms of service, the family's decision**: Google's terms (effective 2026-07-30, read
  2026-10-27) forbid automated access that violates a page's machine-readable instructions, naming
  `robots.txt`; `classroom.google.com/robots.txt` (read 2026-10-27) allows only the home pages.
  This applies to today's extension route too; an unattended job is plainly automated access, and
  the token route additionally poses as a first-party app. The account is the student's school
  account, which the school manages. The family accepts or refuses these risks in the review; this
  research does not decide them.

### R16. «Demuestra que eres tú»: how often, from where, and what the run does

- **Observed**: on 2026-10-25 and 2026-10-26, three times at `/u/<n>` (R1); on 2026-10-27, once
  before Classroom opened, in a browser where the school account was already signed in. Two
  lifetimes were seen: one session was gone within about 1 h 20 min, another was still alive after
  2 h 47 min.
- **The extension's own navigation is the likely trigger** (measured 2026-10-27 in another session,
  in the operator's Chrome 156 on macOS, school account at `/u/5`):
  - Two challenges, and each one came on a `navigate` call of the Claude in Chrome extension
    (`tabs.update`): at 18:35:48 (the 9th load) and at 20:22:35 (the 5th load). This run's
    `log.jsonl` records `session_expired` at 19:25:35 UTC, which is 20:25:35 local, three minutes
    after the second one.
  - Loads that the page starts itself met no challenge: about 120 in the extractor's iframe on
    2026-10-26 over 9 minutes, and 11 on 2026-10-27 by `location.assign()` run inside an open
    Classroom tab. The 11 prove little alone: the session was signed in at about 20:30 and kept
    fresh by a run until 20:54. The weight is the two deaths landing on `navigate`, against 120
    page-started loads with none.
  - Ruled out: the pace (the 120); the network (Google traffic goes out through the home router,
    one public address in 3 samples, and the VPN routes only private 10.x addresses); managed
    Chrome policies (none on this Mac).
  - Mechanism, from [anthropics/claude-code#92703](https://github.com/anthropics/claude-code/issues/92703)
    (open, read 2026-10-27): Device Bound Session Credentials renews Google's short-lived
    `__Secure-*PSIDTS` cookies only when a navigation has no initiator (the browser started it), a
    same-site one, or an allow-listed one. `chrome.tabs.create` and `tabs.update` carry the
    extension's origin as initiator, so the renewal is refused and Google sees an expired session.
    The report also says the passkey sheet never appears in a background tab.
  - Not verified: that DBSC is active in this Chrome profile (macOS privacy controls block reading
    its folder; Chrome 156 only makes it possible). The report says the user's own tabs stay signed
    in after a challenge; here the extractor's page-started loads stopped with `session_expired`
    three minutes later, so in this Chrome one challenge ended the session everywhere. The check
    that would settle it is a person's: DevTools → Network on the failing tab, column «Device bound
    sessions», value `InScopeRefreshNotAllowed`.
  - The report's workaround, turning off `chrome://flags/#enable-bound-session-credentials`, removes
    cookie-theft protection for every account in that Chrome. It is not taken while page-started
    navigation works, and it is the operator's call.
  - **Decided**: the skill never opens a Google page with the extension's `navigate` or
    `tabs_create`. It moves inside the Classroom tab the family left open (`location.assign()` run
    in the page) or loads pages in the extractor's iframe. A tab that is not on Classroom is a
    person's job to bring there.
- **What Google documents** (read 2026-10-27):
  - Workspace admin help, "Set session length for Google services": the web session lasts 14 days
    by default; administrators of the Education editions can change it per organisational unit or
    remove the limit; when it ends, the user sees a "Verify it's you" page and must sign in again.
    Native mobile apps and OAuth apps are exempt, not the Classroom web pages.
  - Workspace Updates blog, October 2022: Google re-challenges sessions it judges risky, with
    cookie theft as the example; the signals are not published.
  - Google's blog, 2026-04-09: Chrome now binds a session to a key that cannot leave the device
    (Device Bound Session Credentials, with the TPM on Windows and the Secure Enclave on macOS);
    public on Windows from Chrome 146, macOS "in an upcoming release". A third-party post of
    2026-08-11 reads Chrome 147 on macOS, rolled out gradually and off by default. A bound session
    copied to another machine stops being renewed, so the family signs in in the runner's own
    browser (R15).
- **Why this matters per route**: the token route is not tied to the web session, so R16 barely
  touches it — a master token lives for months (the family refreshes only on revocation). The web
  route lives or dies by it: a ≤1 h session means a scripted sign-in on almost every run, which is
  both the automated-sign-in wall (R15) and a lockout risk on a minor's account.
- **Not measured, so asked of the spikes**:
  1. (S5, web route) How long does the school account's session last, and how often would the
     scripted sign-in have to run? Either the school states its setting, or the family seeds a
     session and the read runs twice a day until «Demuestra que eres tú», over 14 days.
  2. (S4/S5) Does a cloud project's address meet more challenges or sign-in refusals than a home
     address? Google documents no rule about datacenter addresses, but its sign-in refusal is known
     to key on new locations.
  3. (S5, web route) Does the scripted sign-in itself clear, or does Google answer it with "this
     browser may not be secure" or a second factor beyond the stored seed?
  4. (S4, token route) Does the master-token exchange succeed for this account from the runner's
     environment, and does one read-only Classroom call return the student's work?
- **What a stop does (decided)**: a dead or rejected token, or a web-route load that lands on
  `accounts.google.com` the scripted sign-in cannot clear, is `session_expired`; a human challenge
  is `challenge`. The runner evades nothing, applies what it read completely and ends (spec FR-037).
  The family gets one notice until it refreshes the vault: the run records the secret version it
  used, and a later run that stops the same way with the same version logs `stopped` without a new
  notice.
- **Gate**: SC-012 asks that the family refresh the vault by hand at most once every 7 days. The
  token route meets it trivially if S4 proves it. For the web route, if S5 shows the session expires
  so often that a human sign-in is needed more than weekly, or the scripted sign-in cannot clear
  without evasion, the web route is not built. If both routes fail, User Story 7 is not built and
  the family keeps the scheduled task on the Mac (R1) and the guardian email summaries
  (`docs/roadmap.md`, route 2). The runner runs in the operator's cloud project (constitution IX);
  S4/S5 compare its address with a home one only to understand what Google does, not to add a home
  host.

### R17. Where the runner runs

- **Requirement**: no operator Mac, no operator browser; scheduled at the `[schedule]` times; a
  vault with versions (the token, or the session); the data home in the student's Drive (constitution
  II/VII); read-only by scope (token route) or by the browser guard (web route, R18); a notice that
  reaches the family with the Mac off. The host is settled by the constitution, not chosen here:
  spec 005 and IX commit the cloud run to the operator's Google Cloud project. Size: one student,
  about 22 runs a month. The token route is a handful of API calls, seconds each. The web route is
  heavier: two list pages plus one detail per pending item (35 pending on 2026-10-26, spec 003) at
  about 4 s each (R8), so about 300 s with the browser's start — well inside the free tier.
- **Shape and services** (prices read 2026-10-27 on each provider's page): a Cloud Run job started by
  Cloud Scheduler, the secret in Secret Manager, the data home a state folder in the student's Drive
  (R19), all in the operator's Google Cloud project for alfabeta (the one spec 004 and spec 005 use).
  Even the web route's compute (about 6,600 vCPU-seconds and 13,200 GiB-seconds at 1 vCPU / 2 GiB)
  sits under the 240,000 and 450,000 free a month for jobs (200,000 and 375,000 in Tier 2 regions);
  the token route is far less; Scheduler gives 3 jobs free per billing account, then $0.10 a job;
  Secret Manager 6 active versions and 10,000 accesses free. Custody: the project's organisation (the
  operator's work org) administers it, so its administrators can read the secret (constitution II
  names them; the family accepts, or moves to a personal-account project).
- **Rejected hosts**:
  - **Cloudflare Browser Rendering** (Workers Paid $5, 10 browser hours then $0.09/h): a new provider
    would hold a minor's credential (constitution III), and whether its browser announces itself as a
    bot was not verified.
  - **A Claude routine** (Claude Code on a schedule in Anthropic's cloud): against the plan; research
    preview with a 1 h minimum and a daily cap; no writable secret store for the renewed secret; the
    run would sit in a model-driven environment.
  - **GitHub Actions**: the repository is public, and so are its workflow logs — one slip publishes a
    minor's data; scheduled workflows of a public repo also pause after 60 days.
  - **A home device**: constitution IX (2.0.0, set by spec 005) commits the cloud run to the
    operator's Google Cloud project, so a home host is out of scope here; a later spec could name it
    as its own need. The Mac route (R1) stays for the full sync, excluded by the operator for this
    read.
- **Region**: a European region of the project, to keep the student's data in the EU; whether the
  region changes how Google treats the account is part of S4/S5.
- **Notice with the Mac off**: an alert policy of the project's monitoring on the runner job's
  failed executions, with an email notification channel to the family's address, set in the
  project and never in the repository. It needs no new Google scope. `runner read` fails (exit 1)
  only the first time a stop reason appears for a stored session version; a later run that stops
  for the same reason with the same version logs its `stopped` line and ends with 0 (R16,
  `contracts/cli.md`), so the alert fires once. The notice carries the reason and the student's
  opaque `id`, and its documentation field says how to sign in again.
  Rejected: an event in the student's calendar, which holds only facts from Classroom (spec 003);
  an email through the Gmail API, which needs a scope spec 004 does not grant.
- **Custody, for the family to accept or refuse in the review of this amendment**: the cloud project
  lives in an organisation the operator administers for work. Moving the runner to a project owned
  by a family account changes nothing else in this design.

### R18. Read-only as a property of the web route's browser (the token route uses scope)

- **Today (the Mac route)**: the extractor only reads, Claude follows `SKILL.md`, and a `jsdom` test
  checks that the extractor presses nothing (R11). That relies on whoever drives the browser.
- **Token route**: there is no browser and no guard to build — read-only is the scope the access
  token is requested with (FR-032a). The constitution's "read-only by construction" (IV) is met by
  never asking for a write scope.
- **Web route (decided)**: the guard is part of the browser, installed before any page script runs,
  not a discipline the driver follows (constitution IV). Playwright adds it with a capture-phase
  init script and request routing:
  - **presses**: the init script, on every frame before its own scripts load, adds capture-phase
    listeners that `preventDefault()`/`stopImmediatePropagation()` on every `click`, `submit`,
    `keydown` and `pointerdown`, and wraps `HTMLFormElement.submit`/`requestSubmit`, **unless** the
    target is an allowlisted control — a to-do section header or «Ver todo», by label, or the
    scripted sign-in's own fields on a Google sign-in page. So even the page's own `extract.js`, or
    an injected «Entregar», cannot press. Each blocked press is counted.
  - **document loads**, in the page and its iframes, are allowed only on `classroom.google.com` and
    only for `/u/<n>/h`, `/u/<n>/a/not-turned-in/all`, `/u/<n>/a/missing/all`,
    `/u/<n>/c/<class>/a/<item>/details` and `/u/<n>/c/<class>/mc/<item>/details` (the exact FR-034
    set; the other FR-007 pages are the full sync's, not the runner's — FR-038, resolving the
    wider wording); a load to `accounts.google.com` the scripted sign-in cannot clear ends the run
    `session_expired` (R16); any other load is blocked and counted;
  - **requests** to form or quiz hosts (`docs.google.com/forms`, `forms.gle`) and to download hosts
    (`drive.usercontent.google.com`, any `/export`) are blocked and counted;
  - **background requests**: Classroom draws its pages with JavaScript and fetches data with `POST`
    calls, so the method alone cannot tell a read from a write.
- **Not measured, so asked of spike S6**: which background requests do a to-do read and a detail
  read make (method, host, path and call name; never bodies or cookies)? If reads and writes can be
  told apart by call name, the guard allows only the names S6 records and blocks the rest. If they
  cannot, the plan records the weaker guarantee (document loads and presses only) before anything is
  built.
- **The spikes run read-only**: S5 reads the real account behind this guard's parts that do not need
  S6 — the document-load allowlist and zero presses — since the full guard is built only after the
  spikes (C2). S4 (token route) only ever requests a read-only scope.
- **Test**: offline, a local fake server serves the synthetic to-do and detail pages with a planted
  form link, planted «Entregar» and «Marcar como completado» buttons and a planted unknown call, and
  a planted `extract.js`-style press; all are blocked and counted, and none reaches the server.

### R19. One data home per student

- **Decision**: with the runner enabled, the student's data home is a state folder inside the
  alfabeta folder of the student's Drive (constitution II and VII, as spec 005 sets for a cloud run),
  reached through spec 004's Google connection over the Drive REST API with the standard library. It
  is a hidden subfolder of `drive.root` that no mirror receives (VII). The runner works on a local
  copy under `--home` and writes changed files back, so the commands do not change. The Mac holds no
  second copy that can be written.
- **Lock**: `fcntl.flock` does not work over Drive, so the student's lock becomes the lease of R6: a
  lock file in the state folder, created only if absent and renewed by every step with Drive's
  conditional update (the file's version/etag, which also fences a stale writer), and taken over
  after `lock_idle_minutes` with the dead run's `stopped` line. The runner reads by its route, so it
  takes no browser lock on the Mac.
- **A family session on the Mac** for that student (a full sync, a decision, `book place`) takes
  the lease, copies the home down, works on the copy with `--home`, writes it back and releases the
  lease; while it holds the lease, a scheduled run stops with `lock_busy`.
- **Rejected**: two homes with separate outputs, since both need the class links and the statuses
  and would drift apart; a separate Cloud Storage bucket for the state, which the constitution rules
  out for a cloud run (II and VII place the state folder in the student's Drive).
