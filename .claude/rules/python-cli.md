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

# Python CLI — Commands, Options, Parsing

**Applies to alfabeta's CLI now**: `python -m alfabeta`, built with **`argparse`** in
`build_parser()` (`src/alfabeta/__main__.py`), with command bodies in `src/alfabeta/**/cli.py`.
§1 and §6–§10 apply today. §T (Typer mechanics) applies **only if Typer is adopted** — it is not
declared (`git grep -n typer -- pyproject.toml` is empty), and adopting it is a dependency the
plan must justify (constitution IX). What the CLI *prints* is `python-cli-output.md`; this file
is what it *takes*. alfabeta's vocabulary (groups, verbs, flags) is in `cli-naming.md`. The
section numbers follow the shared rule; its §2–§5, Typer mechanics, are gathered in §T.

Each spec's `contracts/cli.md` is the contract for its commands; where this rule and a contract
or the constitution disagree, the contract and the constitution win.

## 1. A repeated flag is declared once

A flag carried by **two or more** commands is declared once — in argparse, one helper or one
loop over the subparsers that need it (as `build_parser()` does for `--student`), or a
`parents=[…]` parser. A single-use flag stays inline in its command.

**The shared declaration owns identity**: long name, short letter, type, help. **The command
owns its default**, and whether to carry the flag at all. What a *particular* command does with
a shared flag goes in that command's `help=`/description, not in the shared help.

## 6. Naming a command

`{group} {verb}`, group a **noun** of the domain, verb what happens (`lock take`,
`decision confirm`, `book place`); a verb that could mean two things names its object or
destination once a second object is conceivable. Aggregates drop the verb (a status view;
none exists yet). alfabeta's grammar and closed verb list are in `cli-naming.md`.

Rename in-branch, with tests, the spec's `contracts/cli.md` and the skills that call it, and
**never ship a compatibility alias** — a second name for one concept is what the vocabulary
exists to prevent.

## 7. Naming a parameter, and which short letter

The long name is the interface. A **short letter is a separate decision**: it is read by muscle
memory, and a letter meaning one thing in one group and another elsewhere teaches something false.
alfabeta's commands are mostly run by skills and agents, so it defines **no short letters today**
besides argparse's `-h`; a new one has to earn its place.

1. **Earned by frequency.** The option typed on most invocations keeps the letter; a rarely
   typed *override* gives it up.
2. **One letter → one long flag, CLI-wide** — not per group, root options included (`--home`,
   `--version`). Root options go **before** the subcommand (`python -m alfabeta --home <dir> classroom plan
   …`, contract of spec 001); a subcommand reusing a root flag's name is a collision.
3. **Follow the industry convention — after checking which one applies.** Tools with a verbose
   flag put verbose on `-v` and version on `-V`; tools with none leave `-v` free. alfabeta has
   `--version` and no verbose flag: if either gets a letter, write down which camp.
4. **Where you diverge, say so in `cli-naming.md`.** `-r` reads *recursive* almost everywhere, so
   spending it on something else is a choice, not a default.

## 8. Parsing inputs — let argparse do it

The command body receives values, it does not parse them. The declaration is also `--help`.

- **Positional vs option.** A positional is for the one thing the command is *about* and cannot
  run without (`page anonymize <input> <output>` is the exception that proves it: two files, named by
  position like `cp`). Everything else is an option, including anything with a default.
- **Type, not string.** `type=Path`, `type=int`, `type=dt.date.fromisoformat`, `choices=` from the
  model's enum (`choices=[str(m) for m in RunMode]`) — so bad input fails with argparse's message
  and exit code 2, before any side effect. A bounded int takes `choices=range(…)` with a `metavar`.
- **A `bool` option declares its negative** when both states are meaningful:
  `action=argparse.BooleanOptionalAction` gives `--flag/--no-flag`. A one-way switch stays
  `store_true`. Mutually exclusive modes go in `add_mutually_exclusive_group()`.
- **`required=True`** for an option a command cannot run without; a missing one is argparse's
  code 2 and usage message (spec 001 *Common rules*).
- **No I/O and no configuration read in `build_parser()` or a `default=`** — it breaks `--help`
  itself. Configuration is read in `main()`, after parsing, for the tables the group needs.
- **Never an environment axis as a flag on a task command**: the student is `--student`, the
  run is `ALFABETA_RUN`; the command knows the task.

## 9. The docs are part of the contract

The command reference is each spec's `contracts/cli.md`, written by hand, plus the skills that
call the commands — and nothing checks them against the parser, so a rename is exactly what
leaves them behind.

Gate the piece that resolves exactly: **every `python -m alfabeta <group> <verb> --flag` written
in a contract, a skill or a doc must exist on that command** — walk `build_parser()`'s
subparsers, not the AST. It is what a reader copies, and it needs no allow-list. Do **not** widen
it to every flag mentioned anywhere: other tools' flags (`rsync --delete`) would need an
exemption list nobody closes.

Corollary: **name a flag in prose only with its command beside it.**

## 10. Guideline prescriptions (CLIG, GNU, POSIX)

