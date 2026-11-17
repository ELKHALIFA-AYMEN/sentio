"""What happens to one message: enriched, or sent to the dead-letter queue (DLQ).

Everything here is pure: no Kafka, no clock. One input record always gives exactly one output
message, so the worker can commit an input offset as soon as its output has been published.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from pydantic import ValidationError

from sentio_enrichment.enricher import Enricher
from sentio_schemas import EnrichedMessageEvent, RawMessageEvent

SERVICE_NAME = "enrichment"
MAX_ERROR_LENGTH = 1_000
"""Error descriptions are cut to this many characters to keep DLQ headers small."""


class DeadLetterReason(StrEnum):
    INVALID_EVENT = "invalid_event"
    """The message is not a valid ``RawMessageEvent``: not JSON, wrong fields, wrong types..."""
    ENRICHMENT_FAILED = "enrichment_failed"
    """The message is valid, but the enricher failed or made predictions the contract refuses."""


@dataclass(frozen=True, slots=True)
class InputRecord:
    """A message read from Kafka, with its position (topic, partition, offset)."""

    topic: str
    partition: int
    offset: int
    key: bytes | None
    value: bytes | None


@dataclass(frozen=True, slots=True)
class OutputMessage:
    """A message to publish."""

    topic: str
    key: bytes | None
    value: bytes
    headers: tuple[tuple[str, bytes], ...] = ()


@dataclass(frozen=True, slots=True)
class Routing:
    """Where results go."""

    output_topic: str
    dlq_topic: str


def process(
    record: InputRecord, enricher: Enricher, routing: Routing, now: datetime
) -> OutputMessage:
    """Enrich ``record``, or describe why it goes to the DLQ."""
    try:
        raw = RawMessageEvent.model_validate_json(record.value or b"")
    except ValidationError as error:
        return dead_letter(record, routing, DeadLetterReason.INVALID_EVENT, _describe(error), now)

    try:
        enriched = EnrichedMessageEvent.from_raw(raw, enricher.enrich(raw, now))
    except Exception as error:
        # Any failure here concerns this message only: park it in the DLQ and keep the stream
        # flowing, instead of crashing on it again and again. Broker failures happen elsewhere.
        return dead_letter(
            record, routing, DeadLetterReason.ENRICHMENT_FAILED, _describe(error), now
        )

    return OutputMessage(
        topic=routing.output_topic,
        # Same key as the raw event: messages of a conversation stay in order.
        key=str(enriched.conversation_id).encode(),
        value=enriched.model_dump_json().encode(),
    )


def dead_letter(
    record: InputRecord,
    routing: Routing,
    reason: DeadLetterReason,
    error: str,
    now: datetime,
) -> OutputMessage:
    """The DLQ message for ``record``: its original key and bytes, untouched, plus headers
    explaining what went wrong and where the message came from, so it can be inspected and replayed.
    """
    headers = {
        "dlq.reason": reason.value,
        "dlq.error": error[:MAX_ERROR_LENGTH],
        "dlq.service": SERVICE_NAME,
        "dlq.source_topic": record.topic,
        "dlq.source_partition": str(record.partition),
        "dlq.source_offset": str(record.offset),
        "dlq.failed_at": now.isoformat(),
    }
    return OutputMessage(
        topic=routing.dlq_topic,
        key=record.key,
        value=record.value or b"",
        headers=tuple((name, value.encode()) for name, value in headers.items()),
    )


def _describe(error: Exception) -> str:
    if isinstance(error, ValidationError):
        # One short line per problem, e.g. "customer.customer_id: String should match pattern".
        problems = [
            f"{'.'.join(str(part) for part in item['loc']) or '(event)'}: {item['msg']}"
            for item in error.errors()
        ]
        return "; ".join(problems)
    return f"{type(error).__name__}: {error}"
