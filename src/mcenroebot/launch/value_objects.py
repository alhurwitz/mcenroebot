"""Frozen pydantic value objects for the launch subsystem."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator

__all__ = ["LaunchGeometry", "ShotSpec", "ThrottleMap", "WheelCommand"]


class ShotSpec(BaseModel):
    """A desired shot: exit speed, spin magnitude, and spin-axis orientation.

    See the package docstring for the spin sign / axis convention.

    Attributes
    ----------
    speed_mps : float
        Desired ball exit speed in m/s. Must be > 0.
    spin_rad_s : float
        Signed spin magnitude in rad/s. Positive = topspin when the head is
        at roll 0; negative = backspin. The sign drives the wheel differential.
    spin_axis_deg : float
        Head-roll orientation of the spin axis in degrees, in [0, 360).
        0 = top/back-spin, 90 = pure sidespin.
    """

    model_config = ConfigDict(frozen=True)

    speed_mps: float
    spin_rad_s: float
    spin_axis_deg: float

    @field_validator("speed_mps")
    @classmethod
    def _check_speed(cls, value: float) -> float:
        if value <= 0.0:
            raise ValueError(f"speed_mps={value} must be > 0")
        return value

    @field_validator("spin_axis_deg")
    @classmethod
    def _check_axis(cls, value: float) -> float:
        if not (0.0 <= value < 360.0):
            raise ValueError(f"spin_axis_deg={value} out of range [0, 360)")
        return value


class WheelCommand(BaseModel):
    """A concrete two-wheel + head-roll command produced by the controller.

    Attributes
    ----------
    top_rpm, bottom_rpm : float
        Commanded wheel speeds in rpm. Both must be >= 0.
    head_roll_deg : float
        Roll servo angle in degrees, clamped to the [0, 180] servo range.
    """

    model_config = ConfigDict(frozen=True)

    top_rpm: float
    bottom_rpm: float
    head_roll_deg: float

    @field_validator("top_rpm", "bottom_rpm")
    @classmethod
    def _check_rpm(cls, value: float, info: ValidationInfo) -> float:
        if value < 0.0:
            raise ValueError(f"{info.field_name}={value} must be >= 0")
        return value

    @field_validator("head_roll_deg")
    @classmethod
    def _check_head_roll(cls, value: float) -> float:
        if not (0.0 <= value <= 180.0):
            raise ValueError(f"head_roll_deg={value} out of servo range [0, 180]")
        return value


class LaunchGeometry(BaseModel):
    """Fixed physical / calibrated parameters of the two-wheel launch head.

    Mirrors ``TurretGeometry``: injected config, frozen, reused across calls.

    Attributes
    ----------
    wheel_diameter_m : float
        Launch wheel diameter in meters. Must be > 0.
    ball_radius_m : float
        Ball radius in meters (40 mm ball -> 0.02). Must be > 0.
    grip_efficiency : float
        eta = ball speed / mean wheel-surface speed, in (0, 1]. Calibrated.
    spin_efficiency : float
        eta_spin for the surface-speed differential -> spin transfer, in (0, 1].
    max_wheel_rpm : float
        No-load BLDC rpm ceiling at the deploy voltage. Must be > 0.
    """

    model_config = ConfigDict(frozen=True)

    wheel_diameter_m: float
    ball_radius_m: float = 0.02
    grip_efficiency: float = 0.85
    spin_efficiency: float = 0.85
    max_wheel_rpm: float

    @field_validator("wheel_diameter_m", "ball_radius_m", "max_wheel_rpm")
    @classmethod
    def _check_positive(cls, value: float, info: ValidationInfo) -> float:
        if value <= 0.0:
            raise ValueError(f"{info.field_name}={value} must be > 0")
        return value

    @field_validator("grip_efficiency", "spin_efficiency")
    @classmethod
    def _check_efficiency(cls, value: float, info: ValidationInfo) -> float:
        if not (0.0 < value <= 1.0):
            raise ValueError(f"{info.field_name}={value} must be in (0, 1]")
        return value


class ThrottleMap(BaseModel):
    """Calibrated rpm <-> ESC throttle [0, 1] mapping (linear v1 model).

    Attributes
    ----------
    rpm_at_full_throttle : float
        Measured wheel rpm at throttle 1.0. Must be > 0.
    throttle_floor : float
        ESC startup deadband: the lowest throttle at which the motor actually
        spins, in [0, 1). Any commanded rpm > 0 is remapped into
        ``[throttle_floor, 1]`` so low-speed shots clear the deadband instead
        of commanding a throttle the ESC ignores. ``rpm == 0`` still maps to 0
        (wheel off). Measured via scripts/esc_calibrate.py + esc_bringup.py;
        update with the *loaded* value once calibrate_launch.py runs.
    """

    model_config = ConfigDict(frozen=True)

    rpm_at_full_throttle: float
    throttle_floor: float = 0.0

    @field_validator("rpm_at_full_throttle")
    @classmethod
    def _check_full_throttle(cls, value: float) -> float:
        if value <= 0.0:
            raise ValueError(f"rpm_at_full_throttle={value} must be > 0")
        return value

    @field_validator("throttle_floor")
    @classmethod
    def _check_floor(cls, value: float) -> float:
        if not (0.0 <= value < 1.0):
            raise ValueError(f"throttle_floor={value} must be in [0, 1)")
        return value

    def throttle_for(self, rpm: float) -> float:
        """Convert a wheel rpm to an ESC throttle in [0, 1] (clamped).

        ``rpm <= 0`` returns 0.0 (wheel off). Any positive rpm is mapped into
        ``[throttle_floor, 1]`` so it clears the ESC startup deadband.
        """
        if rpm <= 0.0:
            return 0.0
        frac = rpm / self.rpm_at_full_throttle
        throttle = self.throttle_floor + frac * (1.0 - self.throttle_floor)
        return min(1.0, max(0.0, throttle))
