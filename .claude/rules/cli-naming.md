---
paths:
  - "src/alfabeta/__main__.py"
  - "src/alfabeta/**/cli.py"
  - "tests/test_cli_naming.py"
  - "specs/**/contracts/cli.md"
  - "skills/**/SKILL.md"
---
<!-- alfabeta's own rule. It applies python-cli.md §6 and §10 (adapted from Server Startup's shared rules). -->

# alfabeta's command names

Every command reads like a method call in Java: a noun says what is acted on, a verb says what
happens. The vocabulary is closed, and **`tests/test_cli_naming.py` holds it** — the groups, the
subgroups and the verbs, each with its one meaning — and fails the build when a command, a doc or a
message does not follow it. This file says how to use it; the lists live only in the test.

## Grammar

```
python -m alfabeta [--home <dir>] <group> [<subgroup>] <verb>[-<object>] [--option …]
```

- **Group and subgroup**: a singular noun of the domain (`decision`, not `decisions`).
- **Subgroup or suffix**: a noun with **two or more** verbs is a subgroup
  (`google account link|check|unlink`, `calendar probe create|delete`); a noun with **one** verb
  joins it as `<verb>-<object>` (`google set-client`, `claude set-key`, `log write-stop`), as
  `google.setClient()` would in Java.
- **Verb**: from the closed list, one meaning CLI-wide. No synonyms (`update`, never `change`
  beside `correct`), no vague verbs (`run`), no abbreviations (`prep`). A leaf never shares a
  group's name.
- **Aggregates drop the verb**: a status view (none exists yet; the test's `AGGREGATES`) is the only leaf
  that is not a verb.
- **Kebab-case** everywhere; **long options only** (`--student`, no `-s`); a secret is never an
  option (keychain or stdin); every command about a student takes `--student`.

## Adding or renaming a command

1. Pick the noun and the verb from `tests/test_cli_naming.py`. A new noun or verb is added there,
   with its one meaning, in the same change — and only if no listed one already says it.
2. A command a spec designs before it is built goes in `PLANNED` (or `PLANNED_OPTIONS` for a new
   option on a built command), with the spec that designs it; the test checks its grammar now and
   asks to drop the entry once the command exists.
3. A rename changes the parser, the tests, every spec's `contracts/cli.md`, the skills and the
   messages in one change, and **ships no alias** (python-cli.md §6). The test's documentation
   walk finds every place that still writes the old name.
