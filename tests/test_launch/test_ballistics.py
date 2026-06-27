"""Tests for the vacuum projectile solver in mcenroebot.launch.ballistics."""

from __future__ import annotations

import math

import pytest

from mcenroebot.launch import Arc
from mcenroebot.launch.ballistics import solve_elevation


def _height_at_range(
    *, theta_rad: float, d: float, v: float, launch_height: float, g: float
) -> float:
    """Closed-form ball height at horizontal distance ``d`` for a vacuum shot."""
    return (
        launch_height
        + d * math.tan(theta_rad)
        - g * d * d / (2.0 * v * v * math.cos(theta_rad) ** 2)
    )


class TestKnownAngles:
    def test_low_arc_recovers_30_degrees(self) -> None:
        # Flat ground (launch == target height). For theta = 30°, the range is
        # d = v^2 * sin(2*theta) / g. The low arc must recover exactly 30°.
        v, g = 10.0, 9.81
        d = v * v * math.sin(math.radians(60.0)) / g
        theta = solve_elevation(
            horizontal_range_m=d,
            target_height_m=0.0,
            launch_height_m=0.0,
            speed_mps=v,
            gravity_m_s2=g,
            arc=Arc.LOW,
        )
        assert theta is not None
        assert math.degrees(theta) == pytest.approx(30.0, abs=1e-6)

    def test_high_arc_is_complementary_60_degrees(self) -> None:
        # Same geometry, the high arc is the complementary angle, 60°.
        v, g = 10.0, 9.81
        d = v * v * math.sin(math.radians(60.0)) / g
        theta = solve_elevation(
            horizontal_range_m=d,
            target_height_m=0.0,
            launch_height_m=0.0,
            speed_mps=v,
            gravity_m_s2=g,
            arc=Arc.HIGH,
        )
        assert theta is not None
        assert math.degrees(theta) == pytest.approx(60.0, abs=1e-6)

    def test_low_arc_is_shallower_than_high_arc(self) -> None:
        v = 12.0
        d = 6.0
        low = solve_elevation(
            horizontal_range_m=d, target_height_m=0.0, launch_height_m=0.0, speed_mps=v
        )
        high = solve_elevation(
            horizontal_range_m=d,
            target_height_m=0.0,
            launch_height_m=0.0,
            speed_mps=v,
            arc=Arc.HIGH,
        )
        assert low is not None and high is not None
        assert low < high

    def test_low_arc_is_the_default(self) -> None:
        v, d = 12.0, 6.0
        default = solve_elevation(
            horizontal_range_m=d, target_height_m=0.0, launch_height_m=0.0, speed_mps=v
        )
        explicit_low = solve_elevation(
            horizontal_range_m=d,
            target_height_m=0.0,
            launch_height_m=0.0,
            speed_mps=v,
            arc=Arc.LOW,
        )
        assert default == explicit_low


class TestNonzeroTargetHeight:
    @pytest.mark.parametrize("arc", [Arc.LOW, Arc.HIGH])
    @pytest.mark.parametrize("z_target", [0.5, -0.4, 1.2])
    def test_round_trip_through_solver(self, arc: Arc, z_target: float) -> None:
        # Pick an elevation, compute where that shot actually is at range d, then
        # confirm the solver recovers an angle whose trajectory hits that point.
        v, g, d, launch_height = 11.0, 9.81, 5.0, 0.3
        # Choose a theta whose trajectory passes through (d, z_target). We
        # instead derive z_target's matching theta empirically: sweep is overkill;
        # use the solver and verify self-consistency with the closed form.
        theta = solve_elevation(
            horizontal_range_m=d,
            target_height_m=z_target,
            launch_height_m=launch_height,
            speed_mps=v,
            gravity_m_s2=g,
            arc=arc,
        )
        assert theta is not None
        recovered_height = _height_at_range(
            theta_rad=theta, d=d, v=v, launch_height=launch_height, g=g
        )
        assert recovered_height == pytest.approx(z_target, abs=1e-9)


class TestOutOfRange:
    def test_too_far_for_speed_returns_none(self) -> None:
        # A slow ball cannot reach a distant target: discriminant < 0 -> None.
        assert (
            solve_elevation(
                horizontal_range_m=100.0,
                target_height_m=0.0,
                launch_height_m=0.0,
                speed_mps=3.0,
            )
            is None
        )

    def test_target_too_high_returns_none(self) -> None:
        assert (
            solve_elevation(
                horizontal_range_m=2.0,
                target_height_m=50.0,
                launch_height_m=0.0,
                speed_mps=5.0,
            )
            is None
        )


class TestDegenerateInputs:
    @pytest.mark.parametrize("v", [0.0, -5.0])
    def test_non_positive_speed_returns_none(self, v: float) -> None:
        assert (
            solve_elevation(
                horizontal_range_m=3.0, target_height_m=0.0, launch_height_m=0.0, speed_mps=v
            )
            is None
        )

    @pytest.mark.parametrize("d", [0.0, -1.0])
    def test_non_positive_range_returns_none(self, d: float) -> None:
        assert (
            solve_elevation(
                horizontal_range_m=d, target_height_m=0.0, launch_height_m=0.0, speed_mps=8.0
            )
            is None
        )
