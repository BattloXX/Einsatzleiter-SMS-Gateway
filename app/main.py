"""Einsatzleiter SMS-Gateway – Einstiegspunkt.

Startet den WebSocket-Client und behandelt SIGINT/SIGTERM sauber.
"""
import asyncio
import logging
import signal
import sys

from app.gateway_client import run_forever

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("sms-gateway")


async def _main() -> None:
    stop = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            # Windows unterstützt add_signal_handler nicht für alle Signale
            pass

    logger.info("Einsatzleiter SMS-Gateway gestartet")
    await run_forever(stop)


if __name__ == "__main__":
    asyncio.run(_main())
