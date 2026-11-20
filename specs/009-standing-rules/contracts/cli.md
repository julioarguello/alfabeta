# Contract: `exam build` with standing rules

Only what changes from [spec 002's contract](../../002-study-pack/contracts/cli.md). No command or option is added.

## Refusal

| Reason | Code | When | Message names |
|---|---|---|---|
| `rules_too_long` | 1 | The `{rules}` of a sheet is over the limit (research R5), checked before the notebook is asked for anything | the sheet's kind and the characters over; never the text |

A missing, extra or unset rule key is `invalid_config`, as today.

## Output

Stdout gains the top-level key `rules` ([data-model.md](../data-model.md)), `[]` when none were used.

Stderr gains one line for whoever runs it, before the notebook is asked; the JSON comes at the end, as today:

- `alfabeta: <time> standing rules: theory student.both subject.theory 1a2b3c4d; problems student.both subject.problems 5e6f7a8b`
- `alfabeta: <time> no standing rules for this subject`

`<time>` is the Madrid time, `YYYY-MM-DDTHH:MM:SS` (constitution 2.12.0).

No line holds a word of a rule.
