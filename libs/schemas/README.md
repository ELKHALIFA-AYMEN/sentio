# schemas

Shared, versioned event contracts (Pydantic v2) used by every Python service.
See [docs/architecture.md](../../docs/architecture.md#events) for the event formats.

Python package: `sentio-schemas` (import name `sentio_schemas`).

| Model | Topic | Status |
|---|---|---|
| `RawMessageEvent` (v1) | `conversations.raw` | Implemented |
| `EnrichedMessageEvent` (v1) | `conversations.enriched` | Not implemented yet |

Contract rules (strict types, unknown fields rejected, UTC timestamps, exact money, versioning) are explained in
[ADR 0003](../../docs/adr/0003-event-format.md).

## Usage

```python
from sentio_schemas import RawMessageEvent

event = RawMessageEvent.model_validate_json(
    kafka_message_value
)  # raises ValidationError if invalid
payload: str = event.model_dump_json()  # back to the wire format
```

## Development

From the repository root:

```bash
make install            # installs this package in the shared .venv
uv run pytest libs/schemas
uv run mypy libs/schemas
```
