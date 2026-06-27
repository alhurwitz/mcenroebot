"""Vacuum projectile solver for the launch elevation angle.

Physics, no drag and no Magnus lift from spin (v1 — see the package docstring
for the deferred aerodynamics). A ball leaves the launch point at height
``launch_height_m``, speed ``v`` and elevation ``theta``; we solve for the
``theta`` that drops it onto a target at horizontal range ``d`` and height
``z_target``::

    z_target = launch_height + d*tan(theta) - g*d**2 / (2*v**2*cos(theta)**2)

Substituting ``u = tan(theta)`` and ``1/cos(theta)**2 = 1 + u**2`` turns this
into a quadratic in ``u``::

    (g*d**2 / 2v**2) * u**2  -  d * u  +  (z_target - launch_height + g*d**2 / 2v**2) = 0

The two real roots are the shallow (low) and steep (high) arcs that both reach
the target. A negative discriminant means the target is out of ballistic range.
"""

from __future__ import annotations

import math
from enum import Enum

__all__ = ["Arc", "solve_elevation"]


class Arc(Enum):
    """Which of the two ballistic solutions to take.

    ``LOW`` is the shallow arc (smaller elevation); ``HIGH`` is the lofted arc.
    For a feeder the low arc is the natural default — flatter, faster, less
    affected by the (v1-ignored) air. Both reach the same target.
    """

    LOW = "low"
    HIGH = "high"


def solve_elevation(
    *,
    horizontal_range_m: float,
    target_height_m: float,
    launch_height_m: float,
    speed_mps: float,
    gravity_m_s2: float = 9.81,
    arc: Arc = Arc.LOW,
) -> float | None:
    """Solve the launch elevation angle for a vacuum projectile.

    Parameters
    ----------
    horizontal_range_m : float
        Horizontal distance from the launch point to the target, in meters.
    target_height_m : float
        Target height above the origin, in meters (table ~ 0).
    launch_height_m : float
        Height of the launch point above the origin, in meters.
    speed_mps : float
        Ball exit speed, in m/s.
    gravity_m_s2 : float, optional
        Gravitational acceleration, in m/s**2. Defaults to 9.81.
    arc : Arc, optional
        Which root to return. Defaults to :attr:`Arc.LOW` (the shallow arc).

    Returns
    -------
    float
        The launch elevation ``theta`` in radians (may be negative for a
        downward shot when the target sits below the launch point).
    None
        If the shot is degenerate (non-positive speed or range) or the target
        is out of ballistic range (the discriminant is negative).
    """
    d = horizontal_range_m
    v = speed_mps
    g = gravity_m_s2
    if v <= 0.0 or d <= 0.0:
        return None

    # k == g*d**2 / (2*v**2); quadratic is  k*u**2 - d*u + (k + dz) = 0.
    k = g * d * d / (2.0 * v * v)
    dz = target_height_m - launch_height_m
    discriminant = d * d - 4.0 * k * (k + dz)
    if discriminant < 0.0:
        return None

    root = math.sqrt(discriminant)
    u_low = (d - root) / (2.0 * k)
    u_high = (d + root) / (2.0 * k)
    u = u_low if arc is Arc.LOW else u_high
    return math.atan(u)