- **Help** — `-h`/`--help` on every node (argparse's default; never `add_help=False`); every
  subparser has a `help=`; a group without a verb is an error (`required=True` on
  `add_subparsers`).
- **Standard flag names** mean what CLIG says: `--all --debug --force --json --dry-run
  --no-input --output --port --quiet --user`. A conventional name never means something else
  here (`--all` is "every tracked file" in `guardrail check`, which fits).
- **`--dry-run` on every command with a side effect**; `--mode dry-run` is not it. A command
  whose spec contract has no `--dry-run` keeps its contract until a spec adds one; a new command
  with a side effect gets it in its contract.
- **Prompts**: alfabeta's commands run unattended (skills, launchd); a command never waits on a
  terminal prompt. Input comes from flags, a file (`--file`) or stdin where the contract says so
  (`claude set-key`).
- **Never override argparse's `--`, interspersed-option or abbreviation defaults** without
  writing why; prefer `allow_abbrev=False` on a new parser, so a prefix never becomes a contract.
- **`-` for stdin/stdout** (POSIX) where a command takes or writes a stream.
- **A verb means one thing CLI-wide; no synonyms in one group** (`check`/`validate`); a leaf
  never shares a group's name. Gate: a verb-reuse sweep over `build_parser()`.
- **Every `subprocess` call carries `timeout=`** or a same-line reason; network timeouts are
  settings, never literals scattered in the body; `--help` answers fast — heavy imports are
  lazy in the command module.
- **Config:** per-invocation → flag, per-student → the student's TOML (constitution I), per-run
  plumbing → env; a family-turned knob is never env-only.
  **Secrets: never a flag** — they live in the macOS keychain or the data folder and arrive by
  stdin or the keychain, never on a command line (`ps` shows it) nor in output (constitution II,
  III).
- **Deprecation** (§6 "never ship an alias") holds while the only callers are alfabeta's own
  skills and agents; it expires with an outside caller.

## §T. Only if Typer is adopted

None of this applies to argparse. It is kept so an adoption does not rediscover it.

- **T1. The alias module.** A flag on ≥ 2 commands is an `Annotated` alias in a private
  `cli/_options.py`: `StudentOption = Annotated[str, typer.Option("--student", help="…")]`, used
  as `def plan(student: StudentOption) -> None`. The alias owns identity (long name, letter,
  type, help, `envvar`); the command owns its default.
- **T2. Why `Annotated`, not the other four.** Factory callables (`optparse`), `click.option`
  decorators (default baked in), a `common_options` decorator factory (fights `Annotated`), a
  shared `OptionInfo` constant (the first positional *is* the default) — only the `Annotated`
  alias, FastAPI's "share `Annotated` dependencies" precedent, keeps a per-command default.
- **T3. The shared instance is safe.** Typer builds a distinct `click.Option` per command, so the
  `action="append"` state hazard is optparse's, not Typer's. Re-verify before porting to Click.
- **T4. PEP 695 breaks it.** `type X = Annotated[...]` makes the alias lazy and Typer never
  resolves the `typer.Option` (an error at import or at `@app.command()`). Keep `X = Annotated[...]`.
- **T5. The alias import is a runtime import.** Typer reads annotations at import time, so ruff
  `TC002` moving it under `if TYPE_CHECKING:` gives `NameError` on `--help`. Keep `TC` live and
  name the decorators: `[tool.ruff.lint.flake8-type-checking] runtime-evaluated-decorators =
  ["typer.Typer.command", "typer.Typer.callback"]` — a group imported from elsewhere needs its own
  qualified entry.
- **T6. Two gates.** **A** — no inline declaration of a name the alias module owns; **B** — no
  flag on ≥ 2 commands that no alias owns, its sites taken by walking the Typer app (exclude
  Click's `--help`). An exception list names the issue that closes each entry and only shrinks.
- **T7. Typer specifics of §7–§10.** Click offers only `--help` unless told
  (`context_settings={"help_option_names": ["-h", "--help"]}`); a leaf with a required positional
  sets `no_args_is_help=True`; a `--flag/--no-flag` keeps its negative in `secondary_opts`; Click
  consumes root options before the subcommand, so a gate walking only `group.commands` misses the
  root callback; output-file options take `allow_dash=True`; a generated reference
  (`typer utils docs`) compared byte for byte needs the generator pinned exactly.

## 11. Anti-Patterns

| ❌ | ✅ |
|:---|:---|
| `add_argument("--student", …)` retyped in each subparser | one helper or loop, as `build_parser()` has |
| `default=` inside the shared declaration | the default stays with the command |
| a compatibility alias for a renamed flag | rename in-branch, tests, contract and skills included |
| a short letter chosen because it was free | earned by how often the option is typed |
| `str` + hand validation in the body | `type=`, `choices=` in the declaration |
| config or I/O in `build_parser()` | read in `main()`, after parsing |
| a secret as `--token <value>` | keychain or stdin |
| a flag named in prose with no command | `python -m alfabeta <group> <verb> --flag`, so a gate can defend it |
