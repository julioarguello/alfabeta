# Quality gate (spec 001 T006). Every Python recipe uses the project's .venv through uv.
# The guardrail runs over every tracked file; the pre-commit hook runs it over the staged change.
.PHONY: setup-python setup-node setup-hooks ci hook-check lint format-check typecheck test test-js guardrail

setup-python: setup-hooks
	@echo "==> uv lock --check"; uv lock --check
	@echo "==> uv sync --locked"; uv sync --locked

setup-hooks:
	@echo "==> install .githooks/pre-commit"; install -m 755 .githooks/pre-commit .git/hooks/pre-commit

setup-node:
	@echo "==> npm ci"; npm ci --no-audit --no-fund

ci: hook-check lint format-check typecheck test test-js guardrail

# Outside CI the environment is not ready without the hook (spec 001 T015).
hook-check:
	@if [ -z "$$CI" ]; then echo "==> pre-commit hook installed"; cmp -s .githooks/pre-commit .git/hooks/pre-commit || { echo "missing or stale: run make setup-hooks"; exit 1; }; fi

lint:
	@echo "==> ruff check"; uv run --locked ruff check

format-check:
	@echo "==> ruff format --check"; uv run --locked ruff format --check

typecheck:
	@echo "==> pyright"; uv run --locked pyright

# pytest exits 5 when it collects nothing: a gate that inspected nothing is not green.
test:
	@echo "==> pytest"; uv run --locked pytest

test-js:
	@echo "==> node --test"; npm test --silent

guardrail:
	@echo "==> guardrail --all"; uv run --locked python -m alfabeta guardrail --all
