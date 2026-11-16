# simulator

Generates synthetic customer support conversations (French and English) for **Quillnet Mobile**, an invented
European telecom operator, and publishes each message to the `conversations.raw` topic.

No real data is ever used: the texts come from hand-written templates, customer identifiers are random
`CUST-` numbers, and the operator, its plans and prices are made up.

## Design: a pure core and a thin I/O layer

| Module | Role | Side effects |
|---|---|---|
| [`generator.py`](src/sentio_simulator/generator.py) | Builds one conversation from a seed. | none |
| [`stream.py`](src/sentio_simulator/stream.py) | Interleaves conversations into a time-ordered stream at the target rate. | none |
| [`runner.py`](src/sentio_simulator/runner.py) | Waits until each message is due, publishes it, stops when asked. | waits |
| [`publisher.py`](src/sentio_simulator/publisher.py) | Sends events to Kafka (the only module that imports `aiokafka`). | network |
| [`config.py`](src/sentio_simulator/config.py), [`logging_json.py`](src/sentio_simulator/logging_json.py) | Settings from environment variables, JSON logs. | — |
| [`__main__.py`](src/sentio_simulator/__main__.py) | Wires everything: reads the environment and the clock, picks a seed, handles signals. | all |

## How a conversation is built

`generate_conversation(seed, started_at, config)`:

1. **Draw the conversation's profile**: language (50 % French by default), topic (billing, network, plan,
   roaming, porting, other), the customer's mood (negative / neutral / positive, with odds that depend on the
   topic: network issues are more often negative than plan questions), and the channel (chat, e-mail, call).
2. **Draw the customer**: segment (prepaid / postpaid / business), one of the segment's plans
   ([`catalog.py`](src/sentio_simulator/catalog.py)), whose price becomes the monthly revenue, and a tenure.
3. **Pick the sentences** from [`templates.py`](src/sentio_simulator/templates.py):
   a customer opener (topic + language + mood), an agent reply (topic + language + mood), then, most of
   the time, a customer follow-up (language + mood) and an agent closing (language + mood).
   A conversation has 2 to 4 messages. The agent adapts to the customer's mood: apologies and an action for an
   unhappy customer, information for a neutral one, thanks for a happy one. Agents only mention details they
   know (the customer's plan and price, the city the customer complained about), and French sentences avoid
   gendered adjectives.
4. **Fill the placeholders** (`{plan}`, `{price}`, `{amount}`, `{city}`, `{country}`, `{days}`, `{operator}`),
   with amounts written the local way (`€29.99` / `29,99 €`).
5. **Add timestamps**: the first message is sent at `started_at`, each next one after a delay that depends on
   the channel (15–90 s in a chat, 5–40 s in a call, 2–20 min by e-mail, compressed from hours for the demo).
6. **Build the events** as `RawMessageEvent` objects, so every message is checked against the contract.

The result also carries the **ground truth** (intended language, topic and mood). It is not part of the
published events, but it will be used to evaluate the enrichment models.

## The live stream

`live_message_stream(seed, now, messages_per_second)` starts conversations at random moments (a Poisson
process) at the rate needed for the target number of messages per second, and interleaves their messages
by time. The simulation starts one hour (the longest possible conversation) before `now` and skips earlier
messages, so the stream is at full speed immediately; a few conversations are joined midway.

## Publishing

- **Key = `conversation_id`**: Kafka sends all messages with the same key to the same partition, so the
  messages of a conversation are stored and consumed in order.
- **Value** = the event serialised by the contract (`model_dump_json()`), UTF-8 encoded.
- The producer waits for the broker's confirmation (`acks=all`) and is idempotent (retries cannot create
  duplicates).
- **Clean shutdown**: on `SIGTERM` (`docker compose stop`) or `SIGINT` (Ctrl+C), the service stops waiting,
  flushes the messages still buffered, logs `simulator stopped` with the number of messages sent, and exits
  with code 0.
- If Redpanda is unreachable, the service logs the error and exits with code 1; Docker restarts it.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:19092` | Broker address (`redpanda:9092` inside Docker). |
| `SIMULATOR_TOPIC` | `conversations.raw` | Topic to publish to. |
| `SIMULATOR_MESSAGES_PER_SECOND` | `5` | Average rate, between 0 and 1000. |
| `SIMULATOR_FRENCH_SHARE` | `0.5` | Share of conversations in French. |
| `SIMULATOR_SEED` | *(empty)* | Integer seed for a reproducible stream; empty = new seed at each start (logged). |
| `LOG_LEVEL` | `INFO` | `DEBUG` also logs every published message. |

Logs are JSON, one object per line. Every 10 seconds the service logs how many messages it published.

## Running

With the whole stack: `make up` (the simulator starts automatically), then follow it with
`docker compose logs -f simulator`.

Outside Docker, against the Redpanda started by `make up`:

```bash
uv run python -m sentio_simulator
```

## Development

From the repository root:

```bash
uv run python -m pytest services/simulator
uv run python -m mypy services/simulator
docker build -f services/simulator/Dockerfile -t sentio/simulator:dev .
```
