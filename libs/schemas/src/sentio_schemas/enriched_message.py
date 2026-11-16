"""Contract of the events published on the ``conversations.enriched`` topic (version 1).

An enriched event is a raw event (same fields, same rules) plus an ``enrichment`` block
holding the predictions of the enrichment service. See docs/adr/0003-event-format.md.
"""

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, StringConstraints, model_validator

from sentio_schemas._common import Contract, Probability, UtcDatetime
from sentio_schemas.raw_message import Author, RawMessageEvent


class Language(StrEnum):
    """Detected language (ISO 639 codes). ``und`` means the language could not be determined."""

    FR = "fr"
    EN = "en"
    UNDETERMINED = "und"


class SentimentLabel(StrEnum):
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"


class TopicLabel(StrEnum):
    """What the customer is contacting support about."""

    BILLING = "billing"
    NETWORK = "network"
    ROAMING = "roaming"
    PLAN = "plan"
    PORTING = "porting"
    OTHER = "other"


class Sentiment(Contract):
    """Sentiment of a message.

    ``score`` goes from -1 (very negative) to +1 (very positive). It must agree with the label:
    a negative label cannot have a positive score, and vice versa.
    """

    label: SentimentLabel
    score: Annotated[float, Field(ge=-1.0, le=1.0)]

    @model_validator(mode="after")
    def _score_matches_label(self) -> Self:
        if self.label is SentimentLabel.NEGATIVE and self.score > 0:
            raise ValueError("a negative sentiment cannot have a positive score")
        if self.label is SentimentLabel.POSITIVE and self.score < 0:
            raise ValueError("a positive sentiment cannot have a negative score")
        return self


class Topic(Contract):
    label: TopicLabel
    confidence: Probability


ModelVersion = Annotated[str, StringConstraints(min_length=1, max_length=64)]


class ModelVersions(Contract):
    """Version of each model in the pipeline that processed the message, for traceability."""

    language: ModelVersion
    sentiment: ModelVersion
    topic: ModelVersion
    churn: ModelVersion


class Enrichment(Contract):
    """Predictions added by the enrichment service.

    ``sentiment``, ``topic`` and ``churn_risk`` are required (but may be ``null``): they are set
    for customer messages and ``null`` for agent messages. The rule is checked on the event,
    where the author is known.
    """

    language: Language
    language_confidence: Probability
    sentiment: Sentiment | None
    topic: Topic | None
    churn_risk: Probability | None
    model_versions: ModelVersions
    enriched_at: UtcDatetime


class EnrichedMessageEvent(RawMessageEvent):
    """One enriched message, as published on ``conversations.enriched``."""

    enrichment: Enrichment

    @classmethod
    def from_raw(cls, raw: RawMessageEvent, enrichment: Enrichment) -> Self:
        """Build the enriched event for ``raw``, keeping every raw field unchanged."""
        return cls(**dict(raw), enrichment=enrichment)

    @model_validator(mode="after")
    def _predictions_match_author(self) -> Self:
        predictions = {
            "sentiment": self.enrichment.sentiment,
            "topic": self.enrichment.topic,
            "churn_risk": self.enrichment.churn_risk,
        }
        if self.author is Author.CUSTOMER:
            missing = [name for name, value in predictions.items() if value is None]
            if missing:
                raise ValueError(f"customer messages require {', '.join(missing)}")
        else:
            present = [name for name, value in predictions.items() if value is not None]
            if present:
                raise ValueError(f"agent messages must not have {', '.join(present)}")
        return self
