from enrichment_samples import NOW, FixedLanguageDetector, raw_event

from sentio_enrichment import LanguageGuess, MessageEnricher
from sentio_enrichment.enricher import PLACEHOLDER_VERSION
from sentio_schemas import Author, EnrichedMessageEvent, Language, SentimentLabel, TopicLabel


def test_language_comes_from_the_detector() -> None:
    detector = FixedLanguageDetector(LanguageGuess(Language.EN, 0.93))
    raw = raw_event()

    enrichment = MessageEnricher(detector).enrich(raw, NOW)

    assert detector.texts == [raw.text]
    assert enrichment.language is Language.EN
    assert enrichment.language_confidence == 0.93


def test_language_is_detected_for_agent_messages_too() -> None:
    enrichment = MessageEnricher(FixedLanguageDetector()).enrich(raw_event(Author.AGENT), NOW)

    assert enrichment.language is Language.FR


def test_customer_message_gets_neutral_placeholder_predictions() -> None:
    enrichment = MessageEnricher(FixedLanguageDetector()).enrich(raw_event(Author.CUSTOMER), NOW)

    assert enrichment.sentiment is not None
    assert enrichment.sentiment.label is SentimentLabel.NEUTRAL
    assert enrichment.topic is not None
    assert enrichment.topic.label is TopicLabel.OTHER
    assert enrichment.churn_risk == 0.0


def test_agent_message_gets_no_sentiment_topic_or_churn() -> None:
    enrichment = MessageEnricher(FixedLanguageDetector()).enrich(raw_event(Author.AGENT), NOW)

    assert enrichment.sentiment is None
    assert enrichment.topic is None
    assert enrichment.churn_risk is None


def test_model_versions_tell_real_models_from_placeholders() -> None:
    versions = MessageEnricher(FixedLanguageDetector()).enrich(raw_event(), NOW).model_versions

    assert versions.language == "fixed-1.0.0"
    assert {versions.sentiment, versions.topic, versions.churn} == {PLACEHOLDER_VERSION}


def test_enriched_at_is_the_time_given() -> None:
    assert MessageEnricher(FixedLanguageDetector()).enrich(raw_event(), NOW).enriched_at == NOW


def test_undetermined_language_is_accepted_by_the_contract() -> None:
    detector = FixedLanguageDetector(LanguageGuess(Language.UNDETERMINED, 0.0))
    for author in Author:
        raw = raw_event(author)
        enriched = EnrichedMessageEvent.from_raw(raw, MessageEnricher(detector).enrich(raw, NOW))
        assert enriched.enrichment.language is Language.UNDETERMINED
