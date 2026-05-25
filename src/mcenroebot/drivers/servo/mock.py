"""MockServoDriver — in-memory servo driver for unit tests."""

from __future__ import annotations

__all__ = ["MockServoDriver"]


class MockServoDriver:
    """In-memory ServoDriver that records every write for test assertions.

    This mock validates ``angle_deg`` the same way the real driver does so
    that tests against the mock are honest about what values the Pi hardware
    would accept.

    Note: channel range is **not** validated here because the mock has no
    concept of ``channel_count`` — it is intentionally lenient about config
    it doesn't have, strict only about behaviour that matters (angle range).

    Convention: ``history`` records only successful ``write_angle`` calls,
    in the order they were made.  Calls that raise ``ValueError`` are NOT
    appended.
    """

    def __init__(self) -> None:
        self._history: list[tuple[int, float]] = []

    def write_angle(self, channel: int, angle_deg: float) -> None:
        """Record ``(channel, angle_deg)`` if the angle is valid.

        Raises
        ------
        ValueError
            If ``angle_deg`` is outside ``[0, 180]``.
        """
        if not (0.0 <= angle_deg <= 180.0):
            raise ValueError(f"angle_deg {angle_deg} out of range [0, 180]")
        self._history.append((channel, angle_deg))

    @property
    def history(self) -> list[tuple[int, float]]:
        """Return a defensive copy of the write history.

        Mutating the returned list does NOT affect internal state.
        """
        return list(self._history)
