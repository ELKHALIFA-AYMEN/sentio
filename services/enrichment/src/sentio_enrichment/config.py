"""Settings of the enrichment service, read from environment variables (see .env.example)."""

import logging
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    kafka_bootstrap_servers: str = "localhost:19092"
    input_topic: str = "conversations.raw"
    output_topic: str = "conversations.enriched"
    dlq_topic: str = "conversations.dlq"
    group_id: str = "sentio-enrichment"
    """Consumer group: instances with this ID share the partitions and the committed offsets."""
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> "Settings":
        """Build the settings from ``environ`` (usually ``os.environ``).

        Missing or empty variables keep their default value.
        """
        defaults = cls()

        def read(name: str, default: str) -> str:
            return environ.get(name, "").strip() or default

        return cls(
            kafka_bootstrap_servers=read(
                "KAFKA_BOOTSTRAP_SERVERS", defaults.kafka_bootstrap_servers
            ),
            input_topic=read("ENRICHMENT_INPUT_TOPIC", defaults.input_topic),
            output_topic=read("ENRICHMENT_OUTPUT_TOPIC", defaults.output_topic),
            dlq_topic=read("ENRICHMENT_DLQ_TOPIC", defaults.dlq_topic),
            group_id=read("ENRICHMENT_GROUP_ID", defaults.group_id),
            log_level=read("LOG_LEVEL", defaults.log_level).upper(),
        )

    def __post_init__(self) -> None:
        topics = {self.input_topic, self.output_topic, self.dlq_topic}
        if len(topics) != 3:
            # Writing to the topic being read would make the service process its own output forever.
            raise ValueError("input, output and DLQ topics must be three different topics")
        if self.log_level not in logging.getLevelNamesMapping():
            raise ValueError(f"LOG_LEVEL must be a logging level, got {self.log_level!r}")
