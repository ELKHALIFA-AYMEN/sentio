from datetime import UTC, datetime

from sentio_schemas import RawMessageEvent
from sentio_simulator import generate_conversation
from sentio_simulator.publisher import encode

START = datetime(2026, 11, 16, 9, 0, tzinfo=UTC)


def test_key_is_the_conversation_id() -> None:
    conversation = generate_conversation(5, START)

    keys = {encode(event)[0] for event in conversation.events}

    assert keys == {str(conversation.events[0].conversation_id).encode()}


def test_value_is_the_contract_json() -> None:
    event = generate_conversation(5, START).events[0]

    _, value = encode(event)

    assert RawMessageEvent.model_validate_json(value) == event


def test_value_is_utf8_encoded() -> None:
    french = next(
        e
        for seed in range(100)
        for e in generate_conversation(seed, START).events
        if any(ch in e.text for ch in "éèàç")
    )

    _, value = encode(french)

    assert french.text in value.decode("utf-8")
