# infra

Local infrastructure for Sentio. The stack is described in [`compose.yaml`](../compose.yaml) at the repository
root (so that `docker compose up` works from there); this folder holds the configuration files it uses.

## Services

| Service | Image | Role | Port on this machine |
|---|---|---|---|
| `redpanda` | `redpandadata/redpanda` v26.2.7 | Kafka-compatible message broker (single node). | `localhost:19092` (Kafka) |
| `redpanda-init` | same image | One-shot job: creates the topics, then exits. | — |
| `redpanda-console` | `redpandadata/console` v3.14.0 | Web UI to browse topics and messages. | <http://localhost:8080> |
| `postgres` | `postgres` 16.16-alpine | Database. | `localhost:5432` |
| `simulator` | built from [`services/simulator`](../services/simulator) | Publishes synthetic conversations to `conversations.raw` (5 messages/s by default). | — |
| `enrichment` | built from [`services/enrichment`](../services/enrichment) | Reads `conversations.raw` (consumer group `sentio-enrichment`), publishes `conversations.enriched`, sends invalid messages to `conversations.dlq`. | — |

`make up` builds the images of the Sentio services if needed; `docker compose up -d --build` forces a rebuild.

All ports are bound to `127.0.0.1`: they are reachable from this machine only. Containers talk to each other
by service name (`redpanda:9092`, `postgres:5432`). Ports, credentials and topic settings can be overridden in a
`.env` file (see [`.env.example`](../.env.example)); every value has a default.

## Topics

Created by [`redpanda/create-topics.sh`](redpanda/create-topics.sh). The script is idempotent: existing topics
are left unchanged.

| Topic | Producer → consumer |
|---|---|
| `conversations.raw` | simulator → enrichment |
| `conversations.enriched` | enrichment → api-worker, api-server |
| `conversations.dlq` | enrichment → (inspection, replay): messages that could not be parsed or processed |

Defaults: 3 partitions, replication factor 1 (single node), 24-hour retention.
**Automatic topic creation is disabled**: producing to a misspelled topic fails instead of silently creating it.
Partition count and retention only apply when a topic is created; run `make reset` to recreate the topics.

## Healthchecks

| Service | Check | Meaning |
|---|---|---|
| `redpanda` | `rpk cluster health` reports `Healthy: true` | The broker accepts requests. |
| `postgres` | `pg_isready` | The database accepts connections. |

`redpanda-init` and `redpanda-console` only start once `redpanda` is healthy. `make up` waits for every
healthcheck to pass before returning.

## Data

Two named volumes keep the data between restarts: `sentio_redpanda-data` and `sentio_postgres-data`.
`make down` keeps them; `make reset` deletes them.

## Commands

```bash
make up      # start and wait until healthy
make ps      # container states
make logs    # follow logs
make down    # stop, keep data
make reset   # stop and delete data
```
