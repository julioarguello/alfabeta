---
name: classroom-sync
description: Copies the teacher's material from Google Classroom into the student's Drive, one folder per subject and topic, reading only what the student already sees. Use with «sincroniza alfabeta para <alumno>» (sync alfabeta for <student>), «sincroniza alfabeta para <alumno>, solo <asignatura>» (only one subject) or «trae lo nuevo de Classroom» (bring what is new from Classroom).
---

# Classroom sync — the teacher's material in its topic folder

Part of the [alfabeta](https://github.com/julioarguello/alfabeta) project, spec 001 (User Stories 1 and 2).
What each piece does and why is in [the spec](../../specs/001-classroom-sync/spec.md) and its
[research](../../specs/001-classroom-sync/research.md); the commands are in
[contracts/cli.md](../../specs/001-classroom-sync/contracts/cli.md). This file says what to run.

## Configuration

`~/.alfabeta/<student>/config.toml` (template: the repo's `config/template.toml`):

| Key | Used for |
|---|---|
| `tools.repository` | the clone every command runs from |
| `classroom.account` | the school account, compared inside the page; never printed, never in a URL |
| `downloads.folder` | where Chrome leaves captures and attachments |
| `sync.lock_idle_minutes` | how long the run may go without renewing its lock |
| `subjects` | the short name a class is linked to, and whether it has a book |

Every command runs on the Mac through Bash, never in the app's virtual machine. Each tool call is a
new shell, so the run id goes inline every time:

```bash
ALFABETA_RUN=<run> uv run --project <tools.repository> python -m alfabeta <command> --student <student>
```

Below, `alfabeta <command>` stands for that line.

## Steps

1. **Open the run.** `alfabeta config check`, then `alfabeta lock take --mode interactive`; keep its
   `run`. `lock_busy` means another run holds the student: stop and say so.
2. **Find the tab.** With `tabs_context`, find the Classroom tab the family left open. **Never open
   or move a Google page with the extension's `navigate` or `tabs_create`**: in this Chrome it ends
   the school session (research R16). A tab that is not on Classroom, or is on Google's sign-in, is a
   person's job: ask the family to sign in there and leave it on the home page. Read `/u/<n>` from
   `location.pathname` and check the account without writing the address into the call: hash
   `classroom.account` (lower case, SHA-256) on the Mac and let a script in the page compare it with
   the hash of each address in the page's `aria-label`s, returning only true or false. If it does
   not match, try the next `<n>` with `location.assign("/u/<n>/h")` run in the page. A page already
   on screen proves nothing about the session: a tab left overnight still shows last night's page.
   The first load in step 4 is the proof. Ask the family to keep that Chrome window on screen until the
   capture ends: not minimised, not covered by another window, and that tab the active one in it.
   Hidden, its pages hardly load (see «Measured»); the extractor then waits instead of loading.
3. **Inject the extractor.** Read `<tools.repository>/skills/classroom-sync/scripts/extract.js` and
   pass its whole source to `javascript_tool` in that tab. It loads every page in a hidden iframe and
   never moves the tab; inject again only if the tab itself reloaded.
4. **Capture the class list.** Load «Trabajo de clase» of any class with `X.iframeLoader(window)`
   first: a `SessionExpired` there means the family must sign in again.
   ```js
   const X = alfabetaExtract, run = "<run>", now = () => new Date();
   const classes = X.captureClasses({ run, doc: document, path: location.pathname, now });
   X.save(classes, window); ({ type: classes.type, reason: classes.reason, n: classes.classes?.length })
   ```
   A `stop` (`challenge`, `unexpected_ui`) ends the run: `alfabeta log stop --reason <reason>`
   (it writes the line and releases the lock; it sends nothing), and tell the family what to do.
   Otherwise `alfabeta downloads collect --wait 10` and `alfabeta plan`.
5. **Link the classes.** For each `class_link` in `plan.json`'s `pending_decisions`, propose the
   subject whose `classroom_class` names that class — the family wrote it for this — with the reason
   and a confidence, in one file:
   ```json
   [{"type": "class_link", "origin": "<class id>", "target": {"subject": "<short name>"},
     "reason": "<why>", "confidence": "high"}]
   ```
   `alfabeta decisions propose --file <file>`, then ask the family and record each answer with
   `alfabeta decisions confirm --type class_link --origin <class id>` (add `--reject` for a class
   that is not a subject). A hidden class is never linked; the summary lists it.
6. **Capture each linked class** (or only the subject asked for), one at a time, in the background:
   ```js
   window.__ab = { status: "running" };
   X.captureClass({ run, classId: "<class id>", title: "<title>", account: classes.account_index,
     load: X.iframeLoader(window), sleep: (ms) => new Promise((r) => setTimeout(r, ms)), now, random: Math.random })
     .then((c) => { X.save(c, window); window.__ab = { status: "done", type: c.type, reason: c.reason, complete: c.complete }; })
     .catch((e) => { window.__ab = { status: "error", error: String(e) }; });
   ```
   Poll in calls of at most 36 s — the tool call dies at 45 s:
   `for (let i = 0; i < 9 && window.__ab.status === "running"; i++) await new Promise((r) => setTimeout(r, 4000)); window.__ab`.
   Then `alfabeta downloads collect --wait 10`, which also renews the lock. A `stop` midway
   (`session_expired`, `challenge`, `unexpected_ui`) is saved and collected like a capture: capture
   no more classes and go on to step 7 with what you have; the run ends `partial` with that reason.
   `complete: false` means some page did not load; the next run reads it again.
7. **Match the topics.** `alfabeta plan` (with `--subject <short name>` when the family asked for one).
   For each `topic_match` pending, propose the book topic it covers, copying the entry's `title` and
   `book_topics` into the proposal, or a rejected match reopens on every run:
   ```json
   [{"type": "topic_match", "origin": "<topic id>", "target": {"topic": "Tema NN - <title>"},
     "origin_title": "<title from plan.json>", "book_topics": ["<from plan.json>"],
     "reason": "<why>", "confidence": "medium"}]
   ```
   Ask the family, then `decisions confirm --type topic_match --origin <topic id>` or, for a topic
   that belongs to no book topic, the same with `--reject`: it keeps its own
   `<YYYYMMDD> - <teacher's title>` folder. Then `alfabeta plan` again.
8. **Judge the exam candidates.** Each `exam_candidate` in `pending_decisions` is an announcement whose
   `text`, or a material whose `title` or `text`, names a test. Read it in its class's `language` and decide how many exams
   it announces. For each one propose a `detected_exam` whose origin is `<item>#exam-<k>`, with `k` =
   1, 2… in the order the text gives them. Resolve its date against `posted_at`: `YYYY-MM-DD`, or
   `YYYY-MM-DDTHH:MM` when the text gives the time, or `""` when it cannot be resolved. If the text
   announces no exam, propose one `dismissed_candidate` whose origin is `<item>`. Copy `origin_hash`
   from the entry into every proposal: without it `propose` exits 1 and records none of the file;
   with another text's hash the candidate comes back on the next plan. Two candidates, `<item-a>`
   announcing an exam and `<item-b>` announcing none:
   ```json
   [{"type": "detected_exam", "origin": "<item-a>#exam-1", "target": {"date": "2026-11-05",
     "reason": "<the words that give the date>"}, "reason": "<why it is an exam>", "confidence": "high",
     "origin_hash": "<from plan.json>"},
    {"type": "dismissed_candidate", "origin": "<item-b>", "target": {}, "reason": "<why it is no exam>",
     "confidence": "medium", "origin_hash": "<from plan.json>"}]
   ```
   `alfabeta decisions propose --file <file>`. A detected exam counts from that moment, unconfirmed:
   the next `apply` puts it in the agenda, marked «detectado». In an interactive run, tell the family
   each one with its date and each candidate you dismissed; what they say
   is a correction, `alfabeta decisions correct --origin <item>#exam-<k>` with `--date YYYY-MM-DD`,
   `--category <category>` or, when it is no exam, `--discard`; a dismissal they disagree with is
   `alfabeta decisions confirm --type dismissed_candidate --origin <item> --reject`. In a scheduled run ask nothing: they
   stay as detected. Then `alfabeta plan` again.
9. **Download the attachments.** `plan.json`'s `downloads` hold `url`, `expected_name` and `batch`.
   For each batch, starting at 0, load every `url` in a hidden iframe created in the Classroom tab,
   2–3 s apart; they arrive with no dialog (research R4). Then `alfabeta downloads collect --wait 30`
   before the next batch: a batch is how two files with the same name do not overwrite each other.
   A file that never arrives (a large video stops at Drive's virus-scan notice) is left; `apply`
   notes it as «no traído» with its link.
10. **Before the first apply of a subject**, look at its topic folders in Drive. A `classroom/` folder
    made before alfabeta (an earlier import, a hand copy) would sit beside the run's own files with
    other names. With the family's agreement, move it to
    `~/.alfabeta/<student>/data/quarantine/<YYYYMMDD>-<what>/`; never delete it. Leave
    `Classroom · <topic>.pdf` where it is: it is `notebook setup`'s (spec 005) and a source of the
    topic's notebook; quarantine only what is beside it.
11. **Apply.** `alfabeta apply` (with the same `--subject`). `apply` finds what was collected through
    the current `plan.json`, so when subjects go one at a time, plan, download and apply each before
    planning the next. On a subject's first run, apply once
    more: it must report `added` 0 and `changed` 0. Every apply also rewrites the school year's
    `agenda.md` and `agenda.json` if they changed; after a correction alone, `alfabeta agenda`, inside
    a run (`lock take`), does the same without applying. Then `alfabeta lock release`.
12. **Report** to the family, in Spanish: what was placed and where, what waits for them (unlinked
    classes, topics to confirm, attachments not fetched, each with its link), the exams detected
    with their dates, and why a run was `partial`. The agenda is `<school year>/agenda.md`.

## Measured on real runs

Measured 2026-10-27 on one real class of the school account; details in research R3 and R16.

| Behaviour | Consequence |
|---|---|
| One class capture took 75 s | poll in the background (step 6) |
| A page's iframe `load` event came more than 30 s after its content | the extractor polls readiness instead |
| An attachment's label reads «Archivo adjunto: <tipo>: <name>» | the extractor keeps only the name |
| Both «Demuestra que eres tú» challenges came on the extension's `navigate`; about 120 page-started loads met none | step 2 |
| The second `apply` over the same captures changed nothing | step 11 is the check |
| An empty «Trabajo de clase» shows «Aún no hay tareas…» and an empty stream «Aquí se mostrarán novedades…», with no rows (2026-10-28) | the extractor takes both as loaded |
| Drive keeps a double space the page collapses, and a Google Doc's export can arrive with a leading «_» (2026-10-28) | `downloads collect` falls back to comparing letters and digits |
| The school session lasted between 54 and 83 minutes after sign-in (2026-10-28) | sign-in again is the family's; a sync that runs longer stops `partial` |
| Eleven classes took 14 minutes; the session was still alive 50 minutes after the family signed in (2026-10-28) | a whole sync fits in one sign-in |
| On the stream, «Fecha de creación: » and its date are two text nodes, and every post hides a teacher-only notice longer than any line of its text (2026-10-28) | the extractor reads the label's whole element and the post's own text block |
| With the Classroom tab hidden (its window covered), a class took 4–12 minutes and came back incomplete, and later classes timed out until the session expired; on screen, a page loaded in about 10 s and a class in 12–123 s (2026-10-28) | step 2 asks for the window on screen; the loader waits while the tab is hidden |
| A family may have two windows with the same tab group name; only the tab `tabs_context` returns is the one being read (2026-10-28) | to point the family at it, change that tab's `document.title` for the run and restore it after |
| An image posted on the stream was labelled «Archivo adjunto: <name>», with no type (2026-10-28) | the extractor strips the prefix with or without the type |

## Never

- Turn in, comment, mark done, or open a quiz or a form; never click the «Tu trabajo» panel.
- Open or move a Google page with the extension's `navigate` or `tabs_create`.
- Type a password, or sign in for the family.
- Delete anything in Drive or in `data/`: what has to go is quarantined.
- Put the student's name, email or any id into the repository, a URL, a log, an issue or a PR.
