"""Contract of the events published on the ``conversations.raw`` topic (version 1).

One event is one message of a support conversation, exactly as the simulator produced it,
before any enrichment. See docs/adr/0003-event-format.md for the design rules.
"""

from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StringConstraints

from sentio_schemas._common import Contract, UtcDatetime

MAX_TEXT_LENGTH = 5_000
"""Upper bound on a message's text, to protect consumers from abnormally large events."""

CUSTOMER_ID_PATTERN = r"^CUST-\d{6}$"
"""Synthetic customer IDs only, e.g. ``CUST-004211``: phone numbers or e-mails never match."""


class Channel(StrEnum):
    """Where the message was exchanged."""

    CHAT = "chat"
    EMAIL = "email"
    CALL_TRANSCRIPT = "call_transcript"


class Author(StrEnum):
    """Who wrote the message."""

    CUSTOMER = "customer"
    AGENT = "agent"


class CustomerSegment(StrEnum):
    """Commercial segment of the customer."""

    PREPAID = "prepaid"
    POSTPAID = "postpaid"
    BUSINESS = "business"


class Customer(Contract):
    """Snapshot of the customer's attributes at the time of the message."""

    customer_id: Annotated[str, StringConstraints(pattern=CUSTOMER_ID_PATTERN)]
    segment: CustomerSegment
    tenure_months: Annotated[int, Field(ge=0, le=1_200)]
    monthly_revenue_eur: Annotated[Decimal, Field(ge=0, max_digits=8, decimal_places=2)]


class RawMessageEvent(Contract):
    """One message of a conversation, as published on ``conversations.raw``."""

    schema_version: Literal[1] = 1
    event_id: UUID
    conversation_id: UUID
    message_id: UUID
    sequence: Annotated[int, Field(ge=1)]
    sent_at: UtcDatetime
    channel: Channel
    author: Author
    text: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_TEXT_LENGTH)
    ]
    customer: Customer
