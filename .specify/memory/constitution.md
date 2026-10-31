# alfabeta Constitution

alfabeta gathers the study material of a secondary-school student that today is spread between the
school's digital textbook and Google Classroom. It files it by subject and topic in the student's
folder, which syncs with their cloud, creates a Gemini Notebook notebook per topic, and takes
assignments and exams to a calendar the student and their family share. A family runs it on its own
Mac with the Claude desktop app, and with a launchd agent for the few commands that need no app
(Technical constraints); reading Classroom with nobody present can also run as a job in the
family's own cloud project (IX). The repository is public.

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
| **Data and secrets** | Downloads, captures, PDFs, sessions and cookies, tokens, notebook and event ids | Local data folder and the system keychain; for a cloud run a spec names (IX), that project's secret store (the vault of III) and one state folder inside the alfabeta folder of the student's Drive | Never |

- The template MUST mirror every real configuration line by line (*template mirroring*): every key
  the code reads MUST be declared in the template, and an undeclared key is an error at start-up,
  not a silent default.
- Secrets (cookies, tokens, and the stored credential or sign-in token of III) MUST live in the
  system keychain or in the data folder with user-only permissions, never in the configuration. A
  cloud run a spec names (IX) holds its own secrets in its project's secret store (the vault of III),
  readable by that run, the family, and — unavoidably — the administrators of that project; the
  family therefore runs it in a project they administer or whose administrators they trust, and the
  plan names the project and the organisation whose administrators can read it. A secret kept on the
  Mac never leaves it, and the cloud's secrets are never stored on the Mac; a secret minted on the
  Mac for the cloud goes straight to the cloud's store without touching the Mac's disk or keychain.
  The one exception is an OAuth client file downloaded from Google, read once by the command that
  links an account and deleted right after, the same way spec 004 loads the Mac's own client.
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
- The student or their family performs the first sign-in that authorises alfabeta for an account; no
  tool decides on its own to grant itself access. A tool MAY then sign in again on the student's
  behalf, with nobody present, only under all of these conditions:
  - it uses a credential or token the family stored, for that one account, in a vault (II);
  - the vault holds as little as the route needs: a sign-in token in preference to the password, and
    the password with its second-factor seed only for the documented fallback route. The preference
    for the token rests on its being revocable on its own and not reused on other services, not on
    its being narrower in power: a first-party sign-in token can be account-wide and bypass the
    second factor, so the stored secret is at least as sensitive as the password. Read-only is the
    scope alfabeta's code requests from the short-lived tokens it derives, not a property of the
    stored secret. Whoever can read the vault (II names them) can reach the whole account, so the
    family accepts custody of a secret as sensitive as the password;
  - a deterministic script that alfabeta's own code runs does the sign-in. Claude writes that
    script but MUST NOT itself type a credential or run the login by hand;
  - no evasion is used (IV): if a sign-in cannot succeed without defeating a bot or human check, it
    stops and the family is told, instead of trying to get past it;
  - it reads only the student's own material.
  The family can revoke it at any time by changing the credential or signing the account out, and
  the run stops when the stored secret stops working.

Rationale: the school account belongs to a minor and the school manages it; the family answers for
what alfabeta does with it. Storing a credential for that account is a real risk — a lockout, a
breach of the platform's terms — so it is the minimum, for the student's own account, used without
evasion, and the family accepts that risk in the amendment that turns the route on. This principle
changed in 2.0.0: before it, no tool ever typed credentials.

### IV. Read-only on the school's platforms (NON-NEGOTIABLE)

- In Google Classroom no tool MUST turn in, comment, mark as done, or open assessments or quizzes.
  Opening a quiz means answering it or following its form; reading the Classroom detail page that
  describes it does not.
- In the digital textbook (Science Bits and any that follow) assessment lessons MUST NOT be opened:
  they spend attempts and can change marks.
- Only what the platform already shows the student with their account is captured, for their study.
  The material belongs to its authors: personal and educational use, no redistribution.
- Access MUST be that of a student browsing: one platform at a time, no bursts. Evasion MUST NOT be
  used: no CAPTCHA solving, proxies, fingerprint spoofing or stealth tooling. If a platform answers
  with a challenge that a human would have to clear — a CAPTCHA, an "unusual traffic" page, a check
  that the browser is not automated — the sync of that source stops and the family is told; nothing
  is typed to get past it. The scheduled sign-in that III permits is the exception, and only while
  it needs none of this evasion.
