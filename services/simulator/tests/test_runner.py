import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta
from itertools import islice

import pytest

from sentio_schemas import RawMessageEvent
from sentio_simulator.runner import run
from sentio_simulator.stream import message_stream

START = datetime(2026, 11, 16, 9, 0, tzinfo=UTC)


class FakePublisher:
    """Keeps published events in memory instead of sending them to Kafka."""

    def __init__(self, stop_after: int | None = None, stop: asyncio.Event | None = None) -> None:
        self.published: list[RawMessageEvent] = []
        self._stop_after = stop_after
        self._stop = stop

    async def publish(self, event: RawMessageEvent) -> None:
        self.published.append(event)
        if self._stop and self._stop_after is not None and len(self.published) >= self._stop_after:
            self._stop.set()


def events(n: int) -> list[RawMessageEvent]:
    return list(islice(message_stream(1, START, 5.0), n))


def test_publishes_every_due_event_in_order() -> None:
    sample = events(20)
    publisher = FakePublisher()
    far_future = START + timedelta(days=30)  # every event is already due: no waiting

    count = asyncio.run(run(iter(sample), publisher, asyncio.Event(), now=lambda: far_future))

    assert count == 20
    assert publisher.published == sample


def test_stops_when_the_stop_event_is_set() -> None:
    async def scenario() -> FakePublisher:
        stop = asyncio.Event()
        publisher = FakePublisher(stop_after=5, stop=stop)
        far_future = START + timedelta(days=30)
        await run(message_stream(1, START, 5.0), publisher, stop, now=lambda: far_future)
        return publisher

    publisher = asyncio.run(scenario())

    assert len(publisher.published) == 5


def test_stop_interrupts_the_wait_for_a_future_message() -> None:
    """The next message is due in one hour, but a stop request ends the wait immediately."""

    async def scenario() -> tuple[int, float]:
        stop = asyncio.Event()
        one_hour_early = START - timedelta(hours=1)
        asyncio.get_running_loop().call_later(0.05, stop.set)
        began = time.monotonic()
        count = await run(iter(events(3)), FakePublisher(), stop, now=lambda: one_hour_early)
        return count, time.monotonic() - began

    count, elapsed = asyncio.run(scenario())

    assert count == 0
    assert elapsed < 2


def test_waits_until_a_message_is_due() -> None:
    """A message due in 0.2 s is not published before then."""
    event = events(1)[0]
    clock_start = time.monotonic()

    def now() -> datetime:
        return (
            event.sent_at
            - timedelta(seconds=0.2)
            + timedelta(seconds=time.monotonic() - clock_start)
        )

    publisher = FakePublisher()
    count = asyncio.run(run(iter([event]), publisher, asyncio.Event(), now=now))

    assert count == 1
    assert time.monotonic() - clock_start >= 0.19


def test_logs_a_summary(caplog: pytest.LogCaptureFixture) -> None:
    far_future = START + timedelta(days=30)
    with caplog.at_level(logging.INFO, logger="sentio_simulator.runner"):
        asyncio.run(
            run(
                iter(events(3)),
                FakePublisher(),
                asyncio.Event(),
                now=lambda: far_future,
                summary_every_seconds=0,
            )
        )

    summaries = [r for r in caplog.records if r.getMessage() == "messages published"]
    assert summaries
    assert summaries[-1].__dict__["total"] == 3


def test_publisher_errors_are_not_swallowed() -> None:
    class BrokenPublisher:
        async def publish(self, event: RawMessageEvent) -> None:
            raise ConnectionError("broker unreachable")

    far_future = START + timedelta(days=30)
    with pytest.raises(ConnectionError, match="broker unreachable"):
        asyncio.run(
            run(iter(events(1)), BrokenPublisher(), asyncio.Event(), now=lambda: far_future)
        )
