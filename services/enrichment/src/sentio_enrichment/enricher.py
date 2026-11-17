"""What an enricher is, and the enricher used by the service.

The language is detected by a real model. Sentiment, topic and churn risk are still placeholders
(fixed neutral values); they are replaced one by one in the next steps.
"""

from datetime import datetime
from typing import Protocol

from sentio_enrichment.language import LanguageDetector
from sentio_schemas import (
    Author,
    Enrichment,
    ModelVersions,
    RawMessageEvent,
    Sentiment,
    SentimentLabel,
    Topic,
    TopicLabel,
)

PLACEHOLDER_VERSION = "placeholder-0.1.0"
"""Version written for predictions that do not come from a model yet."""


class Enricher(Protocol):
    """Anything that turns a raw message into predictions.

    The pipeline only depends on this interface, so a model can be replaced without touching it.
    ``now`` is the time to record as ``enriched_at``.
    """

    def enrich(self, event: RawMessageEvent, now: datetime) -> Enrichment: ...


class MessageEnricher:
    """Detects the language of every message; other predictions are placeholders for now."""

    def __init__(self, language_detector: LanguageDetector) -> None:
        self._language_detector = language_detector

    def enrich(self, event: RawMessageEvent, now: datetime) -> Enrichment:
        language = self._language_detector.detect(event.text)
        is_customer = event.author is Author.CUSTOMER
        return Enrichment(
            # The language is detected for every message, agent messages included.
            language=language.language,
            language_confidence=language.confidence,
            # Other predictions are made for customer messages only (see the enriched contract).
            sentiment=Sentiment(label=SentimentLabel.NEUTRAL, score=0.0) if is_customer else None,
            topic=Topic(label=TopicLabel.OTHER, confidence=0.0) if is_customer else None,
            churn_risk=0.0 if is_customer else None,
            model_versions=ModelVersions(
                language=self._language_detector.version,
                sentiment=PLACEHOLDER_VERSION,
                topic=PLACEHOLDER_VERSION,
                churn=PLACEHOLDER_VERSION,
            ),
            enriched_at=now,
        )
