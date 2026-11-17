# Architecture Decision Records

| # | Title | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-monorepo-with-uv-workspace.md) | Monorepo with a uv workspace, pinned to Python 3.12 | Accepted |
| [0003](0003-event-format.md) | Event format: JSON validated by versioned Pydantic contracts | Accepted |
| [0004](0004-kafka-client-and-delivery-guarantees.md) | Kafka client and delivery guarantees: aiokafka, at least once, dead-letter topic | Accepted |

## Template

Copy this into `NNNN-short-title.md`:

```markdown
# N. Title

- **Status:** Proposed | Accepted | Superseded by NNNN | Deprecated
- **Date:** YYYY-MM-DD

## Context

What problem are we solving? What forces and constraints are at play?

## Decision

What we decided, stated clearly.

## Consequences

What becomes easier or harder. Trade-offs we accept.
```
