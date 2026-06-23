"""The Drill engine — turn a pattern + cadence into an iterator of Shots."""

from __future__ import annotations

import itertools
import random
from collections.abc import Iterator

from mcenroebot.drill.strategy import AimStrategy
from mcenroebot.drill.value_objects import DrillContext, Shot
from mcenroebot.launch import ShotSpec

__all__ = ["Drill", "_demo"]


class Drill:
    """Combine a shot spec, an :class:`AimStrategy`, and a cadence into Shots.

    Stateless config plus a single seeded RNG: ``shots()`` builds a fresh
    ``random.Random(seed)`` per call, so two iterations with the same seed
    yield identical Shot sequences. v1 uses one constant ``spec`` for every
    shot; speed/spin variation can be layered on later without changing the
    coordinator.

    Args:
        spec: the launch ShotSpec applied to every shot.
        strategy: the aim strategy choosing each target.
        cadence_s: delay until the next shot (``Shot.delay_s``).
        seed: RNG seed for reproducible randomized patterns.
    """

    def __init__(
        self,
        spec: ShotSpec,
        strategy: AimStrategy,
        cadence_s: float,
        seed: int = 0,
    ) -> None:
        self.spec = spec
        self.strategy = strategy
        self.cadence_s = cadence_s
        self.seed = seed

    def shots(self, n: int | None = None) -> Iterator[Shot]:
        """Yield ``n`` Shots (or an unbounded stream when ``n`` is None)."""
        rng = random.Random(self.seed)
        indices: Iterator[int] = itertools.count() if n is None else iter(range(n))
        for i in indices:
            ctx = DrillContext(shot_index=i, rng=rng)
            target = self.strategy.next_target(ctx)
            yield Shot(spec=self.spec, target=target, delay_s=self.cadence_s)


def _demo() -> None:
    """Print the first few Shots of an oscillate drill.

    Run with `python -m mcenroebot.drill`.
    """
    from mcenroebot.drill.strategy import FixedPatternStrategy
    from mcenroebot.drill.value_objects import TableTarget

    target = TableTarget(center_x_m=2.0, half_depth_m=0.4, half_width_m=0.6)
    strategy = FixedPatternStrategy(pattern="oscillate", target=target)
    spec = ShotSpec(speed_mps=7.0, spin_rad_s=40.0, spin_axis_deg=0.0)
    drill = Drill(spec=spec, strategy=strategy, cadence_s=1.2)
    print("=== oscillate drill (5 shots) ===")
    for i, shot in enumerate(drill.shots(5)):
        print(
            f"  shot {i}: target=({shot.target.x:+.2f}, {shot.target.y:+.2f}) m  "
            f"delay={shot.delay_s:.1f}s"
        )
