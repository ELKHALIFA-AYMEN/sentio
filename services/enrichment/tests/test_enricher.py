from enrichment_samples import NOW, raw_event

from sentio_enrichment import PlaceholderEnricher
from sentio_schemas import Author, EnrichedMessageEvent, Language, SentimentLabel, TopicLabel


def test_customer_message_gets_neutral_placeholder_predictions() -> None:
    enrichment = PlaceholderEnricher().enrich(raw_event(Author.CUSTOMER), NOW)

    assert enrichment.language is Language.UNDETERMINED
    assert enrichment.language_confidence == 0.0
    assert enrichment.sentiment is not None
    assert enrichment.sentiment.label is SentimentLabel.NEUTRAL
    assert enrichment.topic is not None
    assert enrichment.topic.label is TopicLabel.OTHER
    assert enrichment.churn_risk == 0.0


def test_agent_message_gets_no_predictions() -> None:
    enrichment = PlaceholderEnricher().enrich(raw_event(Author.AGENT), NOW)

    assert enrichment.sentiment is None
    assert enrichment.topic is None
    assert enrichment.churn_risk is None


def test_placeholder_is_recognisable_from_the_model_versions() -> None:
    versions = PlaceholderEnricher().enrich(raw_event(), NOW).model_versions

    assert set(versions.model_dump().values()) == {"placeholder-0.1.0"}


def test_enriched_at_is_the_time_given() -> None:
    assert PlaceholderEnricher().enrich(raw_event(), NOW).enriched_at == NOW


def test_predictions_respect_the_enriched_contract() -> None:
    for author in Author:
        raw = raw_event(author)
        EnrichedMessageEvent.from_raw(raw, PlaceholderEnricher().enrich(raw, NOW))