- A run with nobody present MUST enforce read-only by construction, not by trusting the code that
  drives it: a browser that blocks every page load and press outside an allowlist before it reaches
  the platform, or a connection asked for with read-only scope only.
- No OAuth client of alfabeta's own is used against the Classroom API for a school account the
  school has not authorised (`docs/classroom-investigacion.md`). The one exception is the
  first-party token route that III permits for a run with nobody present: it reads the API read-only
  as a first-party client with a token the family seeded, and is built only once a spike proves it
  reaches the account. Its added risk (posing as a first-party app, against the platform's terms)
  is the family's to accept, with the rest of III's conditions.

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
- A cloud run that only reads a platform (spec 001's Classroom read) writes no replicas and no topic
  material: it writes only what it derives — the agenda (regenerated from the shared state by any Mac
  run, so a mirror still receives it through the master) and the calendar — straight through that
  connection and confirmed the same way.
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
  names what stays on the Mac. The first is spec 005: the student's notes are transcribed into the
  topic's living file in Drive while the Mac is off, which nothing on the Mac can do; the notebook
  takes that file when the Mac's own refresh reads it. The
  second is spec 001's User Story 7: reading Classroom with nobody present — measured 2026-10-27,
  when a read missed two assignments posted that morning because it needed the Mac — with
  attachments and replicas staying on the Mac.
- A new dependency MUST justify in the plan why the standard library or what is already there is
  not enough.

### X. The student's own schemes lead the study material

- When the student's class notes hold a scheme — a tree, a concept map, a chain of arrows, a
  labelled drawing — the study material of that topic MUST be built on it: its blocks, their order
  and their names follow the scheme's branches, in the student's own words. The textbook and
  Classroom are mapped onto the scheme, never the scheme onto them.
- Every piece the student studies from (video, guide, summary, practice, quiz, flashcards, the
  printed topic) MUST say which branch of the scheme it covers, so the student can always find it on
  his own page. The mind map, made from the sources before the blocks exist, is mapped branch by
  branch to them in the topic's blocks file instead.
- What the sources teach and the scheme lacks is hung from the nearest branch or listed apart, and
  never reorders the scheme. A branch no source explains is a question for the family, not a gap
  the textbook's structure fills.
- Where the notes hold no scheme, the order of the sources (notes, then Classroom, then textbook)
  sets the structure as before.
- The scheme leads the structure and the wording, not the facts. A fact in the notes that the
  textbook or the teacher's material contradicts — or, where they say nothing on it, a named
  external reference — MUST be corrected in the material and the student told that his page says
  otherwise; a fact the notes insist on (repeated, boxed, underlined, marked as important, or in the
  teacher's own words) is kept and becomes a question for the family. A source's silence is not a contradiction.

Rationale: the operator observed with the first physics-and-chemistry topic that material laid out
in the textbook's order left the student lost, while his notes carried schemes the material did not
follow (2026-10-29). The last bullet came after a summary and a flashcard repeated a fact the notes
had wrong while the practice sheet of the same notebook corrected it (2026-10-31).

## Technical constraints

- **Environment**: the Claude desktop app with access to the Mac, and a browser with the student's
  session (Chrome with the Claude extension, or the app's built-in browser). For reading Classroom
  with nobody present (IX), a scheduled job of the operator's Google Cloud project for alfabeta that
  reads either as a first-party client with a token, or with a headless browser whose session the
  family started by hand — using a secret in the vault (II). On the Mac, alfabeta's own commands may
  also run from a launchd agent in the family's user session, with no app open, when a spec names
  the need (spec 005: the notebook owner's refresh, FR-018); such an agent uses the secrets already
  on the Mac and adds none. Python 3.12 for the scripts; JavaScript only inside the browser, to
  extract pages.
- **Configuration**: the `*-env` pattern with *template mirroring* (`template.*` → the student's
  configuration), or its equivalent in a structured format (TOML, which allows a comment per key,
  YAML or JSON).
- **Storage**: one master folder per student on disk, uploaded to the cloud their configuration
  sets, plus zero or more one-way mirrors with the same content in the student's other accounts.
  Structure shared by every source:
  `<school-year>/<subject>/<YYYYMMDD> - <Tema NN[X] - title | teacher's title | No topic>/<folder>/`.
  Every topic folder starts with a date, the posting date of its first Classroom material, so the
  student places each topic in time; the date is set when the folder is created and never changes,
  and a folder is found by the part of its name after the date. `Tema NN - title` is a topic that
  matches the textbook. A textbook topic too long for one study pack is split along its lessons
  into **subtopics**, and each subtopic is a topic in its own right — its own folder, notebook and
  pack: `Tema NNX - title`, with `X` a letter (`A`, `B`, `C`…) in the order of its lessons and the
  title of the lessons it holds (spec 002). A teacher's topic that is not in the textbook carries
  the teacher's title alone; `No topic` holds what Classroom posts with no topic. There are no
  month folders. alfabeta
  writes none of its own files at a topic folder's root, only inside its folders, each named for
  where its content comes from: `notes` (the student's class notes and their living file),
  `classroom` (the teacher's material and its living file), the textbook's provider (`sciencebits`)
  and `notebook` (everything else the topic's notebook generates); `exam` is named for its purpose
  and holds the sheets for the day before an exam. `exam` carries no date: the date goes in each
  file's name. What VII brings back from Drive keeps the place it had there. Every Classroom item
  starts with its posting date, `YYYYMMDD - <title>`, and what the student turned in for an
  assignment goes in its `submission` folder.
- **Notebooks**: one per topic, a subtopic included, named `<grade level>. <Subject>. Tema NN[X] -
  <title>` (`<grade level>` is the student's grade level, not the school year of the folder). Material that arrives after the
  notebook is created goes into the topic's living Drive files, which are its sources (spec 005);
  only the study pack adds other sources, and never twice.
- **Language**: everything technical is written in English: code, identifiers, CLI, configuration
  keys, data files, documentation, specs, issues, pull requests and commits. A folder name the code
  decides is technical too, so it is in English (`notes`, `submission`, `No topic`…): a constant
  in the code, not configuration. What the student and the family read is in Spanish: the names
  of the files alfabeta writes in their folder, the agenda, the summary of each sync, Google Tasks
  and the calendar. A name alfabeta takes from elsewhere keeps its own language: a topic's title
  (the teacher's or the textbook's), a Classroom item's title, and a subject's folder (the
  family's configuration).

## Development workflow

- Every feature starts as a Spec Kit spec: `/speckit-specify` → `/speckit-clarify` →
  `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze`, fixing and repeating the analysis until
  no critical or high finding is left.
- The spec is approved in a documentation-only pull request. Then the issues for its tasks are
  opened, and each issue goes on its own branch from `main` and in its own pull request.
- Nothing is built before the spec is approved.
- **Approval is delegated to the agent.** The operator does not review pull requests. The agent
  that opened a pull request records its approval in it and squash-merges it when, and only when:
  - every gate is green in CI (a skipped gate is not green);
  - for a spec, `/speckit-analyze` run by an agent that did not write it reports no critical or
    high finding;
  - for anything else, code, documentation or an amendment to this constitution, a review by an
    agent that did not write it reports no blocking finding.

  After merging, the agent checks that the change reached `main` by its content, not by the
  merged badge. The pull request records what was verified and what was not.
- These wait for the operator, and no agent merges them without the operator's explicit request:
  - a change that weakens a NON-NEGOTIABLE principle (I, III, IV) or the personal-data guardrail;
  - an amendment that removes or loosens a merge condition above, this list, or Governance,
    including a CI change that removes or skips a gate;
  - a pull request that no agent of the operator opened (an outside contributor, an automated
    dependency update).

  Whether a change falls in this list is decided by the independent reviewer, not by the agent
  that opened it. The operator's request is his own words, in the pull request or in the session
  that prepared it; the pull request quotes them with their date before the agent merges. The agent
  acts through the operator's GitHub account, so that quote is the agent's record, not proof.
- A merged change that breaks something is fixed forward in a new pull request, never by rewriting
  `main`, except to purge personal data or a secret from the history (II, III), which only the
  operator does.
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
- Each pull request's review, by an agent that did not write the change (Development workflow),
  MUST verify compliance with this constitution. Complexity that departs from IX MUST be justified
  in writing. The operator may stop, revert or take back any approval at any time.

**Version**: 2.5.0 | **Ratified**: 2026-10-25 | **Last Amended**: 2026-10-31
