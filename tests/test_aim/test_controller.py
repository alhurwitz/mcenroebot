"""Tests for AimController and its `_demo` helper."""

from __future__ import annotations

import math

import pytest

from mcenroebot.aim import AimController, Position3D, ServoAngles, TurretGeometry


class TestAimControllerReachability:
    def setup_method(self) -> None:
        self.ctrl = AimController()  # default geometry, arm=0.20m

    def test_target_inside_arm_is_reachable(self) -> None:
        assert self.ctrl.is_reachable(Position3D(x=0.10, y=0.0, z=0.0))

    def test_target_exactly_at_arm_length_is_reachable(self) -> None:
        # On the boundary should be reachable (<= comparison).
        assert self.ctrl.is_reachable(Position3D(x=0.20, y=0.0, z=0.0))

    def test_target_beyond_arm_length_is_unreachable(self) -> None:
        assert not self.ctrl.is_reachable(Position3D(x=0.21, y=0.0, z=0.0))

    def test_unreachable_compute_returns_none(self) -> None:
        assert self.ctrl.compute(Position3D(x=0.5, y=0.5, z=0.5)) is None


class TestAimControllerCompute:
    def setup_method(self) -> None:
        self.ctrl = AimController()

    def test_directly_forward_gives_neutral_pose(self) -> None:
        angles = self.ctrl.compute(Position3D(x=0.18, y=0.0, z=0.0))
        assert angles is not None
        assert angles.yaw_deg == pytest.approx(90.0)
        assert angles.pitch_deg == pytest.approx(90.0)

    def test_ball_to_the_left_yaws_left(self) -> None:
        # +Y is left, so atan2(+y, +x) > 0 -> yaw > 90.
        angles = self.ctrl.compute(Position3D(x=0.10, y=0.10, z=0.0))
        assert angles is not None
        assert angles.yaw_deg > 90.0
        assert angles.pitch_deg == pytest.approx(90.0)

    def test_ball_to_the_right_yaws_right(self) -> None:
        angles = self.ctrl.compute(Position3D(x=0.10, y=-0.10, z=0.0))
        assert angles is not None
        assert angles.yaw_deg < 90.0
        assert angles.pitch_deg == pytest.approx(90.0)

    def test_ball_high_pitches_up(self) -> None:
        angles = self.ctrl.compute(Position3D(x=0.10, y=0.0, z=0.10))
        assert angles is not None
        assert angles.pitch_deg > 90.0

    def test_ball_low_pitches_down(self) -> None:
        angles = self.ctrl.compute(Position3D(x=0.10, y=0.0, z=-0.10))
        assert angles is not None
        assert angles.pitch_deg < 90.0

    @pytest.mark.parametrize(
        "target,expected_yaw,expected_pitch",
        [
            # Forward at paddle height -> neutral pose.
            (Position3D(x=0.18, y=0.0, z=0.0), 90.0, 90.0),
            # 45° left, level: yaw = 90 + 45 = 135.
            (
                Position3D(x=0.10, y=0.10, z=0.0),
                90.0 + math.degrees(math.atan2(0.10, 0.10)),
                90.0,
            ),
            # 45° right, level: yaw = 90 - 45 = 45.
            (
                Position3D(x=0.10, y=-0.10, z=0.0),
                90.0 + math.degrees(math.atan2(-0.10, 0.10)),
                90.0,
            ),
            # 45° up, no yaw: pitch = 135.
            (
                Position3D(x=0.10, y=0.0, z=0.10),
                90.0,
                90.0 + math.degrees(math.atan2(0.10, 0.10)),
            ),
        ],
    )
    def test_compute_matches_closed_form(
        self,
        target: Position3D,
        expected_yaw: float,
        expected_pitch: float,
    ) -> None:
        angles = self.ctrl.compute(target)
        assert angles is not None
        assert angles.yaw_deg == pytest.approx(expected_yaw, abs=1e-6)
        assert angles.pitch_deg == pytest.approx(expected_pitch, abs=1e-6)

    def test_output_is_always_servoangles_instance(self) -> None:
        angles = self.ctrl.compute(Position3D(x=0.05, y=0.05, z=0.05))
        assert isinstance(angles, ServoAngles)

    def test_yaw_clamped_to_servo_range_for_target_behind_robot(self) -> None:
        # A target with negative x ("behind") would compute yaw outside
        # [0, 180]. The controller must clamp; we verify the result is
        # always a valid ServoAngles.
        angles = self.ctrl.compute(Position3D(x=-0.05, y=0.05, z=0.0))
        assert angles is not None
        assert 0.0 <= angles.yaw_deg <= 180.0
        assert 0.0 <= angles.pitch_deg <= 180.0

    def test_zero_target_is_reachable_and_neutral_ish(self) -> None:
        # The (0, 0, 0) point is "at the origin" — a degenerate case but
        # the function should still return a valid ServoAngles.
        angles = self.ctrl.compute(Position3D(x=0.0, y=0.0, z=0.0))
        assert angles is not None
        # yaw = atan2(0, 0) = 0 by convention -> 90° + 0 = 90°.
        # pitch = atan2(0, 0) = 0 -> 90°.
        assert angles.yaw_deg == pytest.approx(90.0)
        assert angles.pitch_deg == pytest.approx(90.0)


class TestAimControllerCustomGeometry:
    def test_smaller_arm_length_shrinks_reachable_set(self) -> None:
        small_arm = AimController(TurretGeometry(arm_length_m=0.10))
        # 15 cm forward is inside default reach but outside this one.
        target = Position3D(x=0.15, y=0.0, z=0.0)
        assert not small_arm.is_reachable(target)
        assert small_arm.compute(target) is None

    def test_neutral_offsets_shift_output(self) -> None:
        # If we change yaw_neutral from 90 to 60, a forward target should
        # report yaw=60 instead of yaw=90.
        custom = AimController(
            TurretGeometry(arm_length_m=0.20, yaw_neutral_deg=60.0, pitch_neutral_deg=70.0)
        )
        angles = custom.compute(Position3D(x=0.18, y=0.0, z=0.0))
        assert angles is not None
        assert angles.yaw_deg == pytest.approx(60.0)
        assert angles.pitch_deg == pytest.approx(70.0)


class TestDemo:
    def test_demo_runs_without_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        from mcenroebot.aim import _demo

        _demo()
        captured = capsys.readouterr()
        # Every demo case header should appear in stdout.
        for label in (
            "Forward, paddle-height",
            "Forward and high",
            "Forward and left",
            "Forward and right",
            "Out of reach",
        ):
            assert label in captured.out, f"Demo missing case: {label!r}"
        # The OUT OF REACH branch should print, since the last case is unreachable.
        assert "OUT OF REACH" in captured.out
