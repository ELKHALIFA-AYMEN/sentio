import random
import re
from collections import Counter
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from itertools import pairwise
from string import Formatter

import pytest

from sentio_schemas import Author, Language, RawMessageEvent, SentimentLabel, TopicLabel
from sentio_simulator import Conversation, GeneratorConfig, generate_conversation, templates
from sentio_simulator.catalog import PLANS, ROAMING_COUNTRIES_EN, ROAMING_COUNTRIES_FR
from sentio_simulator.generator import format_eur

START = datetime(2026, 11, 16, 9, 0, tzinfo=UTC)
MANY_SEEDS = range(2_000)


@pytest.fixture(scope="module")
def many_conversations() -> list[Conversation]:
    """A large, reproducible sample: the same 2,000 conversations on every run."""
    return [generate_conversation(seed, START) for seed in MANY_SEEDS]


# --- Reproducibility ------------------------------------------------------------


def test_same_seed_gives_the_same_conversation() -> None:
    assert generate_conversation(42, START) == generate_conversation(42, START)


def test_different_seeds_give_different_conversations() -> None:
    assert generate_conversation(1, START) != generate_conversation(2, START)


def test_generation_does_not_depend_on_global_random_state() -> None:
    random.seed(0)
    first = generate_conversation(7, START)
    random.seed(999)
    second = generate_conversation(7, START)

    assert first == second


# --- Every event respects the contract -------------------------------------------


def test_every_event_survives_the_wire_format(many_conversations: list[Conversation]) -> None:
    for conversation in many_conversations:
        for event in conversation.events:
            assert RawMessageEvent.model_validate_json(event.model_dump_json()) == event


def test_no_unfilled_placeholder(many_conversations: list[Conversation]) -> None:
    for conversation in many_conversations:
        for event in conversation.events:
            assert "{" not in event.text
            assert "}" not in event.text


def test_no_personal_data_in_texts(many_conversations: list[Conversation]) -> None:
    long_number = re.compile(r"\d{6,}")  # phone numbers, card numbers, account numbers...
    for conversation in many_conversations:
        for event in conversation.events:
            assert "@" not in event.text
            assert not long_number.search(event.text), event.text


# --- Shape of a conversation ---------------------------------------------------------


def test_conversation_has_between_2_and_4_messages(
    many_conversations: list[Conversation],
) -> None:
    lengths = Counter(len(c.events) for c in many_conversations)

    assert set(lengths) == {2, 3, 4}


def test_sequences_are_contiguous_and_ids_are_unique(
    many_conversations: list[Conversation],
) -> None:
    all_ids: set[object] = set()
    for conversation in many_conversations:
        events = conversation.events
        assert [e.sequence for e in events] == list(range(1, len(events) + 1))
        assert len({e.conversation_id for e in events}) == 1
        ids = [e.message_id for e in events] + [e.event_id for e in events]
        all_ids.update(ids)
    total_events = sum(len(c.events) for c in many_conversations)

    assert len(all_ids) == 2 * total_events


def test_customer_speaks_first_and_turns_alternate(
    many_conversations: list[Conversation],
) -> None:
    for conversation in many_conversations:
        authors = [e.author for e in conversation.events]
        expected = [Author.CUSTOMER, Author.AGENT] * 2
        assert authors == expected[: len(authors)]


def test_timestamps_start_at_started_at_and_increase(
    many_conversations: list[Conversation],
) -> None:
    for conversation in many_conversations:
        times = [e.sent_at for e in conversation.events]
        assert times[0] == START
        assert all(later > earlier for earlier, later in pairwise(times))


def test_channel_and_customer_stay_the_same(many_conversations: list[Conversation]) -> None:
    for conversation in many_conversations:
        assert len({e.channel for e in conversation.events}) == 1
        assert len({e.customer for e in conversation.events}) == 1


def test_customer_pays_the_price_of_a_plan_of_their_segment(
    many_conversations: list[Conversation],
) -> None:
    for conversation in many_conversations:
        customer = conversation.events[0].customer
        prices = {plan.monthly_price_eur for plan in PLANS[customer.segment]}
        assert customer.monthly_revenue_eur in prices


def test_started_at_in_another_timezone_is_stored_in_utc() -> None:
    paris = timezone(timedelta(hours=1))

    event = generate_conversation(3, datetime(2026, 11, 16, 10, 0, tzinfo=paris)).events[0]

    assert event.sent_at == START
    assert event.sent_at.tzinfo is UTC


def test_naive_started_at_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        generate_conversation(1, datetime(2026, 11, 16, 9, 0))


