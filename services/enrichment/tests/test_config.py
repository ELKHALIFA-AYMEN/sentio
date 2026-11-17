import pytest

from sentio_enrichment.config import Settings


def test_defaults_work_without_any_variable() -> None:
    assert Settings.from_env({}) == Settings(
        kafka_bootstrap_servers="localhost:19092",
        input_topic="conversations.raw",
        output_topic="conversations.enriched",
        dlq_topic="conversations.dlq",
        group_id="sentio-enrichment",
        log_level="INFO",
    )


def test_every_variable_is_read() -> None:
    settings = Settings.from_env(
        {
            "KAFKA_BOOTSTRAP_SERVERS": "redpanda:9092",
            "ENRICHMENT_INPUT_TOPIC": "in",
            "ENRICHMENT_OUTPUT_TOPIC": "out",
            "ENRICHMENT_DLQ_TOPIC": "dlq",
            "ENRICHMENT_GROUP_ID": "group",
            "LOG_LEVEL": "debug",
        }
    )

    assert settings == Settings(
        kafka_bootstrap_servers="redpanda:9092",
        input_topic="in",
        output_topic="out",
        dlq_topic="dlq",
        group_id="group",
        log_level="DEBUG",
    )


def test_empty_values_fall_back_to_defaults() -> None:
    settings = Settings.from_env({"ENRICHMENT_GROUP_ID": " ", "KAFKA_BOOTSTRAP_SERVERS": ""})

    assert settings.group_id == "sentio-enrichment"
    assert settings.kafka_bootstrap_servers == "localhost:19092"


@pytest.mark.parametrize(
    "variable", ["ENRICHMENT_OUTPUT_TOPIC", "ENRICHMENT_DLQ_TOPIC"], ids=["output", "dlq"]
)
def test_service_must_not_write_to_the_topic_it_reads(variable: str) -> None:
    with pytest.raises(ValueError, match="three different topics"):
        Settings.from_env({variable: "conversations.raw"})


def test_invalid_log_level_is_rejected() -> None:
    with pytest.raises(ValueError, match="logging level"):
        Settings.from_env({"LOG_LEVEL": "LOUD"})
