"""Tests for LaunchController — the pure-math two-wheel launch solver."""

from __future__ import annotations

import math

import pytest

from mcenroebot.launch import LaunchController, LaunchGeometry, ShotSpec, ThrottleMap, WheelCommand


def _rpm(u_surface: float, wheel_diameter_m: float) -> float:
    return u_surface * 60.0 / (math.pi * wheel_diameter_m)


@pytest.fixture
def geometry() -> LaunchGeometry:
    return LaunchGeometry(
        wheel_diameter_m=0.055,
        ball_radius_m=0.02,
        grip_efficiency=0.85,
        spin_efficiency=0.85,
        max_wheel_rpm=10000.0,
    )


@pytest.fixture
def controller(geometry: LaunchGeometry) -> LaunchController:
    return LaunchController(geometry=geometry)


class TestCompute:
    def test_zero_spin_gives_equal_wheels(
        self, controller: LaunchController, geometry: LaunchGeometry
    ) -> None:
        cmd = controller.compute(ShotSpec(speed_mps=6.0, spin_rad_s=0.0, spin_axis_deg=0.0))
        assert cmd is not None
        assert cmd.top_rpm == pytest.approx(cmd.bottom_rpm)
        expected = _rpm(6.0 / geometry.grip_efficiency, geometry.wheel_diameter_m)
        assert cmd.top_rpm == pytest.approx(expected)

    def test_positive_spin_top_faster(self, controller: LaunchController) -> None:
        cmd = controller.compute(ShotSpec(speed_mps=6.0, spin_rad_s=20.0, spin_axis_deg=0.0))
        assert cmd is not None
        assert cmd.top_rpm > cmd.bottom_rpm

    def test_negative_spin_bottom_faster(self, controller: LaunchController) -> None:
        cmd = controller.compute(ShotSpec(speed_mps=6.0, spin_rad_s=-20.0, spin_axis_deg=0.0))
        assert cmd is not None
        assert cmd.bottom_rpm > cmd.top_rpm

    def test_round_trip_recovers_wheel_speeds(
        self, controller: LaunchController, geometry: LaunchGeometry
    ) -> None:
        # Pick target surface speeds, derive the ShotSpec they imply, confirm
        # compute() reproduces exactly those wheel rpms.
        u_top, u_bottom = 8.0, 6.0
        mean_surface = (u_top + u_bottom) / 2.0
        diff_surface = u_top - u_bottom
        speed = mean_surface * geometry.grip_efficiency
        spin = diff_surface * geometry.spin_efficiency / (2.0 * geometry.ball_radius_m)

        cmd = controller.compute(ShotSpec(speed_mps=speed, spin_rad_s=spin, spin_axis_deg=0.0))
        assert cmd is not None
        assert cmd.top_rpm == pytest.approx(_rpm(u_top, geometry.wheel_diameter_m), abs=1e-6)
        assert cmd.bottom_rpm == pytest.approx(_rpm(u_bottom, geometry.wheel_diameter_m), abs=1e-6)

    def test_spin_too_high_for_speed_returns_none(self, controller: LaunchController) -> None:
        # Huge backspin relative to a slow ball drives u_top negative -> None,
        # never a negative rpm.
        cmd = controller.compute(ShotSpec(speed_mps=1.0, spin_rad_s=500.0, spin_axis_deg=0.0))
        assert cmd is None

    def test_rpm_over_max_returns_none(self, geometry: LaunchGeometry) -> None:
        low_max = LaunchGeometry(
            wheel_diameter_m=geometry.wheel_diameter_m,
            ball_radius_m=geometry.ball_radius_m,
            grip_efficiency=geometry.grip_efficiency,
            spin_efficiency=geometry.spin_efficiency,
            max_wheel_rpm=100.0,
        )
        controller = LaunchController(geometry=low_max)
        cmd = controller.compute(ShotSpec(speed_mps=20.0, spin_rad_s=0.0, spin_axis_deg=0.0))
        assert cmd is None

    @pytest.mark.parametrize(
        "axis,expected_roll",
        [(0.0, 0.0), (90.0, 90.0), (180.0, 0.0), (270.0, 90.0), (200.0, 20.0)],
    )
    def test_head_roll_folds_into_0_180(
        self, controller: LaunchController, axis: float, expected_roll: float
    ) -> None:
        cmd = controller.compute(ShotSpec(speed_mps=6.0, spin_rad_s=0.0, spin_axis_deg=axis))
        assert cmd is not None
        assert cmd.head_roll_deg == pytest.approx(expected_roll)

    def test_default_geometry_is_used_when_omitted(self) -> None:
        # Constructing without geometry must still work (requires a default).
        controller = LaunchController()
        cmd = controller.compute(ShotSpec(speed_mps=5.0, spin_rad_s=0.0, spin_axis_deg=0.0))
        assert cmd is not None


class TestThrottles:
    def test_throttles_map_each_wheel(self, controller: LaunchController) -> None:
        cmd = WheelCommand(top_rpm=5000.0, bottom_rpm=2500.0, head_roll_deg=0.0)
        tm = ThrottleMap(rpm_at_full_throttle=10000.0)
        top, bottom = controller.throttles(cmd, tm)
        assert top == pytest.approx(0.5)
        assert bottom == pytest.approx(0.25)

    def test_throttles_clamp(self, controller: LaunchController) -> None:
        cmd = WheelCommand(top_rpm=20000.0, bottom_rpm=0.0, head_roll_deg=0.0)
        tm = ThrottleMap(rpm_at_full_throttle=10000.0)
        top, bottom = controller.throttles(cmd, tm)
        assert top == 1.0
        assert bottom == 0.0


class TestDemo:
    def test_demo_runs_without_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        from mcenroebot.launch import _demo

        _demo()
        captured = capsys.readouterr()
        for label in ("Flat medium", "Heavy topspin", "Backspin", "Sidespin", "Spin too high"):
            assert label in captured.out
        assert "OUT OF ENVELOPE" in captured.out
