"""Stateless controller mapping a target point to the pan (yaw) servo angle."""

from __future__ import annotations

import math

from mcenroebot.aim.value_objects import AimGeometry, Position3D, ServoAngles

__all__ = ["AimController"]

# Tolerance (degrees) for snapping a computed angle that overshoots the [0, 180]
# servo range by floating-point noise back onto the boundary instead of
# rejecting it as unreachable.
_EDGE_EPS_DEG = 1e-9

# Deprecated V2 turret constants — used only by the compute()/is_reachable()
# shim below, which exists for the shelved rally stack. Not used by the feeder.
_V2_ARM_LENGTH_M = 0.20
_V2_PITCH_NEUTRAL_DEG = 90.0


class AimController:
    """Convert a target point in the robot frame to the pan servo angle.

    Aiming is horizontal only: the controller rotates the launch head in yaw
    to face the target's bearing. Elevation (the tilt servo) is owned by the
    launch subsystem, which holds the exit speed needed to solve the ballistic
    arc.

    Stateless aside from the injected geometry; one instance is reused across
    many ``pan_angle_for()`` calls.

    Example
    -------
    >>> ctrl = AimController()
    >>> ctrl.pan_angle_for(Position3D(x=1.5, y=0.0, z=0.0))  # straight ahead
    90.0
    """

    def __init__(self, geometry: AimGeometry | None = None) -> None:
        self.geometry: AimGeometry = geometry or AimGeometry()

    def pan_angle_for(self, target: Position3D) -> float | None:
        """Compute the pan-servo angle that aims at ``target``'s bearing.

        Parameters
        ----------
        target : Position3D
            Target point in the robot frame. Only the horizontal (x, y)
            components matter; height is ignored.

        Returns
        -------
        float
            The pan-servo angle in degrees, within [0, 180].
        None
            If the required angle falls outside the servo's [0, 180] range —
            the honest, angular reachability test (the head cannot face that
            bearing).

        Notes
        -----
        ``yaw = atan2(y, x)`` is the target bearing measured left (+Y) of
        forward (+X); ``pan = yaw_neutral_deg + degrees(yaw)``.
        """
        yaw_rad = math.atan2(target.y, target.x)
        pan_deg = self.geometry.yaw_neutral_deg + math.degrees(yaw_rad)

        if pan_deg < -_EDGE_EPS_DEG or pan_deg > 180.0 + _EDGE_EPS_DEG:
            return None
        # Snap floating-point overshoot at the boundary cleanly into range.
        return min(180.0, max(0.0, pan_deg))

    # -- Deprecated V2 turret shim --------------------------------------------
    # The shelved V2 rally stack (mcenroebot._shelved) aims a paddle in both
    # yaw and pitch and tests reachability as a spherical arm reach. The V4
    # feeder uses pan_angle_for() (above) for yaw and the launch subsystem for
    # tilt; these two methods exist only so the shelved code keeps running.

    def is_reachable(self, target: Position3D) -> bool:
        """Deprecated: V2 spherical arm-reach test. Shelved rally only."""
        return target.magnitude <= _V2_ARM_LENGTH_M

    def compute(self, target: Position3D) -> ServoAngles | None:
        """Deprecated: V2 turret yaw+pitch aim. Shelved rally only.

        Points the paddle's sweep plane directly at ``target`` (yaw from the
        bearing, pitch from the elevation), returning None when the target is
        outside the spherical arm reach. Feeder code must use
        :meth:`pan_angle_for` and the launch subsystem's tilt instead.
        """
        if not self.is_reachable(target):
            return None
        yaw_rad = math.atan2(target.y, target.x)
        elevation_rad = math.atan2(target.z, target.horizontal_distance)
        yaw_deg = min(180.0, max(0.0, self.geometry.yaw_neutral_deg + math.degrees(yaw_rad)))
        pitch_deg = min(180.0, max(0.0, _V2_PITCH_NEUTRAL_DEG + math.degrees(elevation_rad)))
        return ServoAngles(yaw_deg=yaw_deg, pitch_deg=pitch_deg)


def _demo() -> None:
    """Print sanity-check pan angles for a few representative targets.

    Run with `python -m mcenroebot.aim`.
    """
    controller = AimController()
    cases = [
        ("Forward", Position3D(x=1.5, y=0.0, z=0.0)),
        ("Forward and left", Position3D(x=1.5, y=0.6, z=0.0)),
        ("Forward and right", Position3D(x=1.5, y=-0.6, z=0.0)),
        ("Behind (out of range)", Position3D(x=-0.5, y=0.5, z=0.0)),
    ]
    for label, target in cases:
        pan = controller.pan_angle_for(target)
        print(f"=== {label} ===")
        print(f"  target=({target.x:+.3f}, {target.y:+.3f}, {target.z:+.3f}) m")
        if pan is None:
            print("  -> OUT OF RANGE")
        else:
            print(f"  -> pan={pan:6.1f}°")
        print()
