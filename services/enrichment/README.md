# enrichment

Consumes `conversations.raw`, adds predictions to every message and publishes the result to
`conversations.enriched`. Messages that cannot be processed go to the dead-letter topic `conversations.dlq`.

> **Status:** the pipeline runs end to end with a **placeholder enricher**: every message gets the same neutral
> predictions (language `und`, sentiment `neutral`, topic `other`, churn risk 0, model version
> `placeholder-0.1.0`). Language detection, sentiment, topic and churn-risk models replace it in the next steps.

## Design: a pure core and a thin I/O layer

| Module | Role | Side effects |
|---|---|---|
| [`enricher.py`](src/sentio_enrichment/enricher.py) | The `Enricher` interface and the placeholder implementation. | none |
| [`processing.py`](src/sentio_enrichment/processing.py) | One input record → one output message: the enriched event, or a dead letter. | none |
| [`worker.py`](src/sentio_enrichment/worker.py) | The loop: read a batch, process, publish, commit. Stops cleanly when asked. | through `Source` / `Sink` |
| [`kafka.py`](src/sentio_enrichment/kafka.py) | Kafka consumer and producer (the only module that imports `aiokafka`). | network |
| [`config.py`](src/sentio_enrichment/config.py), [`logging_json.py`](src/sentio_enrichment/logging_json.py) | Settings from environment variables, JSON logs. | — |
| [`__main__.py`](src/sentio_enrichment/__main__.py) | Wires everything, handles signals. | all |

The worker only knows two small interfaces, `Source` (poll, commit) and `Sink` (send and wait), so tests run it
against an in-memory fake broker.

## Reading: consumer group, offsets, commits

- The service reads `conversations.raw` as a member of the consumer group **`sentio-enrichment`**.
  The topic has 3 partitions; Redpanda assigns them to the group's members. With one instance, it reads all 3;
  a second instance would take over some of them (`docker compose up -d --scale enrichment=2`).
- The **offset** is the position of a message in its partition. The group stores, per partition, the offset of
  the next message to read: this is the **commit**.
- Offsets are committed **by the service, after** the results of a batch have been acknowledged by the broker,
  never before (automatic commits are disabled). See [ADR 0004](../../docs/adr/0004-kafka-client-and-delivery-guarantees.md).
- On the very first start the group has no committed offset: it starts from the oldest message kept by the topic
  (24 hours by default), so the first run catches up on the backlog — several thousand messages per second.

## Delivery: nothing lost, duplicates possible

| What happens | Result |
|---|---|
| Normal batch | Outputs published and acknowledged, then offsets committed. |
| Service stopped (`docker compose stop`, Ctrl+C) | The current batch is finished and committed, then the service exits. |
| Crash or broker down before the commit | Nothing is committed: the batch is read again after the restart. Its messages may be published **twice**, never lost. |
| Rebalance during a batch (an instance joins or leaves) | The commit is refused; the new owner of the partition reads the batch again (duplicates). |

Output messages keep the key of the raw event (`conversation_id`), so a conversation stays in order.
Consumers of `conversations.enriched` deduplicate on `message_id`.

## Dead-letter queue (`conversations.dlq`)

A message goes to the DLQ when the problem is in the message itself, so retrying would fail again:

| `dlq.reason` | When |
|---|---|
| `invalid_event` | Not a valid `RawMessageEvent`: not JSON, not UTF-8, empty, missing or unknown fields, wrong values. |
| `enrichment_failed` | Valid message, but the enricher raised an error or returned predictions the enriched contract refuses. |

The DLQ message keeps the **original key and bytes** and adds headers: `dlq.reason`, `dlq.error`,
`dlq.service`, `dlq.source_topic`, `dlq.source_partition`, `dlq.source_offset`, `dlq.failed_at`.
The service logs a warning for each one, then moves on. Broker failures are **not** sent to the DLQ: the service
stops and Docker restarts it.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:19092` | Broker address (`redpanda:9092` inside Docker). |
| `ENRICHMENT_INPUT_TOPIC` | `conversations.raw` | Topic to read. |
| `ENRICHMENT_OUTPUT_TOPIC` | `conversations.enriched` | Topic for enriched messages. |
| `ENRICHMENT_DLQ_TOPIC` | `conversations.dlq` | Topic for messages that cannot be processed. |
| `ENRICHMENT_GROUP_ID` | `sentio-enrichment` | Consumer group. |
| `LOG_LEVEL` | `INFO` | Log level. |

The three topics must be different. Logs are JSON, one object per line; every 10 seconds the service logs how many
messages it processed, enriched and sent to the DLQ.

## Running and checking the flow

With the whole stack: `make up`, then `docker compose logs -f enrichment`.

In the Redpanda console (<http://localhost:8080>):

- **Topics → `conversations.enriched`**: the enriched messages, each with an `enrichment` block.
- **Consumer Groups → `sentio-enrichment`**: the committed offset and the **lag** (messages not yet processed)
  of each partition. A lag that stays close to 0 means the service keeps up.
- **Topics → `conversations.dlq`**: dead letters; open one to see its headers.

To send an invalid message on purpose and watch it reach the DLQ:

```bash
echo 'this is not json' | docker compose exec -T redpanda rpk topic produce conversations.raw -k test
```

Outside Docker, against the Redpanda started by `make up`: `uv run python -m sentio_enrichment`.

## Development

From the repository root:

```bash
uv run python -m pytest services/enrichment
uv run python -m mypy services/enrichment
docker build -f services/enrichment/Dockerfile -t sentio/enrichment:dev .
```
