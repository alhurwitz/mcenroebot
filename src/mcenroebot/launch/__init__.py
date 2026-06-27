"""Launch controller — map a desired shot to two-wheel speeds + head roll.

This package solves the "launch" half of the V4 feeder: given a desired exit
speed, spin magnitude, and spin-axis orientation, it returns the pair of wheel
rpms and the head-roll servo angle that produce it. It is the feeder analog of
``aim`` — pure math, stateless aside from injected geometry, no hardware.

The launch head also owns the *vertical* half of pointing: it holds the exit
speed, so it solves the ballistic elevation angle and the tilt-servo angle (see
``ballistics.py`` and :meth:`LaunchController.tilt_angle_for`). Horizontal
pointing (the pan servo) is the ``aim`` package's job.

Layout
------
    value_objects.py  — ShotSpec, WheelCommand, LaunchGeometry, ThrottleMap (frozen pydantic).
    ballistics.py     — Arc + solve_elevation (pure vacuum projectile solver).
    controller.py     — LaunchController + private `_demo` helper.
    __main__.py       — entry point for `python -m mcenroebot.launch`.

Spin sign / axis convention
---------------------------
    Topspin > 0 (ball top rotates toward the player); backspin < 0. The signed
    spin magnitude drives the wheel-surface-speed differential; the spin axis
    is oriented physically by rolling the two-wheel head about the shot axis:
    head_roll 0° = spin axis horizontal (pure top/back-spin), 90° = spin axis
    vertical (pure sidespin). The head has 180° symmetry, so the requested
    axis folds into [0, 180).

Mechanism
---------
    Two counter-rotating wheels grip the ball. Mean surface speed sets exit
    speed; the surface-speed difference sets spin magnitude. Shots that would
    need a wheel to spin backward, or exceed the wheel rpm ceiling, are out of
    envelope and ``compute()`` returns None.
"""

from mcenroebot.launch.ballistics import Arc, solve_elevation
from mcenroebot.launch.controller import LaunchController, _demo
from mcenroebot.launch.value_objects import (
    LaunchGeometry,
    ShotSpec,
    ThrottleMap,
    WheelCommand,
)

__all__ = [
    "Arc",
    "LaunchController",
    "LaunchGeometry",
    "ShotSpec",
    "ThrottleMap",
    "WheelCommand",
    "_demo",
    "solve_elevation",
]
