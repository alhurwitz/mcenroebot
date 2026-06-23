"""MockFeederDriver — in-memory escapement driver for unit tests."""

from __future__ import annotations

__all__ = ["MockFeederDriver"]


class MockFeederDriver:
    """In-memory FeederDriver that records every call in order for assertions.

    Unlike the real v1 driver, the mock records ``fire()`` rather than raising
    ``NotImplementedError`` — so higher layers can be tested against either the
    sensorless ``set_rate`` path or the future index-upgrade ``fire`` path.

    Convention (``calls``):
        - ``set_rate(bpm)`` appends ``("set_rate", bpm)`` for valid rates.
        - ``stop()`` appends ``("stop", None)``.
        - ``fire()`` appends ``("fire", None)``.
        - Calls that raise ``ValueError`` are NOT recorded.
    """

    def __init__(self) -> None:
        self._calls: list[tuple[str, float | None]] = []

    @property
    def calls(self) -> list[tuple[str, float | None]]:
        """Defensive copy of the call history; mutating it does not affect state."""
        return list(self._calls)

    def set_rate(self, balls_per_min: float) -> None:
        """Record ``("set_rate", balls_per_min)`` if the rate is valid.

        Raises
        ------
        ValueError
            If ``balls_per_min`` is negative.
        """
        if balls_per_min < 0.0:
            raise ValueError(f"balls_per_min={balls_per_min} must be >= 0")
        self._calls.append(("set_rate", balls_per_min))

    def stop(self) -> None:
        """Record a ``("stop", None)`` call."""
        self._calls.append(("stop", None))

    def fire(self) -> None:
        """Record a ``("fire", None)`` call (index-upgrade path)."""
        self._calls.append(("fire", None))
