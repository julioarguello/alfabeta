# Research: Standing rules per subject and per student

## R1. Keys rather than texts of their own

- **Decision**: flat string keys, `rules_problems`, `rules_theory` and `rules_both`, in `[student]` and in each `[[subjects]]`.
- **Rationale**: the operator's framing, a rule is one more parameter of the student. The configuration check already reports a
  missing, extra, mistyped or unset key by name and never by value, so a mistyped subject stops being a failure of its own. TOML
  holds multi-line strings.
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
- **Limits checked against the prompts**: corrections are appended at the end of the prompts with no announcement, so a rule after
  them could undo them, and they are listed. The print step breaks the page on «Soluciones», so word-for-word titles are listed.
- **Alternatives**: a whole prompt per subject: loses the measured wording and multiplies the texts to maintain.

## R4. Kinds of piece

- **Decision**: problems, theory or both.
- **Rationale**: the theory sheet says that problems do not go there, and a rule that prevails could put them back. A rule on how to
  split problems must not reach it.
- **Alternatives**: every rule to every sheet: the failure just described. A kind per piece: more keys than any rule so far needs.

## R5. Length limit

- **Decision**: 2,000 characters of added text per prompt, a constant in `src/alfabeta/exam/prompts.py`. Above it the run refuses
  with `rules_too_long`.
- **Rationale**: the longest exam prompt is about 2,000 characters before an announcement, and no limit of the notebook's report
  prompt is measured in this repository. Doubling a prompt is a cautious bound, and refusing is better than a rule cut in silence.
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

- **Decision**: empty keys are added to the student's real configuration in the step that updates the family's checkout.
- **Rationale**: old code refuses them as extra, new code refuses their absence, and the scheduled sync runs from that checkout. The
  agent does it as this feature's migration, on the operator's approval of 2026-11-06, adding only those keys.
- **Alternatives**: an optional key with a silent default: forbidden by constitution II.
