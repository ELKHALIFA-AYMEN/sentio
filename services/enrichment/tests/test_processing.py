import json
from datetime import datetime

import pytest
from enrichment_samples import CONVERSATION_ID, NOW, make_enricher, raw_event, raw_record, record

from sentio_enrichment import DeadLetterReason, OutputMessage, Routing, process
from sentio_enrichment.processing import MAX_ERROR_LENGTH
from sentio_schemas import Author, EnrichedMessageEvent, Enrichment, RawMessageEvent

ROUTING = Routing(output_topic="conversations.enriched", dlq_topic="conversations.dlq")


def run_process(value: bytes | None) -> OutputMessage:
    return process(record(value, offset=42, partition=2), make_enricher(), ROUTING, NOW)


def headers(message: OutputMessage) -> dict[str, str]:
    return {name: value.decode() for name, value in message.headers}


# --- Valid messages ------------------------------------------------------------------


@pytest.mark.parametrize("author", list(Author))
def test_valid_message_is_enriched_and_published_on_the_output_topic(author: Author) -> None:
    raw = raw_event(author)

    output = process(raw_record(author), make_enricher(), ROUTING, NOW)

    assert output.topic == "conversations.enriched"
    assert output.headers == ()
    enriched = EnrichedMessageEvent.model_validate_json(output.value)
    # Every raw field is kept unchanged.
    assert RawMessageEvent.model_validate(enriched.model_dump(exclude={"enrichment"})) == raw
    assert enriched.enrichment.enriched_at == NOW


def test_key_is_the_conversation_id() -> None:
    output = process(raw_record(), make_enricher(), ROUTING, NOW)

    assert output.key == str(CONVERSATION_ID).encode()


def test_accents_survive_the_round_trip() -> None:
    output = process(raw_record(), make_enricher(), ROUTING, NOW)

    assert "à Lyon" in EnrichedMessageEvent.model_validate_json(output.value).text


# --- Invalid messages go to the DLQ ----------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected_error"),
    [
        (b"not json at all", "Invalid JSON"),
        (b"\xff\xfe broken utf-8", "(event)"),
        (b"", "(event)"),
        (None, "(event)"),
        (b'{"schema_version": 1}', "event_id: Field required"),
    ],
    ids=["not-json", "not-utf8", "empty", "no-value", "missing-fields"],
)
def test_message_that_is_not_a_raw_event_goes_to_the_dlq(
    value: bytes | None, expected_error: str
) -> None:
    output = run_process(value)

    assert output.topic == "conversations.dlq"
    assert headers(output)["dlq.reason"] == DeadLetterReason.INVALID_EVENT
    assert expected_error in headers(output)["dlq.error"]


def test_raw_event_breaking_a_rule_goes_to_the_dlq() -> None:
    data = json.loads(raw_event().model_dump_json())
    data["customer"]["customer_id"] = "+33 6 12 34 56 78"  # a phone number instead of an ID

    output = run_process(json.dumps(data).encode())

    assert headers(output)["dlq.reason"] == DeadLetterReason.INVALID_EVENT
    assert "customer.customer_id" in headers(output)["dlq.error"]


def test_enriched_event_on_the_raw_topic_goes_to_the_dlq() -> None:
    already_enriched = process(raw_record(), make_enricher(), ROUTING, NOW).value

    output = run_process(already_enriched)

    assert headers(output)["dlq.reason"] == DeadLetterReason.INVALID_EVENT
    assert "enrichment" in headers(output)["dlq.error"]


class FailingEnricher:
    def enrich(self, event: RawMessageEvent, now: datetime) -> Enrichment:
        raise RuntimeError("model file missing")


class AgentPredictingEnricher:
    """Breaks the contract: predicts a sentiment for every message, agent messages included."""

    def enrich(self, event: RawMessageEvent, now: datetime) -> Enrichment:
        customer_view = raw_event(Author.CUSTOMER)
        return make_enricher().enrich(customer_view, now)


def test_enricher_error_sends_the_message_to_the_dlq() -> None:
    output = process(raw_record(), FailingEnricher(), ROUTING, NOW)

    assert output.topic == "conversations.dlq"
    assert headers(output)["dlq.reason"] == DeadLetterReason.ENRICHMENT_FAILED
    assert headers(output)["dlq.error"] == "RuntimeError: model file missing"


def test_predictions_refused_by_the_contract_send_the_message_to_the_dlq() -> None:
    output = process(raw_record(Author.AGENT), AgentPredictingEnricher(), ROUTING, NOW)

    assert headers(output)["dlq.reason"] == DeadLetterReason.ENRICHMENT_FAILED
    assert "agent messages must not have sentiment" in headers(output)["dlq.error"]


# --- What a DLQ message contains ---------------------------------------------------------


def test_dlq_message_keeps_the_original_key_and_bytes() -> None:
    original = b"\xff\xfe broken utf-8"

    output = process(record(original, key=b"k-1"), make_enricher(), ROUTING, NOW)

    assert output.key == b"k-1"
    assert output.value == original


def test_dlq_message_says_where_the_message_came_from_and_when_it_failed() -> None:
    output = run_process(b"not json")

    assert headers(output) | {"dlq.error": "..."} == {
        "dlq.reason": "invalid_event",
        "dlq.error": "...",
        "dlq.service": "enrichment",
        "dlq.source_topic": "conversations.raw",
        "dlq.source_partition": "2",
        "dlq.source_offset": "42",
        "dlq.failed_at": "2026-11-17T09:00:05+00:00",
    }


def test_long_errors_are_cut() -> None:
    data = {"schema_version": 1, **{f"unknown_{i}": i for i in range(200)}}

    output = run_process(json.dumps(data).encode())

    assert len(headers(output)["dlq.error"]) == MAX_ERROR_LENGTH
