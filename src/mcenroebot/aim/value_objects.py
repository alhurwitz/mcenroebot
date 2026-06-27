"""Frozen pydantic value objects for the aim subsystem."""

from __future__ import annotations

import math

import numpy as np
from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator

__all__ = ["AimGeometry", "Position3D", "ServoAngles"]


class Position3D(BaseModel):
    """A 3D point in the robot frame, in meters.

    See the package docstring for the coordinate convention.
    """

    model_config = ConfigDict(frozen=True)

    x: float
    y: float
    z: float

    @property
    def horizontal_distance(self) -> float:
        """Distance from origin projected onto the XY (ground) plane."""
        return math.hypot(self.x, self.y)

    @property
    def magnitude(self) -> float:
        """Euclidean distance from origin."""
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def as_array(self) -> np.ndarray:
        """Return as a length-3 numpy array — useful for vectorized math."""
        return np.array([self.x, self.y, self.z], dtype=float)


class ServoAngles(BaseModel):
    """Deprecated V2 turret servo-angle pair (yaw + pitch), in degrees.

    Retained only for the shelved V2 rally stack
    (``mcenroebot._shelved``), which still aims a paddle in both yaw and
    pitch via :meth:`AimController.compute`. The V4 feeder does not use this:
    pan comes from :meth:`AimController.pan_angle_for` (a bare float) and tilt
    from the launch subsystem. Do not use in feeder code.
    """

    model_config = ConfigDict(frozen=True)

    yaw_deg: float
    pitch_deg: float

    @field_validator("yaw_deg", "pitch_deg")
    @classmethod
    def _check_servo_range(cls, value: float, info: ValidationInfo) -> float:
        if not (0.0 <= value <= 180.0):
            raise ValueError(f"{info.field_name}={value} out of servo range [0, 180]")
        return value


class AimGeometry(BaseModel):
    """Calibrated parameters for horizontal (pan) pointing.

    The aim subsystem only steers in yaw, so the geometry needs a single
    parameter: the pan-servo angle that points the launch head straight
    forward (+X).

    Attributes
    ----------
    yaw_neutral_deg : float
        Pan-servo angle, in degrees, that aims along +X. Must lie within
        the [0, 180] servo range. Defaults to the mechanical center, 90°.
    """

    model_config = ConfigDict(frozen=True)

    yaw_neutral_deg: float = 90.0

    @field_validator("yaw_neutral_deg")
    @classmethod
    def _check_servo_range(cls, value: float) -> float:
        if not (0.0 <= value <= 180.0):
            raise ValueError(f"yaw_neutral_deg={value} out of servo range [0, 180]")
        return value
