# Contributing to alfabeta

alfabeta is a small tool a family runs on its own Mac. This page is for whoever changes its code or
its documents. For using it, read the [README](README.md).

## Prepare the environment

You need [uv](https://docs.astral.sh/uv/) and [Node.js](https://nodejs.org/) 23 or later. CI runs the
major in `.node-version`, the same way `.python-version` sets Python.

```bash
make setup-python setup-node
```

`make setup-python` also installs the pre-commit hook (`.githooks/pre-commit`), which runs the
personal-data guardrail on every commit. `uv` installs Python 3.12 if it is missing and creates
`.venv/` from `uv.lock`. `npm ci` installs
`jsdom`, which the browser extractor's tests use.

## The gate

```bash
make ci
```

It runs, in this order:

1. `ruff check`;
2. `ruff format --check`;
3. strict `pyright`;
4. `pytest`, which fails if it collects no tests;
5. `node --test` for the browser JavaScript;
6. the personal-data guardrail over every tracked file (`python -m alfabeta guardrail check --all`).

Outside CI, `make ci` also fails if the pre-commit hook is missing or stale.

GitHub runs the same `make ci` on every pull request (`.github/workflows/ci.yml`). The `autofix`
job beside it only reports what ruff would change and never blocks.

- Pyright in strict mode is the only type checker. Do not add mypy.
- A gate that inspected nothing is not green. pytest exits non-zero when it collects zero tests.
  The guardrail plants one defect per detector in memory before it scans, and exits 3 if a
  detector misses it.
- The guardrail names `file:line: detector` and never the value. An invented value that reached
  the published history goes in `.guardrail-allow`, with a comment; a real one never does.

## Agent rules and command names

`.claude/rules/` holds the rules Claude Code loads when it touches the files each one names in
its `paths:`. The Python and CLI ones (`python.md`, `python-cli.md`, `python-cli-output.md`,
`python-quality-gates.md`, `python-test-cost.md`) are adapted from Server Startup's shared rules;
the constitution wins where they disagree. `cli-naming.md` is alfabeta's own.

Every command is `python -m alfabeta <group> [<subgroup>] <verb>`: a singular noun, then a verb
from a closed list with one meaning each (`decision confirm`, `google account link`,
`log write-stop`). The list lives in `tests/test_cli_naming.py`, which fails the gate when a
command breaks the grammar or when a skill, a spec, a doc or a message writes a command or an
option the parser does not have. A rename ships no alias: it changes the parser, the tests, the
contracts, the skills and the messages in one pull request.

## What may go into the repository

The repository is public. It holds code and templates only, never a student's data. The
[constitution](.specify/memory/constitution.md) is the rule; in short:

- **Configuration:** only `config/template.toml`, with `changeme` values. A student's configuration
  lives in `~/.alfabeta/<student>/`.
- **Test fixtures:** only invented data, and only synthetic pages generated with `page anonymize` go into
  `tests/fixtures/`. A real Classroom page, a real name, an email address or a real id never does.
- **Secrets:** tokens and cookies live in the macOS keychain or the data folder, never here.

## How work is organised

The work follows Spec Kit: spec, plan, tasks, then one branch from `main` and one pull request per
issue. Branches are named `<type>/<issue>-<summary>`, and commits follow Conventional Commits.
Pull requests are merged by the agent that opened them, once CI is green and an agent that did not
write the change finds nothing blocking: `/speckit-analyze` for a spec, a review for anything else
(constitution, *Development workflow*). Changes that touch principles I, III or IV, the
personal-data guardrail, these merge rules or Governance, and pull requests from anyone else, wait
for the operator's explicit request; the operator can also stop or revert any of them.

A general consideration from the family about how alfabeta should work becomes part of the
specifications in the same session: an issue, the spec it belongs to with a clarification in its
terms, and the skill that acts on it, besides solving the case at hand. An agent's memory does not
count, because the project has to carry its own rules. A rule about one subject or one student is a
standing rule of its configuration instead (spec 009). Personal data stays out, and the merge rules
above still apply.
