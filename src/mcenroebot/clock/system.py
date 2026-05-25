"""Real clock backed by the OS monotonic timer and asyncio."""

from __future__ import annotations

import asyncio
import time

__all__ = ["SystemClock"]


class SystemClock:
    """Real clock backed by the OS monotonic timer and asyncio.

    ``now()`` uses ``time.monotonic()`` so that the returned values are
    suitable for *relative* timing (deltas, timeouts) regardless of NTP
    adjustments or timezone changes.

    ``sleep(seconds)`` delegates to ``asyncio.sleep`` and therefore must
    be awaited from within a running event loop.
    """

    def now(self) -> float:
        """Return ``time.monotonic()`` in seconds."""
        return time.monotonic()

    async def sleep(self, seconds: float) -> None:
        """Await ``asyncio.sleep(seconds)``.

        Raises
        ------
        ValueError
            If *seconds* is negative.
        """
        if seconds < 0:
            raise ValueError(f"sleep duration must be non-negative, got {seconds!r}")
        await asyncio.sleep(seconds)
