"""Hand-built events for the tests (the enrichment service does not depend on the simulator)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sentio_enrichment import InputRecord
from sentio_schemas import Author, Channel, Customer, CustomerSegment, RawMessageEvent

NOW = datetime(2026, 11, 17, 9, 0, 5, tzinfo=UTC)
CONVERSATION_ID = UUID("6f1c2a0e-3b4d-4e5f-8a9b-0c1d2e3f4a5b")


def raw_event(author: Author = Author.CUSTOMER, sequence: int = 1) -> RawMessageEvent:
    return RawMessageEvent(
        event_id=UUID(int=sequence, version=4),
        conversation_id=CONVERSATION_ID,
        message_id=UUID(int=1_000 + sequence, version=4),
        sequence=sequence,
        sent_at=datetime(2026, 11, 17, 9, 0, tzinfo=UTC),
        channel=Channel.CHAT,
        author=author,
        text="Je n'ai plus de 4G à Lyon depuis trois jours.",
        customer=Customer(
            customer_id="CUST-004211",
            segment=CustomerSegment.POSTPAID,
            tenure_months=38,
            monthly_revenue_eur=Decimal("29.99"),
        ),
    )


def record(
    value: bytes | None,
    offset: int = 0,
    partition: int = 0,
    key: bytes | None = b"key",
    topic: str = "conversations.raw",
) -> InputRecord:
    return InputRecord(topic=topic, partition=partition, offset=offset, key=key, value=value)


def raw_record(
    author: Author = Author.CUSTOMER, offset: int = 0, partition: int = 0
) -> InputRecord:
    event = raw_event(author, sequence=offset + 1)
    return record(
        event.model_dump_json().encode(),
        offset=offset,
        partition=partition,
        key=str(event.conversation_id).encode(),
    )
