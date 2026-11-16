import json
import logging
import sys

from sentio_simulator.logging_json import JsonFormatter


def make_record(**extra: object) -> logging.LogRecord:
    record = logging.LogRecord(
        name="sentio_simulator",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="messages published: %d",
        args=(50,),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_record_is_one_line_of_json_with_the_basic_fields() -> None:
    line = JsonFormatter("simulator").format(make_record())

    entry = json.loads(line)
    assert "\n" not in line
    assert entry["level"] == "INFO"
    assert entry["service"] == "simulator"
    assert entry["logger"] == "sentio_simulator"
    assert entry["message"] == "messages published: 50"
    assert entry["time"].endswith("+00:00")


def test_extra_fields_are_included() -> None:
    entry = json.loads(JsonFormatter("simulator").format(make_record(topic="t", total=7)))

    assert entry["topic"] == "t"
    assert entry["total"] == 7


def test_values_json_cannot_encode_are_written_as_text() -> None:
    entry = json.loads(JsonFormatter("simulator").format(make_record(started=object())))

    assert entry["started"].startswith("<object object")


def test_exception_is_included() -> None:
    try:
        raise RuntimeError("broker unreachable")
    except RuntimeError:
        record = make_record()
        record.exc_info = sys.exc_info()

    entry = json.loads(JsonFormatter("simulator").format(record))

    assert "RuntimeError: broker unreachable" in entry["exception"]


def test_accents_are_kept_readable() -> None:
    line = JsonFormatter("simulator").format(make_record(city="Genève"))

    assert "Genève" in line
