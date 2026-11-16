"""Turns generated conversations into one continuous, time-ordered stream of messages.

Like the generator, this is pure: given a seed and a start time, the stream is always the same.
It does not wait and does not send anything; it only says *which* message comes next and *when*.
"""

import heapq
import random
from collections.abc import Iterator
from datetime import datetime, timedelta
from itertools import dropwhile

from sentio_schemas import RawMessageEvent
from sentio_simulator.generator import (
    CLOSING_PROBABILITY,
    FOLLOW_UP_PROBABILITY,
    REPLY_DELAY_SECONDS,
    GeneratorConfig,
    generate_conversation,
)

EXPECTED_MESSAGES_PER_CONVERSATION = 2 + FOLLOW_UP_PROBABILITY * (1 + CLOSING_PROBABILITY)
"""Opener + agent reply, plus the optional follow-up and closing (about 3.35 messages)."""

MAX_CONVERSATION_DURATION = timedelta(
    seconds=3 * max(longest for _, longest in REPLY_DELAY_SECONDS.values())
)
"""Longest possible conversation: 4 messages, so 3 delays of the slowest channel (1 hour)."""


def message_stream(
    seed: int,
    started_at: datetime,
    messages_per_second: float,
    config: GeneratorConfig | None = None,
) -> Iterator[RawMessageEvent]:
    """Yield messages of overlapping conversations, ordered by ``sent_at``, forever.

    New conversations start at random moments (a Poisson process), at the rate needed to reach
    ``messages_per_second`` on average. Each conversation's messages are then spread over time
    (seconds in a chat, minutes by e-mail), so messages of many conversations are interleaved,
    as in a real contact centre.

    The stream starts empty: it reaches its target rate once the first conversations are complete.
    Use :func:`live_message_stream` to get the target rate from the first second.
    """
    if messages_per_second <= 0:
        raise ValueError("messages_per_second must be positive")
    rng = random.Random(seed)
    conversations_per_second = messages_per_second / EXPECTED_MESSAGES_PER_CONVERSATION
    next_start = started_at
    # Messages generated but not yet due, ordered by (sent_at, tie-breaker).
    pending: list[tuple[datetime, int, RawMessageEvent]] = []
    order = 0

    while True:
        # Generate conversations until the next one would start after the earliest pending message:
        # then that message is guaranteed to be the next one in time.
        while not pending or next_start <= pending[0][0]:
            conversation = generate_conversation(rng.getrandbits(64), next_start, config)
            for event in conversation.events:
                heapq.heappush(pending, (event.sent_at, order, event))
                order += 1
            next_start += timedelta(seconds=rng.expovariate(conversations_per_second))
        yield heapq.heappop(pending)[2]


def live_message_stream(
    seed: int,
    now: datetime,
    messages_per_second: float,
    config: GeneratorConfig | None = None,
) -> Iterator[RawMessageEvent]:
    """Like :func:`message_stream`, but already at full speed at ``now``.

    The simulation starts one conversation duration in the past and skips every message sent
    before ``now``. Conversations that were already in progress are therefore joined midway,
    just as when monitoring starts in a busy contact centre.
    """
    events = message_stream(seed, now - MAX_CONVERSATION_DURATION, messages_per_second, config)
    return dropwhile(lambda event: event.sent_at < now, events)
