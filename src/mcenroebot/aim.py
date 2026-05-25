"""Aim controller — compute J1 (yaw) and J2 (pitch) servo angles.

This module solves the "aim" half of the V2 turret. Given a target point
in the robot frame, it returns the pair of servo angles that point the
paddle's sweep plane at the target. Swing timing — picking *when* during
the BLDC's rotation the paddle is at the target — is a separate problem
handled by the trajectory predictor and swing-fire logic.

Coordinate system
-----------------
    Origin: J1 yaw axis, at the height of the J2 pitch pivot.
    +X: forward (toward the ball).
    +Y: left (viewed from above).
    +Z: up.
    Units: meters.

Servo convention
----------------
    Both MG996R servos have a 180° range. The neutral pose is yaw=90°,
    pitch=90° (paddle sweeps forward in the vertical X-Z plane). Yaw
    decreases as the turret rotates right (toward -Y); pitch increases
    as the sweep plane tilts up.

Simplifications for V1
----------------------
    1. The J2 pivot and the BLDC shaft center are treated as coincident.
       In reality they're offset by ~30mm (pitch bracket length). This
       matters at extreme angles but not at typical strike-zone positions.
    2. The controller doesn't pick a swing angle — that's the trajectory
       predictor's job. This module only orients the sweep plane.
    3. Flat returns only. No paddle face tilt for topspin/backspin.
"""

from __future__ import annotations

import math

import numpy as np
from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator

__all__ = [
    "AimController",
    "Position3D",
    "ServoAngles",
    "TurretGeometry",
]


class Position3D(BaseModel):
    """A 3D point in the robot frame, in meters.

    See module docstring for the coordinate convention.
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


class AimController:
    """Convert a target point in the robot frame to J1/J2 servo angles.

    The controller is stateless aside from the turret geometry. One
    instance can be reused across many `compute()` calls.

    Example
    -------
    >>> ctrl = AimController()
    >>> target = Position3D(x=0.18, y=0.0, z=0.0)  # 18cm directly forward
    >>> angles = ctrl.compute(target)
    >>> angles.yaw_deg, angles.pitch_deg
    (90.0, 90.0)
    """

    def __init__(self, geometry: TurretGeometry | None = None) -> None:
        self.geometry: TurretGeometry = geometry or TurretGeometry()

    # ----- Public API -----

    def is_reachable(self, target: Position3D) -> bool:
        """Return True if the target is within paddle reach."""
        return target.magnitude <= self.geometry.arm_length_m

    def compute(self, target: Position3D) -> ServoAngles | None:
        """Compute the (J1, J2) angles needed to point at the target.

        Returns
        -------
        ServoAngles
            The yaw and pitch angles to command the servos to.
        None
            If the target is outside the reachable workspace.

        Notes
        -----
        Aiming strategy:
            yaw   = atan2(y, x)          — rotate horizontally to face target.
            pitch = atan2(z, hypot(x,y)) — tilt sweep plane up by elevation.
        Then add the neutral offsets and clamp to [0, 180].
        """
        if not self.is_reachable(target):
            return None

        yaw_rad = math.atan2(target.y, target.x)
        elevation_rad = math.atan2(target.z, target.horizontal_distance)

        yaw_deg = self.geometry.yaw_neutral_deg + math.degrees(yaw_rad)
        pitch_deg = self.geometry.pitch_neutral_deg + math.degrees(elevation_rad)

        # np.clip catches numerical edge cases right at the boundary and
        # plays nicely with future vectorization.
        yaw_deg = float(np.clip(yaw_deg, 0.0, 180.0))
        pitch_deg = float(np.clip(pitch_deg, 0.0, 180.0))

        return ServoAngles(yaw_deg=yaw_deg, pitch_deg=pitch_deg)


# ----- Demo -----


def _demo() -> None:
    """Print sanity-check results for a few representative targets.

    Run with `python -m mcenroebot.aim` or `uv run python -m mcenroebot.aim`.
    """
    controller = AimController()
    cases = [
        ("Forward, paddle-height", Position3D(x=0.18, y=0.0, z=0.0)),
        ("Forward and high", Position3D(x=0.10, y=0.0, z=0.15)),
        ("Forward and left", Position3D(x=0.13, y=0.13, z=0.0)),
        ("Forward and right", Position3D(x=0.13, y=-0.13, z=0.0)),
        ("Out of reach", Position3D(x=0.5, y=0.5, z=0.5)),
    ]
    arm = controller.geometry.arm_length_m
    for label, target in cases:
        angles = controller.compute(target)
        print(f"=== {label} ===")
        print(
            f"  target=({target.x:+.3f}, {target.y:+.3f}, {target.z:+.3f}) m  "
            f"|r|={target.magnitude:.3f}  (arm={arm:.3f})"
        )
        if angles is None:
            print("  -> OUT OF REACH")
        else:
            print(f"  -> yaw={angles.yaw_deg:6.1f}°  pitch={angles.pitch_deg:6.1f}°")
        print()


if __name__ == "__main__":
    _demo()
