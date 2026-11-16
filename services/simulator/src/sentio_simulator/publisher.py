"""Sending events to Redpanda. This is the only module that knows about Kafka."""

from types import TracebackType
from typing import Protocol, Self

from aiokafka import AIOKafkaProducer

from sentio_schemas import RawMessageEvent


class Publisher(Protocol):
    """Anything that can publish an event. Tests use an in-memory fake."""

    async def publish(self, event: RawMessageEvent) -> None: ...


def encode(event: RawMessageEvent) -> tuple[bytes, bytes]:
    """Kafka key and value for ``event``.

    The key is the conversation ID: Kafka sends all messages with the same key to the same
    partition, so the messages of a conversation are stored, and read, in order.
    """
    return str(event.conversation_id).encode(), event.model_dump_json().encode()


class KafkaPublisher:
    """Publishes events to a Kafka topic.

    Use it as ``async with KafkaPublisher(...) as publisher``: the connection is opened on entry and
    closed on exit, after the messages still buffered have been sent.
    """

    def __init__(self, bootstrap_servers: str, topic: str) -> None:
        self._topic = topic
        self._producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            client_id="sentio-simulator",
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
        # Sends whatever is still buffered, then closes the connection.
        await self._producer.stop()

    async def publish(self, event: RawMessageEvent) -> None:
        key, value = encode(event)
        await self._producer.send_and_wait(self._topic, value=value, key=key)
