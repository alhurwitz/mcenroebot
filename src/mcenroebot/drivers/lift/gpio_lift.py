"""GPIO auger lift driver — Pi hardware-PWM into an L298N ENA (Pi only).

Used instead of ``Pca9685LiftDriver`` when there is a single PCA9685: that
board runs at 50 Hz for the servos/ESCs, but the auger wants ~1 kHz PWM, and
PCA9685 frequency is board-wide. So the auger ENA is driven from a Pi
hardware-PWM GPIO pin, independent of the PCA9685's frequency.

Direction (L298N IN1/IN2) is hardwired for single-direction lift, so this
driver only controls speed via the ENA PWM duty cycle.

``RPi.GPIO`` is imported lazily and, on a Pi 5, is provided by the ``rpi-lgpio``
shim (the legacy ``RPi.GPIO`` / ``rpi-gpio`` package is incompatible with the
Pi 5 RP1 chip). Install with ``uv sync --extra pi``.
"""

from __future__ import annotations

__all__ = ["GpioLiftDriver"]


class GpioLiftDriver:
    """Real auger driver: Pi hardware-PWM on a GPIO pin -> L298N ENA.

    Args:
        pin: BCM GPIO pin wired to the L298N ENA (hardware-PWM capable).
        frequency_hz: PWM frequency in Hz (default 1000).
    """

    def __init__(self, pin: int, frequency_hz: int = 1000) -> None:
        try:
            import RPi.GPIO as GPIO  # provided by rpi-lgpio on the Pi 5
        except ImportError as exc:
            raise ImportError(
                "RPi.GPIO is not installed. Install the Pi optional extra with: "
                "uv sync --extra pi (provides rpi-lgpio on the Pi 5)."
            ) from exc

        self._pin = pin  # pragma: no cover
        self._GPIO = GPIO  # pragma: no cover
        GPIO.setmode(GPIO.BCM)  # pragma: no cover
        GPIO.setup(pin, GPIO.OUT)  # pragma: no cover
        self._pwm = GPIO.PWM(pin, frequency_hz)  # pragma: no cover
        self._pwm.start(0.0)  # pragma: no cover

    def set_duty(self, fraction: float) -> None:  # pragma: no cover
        """Drive the auger at ``fraction`` duty in ``[0.0, 1.0]``.

        Raises
        ------
        ValueError
            If ``fraction`` is outside ``[0.0, 1.0]``.
        """
        if not (0.0 <= fraction <= 1.0):
            raise ValueError(f"duty fraction={fraction} out of range [0, 1]")
        self._pwm.ChangeDutyCycle(fraction * 100.0)

    def off(self) -> None:  # pragma: no cover
        """Stop the auger (duty 0)."""
        self._pwm.ChangeDutyCycle(0.0)
