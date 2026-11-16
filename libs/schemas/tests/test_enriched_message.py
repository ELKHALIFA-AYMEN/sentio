import json
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from sentio_schemas import (
    Author,
    EnrichedMessageEvent,
    Enrichment,
    Language,
    RawMessageEvent,
    SentimentLabel,
    TopicLabel,
)


def parse(payload: dict[str, Any]) -> EnrichedMessageEvent:
    """Validate a payload the way a Kafka consumer does: from JSON bytes."""
    return EnrichedMessageEvent.model_validate_json(json.dumps(payload))


# --- Happy path ---------------------------------------------------------------


def test_customer_message_is_parsed_into_typed_fields(enriched_payload: dict[str, Any]) -> None:
    enrichment = parse(enriched_payload).enrichment

    assert enrichment.language is Language.EN
    assert enrichment.language_confidence == 0.98
    assert enrichment.sentiment is not None
    assert enrichment.sentiment.label is SentimentLabel.NEGATIVE
    assert enrichment.sentiment.score == -0.82
    assert enrichment.topic is not None
    assert enrichment.topic.label is TopicLabel.NETWORK
    assert enrichment.churn_risk == 0.74
    assert enrichment.model_versions.sentiment == "tfidf-lr-0.1.0"
    assert enrichment.enriched_at == datetime(2026, 11, 9, 10, 15, 42, 350_000, tzinfo=UTC)


def test_agent_message_has_only_a_language(agent_enriched_payload: dict[str, Any]) -> None:
    event = parse(agent_enriched_payload)

    assert event.author is Author.AGENT
    assert event.enrichment.language is Language.EN
    assert event.enrichment.sentiment is None
    assert event.enrichment.topic is None
    assert event.enrichment.churn_risk is None


@pytest.mark.parametrize("fixture", ["enriched_payload", "agent_enriched_payload"])
def test_serialised_json_matches_the_wire_format(
    request: pytest.FixtureRequest, fixture: str
) -> None:
    payload: dict[str, Any] = request.getfixturevalue(fixture)

    assert json.loads(parse(payload).model_dump_json()) == payload


def test_from_raw_keeps_every_raw_field(enriched_payload: dict[str, Any]) -> None:
    enrichment_json = json.dumps(enriched_payload.pop("enrichment"))
    raw = RawMessageEvent.model_validate_json(json.dumps(enriched_payload))
    enrichment = Enrichment.model_validate_json(enrichment_json)

    event = EnrichedMessageEvent.from_raw(raw, enrichment)

    assert event.model_dump(exclude={"enrichment"}) == raw.model_dump()
    assert event.enrichment == enrichment


def test_undetermined_language_is_accepted(agent_enriched_payload: dict[str, Any]) -> None:
    agent_enriched_payload["enrichment"]["language"] = "und"

    assert parse(agent_enriched_payload).enrichment.language is Language.UNDETERMINED


def test_neutral_sentiment_accepts_any_score(enriched_payload: dict[str, Any]) -> None:
    enriched_payload["enrichment"]["sentiment"] = {"label": "neutral", "score": 0.3}

    assert parse(enriched_payload).enrichment.sentiment is not None


# --- The two topics cannot be mixed up ------------------------------------------


def test_raw_event_is_not_a_valid_enriched_event(raw_payload: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="enrichment"):
        parse(raw_payload)


def test_enriched_event_is_not_a_valid_raw_event(enriched_payload: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="enrichment"):
        RawMessageEvent.model_validate_json(json.dumps(enriched_payload))


def test_raw_field_rules_still_apply(enriched_payload: dict[str, Any]) -> None:
    enriched_payload["customer"]["customer_id"] = "+33612345678"

    with pytest.raises(ValidationError, match="customer_id"):
        parse(enriched_payload)


# --- Predictions depend on the author --------------------------------------------


@pytest.mark.parametrize("field", ["sentiment", "topic", "churn_risk"])
def test_customer_message_requires_every_prediction(
    enriched_payload: dict[str, Any], field: str
) -> None:
    enriched_payload["enrichment"][field] = None

    with pytest.raises(ValidationError, match=f"customer messages require {field}"):
        parse(enriched_payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sentiment", {"label": "neutral", "score": 0.0}),
        ("topic", {"label": "other", "confidence": 0.5}),
        ("churn_risk", 0.1),
    ],
)
def test_agent_message_must_not_have_predictions(
    agent_enriched_payload: dict[str, Any], field: str, value: Any
) -> None:
    agent_enriched_payload["enrichment"][field] = value

    with pytest.raises(ValidationError, match=f"agent messages must not have {field}"):
        parse(agent_enriched_payload)


