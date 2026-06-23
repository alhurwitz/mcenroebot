"""Tests for the Drill engine — Shot iterator over a pattern + cadence."""

from __future__ import annotations

import itertools

from mcenroebot.drill import Drill, FixedPatternStrategy, TableTarget
from mcenroebot.launch import ShotSpec


def _drill(pattern: str = "oscillate", seed: int = 0, cadence_s: float = 1.2) -> Drill:
    target = TableTarget(center_x_m=2.0, half_depth_m=0.5, half_width_m=0.6)
    strat = FixedPatternStrategy(pattern=pattern, target=target)  # type: ignore[arg-type]
    spec = ShotSpec(speed_mps=7.0, spin_rad_s=30.0, spin_axis_deg=0.0)
    return Drill(spec=spec, strategy=strat, cadence_s=cadence_s, seed=seed)


class TestDrill:
    def test_finite_shot_count(self) -> None:
        shots = list(_drill().shots(5))
        assert len(shots) == 5

    def test_cadence_is_applied(self) -> None:
        shots = list(_drill(cadence_s=0.8).shots(3))
        assert all(s.delay_s == 0.8 for s in shots)

    def test_spec_carried_through(self) -> None:
        shots = list(_drill().shots(3))
        assert all(s.spec.speed_mps == 7.0 and s.spec.spin_rad_s == 30.0 for s in shots)

    def test_fixed_seed_gives_identical_sequence(self) -> None:
        a = [(s.target.x, s.target.y) for s in _drill(pattern="random", seed=99).shots(10)]
        b = [(s.target.x, s.target.y) for s in _drill(pattern="random", seed=99).shots(10)]
        assert a == b

    def test_different_seed_changes_random_sequence(self) -> None:
        a = [s.target.y for s in _drill(pattern="random", seed=1).shots(10)]
        b = [s.target.y for s in _drill(pattern="random", seed=2).shots(10)]
        assert a != b

    def test_unbounded_is_infinite(self) -> None:
        first_three = list(itertools.islice(_drill().shots(), 3))
        assert len(first_three) == 3

    def test_oscillate_targets_within_bounds(self) -> None:
        for s in _drill(pattern="oscillate").shots(8):
            assert -0.6 <= s.target.y <= 0.6
