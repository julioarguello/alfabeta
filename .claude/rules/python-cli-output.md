---
paths:
  - "src/alfabeta/__main__.py"
  - "src/alfabeta/**/cli.py"
  - "tests/test_smoke.py"
  - "tests/test_notes_cli.py"
  - "tests/test_notes_agent.py"
  - "tests/test_agenda.py"
  - "tests/test_anonymize.py"
  - "tests/test_book.py"
  - "tests/test_config.py"
  - "tests/test_decisions.py"
  - "tests/test_exam_prep.py"
  - "tests/test_google_notify.py"
  - "tests/test_multiple_students.py"
  - "tests/test_plan.py"
  - "tests/test_plan_apply_us1.py"
  - "tests/test_sandbox.py"
  - "tests/test_state.py"
---
<!-- Adapted on 2026-11-02 from Server Startup's shared Python and CLI rules; edit here, this copy is alfabeta's own. -->

# Python CLI — Output, Errors, Version

Governs what `python -m alfabeta` **prints**. What it *takes* is `python-cli.md`. Every rule
carries a label — **standard** (source named), **deliberate divergence** (opposite source + the
precondition), **house rule** — and a **Gate:** or a **Not gated:** with the reason.

**What wins.** Each spec's `contracts/cli.md` fixes a command's stdout (a JSON result), its
reasons and its exit codes; the constitution fixes language and what may never be shown
(Technical constraints › Language; principles II, III). Where this rule prescribes something
else — glyphs, colour, a banner, a label — it is guidance for human-facing lines, and the
contract and the constitution win.

Sources: **CLIG** clig.dev · **GNU** Coding Standards §4.4, §4.8 · **NO_COLOR** no-color.org ·
**PRIMER** GitHub Primer CLI · **HEROKU** CLI style guide · **POSIX** XBD §12.2.

**Proving the gates (house rule):** a rule this file says is gated has a test that fails when it
is broken; a rule promised a gate that does not exist yet is a skipped test carrying the reason,
not an absence.

## 1. Streams — standard (CLIG)

- **Primary output → stdout, as one JSON object** (`_emit()`, `ensure_ascii=False`), whose
  fields the command's contract lists. **Messaging → stderr**: progress, warnings, the error
  line, the summary for the family.
- **Composability test:** if a skill or a reader would write `… | jq` or `$(…)` for it, it is
  primary output and belongs in the JSON.
- **One producer per stream:** machines through `_emit()`, people through one stderr helper per
  module (`_fail()` and its siblings). A bare `print()` elsewhere in a command module is a defect.
- **Language:** a line the student or the family reads is in **Spanish** (the `classroom apply` summary,
  «agenda actualizada», a notification); a line for whoever runs the code, JSON keys and
  `reason` values are in English (constitution, Technical constraints › Language).

**Gate:** each spec's CLI tests parse stdout as JSON. **Not gated:** a stray `print()` (ruff
`T20` is not selected; adopting it with a per-file ignore for the emitters is the gate).

## 2. The version line — standard (GNU 4.8.1)

- `python -m alfabeta --version | head -1` is `alfabeta X.Y.Z` — a constant name, the version
  after the last space; **stdout, exit 0**. argparse's `action="version"` does exactly this.
- **The commit — house rule, not adopted:** the version literal moves on a release, not on a
  merge, so it cannot tell two commits apart. If a second line is ever added, it is
  `git describe --tags --always --dirty` of the tree **above the installed package**, with
  `GIT_DIR`/`GIT_WORK_TREE`/`GIT_INDEX_FILE`/`GIT_COMMON_DIR` scrubbed (a run from a git hook
  would otherwise name another commit); no checkout ⇒ no line, never a placeholder.
- **No banner, no ASCII art.** If one is ever wanted: TTY only, never into a pipe, never before
  the parseable line.

**Gate:** `tests/test_smoke.py` runs `--version`.

## 3. Colour and the terminal — standard (CLIG, NO_COLOR, PRIMER, HEROKU)

alfabeta prints **no colour** and does not declare `rich`; adding either is a dependency the plan
justifies (constitution IX). If colour is ever added:

- **Disable it** off a TTY, on `NO_COLOR` (set and non-empty), on `TERM=dumb`. `NO_COLOR`
  disables colour only.
- **Colour enhances meaning, never carries it**: every state has a word on the line.
- **Yellow and red are reserved** for warnings and errors; cyan for an identifier or a command
  to run next.

**Gate:** none needed while no line carries an escape; then `NO_COLOR=1 … | cat` has zero SGR.

## 4. Vocabulary — house rule, extending PRIMER (`✓ - ✗ + !`)

