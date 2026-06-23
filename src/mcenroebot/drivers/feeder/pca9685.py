"""PCA9685 feeder driver — continuous-rotation servo escapement (Pi only)."""

from __future__ import annotations

from mcenroebot.drivers.feeder.mapping import throttle_for_rate

__all__ = ["Pca9685FeederDriver"]


class Pca9685FeederDriver:
    """Real escapement driver: a continuous-rotation servo on a PCA9685 channel.

    Feed rate is set by spinning the single-pocket indexing disk at a constant
    speed; ``balls_per_min`` is mapped to a continuous-servo throttle in
    ``[-1, 1]`` via the calibrated ``throttle_per_bpm`` factor (see
    ``scripts/calibrate_feeder.py``).

    The Adafruit libraries live in the ``pi`` optional extra and are imported
    lazily in the constructor, so importing this module on a Mac never raises.

    Args:
        channel: PCA9685 channel the CR servo is wired to.
        throttle_per_bpm: calibrated throttle units per ball-per-minute.
        i2c_address: I2C address of the PCA9685 board (default 0x40).
        channel_count: number of channels on the board (default 16).
    """

    def __init__(
        self,
        channel: int,
        throttle_per_bpm: float = 0.01,
        i2c_address: int = 0x40,
        channel_count: int = 16,
    ) -> None:
        try:
            from adafruit_servokit import ServoKit
        except ImportError as exc:
            raise ImportError(
                "adafruit_servokit is not installed. "
                "Install the Pi optional extra with: uv sync --extra pi"
            ) from exc

        self._channel = channel  # pragma: no cover
        self._throttle_per_bpm = throttle_per_bpm  # pragma: no cover
        self._kit = ServoKit(channels=channel_count, address=i2c_address)  # pragma: no cover

    def set_rate(self, balls_per_min: float) -> None:  # pragma: no cover
        """Spin the disk at the throttle that feeds ``balls_per_min``."""
        throttle = throttle_for_rate(balls_per_min, self._throttle_per_bpm)
        self._kit.continuous_servo[self._channel].throttle = throttle

    def stop(self) -> None:  # pragma: no cover
        """Stop the escapement disk (throttle 0)."""
        self._kit.continuous_servo[self._channel].throttle = 0.0

    def fire(self) -> None:  # pragma: no cover
        """Unsupported on the v1 sensorless feeder.

        Raises
        ------
        NotImplementedError
            Always — per-ball ``fire()`` needs the index-endstop upgrade
            (see ``docs/V4_PLAN.md`` §1). Use ``set_rate`` for v1.
        """
        raise NotImplementedError(
            "v1 feeder is sensorless; fire() needs the index-endstop upgrade. Use set_rate()."
        )
