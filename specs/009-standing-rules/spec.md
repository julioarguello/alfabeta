# Feature Specification: Standing rules per subject and per student

**Feature Branch**: `docs/187-spec-009-standing-rules` (spec dir `009-standing-rules`)

**Created**: 2026-11-06

**Status**: Draft

**Input**: Operator's request (translated from Spanish), julioarguello/alfabeta#187: "a prompt of basic rules to load
whenever a subject is dealt with" («un prompt a modo de reglas básicas a cargar siempre que se trate una asignatura»),
and, on preparing an exam, "exam preparation is something that depended on the subject" («la preparación del examen es
algo que dependía de la asignatura»). Asked whether to make one subject's sheets by hand first or generalize first, the
operator chose to generalize first.

## Context and scope

The family gives instructions for one subject in a chat, and the next run has to be told again. Meanwhile
`exam build` sends every subject the same fixed texts, so the sheets of a subject of essays and of a subject of
calculation are asked for in the same words.

### Three levels, which do not mix

| Level | What it holds | Example, invented | Where |
|---|---|---|---|
| **Tool** | What is true of every student | Recognising a task that lacks its statement (spec 008) | The repository's prompts and code |
| **Student** | What is true across this student's subjects | "Classify the statements as well as the problems" | The student's configuration |
| **Subject** | What changes between subjects | "Split the types of problem finely, even if the sheet grows" | The student's configuration |

A rule is a parameter of the student, like a class's title or a calendar's id: the difference is only that it is
heuristic rather than deterministic. So it follows the configuration's layers (constitution II): the repository's
template documents the keys with generic example rules, and each student's own values stay in that student's
configuration. A real student's rule can describe a minor's difficulties, so it never reaches the repository
(constitution III). The tool level already has its place and gets nothing new here.

### What this makes of an exam's preparation

A rule shapes what an existing piece asks for. No new kind of sheet is needed for the case that prompted this
spec, an exam in a subject of calculation:

| What the family wants | Which piece gives it | What this spec adds |
|---|---|---|
| Problems sorted by type, the hardest of each worked | The problems sheet of `exam build` | A subject rule on how finely to split, which prevails over "as few patterns as possible" (FR-034 of spec 002) |
| The forms a statement takes, and how to read each | The problems sheet and the practice sheet | A student rule |
| New problems with their type solutions, numbers checked | The practice sheet of the study pack, whose numbers the skill recomputes (spec 002) | The same rules reach it |
| The family's own statements and solutions as source | The notebook's sources | Nothing: that is spec 008 FR-011, and a rule cannot make a notebook read what it does not hold |

### In this spec

- The keys that hold the rules, and how the family gives them.
- When they load, and which pieces each one reaches.
- What a rule may and may not change.
- How a run shows which rules it relied on, without printing them.

### Out of this spec

- Sync, the agenda and the calendar: they replicate and report, and no rule changes a fact (constitution IV and spec
  003). A rule that would help them is a later spec.
