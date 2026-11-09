# Developer commands. Recipes are kept to plain commands so they work with both
# a POSIX shell (Linux, macOS, CI) and cmd.exe (GNU make on Windows).

# Python packages type-checked one by one (each has its own tests/ folder).
PY_PACKAGES := libs/schemas

.DEFAULT_GOAL := help
.PHONY: help install lint format typecheck test check

help: ## Show available commands
	@echo Available commands:
	@echo   make install    - create .venv with Python 3.12 and install the locked dependencies
	@echo   make lint       - ruff lint + format check + mypy --strict
	@echo   make format     - auto-fix lint issues and format the code
	@echo   make typecheck  - mypy --strict on every Python package
	@echo   make test       - run all tests
	@echo   make check      - lint + test (what CI runs)

install: ## Create the virtual environment and install all workspace packages
	uv sync --all-packages --locked

lint: ## Lint, check formatting and type-check
	uv run ruff check .
	uv run ruff format --check .
	$(MAKE) typecheck

format: ## Auto-fix and format
	uv run ruff check --fix .
	uv run ruff format .

typecheck: ## mypy --strict, one package at a time
	$(foreach pkg,$(PY_PACKAGES),uv run mypy $(pkg) &&) echo mypy: all packages OK

test: ## Run all tests
	uv run pytest

check: lint test ## Everything CI runs
