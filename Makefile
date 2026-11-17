# Developer commands. Recipes are kept to plain commands so they work with both
# a POSIX shell (Linux, macOS, CI) and cmd.exe (GNU make on Windows).

# Python packages type-checked one by one (each has its own tests/ folder).
PY_PACKAGES := libs/schemas services/simulator services/enrichment

.DEFAULT_GOAL := help
.PHONY: help install lint format typecheck test check up down ps logs reset incident

help: ## Show available commands
	@echo Available commands:
	@echo   make install    - create .venv with Python 3.12 and install the locked dependencies
	@echo   make lint       - ruff lint + format check + mypy --strict
	@echo   make format     - auto-fix lint issues and format the code
	@echo   make typecheck  - mypy --strict on every Python package
	@echo   make test       - run all tests
	@echo   make check      - lint + test (what CI runs)
	@echo   make up         - start the local stack and wait until it is healthy
	@echo   make ps         - show the state of each container
	@echo   make logs       - follow the logs of all containers (Ctrl+C to stop)
	@echo   make down       - stop the stack, keep the data
	@echo   make reset      - stop the stack and DELETE its data (topics, database)
	@echo   make incident SCENARIO=network_outage - restart the simulator with an incident
	@echo                   (network_outage or billing_error; without SCENARIO: back to normal)

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
	$(foreach pkg,$(PY_PACKAGES),uv run python -m mypy $(pkg) &&) echo mypy: all packages OK

test: ## Run all tests
	uv run python -m pytest

check: lint test ## Everything CI runs

up: ## Start the local stack (compose.yaml) and wait for the healthchecks
	docker compose up -d --wait

ps: ## Show container states
	docker compose ps -a

logs: ## Follow container logs
	docker compose logs -f

down: ## Stop the stack, keep the volumes
	docker compose down

reset: ## Stop the stack and delete its volumes
	docker compose down -v

# The variable is exported to docker compose for this target only, which works the same way in a
# POSIX shell and in cmd.exe. It takes precedence over a value in .env.
incident: export SIMULATOR_SCENARIO = $(SCENARIO)
incident: ## Restart the simulator with an incident scenario (SCENARIO=network_outage|billing_error)
	docker compose up -d --wait simulator