Guidance for human-facing stderr lines; a contract's wording (a Spanish line it quotes) wins.

| Glyph | Meaning |
|:--|:--|
| `✓` | step or item done |
| `✗` | item failed, or the command refuses |
| `⚠` | warning; run stays green |
| `→` | from → to, nothing else |
| `…` | closes a step header, nothing else |

- **No emoji**: a hint is a sentence naming the command; elapsed time is `in 4.2 s`.
- Glyphs are spelled in one helper, not in each command module. **Not gated** while none is used.

## 5. Paths and state changes — standard (CLIG); the path form is the constitution's

- **Every write, move and delete names its path** — one line or JSON entry per file, or the
  directory plus the count when the directory is the unit. A delete lists what went.
- **Path form: relative to the student's root, never absolute** — the absolute root of Google
  Drive for desktop carries the account's email address (spec 001 contract; principle III). No
  output names an address, a token or a `display_name`; accounts by alias, ids abbreviated, an
  account of a list (`drive.share_with`) by its position. This replaces the shared rule's "absolute otherwise": the constitution
  wins.
- **Announce before crossing a boundary** — a line before a download, an upload, a sign-in.

**Gate:** the guardrail and each spec's tests that assert no output carries student data.
Boundary announcements **not gated** — a review item.

## 6. Brevity and quiet — standard (CLIG)

- **One line per step on the happy path.** Detail belongs to a warning.
- **No timestamps on the terminal**; a timestamp belongs in `data/log.jsonl`. A new line carries
  no `FAIL`/`ERROR`/`INFO` prefix; the `alfabeta: warning:` lines a contract already prints stay.
- **An unattended run is silent on success** where its contract says so (`runner read` on
  `lock_busy`).

## 7. Errors — standard (GNU 4.4); hints, items and pipes house rules

- **One shape for every failure:** `alfabeta: <message>` on stderr and
  `{"ok": false, "reason": "<reason>"}` on stdout, through `_fail()`. `reason` is a stable
  snake_case word from the contract (`invalid_config`, `lock_not_held`); the message is for people.
- **Label: GNU's non-interactive form `program: message`** — alfabeta's commands are run by
  skills and agents, not typed. The shared rule's `Error:` label (for a CLI a person types) does
  not apply. Sentence: lowercase first word, no trailing period, as `_fail()`'s callers write it.
- **An error states the fact; the remedy is the next command**, quoted, at the end: «…; photos
  wait (`claude set-key`)». A hint opens with its action, one sentence, at most 140 characters.
- **The message names the key, never the value** (principle III; `config check`).
- **Several items, one line or entry each** — a headline that counts, then `<item>  <outcome>` in
  the order processed; design from every combination of outcomes. **Verdict last.**
- **A loop asks every item before it fails** — collect each status (`share`: a failed account is
  counted and the rest go on) and exit with the worst after the last.

**Gate:** each command's tests assert its `reason` and exit code for every failure its contract
lists.

## 8. Exit codes — standard (CLIG); the map is the contract's

`0` success · `1` failure · `2` argparse's usage errors. A command's other codes are in its
contract's *Codes* column (`guardrail check`: 2 checked nothing, 3 blind detector; `google account check`: 2 the
link is unusable; partial runs and signed-out states in specs 002 and 005). That column is the
map; a new code is added there first. The shared rule reserves `2` for usage only — where a
contract already assigns it, the contract wins; a new code avoids `2`.

**Gate:** each command's tests assert the codes of its contract.

## 9. Machine output, counts, empty states — standard (CLIG, PRIMER)

- Machine output is the JSON on stdout: no colour, no truncation, exact dates (ISO 8601,
  `Europe/Madrid`, principle VIII), state as a word.
- **Counts carry nouns** in human lines. Not gated.
- **An empty result is a result:** «sin cambios» on stderr, an empty list in the JSON, exit 0 —
  neither a warning nor an error.

## 10. Anti-patterns

| ❌ | ✅ |
|:---|:---|
| a result only on stderr | the JSON on stdout, the summary on stderr |
| bare `print()` in a command module | `_emit()` for machines; one stderr helper for people |
| an English line in the family's summary | Spanish, as the constitution says |
| an absolute path, an address, a `display_name` | relative to the student's root; alias; abbreviated id |
| `✅`, `❌`, `💡` | `✓`, `✗`, the sentence |
| `alfabeta: Something went wrong.` | `alfabeta: the configuration folder does not exist` + `reason` |
| the value of a bad key in the message | the key and why |
| exit inside a loop on the first failure | collect; exit with the worst after the loop |
| a new exit code nobody listed | the contract's *Codes* column first |
| a traceback as the only output | `_fail()` with a `reason`, for every failure the contract names |
