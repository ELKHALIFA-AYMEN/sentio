"""Shared, versioned event contracts for Sentio services."""

from importlib.metadata import version

from sentio_schemas.raw_message import Author, Channel, Customer, CustomerSegment, RawMessageEvent

__version__: str = version("sentio-schemas")

__all__ = [
    "Author",
    "Channel",
    "Customer",
    "CustomerSegment",
    "RawMessageEvent",
    "__version__",
]
