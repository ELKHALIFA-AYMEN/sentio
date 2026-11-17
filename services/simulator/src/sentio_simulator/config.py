"""Settings of the simulator service, read from environment variables (see .env.example)."""

import logging
from collections.abc import Mapping
from dataclasses import dataclass

from sentio_simulator.scenarios import ScenarioName


@dataclass(frozen=True, slots=True)
class Settings:
    kafka_bootstrap_servers: str = "localhost:19092"
    topic: str = "conversations.raw"
    messages_per_second: float = 5.0
    french_share: float = 0.5
    seed: int | None = None
    """Fixed seed for a reproducible stream; ``None`` picks a new random seed at each start."""
    log_level: str = "INFO"
    scenario: ScenarioName | None = None
    """Incident to simulate once, after ``scenario_delay_seconds``; ``None`` = normal traffic."""
    scenario_delay_seconds: float = 60.0
    scenario_duration_seconds: float = 600.0

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> "Settings":
        """Build the settings from ``environ`` (usually ``os.environ``).

        Missing or empty variables keep their default value.
        """
        defaults = cls()
        seed_text = environ.get("SIMULATOR_SEED", "").strip()
        scenario_text = environ.get("SIMULATOR_SCENARIO", "").strip().lower()
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
            scenario=_parse_scenario(scenario_text) if scenario_text else None,
            scenario_delay_seconds=_parse_float(
                environ, "SIMULATOR_SCENARIO_DELAY_SECONDS", defaults.scenario_delay_seconds
            ),
            scenario_duration_seconds=_parse_float(
                environ, "SIMULATOR_SCENARIO_DURATION_SECONDS", defaults.scenario_duration_seconds
            ),
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
        if self.scenario_delay_seconds < 0:
            raise ValueError("SIMULATOR_SCENARIO_DELAY_SECONDS must be >= 0")
        if self.scenario_duration_seconds <= 0:
            raise ValueError("SIMULATOR_SCENARIO_DURATION_SECONDS must be > 0")


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


def _parse_scenario(text: str) -> ScenarioName:
    try:
        return ScenarioName(text)
    except ValueError:
        names = ", ".join(name.value for name in ScenarioName)
        raise ValueError(f"SIMULATOR_SCENARIO must be one of: {names}; got {text!r}") from None
