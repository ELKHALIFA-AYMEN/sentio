# 3. Event format: JSON validated by versioned Pydantic contracts

- **Status:** Accepted
- **Date:** 2026-11-09

## Context

Services exchange events through Redpanda. Producer and consumers are separate processes, possibly running
different code versions for a while. We need a format that is:

- easy to read and debug (in the Redpanda console, in logs, in tests);
- validated at both ends, so a malformed event is detected at the boundary instead of deep inside a service;
- able to evolve without silently breaking consumers;
- safe with respect to data protection: only synthetic data may ever enter the system.

## Decision

**Encoding.** Events are UTF-8 **JSON** objects. Binary formats (Avro, Protobuf) and a schema registry are
not needed at our volume and would make debugging harder; they can be revisited later.

**Contracts.** Each event type is a Pydantic v2 model in `libs/schemas`, shared by producers and consumers.
Producers serialise with `model_dump_json()`; consumers parse with `model_validate_json()`.
All contract models are:

- `strict=True` — no silent type coercion (the string `"3"` is not accepted as the integer `3`);
- `extra="forbid"` — unknown fields are rejected, which catches typos and undeclared changes;
- `frozen=True` — events are facts: once parsed they cannot be modified.

**Granularity and keys.** One event is **one message** of a conversation. The Kafka message key is the
`conversation_id`, so all messages of a conversation land in the same partition and keep their order.

**Identifiers.** `event_id`, `conversation_id` and `message_id` are UUIDs. `message_id` is the deduplication key:
delivery is at least once, so consumers must ignore a `message_id` they have already processed.

**Time.** Timestamps must carry a timezone (naive timestamps are rejected) and are normalised to **UTC**.

**Money.** Amounts are `Decimal` with at most 2 decimal places, never floats (floats cannot represent `0.10`
exactly). They are serialised as JSON **strings** (`"29.99"`) to stay exact; numbers are accepted on input.
The currency is part of the field name (`monthly_revenue_eur`).

**Data protection.** Customer identifiers must match `CUST-` followed by 6 digits, so a phone number or e-mail
address can never be used as an identifier. Message text is limited to 5,000 characters.

**Versioning.** Every event has an integer `schema_version` (a `Literal`, currently `1`).

- Because unknown fields are rejected, **any** change to a contract (even adding an optional field) is made
  in the same change as the update of every producer and consumer in this monorepo, and is deployed together.
- A change that existing data cannot satisfy (renaming, removing, changing a type or meaning) creates a new
  version: a new model with `schema_version: Literal[2]`, published on a new topic (e.g. `conversations.raw.v2`)
  while consumers migrate.

## Consequences

- Invalid events fail fast at the service boundary with a precise error message; consumers can route them to
  the dead-letter topic instead of crashing.
- Contracts are plain Python code: they are type-checked, tested and reviewed like the rest of the code.
- The strict `extra="forbid"` rule trades some flexibility for safety. It suits a monorepo where all services are
  released together; it would need to be relaxed if independent teams released services on their own schedule.
- The dashboard (TypeScript) cannot import Pydantic models; it will receive types generated from the API's
  OpenAPI schema instead.
