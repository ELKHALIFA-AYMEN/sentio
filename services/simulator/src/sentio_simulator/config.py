"""Settings of the simulator service, read from environment variables (see .env.example)."""

import logging
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    kafka_bootstrap_servers: str = "localhost:19092"
    topic: str = "conversations.raw"
    messages_per_second: float = 5.0
    french_share: float = 0.5
    seed: int | None = None
    """Fixed seed for a reproducible stream; ``None`` picks a new random seed at each start."""
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> "Settings":
        """Build the settings from ``environ`` (usually ``os.environ``).

        Missing or empty variables keep their default value.
        """
        defaults = cls()
        seed_text = environ.get("SIMULATOR_SEED", "").strip()
        return cls(
            kafka_bootstrap_servers=environ.get(
                "KAFKA_BOOTSTRAP_SERVERS", defaults.kafka_bootstrap_servers
            ),
            topic=environ.get("SIMULATOR_TOPIC", defaults.topic),
            messages_per_second=_parse_float(
                environ, "SIMULATOR_MESSAGES_PER_SECOND", defaults.messages_per_second
            ),
            french_share=_parse_float(environ, "SIMULATOR_FRENCH_SHARE", defaults.french_share),
            seed=_parse_int(seed_text, "SIMULATOR_SEED") if seed_text else None,
            log_level=environ.get("LOG_LEVEL", defaults.log_level).upper(),
        )

    def __post_init__(self) -> None:
        if not self.kafka_bootstrap_servers.strip():
            raise ValueError("KAFKA_BOOTSTRAP_SERVERS must not be empty")
        if not self.topic.strip():
            raise ValueError("SIMULATOR_TOPIC must not be empty")
        if not 0 < self.messages_per_second <= 1_000:
            raise ValueError("SIMULATOR_MESSAGES_PER_SECOND must be > 0 and <= 1000")
        if not 0.0 <= self.french_share <= 1.0:
            raise ValueError("SIMULATOR_FRENCH_SHARE must be between 0 and 1")
        if self.log_level not in logging.getLevelNamesMapping():
            raise ValueError(f"LOG_LEVEL must be a logging level, got {self.log_level!r}")


def _parse_float(environ: Mapping[str, str], name: str, default: float) -> float:
    text = environ.get(name, "").strip()
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        raise ValueError(f"{name} must be a number, got {text!r}") from None


def _parse_int(text: str, name: str) -> int:
    try:
        return int(text)
    except ValueError:
        raise ValueError(f"{name} must be an integer, got {text!r}") from None
