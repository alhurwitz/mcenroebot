"""Tests for AimController.pan_angle_for and its `_demo` helper."""

from __future__ import annotations

import math

import pytest

from mcenroebot.aim import AimController, AimGeometry, Position3D, ServoAngles


class TestPanAngleFor:
    def setup_method(self) -> None:
        self.ctrl = AimController()  # default geometry, yaw_neutral=90

    def test_directly_forward_gives_neutral(self) -> None:
        # Pure +X -> yaw = atan2(0, x) = 0 -> 90° neutral.
        pan = self.ctrl.pan_angle_for(Position3D(x=1.5, y=0.0, z=0.0))
        assert pan == pytest.approx(90.0)

    def test_ball_to_the_left_yaws_left(self) -> None:
        # +Y is left, so atan2(+y, +x) > 0 -> pan > 90.
        pan = self.ctrl.pan_angle_for(Position3D(x=1.5, y=0.5, z=0.0))
        assert pan is not None
        assert pan > 90.0

    def test_ball_to_the_right_yaws_right(self) -> None:
        pan = self.ctrl.pan_angle_for(Position3D(x=1.5, y=-0.5, z=0.0))
        assert pan is not None
        assert pan < 90.0

    def test_left_right_symmetry_about_neutral(self) -> None:
        left = self.ctrl.pan_angle_for(Position3D(x=1.5, y=0.5, z=0.0))
        right = self.ctrl.pan_angle_for(Position3D(x=1.5, y=-0.5, z=0.0))
        assert left is not None and right is not None
        # Mirrored targets sit equal angular distances either side of neutral.
        assert (left - 90.0) == pytest.approx(90.0 - right)

    def test_height_is_ignored(self) -> None:
        # Pan is horizontal only; z must not change the answer.
        flat = self.ctrl.pan_angle_for(Position3D(x=1.5, y=0.5, z=0.0))
        high = self.ctrl.pan_angle_for(Position3D(x=1.5, y=0.5, z=2.0))
        assert flat == pytest.approx(high)

    @pytest.mark.parametrize(
        "target,expected",
        [
            (Position3D(x=1.5, y=0.0, z=0.0), 90.0),
            (Position3D(x=0.5, y=0.5, z=0.0), 90.0 + math.degrees(math.atan2(0.5, 0.5))),
            (Position3D(x=0.5, y=-0.5, z=0.0), 90.0 + math.degrees(math.atan2(-0.5, 0.5))),
        ],
    )
    def test_matches_closed_form(self, target: Position3D, expected: float) -> None:
        pan = self.ctrl.pan_angle_for(target)
        assert pan == pytest.approx(expected, abs=1e-6)

    def test_target_at_left_limit_returns_180(self) -> None:
        # Straight to the left (x=0, +y) -> yaw +90° -> pan exactly 180.
        pan = self.ctrl.pan_angle_for(Position3D(x=0.0, y=1.0, z=0.0))
        assert pan == pytest.approx(180.0)

    def test_target_at_right_limit_returns_0(self) -> None:
        pan = self.ctrl.pan_angle_for(Position3D(x=0.0, y=-1.0, z=0.0))
        assert pan == pytest.approx(0.0)

    def test_target_behind_left_is_out_of_range(self) -> None:
        # Behind and to the left -> yaw > +90° -> pan > 180 -> None.
        assert self.ctrl.pan_angle_for(Position3D(x=-0.5, y=0.5, z=0.0)) is None

    def test_target_behind_right_is_out_of_range(self) -> None:
        assert self.ctrl.pan_angle_for(Position3D(x=-0.5, y=-0.5, z=0.0)) is None


class TestCustomGeometry:
    def test_neutral_offset_shifts_output(self) -> None:
        custom = AimController(AimGeometry(yaw_neutral_deg=60.0))
        pan = custom.pan_angle_for(Position3D(x=1.5, y=0.0, z=0.0))
        assert pan == pytest.approx(60.0)

    def test_neutral_offset_moves_reachable_window(self) -> None:
        # With neutral at 170°, even a modest left target pushes pan past 180.
        custom = AimController(AimGeometry(yaw_neutral_deg=170.0))
        assert custom.pan_angle_for(Position3D(x=1.0, y=1.0, z=0.0)) is None


class TestDeprecatedV2Shim:
    """compute()/is_reachable() are a V2 turret shim for the shelved rally."""

    def setup_method(self) -> None:
        self.ctrl = AimController()  # default geometry, V2 arm reach 0.20 m

    def test_inside_arm_reach_is_reachable(self) -> None:
        assert self.ctrl.is_reachable(Position3D(x=0.1, y=0.0, z=0.0))

    def test_beyond_arm_reach_is_unreachable(self) -> None:
        assert not self.ctrl.is_reachable(Position3D(x=5.0, y=0.0, z=0.0))

    def test_compute_forward_target_is_neutral(self) -> None:
        angles = self.ctrl.compute(Position3D(x=0.1, y=0.0, z=0.0))
        assert isinstance(angles, ServoAngles)
        assert angles.yaw_deg == pytest.approx(90.0)
        assert angles.pitch_deg == pytest.approx(90.0)

    def test_compute_high_target_pitches_up(self) -> None:
        angles = self.ctrl.compute(Position3D(x=0.1, y=0.0, z=0.1))
        assert angles is not None
        assert angles.pitch_deg > 90.0

    def test_compute_out_of_reach_returns_none(self) -> None:
        assert self.ctrl.compute(Position3D(x=5.0, y=0.0, z=0.0)) is None


class TestDemo:
    def test_demo_runs_without_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        from mcenroebot.aim import _demo

        _demo()
        captured = capsys.readouterr()
        for label in ("Forward", "Forward and left", "Forward and right", "Behind"):
            assert label in captured.out, f"Demo missing case: {label!r}"
        assert "OUT OF RANGE" in captured.out
