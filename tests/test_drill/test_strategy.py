"""Tests for FixedPatternStrategy aim patterns."""

from __future__ import annotations

import random

import pytest

from mcenroebot.drill import DrillContext, FixedPatternStrategy, TableTarget


def _ctx(index: int, seed: int = 0) -> DrillContext:
    return DrillContext(shot_index=index, rng=random.Random(seed))


@pytest.fixture
def target() -> TableTarget:
    return TableTarget(center_x_m=2.0, half_depth_m=0.5, half_width_m=0.6, z_m=0.0)


class TestStaticPattern:
    def test_always_same_point(self, target: TableTarget) -> None:
        strat = FixedPatternStrategy(pattern="static", target=target, static_y_m=0.1)
        points = [strat.next_target(_ctx(i)) for i in range(5)]
        assert all(p.x == 2.0 and p.y == 0.1 and p.z == 0.0 for p in points)


class TestOscillatePattern:
    def test_alternates_left_right_extremes(self, target: TableTarget) -> None:
        strat = FixedPatternStrategy(pattern="oscillate", target=target)
        ys = [strat.next_target(_ctx(i)).y for i in range(4)]
        assert ys == [0.6, -0.6, 0.6, -0.6]

    def test_x_is_center(self, target: TableTarget) -> None:
        strat = FixedPatternStrategy(pattern="oscillate", target=target)
        assert all(strat.next_target(_ctx(i)).x == 2.0 for i in range(4))


class TestRandomPattern:
    def test_within_bounds(self, target: TableTarget) -> None:
        strat = FixedPatternStrategy(pattern="random", target=target)
        for i in range(20):
            p = strat.next_target(_ctx(i, seed=i))
            assert -0.6 <= p.y <= 0.6
            assert p.x == 2.0

    def test_deterministic_under_same_rng(self, target: TableTarget) -> None:
        strat = FixedPatternStrategy(pattern="random", target=target)
        a = strat.next_target(DrillContext(shot_index=0, rng=random.Random(42)))
        b = strat.next_target(DrillContext(shot_index=0, rng=random.Random(42)))
        assert a.y == b.y


class TestFigure8Pattern:
    def test_visits_four_corner_quadrants_in_order(self, target: TableTarget) -> None:
        strat = FixedPatternStrategy(pattern="figure8", target=target)
        # Corner phases of the 8-step lissajous: indices 1,3,5,7 hit the four
        # (sign dx, sign dy) quadrants in this order.
        corners = [strat.next_target(_ctx(i)) for i in (1, 3, 5, 7)]
        signs = [((p.x > 2.0) - (p.x < 2.0), (p.y > 0) - (p.y < 0)) for p in corners]
        assert signs == [(1, 1), (1, -1), (-1, 1), (-1, -1)]

    def test_within_bounds(self, target: TableTarget) -> None:
        strat = FixedPatternStrategy(pattern="figure8", target=target)
        for i in range(16):
            p = strat.next_target(_ctx(i))
            assert 1.5 - 1e-9 <= p.x <= 2.5 + 1e-9
            assert -0.6 - 1e-9 <= p.y <= 0.6 + 1e-9

    def test_crossing_point_near_center(self, target: TableTarget) -> None:
        strat = FixedPatternStrategy(pattern="figure8", target=target)
        p = strat.next_target(_ctx(0))
        assert p.x == pytest.approx(2.0)
        assert p.y == pytest.approx(0.0)


class TestUnknownPattern:
    def test_rejects_unknown_pattern(self, target: TableTarget) -> None:
        with pytest.raises(ValueError, match=r"pattern"):
            FixedPatternStrategy(pattern="zigzag", target=target)  # type: ignore[arg-type]
