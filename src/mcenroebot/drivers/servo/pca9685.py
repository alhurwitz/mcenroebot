"""PCA9685 servo driver — real hardware implementation using adafruit_servokit."""

from __future__ import annotations

__all__ = ["PCA9685ServoDriver"]


class PCA9685ServoDriver:
    """Real driver for PCA9685 + servokit.  Lazy import of adafruit_servokit.

    The Adafruit libraries are not available on a Mac dev environment —
    they live in the ``pi`` optional extra and are installed via
    ``uv sync --extra pi`` on the Raspberry Pi only.  This class therefore
    defers ``import adafruit_servokit`` to the constructor so that importing
    *this module* never raises an ``ImportError`` on a Mac.

    Args:
        i2c_address: I2C address of the PCA9685 board (default 0x40).
        frequency_hz: PWM frequency in Hz (default 50 — standard servo).
        channel_count: Number of channels on the board (default 16).
    """

    def __init__(
        self,
        i2c_address: int = 0x40,
        frequency_hz: int = 50,
        channel_count: int = 16,
    ) -> None:
        try:
            from adafruit_servokit import ServoKit
        except ImportError as exc:
            raise ImportError(
                "adafruit_servokit is not installed. "
                "Install the Pi optional extra with: uv sync --extra pi"
            ) from exc

        self._channel_count = channel_count  # pragma: no cover
        self._kit = ServoKit(  # pragma: no cover
            channels=channel_count,
            address=i2c_address,
            frequency=frequency_hz,
        )

    def write_angle(self, channel: int, angle_deg: float) -> None:  # pragma: no cover
        """Drive ``channel`` to ``angle_deg`` degrees.

        Raises
        ------
        ValueError
            If ``channel`` is outside ``[0, channel_count)`` or
            ``angle_deg`` is outside ``[0, 180]``.
        """
        if not (0 <= channel < self._channel_count):
            raise ValueError(f"channel {channel} out of range [0, {self._channel_count})")
        if not (0.0 <= angle_deg <= 180.0):
            raise ValueError(f"angle_deg {angle_deg} out of range [0, 180]")
        self._kit.servo[channel].angle = angle_deg
