"""Builds synthetic support conversations.

Everything here is a pure function: the result depends only on the arguments (a seed, a start time,
a configuration). Nothing reads the clock, the network or a global random state, so the same
arguments always produce exactly the same conversation.
"""

import random
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from types import MappingProxyType
from uuid import UUID

from sentio_schemas import (
    Author,
    Channel,
    Customer,
    CustomerSegment,
    Language,
    RawMessageEvent,
    SentimentLabel,
    TopicLabel,
)
from sentio_simulator import templates
from sentio_simulator.catalog import (
    CITIES,
    OPERATOR_NAME,
    PLANS,
    ROAMING_COUNTRIES_EN,
    ROAMING_COUNTRIES_FR,
    Plan,
)

DEFAULT_TOPIC_WEIGHTS: Mapping[TopicLabel, float] = MappingProxyType(
    {
        TopicLabel.BILLING: 0.25,
        TopicLabel.NETWORK: 0.20,
        TopicLabel.PLAN: 0.20,
        TopicLabel.OTHER: 0.15,
        TopicLabel.ROAMING: 0.10,
        TopicLabel.PORTING: 0.10,
    }
)

# How customers feel, per topic: (negative, neutral, positive).
MOOD_WEIGHTS: Mapping[TopicLabel, tuple[float, float, float]] = MappingProxyType(
    {
        TopicLabel.BILLING: (0.50, 0.35, 0.15),
        TopicLabel.NETWORK: (0.60, 0.30, 0.10),
        TopicLabel.ROAMING: (0.40, 0.40, 0.20),
        TopicLabel.PLAN: (0.25, 0.45, 0.30),
        TopicLabel.PORTING: (0.55, 0.30, 0.15),
        TopicLabel.OTHER: (0.20, 0.55, 0.25),
    }
)
MOODS = (SentimentLabel.NEGATIVE, SentimentLabel.NEUTRAL, SentimentLabel.POSITIVE)

SEGMENT_WEIGHTS: Mapping[CustomerSegment, float] = MappingProxyType(
    {CustomerSegment.PREPAID: 0.40, CustomerSegment.POSTPAID: 0.45, CustomerSegment.BUSINESS: 0.15}
)
CHANNEL_WEIGHTS: Mapping[Channel, float] = MappingProxyType(
    {Channel.CHAT: 0.60, Channel.EMAIL: 0.25, Channel.CALL_TRANSCRIPT: 0.15}
)

# Delay between two messages, in seconds (min, max), per channel.
REPLY_DELAY_SECONDS: Mapping[Channel, tuple[int, int]] = MappingProxyType(
    {
        Channel.CHAT: (15, 90),
        Channel.EMAIL: (30 * 60, 6 * 3600),
        Channel.CALL_TRANSCRIPT: (5, 40),
    }
)

FOLLOW_UP_PROBABILITY = 0.75
CLOSING_PROBABILITY = 0.80


@dataclass(frozen=True, slots=True)
class GeneratorConfig:
    """What the generated traffic looks like. Defaults describe a normal day."""

    french_share: float = 0.5
    topic_weights: Mapping[TopicLabel, float] = field(default_factory=lambda: DEFAULT_TOPIC_WEIGHTS)

    def __post_init__(self) -> None:
        if not 0.0 <= self.french_share <= 1.0:
            raise ValueError("french_share must be between 0 and 1")
        if not self.topic_weights or any(w < 0 for w in self.topic_weights.values()):
            raise ValueError("topic_weights must be non-empty and non-negative")
        if sum(self.topic_weights.values()) <= 0:
            raise ValueError("at least one topic weight must be positive")


@dataclass(frozen=True, slots=True)
class Conversation:
    """A generated conversation and the ground truth used to build it.

    ``language``, ``topic`` and ``mood`` are what the generator *intended*. They are not part of the
    published events (the enrichment service must find them on its own), but they let us measure how
    well the models do.
    """

    events: tuple[RawMessageEvent, ...]
    language: Language
    topic: TopicLabel
    mood: SentimentLabel


def generate_conversation(
    seed: int, started_at: datetime, config: GeneratorConfig | None = None
) -> Conversation:
    """Generate one conversation.

    The same ``seed``, ``started_at`` and ``config`` always give the same result.
    """
    if started_at.tzinfo is None:
        raise ValueError("started_at must be timezone-aware")
    config = config or GeneratorConfig()
    rng = random.Random(seed)

    language = Language.FR if rng.random() < config.french_share else Language.EN
    topic = _weighted_choice(rng, config.topic_weights)
    mood = rng.choices(MOODS, weights=MOOD_WEIGHTS[topic])[0]
    channel = _weighted_choice(rng, CHANNEL_WEIGHTS)
    segment = _weighted_choice(rng, SEGMENT_WEIGHTS)
    plan = rng.choice(PLANS[segment])
    customer = Customer(
        customer_id=f"CUST-{rng.randrange(1_000_000):06d}",
        segment=segment,
        tenure_months=rng.randint(0, 120),
        monthly_revenue_eur=plan.monthly_price_eur,
    )
    slots = _slot_values(rng, language, plan)

    turns: list[tuple[Author, str]] = [
        (Author.CUSTOMER, rng.choice(templates.OPENERS[topic][language][mood])),
        (Author.AGENT, rng.choice(templates.AGENT_REPLIES[topic][language][mood])),
    ]
    if rng.random() < FOLLOW_UP_PROBABILITY:
        turns.append((Author.CUSTOMER, rng.choice(templates.FOLLOW_UPS[language][mood])))
        if rng.random() < CLOSING_PROBABILITY:
            turns.append((Author.AGENT, rng.choice(templates.CLOSINGS[language][mood])))

    conversation_id = _uuid(rng)
    min_delay, max_delay = REPLY_DELAY_SECONDS[channel]
    sent_at = started_at
    events: list[RawMessageEvent] = []
    for sequence, (author, template) in enumerate(turns, start=1):
        if sequence > 1:
            sent_at += timedelta(seconds=rng.randint(min_delay, max_delay))
        events.append(
            RawMessageEvent(
                event_id=_uuid(rng),
                conversation_id=conversation_id,
                message_id=_uuid(rng),
                sequence=sequence,
                sent_at=sent_at,
                channel=channel,
                author=author,
                text=template.format_map(slots),
                customer=customer,
            )
        )

    return Conversation(events=tuple(events), language=language, topic=topic, mood=mood)


def format_eur(amount: Decimal, language: Language) -> str:
    """Write an amount the way each language does: ``€29.99`` in English, ``29,99 €`` in French."""
    text = f"{amount:.2f}"
    return f"{text.replace('.', ',')} €" if language is Language.FR else f"€{text}"


def _slot_values(rng: random.Random, language: Language, plan: Plan) -> dict[str, str]:
    countries = ROAMING_COUNTRIES_FR if language is Language.FR else ROAMING_COUNTRIES_EN
    extra_charge = Decimal(rng.randint(500, 6_000)) / 100
    return {
        "operator": OPERATOR_NAME,
        "plan": plan.name,
        "price": format_eur(plan.monthly_price_eur, language),
        "amount": format_eur(extra_charge, language),
        "city": rng.choice(CITIES),
        "country": rng.choice(countries),
        "days": str(rng.randint(2, 7)),
    }


def _weighted_choice[T](rng: random.Random, weights: Mapping[T, float]) -> T:
    options = list(weights)
    return rng.choices(options, weights=[weights[o] for o in options])[0]


def _uuid(rng: random.Random) -> UUID:
    """A random (version 4) UUID drawn from ``rng``, so it is reproducible."""
    return UUID(int=rng.getrandbits(128), version=4)
