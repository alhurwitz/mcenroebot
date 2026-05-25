"""Deterministic clock for unit tests — never blocks, time only moves on command."""

from __future__ import annotations

__all__ = ["FakeClock"]


class FakeClock:
    """Deterministic clock for unit tests.

    Time never advances on its own — it only moves when you call
    ``sleep()`` or ``advance()``.  This means async tests that call
    ``await clock.sleep(10_000)`` complete in microseconds of real time.

    Parameters
    ----------
    start:
        The initial value returned by ``now()`` (and the baseline for
        ``elapsed``).  Defaults to ``0.0``.

    Attributes
    ----------
    elapsed : float
        Total seconds advanced since construction (i.e. ``now() - start``).
    """

    def __init__(self, start: float = 0.0) -> None:
        self._start: float = start
        self._current: float = start

    def now(self) -> float:
        """Return the internal (fake) time in seconds."""
        return self._current

    async def sleep(self, seconds: float) -> None:
        """Advance the internal clock by *seconds* without really sleeping.

        Because no real suspension occurs, async tests that use
        ``FakeClock`` run at full speed regardless of the requested
        duration.

        Raises
        ------
        ValueError
            If *seconds* is negative.
        """
        if seconds < 0:
            raise ValueError(f"sleep duration must be non-negative, got {seconds!r}")
        self._current += seconds

    def advance(self, seconds: float) -> None:
        """Synchronously advance the internal clock by *seconds*.

        Equivalent to ``asyncio.run(self.sleep(seconds))`` but synchronous,
        so it can be called from non-async test setup code.

        Raises
        ------
        ValueError
            If *seconds* is negative.
        """
        if seconds < 0:
            raise ValueError(f"advance duration must be non-negative, got {seconds!r}")
        self._current += seconds

    @property
    def elapsed(self) -> float:
        """Seconds elapsed since this clock was constructed (``now() - start``)."""
        return self._current - self._start
