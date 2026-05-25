"""MockBLDCDriver — in-memory BLDC/ESC driver for unit tests."""

from __future__ import annotations

__all__ = ["MockBLDCDriver"]


class MockBLDCDriver:
    """In-memory BLDCDriver recording throttle history and armed state.

    This mock validates inputs the same way the real driver does so that
    tests against the mock are honest about what values the Pi hardware
    would accept.

    Convention (throttle_history):
        - ``arm()`` does NOT append to ``throttle_history``.
        - ``set_throttle(t)`` appends ``t`` for every successful call.
        - ``disarm()`` appends ``0.0`` to show the throttle was zeroed.
        - Calls that raise do NOT append.
    """

    def __init__(self) -> None:
        self._armed: bool = False
        self._history: list[float] = []

    @property
    def armed(self) -> bool:
        """``True`` between a successful ``arm()`` and the next ``disarm()``."""
        return self._armed

    @property
    def throttle_history(self) -> list[float]:
        """Defensive copy of the throttle history.

        Records each successful ``set_throttle`` value plus a trailing
        ``0.0`` appended by ``disarm()``.  ``arm()`` does not append.

        Mutating the returned list does NOT affect internal state.
        """
        return list(self._history)

    def arm(self) -> None:
        """Set the armed flag.  Does not append to ``throttle_history``."""
        self._armed = True

    def set_throttle(self, throttle: float) -> None:
        """Record ``throttle`` if the driver is armed and the value is valid.

        Raises
        ------
        RuntimeError
            If called before ``arm()``.
        ValueError
            If ``throttle`` is outside ``[0.0, 1.0]``.
        """
        if not self._armed:
            raise RuntimeError("BLDC must be armed before set_throttle")
        if not (0.0 <= throttle <= 1.0):
            raise ValueError(f"throttle {throttle} out of range [0, 1]")
        self._history.append(throttle)

    def disarm(self) -> None:
        """Clear the armed flag and append ``0.0`` to ``throttle_history``."""
        self._history.append(0.0)
        self._armed = False
