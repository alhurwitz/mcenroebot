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

    Injected config: frozen, reused across calls. Besides the wheel/ball
    parameters that set exit speed and spin, it carries the ballistic
    parameters used to solve the launch elevation and tilt-servo angle.

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
    launch_height_m : float
        Height of the launch point (ball exit) above the origin, in meters.
        Must be >= 0.
    gravity_m_s2 : float
        Gravitational acceleration used by the ballistic solver, in m/s**2.
        Must be > 0. Defaults to 9.81.
    pitch_neutral_deg : float
        Tilt-servo angle, in degrees, that fires horizontally (elevation 0).
        Must lie within [0, 180]. Defaults to the mechanical center, 90°;
        calibrate against the real head later.
    """

    model_config = ConfigDict(frozen=True)

    wheel_diameter_m: float
    ball_radius_m: float = 0.02
    grip_efficiency: float = 0.85
    spin_efficiency: float = 0.85
    max_wheel_rpm: float
    launch_height_m: float
    gravity_m_s2: float = 9.81
    pitch_neutral_deg: float = 90.0

    @field_validator("wheel_diameter_m", "ball_radius_m", "max_wheel_rpm", "gravity_m_s2")
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

    @field_validator("launch_height_m")
    @classmethod
    def _check_non_negative(cls, value: float, info: ValidationInfo) -> float:
        if value < 0.0:
            raise ValueError(f"{info.field_name}={value} must be >= 0")
        return value

    @field_validator("pitch_neutral_deg")
    @classmethod
    def _check_servo_range(cls, value: float, info: ValidationInfo) -> float:
        if not (0.0 <= value <= 180.0):
            raise ValueError(f"{info.field_name}={value} out of servo range [0, 180]")
        return value


class ThrottleMap(BaseModel):
    """Calibrated rpm <-> ESC throttle [0, 1] mapping with per-wheel deadbands.

    Attributes
    ----------
    rpm_at_full_throttle : float
        Measured wheel rpm at throttle 1.0. Must be > 0. Shared default for
        both wheels when the motors match.
    top_rpm_at_full, bottom_rpm_at_full : float | None
        Optional per-wheel overrides of ``rpm_at_full_throttle`` for a
        mixed-motor pair (e.g. A2212 1400KV top / 1000KV bottom, whose
        full-throttle rpm differ by ~40%). ``None`` falls back to the shared
        value. Must be > 0 when set.
    top_floor, bottom_floor : float
        Per-wheel ESC startup deadband in [0, 1): the lowest throttle at which
        that wheel actually spins under load. The two wheels rarely match (a
        measured pair was top 0.08 / bottom 0.05), so each carries its own
        floor. Any commanded rpm > 0 is remapped into ``[floor, 1]`` for that
        wheel so low-speed shots clear the deadband instead of commanding a
        throttle the ESC ignores; ``rpm == 0`` still maps to 0 (wheel off).
        Provisional until calibrate_launch.py measures loaded values per wheel.
    """

    model_config = ConfigDict(frozen=True)

    rpm_at_full_throttle: float
    top_rpm_at_full: float | None = None
    bottom_rpm_at_full: float | None = None
    top_floor: float = 0.0
    bottom_floor: float = 0.0

    @field_validator("rpm_at_full_throttle")
    @classmethod
    def _check_full_throttle(cls, value: float) -> float:
        if value <= 0.0:
            raise ValueError(f"rpm_at_full_throttle={value} must be > 0")
        return value

    @field_validator("top_rpm_at_full", "bottom_rpm_at_full")
    @classmethod
    def _check_per_wheel_full(cls, value: float | None, info: ValidationInfo) -> float | None:
        if value is not None and value <= 0.0:
            raise ValueError(f"{info.field_name}={value} must be > 0 when set")
        return value

    @field_validator("top_floor", "bottom_floor")
    @classmethod
    def _check_floor(cls, value: float, info: ValidationInfo) -> float:
        if not (0.0 <= value < 1.0):
            raise ValueError(f"{info.field_name}={value} must be in [0, 1)")
        return value

    def throttle_for(
        self, rpm: float, floor: float = 0.0, rpm_at_full: float | None = None
    ) -> float:
        """Map a wheel rpm to an ESC throttle in [0, 1], remapped into ``[floor, 1]``.

        ``rpm <= 0`` returns 0.0 (wheel off). Any positive rpm is mapped into
        ``[floor, 1]`` so it clears the ESC startup deadband. Prefer the
        per-wheel helpers :meth:`throttle_for_top` / :meth:`throttle_for_bottom`,
        which supply the matching floor and per-wheel full-throttle rpm; this
        method takes an explicit floor (default 0.0 = plain linear) and an
        optional ``rpm_at_full`` override for generic use.
        """
        if rpm <= 0.0:
            return 0.0
        frac = rpm / (rpm_at_full if rpm_at_full is not None else self.rpm_at_full_throttle)
        throttle = floor + frac * (1.0 - floor)
        return min(1.0, max(0.0, throttle))

    def throttle_for_top(self, rpm: float) -> float:
        """Throttle for the top wheel, using ``top_floor`` and ``top_rpm_at_full``."""
        return self.throttle_for(rpm, self.top_floor, self.top_rpm_at_full)

    def throttle_for_bottom(self, rpm: float) -> float:
        """Throttle for the bottom wheel, using ``bottom_floor`` and ``bottom_rpm_at_full``."""
        return self.throttle_for(rpm, self.bottom_floor, self.bottom_rpm_at_full)
