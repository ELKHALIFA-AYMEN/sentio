# api

One image, two processes:

- **api-worker** — consumes `conversations.enriched`, stores messages in PostgreSQL, updates aggregates and
  evaluates alert rules.
- **api-server** — FastAPI REST endpoints (conversations, metrics, alerts) and a WebSocket for live updates.

> **Status:** not implemented yet.
