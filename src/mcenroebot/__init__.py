"""McEnroe ping pong robot — V4 feeder control software.

Package layout:
    aim         — pan (yaw) pointing controller.
    launch      — two-wheel launch + ballistic tilt controller.
    drill       — shot-pattern engine.
    coordinator — periodic feeder scheduler.

Coordinate system (used across the package):
    Origin: pan (yaw) axis, at the tilt-pivot height.
    +X: forward (toward the player / opponent's side of the table).
    +Y: left (when viewed from above).
    +Z: up.
    Units: meters, radians (internally), degrees (servo I/O).
"""

from mcenroebot.aim import AimController, AimGeometry, Position3D

__all__ = [
    "AimController",
    "AimGeometry",
    "Position3D",
]
