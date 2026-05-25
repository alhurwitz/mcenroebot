"""ServoDriver protocol — the minimal interface every servo driver must satisfy."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = ["ServoDriver"]


@runtime_checkable
class ServoDriver(Protocol):
    """Minimal interface for writing angles to a servo channel.

    Both ``PCA9685ServoDriver`` and ``MockServoDriver`` satisfy this protocol,
    so any component that accepts a ``ServoDriver`` is trivially testable
    without real hardware.
    """

    def write_angle(self, channel: int, angle_deg: float) -> None:
        """Drive ``channel`` to ``angle_deg`` degrees.

        Implementations clamp/validate to the servo's physical range.

        Raises
        ------
        ValueError
            If ``angle_deg`` is outside ``[0, 180]``.
        """
        ...
