# Research: Standing rules per subject and per student

## R1. Keys rather than texts of their own

- **Decision**: flat string keys, `rules_problems`, `rules_theory` and `rules_both`, in `[student]` and in each `[[subjects]]`.
- **Rationale**: the operator's framing, a rule is one more parameter of the student. The configuration check already reports a
  missing, extra, mistyped or unset key by name and never by value, so a mistyped subject stops being a failure of its own.
- **Cost, probed with `tomllib`**: in a basic string an inner quote or `\sqrt` is a decode error, and `\frac` silently becomes a form
  feed plus `rac`. A file that does not parse stops every command that reads it, so one bad rule could stop the sync. `'''...'''` holds
  them all, so the template's examples and the agent's writes use it, and a write goes through a checked copy (FR-011).
- **Alternatives**: a folder of Markdown files, one per subject: it needed its own validation, a companion template and a way to
  catch a file named after no subject. A nested `[student.rules]` table: reads the same, and adds a level to `[[subjects]]`.

## R2. Added after filling, not through a placeholder

- **Decision**: `exam build` fills the prompt as today, then appends the added text.
- **Rationale**: every template stays byte-identical, so the hash test stands and SC-001 holds by construction. A rule is never
  read for placeholders, since `fill` is not applied to it as a template (the same care as an announcement with braces).
- **Alternatives**: a `{rules}` placeholder in six prompts: changes all the hashes and every prompt's trailing space, for nothing.

## R3. The rule prevails, with limits

- **Decision**: rules add, and prevail where they contradict the fixed text, except on the limits of FR-006.
- **Rationale**: the problems sheet says "as few patterns as possible", and the first real rule says the opposite. Adding without
  precedence leaves the notebook to choose.
- **Limits checked against the prompts**: the notebook reads only what the added text says, so "whatever the constitution requires"
  has to be spelled out. Corrections sit at the end of the prompts with no announcement, so a rule after them could undo them. The
  scheme clause holds constitution X. «Usa solo los problemas de las fotocopias» keeps out new numbers nothing recomputes. The print
  step breaks the page on «Soluciones», and spec 007 asks for an opening sentence word for word: both are in quotation marks.
- **Alternatives**: a whole prompt per subject: loses the measured wording and multiplies the texts to maintain.

## R4. Kinds of piece

- **Decision**: problems, theory or both.
- **Rationale**: the theory sheet says that problems do not go there, and a rule that prevails could put them back. A rule on how to
  split problems must not reach it.
- **Alternatives**: every rule to every sheet: the failure just described. A kind per piece: more keys than any rule so far needs.

## R5. Length limit

- **Decision**: 2,000 characters of `{rules}` per prompt, a constant in `src/alfabeta/exam/prompts.py`. Above it the run refuses with
  `rules_too_long`. The skill applies the same figure and tells the family.
- **Rationale**: the exam prompts measure between about 1,600 and 2,500 characters unfilled, before an announcement or corrections,
  and no limit of the notebook's report prompt is measured in this repository. About doubling a prompt is a cautious bound, and
  refusing is better than a rule cut in silence.
- **Unmeasured**: the first real run (gate 2) tests it. A notebook refusing a shorter prompt shows up as a failed report step, as
  today.

## R6. Fingerprint

- **Decision**: the first 8 hexadecimal characters of the SHA-256 of the added text, per sheet.
- **Rationale**: enough to tell two versions apart, and it reveals nothing readable. It lives in the result and in the pack's record.
- **Alternatives**: the rule's first words: a minor's data in output. A version number: someone has to bump it.

## R7. What the skill does

- **Decision**: the skill reads the keys from the configuration it already reads and appends the same section of `prompts.md`.
- **Rationale**: it already fills prompts by hand; it needs no command. It reports levels and kinds. It computes no fingerprint,
  since nothing compares it.
- **Consequence**: its "never write to the configuration" gains one exception in slice 2, a rule the family confirmed.

## R8. Rules outside `Subject`

- **Decision**: `StudentConfig.rules(folder)` returns a `Rules` value with `repr=False`, rather than new fields on `model.Subject`.
- **Rationale**: `Subject` is built and printed across sync; a rule on it could reach a traceback or a log. Sync has no reason to
  hold rules (FR-013).

## R9. Bringing the keys to a real configuration

- **Decision**: one sequence, run by the agent outside any scheduled time: copy the configuration with user-only permissions;
  remove the refresh agent; add the empty keys through a checked copy; update the checkout with a fast-forward pull; run the
  configuration check; on failure restore the copy and the previous commit; install the refresh agent again.
- **Rationale**: old code refuses the keys as extra, new code refuses their absence. The scheduled sync stops at its configuration
  check, before it takes the lock, so a lock protects nothing. `notebook refresh` also validates `student`, every `refresh_minutes`
  and at load, and fails before it can notify, so a half-done step would silently stop notes reaching the notebook. Any pull in that
  checkout between the merge and this step would do the same, so none happens. The operator accepted this cost on 2026-11-06.
- **Alternatives**: an optional key with a silent default: forbidden by constitution II.
