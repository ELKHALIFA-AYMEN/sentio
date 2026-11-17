from dataclasses import dataclass

from sentio_enrichment import InputRecord
from sentio_enrichment.kafka import to_input_records


@dataclass(frozen=True)
class FakeConsumerRecord:
    """Same fields as aiokafka's ConsumerRecord (plus some the service ignores)."""

    topic: str
    partition: int
    offset: int
    key: bytes | None
    value: bytes | None
    timestamp: int = 0


def test_records_of_every_partition_are_kept_in_order() -> None:
    batches = [
        [FakeConsumerRecord("t", 0, 5, b"a", b"1"), FakeConsumerRecord("t", 0, 6, b"a", b"2")],
        [FakeConsumerRecord("t", 1, 9, None, None)],
    ]

    assert to_input_records(batches) == [
        InputRecord("t", 0, 5, b"a", b"1"),
        InputRecord("t", 0, 6, b"a", b"2"),
        InputRecord("t", 1, 9, None, None),
    ]
