# 4. Kafka client and delivery guarantees: aiokafka, at least once, dead-letter topic

- **Status:** Accepted
- **Date:** 2026-11-17

## Context

Every Sentio service talks to Redpanda through the Kafka protocol. We need to choose:

- a **client library** for Python services that are built on asyncio (the API will be FastAPI);
- a **delivery guarantee**: what happens to a message when a service crashes, restarts or is rebalanced;
- what to do with a message that **cannot be processed** (malformed, or rejected by a model), without
  losing it and without blocking the messages behind it.

## Decision

**Client: aiokafka.** It is asyncio-native, so a service never blocks its event loop while waiting for the
broker, and it installs as a pure Python wheel (no C library to build in Docker images). `confluent-kafka` is
faster and more complete, but its asyncio support is limited and it ships a native library; at our volume
(a few messages per second, a few thousand when catching up) speed is not the constraint. All Kafka code lives
in one small module per service, so the client can be replaced later.

**Producers** wait for the broker's acknowledgement from all replicas (`acks=all`) and are idempotent
(a retry never writes the same message twice).

**Consumers: at least once.** A service that reads a topic is a member of a **consumer group**.
Automatic offset commits are disabled; the processing loop is:

1. read a batch of messages;
2. process each one, producing exactly one output message per input (a result or a dead letter);
3. publish all outputs and **wait until the broker has acknowledged them**;
4. only then **commit** the offsets of the batch.

If the service stops anywhere before step 4, the batch is read again: a message can be **published twice**,
but it is **never lost**. A new group starts from the oldest message still kept by the topic
(`auto_offset_reset=earliest`), so nothing published before the first start is skipped.
Duplicates are handled downstream: every consumer deduplicates on `message_id` (see [ADR 0003](0003-event-format.md)).

**Dead-letter topic: `conversations.dlq`.** A message goes there when the problem belongs to the message
itself and retrying would fail the same way:

| Reason | When |
|---|---|
| `invalid_event` | The message does not match the input contract (not JSON, not UTF-8, missing or unknown fields, wrong types...). |
| `enrichment_failed` | The message is valid, but the enricher raised an error or returned predictions the output contract refuses. |

The dead letter keeps the **original key and bytes, untouched**, so it can be inspected and replayed after a fix.
Kafka headers describe the failure: `dlq.reason`, `dlq.error` (cut to 1,000 characters), `dlq.service`,
`dlq.source_topic`, `dlq.source_partition`, `dlq.source_offset`, `dlq.failed_at`. Its offset is then committed
like any other: the message is safely parked and the stream goes on.

**Infrastructure failures are not dead letters.** If the broker is unreachable, publishing fails, nothing is
committed and the service exits with an error; Docker restarts it and it resumes from the last committed offset.

## Consequences

- No message is lost on a crash, a restart or a rebalance; the price is occasional duplicates, which consumers
  must ignore. This is simpler than Kafka transactions (exactly-once), which aiokafka supports but which add
  coordination and latency for a problem that `message_id` deduplication already solves.
- One bad message never blocks a partition: it is parked in the DLQ and logged as a warning.
- A bug in an enricher sends messages to the DLQ instead of crashing the service. This keeps the pipeline
  running, but it must be watched: a growing DLQ is a signal to look at.
- One output per input keeps offset handling trivial: an offset is committed once its output is acknowledged.
