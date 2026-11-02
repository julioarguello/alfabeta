---
paths:
  - "**/*.py"
---
<!-- Adapted on 2026-11-02 from Server Startup's shared rule rules/python.md (private repository); edit here, this copy is alfabeta's own. -->

# Python Standards

**States what is IN FORCE, not what would be nice.** An entry not yet adopted is labelled.
Where this rule and the [constitution](../../.specify/memory/constitution.md) disagree, the
constitution wins (its Governance says so).

## 1. Stack — in force vs candidate

| Domain | In force | Candidate |
|:-------|:---------|:----------|
| Testing | `pytest` | `pytest-cov` (no coverage gate) |
| Type checking | Pyright strict — the only checker (`CONTRIBUTING.md`: "Do not add mypy") | — |
| Lint + format | `ruff` | — |
| Schemas in tests | `jsonschema` (dev group) | — |
| PDF | `pypdf`, `reportlab` (spec 005) | — |
| Retry | — (none declared) | `tenacity` |
| Boundary models | `dataclasses` | `pydantic` |
| Config | TOML with template mirroring (`config/template.toml`, §4); env only for run plumbing (`ALFABETA_RUN`) | `pydantic-settings` |
| CLI | `argparse` | `typer` (`python-cli.md`), `rich` (`python-cli-output.md`) |
| Packaging | `uv` — `uv.lock`, `.python-version`, `make setup-python` | — |

**A candidate becomes in force when `pyproject.toml` declares it — never by being written
here.** Check, don't assume: `git grep -nE 'typer|rich|pydantic|tenacity|mypy' -- pyproject.toml`.
And a candidate is not adopted on taste: constitution IX — *a new dependency MUST justify in the
plan why the standard library or what is already there is not enough.*

## 2. Code Style

- `ruff` lints **and** formats. Line length 120; `E501` ignored — the formatter owns wrapping.
- Google docstrings · absolute imports only (`from alfabeta.google import accounts`).
- **`T | None`, never `Optional[T]`** — `ruff` `UP` enforces it from `target-version = "py312"`.
  Most modules carry `from __future__ import annotations`; with it, `ruff` `TC` can move a
  type-only import under `if TYPE_CHECKING:` safely.
- **`Protocol` for dependency inversion, not `ABC`** — needs no registration and no inheritance
  from the implementing side, which keeps adapters (a transport, a keychain, a notifier) out of the
  core's import graph and lets a test pass a fake.
- Canonical values and CI wiring: [`python-quality-gates.md`](python-quality-gates.md).

## 3. Derive, never transcribe

A catalogue kept by hand in several places goes stale. Ask the repository instead of copying a
list into a rule or a doc: `git ls-files skills/` for the skills, `git ls-files 'src/**/cli.py'`
for the command modules, `build_parser()` for the commands. The working tree is not the
repository — resolve existence against git before reporting a gap.

## 4. Configuration

A student's configuration is read from `~/.alfabeta/<student>/` and mirrors `config/template.toml`
(constitution, Technical constraints › Configuration; principle I).

- **Fail at the point of reading, and name the key** — never the value (principle III). A silent
  default is indistinguishable from a real value and fails later, where the missing input is no
  longer visible. `config check` names the key and the reason.
- **Every key read MUST be declared** in `config/template.toml`, with `changeme` values. An
  undeclared read is invisible until the configuration it is missing from. Gated, not a matter of
  care: `tests/test_template_covers_reads.py` walks the AST for every `config.READERS` call and
  needs a string-literal path.
- An environment variable read in the process (`os.environ`) is for run plumbing a skill passes
  inline, not for a setting the family turns.

## 5. Pyright — one config, at the project root

`pyrightconfig.json` is the only config: `src` and `tests` get different search paths through
`executionEnvironments` (`tests` adds `.` and `src`, and relaxes `reportPrivateUsage`). One file,
two roots.

**NEVER a `tests/pyrightconfig.json`** — a second config silently overrides the root one for
everything beneath it. `extraPaths` resolves relative to the `pyrightconfig.json`, not to the
importing file, and Pyright inherits config from parent directories.

**Recurring failure**: stale `extraPaths` after a rename → `Cannot find module` for every source
module at once, which reads like a broken environment, not a stale path.

## 6. Complementary Rules

`python-quality-gates.md` (canonical values, CI) · `python-cli.md` (what a command takes) ·
`python-cli-output.md` (what it prints — streams, version line, errors, exit codes) ·
`python-test-cost.md` (what the test job costs) · `cli-naming.md` (alfabeta's vocabulary).
