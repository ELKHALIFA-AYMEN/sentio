# schemas

Shared, versioned event contracts (Pydantic v2) used by every Python service.
See [docs/architecture.md](../../docs/architecture.md#events) for the event formats.

Python package: `sentio-schemas` (import name `sentio_schemas`).

> **Status:** package skeleton only; the event models are not implemented yet.

## Development

From the repository root:

```bash
make install            # installs this package in the shared .venv
uv run pytest libs/schemas
uv run mypy libs/schemas
```
