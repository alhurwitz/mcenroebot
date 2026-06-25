"""GPIO hopper-full sensor — reads an endstop via RPi.GPIO (Pi only)."""

from __future__ import annotations

__all__ = ["GpioHopperSensor"]


class GpioHopperSensor:
    """Real HopperSensor reading a GPIO endstop. Lazy ``RPi.GPIO`` import.

    Args:
        pin: BCM pin number the endstop is wired to.
        active_high: if True, a HIGH reading means full; else LOW means full.
    """

    def __init__(self, pin: int, active_high: bool = True) -> None:
        try:
            import RPi.GPIO as GPIO
        except ImportError as exc:
            raise ImportError(
                "RPi.GPIO is not installed. Install the Pi optional extra with: uv sync --extra pi"
            ) from exc

        self._pin = pin  # pragma: no cover
        self._active_high = active_high  # pragma: no cover
        self._GPIO = GPIO  # pragma: no cover
        GPIO.setmode(GPIO.BCM)  # pragma: no cover
        GPIO.setup(pin, GPIO.IN)  # pragma: no cover

    def is_full(self) -> bool:  # pragma: no cover
        """Return True when the endstop reads its active level."""
        reading = self._GPIO.input(self._pin)
        return bool(reading) if self._active_high else not bool(reading)
