"""Entry point for `python -m mcenroebot.coordinator`."""

import asyncio

from mcenroebot.coordinator.feeder import _demo

if __name__ == "__main__":
    asyncio.run(_demo())
