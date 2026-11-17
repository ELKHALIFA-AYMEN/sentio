"""Reading from and writing to Redpanda. This is the only module that knows about Kafka."""

import asyncio
import logging
from collections.abc import Iterable, Mapping, Sequence
from types import TracebackType
from typing import Protocol, Self

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, TopicPartition
from aiokafka.errors import CommitFailedError

from sentio_enrichment.processing import InputRecord, OutputMessage
from sentio_enrichment.worker import Partition

logger = logging.getLogger(__name__)

CLIENT_ID = "sentio-enrichment"


class KafkaRecord(Protocol):
    """The fields of an aiokafka ``ConsumerRecord`` that the service uses."""

    @property
    def topic(self) -> str: ...
    @property
    def partition(self) -> int: ...
    @property
    def offset(self) -> int: ...
    @property
    def key(self) -> bytes | None: ...
    @property
    def value(self) -> bytes | None: ...


def to_input_records(batches: Iterable[Sequence[KafkaRecord]]) -> list[InputRecord]:
    return [
        InputRecord(r.topic, r.partition, r.offset, r.key, r.value)
        for records in batches
        for r in records
    ]


class KafkaSource:
    """Reads a topic as a member of a consumer group, committing offsets by hand.

    Use it as ``async with KafkaSource(...) as source``: the consumer joins the group on entry
    and leaves it on exit, so its partitions are handed to another member straight away.
    """

    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        group_id: str,
        poll_timeout_ms: int = 1_000,
        max_records: int = 500,
    ) -> None:
        self._poll_timeout_ms = poll_timeout_ms
        self._max_records = max_records
        self._consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            client_id=CLIENT_ID,
            # Offsets are committed by the worker, only once the results are safely published.
            enable_auto_commit=False,
            # A new group starts at the oldest message kept by the topic, so nothing is skipped.
            auto_offset_reset="earliest",
        )

    async def __aenter__(self) -> Self:
        await self._consumer.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._consumer.stop()

    async def poll(self) -> list[InputRecord]:
        batches = await self._consumer.getmany(
            timeout_ms=self._poll_timeout_ms, max_records=self._max_records
        )
        return to_input_records(batches.values())

    async def commit(self, offsets: Mapping[Partition, int]) -> None:
        try:
            await self._consumer.commit(
                {
                    TopicPartition(topic, partition): offset
                    for (topic, partition), offset in offsets.items()
                }
            )
        except CommitFailedError:
            # The group was rebalanced while the batch was processed: these partitions now belong
            # to another member, which will read the batch again. Duplicates, but nothing lost.
            logger.warning("offset commit failed after a rebalance; the batch will be read again")


class KafkaSink:
    """Publishes messages, waiting for the broker to acknowledge them.

    Use it as ``async with KafkaSink(...) as sink``.
    """

    def __init__(self, bootstrap_servers: str) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            client_id=CLIENT_ID,
            acks="all",  # the broker confirms only once the message is safely stored
            enable_idempotence=True,  # retries never create duplicates in the topic
            linger_ms=5,  # wait up to 5 ms to group messages into one request
        )

    async def __aenter__(self) -> Self:
        await self._producer.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._producer.stop()

    async def send_all(self, messages: Sequence[OutputMessage]) -> None:
        # send() queues the message and returns a future, resolved when the broker acknowledges it.
        # Queueing them all first lets the producer send the batch in a few requests, in order.
        acknowledgements = [
            await self._producer.send(
                message.topic, value=message.value, key=message.key, headers=list(message.headers)
            )
            for message in messages
        ]
        await asyncio.gather(*acknowledgements)
