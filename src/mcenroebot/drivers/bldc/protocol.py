"""BLDCDriver protocol — the minimal interface every BLDC/ESC driver must satisfy."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = ["BLDCDriver"]


@runtime_checkable
class BLDCDriver(Protocol):
    """Minimal interface for driving a brushless motor via an ESC.

    Throttle is expressed as a normalised float in ``[0.0, 1.0]``, where
    0.0 = idle (1000 µs ESC pulse) and 1.0 = full throttle (2000 µs).

    Lifecycle: ``arm()`` → one or more ``set_throttle()`` calls → ``disarm()``.
    Calling ``set_throttle()`` before ``arm()`` must raise ``RuntimeError``.
    """

    def arm(self) -> None:
        """Send the idle signal (1000 µs) so the ESC arms and enables throttle."""
        ...

    def set_throttle(self, throttle: float) -> None:
        """Set throttle to ``throttle`` in ``[0.0, 1.0]``.

        Raises
        ------
        RuntimeError
            If called before ``arm()``.
        ValueError
            If ``throttle`` is outside ``[0.0, 1.0]``.
        """
        ...

    def disarm(self) -> None:
        """Drop throttle to 0 µs and clear the armed flag."""
        ...
