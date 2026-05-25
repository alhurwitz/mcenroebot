"""Frozen pydantic value objects for the aim subsystem."""

from __future__ import annotations

import math

import numpy as np
from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator

__all__ = ["Position3D", "ServoAngles", "TurretGeometry"]


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
    """Servo angles for the aim turret, in degrees.

    Both angles are clamped to the MG996R's [0, 180] range; values
    outside that range raise pydantic.ValidationError (which wraps the
    underlying ValueError so the original message is preserved).
    """

    model_config = ConfigDict(frozen=True)

    yaw_deg: float
    pitch_deg: float

    @field_validator("yaw_deg", "pitch_deg")
    @classmethod
    def _check_servo_range(cls, value: float, info: ValidationInfo) -> float:
        if not (0.0 <= value <= 180.0):
            raise ValueError(f"{info.field_name}={value} out of MG996R servo range [0, 180]")
        return value


class TurretGeometry(BaseModel):
    """Fixed physical parameters of the V2 turret.

    Attributes
    ----------
    arm_length_m : float
        Distance from BLDC shaft center to paddle face, in meters. Used
        as the reachability bound (targets beyond this distance return
        no solution).
    yaw_neutral_deg : float
        Servo angle that points the sweep plane straight forward (+X).
    pitch_neutral_deg : float
        Servo angle that puts the sweep plane vertical (BLDC shaft along Y).
    """

    model_config = ConfigDict(frozen=True)

    arm_length_m: float = 0.20
    yaw_neutral_deg: float = 90.0
    pitch_neutral_deg: float = 90.0
