# Contributing to Sentio

Thanks for your interest! This document describes how the project is built and what every change must respect.

## Development setup

### Prerequisites

| Tool | Why | Install |
|---|---|---|
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Python versions, virtual environment, dependencies | see link |
| GNU make | Common commands (`make lint`, `make test`, …) | see below |

You do **not** need to install Python 3.12 yourself: uv selects it (or downloads it) automatically,
even if your system has a newer Python. The version is pinned in `.python-version`.

#### Installing make on Windows

In PowerShell:

```powershell
winget install --id ezwinports.make --exact --source winget
```

Then **close and reopen** your terminal (and VS Code) so the updated `PATH` is picked up, and check:

```powershell
make --version
```

On macOS, `make` comes with the Xcode command line tools (`xcode-select --install`).
On Debian/Ubuntu: `sudo apt install make`.

### First run

```bash
make install   # creates .venv with Python 3.12 and installs all packages
make check     # lint + type-check + tests
```

Run `make` alone to list all commands.

### Repository layout

The Python code is a [uv workspace](docs/adr/0002-monorepo-with-uv-workspace.md): the root `pyproject.toml`
holds the shared tool configuration, and each service or library under `services/` and `libs/` is a workspace
member with its own `pyproject.toml`, `src/` and `tests/`. A new member must be added to the `members` list in
the root `pyproject.toml` and to `PY_PACKAGES` in the `Makefile`.

## Workflow

1. **Plan before code.** For any non-trivial change, open an issue or a short design note first.
2. **Small steps.** One feature per change. Every change leaves the project in a working state.
3. **Tests come with the code.** Every service has unit tests (pytest for Python, vitest for TypeScript).
4. **Docs follow code.** If behaviour changes, update the relevant README or document in the same change.
5. **Decisions are recorded.** Important technical choices get an ADR in [docs/adr](docs/adr).

## Quality gates

| Language | Lint / format | Types | Tests |
|---|---|---|---|
| Python | `ruff check`, `ruff format` | `mypy --strict` | `pytest` |
| TypeScript | `eslint` | `tsc --noEmit` (no `any`) | `vitest` |

All gates run in CI and must pass before merging.

## Conventions

- **Language:** code, comments, commit messages and documentation are written in English.
- **Configuration** comes from environment variables, documented in `.env.example`. Never commit secrets.
- **Logging** is structured (JSON) in every service.
- **Services are independent:** they communicate only through the message broker or the API.
  Shared event contracts live in [`libs/schemas`](libs/schemas).

## Commit messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(simulator): add incident scenarios
fix(api): ignore duplicate messages on replay
docs: describe alert rules
```

Common types: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `ci`. Use the service name as scope when relevant.

## Data & ethics

- Only **synthetic** conversations. Never use real conversations, names, phone numbers or customer identifiers.
- Public datasets may be used for model training only if they have an open licence and contain no personal data.
- Every model has a model card in [`ml/`](ml) describing its data (source and licence), metrics and limits.
