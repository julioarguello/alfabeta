# alfabeta Constitution

alfabeta gathers the study material of a secondary-school student that today is spread between the
school's digital textbook and Google Classroom. It files it by subject and topic in the student's
folder, which syncs with their cloud, creates a Gemini Notebook notebook per topic, and takes
assignments and exams to a calendar the student and their family share. A family runs it on its own
Mac with the Claude desktop app. The repository is public.

## Core Principles

### I. The student is configuration (NON-NEGOTIABLE)

- No student, school, specific school year or grade level, or account MUST appear in the code, in the tests or in
  logic branches. They exist only in their configuration.
- Adding a second student (a sibling, for example) MUST require only creating another
  configuration, without touching code.
- A student's data and outputs (folder, notebooks, calendar, sync log) MUST stay separate from any
  other student's.

Rationale: the first student is the first *tenant*, not the product.

### II. Three layers that never mix

| Layer | What it is | Where | In the repo? |
|---|---|---|---|
| **Template** | Structure and example values (`changeme`) documenting every key | Repo (`template.*`) | Yes, the only one |
| **Student configuration** | Name, school year, school, subjects, paths, calendar, accounts | Outside the repo or ignored by git | Never |
| **Data and secrets** | Downloads, captures, PDFs, sessions and cookies, tokens, notebook and event ids | Local data folder and the system keychain; for a cloud run a spec names (IX), that project's secret store and one state folder inside the alfabeta folder of the student's Drive | Never |

- The template MUST mirror every real configuration line by line (*template mirroring*): every key
  the code reads MUST be declared in the template, and an undeclared key is an error at start-up,
  not a silent default.
- Secrets (cookies, tokens) MUST live in the system keychain or in the data folder with user-only
  permissions, never in the configuration. A cloud run a spec names (IX) holds its own secrets in
  its project's secret store, readable only by that run. A secret kept on the Mac never leaves it,
  and the cloud's secrets are never stored on the Mac; a secret minted on the Mac for the cloud goes
  straight to the cloud's store without touching the Mac's disk or keychain.
- An automatic guardrail (pre-commit hook and CI test) MUST prevent pushing real names, emails,
  personal paths or ids. The guardrail MUST have cases that prove it fires.

Rationale: in a public repository, whatever the structure does not separate, a slip publishes a
minor's data.

### III. Minors' data (NON-NEGOTIABLE)

- The student is a minor. alfabeta MUST keep only what its function needs: display name, school
  year, subjects, the accounts it operates with, and the student's own study material (what they
  handed in, and the grading and marks the school returns), which goes only to the family's folder.
- Their name, email or any data that identifies them MUST NOT appear in a URL, a log, an error
  message, an issue, a pull request or a commit. Logs use opaque ids.
