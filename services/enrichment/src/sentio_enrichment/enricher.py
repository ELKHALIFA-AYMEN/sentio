"""What an enricher is, and a placeholder used until the real models are plugged in."""

from datetime import datetime
from typing import Protocol

from sentio_schemas import (
    Author,
    Enrichment,
    Language,
    ModelVersions,
    RawMessageEvent,
    Sentiment,
    SentimentLabel,
    Topic,
    TopicLabel,
)


class Enricher(Protocol):
    """Anything that turns a raw message into predictions.

    The pipeline only depends on this interface, so a model can be replaced without touching it.
    ``now`` is the time to record as ``enriched_at``.
    """

    def enrich(self, event: RawMessageEvent, now: datetime) -> Enrichment: ...


class PlaceholderEnricher:
    """Returns the same neutral, obviously fake predictions for every message.

    It lets the whole pipeline run end to end before any model exists. Its version, written in
    ``model_versions``, makes placeholder predictions easy to recognise downstream.
    """

    VERSION = "placeholder-0.1.0"

    def enrich(self, event: RawMessageEvent, now: datetime) -> Enrichment:
        is_customer = event.author is Author.CUSTOMER
        return Enrichment(
            language=Language.UNDETERMINED,
            language_confidence=0.0,
            # Predictions are made for customer messages only (see the enriched event contract).
            sentiment=Sentiment(label=SentimentLabel.NEUTRAL, score=0.0) if is_customer else None,
            topic=Topic(label=TopicLabel.OTHER, confidence=0.0) if is_customer else None,
            churn_risk=0.0 if is_customer else None,
            model_versions=ModelVersions(
                language=self.VERSION,
                sentiment=self.VERSION,
                topic=self.VERSION,
                churn=self.VERSION,
            ),
            enriched_at=now,
        )
