import re
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import islice

import pytest

from sentio_schemas import Language, RawMessageEvent, SentimentLabel, TopicLabel
from sentio_simulator import (
    SCENARIOS,
    Conversation,
    GeneratorConfig,
    Incident,
    Scenario,
    ScenarioName,
    generate_conversation,
    stream,
)
from sentio_simulator.catalog import CITIES, PLANS
from sentio_simulator.generator import format_eur
from sentio_simulator.stream import message_stream

START = datetime(2026, 11, 16, 9, 0, tzinfo=UTC)
SEEDS = range(2_000)
NETWORK_OUTAGE = SCENARIOS[ScenarioName.NETWORK_OUTAGE]
BILLING_ERROR = SCENARIOS[ScenarioName.BILLING_ERROR]


def conversations(config: GeneratorConfig | None = None) -> list[Conversation]:
    return [generate_conversation(seed, START, config) for seed in SEEDS]


def negative_share(sample: Iterable[Conversation], topic: TopicLabel | None = None) -> float:
    moods = [c.mood for c in sample if topic is None or c.topic is topic]
    return moods.count(SentimentLabel.NEGATIVE) / len(moods)


def topic_share(sample: list[Conversation], topic: TopicLabel) -> float:
    return sum(c.topic is topic for c in sample) / len(sample)


@pytest.fixture(scope="module")
def normal_day() -> list[Conversation]:
    return conversations()


# --- The catalog -------------------------------------------------------------------


def test_every_scenario_name_has_a_scenario() -> None:
    assert set(SCENARIOS) == set(ScenarioName)
    for name, scenario in SCENARIOS.items():
        assert scenario.name is name


@pytest.mark.parametrize("scenario", SCENARIOS.values(), ids=str)
def test_applying_a_scenario_gives_the_announced_topic_share(scenario: Scenario) -> None:
    config = scenario.apply(GeneratorConfig())

    total = sum(config.topic_weights.values())
    assert config.topic_weights[scenario.topic] / total == pytest.approx(scenario.topic_share)
    assert config.mood_weights[scenario.topic] == scenario.mood_weights


def test_applying_a_scenario_keeps_the_other_settings() -> None:
    config = NETWORK_OUTAGE.apply(GeneratorConfig(french_share=0.9))

    assert config.french_share == 0.9
    # The other topics keep their usual mood and their proportions between them.
    assert (
        config.mood_weights[TopicLabel.BILLING]
        == GeneratorConfig().mood_weights[TopicLabel.BILLING]
    )
    weights = config.topic_weights
    assert weights[TopicLabel.BILLING] / weights[TopicLabel.PLAN] == pytest.approx(0.25 / 0.20)


def test_applying_a_scenario_to_traffic_without_other_topics() -> None:
    config = BILLING_ERROR.apply(GeneratorConfig(topic_weights={TopicLabel.BILLING: 1.0}))

    assert dict(config.topic_weights) == {TopicLabel.BILLING: 1.0}


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"topic_share": 0.0}, "topic_share"),
        ({"topic_share": 1.5}, "topic_share"),
        ({"rate_multiplier": 0.5}, "rate_multiplier"),
    ],
)
def test_invalid_scenario_is_rejected(changes: dict[str, float], message: str) -> None:
    settings = {"topic_share": 0.5, "rate_multiplier": 1.0, **changes}
    with pytest.raises(ValueError, match=message):
        Scenario(
            name=ScenarioName.NETWORK_OUTAGE,
            topic=TopicLabel.NETWORK,
            topic_share=settings["topic_share"],
            mood_weights=(1.0, 0.0, 0.0),
            rate_multiplier=settings["rate_multiplier"],
        )


# --- Network outage ------------------------------------------------------------------


@pytest.fixture(scope="module")
def outage() -> list[Conversation]:
    return conversations(NETWORK_OUTAGE.apply(GeneratorConfig()))


def test_outage_makes_network_the_main_topic(
    normal_day: list[Conversation], outage: list[Conversation]
) -> None:
    assert topic_share(normal_day, TopicLabel.NETWORK) == pytest.approx(0.20, abs=0.03)
    assert topic_share(outage, TopicLabel.NETWORK) == pytest.approx(0.60, abs=0.03)