# --- Variety and configuration ----------------------------------------------------------


def test_default_traffic_covers_every_language_topic_and_mood(
    many_conversations: list[Conversation],
) -> None:
    assert {c.language for c in many_conversations} == {Language.FR, Language.EN}
    assert {c.topic for c in many_conversations} == set(TopicLabel)
    assert {c.mood for c in many_conversations} == set(SentimentLabel)


def test_default_traffic_is_half_french(many_conversations: list[Conversation]) -> None:
    french = sum(c.language is Language.FR for c in many_conversations)

    assert 0.45 < french / len(many_conversations) < 0.55


def test_french_share_is_respected() -> None:
    config = GeneratorConfig(french_share=1.0)

    assert all(
        generate_conversation(seed, START, config).language is Language.FR for seed in range(200)
    )


def test_topic_weights_are_respected() -> None:
    config = GeneratorConfig(topic_weights={TopicLabel.NETWORK: 1.0})

    assert all(
        generate_conversation(seed, START, config).topic is TopicLabel.NETWORK
        for seed in range(200)
    )


def test_ground_truth_language_matches_the_text() -> None:
    """Every message matches a template of the conversation's language, and none of the other."""
    patterns = {language: _template_patterns(language) for language in (Language.EN, Language.FR)}
    for seed in range(500):
        conversation = generate_conversation(seed, START)
        other = Language.EN if conversation.language is Language.FR else Language.FR
        for event in conversation.events:
            assert any(p.fullmatch(event.text) for p in patterns[conversation.language]), event.text
            assert not any(p.fullmatch(event.text) for p in patterns[other]), event.text


def test_agent_tone_follows_the_customer_mood(many_conversations: list[Conversation]) -> None:
    apology = re.compile(r"sorry|apolog|excuses", re.IGNORECASE)
    for conversation in many_conversations:
        agent_reply = conversation.events[1].text
        apologises = bool(apology.search(agent_reply))
        assert apologises == (conversation.mood is SentimentLabel.NEGATIVE), agent_reply


def test_countries_come_with_the_right_preposition(
    many_conversations: list[Conversation],
) -> None:
    """'I'm in Spain' / 'je suis en Espagne', never 'I'm Spain' or 'je suis Espagne'."""
    # "in the United Kingdom" -> country "the United Kingdom"; "Canada" has an EN and a FR form.
    correct_forms: dict[str, set[str]] = {}
    for value in ROAMING_COUNTRIES_EN + ROAMING_COUNTRIES_FR:
        correct_forms.setdefault(value.split(" ", 1)[1], set()).add(value)
    roaming_texts = [
        event.text
        for conversation in many_conversations
        if conversation.topic is TopicLabel.ROAMING
        for event in conversation.events
    ]
    checked = 0
    for text in roaming_texts:
        for country, forms in correct_forms.items():
            if re.search(rf"\b{re.escape(country)}\b", text):
                assert any(form in text for form in forms), text
                checked += 1
    assert checked > 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"french_share": 1.5},
        {"french_share": -0.1},
        {"topic_weights": {}},
        {"topic_weights": {TopicLabel.BILLING: -1.0}},
        {"topic_weights": {TopicLabel.BILLING: 0.0}},
    ],
)
def test_invalid_config_is_rejected(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):  # noqa: PT011 - each case has its own message
        GeneratorConfig(**kwargs)  # type: ignore[arg-type]


def _template_patterns(language: Language) -> list[re.Pattern[str]]:
    """Turn each template of ``language`` into a regex: literal text, and ``.+`` for each slot."""
    texts = [
        *(
            t
            for by_lang in templates.OPENERS.values()
            for ts in by_lang[language].values()
            for t in ts
        ),
        *(
            t
            for by_lang in templates.AGENT_REPLIES.values()
            for ts in by_lang[language].values()
            for t in ts
        ),
        *(t for ts in templates.FOLLOW_UPS[language].values() for t in ts),
        *(t for ts in templates.CLOSINGS[language].values() for t in ts),
    ]
    patterns = []
    for text in texts:
        parts = [
            re.escape(literal) + (".+" if name is not None else "")
            for literal, name, _, _ in Formatter().parse(text)
        ]
        patterns.append(re.compile("".join(parts)))
    return patterns


# --- Formatting -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("language", "expected"), [(Language.EN, "€29.99"), (Language.FR, "29,99 €")]
)
def test_amounts_are_written_the_local_way(language: Language, expected: str) -> None:
    assert format_eur(Decimal("29.99"), language) == expected
