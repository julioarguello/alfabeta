# Data model: Standing rules per subject and per student

## Configuration keys

In `[student]` and in each `[[subjects]]`:

| Key | Type | Reaches | Empty |
|---|---|---|---|
| `rules_both` | string | every piece that takes rules ([contracts/prompts.md](contracts/prompts.md)) | no rule |
| `rules_problems` | string | problems sheet, practice sheet, quiz, parent guide | no rule |
| `rules_theory` | string | theory sheet, summary, the blocks and plan the agent works out | no rule |

Validation is the configuration check's: missing, extra, wrong type or holding `changeme` is a problem named by its key. A value
of spaces only counts as empty. Examples and the agent's writes use literal strings (`'...'` or `'''...'''`), which keep quotes and
backslashes as written; a basic string can stop every command reading the file, or silently change a backslash.

## `Rules` (in memory, `repr=False`)

| Field | Meaning |
|---|---|
| `student_both`, `student_problems`, `student_theory` | the student's level, stripped |
| `subject_both`, `subject_problems`, `subject_theory` | the subject's level, stripped |

For a sheet of kind `problems` or `theory`, the used parts are, in this order: the student's `both`, the student's kind, the subject's
`both`, the subject's kind.

## Result of `exam build`

Top-level key `rules`, a list with one entry per sheet kind that gained text, and empty when none did:

```json
{"rules": [
  {"sheet": "theory", "used": ["student.both", "subject.theory"], "fingerprint": "1a2b3c4d"},
  {"sheet": "problems", "used": ["student.both", "subject.problems"], "fingerprint": "5e6f7a8b"}
]}
```

## Pack record (`data/study-pack.json`)

Each exam piece gains `rules`: `{"used": [...], "fingerprint": "..."}`, with the same values as the result, or `null`. Pieces recorded
before this feature have no such key, and readers treat that as `null`.

## What holds no rule text

The result, stderr, `data/log.jsonl`, the pack's record, a `Problem`, an exception message and `repr(Rules)`.
