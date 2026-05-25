"""PCA9685 BLDC driver — real hardware implementation using adafruit_pca9685."""

from __future__ import annotations

__all__ = ["PCA9685BLDCDriver"]


class PCA9685BLDCDriver:
    """ESC PWM driver: throttle 0 → 1000 µs, throttle 1 → 2000 µs.

    The ESC expects a standard hobby-RC PWM signal at 50 Hz.  Throttle is
    mapped linearly: 0.0 → 1000 µs (arm/idle) and 1.0 → 2000 µs (full).

    The Adafruit libraries are not available on a Mac dev environment —
    they live in the ``pi`` optional extra and must be installed via
    ``uv sync --extra pi`` on the Raspberry Pi only.  This class defers
    all Adafruit imports to the constructor so importing this module never
    raises ``ImportError`` on a Mac.

    Args:
        channel: PCA9685 channel the ESC signal is wired to (default 2).
        i2c_address: I2C address of the PCA9685 board (default 0x40).
        frequency_hz: PWM frequency in Hz (default 50 — standard ESC).
    """

    def __init__(
        self,
        channel: int = 2,
        i2c_address: int = 0x40,
        frequency_hz: int = 50,
    ) -> None:
        try:
            import board
            import busio
            from adafruit_pca9685 import PCA9685
        except ImportError as exc:
            raise ImportError(
                "adafruit_pca9685 / busio / board are not installed. "
                "Install the Pi optional extra with: uv sync --extra pi"
            ) from exc

        self._channel = channel  # pragma: no cover
        self._frequency_hz = frequency_hz  # pragma: no cover
        self._armed = False  # pragma: no cover

        i2c = busio.I2C(board.SCL, board.SDA)  # pragma: no cover
        self._pca = PCA9685(i2c, address=i2c_address)  # pragma: no cover
        self._pca.frequency = frequency_hz  # pragma: no cover

    def arm(self) -> None:  # pragma: no cover
        """Send 1000 µs (idle / zero throttle) so the ESC arms."""
        self._set_pulse_width_us(1000)
        self._armed = True

    def set_throttle(self, throttle: float) -> None:  # pragma: no cover
        """Set throttle in ``[0.0, 1.0]``.

        Raises
        ------
        RuntimeError
            If ``arm()`` has not been called first.
        ValueError
            If ``throttle`` is outside ``[0.0, 1.0]``.
        """
        if not self._armed:
            raise RuntimeError("BLDC must be armed before set_throttle")
        if not (0.0 <= throttle <= 1.0):
            raise ValueError(f"throttle {throttle} out of range [0, 1]")
        pulse_us = 1000.0 + throttle * 1000.0  # linear map: 0 → 1000 µs, 1 → 2000 µs
        self._set_pulse_width_us(pulse_us)

    def disarm(self) -> None:  # pragma: no cover
        """Drop throttle to 0 µs and clear the armed flag.

        After ``disarm()``, ``set_throttle()`` will raise ``RuntimeError``
        again until ``arm()`` is called.
        """
        self._set_pulse_width_us(0)
        self._armed = False

    def _set_pulse_width_us(self, pulse_us: float) -> None:  # pragma: no cover
        """Convert a pulse width in microseconds to a 12-bit PCA9685 duty value.

        Formula: ``duty = round(pulse_us * 4096 / (1_000_000 / frequency_hz))``

        This encapsulates the PWM arithmetic so sub-classes or monkeypatching
        can intercept it during tests without needing real I2C hardware.
        """
        period_us = 1_000_000.0 / self._frequency_hz
        duty = round(pulse_us * 4096 / period_us)
        self._pca.channels[self._channel].duty_cycle = duty
