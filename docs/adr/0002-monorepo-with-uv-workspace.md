# 2. Monorepo with a uv workspace, pinned to Python 3.12

- **Status:** Accepted
- **Date:** 2026-11-09

## Context

Sentio has several Python services (simulator, enrichment, api) and one shared library (`libs/schemas`)
that holds the event contracts. We need:

- every service to use the **same version** of the shared contracts, without publishing them to a package index;
- one consistent set of quality tools (ruff, mypy, pytest) and configuration;
- reproducible installs on Windows, Linux and CI;
- one Python version everywhere, even though contributors may have a newer Python installed.

## Decision

- The repository is a **monorepo** managed as a **[uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/)**.
  The root `pyproject.toml` is a virtual root: it declares the workspace members, the shared dev tools
  (dependency group `dev`) and the ruff / mypy / pytest configuration. It is not a package itself.
- Each Python service and library is a **workspace member** with its own `pyproject.toml`, `src/` layout and `tests/`.
  Members are listed explicitly in the root `pyproject.toml` and added as they are created.
- Services depend on `sentio-schemas` as a workspace dependency (resolved from `libs/schemas`).
  The library is shared **at build time only**; services never call each other's code at runtime.
- A **single `uv.lock`** at the root is committed, so every environment installs exactly the same versions.
- Python is pinned to **3.12**: `.python-version` contains `3.12` and every member declares
  `requires-python = ">=3.12,<3.13"`. uv downloads or selects a 3.12 interpreter even when a newer one
  is the system default.
- mypy runs in `--strict` mode on all code, one package at a time (so each package's `tests/` folder can
  use the same file names). pytest uses `--import-mode=importlib` for the same reason.
- A `Makefile` provides the common entry points (`make install`, `make lint`, `make test`). Recipes are plain
  commands so they work both in a POSIX shell and in `cmd.exe` (GNU make on Windows).

## Consequences

- One `uv sync --all-packages` installs everything; one lockfile to review.
- A change to the event contracts and the services using them can land in the same commit.
- Docker images of the services must be built with the **repository root** as build context, so they can
  include `libs/schemas`.
- All members must agree on dependency versions (single resolution). This is acceptable for a project of this size.
- Windows contributors must install GNU make (documented in `CONTRIBUTING.md`).
