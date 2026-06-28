"""Tests for the frozen pydantic value objects in mcenroebot.launch.value_objects."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mcenroebot.launch import LaunchGeometry, ShotSpec, ThrottleMap, WheelCommand


class TestShotSpec:
    def test_accepts_valid_values(self) -> None:
        spec = ShotSpec(speed_mps=8.0, spin_rad_s=-30.0, spin_axis_deg=45.0)
        assert spec.speed_mps == 8.0
        assert spec.spin_rad_s == -30.0
        assert spec.spin_axis_deg == 45.0

    @pytest.mark.parametrize("speed", [0.0, -1.0])
    def test_non_positive_speed_raises(self, speed: float) -> None:
        with pytest.raises(ValidationError, match=r"speed_mps"):
            ShotSpec(speed_mps=speed, spin_rad_s=0.0, spin_axis_deg=0.0)

    @pytest.mark.parametrize("axis", [-0.1, 360.0, 400.0])
    def test_spin_axis_out_of_range_raises(self, axis: float) -> None:
        with pytest.raises(ValidationError, match=r"spin_axis_deg"):
            ShotSpec(speed_mps=8.0, spin_rad_s=0.0, spin_axis_deg=axis)

    def test_spin_axis_boundaries(self) -> None:
        ShotSpec(speed_mps=8.0, spin_rad_s=0.0, spin_axis_deg=0.0)
        ShotSpec(speed_mps=8.0, spin_rad_s=0.0, spin_axis_deg=359.999)

    def test_is_frozen(self) -> None:
        spec = ShotSpec(speed_mps=8.0, spin_rad_s=0.0, spin_axis_deg=0.0)
        with pytest.raises(ValidationError):
            spec.speed_mps = 9.0  # type: ignore[misc]


class TestWheelCommand:
    def test_accepts_valid_values(self) -> None:
        cmd = WheelCommand(top_rpm=3000.0, bottom_rpm=2000.0, head_roll_deg=90.0)
        assert cmd.top_rpm == 3000.0
        assert cmd.bottom_rpm == 2000.0
        assert cmd.head_roll_deg == 90.0

    @pytest.mark.parametrize("top,bottom", [(-1.0, 0.0), (0.0, -0.1)])
    def test_negative_rpm_raises(self, top: float, bottom: float) -> None:
        with pytest.raises(ValidationError, match=r"rpm"):
            WheelCommand(top_rpm=top, bottom_rpm=bottom, head_roll_deg=0.0)

    @pytest.mark.parametrize("roll", [-0.1, 180.1, 270.0])
    def test_head_roll_out_of_range_raises(self, roll: float) -> None:
        with pytest.raises(ValidationError, match=r"head_roll_deg"):
            WheelCommand(top_rpm=0.0, bottom_rpm=0.0, head_roll_deg=roll)

    def test_head_roll_boundaries(self) -> None:
        WheelCommand(top_rpm=0.0, bottom_rpm=0.0, head_roll_deg=0.0)
        WheelCommand(top_rpm=0.0, bottom_rpm=0.0, head_roll_deg=180.0)

    def test_is_frozen(self) -> None:
        cmd = WheelCommand(top_rpm=1.0, bottom_rpm=1.0, head_roll_deg=0.0)
        with pytest.raises(ValidationError):
            cmd.top_rpm = 2.0  # type: ignore[misc]


class TestLaunchGeometry:
    def test_defaults(self) -> None:
        geo = LaunchGeometry(wheel_diameter_m=0.055, max_wheel_rpm=10000.0, launch_height_m=0.3)
        assert geo.ball_radius_m == 0.02
        assert geo.grip_efficiency == 0.85
        assert geo.spin_efficiency == 0.85

    def test_ballistic_defaults(self) -> None:
        geo = LaunchGeometry(wheel_diameter_m=0.055, max_wheel_rpm=10000.0, launch_height_m=0.3)
        assert geo.launch_height_m == pytest.approx(0.3)
        assert geo.gravity_m_s2 == pytest.approx(9.81)
        assert geo.pitch_neutral_deg == pytest.approx(90.0)

    def test_zero_launch_height_is_allowed(self) -> None:
        geo = LaunchGeometry(wheel_diameter_m=0.055, max_wheel_rpm=10000.0, launch_height_m=0.0)
        assert geo.launch_height_m == 0.0

    @pytest.mark.parametrize(
        "field,value",
        [
            ("wheel_diameter_m", 0.0),
            ("ball_radius_m", -0.01),
            ("grip_efficiency", 0.0),
            ("grip_efficiency", 1.5),
            ("spin_efficiency", 0.0),
            ("spin_efficiency", 1.1),
            ("max_wheel_rpm", 0.0),
            ("launch_height_m", -0.1),
            ("gravity_m_s2", 0.0),
            ("gravity_m_s2", -9.81),
            ("pitch_neutral_deg", -0.1),
            ("pitch_neutral_deg", 180.1),
        ],
    )
    def test_out_of_range_raises(self, field: str, value: float) -> None:
        kwargs: dict[str, float] = {
            "wheel_diameter_m": 0.055,
            "max_wheel_rpm": 10000.0,
            "launch_height_m": 0.3,
        }
        kwargs[field] = value
        with pytest.raises(ValidationError, match=field):
            LaunchGeometry(**kwargs)

    def test_is_frozen(self) -> None:
        geo = LaunchGeometry(wheel_diameter_m=0.055, max_wheel_rpm=10000.0, launch_height_m=0.3)
        with pytest.raises(ValidationError):
            geo.wheel_diameter_m = 0.06  # type: ignore[misc]


class TestThrottleMap:
    def test_throttle_for_linear(self) -> None:
        tm = ThrottleMap(rpm_at_full_throttle=10000.0)
        assert tm.throttle_for(5000.0) == pytest.approx(0.5)

    def test_throttle_for_clamps_high(self) -> None:
        tm = ThrottleMap(rpm_at_full_throttle=10000.0)
        assert tm.throttle_for(15000.0) == 1.0

    def test_throttle_for_clamps_low(self) -> None:
        tm = ThrottleMap(rpm_at_full_throttle=10000.0)
        assert tm.throttle_for(-100.0) == 0.0

    def test_floors_default_to_zero(self) -> None:
        tm = ThrottleMap(rpm_at_full_throttle=10000.0)
        assert tm.top_floor == 0.0
        assert tm.bottom_floor == 0.0
        # With zero floors the per-wheel helpers are plain linear.
        assert tm.throttle_for_top(5000.0) == pytest.approx(0.5)
        assert tm.throttle_for_bottom(5000.0) == pytest.approx(0.5)

    def test_per_wheel_floors_remap_into_live_band(self) -> None:
        tm = ThrottleMap(rpm_at_full_throttle=10000.0, top_floor=0.08, bottom_floor=0.05)
        # rpm>0 is remapped into [floor, 1]: floor + frac*(1-floor).
        assert tm.throttle_for_top(5000.0) == pytest.approx(0.08 + 0.5 * 0.92)
        assert tm.throttle_for_bottom(5000.0) == pytest.approx(0.05 + 0.5 * 0.95)
        # Same rpm, different wheel -> different throttle (the whole point).
        assert tm.throttle_for_top(5000.0) != tm.throttle_for_bottom(5000.0)

    def test_full_rpm_maps_to_one_regardless_of_floor(self) -> None:
        tm = ThrottleMap(rpm_at_full_throttle=10000.0, top_floor=0.08, bottom_floor=0.05)
        assert tm.throttle_for_top(10000.0) == pytest.approx(1.0)
        assert tm.throttle_for_bottom(10000.0) == pytest.approx(1.0)

    def test_zero_rpm_is_off_even_with_floor(self) -> None:
        tm = ThrottleMap(rpm_at_full_throttle=10000.0, top_floor=0.08, bottom_floor=0.05)
        assert tm.throttle_for_top(0.0) == 0.0
        assert tm.throttle_for_bottom(0.0) == 0.0

    @pytest.mark.parametrize(
        "field,value",
        [("top_floor", -0.1), ("top_floor", 1.0), ("bottom_floor", -0.01), ("bottom_floor", 1.5)],
    )
    def test_floor_out_of_range_raises(self, field: str, value: float) -> None:
        with pytest.raises(ValidationError, match=field):
            ThrottleMap(rpm_at_full_throttle=10000.0, **{field: value})

    def test_floor_boundaries(self) -> None:
        ThrottleMap(rpm_at_full_throttle=10000.0, top_floor=0.0, bottom_floor=0.999)

    def test_non_positive_full_throttle_raises(self) -> None:
        with pytest.raises(ValidationError, match=r"rpm_at_full_throttle"):
            ThrottleMap(rpm_at_full_throttle=0.0)

    def test_is_frozen(self) -> None:
        tm = ThrottleMap(rpm_at_full_throttle=10000.0)
        with pytest.raises(ValidationError):
            tm.rpm_at_full_throttle = 5000.0  # type: ignore[misc]
