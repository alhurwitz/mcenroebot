"""Aim strategies — pick the court target for each shot.

``AimStrategy`` is the pluggable seam: ``FixedPatternStrategy`` (no vision)
ships in Wave 3; ``VisionPlacementStrategy`` (Wave 6) drops in behind the same
Protocol without touching the launch math or the coordinator.
"""

from __future__ import annotations

import math
from typing import Literal, Protocol, runtime_checkable

from mcenroebot.aim import Position3D
from mcenroebot.drill.value_objects import DrillContext, TableTarget

__all__ = ["AimStrategy", "FixedPatternStrategy", "Pattern"]

Pattern = Literal["static", "oscillate", "random", "figure8"]

_FIGURE8_PERIOD = 8  # shots per full figure-8 loop


@runtime_checkable
class AimStrategy(Protocol):
    """Decide the court location to aim the next ball at."""

    def next_target(self, ctx: DrillContext) -> Position3D:
        """Return the target point for the shot described by ``ctx``."""
        ...


class FixedPatternStrategy:
    """Deterministic, vision-free aim patterns over a :class:`TableTarget`.

    Patterns
    --------
    static
        Always the same point (``center_x``, ``static_y_m``).
    oscillate
        Alternates the left/right extremes (±``half_width``) at center depth.
    random
        Uniform random lateral placement within ±``half_width`` (uses the
        drill RNG in ``ctx``, so a fixed seed is reproducible).
    figure8
        A 1:2 Lissajous over depth x width tracing a figure-8 through the region.

    Pure function of ``ctx.shot_index`` (and ``ctx.rng`` for ``random``).
    """

    def __init__(
        self,
        pattern: Pattern,
        target: TableTarget,
        static_y_m: float = 0.0,
    ) -> None:
        if pattern not in ("static", "oscillate", "random", "figure8"):
            raise ValueError(f"unknown pattern {pattern!r}")
        self.pattern: Pattern = pattern
        self.target = target
        self.static_y_m = static_y_m

    def next_target(self, ctx: DrillContext) -> Position3D:
        """Return the target point for ``ctx.shot_index`` under this pattern."""
        t = self.target
        if self.pattern == "static":
            return Position3D(x=t.center_x_m, y=self.static_y_m, z=t.z_m)
        if self.pattern == "oscillate":
            y = t.half_width_m if ctx.shot_index % 2 == 0 else -t.half_width_m
            return Position3D(x=t.center_x_m, y=y, z=t.z_m)
        if self.pattern == "random":
            y = ctx.rng.uniform(-t.half_width_m, t.half_width_m)
            return Position3D(x=t.center_x_m, y=y, z=t.z_m)
        # figure8
        theta = 2.0 * math.pi * (ctx.shot_index % _FIGURE8_PERIOD) / _FIGURE8_PERIOD
        x = t.center_x_m + t.half_depth_m * math.sin(theta)
        y = t.half_width_m * math.sin(2.0 * theta)
        return Position3D(x=x, y=y, z=t.z_m)
