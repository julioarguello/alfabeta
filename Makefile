# Quality gate. Every recipe uses the project's .venv through uv.
# Node (spec 001 T004) and the guardrail (spec 001 T014) join `ci` when they exist.
.PHONY: setup-python ci lint format-check typecheck test

setup-python:
	@echo "==> uv lock --check"; uv lock --check
	@echo "==> uv sync --locked"; uv sync --locked

ci: lint format-check typecheck test

lint:
	@echo "==> ruff check"; uv run --locked ruff check

format-check:
	@echo "==> ruff format --check"; uv run --locked ruff format --check

typecheck:
	@echo "==> pyright"; uv run --locked pyright

# pytest exits 5 when it collects nothing: a gate that inspected nothing is not green.
test:
	@echo "==> pytest"; uv run --locked pytest
