# Architecture

This document describes the target architecture of Sentio v1. It is updated as the implementation progresses;
the reasoning behind each important choice is recorded in the [ADRs](adr).

## Overview

```
simulator ──► Redpanda [conversations.raw] ──► enrichment ──► Redpanda [conversations.enriched]
                                   │                                  │
                                   └──► [conversations.dlq] ◄─────────┤ (invalid events)
                                                                      ▼
                                                    api-worker ──► PostgreSQL
                                                                      │
                                                                      ▼
                                                    api-server (REST + WebSocket)
                                                                      │
                                                                      ▼
                                                                dashboard
```

Each service has its own Dockerfile, tests and README. Services communicate only through the broker or the API.

## Services

| Service | Input | Responsibility | Output |
|---|---|---|---|
| **simulator** | — | Generates synthetic FR/EN conversations for Quillnet Mobile, an invented European telecom operator, from hand-written templates (reproducible with a seed), including incident scenarios (a network outage or a billing error causing a burst of negative messages on one topic, triggered with `SIMULATOR_SCENARIO`). Default rate: 5 messages/second, configurable. | `conversations.raw` |
| **enrichment** | `conversations.raw` | Stateless: detects the language of every message; adds sentiment, topic and churn-risk score to customer messages. Messages it cannot process go to the dead-letter topic. Language detection is in place; sentiment, topic and churn risk are still placeholders (fixed neutral values). | `conversations.enriched`, `conversations.dlq` |
| **api-worker** | `conversations.enriched` | Persists messages idempotently, updates per-minute aggregates, evaluates alert rules. | PostgreSQL rows |
| **api-server** | PostgreSQL, `conversations.enriched` | REST endpoints (conversations, metrics, alerts) and a WebSocket for live updates. | HTTP / WebSocket |
| **dashboard** | api-server | Live feed, KPIs, topic trends, alerts (UI in English). | Web UI |

`api-worker` and `api-server` are two processes built from the same `services/api` image.

## Events

