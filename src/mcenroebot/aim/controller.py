"""Stateless controller mapping target points to (J1, J2) servo angles."""

from __future__ import annotations

import math

import numpy as np

from mcenroebot.aim.value_objects import Position3D, ServoAngles, TurretGeometry

__all__ = ["AimController"]


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


def _demo() -> None:
    """Print sanity-check results for a few representative targets.

    Run with `python -m mcenroebot.aim`.
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