- Data MUST go only to the services the family itself uses and configures (the student's or the
  family's Google account, their cloud, the operator's Google Cloud project for alfabeta, Claude
  through the app or the operator's API workspace). No other third party.
- Test data MUST be invented. No fixture holds material or data of a real student.
- The student or their family signs in to each platform. No tool MUST type credentials.

Rationale: the school account belongs to a minor and the school manages it; the family answers for
what alfabeta does with it.

### IV. Read-only on the school's platforms (NON-NEGOTIABLE)

- In Google Classroom no tool MUST turn in, comment, mark as done, or open assessments or quizzes.
  Opening a quiz means answering it or following its form; reading the Classroom detail page that
  describes it does not.
- In the digital textbook (Science Bits and any that follow) assessment lessons MUST NOT be opened:
  they spend attempts and can change marks.
- Only what the platform already shows the student with their account is captured, for their study.
  The material belongs to its authors: personal and educational use, no redistribution.
- Access MUST be that of a student browsing: one platform at a time, no bursts. Evasion MUST NOT be
  used: no CAPTCHA solving, proxies or fingerprint spoofing. If a platform answers with a challenge,
  the sync of that source stops and the family is told.
- The Classroom API stays out until the school authorises an OAuth client for alfabeta
  (`docs/classroom-investigacion.md`).

Rationale: one click too many can turn in a blank assignment or spend an exam attempt, and that
cannot be undone.

### V. Idempotent, incremental sync

- Every synced item (material, attachment, assignment, announcement, notebook source, calendar
  event) MUST have a stable identifier derived from its origin, and repeating a sync MUST NOT
  duplicate anything.
- Two consecutive syncs with no change at the origin MUST produce zero writes in the second one
  (except its own log).
- A change at the origin (a moved date, new or edited material) MUST be detected and propagated to
  the folder, the notebook and the calendar.
- Every sync MUST leave a record of what was synced, from where and when.
- alfabeta MUST NOT delete anything belonging to the student or the family because it disappeared
  from the origin: it is marked and the family is told.

### VI. One source, one isolated and tested provider

- Every content origin (a digital textbook, Classroom) MUST be implemented as a provider behind a
  common interface. Science Bits is the first textbook provider; adding another MUST NOT change the
  rest.
- The failure of one provider or one subject MUST NOT abort the others: it is logged, reported, and
  the run continues.
- Every extractor MUST have tests against saved pages with invented data. Tests and CI MUST NOT call
  real platforms.

### VII. Every output is optional and degrades on its own

- The student's master folder on the Mac's disk is the base output. Which cloud receives it is
  configuration. When that cloud is the family's Drive, alfabeta MUST write it through its own
  Google connection and count a file as uploaded only when the cloud confirms it; it MUST NOT rely
  for it on a sync client whose result it cannot read.
- Whatever that Drive holds under a topic folder and the master lacks (what the family adds, such as
  the student's photos of his notes, and what a cloud run writes) MUST be brought back into the
  master, so the mirrors receive it too. This is the only Drive-to-master direction; it never
  applies to a mirror. A cloud run's state folder and its reports live only in Drive: they are not
  part of the master and never reach a mirror.
- alfabeta then brings each configured mirror up to date from the master, one-way. A mirror is the
  Drive folder of an account alfabeta's own connection cannot reach (the school account), mounted on
  the same Mac. It is never read back into the master, and nothing is deleted from it. Its upload
  belongs to the sync client, so alfabeta reports it as written on the Mac, never as confirmed. A
  failed mirror MUST NOT undo or block the master or the other outputs.
- Every output reaches every account the configuration lists for it: the mirrors for the folder,
  and a list of accounts the calendar and each notebook are shared with. alfabeta shares nothing
  with an account the configuration does not list. The Gemini Notebook notebook and the calendar
  are outputs enabled by configuration.
- Gemini Notebook has no public API and is used through `notebooklm-mcp-cli`, which can break. If one
  output fails, the others MUST complete and the failure MUST show in the log.

Rationale: an unofficial tool must not leave the student without their notes.

### VIII. Local time, always `Europe/Madrid`

- Dates from Classroom and the platforms are read as `Europe/Madrid` and stored as absolute instants
  or as dates without time, depending on the origin. Writing to the calendar uses
  `timeZone: "Europe/Madrid"`.
- Code MUST NOT compute offsets by hand, and reminders MUST be tested across daylight-saving
  changes.

### IX. Simplicity

- Everything runs on the family's Mac unless a spec names a need the Mac cannot meet. Such a need
  runs in the operator's Google Cloud project for alfabeta, within its free tier, and the spec
  names what stays on the Mac. The first is spec 005: the student's notes reach the notebook while
  the Mac is off, because the desktop app's scheduled tasks run only while the app is open.
- A new dependency MUST justify in the plan why the standard library or what is already there is
  not enough.

## Technical constraints

- **Environment**: the Claude desktop app with access to the Mac, and a browser with the student's
  session (Chrome with the Claude extension, or the app's built-in browser). Python 3.12 for the
  scripts; JavaScript only inside the browser, to extract pages.
- **Configuration**: the `*-env` pattern with *template mirroring* (`template.*` → the student's
  configuration), or its equivalent in a structured format (TOML, which allows a comment per key,
  YAML or JSON).
- **Storage**: one master folder per student on disk, uploaded to the cloud their configuration
  sets, plus zero or more one-way mirrors with the same content in the student's other accounts.
  Structure shared by every source:
  `<school-year>/<subject>/<YYYYMMDD> - <Tema NN - title | teacher's title | Sin tema>/<source>/`
  (`classroom`, `sciencebits`…). Every topic folder starts with a date, the posting date of its
  first Classroom material, so the student places each topic in time; the date is set when the
  folder is created and never changes, and a folder is found by the part of its name after the
  date. `Tema NN - title` is a topic that matches the textbook; a teacher's topic that is not in
  the textbook carries the teacher's title alone; `Sin tema` holds what Classroom posts with no
  topic. There are no month folders. Every Classroom item starts with its posting date,
  `YYYYMMDD - <title>`.
- **Notebooks**: one per topic, named `<grade level>. <Subject>. Tema NN - <title>` (`<grade level>`
  is the student's grade level, not the school year of the folder). Material that arrives after the
  notebook is created goes into the topic's living Drive files, which are its sources (spec 005);
  only the study pack adds other sources, and never twice.
- **Language**: everything technical is written in English: code, identifiers, CLI, configuration
  keys, data files, documentation, specs, issues, pull requests and commits. What the student and
  the family read is in Spanish: the folder and file names in their folder, the agenda, the summary
  of each sync, Google Tasks and the calendar.

## Development workflow

- Every feature starts as a Spec Kit spec: `/speckit-specify` → `/speckit-clarify` →
  `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze`, fixing and repeating the analysis until
  no critical or high finding is left.
- The spec is approved in a documentation-only pull request. Then the issues for its tasks are
  opened, and each issue goes on its own branch from `main` and in its own pull request.
- Nothing is built before the spec is approved.
- Each spec's plan MUST pass the Constitution Check against these principles. Any exception MUST be
  justified in the plan's complexity table.
- Gates before every pull request: `ruff`, `pyright`, `pytest` and the personal-data guardrail
  (II). A skipped gate MUST be named in the pull request.
- Whatever `/speckit-plan` adds to `CLAUDE.md` is ephemeral: that file is regenerated.

## Governance

- This constitution takes precedence over any other practice in the project.
- Every amendment MUST be made by a pull request that updates this file and bumps the version, with
  its Sync Impact Report in the pull request description (the block in the file is deleted before
  the commit):
  - MAJOR: a principle is removed or redefined.
  - MINOR: a principle or a section is added, or what one allows is materially broadened.
  - PATCH: clarifications.
- Pull request reviews MUST verify compliance. Complexity that departs from IX MUST be justified in
  writing.

**Version**: 1.6.0 | **Ratified**: 2026-10-25 | **Last Amended**: 2026-10-27