- Transcribing the class notes (spec 005), even though a rule on the notes' languages would help it.
- Building patches (spec 008, julioarguello/alfabeta#184).
- Recomputing the numbers of the exam sheets: they stay the notebook's, an accepted risk (spec 002 FR-036). New numbers
  a family can trust belong to the practice sheet.
- Regenerating a piece when a rule changes.

### Changes elsewhere

| Where | What changes |
|---|---|
| Spec 002 | FR-029's closed list of what fills a prompt gains the text added after filling (FR-003 here). FR-034's "as few patterns as possible" becomes the default a subject rule may change. |
| `skills/study-pack/SKILL.md` | Reads the rules before its prompts and its judgement steps, and may write them on the family's word (FR-004, FR-011). |
| `skills/classroom-sync/SKILL.md`, `skills/sciencebits-a-notebooklm/SKILL.md` | They read the same configuration, and say they ignore the rule keys (FR-013). |
| `config/template.toml` and its contract copy | The new keys, with generic example rules (constitution II). |
| The guardrail | The rule keys count as identifying, so a real rule cannot be committed (FR-009). |

## Clarifications

### Session 2026-11-06

- Q: Where do the rules live: texts of their own, or keys of the configuration? → A: Keys. The operator: a student's
  parameters include deterministic ones such as a class's address and heuristic ones such as a prompt. Generic example
  templates in the repository are welcome, since they hold nothing confidential.
- Q: Does a rule replace a prompt, or add to it? → A: It adds, and prevails where they contradict, within the limits of
  FR-006. The measured wording stays.
- Q: Who writes a rule? → A: The family says it in the chat and the agent writes it after they confirm, or the family
  edits the configuration by hand.
- Q: Which pieces do rules reach? → A: Every study piece whose prompt can take them, not only the exam sheets: the practice
  sheet is where new problems come from. FR-004 lists them, and which pieces take none.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The exam sheets follow the subject and the student (Priority: P1)

The family has said once how a subject's problems should be split and how this student's statements should be
classified. Every `exam build` of that subject asks for its sheets accordingly, with nobody repeating it.

**Why this priority**: it is what the operator asked for, and with no way into the prompts the rest changes nothing.

**Independent Test**: with invented rules for one invented subject and for the student, build that subject's exam and
another subject's, and read the prompts each one sends.

**Acceptance Scenarios**:

1. **Given** a rule for problems in subject A and one for the student, **When** subject A's exam is built, **Then** the
   problems sheet's prompt carries both, the student's first and the subject's after.
2. **Given** the same rules, **When** subject B's exam is built, **Then** its prompts carry the student's rule and not
   subject A's.
3. **Given** a rule for problems only, **When** the exam is built, **Then** the theory sheet's prompt does not carry it.
4. **Given** every rule key empty, **When** the exam is built, **Then** every prompt is byte-identical to what it is today.
5. **Given** a rule that contradicts the fixed text, **When** the prompt is written, **Then** it says that the rule
   prevails there, and the limits of FR-006 stay in force.

---

### User Story 2 - A run says which rules it relied on (Priority: P1)

Reading a run's result, the family knows that the rules loaded and which version of them, without their text showing up
where it should not.

**Why this priority**: a rule left empty by mistake looks exactly like a rule the notebook ignored.

**Independent Test**: build with rules, without rules and after changing one, and read the output and the pack's
record.

**Acceptance Scenarios**:

1. **Given** rules at both levels, **When** a run ends, **Then** its result names each level and kind it used with a
   short fingerprint, and holds no word of the rules.
2. **Given** no rules, **When** a run ends, **Then** its result says that none were used.
3. **Given** a changed rule, **When** the next run ends, **Then** the fingerprint differs, and the earlier sheets are
   neither regenerated nor touched.
4. **Given** a built sheet, **When** the pack's record is read, **Then** it holds the fingerprint of the rules it was
   asked with.

---

### User Story 3 - The study pack follows the same rules (Priority: P2)

The same rules reach what the study-pack skill asks for, above all the practice sheet, so that the problems the student
practises are sorted and worded as the family asked.

**Why this priority**: it gives the new problems with checked solutions, but only needs the skill to read what story 1
already defines.

**Independent Test**: follow the skill on an invented topic with invented rules, and check that the practice sheet's prompt
carries them and that the report names them.

**Acceptance Scenarios**:

1. **Given** a rule for problems, **When** the skill asks for a practice sheet, **Then** its prompt carries the rule, and
   every number in it is still recomputed.
2. **Given** a rule for theory, **When** the skill proposes blocks or asks for a guide, **Then** it follows the rule, and
   the student's scheme still leads the structure (constitution X).
3. **Given** a subject rule that states a standing fact, **When** the skill would otherwise ask the family about it,
   **Then** it does not ask again, and it says which level and kind it relied on. What only the family can settle for this
   topic stays a question: which subtopics an exam covers, and a question on the notes.

---

### User Story 4 - The family gives a rule once (Priority: P2)

The family says a rule in the chat. It is written down in the family's words, read back, and from then on it loads.

**Why this priority**: a rule stuck in a chat is the problem this spec exists for, but the family can edit the
configuration by hand until this works.

**Independent Test**: state an invented rule in a session, confirm it, and check that it is in the student's configuration,
that nothing of it reached the repository, and that a later run uses it.

**Acceptance Scenarios**:

1. **Given** a rule said in the chat, **When** the agent proposes it, **Then** it shows the text, the level and the
   kind, and writes nothing until the family confirms.
2. **Given** a key the family edited by hand, **When** a run loads it, **Then** it is used as it stands.
3. **Given** a mistyped rule key, **When** the configuration is checked, **Then** it is reported, by key and never by
   content, as any other key is.

### Edge Cases

- A rule that holds braces: it reaches the prompt as written, and is never read for placeholders.
- A rule key missing from a student's configuration, or still holding `changeme`: the configuration check stops the run, as
  with any other key. Empty is the valid way to say "no rule".
- Rules too long for the prompt: the run refuses, says which sheet and by how much, and sends nothing. They are never cut in
  silence.
- A rule of spaces only: the same as an empty one.
- A rule holding quotes or backslashes, as formulas do: only a literal string keeps it as written. A basic string either stops
  every command reading the file or silently changes the text (`\frac` becomes a form feed), so the template's examples and the
  agent's writes use literal strings, and a write is checked on a copy before it replaces the file (FR-011).
- A guide 0: its prompt says to copy a block word for word, so added text would be printed to every viewer. It takes none, and
  the rules shape the plan the agent writes.
- The notebook keeps a piece's prompt with the piece, and it may be readable by the accounts the notebook is shared with: see
  FR-009.
- The study guide `exam build` may regenerate: a built-in format that takes no prompt, so it carries no rules (spec 002
  FR-033). The run does not claim otherwise.
- A rule the notebook does not obey: alfabeta cannot tell from the prompt, so the first real run is checked by eye (SC-005).
- A rule asking for new numbers on an exam sheet: nothing recomputes those (spec 002 FR-036), so the proposal in story 4
  says so and points to the practice sheet.
- A rule saying part of a topic is not in the exam: FR-006 applies; it needs a source, and the rule alone excludes nothing.
- An exam over several topics: each sheet carries the same rules.
- The second student: their rules are separate, and one student's never load for another (constitution I).

## Requirements *(mandatory)*

### Functional Requirements

**Where they live**

- **FR-001**: Rules MUST be keys of the student's configuration: three at the student's level and three in each subject,
  one each for **problems**, **theory** and **both**. Each MUST be a text, and empty MUST be valid and mean no rule
  (constitution VII).
- **FR-002**: The repository's template MUST declare the keys with `changeme` values and generic, invented example rules in
  its comments, among them a subject of calculation and a subject of languages (constitution II). No example MUST describe
  a real student. A missing, extra or unset rule key MUST be reported like any other key, by key and never by content.

**When they load**

- **FR-003**: `exam build` MUST add to the prompt of each sheet the rules that speak to it, the student's first and the
  subject's after, each time it runs. The problems sheet takes **both** and **problems**, the theory sheet **both** and
  **theory**, and start notes none. With every key empty, the prompt sent MUST stay byte-identical to today's.
- **FR-004**: The study-pack skill MUST read the same keys before its prompts and its judgement steps, adding **both** and
  **problems** to the practice sheet, the quiz and the parent guide, **both** and **theory** to the summary and to the blocks
  and plan it works out itself, and **both** alone to the flashcards and the glossary. A video's focus takes only what fits, as a
  judgement of the agent, reported as such. Guide 0, the built-in study guide and the tutor chat take no added text: the chat talks
  with the student, and a question could draw a rule out of it. A rule MUST
  NOT be copied into `bloques.md` or any file of the topic's folder.
- **FR-005**: Each run reads the keys as they stand. Nothing MUST copy a rule to another place to go stale.

**What a rule may change**

- **FR-006**: The added text MUST say that a rule prevails where it contradicts the fixed prompt, and a subject's rule over
  a student's, and it MUST itself name each exception, since the notebook reads nothing else: what is in the exam and following
  its points (the announcement, the exclusions that need a source, the family's named topics), the corrections already checked
  (spec 002 FR-046), the student's schemes leading the structure and the wording (constitution X), checking every number, showing
  where a fact comes from, using only the problems a prompt says to use, blaming or naming no one, and the sentences and titles a
  prompt asks for in quotation marks (printing breaks the page on «Soluciones»). The skill applies the same limits to its
  judgement steps.
- **FR-007**: The added text MUST tell the notebook to apply the rules without quoting or mentioning them, so that no sheet
  reads "this student has trouble with…" to the student.

**What a run shows**

- **FR-008**: The result of `exam build` and the pack's record of each sheet MUST name the levels and kinds used, with a short
  fingerprint of the added text, or say that none were used. The skill's report MUST name the levels and kinds it used.
  None of them MUST hold a word of the rules, and the skill MUST NOT quote a piece's status output, which can hold its prompt.
- **FR-009**: A rule's text MUST NOT reach a log, a message, an issue, a pull request or a commit, and the guardrail MUST catch a
  configured rule in the repository, line by line. It MAY go to the services the family uses for the study material: the notebook
  owner's account and Claude (constitution III). The notebook keeps the prompt with the piece, so the accounts the notebook is
  shared with may be able to read it: the template warns of this, and no rule describing a difficulty is written until the first
  real run has checked what a viewer sees, on a report and on a quiz (SC-005).
- **FR-010**: Rules too long for a prompt MUST stop `exam build` before anything is asked of the notebook, saying which sheet
  and by how much. The skill applies the same limit, and tells the family instead of cutting.

**Who writes them**

- **FR-011**: The family MAY edit a rule key by hand. An agent MAY write one only after showing the family its text, level
  and kind and hearing their confirmation, and only that key, as a literal string: it writes a copy, checks that the copy parses,
  that every other value is unchanged and that the configuration check passes, and only then replaces the file. On any failure the
  original stays. The one other write is bringing the empty keys to an existing configuration, once, by the same route except that
  the configuration check runs after the code arrives, since older code refuses the new keys (research R9).

**What rules never do**

- **FR-012**: A change of rules MUST NOT regenerate, retitle or delete any piece.
- **FR-013**: No command but `exam build` MUST use the rules; `config check` validates them and the guardrail compares them, and
  neither prints them. A skill that holds the configuration for other work (sync, the
  book's capture) MUST ignore them: no rule shapes a classification, a date or an agenda.

### Key Entities

- **Rule**: the value of one key: one level (student or subject), one kind (problems, theory or both). The family's words,
  never validated for meaning.
- **Fingerprint**: a short value computed from the text a sheet's prompt gained, which tells two versions apart and reveals
  nothing of them.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With every rule key empty, in a fixture, each prompt `exam build` sends is byte-identical to the one sent before
  this feature, for all the prompts of an exam with and without an announcement; since spec 002 FR-052 (#229), that
  prompt ends with the reading format, which comes before any rules.
- **SC-002**: In a fixture with rules for two subjects, no prompt of one carries a word of the other's, and no theory sheet's
  prompt carries a problems rule.
- **SC-003**: The template's examples are invented, and in a fixture no word of a rule reaches any run's output, record or log.
- **SC-004**: A family that has stated a rule does not need to repeat it: over two runs of a subject, the second needs no
  instruction from the chat to carry it.
- **SC-005**: On the first real run with rules, reading the printed sheets shows each rule applied and none quoted, and a viewer
  account's view of the notebook is checked for the prompt, on a sheet and on a quiz made with an invented rule. Until that run the added text is unmeasured, like the prompts around
  it, and what it found is recorded with no personal data.

## Assumptions

- Rules are written in the prompts' language, Spanish, as the family speaks it; nothing translates them.
- The prompt length the notebook accepts has not been measured; the plan sets a cautious limit, and the first real run tests it.
- A student's configuration gains the new keys when the code that reads them arrives, as with any new key: the configuration
  check stops a run otherwise, so the two change together.

## Dependencies

- Spec 002: the exam sheets and the study pack's pieces, and FR-036's accepted risk.
- Spec 007: an exam with nothing announced takes the same rules.
- Spec 008: FR-011, for study material to read the family's statements and solutions. Without it a notebook holds them only
  if someone added them as sources.
- Constitution I, II, III and X. Rules are student configuration under II, so no amendment is needed.
