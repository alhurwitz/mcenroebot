"""VisionPlacementStrategy — aim the open court away from the detected player.

The optional Wave 6 strategy. Implements the same ``AimStrategy`` Protocol as
``FixedPatternStrategy``, so dropping it into a ``Drill`` changes *where* balls
go with no change to the launch math or the coordinator. When the player isn't
confidently found it defers to a fixed-pattern fallback.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from numpy.typing import NDArray

from mcenroebot.aim import Position3D
from mcenroebot.drill.strategy import AimStrategy
from mcenroebot.drill.value_objects import DrillContext, TableTarget
from mcenroebot.player import PlayerDetector

__all__ = ["VisionPlacementStrategy"]


class VisionPlacementStrategy:
    """Send the next ball to the side opposite the detected player.

    Args:
        detector: finds the player in a frame.
        frame_source: returns the latest camera frame to detect on.
        target: the court target region (depth, width, height).
        fallback: strategy used when no confident detection is available.
        min_confidence: detections below this confidence defer to ``fallback``.
    """

    def __init__(
        self,
        detector: PlayerDetector,
        frame_source: Callable[[], NDArray[Any]],
        target: TableTarget,
        fallback: AimStrategy,
        min_confidence: float = 0.5,
    ) -> None:
        self.detector = detector
        self.frame_source = frame_source
        self.target = target
        self.fallback = fallback
        self.min_confidence = min_confidence

    def next_target(self, ctx: DrillContext) -> Position3D:
        """Aim opposite the player, or defer to the fallback if unsure."""
        position = self.detector.detect(self.frame_source())
        if position is None or position.confidence < self.min_confidence:
            return self.fallback.next_target(ctx)

        # Aim to the side opposite the player. copysign keeps it deterministic
        # even when the player is dead center (offset 0.0 -> aim -half_width).
        open_y = -math.copysign(self.target.half_width_m, position.side_offset_m)
        return Position3D(x=self.target.center_x_m, y=open_y, z=self.target.z_m)
