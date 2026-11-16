"""Shared, versioned event contracts for Sentio services."""

from importlib.metadata import version

from sentio_schemas.enriched_message import (
    EnrichedMessageEvent,
    Enrichment,
    Language,
    ModelVersions,
    Sentiment,
    SentimentLabel,
    Topic,
    TopicLabel,
)
from sentio_schemas.raw_message import Author, Channel, Customer, CustomerSegment, RawMessageEvent

__version__: str = version("sentio-schemas")

__all__ = [
    "Author",
    "Channel",
    "Customer",
    "CustomerSegment",
    "EnrichedMessageEvent",
    "Enrichment",
    "Language",
    "ModelVersions",
    "RawMessageEvent",
    "Sentiment",
    "SentimentLabel",
    "Topic",
    "TopicLabel",
    "__version__",
]
