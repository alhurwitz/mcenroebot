"""Tests for LaunchController — the pure-math two-wheel launch solver."""

from __future__ import annotations

import math

import pytest

from mcenroebot.aim import Position3D
from mcenroebot.launch import (
    Arc,
    LaunchController,
    LaunchGeometry,
    ShotSpec,
    ThrottleMap,
    WheelCommand,
)


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
        launch_height_m=0.3,
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
            launch_height_m=geometry.launch_height_m,
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


class TestTiltAngleFor:
    def test_known_low_arc_maps_to_servo_angle(self) -> None:
        # Flat ground, theta_low = 30° -> tilt = pitch_neutral + 30 = 120.
        v, g = 10.0, 9.81
        d = v * v * math.sin(math.radians(60.0)) / g
        geo = LaunchGeometry(
            wheel_diameter_m=0.055,
            max_wheel_rpm=10000.0,
            launch_height_m=0.0,
            gravity_m_s2=g,
            pitch_neutral_deg=90.0,
        )
        ctrl = LaunchController(geometry=geo)
        spec = ShotSpec(speed_mps=v, spin_rad_s=0.0, spin_axis_deg=0.0)
        tilt = ctrl.tilt_angle_for(Position3D(x=d, y=0.0, z=0.0), spec)
        assert tilt == pytest.approx(120.0, abs=1e-6)

    def test_high_arc_is_steeper_than_low(self, controller: LaunchController) -> None:
        spec = ShotSpec(speed_mps=11.0, spin_rad_s=0.0, spin_axis_deg=0.0)
        target = Position3D(x=4.0, y=0.0, z=0.0)
        low = controller.tilt_angle_for(target, spec, arc=Arc.LOW)
        high = controller.tilt_angle_for(target, spec, arc=Arc.HIGH)
        assert low is not None and high is not None
        assert high > low

    def test_low_arc_is_the_default(self, controller: LaunchController) -> None:
        spec = ShotSpec(speed_mps=11.0, spin_rad_s=0.0, spin_axis_deg=0.0)
        target = Position3D(x=4.0, y=0.0, z=0.0)
        assert controller.tilt_angle_for(target, spec) == controller.tilt_angle_for(
            target, spec, arc=Arc.LOW
        )

    def test_uses_horizontal_distance_so_y_is_symmetric(self, controller: LaunchController) -> None:
        spec = ShotSpec(speed_mps=11.0, spin_rad_s=0.0, spin_axis_deg=0.0)
        left = controller.tilt_angle_for(Position3D(x=2.0, y=0.6, z=0.0), spec)
        right = controller.tilt_angle_for(Position3D(x=2.0, y=-0.6, z=0.0), spec)
        assert left is not None and right is not None
        assert left == pytest.approx(right)

    def test_higher_target_needs_more_elevation(self, controller: LaunchController) -> None:
        spec = ShotSpec(speed_mps=11.0, spin_rad_s=0.0, spin_axis_deg=0.0)
        flat = controller.tilt_angle_for(Position3D(x=2.0, y=0.0, z=0.0), spec)
        raised = controller.tilt_angle_for(Position3D(x=2.0, y=0.0, z=1.0), spec)
        assert flat is not None and raised is not None
        assert raised > flat

    def test_out_of_ballistic_range_returns_none(self, controller: LaunchController) -> None:
        # A slow ball cannot reach a far target -> no real elevation -> None.
        spec = ShotSpec(speed_mps=3.0, spin_rad_s=0.0, spin_axis_deg=0.0)
        assert controller.tilt_angle_for(Position3D(x=100.0, y=0.0, z=0.0), spec) is None

    def test_zero_horizontal_distance_returns_none(self, controller: LaunchController) -> None:
        # Target directly above/at the launch axis -> no bearing -> None.
        spec = ShotSpec(speed_mps=6.0, spin_rad_s=0.0, spin_axis_deg=0.0)
        assert controller.tilt_angle_for(Position3D(x=0.0, y=0.0, z=0.0), spec) is None

    def test_servo_angle_out_of_range_returns_none(self) -> None:
        # Neutral parked near the upper limit: a lofted high arc pushes the
        # mapped tilt past 180° -> unmappable -> None.
        geo = LaunchGeometry(
            wheel_diameter_m=0.055,
            max_wheel_rpm=10000.0,
            launch_height_m=0.0,
            pitch_neutral_deg=178.0,
        )
        ctrl = LaunchController(geometry=geo)
        spec = ShotSpec(speed_mps=11.0, spin_rad_s=0.0, spin_axis_deg=0.0)
        assert ctrl.tilt_angle_for(Position3D(x=4.0, y=0.0, z=0.0), spec, arc=Arc.HIGH) is None


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

    def test_throttles_use_per_wheel_floors(self, controller: LaunchController) -> None:
        # Equal commanded rpm, different per-wheel floors -> different throttles.
        cmd = WheelCommand(top_rpm=5000.0, bottom_rpm=5000.0, head_roll_deg=0.0)
        tm = ThrottleMap(rpm_at_full_throttle=10000.0, front_floor=0.08, back_floor=0.05)
        top, bottom = controller.throttles(cmd, tm)
        assert top == pytest.approx(0.08 + 0.5 * 0.92)
        assert bottom == pytest.approx(0.05 + 0.5 * 0.95)
        assert top > bottom


class TestDemo:
    def test_demo_runs_without_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        from mcenroebot.launch import _demo

        _demo()
        captured = capsys.readouterr()
        for label in ("Flat medium", "Heavy topspin", "Backspin", "Sidespin", "Spin too high"):
            assert label in captured.out
        assert "OUT OF ENVELOPE" in captured.out
