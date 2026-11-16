"""The service loop: waits until each message is due, publishes it, stops cleanly when asked."""

import asyncio
import logging
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime

from sentio_schemas import RawMessageEvent
from sentio_simulator.publisher import Publisher

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(UTC)


async def run(
    events: Iterator[RawMessageEvent],
    publisher: Publisher,
    stop: asyncio.Event,
    now: Callable[[], datetime] = utc_now,
    summary_every_seconds: float = 10.0,
) -> int:
    """Publish ``events`` in real time until ``stop`` is set. Returns the number of messages sent.

    Each event is published when the clock reaches its ``sent_at``. Waiting is interrupted as
    soon as ``stop`` is set, so the service stops within milliseconds, never during a send.
    """
    published = 0
    last_summary_at = time.monotonic()
    published_at_last_summary = 0

    for event in events:
        delay = (event.sent_at - now()).total_seconds()
        if delay > 0 and await _stopped_while_waiting(stop, delay):
            break
        if stop.is_set():
            break

        await publisher.publish(event)
        published += 1
        logger.debug(
            "message published",
            extra={
                "conversation_id": str(event.conversation_id),
                "sequence": event.sequence,
                "author": event.author.value,
            },
        )

        elapsed = time.monotonic() - last_summary_at
        if elapsed >= summary_every_seconds:
            sent = published - published_at_last_summary
            logger.info(
                "messages published",
                extra={
                    "messages": sent,
                    # The clock can report 0 s between two close readings (coarse on Windows).
                    "messages_per_second": round(sent / elapsed, 2) if elapsed > 0 else None,
                    "total": published,
                },
            )
            last_summary_at = time.monotonic()
            published_at_last_summary = published

    return published


async def _stopped_while_waiting(stop: asyncio.Event, seconds: float) -> bool:
    """Wait ``seconds``, or less if ``stop`` is set first.

    Returns True if the wait ended because of ``stop``.
    """
    try:
        await asyncio.wait_for(stop.wait(), timeout=seconds)
    except TimeoutError:
        return False
    return True
