# Contributing to alfabeta

alfabeta is a small tool a family runs on its own Mac. This page is for whoever changes its code or
its documents. For using it, read the [README](README.md).

## Prepare the environment

You need [uv](https://docs.astral.sh/uv/) and [Node.js](https://nodejs.org/) 23 or later.

```bash
make setup-python setup-node
```

`uv` installs Python 3.12 if it is missing and creates `.venv/` from `uv.lock`. `npm ci` installs
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
6. the personal-data guardrail. Until spec 001 T014 adds it, the gate prints it as skipped.

GitHub runs the same `make ci` on every pull request (`.github/workflows/ci.yml`). The `autofix`
job beside it only reports what ruff would change and never blocks.

- Pyright in strict mode is the only type checker. Do not add mypy.
- A gate that inspected nothing is not green. pytest exits non-zero when it collects zero tests,
  and the guardrail checks itself before it scans.

## What may go into the repository

The repository is public. It holds code and templates only, never a student's data. The
[constitution](.specify/memory/constitution.md) is the rule; in short:

- **Configuration:** only `config/template.toml`, with `changeme` values. A student's configuration
  lives in `~/.alfabeta/<student>/`.
- **Test fixtures:** only invented data, and only synthetic pages generated with `anonymize` go into
  `tests/fixtures/`. A real Classroom page, a real name, an email address or a real id never does.
- **Secrets:** tokens and cookies live in the macOS keychain or the data folder, never here.

## How work is organised

The work follows Spec Kit: spec, plan, tasks, then one branch from `main` and one pull request per
issue. Branches are named `<type>/<issue>-<summary>`, and commits follow Conventional Commits.
