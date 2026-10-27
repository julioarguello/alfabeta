# Quality gate (spec 001 T006). Every Python recipe uses the project's .venv through uv.
# The guardrail joins `ci` with spec 001 T014; until then the gate names it as skipped.
.PHONY: setup-python setup-node ci lint format-check typecheck test test-js guardrail

setup-python:
	@echo "==> uv lock --check"; uv lock --check
	@echo "==> uv sync --locked"; uv sync --locked

setup-node:
	@echo "==> npm ci"; npm ci --no-audit --no-fund

ci: lint format-check typecheck test test-js guardrail

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
	@echo "==> guardrail: SKIPPED until spec 001 T014 adds it"
