from collections import defaultdict
from datetime import UTC, datetime, timedelta
from itertools import islice, pairwise
from uuid import UUID

import pytest

from sentio_schemas import Language, RawMessageEvent
from sentio_simulator import Conversation, GeneratorConfig, generate_conversation, stream
from sentio_simulator.stream import (
    EXPECTED_MESSAGES_PER_CONVERSATION,
    MAX_CONVERSATION_DURATION,
    live_message_stream,
    message_stream,
)

START = datetime(2026, 11, 16, 9, 0, tzinfo=UTC)


def take(n: int, seed: int = 1, rate: float = 5.0) -> list[RawMessageEvent]:
    return list(islice(message_stream(seed, START, rate), n))


def test_same_seed_gives_the_same_stream() -> None:
    assert take(300) == take(300)


def test_different_seeds_give_different_streams() -> None:
    assert take(50, seed=1) != take(50, seed=2)


def test_messages_come_in_time_order_and_never_before_the_start() -> None:
    events = take(3_000)

    assert events[0].sent_at == START
    assert all(later.sent_at >= earlier.sent_at for earlier, later in pairwise(events))


def test_conversations_overlap() -> None:
    first_ten = take(10)

    assert len({e.conversation_id for e in first_ten}) > 1


def test_each_conversation_arrives_in_order() -> None:
    sequences: dict[UUID, list[int]] = defaultdict(list)
    for event in take(3_000):
        sequences[event.conversation_id].append(event.sequence)

    for seen in sequences.values():
        assert seen == list(range(1, len(seen) + 1))


@pytest.mark.parametrize("rate", [2.0, 5.0, 20.0])
def test_conversations_start_at_the_rate_needed_for_the_target(rate: float) -> None:
    """Over 20 simulated minutes, conversations start at rate / 3.35 per second (within 10 %).

    Counting conversation starts (first messages, sent without delay) avoids waiting for e-mail
    replies that arrive hours later. Combined with the next test, it gives the message rate.
    """
    window = timedelta(minutes=20)
    starts = 0
    for event in message_stream(7, START, rate):
        if event.sent_at >= START + window:
            break
        if event.sequence == 1:
            starts += 1

    measured = starts / window.total_seconds()
    assert measured == pytest.approx(rate / EXPECTED_MESSAGES_PER_CONVERSATION, rel=0.10)


def test_expected_messages_per_conversation_matches_the_generator() -> None:
    lengths = [len(generate_conversation(seed, START).events) for seed in range(2_000)]

    average = sum(lengths) / len(lengths)

    assert average == pytest.approx(EXPECTED_MESSAGES_PER_CONVERSATION, rel=0.03)
    assert pytest.approx(3.35) == EXPECTED_MESSAGES_PER_CONVERSATION


def test_generator_config_is_passed_on(monkeypatch: pytest.MonkeyPatch) -> None:
    config = GeneratorConfig(french_share=1.0)
    languages: list[Language] = []

    def recording_generate(
        seed: int, started_at: datetime, config: GeneratorConfig | None = None
    ) -> Conversation:
        conversation = generate_conversation(seed, started_at, config)
        languages.append(conversation.language)
        return conversation

    monkeypatch.setattr(stream, "generate_conversation", recording_generate)
    list(islice(stream.message_stream(1, START, 5.0, config), 200))

    assert languages
    assert set(languages) == {Language.FR}


def test_longest_conversation_lasts_one_hour() -> None:
    assert timedelta(hours=1) == MAX_CONVERSATION_DURATION


def test_no_conversation_lasts_longer_than_the_maximum() -> None:
    for seed in range(2_000):
        events = generate_conversation(seed, START).events
        assert events[-1].sent_at - events[0].sent_at <= MAX_CONVERSATION_DURATION


def test_live_stream_starts_at_now() -> None:
    events = list(islice(live_message_stream(1, START, 5.0), 500))

    assert all(event.sent_at >= START for event in events)
    assert events[0].sent_at - START < timedelta(seconds=5)


def test_live_stream_joins_conversations_already_in_progress() -> None:
    events = list(islice(live_message_stream(1, START, 5.0), 500))

    assert any(event.sequence > 1 for event in events[:20])


@pytest.mark.parametrize("rate", [2.0, 5.0, 20.0])
def test_live_stream_is_at_full_speed_from_the_start(rate: float) -> None:
    """In the first 10 minutes, the message rate is already within 10 % of the target."""
    window = timedelta(minutes=10)
    count = 0
    for event in live_message_stream(3, START, rate):
        if event.sent_at >= START + window:
            break
        count += 1

    assert count / window.total_seconds() == pytest.approx(rate, rel=0.10)


def test_rate_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        next(message_stream(1, START, 0))
