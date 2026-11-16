import pytest

from sentio_simulator.config import Settings


def test_defaults_work_without_any_variable() -> None:
    settings = Settings.from_env({})

    assert settings == Settings(
        kafka_bootstrap_servers="localhost:19092",
        topic="conversations.raw",
        messages_per_second=5.0,
        french_share=0.5,
        seed=None,
        log_level="INFO",
    )


def test_every_variable_is_read() -> None:
    settings = Settings.from_env(
        {
            "KAFKA_BOOTSTRAP_SERVERS": "redpanda:9092",
            "SIMULATOR_TOPIC": "test.topic",
            "SIMULATOR_MESSAGES_PER_SECOND": "12.5",
            "SIMULATOR_FRENCH_SHARE": "0.8",
            "SIMULATOR_SEED": "42",
            "LOG_LEVEL": "debug",
        }
    )

    assert settings == Settings(
        kafka_bootstrap_servers="redpanda:9092",
        topic="test.topic",
        messages_per_second=12.5,
        french_share=0.8,
        seed=42,
        log_level="DEBUG",
    )


def test_empty_values_fall_back_to_defaults() -> None:
    settings = Settings.from_env({"SIMULATOR_SEED": "", "SIMULATOR_MESSAGES_PER_SECOND": " "})

    assert settings.seed is None
    assert settings.messages_per_second == 5.0


@pytest.mark.parametrize(
    ("variable", "value", "message"),
    [
        ("SIMULATOR_MESSAGES_PER_SECOND", "fast", "must be a number"),
        ("SIMULATOR_MESSAGES_PER_SECOND", "0", "must be > 0"),
        ("SIMULATOR_MESSAGES_PER_SECOND", "5000", "<= 1000"),
        ("SIMULATOR_FRENCH_SHARE", "1.2", "between 0 and 1"),
        ("SIMULATOR_SEED", "abc", "must be an integer"),
        ("LOG_LEVEL", "LOUD", "logging level"),
        ("KAFKA_BOOTSTRAP_SERVERS", " ", "must not be empty"),
        ("SIMULATOR_TOPIC", "", "must not be empty"),
    ],
)
def test_invalid_value_is_rejected_with_a_clear_message(
    variable: str, value: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        Settings.from_env({variable: value})
