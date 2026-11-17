"""Entry point: ``python -m sentio_enrichment``.

This is the only place with side effects: it reads the environment, listens for shutdown signals
and connects to Redpanda. Everything it calls is tested on its own.
"""

import asyncio
import contextlib
import logging
import os
import signal
import sys

from sentio_enrichment.config import Settings
from sentio_enrichment.enricher import MessageEnricher
from sentio_enrichment.kafka import KafkaSink, KafkaSource
from sentio_enrichment.language import LangidDetector
from sentio_enrichment.logging_json import configure_logging
from sentio_enrichment.processing import Routing
from sentio_enrichment.worker import run

logger = logging.getLogger("sentio_enrichment")


async def serve(settings: Settings) -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        # Docker sends SIGTERM on `docker compose stop`; Ctrl+C sends SIGINT.
        # Not supported on Windows, where Ctrl+C cancels the program instead (also handled).
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)

    language_detector = LangidDetector()  # loads the model once, before reading any message
    logger.info(
        "enrichment starting",
        extra={
            "kafka_bootstrap_servers": settings.kafka_bootstrap_servers,
            "input_topic": settings.input_topic,
            "output_topic": settings.output_topic,
            "dlq_topic": settings.dlq_topic,
            "group_id": settings.group_id,
            "language_model": language_detector.version,
        },
    )
    routing = Routing(output_topic=settings.output_topic, dlq_topic=settings.dlq_topic)
    async with (
        KafkaSink(settings.kafka_bootstrap_servers) as sink,
        KafkaSource(
            settings.kafka_bootstrap_servers, settings.input_topic, settings.group_id
        ) as source,
    ):
        stats = await run(source, sink, MessageEnricher(language_detector), routing, stop)
    logger.info(
        "enrichment stopped",
        extra={
            "processed": stats.processed,
            "enriched": stats.enriched,
            "dead_lettered": stats.dead_lettered,
        },
    )


def main() -> int:
    configure_logging("enrichment", "INFO")
    try:
        settings = Settings.from_env(os.environ)
    except ValueError as error:
        logger.error("invalid configuration", extra={"error": str(error)})
        return 2
    logging.getLogger().setLevel(settings.log_level)

    try:
        asyncio.run(serve(settings))
    except KeyboardInterrupt:
        logger.info("enrichment interrupted")
    except Exception:
        logger.exception("enrichment crashed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
