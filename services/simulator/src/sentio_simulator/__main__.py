"""Entry point: ``python -m sentio_simulator``.

This is the only place with side effects: it reads the environment and the clock, picks a seed,
listens for shutdown signals and connects to Redpanda. Everything it calls is tested on its own.
"""

import asyncio
import contextlib
import logging
import os
import random
import signal
import sys

from sentio_simulator.config import Settings
from sentio_simulator.generator import GeneratorConfig
from sentio_simulator.logging_json import configure_logging
from sentio_simulator.publisher import KafkaPublisher
from sentio_simulator.runner import run, utc_now
from sentio_simulator.stream import live_message_stream

logger = logging.getLogger("sentio_simulator")


async def serve(settings: Settings) -> None:
    seed = settings.seed if settings.seed is not None else random.SystemRandom().getrandbits(32)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        # Docker sends SIGTERM on `docker compose stop`; Ctrl+C sends SIGINT.
        # Not supported on Windows, where Ctrl+C cancels the program instead (also handled).
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)

    logger.info(
        "simulator starting",
        extra={
            "kafka_bootstrap_servers": settings.kafka_bootstrap_servers,
            "topic": settings.topic,
            "messages_per_second": settings.messages_per_second,
            "french_share": settings.french_share,
            "seed": seed,
        },
    )
    events = live_message_stream(
        seed=seed,
        now=utc_now(),
        messages_per_second=settings.messages_per_second,
        config=GeneratorConfig(french_share=settings.french_share),
    )
    async with KafkaPublisher(settings.kafka_bootstrap_servers, settings.topic) as publisher:
        published = await run(events, publisher, stop)
    logger.info("simulator stopped", extra={"messages_published": published})


def main() -> int:
    configure_logging("simulator", "INFO")
    try:
        settings = Settings.from_env(os.environ)
    except ValueError as error:
        logger.error("invalid configuration", extra={"error": str(error)})
        return 2
    logging.getLogger().setLevel(settings.log_level)

    try:
        asyncio.run(serve(settings))
    except KeyboardInterrupt:
        logger.info("simulator interrupted")
    except Exception:
        logger.exception("simulator crashed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