- Serialised as **JSON**, validated with the Pydantic models in `libs/schemas`.
- **One event = one message** of a conversation.
- **Kafka key = `conversation_id`**, so messages of a conversation stay ordered within a partition.
- Every event carries a `schema_version`. All timestamps are ISO 8601 in UTC.
- Delivery is **at least once**; consumers must be idempotent (deduplicate on `message_id`).
  See [Delivery and dead letters](#delivery-and-dead-letters).
- Contracts are strict: unknown fields, wrong types and naive timestamps are rejected.
  See [ADR 0003](adr/0003-event-format.md) for the full rules and the versioning policy.

### `conversations.raw` — `RawMessageEvent` v1

Model: [`libs/schemas/src/sentio_schemas/raw_message.py`](../libs/schemas/src/sentio_schemas/raw_message.py).

```json
{
  "schema_version": 1,
  "event_id": "uuid",
  "conversation_id": "uuid",
  "message_id": "uuid",
  "sequence": 3,
  "sent_at": "2026-11-09T10:15:42Z",
  "channel": "chat | email | call_transcript",
  "author": "customer | agent",
  "text": "My 4G has been down for three days...",
  "customer": {
    "customer_id": "CUST-004211",
    "segment": "prepaid | postpaid | business",
    "tenure_months": 38,
    "monthly_revenue_eur": "29.99"
  }
}
```

| Field | Rule |
|---|---|
| `schema_version` | Always `1` for this contract. |
| `event_id`, `conversation_id`, `message_id` | UUIDs. `message_id` is the deduplication key. |
| `sequence` | Position of the message in its conversation, starting at 1. |
| `sent_at` | Timezone required; normalised to UTC. |
| `text` | Trimmed; 1 to 5,000 characters. |
| `customer.customer_id` | Synthetic only: `CUST-` + 6 digits. |
| `customer.tenure_months` | 0 to 1,200. |
| `customer.monthly_revenue_eur` | EUR amount ≥ 0 with at most 2 decimals, serialised as a string to stay exact. |

### `conversations.enriched` — `EnrichedMessageEvent` v1

Model: [`libs/schemas/src/sentio_schemas/enriched_message.py`](../libs/schemas/src/sentio_schemas/enriched_message.py).

All fields of the raw event (same rules), plus:

```json
{
  "enrichment": {
    "language": "fr | en | und",
    "language_confidence": 0.98,
    "sentiment": { "label": "negative | neutral | positive", "score": -0.82 },
    "topic": { "label": "billing | network | roaming | plan | porting | other", "confidence": 0.91 },
    "churn_risk": 0.74,
    "model_versions": {
      "language": "py3langid-0.4.0",
      "sentiment": "tfidf-lr-0.1.0",
      "topic": "tfidf-lr-0.1.0",
      "churn": "rules-0.1.0"
    },
    "enriched_at": "2026-11-09T10:15:42.350000Z"
  }
}
```

| Field | Rule |
|---|---|
| `language` | `fr`, `en`, or `und` (ISO 639 "undetermined") when detection fails. |
| `language_confidence`, `topic.confidence`, `churn_risk` | Between 0 and 1. |
| `sentiment.score` | Between -1 and +1. A `negative` label requires a score ≤ 0, a `positive` label a score ≥ 0. |
| `sentiment`, `topic`, `churn_risk` | Always present. **Set for customer messages, `null` for agent messages.** |
| `model_versions` | Version of each model of the pipeline (non-empty), so every prediction can be traced. |
| `enriched_at` | Timezone required; normalised to UTC. |

An enriched event is rejected by the raw contract and vice versa, so the two topics cannot be mixed up.
The enrichment service builds events with `EnrichedMessageEvent.from_raw(raw, enrichment)`.

## Delivery and dead letters

Decided in [ADR 0004](adr/0004-kafka-client-and-delivery-guarantees.md).

- Services use **aiokafka**. Producers use `acks=all` and idempotence.
- Consumers belong to a consumer group (e.g. `sentio-enrichment`) and **commit offsets by hand, after** their
  outputs have been acknowledged by the broker: a crash causes duplicates, never losses.
- A message that cannot be processed because of its own content goes to **`conversations.dlq`**, with its original
  key and bytes and these headers:

| Header | Content |
|---|---|
| `dlq.reason` | `invalid_event` (does not match the input contract) or `enrichment_failed` (the enricher failed or its predictions break the output contract). |
| `dlq.error` | Short description of the error (at most 1,000 characters). |
| `dlq.service` | Service that rejected the message (e.g. `enrichment`). |
| `dlq.source_topic`, `dlq.source_partition`, `dlq.source_offset` | Where the message was read. |
| `dlq.failed_at` | When it was rejected (ISO 8601, UTC). |

- Broker failures are not dead letters: the service exits without committing and is restarted.

## Database (PostgreSQL 16)

| Table | Purpose | Keys |
|---|---|---|
| `customers` | Latest known customer attributes. | PK `customer_id` (upsert) |
| `conversations` | One row per conversation with running stats (message count, last sentiment, max churn risk). | PK `conversation_id`, FK `customer_id` |
| `messages` | Every message with its enrichment. | PK `message_id`; indexes on `sent_at`, `(topic, sent_at)` |
| `topic_metrics_minute` | Per-minute, per-topic aggregates (`message_count`, `negative_count`, `sentiment_sum`). | PK `(bucket_start, topic)` |
| `alerts` | Raised alerts with `status` (`open` / `acknowledged`) and a `dedup_key`. | PK `id`; unique `dedup_key` among open alerts |

## Alert rules (v1)

Thresholds are configurable through environment variables.

1. **`negative_spike`** — on a topic, over the last 10 minutes, at least 20 messages and more than 40 % negative.
   Deduplicated per topic for 30 minutes.
   > **To revisit when the alert rules are built:** a fixed 40 % threshold does not work with the simulated
   > traffic, where the usual share of negative messages is already above it on some topics (about 60 % on
   > network, 55 % on porting, 50 % on billing), so the alert would fire all the time. Planned approach: compare
   > the recent negative share of a topic with its **baseline** (its usual share over a longer period) and alert
   > when it rises well above it.
2. **`high_churn_risk`** — a customer message with `churn_risk ≥ 0.8` from a `postpaid` or `business` customer.
   Deduplicated per customer for 24 hours.

Alerts can be acknowledged through the API.

## Machine learning (v1)

- **Language:** off-the-shelf detector (py3langid) restricted to French and English; `und` when a text has no
  letters or the detector is less than 70 % sure. See the [model card](../ml/language/README.md).
- **Sentiment and topic:** scikit-learn baselines (TF-IDF + logistic regression). Transformer models are planned for v2.
- **Churn risk:** transparent rule-based score (no real churn labels are available).
- All enrichers implement a common interface so a model can be replaced without touching the pipeline.
- Each model has a model card in `ml/`.
