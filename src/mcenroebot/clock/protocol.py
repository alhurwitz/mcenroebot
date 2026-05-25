"""Clock protocol — the minimal timing interface both real and fake clocks satisfy."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = ["Clock"]


@runtime_checkable
class Clock(Protocol):
    """Minimal timing interface for any code that needs to sleep or read time.

    Both ``SystemClock`` and ``FakeClock`` satisfy this protocol, so any
    component that accepts a ``Clock`` is trivially testable without patching
    builtins or spinning up a real event loop.
    """

    def now(self) -> float:
        """Return the current time in seconds (monotonic source)."""
        ...

    async def sleep(self, seconds: float) -> None:
        """Suspend execution for *seconds* seconds.

        Raises
        ------
        ValueError
            If *seconds* is negative.
        """
        ...