def test_outage_raises_the_share_of_negative_network_conversations(
    normal_day: list[Conversation], outage: list[Conversation]
) -> None:
    assert negative_share(normal_day, TopicLabel.NETWORK) == pytest.approx(0.60, abs=0.05)
    assert negative_share(outage, TopicLabel.NETWORK) == pytest.approx(0.90, abs=0.03)


def test_outage_raises_the_share_of_negative_conversations_overall(
    normal_day: list[Conversation], outage: list[Conversation]
) -> None:
    assert negative_share(outage) > negative_share(normal_day) + 0.20


def test_every_network_message_during_the_outage_names_the_same_city(
    outage: list[Conversation],
) -> None:
    other_cities = set(CITIES) - {"Lyon"}
    texts = [e.text for c in outage if c.topic is TopicLabel.NETWORK for e in c.events]

    assert sum("Lyon" in text for text in texts) > 500
    assert not any(city in text for text in texts for city in other_cities)


# --- Billing error --------------------------------------------------------------------


@pytest.fixture(scope="module")
def billing_error() -> list[Conversation]:
    return conversations(BILLING_ERROR.apply(GeneratorConfig()))


def test_billing_error_raises_the_share_of_negative_billing_conversations(
    normal_day: list[Conversation], billing_error: list[Conversation]
) -> None:
    assert topic_share(billing_error, TopicLabel.BILLING) == pytest.approx(0.60, abs=0.03)
    assert negative_share(normal_day, TopicLabel.BILLING) == pytest.approx(0.50, abs=0.05)
    assert negative_share(billing_error, TopicLabel.BILLING) == pytest.approx(0.85, abs=0.03)
    assert negative_share(billing_error) > negative_share(normal_day) + 0.20


def test_every_unexpected_charge_is_the_same_amount(billing_error: list[Conversation]) -> None:
    """Amounts quoted in billing messages are the wrong fee or the customer's plan price."""
    plan_prices = {plan.monthly_price_eur for plans in PLANS.values() for plan in plans}
    seen: set[Decimal] = set()
    for conversation in billing_error:
        if conversation.topic is not TopicLabel.BILLING:
            continue
        for event in conversation.events:
            for amount in re.findall(r"\d+[.,]\d{2}", event.text):
                seen.add(Decimal(amount.replace(",", ".")))

    assert Decimal("12.90") in seen
    assert seen <= plan_prices | {Decimal("12.90")}


def test_the_fee_is_written_the_local_way(billing_error: list[Conversation]) -> None:
    texts = {e.text for c in billing_error for e in c.events}
    english = format_eur(Decimal("12.90"), Language.EN)
    french = format_eur(Decimal("12.90"), Language.FR)

    assert any(english in text for text in texts)
    assert any(french in text for text in texts)


# --- Generator settings used by the scenarios ------------------------------------------


def test_overrides_change_only_the_overridden_values() -> None:
    """Same seed with and without an override: everything else in the conversation is identical."""
    normal = generate_conversation(3, START)
    with_city = generate_conversation(3, START, GeneratorConfig(city="Lille"))

    assert [e.message_id for e in with_city.events] == [e.message_id for e in normal.events]
    assert with_city.topic is normal.topic
    assert with_city.mood is normal.mood


