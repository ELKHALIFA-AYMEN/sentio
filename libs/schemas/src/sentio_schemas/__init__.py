"""Shared, versioned event contracts for Sentio services."""

from importlib.metadata import version

__version__: str = version("sentio-schemas")

__all__ = ["__version__"]
