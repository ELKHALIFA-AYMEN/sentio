# Sentio

**Real-time customer conversation intelligence.**

Support teams handle thousands of conversations a day, but they usually discover problems — a failing
offer, a network outage, a high-value customer about to leave — days later, through reports.
Sentio processes customer conversations **as a stream**: every message is enriched with machine learning
(language, sentiment, topic, churn risk), signals are aggregated in real time, and alerts appear on a live
dashboard within seconds.

The demo domain is a **fictional European telecom operator** (mobile plans, billing, roaming, network issues,
number porting). All conversations are **synthetic** — no real customer data is ever used.

> **Status:** early development. The repository skeleton is in place; services are being built step by step.

## Architecture

```
simulator ──► Redpanda [conversations.raw] ──► enrichment ──► Redpanda [conversations.enriched]
                                                                  │
                                                                  ▼
                                                api-worker ──► PostgreSQL
                                                                  │
                                                                  ▼
                                                api-server (REST + WebSocket)
                                                                  │
                                                                  ▼
                                                            dashboard
```

| Component | Role |
|---|---|
| [`services/simulator`](services/simulator) | Generates synthetic FR/EN support conversations and publishes them. |
| [`services/enrichment`](services/enrichment) | Adds language, sentiment, topic and churn-risk score to each message. |
| [`services/api`](services/api) | Persists enriched messages, computes aggregates and alerts, serves REST + WebSocket. |
| [`services/dashboard`](services/dashboard) | Live feed, KPIs, topic trends and alerts (Next.js). |
| [`libs/schemas`](libs/schemas) | Shared, versioned event contracts (Pydantic). |
| [`ml`](ml) | Training scripts and model cards. |
| [`infra`](infra) | Docker Compose and infrastructure configuration. |

See [docs/architecture.md](docs/architecture.md) for details and [docs/adr](docs/adr) for the recorded decisions.

## Tech stack

Python 3.12 (uv) · FastAPI · Pydantic v2 · SQLAlchemy 2 + Alembic · aiokafka · scikit-learn ·
PostgreSQL 16 · Redpanda · Next.js + TypeScript + Tailwind · Docker Compose · GitHub Actions

## Getting started

The goal is a one-command demo (`make up`). Setup instructions will be added as the services land.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) © Aymen Elkhalifa
