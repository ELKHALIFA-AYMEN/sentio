"""Incident scenarios: a temporary change in the traffic, like a real problem would cause.

A *scenario* describes what an incident looks like (which topic it hits, how unhappy customers are,
how much more they write). An *incident* is a scenario scheduled between two moments. While an
incident is active, the stream generates new conversations with the scenario's configuration;
before and after, traffic is normal.

Like the generator, everything here is pure: no clock, no randomness.
"""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from itertools import pairwise
from types import MappingProxyType

from sentio_schemas import TopicLabel
from sentio_simulator.generator import GeneratorConfig, MoodWeights


class ScenarioName(StrEnum):
    NETWORK_OUTAGE = "network_outage"
    BILLING_ERROR = "billing_error"


@dataclass(frozen=True, slots=True)
class Scenario:
    """How an incident changes the traffic."""

    name: ScenarioName
    topic: TopicLabel
    """The topic customers suddenly write about."""
    topic_share: float
    """Share of new conversations about ``topic`` (the other topics keep their proportions)."""
    mood_weights: MoodWeights
    """Odds of (negative, neutral, positive) for conversations about ``topic``."""
    rate_multiplier: float
    """How many times more messages are sent (customers contact support more during an incident)."""
    city: str | None = None
    extra_charge_eur: Decimal | None = None

    def __post_init__(self) -> None:
        if not 0.0 < self.topic_share <= 1.0:
            raise ValueError("topic_share must be > 0 and <= 1")
        if self.rate_multiplier < 1.0:
            raise ValueError("rate_multiplier must be >= 1")

    def apply(self, config: GeneratorConfig) -> GeneratorConfig:
        """The configuration to use while the incident is active, starting from ``config``."""
        others = {topic: w for topic, w in config.topic_weights.items() if topic is not self.topic}
        others_total = sum(others.values())
        if others_total > 0:
            topic_weights = {
                topic: w / others_total * (1 - self.topic_share) for topic, w in others.items()
            }
            topic_weights[self.topic] = self.topic_share
        else:
            topic_weights = {self.topic: 1.0}
        return replace(
            config,
            topic_weights=MappingProxyType(topic_weights),
            mood_weights=MappingProxyType({**config.mood_weights, self.topic: self.mood_weights}),
            city=self.city if self.city is not None else config.city,
            extra_charge_eur=(
                self.extra_charge_eur
                if self.extra_charge_eur is not None
                else config.extra_charge_eur
            ),
        )


SCENARIOS: Mapping[ScenarioName, Scenario] = MappingProxyType(
    {
        # The mobile network goes down in one city: many customers of that city complain at once.
        ScenarioName.NETWORK_OUTAGE: Scenario(
            name=ScenarioName.NETWORK_OUTAGE,
            topic=TopicLabel.NETWORK,
            topic_share=0.60,
            mood_weights=(0.90, 0.08, 0.02),
            rate_multiplier=1.5,
            city="Lyon",
        ),
        # A wrong fee is added to many invoices: customers ask why they were charged the same sum.
        ScenarioName.BILLING_ERROR: Scenario(
            name=ScenarioName.BILLING_ERROR,
            topic=TopicLabel.BILLING,
            topic_share=0.60,
            mood_weights=(0.85, 0.13, 0.02),
            rate_multiplier=1.3,
            extra_charge_eur=Decimal("12.90"),
        ),
    }
)


@dataclass(frozen=True, slots=True)
class Incident:
    """A scenario active from ``starts_at`` (included) to ``ends_at`` (excluded)."""

    scenario: Scenario
    starts_at: datetime
    ends_at: datetime

    def __post_init__(self) -> None:
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise ValueError("incident times must be timezone-aware")
        if self.ends_at <= self.starts_at:
            raise ValueError("an incident must end after it starts")

    @classmethod
    def starting_after(
        cls, name: ScenarioName, now: datetime, delay: timedelta, duration: timedelta
    ) -> "Incident":
        """The scenario ``name``, starting ``delay`` after ``now`` and lasting ``duration``."""
        starts_at = now + delay
        return cls(SCENARIOS[name], starts_at, starts_at + duration)

    def is_active(self, at: datetime) -> bool:
        return self.starts_at <= at < self.ends_at


def check_no_overlap(incidents: tuple[Incident, ...]) -> None:
    """Only one incident can be active at a time: reject overlapping incidents."""
    ordered = sorted(incidents, key=lambda incident: incident.starts_at)
    for earlier, later in pairwise(ordered):
        if later.starts_at < earlier.ends_at:
            raise ValueError("incidents must not overlap")
