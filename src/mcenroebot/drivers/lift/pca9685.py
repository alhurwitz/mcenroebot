"""PCA9685 auger lift driver — single-direction PWM to a MOSFET gate (Pi only)."""

from __future__ import annotations

__all__ = ["Pca9685LiftDriver"]


class Pca9685LiftDriver:
    """Real auger driver: a PCA9685 PWM channel driving a MOSFET/L298N enable.

    The 12 V gearmotor runs in one direction; ``set_duty`` sets the PWM duty
    cycle (0..1 mapped to the 16-bit PCA9685 duty value). Adafruit libraries
    are imported lazily in the constructor so importing this module on a Mac
    never raises.

    Args:
        channel: PCA9685 channel wired to the MOSFET gate.
        i2c_address: I2C address of the PCA9685 board (default 0x40).
        frequency_hz: PWM frequency in Hz (default 1000 — MOSFET switching).
    """

    def __init__(
        self,
        channel: int,
        i2c_address: int = 0x40,
        frequency_hz: int = 1000,
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
        i2c = busio.I2C(board.SCL, board.SDA)  # pragma: no cover
        self._pca = PCA9685(i2c, address=i2c_address)  # pragma: no cover
        self._pca.frequency = frequency_hz  # pragma: no cover

    def set_duty(self, fraction: float) -> None:  # pragma: no cover
        """Drive the auger at ``fraction`` duty in ``[0.0, 1.0]``.

        Raises
        ------
        ValueError
            If ``fraction`` is outside ``[0.0, 1.0]``.
        """
        if not (0.0 <= fraction <= 1.0):
            raise ValueError(f"duty fraction={fraction} out of range [0, 1]")
        self._pca.channels[self._channel].duty_cycle = round(fraction * 0xFFFF)

    def off(self) -> None:  # pragma: no cover
        """Stop the auger (duty 0)."""
        self._pca.channels[self._channel].duty_cycle = 0
