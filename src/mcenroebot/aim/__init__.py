"""Aim controller — compute the pan (yaw) servo angle for a target.

This package solves the *horizontal* half of feeder pointing. Given a target
point in the robot frame, it returns the pan-servo angle that rotates the
launch head to face the target's bearing. It carries no physics and no
elevation: the vertical/ballistic half (the tilt servo) lives in the ``launch``
package, which owns the exit speed needed to solve the projectile arc.

Layout
------
    value_objects.py  — Position3D, AimGeometry (frozen pydantic).
    controller.py     — AimController + private `_demo` helper.
    __main__.py       — entry point for `python -m mcenroebot.aim`.

The package also re-exports ``ServoAngles`` and ``AimController`` carries
deprecated ``compute``/``is_reachable`` methods — a thin V2-turret shim kept
only so the shelved rally stack (``mcenroebot._shelved``) keeps running. Feeder
code must not use them.

Coordinate system
-----------------
    Origin: pan (yaw) axis, at the tilt-pivot height.
    +X: forward (toward the player).
    +Y: left (viewed from above).
    +Z: up.
    Units: meters.

Servo convention
----------------
    The pan servo has a 180° range. Neutral (``yaw_neutral_deg``, default 90°)
    aims straight forward (+X). The angle increases toward +Y (left) and
    decreases toward -Y (right). Bearings that would need an angle outside
    [0, 180] are unreachable and ``pan_angle_for`` returns None.
"""

from mcenroebot.aim.controller import AimController, _demo
from mcenroebot.aim.value_objects import AimGeometry, Position3D, ServoAngles

__all__ = [
    "AimController",
    "AimGeometry",
    "Position3D",
    "ServoAngles",
    "_demo",
]
