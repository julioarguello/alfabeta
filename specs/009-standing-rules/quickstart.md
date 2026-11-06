# Quickstart: checking standing rules

Everything here but the last scenario uses invented data and the stand-in for `nlm`.

## Automated

```bash
uv run pytest tests/test_config.py tests/test_exam_prep.py tests/test_contracts.py -q
```

Expected: empty keys give the same prompts and the same text hashes as before; rules for one subject never reach another's prompts;
a problems rule never reaches a theory prompt; no word of a rule is in stdout, stderr or the pack's record; over-long rules refuse
with `rules_too_long` and ask nothing; a rule written with quotes and backslashes in a literal string arrives as written.

## On the configuration

```bash
uv run python -m alfabeta config check --student <id>
```

Expected, with a rule key removed, renamed or left at `changeme`: the key is named with its reason, and its value is not.

## On a real notebook, by the family

1. Write one rule in the subject's `rules_problems` and one in the student's `rules_both`.
2. Run `exam build` for that subject with `--topic <folder>`.
3. Read the result's `rules`: both are named, with a fingerprint.
4. Read the printed sheets: each rule is applied, and none is quoted or mentioned.
5. As a viewer of the notebook, look for the prompt on a sheet and on a quiz made with an invented rule. Until both are known, write
   no rule that describes a difficulty.
6. Record what it found with no personal data (SC-005).
