"""Protocols for the auger lift driver and the optional hopper-full sensor."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = ["HopperSensor", "LiftDriver"]


@runtime_checkable
class LiftDriver(Protocol):
    """Minimal interface for the auger motor (single-direction PWM via MOSFET).

    Duty is a normalised float in ``[0.0, 1.0]`` driving the MOSFET/L298N enable.
    The auger runs slow and continuous; no precision or direction control needed.
    """

    def set_duty(self, fraction: float) -> None:
        """Drive the auger at ``fraction`` duty in ``[0.0, 1.0]``.

        Raises
        ------
        ValueError
            If ``fraction`` is outside ``[0.0, 1.0]``.
        """
        ...

    def off(self) -> None:
        """Stop the auger (duty 0)."""
        ...


@runtime_checkable
class HopperSensor(Protocol):
    """Optional hopper-full endstop. ``is_full()`` gates the auger on/off."""

    def is_full(self) -> bool:
        """Return ``True`` when the hopper is full and the auger should stop."""
        ...
