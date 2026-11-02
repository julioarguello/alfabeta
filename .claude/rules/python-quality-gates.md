---
paths:
  - "pyproject.toml"
  - "pyrightconfig.json"
  - "Makefile"
  - ".github/workflows/**"
---
<!-- Adapted on 2026-11-02 from Server Startup's shared Python and CLI rules; edit here, this copy is alfabeta's own. -->

# Python Quality Gates

**States what is IN FORCE, not what would be nice.** A canonical value nobody adopted is
marked as such. A rule describing a tool nobody installs makes an agent "fix" the working
setup. The list of gates is the constitution's (*Development workflow*: `ruff`, `pyright`,
`pytest` and the personal-data guardrail before every pull request) and `CONTRIBUTING.md`'s;
where this rule disagrees, those win.

## 1. Tool Selection

| Gate | Tool | Blocking |
|:-----|:-----|:---------|
| Lint + Format | `ruff check` + `ruff format --check` | ✅ |
| Type check | Pyright strict — §2 | ✅ |
| Test | `pytest` (0 collected MUST fail) | ✅ |
| Browser JS | `node --test` | ✅ |
| Personal data | `python -m alfabeta guardrail check --all` | ✅ |
| Coverage | `pytest-cov` — **not adopted** | ❌ |

All of them run through **`make ci`**, in that order (`CONTRIBUTING.md`, *The gate*).

## 2. MUST: exactly one type checker, strict, named in `CONTRIBUTING.md`

alfabeta's choice is **Pyright strict**; `CONTRIBUTING.md` says "Do not add mypy". Never one
checker in the IDE and a different one in CI — that makes local-green/CI-red permanent. Pyright
is the same engine as Pylance, so IDE and gate agree.

### 2.1. Why `ANN` is not optional on a Pyright gate

| Signature | Pyright strict | ruff `ANN` |
|:----------|:---------------|:-----------|
| `def f(a, b):` | `reportMissingParameterType` ×2 | `ANN001` ×2, `ANN201` |
| `def f(a: int, b):` | `reportMissingParameterType` | `ANN001`, `ANN201` |
| `def f(a: int, b: int):` | **nothing** (return inferred) | `ANN201` |

Pyright rejects an unannotated **parameter**, accepts a missing **return** annotation.
Dropping `ANN` silently stops requiring return types anywhere.

## 3. Ruff — in force (`pyproject.toml`)

**select**: `E W F I B C4 SIM UP RUF D TC ANN`
**ignore**: `E501 D100 D104 D107 ANN401` (`ANN401`: `Any` where a Protocol needs it)
**per-file-ignores**: `tests/** = ["ANN","D","RUF001","RUF012","RUF043","RUF059","TC","SIM"]`
**extend-exclude**: the vendored `skills/sciencebits-a-notebooklm` and the untracked `scripts/`

| Setting | Value | Immutable? |
|:--------|:------|:-----------|
| `line-length` | `120` | ✅ |
| `target-version` | `py312`, matching `.python-version` | Per-project |
| `pydocstyle.convention` | `google` | ✅ |
| `format.quote-style` | `double` | ✅ |

**Recommended, not adopted**: `N` (pep8-naming), `S` (bandit),
`format.docstring-code-format = true`. Do not claim any of them is in force. **`E501`** stays
ignored — the formatter owns line length.

## 4. Pyright — in force

**One `pyrightconfig.json`, at the root**: `strict`, `pythonVersion` 3.12, `venv` `.venv`,
`include` `src` and `tests`, `reportMissingTypeStubs: false`; `executionEnvironments` separate
`src` from `tests` (`extraPaths: [".", "src"]`, `reportPrivateUsage: "none"`).

- **NEVER a `tests/pyrightconfig.json`** — it silently overrides the root one beneath it.
- If an untyped library forces it, relax with `reportUnknown*: "warning"` in the root config
  and say why there; never a second checker, never a blanket `# type: ignore` in a module.

## 5. pytest — in force

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --tb=short"
```

- alfabeta declares **no tier markers** today: every test runs in `make ci`, offline, with
  fakes for Google, the keychain and the browser. Declare a tier only when one exists, and
  deselect only what needs credentials or a deployment.
- **Unit tests carry NO marker** — a `unit:` marker means a forgotten decorator silently drops
  a test from the default run.
- **The runner never passes its own `-m`**: the expression lives in `addopts`.
- **Exit code 5 (0 collected) MUST fail.** A gate that inspected nothing is not green; the
  Makefile's `test` recipe says so beside it.
- Config lives in `pyproject.toml`. **Never a `pytest.ini`** — pytest silently prefers it.

## 6. CI Architecture (MUST)

**The gate is `make ci`**, invoked identically from a shell and from CI. The moment CI
re-implements the steps, they drift.

```
Job 1: autofix       (continue-on-error) → ruff check --fix --diff + ruff format --diff, report only
Job 2: quality-gate  (BLOCKING, NO `needs:`) → make setup-python setup-node ci
```

- **NEVER `needs: autofix`** on the blocking job — it would *skip* when autofix fails, and a
  gate that never ran looks exactly like one that passed.
- **NEVER a `paths:` filter on the gate** — a hand-kept list goes stale and a PR outside it
  runs no gate. A CI change that removes or skips a gate waits for the operator (constitution,
  *Development workflow*).
- `python-version-file: .python-version` and `node-version-file: .node-version`, never a
  literal in the workflow.

## 7. Overrides — Allowed

`target-version` · `per-file-ignores` · test markers and an `addopts` `-m`, once tiers exist.

## 8. Overrides — Forbidden

- `line-length` ≠ 120 · `quote-style` ≠ double · `pydocstyle.convention` ≠ google
- Removing core `select` rules — or `ANN` while the gate is Pyright · adding mypy
- Single-job CI · a blocking gate that `needs:` autofix · a gate without tests or without the
  guardrail

## 9. The interpreter a Makefile runs — a uv-owned `.venv`

- **Every Python recipe runs `uv run --locked …`, never a bare `python`/`python3`/`pip`.** A bare
  `python3` is whatever is first on `PATH` — another project's venv, another version.
- **Files**: `pyproject.toml` + `uv.lock` + `.python-version`. alfabeta is a package
  (`[tool.uv] package = true`, hatchling); tools live in `[dependency-groups] dev`.
- **`make setup-python`** — the command anyone types first: installs the pre-commit hook, then
  `uv lock --check` (a clear message when the lock is stale) → `uv sync --locked`.
- **One owner**: nothing else installs into `.venv` (`uv sync` is exact) — not `pip`, not a
  script.
- **A relock may change the lock format**, and an older uv does not downgrade it. A
  dependency-only PR relocks with the uv the lock was written by.
- **CI**: `astral-sh/setup-uv` with `enable-cache`, then `make setup-python`; the recipes'
  `uv run` finds `.venv` without touching `PATH`.

## 10. What the test job costs

Measuring and cutting a pytest CI job's cost: [`python-test-cost.md`](python-test-cost.md).
