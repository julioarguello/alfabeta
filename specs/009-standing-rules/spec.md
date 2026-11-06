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
| **Subject** | What changes between subjects | "Split the types of problem finely, even at the cost of extra exercises" | The student's configuration |

The student and subject levels are one student's facts, often about a minor's difficulties, so they are never
repository content (constitution I, II and III). The tool level already has its place and gets nothing new here.

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

- Where the rules live and how the family gives them.
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
| Spec 002 | The exam sheets' prompts carry the rules (FR-003 here). FR-034's "as few patterns as possible" becomes the default a subject rule may change. |
| `skills/study-pack/SKILL.md` | Reads the rules before its prompts and its judgement steps, and may write them on the family's word (FR-002, FR-004). |
| `config/template.toml` and its companion | Documents the rules, with `changeme` examples (constitution II). |
| Spec 008, Out of this spec | Its "per-subject prompts" points here. |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The exam sheets follow the subject and the student (Priority: P1)

The family has said once how a subject's problems should be split and how this student's statements should be
classified. Every `exam build` of that subject asks for its sheets accordingly, with nobody repeating it.

**Why this priority**: it is what the operator asked for, and with no slot into the prompts the rest changes nothing.

**Independent Test**: with invented rules for one invented subject and for the student, build that subject's exam and
another subject's, and read the prompts each one sends.

**Acceptance Scenarios**:

1. **Given** a rule for problems in subject A and one for the student, **When** subject A's exam is built, **Then** the
   problems sheet's prompt carries both, the student's first and the subject's after.
2. **Given** the same rules, **When** subject B's exam is built, **Then** its prompts carry the student's rule and not
   subject A's.
3. **Given** a rule for problems only, **When** the exam is built, **Then** the theory sheet's prompt does not carry it.
4. **Given** no rules at all, **When** the exam is built, **Then** every prompt is byte-identical to what it is today.
5. **Given** a rule that contradicts the fixed text, **When** the prompt is written, **Then** it says that the rule
   prevails there, and the limits of FR-006 stay in force.

---

### User Story 2 - A run says which rules it relied on (Priority: P1)

Reading a run's result, the family knows that the rules loaded and which version of them, without their text showing up
where it should not.

**Why this priority**: a rule that silently failed to load looks exactly like a rule the notebook ignored.

**Independent Test**: build with rules, without rules and after changing one, and read the output and the pack's
record.

**Acceptance Scenarios**:

1. **Given** rules for both levels, **When** a run ends, **Then** its result names each level and section it used with a
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
   **Then** it does not ask again, and it says which rule it relied on.

---

### User Story 4 - The family gives a rule once (Priority: P2)

The family says a rule in the chat. It is written down in the family's words, read back, and from then on it loads.

**Why this priority**: a rule stuck in a chat is the problem this spec exists for, but the family can write the file by
hand until this works.

**Independent Test**: state an invented rule in a session, confirm it, and check that it is in the student's configuration,
that nothing of it reached the repository, and that a later run uses it.

**Acceptance Scenarios**:

1. **Given** a rule said in the chat, **When** the agent proposes it, **Then** it shows the text, the level and the
   section, and writes nothing until the family confirms.
2. **Given** a rule file the family edited by hand, **When** a run loads it, **Then** it is used as it stands.
3. **Given** a mistyped subject name or section, **When** the configuration is checked, **Then** it is reported, by name
   and never by content.

### Edge Cases

- A rule that holds braces: it reaches the prompt as written, and is never read for placeholders.
- A rules file that cannot be read: the run refuses before asking the notebook for anything, and says which level. Running
  without it would look like a run that followed it.
- A rules file still holding `changeme`: the same refusal, as with any other configuration (FR-003 of spec 001).
- Rules too long for the prompt: the run refuses, says by how much and which level, and sends nothing. They are never cut
  in silence.
- An empty file or section: the same as none.
- A rule the notebook does not obey: alfabeta cannot tell from the prompt, so the first real run is checked by eye (SC-005).
- A rule asking for new numbers on an exam sheet: nothing recomputes those (spec 002 FR-036), so the proposal in story 4
  says so and points to the practice sheet.
- A rule saying part of a topic is not in the exam: FR-006 applies; it needs a source, and the rule alone excludes nothing.
- An exam over several topics: each sheet carries the same rules.
- The second student: their rules are separate, and one student's never load for another (constitution I).

## Requirements *(mandatory)*

### Functional Requirements

**Where they live**

- **FR-001**: Rules MUST live in the student's configuration folder, outside the repository: one text for the student and
  at most one per configured subject. Having none MUST be valid, and each is optional (constitution VII).
