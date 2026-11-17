import asyncio
import logging
from collections.abc import Mapping, Sequence

import pytest
from enrichment_samples import NOW, make_enricher, raw_record, record

from sentio_enrichment import InputRecord, OutputMessage, Routing
from sentio_enrichment.worker import Partition, Stats, next_offsets, run

ROUTING = Routing(output_topic="conversations.enriched", dlq_topic="conversations.dlq")


class FakeBroker:
    """Plays both sides of Kafka in memory and records every call, in order.

    ``poll`` returns the given batches one by one, then sets ``stop``: the worker ends once
    everything has been processed.
    """

    def __init__(
        self, batches: list[list[InputRecord]], stop: asyncio.Event, fail_sends: bool = False
    ) -> None:
        self._batches = list(batches)
        self._stop = stop
        self._fail_sends = fail_sends
        self.calls: list[str] = []
        self.sent: list[OutputMessage] = []
        self.committed: list[dict[Partition, int]] = []

    async def poll(self) -> Sequence[InputRecord]:
        self.calls.append("poll")
        if not self._batches:
            self._stop.set()
            return []
        return self._batches.pop(0)

    async def send_all(self, messages: Sequence[OutputMessage]) -> None:
        self.calls.append("send")
        if self._fail_sends:
            raise ConnectionError("broker unreachable")
        self.sent.extend(messages)

    async def commit(self, offsets: Mapping[Partition, int]) -> None:
        self.calls.append("commit")
        self.committed.append(dict(offsets))


def run_worker(broker: FakeBroker, stop: asyncio.Event) -> Stats:
    return asyncio.run(run(broker, broker, make_enricher(), ROUTING, stop, now=lambda: NOW))


def test_every_message_is_published_in_order_then_committed() -> None:
    stop = asyncio.Event()
    batch = [raw_record(offset=i) for i in range(5)]
    broker = FakeBroker([batch], stop)

    stats = run_worker(broker, stop)

    assert [m.topic for m in broker.sent] == ["conversations.enriched"] * 5
    assert broker.committed == [{("conversations.raw", 0): 5}]
    assert stats == Stats(processed=5, enriched=5, dead_lettered=0)


def test_offsets_are_committed_only_after_the_results_are_published() -> None:
    stop = asyncio.Event()
    broker = FakeBroker([[raw_record(offset=0)], [raw_record(offset=1)]], stop)

    run_worker(broker, stop)

    assert broker.calls == ["poll", "send", "commit", "poll", "send", "commit", "poll"]


def test_nothing_is_committed_when_publishing_fails() -> None:
    """The broker is down: the service stops with an error and the batch will be read again."""
    stop = asyncio.Event()
    broker = FakeBroker([[raw_record()]], stop, fail_sends=True)

    with pytest.raises(ConnectionError):
        run_worker(broker, stop)

    assert broker.committed == []


def test_invalid_message_goes_to_the_dlq_and_the_stream_goes_on() -> None:
    stop = asyncio.Event()
    batch = [raw_record(offset=0), record(b"garbage", offset=1), raw_record(offset=2)]
    broker = FakeBroker([batch], stop)

    stats = run_worker(broker, stop)

    assert [m.topic for m in broker.sent] == [
        "conversations.enriched",
        "conversations.dlq",
        "conversations.enriched",
    ]
    # The invalid message is committed too: it is safely parked in the DLQ.
    assert broker.committed == [{("conversations.raw", 0): 3}]
    assert stats == Stats(processed=3, enriched=2, dead_lettered=1)


def test_dlq_message_is_logged_as_a_warning(caplog: pytest.LogCaptureFixture) -> None:
    stop = asyncio.Event()
    broker = FakeBroker([[record(b"garbage", offset=7)]], stop)

    with caplog.at_level(logging.WARNING):
        run_worker(broker, stop)

    [entry] = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert entry.getMessage() == "message sent to the dead-letter queue"
    assert entry.__dict__["reason"] == "invalid_event"
    assert entry.__dict__["source_offset"] == 7


def test_empty_polls_publish_and_commit_nothing() -> None:
    stop = asyncio.Event()
    broker = FakeBroker([[], [], []], stop)

    stats = run_worker(broker, stop)

    assert broker.sent == []
    assert broker.committed == []
    assert stats == Stats()


def test_does_not_poll_once_stopped() -> None:
    stop = asyncio.Event()
    stop.set()
    broker = FakeBroker([[raw_record()]], stop)

    run_worker(broker, stop)

    assert broker.calls == []


def test_batch_in_progress_is_finished_when_stop_is_requested() -> None:
    stop = asyncio.Event()
    broker = FakeBroker(
        [[raw_record(offset=0), raw_record(offset=1)], [raw_record(offset=2)]], stop
    )
    original_poll = broker.poll

    async def poll_then_stop() -> Sequence[InputRecord]:
        records = await original_poll()
        stop.set()  # SIGTERM arrives while the first batch is being processed
        return records

    broker.poll = poll_then_stop  # type: ignore[method-assign]
    run_worker(broker, stop)

    assert len(broker.sent) == 2
    assert broker.committed == [{("conversations.raw", 0): 2}]


def test_next_offsets_are_one_past_the_last_record_of_each_partition() -> None:
    records = [
        raw_record(offset=10, partition=0),
        raw_record(offset=11, partition=0),
        raw_record(offset=3, partition=2),
    ]

    assert next_offsets(records) == {("conversations.raw", 0): 12, ("conversations.raw", 2): 4}
