# Sentio

[![CI](https://github.com/ELKHALIFA-AYMEN/sentio/actions/workflows/ci.yml/badge.svg)](https://github.com/ELKHALIFA-AYMEN/sentio/actions/workflows/ci.yml)

**Real-time customer conversation intelligence.**

Support teams handle thousands of conversations a day, but they usually discover problems — a failing
offer, a network outage, a high-value customer about to leave — days later, through reports.
Sentio processes customer conversations **as a stream**: every message is enriched with machine learning
(language, sentiment, topic, churn risk), signals are aggregated in real time, and alerts appear on a live
dashboard within seconds.

The demo domain is **Quillnet Mobile**, an invented European telecom operator (mobile plans, billing, roaming,
network issues, number porting). All conversations are **synthetic** — no real customer data is ever used.

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

The goal is a one-command demo (`make up`). Today it starts the infrastructure (Redpanda, its web console and
PostgreSQL), the simulator, which publishes about 5 synthetic messages per second, and the enrichment service,
which detects their language and turns them into enriched messages (sentiment, topic and churn risk are
placeholders until the models land); the other Sentio
services will be added as they land.

```bash
make up        # start the local stack (requires Docker) and wait until it is healthy
make install   # Python 3.12 virtual environment with all packages (requires uv)
make check     # lint, type-check and tests
make incident SCENARIO=network_outage   # simulate an incident (or billing_error)
```

Then open the Redpanda console at <http://localhost:8080> to browse the topics.
See [infra/README.md](infra/README.md) for the services, ports and data volumes.

Prerequisites (Docker, uv, GNU make — including on Windows) are described in
[CONTRIBUTING.md](CONTRIBUTING.md#development-setup).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) © Aymen Elkhalifa
