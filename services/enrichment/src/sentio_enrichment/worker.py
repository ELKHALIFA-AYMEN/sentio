"""The service loop: read a batch, process it, publish the results, then commit.

The order of these steps gives the delivery guarantee (at least once, see docs/adr/0004):
an input offset is committed only after its output has been acknowledged by the broker.
If the service stops anywhere before the commit, the batch is read again on restart:
a message can be published twice, never lost.
"""

import asyncio
import logging
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from sentio_enrichment.enricher import Enricher
from sentio_enrichment.processing import InputRecord, OutputMessage, Routing, process

logger = logging.getLogger(__name__)

Partition = tuple[str, int]
"""(topic, partition)."""


class Source(Protocol):
    """Where messages are read from. Tests use an in-memory fake."""

    async def poll(self) -> Sequence[InputRecord]:
        """The next batch, possibly empty after a short wait."""
        ...

    async def commit(self, offsets: Mapping[Partition, int]) -> None:
        """Record, per partition, the offset of the next message to read."""
        ...


class Sink(Protocol):
    """Where results are published. Tests use an in-memory fake."""

    async def send_all(self, messages: Sequence[OutputMessage]) -> None:
        """Publish ``messages`` in order; return once the broker has acknowledged all of them."""
        ...


@dataclass(slots=True)
class Stats:
    processed: int = 0
    enriched: int = 0
    dead_lettered: int = 0


def utc_now() -> datetime:
    return datetime.now(UTC)


def next_offsets(records: Sequence[InputRecord]) -> dict[Partition, int]:
    """Per partition, the offset to commit: the one after the last record read."""
    offsets: dict[Partition, int] = {}
    for record in records:
        partition = (record.topic, record.partition)
        offsets[partition] = max(offsets.get(partition, 0), record.offset + 1)
    return offsets


async def run(
    source: Source,
    sink: Sink,
    enricher: Enricher,
    routing: Routing,
    stop: asyncio.Event,
    now: Callable[[], datetime] = utc_now,
    summary_every_seconds: float = 10.0,
) -> Stats:
    """Process batches until ``stop`` is set. A batch in progress is always finished first."""
    stats = Stats()
    last_summary_at = time.monotonic()
    processed_at_last_summary = 0

    while not stop.is_set():
        records = await source.poll()
        if not records:
            continue

        outputs = [process(record, enricher, routing, now()) for record in records]
        for record, output in zip(records, outputs, strict=True):
            if output.topic == routing.dlq_topic:
                stats.dead_lettered += 1
                headers = dict(output.headers)
                logger.warning(
                    "message sent to the dead-letter queue",
                    extra={
                        "reason": headers["dlq.reason"].decode(),
                        "error": headers["dlq.error"].decode(),
                        "source_partition": record.partition,
                        "source_offset": record.offset,
                    },
                )
            else:
                stats.enriched += 1
        stats.processed += len(records)

        await sink.send_all(outputs)
        await source.commit(next_offsets(records))

        elapsed = time.monotonic() - last_summary_at
        if elapsed >= summary_every_seconds:
            done = stats.processed - processed_at_last_summary
            logger.info(
                "messages processed",
                extra={
                    "messages": done,
                    "messages_per_second": round(done / elapsed, 2) if elapsed > 0 else None,
                    "total": stats.processed,
                    "enriched": stats.enriched,
                    "dead_lettered": stats.dead_lettered,
                },
            )
            last_summary_at = time.monotonic()
            processed_at_last_summary = stats.processed

    return stats