@pytest.mark.parametrize("field", ["sentiment", "topic", "churn_risk"])
def test_prediction_fields_cannot_be_omitted(
    agent_enriched_payload: dict[str, Any], field: str
) -> None:
    del agent_enriched_payload["enrichment"][field]

    with pytest.raises(ValidationError, match=field):
        parse(agent_enriched_payload)


# --- Value rules --------------------------------------------------------------


def test_unsupported_language_is_rejected(enriched_payload: dict[str, Any]) -> None:
    enriched_payload["enrichment"]["language"] = "de"

    with pytest.raises(ValidationError, match="language"):
        parse(enriched_payload)


@pytest.mark.parametrize("value", [-0.01, 1.01])
@pytest.mark.parametrize(
    "path", [("language_confidence",), ("churn_risk",), ("topic", "confidence")]
)
def test_probabilities_must_be_between_0_and_1(
    enriched_payload: dict[str, Any], path: tuple[str, ...], value: float
) -> None:
    target = enriched_payload["enrichment"]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    with pytest.raises(ValidationError, match=path[-1]):
        parse(enriched_payload)


@pytest.mark.parametrize("score", [-1.01, 1.01])
def test_sentiment_score_must_be_between_minus_1_and_1(
    enriched_payload: dict[str, Any], score: float
) -> None:
    enriched_payload["enrichment"]["sentiment"] = {"label": "neutral", "score": score}

    with pytest.raises(ValidationError, match="score"):
        parse(enriched_payload)


@pytest.mark.parametrize(("label", "score"), [("negative", 0.5), ("positive", -0.5)])
def test_sentiment_score_must_agree_with_label(
    enriched_payload: dict[str, Any], label: str, score: float
) -> None:
    enriched_payload["enrichment"]["sentiment"] = {"label": label, "score": score}

    with pytest.raises(ValidationError, match="cannot have a"):
        parse(enriched_payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sentiment", {"label": "angry", "score": -0.5}),
        ("topic", {"label": "weather", "confidence": 0.5}),
    ],
)
def test_unknown_label_is_rejected(
    enriched_payload: dict[str, Any], field: str, value: Any
) -> None:
    enriched_payload["enrichment"][field] = value

    with pytest.raises(ValidationError, match="label"):
        parse(enriched_payload)


@pytest.mark.parametrize("model", ["language", "sentiment", "topic", "churn"])
def test_every_model_version_is_required(enriched_payload: dict[str, Any], model: str) -> None:
    del enriched_payload["enrichment"]["model_versions"][model]

    with pytest.raises(ValidationError, match=model):
        parse(enriched_payload)


def test_empty_model_version_is_rejected(enriched_payload: dict[str, Any]) -> None:
    enriched_payload["enrichment"]["model_versions"]["topic"] = ""

    with pytest.raises(ValidationError, match="topic"):
        parse(enriched_payload)


def test_enriched_at_without_timezone_is_rejected(enriched_payload: dict[str, Any]) -> None:
    enriched_payload["enrichment"]["enriched_at"] = "2026-11-09T10:15:42"

    with pytest.raises(ValidationError, match="enriched_at"):
        parse(enriched_payload)


def test_enriched_at_is_converted_to_utc(enriched_payload: dict[str, Any]) -> None:
    enriched_payload["enrichment"]["enriched_at"] = "2026-11-09T11:15:42+01:00"

    enriched_at = parse(enriched_payload).enrichment.enriched_at

    assert enriched_at == datetime(2026, 11, 9, 10, 15, 42, tzinfo=UTC)
    assert enriched_at.tzinfo is UTC


def test_unknown_enrichment_field_is_rejected(enriched_payload: dict[str, Any]) -> None:
    enriched_payload["enrichment"]["summary"] = "Customer is angry."

    with pytest.raises(ValidationError, match="summary"):
        parse(enriched_payload)


def test_event_is_immutable(enriched_payload: dict[str, Any]) -> None:
    event = parse(enriched_payload)

    with pytest.raises(ValidationError, match="frozen"):
        event.enrichment.churn_risk = 0.0  # type: ignore[misc]
