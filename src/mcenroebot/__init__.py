"""McEnroe ping pong robot — V2 control software.

Package layout:
    aim         — Aim-the-paddle controller (J1 yaw + J2 pitch).
    (future)    — swing.py, predictor.py, tracker.py, etc.

Coordinate system (used across the package):
    Origin: J1 yaw axis, at J2 pitch pivot height.
    +X: forward (toward the ball / opponent's side of the table).
    +Y: left (when viewed from above).
    +Z: up.
    Units: meters, radians (internally), degrees (servo I/O).
"""

from mcenroebot.aim import AimController, Position3D, ServoAngles, TurretGeometry

__all__ = [
    "AimController",
    "Position3D",
    "ServoAngles",
    "TurretGeometry",
]