@pytest.mark.parametrize(
    ("config", "message"),
    [
        ({"topic_weights": {TopicLabel.NETWORK: 1.0}, "mood_weights": {}}, "no odds"),
        ({"mood_weights": {t: (1.0, 0.0) for t in TopicLabel}}, "3 non-negative odds"),
        ({"mood_weights": {t: (0.0, 0.0, 0.0) for t in TopicLabel}}, "3 non-negative odds"),
        ({"city": " "}, "city"),
        ({"extra_charge_eur": Decimal(0)}, "extra_charge_eur"),
    ],
)
def test_invalid_generator_overrides_are_rejected(config: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        GeneratorConfig(**config)  # type: ignore[arg-type]


# --- Incidents in the stream ---------------------------------------------------------


def outage_between(start_minute: int, end_minute: int) -> Incident:
    return Incident(
        NETWORK_OUTAGE,
        START + timedelta(minutes=start_minute),
        START + timedelta(minutes=end_minute),
    )


def test_incident_is_active_from_its_start_to_just_before_its_end() -> None:
    incident = outage_between(10, 20)

    assert not incident.is_active(START + timedelta(minutes=9, seconds=59))
    assert incident.is_active(START + timedelta(minutes=10))
    assert incident.is_active(START + timedelta(minutes=19, seconds=59))
    assert not incident.is_active(START + timedelta(minutes=20))


def test_incident_starting_after_a_delay() -> None:
    incident = Incident.starting_after(
        ScenarioName.BILLING_ERROR, START, timedelta(minutes=1), timedelta(minutes=10)
    )

    assert incident == Incident(
        BILLING_ERROR, START + timedelta(minutes=1), START + timedelta(minutes=11)
    )


def test_incident_must_end_after_it_starts() -> None:
    with pytest.raises(ValueError, match="end after it starts"):
        outage_between(10, 10)


def test_incident_times_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        Incident(NETWORK_OUTAGE, datetime(2026, 11, 16, 9, 0), START)


def test_overlapping_incidents_are_rejected() -> None:
    with pytest.raises(ValueError, match="overlap"):
        next(
            message_stream(1, START, 5.0, incidents=[outage_between(0, 20), outage_between(10, 30)])
        )


def test_incidents_one_after_the_other_are_accepted() -> None:
    incidents = [outage_between(0, 10), outage_between(10, 20)]

    assert next(message_stream(1, START, 5.0, incidents=incidents)).sent_at == START


def test_same_seed_and_incident_give_the_same_stream() -> None:
    def take() -> list[RawMessageEvent]:
        return list(islice(message_stream(1, START, 5.0, incidents=[outage_between(0, 5)]), 500))

    assert take() == take()


@pytest.fixture(scope="module")
def stream_with_outage() -> list[Conversation]:
    """One simulated hour at 5 messages/s with an outage from minute 20 to minute 40.

    Records every conversation the stream generates, with its ground truth.
    """
    recorded: list[Conversation] = []

    def recording_generate(
        seed: int, started_at: datetime, config: GeneratorConfig | None = None
    ) -> Conversation:
        conversation = generate_conversation(seed, started_at, config)
        recorded.append(conversation)
        return conversation

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(stream, "generate_conversation", recording_generate)
        end = START + timedelta(hours=1)
        for event in stream.message_stream(5, START, 5.0, incidents=[outage_between(20, 40)]):
            if event.sent_at >= end:
                break
    return [c for c in recorded if c.events[0].sent_at < end]


def started_between(
    sample: list[Conversation], start_minute: int, end_minute: int
) -> list[Conversation]:
    low, high = START + timedelta(minutes=start_minute), START + timedelta(minutes=end_minute)
    return [c for c in sample if low <= c.events[0].sent_at < high]


def test_stream_is_negative_on_network_only_during_the_outage(
    stream_with_outage: list[Conversation],
) -> None:
    before = started_between(stream_with_outage, 0, 20)
    during = started_between(stream_with_outage, 20, 40)
    after = started_between(stream_with_outage, 40, 60)

    assert negative_share(before, TopicLabel.NETWORK) == pytest.approx(0.60, abs=0.10)
    assert negative_share(during, TopicLabel.NETWORK) == pytest.approx(0.90, abs=0.05)
    assert negative_share(after, TopicLabel.NETWORK) == pytest.approx(0.60, abs=0.10)
    assert topic_share(during, TopicLabel.NETWORK) == pytest.approx(0.60, abs=0.05)
    assert topic_share(after, TopicLabel.NETWORK) == pytest.approx(0.20, abs=0.05)


def test_stream_sends_more_messages_during_the_outage(
    stream_with_outage: list[Conversation],
) -> None:
    """Conversations start 1.5 times as often during the outage (within 15 %)."""
    before = len(started_between(stream_with_outage, 0, 20))
    during = len(started_between(stream_with_outage, 20, 40))

    assert during / before == pytest.approx(NETWORK_OUTAGE.rate_multiplier, rel=0.15)
