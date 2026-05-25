"""Aim controller — compute J1 (yaw) and J2 (pitch) servo angles.

This package solves the "aim" half of the V2 turret. Given a target point
in the robot frame, it returns the pair of servo angles that point the
paddle's sweep plane at the target. Swing timing — picking *when* during
the BLDC's rotation the paddle is at the target — is a separate problem
handled by the trajectory predictor and swing-fire logic.

Layout
------
    value_objects.py  — Position3D, ServoAngles, TurretGeometry (frozen pydantic).
    controller.py     — AimController + private `_demo` helper.
    __main__.py       — entry point for `python -m mcenroebot.aim`.

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

from mcenroebot.aim.controller import AimController, _demo
from mcenroebot.aim.value_objects import Position3D, ServoAngles, TurretGeometry

__all__ = [
    "AimController",
    "Position3D",
    "ServoAngles",
    "TurretGeometry",
    "_demo",
]