- **FR-002**: A rule text MUST be written in sections naming what it speaks to: **problems**, **theory** or **both**. A
  section with another name, or a file naming no configured subject, MUST be reported by the configuration check, by name
  and never by content. The repository MUST hold only the documented shape, with `changeme` examples.

**When they load**

- **FR-003**: `exam build` MUST add to the prompt of each sheet the sections that speak to it, the student's first and the
  subject's after, each time it runs. The problems sheet gets **problems** and **both**, the theory sheet **theory** and
  **both**, and start notes none. With no rules, the prompt sent MUST stay byte-identical to today's.
- **FR-004**: The study-pack skill MUST read the same rules before its prompts and its judgement steps, carrying **problems**
  and **both** into the practice sheet and the quiz, and **theory** and **both** into the guide, the summary and the blocks it
  proposes. A video's focus takes only what fits, as a judgement of the agent, reported as such.
- **FR-005**: Each run reads the rules as they stand. Nothing MUST copy them to another place to go stale.

**What a rule may change**

- **FR-006**: The added text MUST say that a rule prevails where it contradicts the fixed prompt, and a subject's rule over
  a student's. It MUST NOT prevail on: what is in the exam (the announcement, the exclusions that need a source, the family's
  named topics), checking every number, showing where a fact comes from, or anything the constitution requires. The skill
  applies the same limits to its judgement steps.
- **FR-007**: The added text MUST tell the notebook to apply the rules without quoting or mentioning them, so that no sheet
  reads "this student has trouble with…" to the student.

**What a run shows**

- **FR-008**: A run's result and the pack's record of each sheet MUST name the levels and sections used, with a short
  fingerprint of their text, or say that none were used. Neither MUST hold a word of the rules.
- **FR-009**: A rules text MUST NOT reach a log, a message, an issue, a pull request or a commit. It MAY go to the services
  the family uses for the study material: the notebook owner's account and Claude (constitution III).
- **FR-010**: An unreadable rules file, one still holding `changeme`, or rules too long for the prompt MUST stop the run
  before anything is asked of the notebook, saying which level and why.

**Who writes them**

- **FR-011**: The family MAY edit a rule text by hand. An agent MAY write one only after showing the family its text, level
  and section and hearing their confirmation, and only that text: the rest of the configuration stays as it was.

**What rules never do**

- **FR-012**: A change of rules MUST NOT regenerate, retitle or delete any piece.
- **FR-013**: Sync, the agenda and the calendar MUST NOT read the rules.

### Key Entities

- **Rule text**: one student's or one subject's rules, in sections, in the student's configuration. The family's words,
  never validated for meaning.
- **Section**: the part of a rule text that speaks to problems, theory or both.
- **Fingerprint**: a short value computed from the text a run used, which tells two versions apart and reveals nothing
  of them.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With no rules, in a fixture, each prompt `exam build` sends is byte-identical to the one sent before this
  feature, for all the prompts of an exam with and without an announcement.
- **SC-002**: In a fixture with rules for two subjects, no prompt of one carries a word of the other's, and no theory sheet's
  prompt carries a problems section.
- **SC-003**: The guardrail finds no rules text in the repository, and in a fixture no word of a rule reaches any run's output,
  record or log.
- **SC-004**: A family that has stated a rule does not need to repeat it: over two runs of a subject, the second needs no
  instruction from the chat to carry it.
- **SC-005**: On the first real run with rules, reading the printed sheets shows each rule applied and none quoted. Until that
  run the added text is unmeasured, like the prompts around it, and what it found is recorded with no personal data.

## Assumptions

Defaults the operator has not ruled on yet:

- A rule adds to the fixed prompt and prevails where they contradict, within FR-006. It never replaces a prompt, so the
  measured wording stays, and a subject's own prompt is left for when rules prove not to be enough.
- The family dictates and the agent writes after confirmation, or the family edits by hand (FR-011). A dedicated command is
  left out: the file is plain text, and a command would add nothing a confirmed edit lacks.
- Rules reach every study piece, not only the exam sheets, since the practice sheet is where new problems come from.

Other assumptions:

- Rules are written in the prompts' language, Spanish, as the family speaks it; nothing translates them.
- The prompt length the notebook accepts is measured in the plan, not assumed here.

## Dependencies

- Spec 002: the exam sheets and the study pack's pieces, and FR-036's accepted risk.
- Spec 007: an exam with nothing announced takes the same rules.
- Spec 008: FR-011, for study material to read the family's statements and solutions. Without it a notebook holds them only
  if someone added them as sources.
- Constitution I, II, III and X. Rules are student configuration under II, so no amendment is expected; the plan
  checks it.
