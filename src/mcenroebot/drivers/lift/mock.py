"""In-memory lift driver and hopper sensor for unit tests."""

from __future__ import annotations

__all__ = ["MockHopperSensor", "MockLiftDriver"]


class MockLiftDriver:
    """In-memory LiftDriver recording duty history for assertions.

    Validates ``fraction`` the same way the real driver does so tests are
    honest about what the hardware would accept.

    Convention (``duty_history``):
        - ``set_duty(f)`` appends ``f`` for valid values.
        - ``off()`` appends ``0.0``.
        - Calls that raise ``ValueError`` are NOT recorded.
    """

    def __init__(self) -> None:
        self._history: list[float] = []

    @property
    def duty_history(self) -> list[float]:
        """Defensive copy of the duty history; mutating it does not affect state."""
        return list(self._history)

    def set_duty(self, fraction: float) -> None:
        """Record ``fraction`` if it is within ``[0.0, 1.0]``.

        Raises
        ------
        ValueError
            If ``fraction`` is outside ``[0.0, 1.0]``.
        """
        if not (0.0 <= fraction <= 1.0):
            raise ValueError(f"duty fraction={fraction} out of range [0, 1]")
        self._history.append(fraction)

    def off(self) -> None:
        """Record a ``0.0`` duty (auger stopped)."""
        self._history.append(0.0)


class MockHopperSensor:
    """Programmable HopperSensor for tests. Set ``full`` to drive ``is_full()``."""

    def __init__(self, full: bool = False) -> None:
        self.full = full

    def is_full(self) -> bool:
        """Return the programmed ``full`` state."""
        return self.full
