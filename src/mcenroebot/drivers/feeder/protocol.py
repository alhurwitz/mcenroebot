"""FeederDriver protocol — the minimal interface every escapement driver satisfies."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = ["FeederDriver"]


@runtime_checkable
class FeederDriver(Protocol):
    """Minimal interface for metering balls out of the hopper, one at a time.

    The v1 escapement is a continuous-rotation servo spinning a single-pocket
    indexing disk at a fixed rate — feed rate is geometric (one pocket = one
    ball per revolution), so ``set_rate`` is the primary control. ``fire`` is
    the index-upgrade path (one ball per call via an endstop) and is optional:
    v1 drivers raise ``NotImplementedError``.
    """

    def set_rate(self, balls_per_min: float) -> None:
        """Spin the escapement disk at the speed that feeds ``balls_per_min``.

        Raises
        ------
        ValueError
            If ``balls_per_min`` is negative.
        """
        ...

    def stop(self) -> None:
        """Stop the escapement disk (throttle 0)."""
        ...

    def fire(self) -> None:
        """Release exactly one ball (index-upgrade path).

        Raises
        ------
        NotImplementedError
            On v1 sensorless drivers that only support ``set_rate``.
        """
        ...
