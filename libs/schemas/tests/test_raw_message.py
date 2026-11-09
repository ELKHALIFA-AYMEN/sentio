import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError

from sentio_schemas import Author, Channel, CustomerSegment, RawMessageEvent


def parse(payload: dict[str, Any]) -> RawMessageEvent:
    """Validate a payload the way a Kafka consumer does: from JSON bytes."""
    return RawMessageEvent.model_validate_json(json.dumps(payload))


# --- Happy path ---------------------------------------------------------------


def test_valid_payload_is_parsed_into_typed_fields(raw_payload: dict[str, Any]) -> None:
    event = parse(raw_payload)

    assert event.schema_version == 1
    assert event.message_id == UUID("a91e3c4d-7f50-4b81-9c3d-4e5f6a7b8c03")
    assert event.sent_at == datetime(2026, 11, 9, 10, 15, 42, tzinfo=UTC)
    assert event.channel is Channel.CHAT
    assert event.author is Author.CUSTOMER
    assert event.customer.segment is CustomerSegment.POSTPAID
    assert event.customer.monthly_revenue_eur == Decimal("29.99")


def test_json_round_trip_preserves_the_event(raw_payload: dict[str, Any]) -> None:
    event = parse(raw_payload)

    assert RawMessageEvent.model_validate_json(event.model_dump_json()) == event


def test_serialised_json_matches_the_wire_format(raw_payload: dict[str, Any]) -> None:
    assert json.loads(parse(raw_payload).model_dump_json()) == raw_payload


def test_schema_version_defaults_to_1(raw_payload: dict[str, Any]) -> None:
    del raw_payload["schema_version"]

    assert parse(raw_payload).schema_version == 1


# --- Versioning and contract strictness ---------------------------------------


def test_unknown_schema_version_is_rejected(raw_payload: dict[str, Any]) -> None:
    raw_payload["schema_version"] = 2

    with pytest.raises(ValidationError, match="schema_version"):
        parse(raw_payload)


def test_unknown_field_is_rejected(raw_payload: dict[str, Any]) -> None:
    raw_payload["sentiment"] = "negative"

    with pytest.raises(ValidationError, match="sentiment"):
        parse(raw_payload)


@pytest.mark.parametrize(
    "field", ["event_id", "conversation_id", "message_id", "sent_at", "text", "customer"]
)
def test_required_field_is_enforced(raw_payload: dict[str, Any], field: str) -> None:
    del raw_payload[field]

    with pytest.raises(ValidationError, match=field):
        parse(raw_payload)


def test_types_are_not_coerced(raw_payload: dict[str, Any]) -> None:
    raw_payload["sequence"] = "3"

    with pytest.raises(ValidationError, match="sequence"):
        parse(raw_payload)


def test_event_is_immutable(raw_payload: dict[str, Any]) -> None:
    event = parse(raw_payload)

    with pytest.raises(ValidationError, match="frozen"):
        event.text = "changed"  # type: ignore[misc]


# --- Field rules ----------------------------------------------------------------


def test_invalid_uuid_is_rejected(raw_payload: dict[str, Any]) -> None:
    raw_payload["message_id"] = "not-a-uuid"

    with pytest.raises(ValidationError, match="message_id"):
        parse(raw_payload)


def test_sequence_starts_at_1(raw_payload: dict[str, Any]) -> None:
    raw_payload["sequence"] = 0

    with pytest.raises(ValidationError, match="sequence"):
        parse(raw_payload)


def test_timestamp_without_timezone_is_rejected(raw_payload: dict[str, Any]) -> None:
    raw_payload["sent_at"] = "2026-11-09T10:15:42"

    with pytest.raises(ValidationError, match="sent_at"):
        parse(raw_payload)


def test_timestamp_in_another_timezone_is_converted_to_utc(raw_payload: dict[str, Any]) -> None:
    raw_payload["sent_at"] = "2026-11-09T11:15:42+01:00"

    event = parse(raw_payload)

    assert event.sent_at == datetime(2026, 11, 9, 10, 15, 42, tzinfo=UTC)
    assert event.sent_at.tzinfo is UTC


@pytest.mark.parametrize(("field", "value"), [("channel", "sms"), ("author", "bot")])
def test_unknown_enum_value_is_rejected(
    raw_payload: dict[str, Any], field: str, value: str
) -> None:
    raw_payload[field] = value

    with pytest.raises(ValidationError, match=field):
        parse(raw_payload)


def test_text_is_stripped(raw_payload: dict[str, Any]) -> None:
    raw_payload["text"] = "   Hello   "

    assert parse(raw_payload).text == "Hello"


@pytest.mark.parametrize("text", ["", "     "])
def test_empty_text_is_rejected(raw_payload: dict[str, Any], text: str) -> None:
    raw_payload["text"] = text

    with pytest.raises(ValidationError, match="text"):
        parse(raw_payload)


def test_text_longer_than_5000_characters_is_rejected(raw_payload: dict[str, Any]) -> None:
    raw_payload["text"] = "a" * 5_001

    with pytest.raises(ValidationError, match="text"):
        parse(raw_payload)


# --- Customer -------------------------------------------------------------------


@pytest.mark.parametrize(
    "customer_id",
    [
        "+33612345678",  # phone number: personal data must never enter the system
        "jane.doe@example.com",  # e-mail address
        "CUST-42",  # wrong format
    ],
)
def test_customer_id_must_be_synthetic(raw_payload: dict[str, Any], customer_id: str) -> None:
    raw_payload["customer"]["customer_id"] = customer_id

    with pytest.raises(ValidationError, match="customer_id"):
        parse(raw_payload)


def test_revenue_accepts_a_json_number(raw_payload: dict[str, Any]) -> None:
    raw_payload["customer"]["monthly_revenue_eur"] = 29.99

    assert parse(raw_payload).customer.monthly_revenue_eur == Decimal("29.99")


@pytest.mark.parametrize("revenue", ["-1.00", "29.999"])
def test_invalid_revenue_is_rejected(raw_payload: dict[str, Any], revenue: str) -> None:
    raw_payload["customer"]["monthly_revenue_eur"] = revenue

    with pytest.raises(ValidationError, match="monthly_revenue_eur"):
        parse(raw_payload)


def test_negative_tenure_is_rejected(raw_payload: dict[str, Any]) -> None:
    raw_payload["customer"]["tenure_months"] = -1

    with pytest.raises(ValidationError, match="tenure_months"):
        parse(raw_payload)


def test_unknown_customer_segment_is_rejected(raw_payload: dict[str, Any]) -> None:
    raw_payload["customer"]["segment"] = "vip"

    with pytest.raises(ValidationError, match="segment"):
        parse(raw_payload)
