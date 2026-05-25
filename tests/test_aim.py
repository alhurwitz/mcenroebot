"""Tests for mcenroebot.aim."""

from __future__ import annotations

import math

import numpy as np
import pytest

from mcenroebot.aim import (
    AimController,
    Position3D,
    ServoAngles,
    TurretGeometry,
)

# --------------------------------------------------------------------------- #
# Position3D
# --------------------------------------------------------------------------- #


class TestPosition3D:
    def test_horizontal_distance_uses_xy_only(self) -> None:
        p = Position3D(3.0, 4.0, 99.0)
        assert p.horizontal_distance == pytest.approx(5.0)

    def test_magnitude_uses_all_three_components(self) -> None:
        p = Position3D(1.0, 2.0, 2.0)
        # sqrt(1 + 4 + 4) = 3
        assert p.magnitude == pytest.approx(3.0)

    def test_as_array_returns_length_three_float_array(self) -> None:
        p = Position3D(1.0, -2.0, 3.5)
        arr = p.as_array()
        assert isinstance(arr, np.ndarray)
        assert arr.shape == (3,)
        assert arr.dtype == float
        np.testing.assert_allclose(arr, [1.0, -2.0, 3.5])

    def test_is_frozen(self) -> None:
        p = Position3D(0.0, 0.0, 0.0)
        with pytest.raises(Exception):
            p.x = 1.0  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# ServoAngles
# --------------------------------------------------------------------------- #


class TestServoAngles:
    def test_in_range_values_are_accepted(self) -> None:
        a = ServoAngles(yaw_deg=45.0, pitch_deg=120.0)
        assert a.yaw_deg == 45.0
        assert a.pitch_deg == 120.0

    def test_boundary_values_are_accepted(self) -> None:
        ServoAngles(yaw_deg=0.0, pitch_deg=0.0)
        ServoAngles(yaw_deg=180.0, pitch_deg=180.0)

    @pytest.mark.parametrize(
        "yaw,pitch",
        [
            (-0.1, 90.0),
            (180.1, 90.0),
            (90.0, -1.0),
            (90.0, 200.0),
        ],
    )
    def test_out_of_range_raises(self, yaw: float, pitch: float) -> None:
        with pytest.raises(ValueError, match=r"out of MG996R servo range"):
            ServoAngles(yaw_deg=yaw, pitch_deg=pitch)


# --------------------------------------------------------------------------- #
# TurretGeometry
# --------------------------------------------------------------------------- #


class TestTurretGeometry:
    def test_defaults_match_v2_design(self) -> None:
        g = TurretGeometry()
        assert g.arm_length_m == pytest.approx(0.20)
        assert g.yaw_neutral_deg == pytest.approx(90.0)
        assert g.pitch_neutral_deg == pytest.approx(90.0)

    def test_can_override_defaults(self) -> None:
        g = TurretGeometry(arm_length_m=0.25, yaw_neutral_deg=85.0)
        assert g.arm_length_m == pytest.approx(0.25)
        assert g.yaw_neutral_deg == pytest.approx(85.0)
        # Unspecified field falls back to default.
        assert g.pitch_neutral_deg == pytest.approx(90.0)


# --------------------------------------------------------------------------- #
# AimController — reachability
# --------------------------------------------------------------------------- #


class TestAimControllerReachability:
    def setup_method(self) -> None:
        self.ctrl = AimController()  # default geometry, arm=0.20m

    def test_target_inside_arm_is_reachable(self) -> None:
        assert self.ctrl.is_reachable(Position3D(0.10, 0.0, 0.0))

    def test_target_exactly_at_arm_length_is_reachable(self) -> None:
        # On the boundary should be reachable (<= comparison).
        assert self.ctrl.is_reachable(Position3D(0.20, 0.0, 0.0))

    def test_target_beyond_arm_length_is_unreachable(self) -> None:
        assert not self.ctrl.is_reachable(Position3D(0.21, 0.0, 0.0))

    def test_unreachable_compute_returns_none(self) -> None:
        assert self.ctrl.compute(Position3D(0.5, 0.5, 0.5)) is None


# --------------------------------------------------------------------------- #
# AimController — angle computation
# --------------------------------------------------------------------------- #


class TestAimControllerCompute:
    def setup_method(self) -> None:
        self.ctrl = AimController()

    def test_directly_forward_gives_neutral_pose(self) -> None:
        angles = self.ctrl.compute(Position3D(0.18, 0.0, 0.0))
        assert angles is not None
        assert angles.yaw_deg == pytest.approx(90.0)
        assert angles.pitch_deg == pytest.approx(90.0)

    def test_ball_to_the_left_yaws_left(self) -> None:
        # +Y is left, so atan2(+y, +x) > 0 -> yaw > 90.
        angles = self.ctrl.compute(Position3D(0.10, 0.10, 0.0))
        assert angles is not None
        assert angles.yaw_deg > 90.0
        assert angles.pitch_deg == pytest.approx(90.0)

    def test_ball_to_the_right_yaws_right(self) -> None:
        angles = self.ctrl.compute(Position3D(0.10, -0.10, 0.0))
        assert angles is not None
        assert angles.yaw_deg < 90.0
        assert angles.pitch_deg == pytest.approx(90.0)

    def test_ball_high_pitches_up(self) -> None:
        angles = self.ctrl.compute(Position3D(0.10, 0.0, 0.10))
        assert angles is not None
        assert angles.pitch_deg > 90.0

    def test_ball_low_pitches_down(self) -> None:
        angles = self.ctrl.compute(Position3D(0.10, 0.0, -0.10))
        assert angles is not None
        assert angles.pitch_deg < 90.0

    @pytest.mark.parametrize(
        "target,expected_yaw,expected_pitch",
        [
            # Forward at paddle height -> neutral pose.
            (Position3D(0.18, 0.0, 0.0), 90.0, 90.0),
            # 45° left, level: yaw = 90 + 45 = 135.
            (
                Position3D(0.10, 0.10, 0.0),
                90.0 + math.degrees(math.atan2(0.10, 0.10)),
                90.0,
            ),
            # 45° right, level: yaw = 90 - 45 = 45.
            (
                Position3D(0.10, -0.10, 0.0),
                90.0 + math.degrees(math.atan2(-0.10, 0.10)),
                90.0,
            ),
            # 45° up, no yaw: pitch = 135.
            (
                Position3D(0.10, 0.0, 0.10),
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
        angles = self.ctrl.compute(Position3D(0.05, 0.05, 0.05))
        assert isinstance(angles, ServoAngles)

    def test_yaw_clamped_to_servo_range_for_target_behind_robot(self) -> None:
        # A target with negative x ("behind") would compute yaw outside
        # [0, 180]. The controller must clamp; we verify the result is
        # always a valid ServoAngles.
        angles = self.ctrl.compute(Position3D(-0.05, 0.05, 0.0))
        assert angles is not None
        assert 0.0 <= angles.yaw_deg <= 180.0
        assert 0.0 <= angles.pitch_deg <= 180.0

    def test_zero_target_is_reachable_and_neutral_ish(self) -> None:
        # The (0, 0, 0) point is "at the origin" — a degenerate case but
        # the function should still return a valid ServoAngles.
        angles = self.ctrl.compute(Position3D(0.0, 0.0, 0.0))
        assert angles is not None
        # yaw = atan2(0, 0) = 0 by convention -> 90° + 0 = 90°.
        # pitch = atan2(0, 0) = 0 -> 90°.
        assert angles.yaw_deg == pytest.approx(90.0)
        assert angles.pitch_deg == pytest.approx(90.0)


# --------------------------------------------------------------------------- #
# AimController — custom geometry
# --------------------------------------------------------------------------- #


class TestAimControllerCustomGeometry:
    def test_smaller_arm_length_shrinks_reachable_set(self) -> None:
        small_arm = AimController(TurretGeometry(arm_length_m=0.10))
        # 15 cm forward is inside default reach but outside this one.
        target = Position3D(0.15, 0.0, 0.0)
        assert not small_arm.is_reachable(target)
        assert small_arm.compute(target) is None

    def test_neutral_offsets_shift_output(self) -> None:
        # If we change yaw_neutral from 90 to 60, a forward target should
        # report yaw=60 instead of yaw=90.
        custom = AimController(
            TurretGeometry(arm_length_m=0.20, yaw_neutral_deg=60.0, pitch_neutral_deg=70.0)
        )
        angles = custom.compute(Position3D(0.18, 0.0, 0.0))
        assert angles is not None
        assert angles.yaw_deg == pytest.approx(60.0)
        assert angles.pitch_deg == pytest.approx(70.0)


# --------------------------------------------------------------------------- #
# Immutability — both value objects should be frozen so they can be hashed
# and safely shared between threads/coroutines.
# --------------------------------------------------------------------------- #


class TestImmutability:
    def test_servoangles_is_frozen(self) -> None:
        a = ServoAngles(yaw_deg=10.0, pitch_deg=20.0)
        with pytest.raises(Exception):
            a.yaw_deg = 99.0  # type: ignore[misc]

    def test_turretgeometry_is_frozen(self) -> None:
        g = TurretGeometry()
        with pytest.raises(Exception):
            g.arm_length_m = 0.5  # type: ignore[misc]

    def test_position3d_is_hashable(self) -> None:
        # Frozen dataclasses become hashable, which is useful for caching
        # aim solutions keyed on (position, geometry).
        p = Position3D(1.0, 2.0, 3.0)
        assert hash(p) == hash(Position3D(1.0, 2.0, 3.0))


# --------------------------------------------------------------------------- #
# Demo — covers the _demo() function so coverage stays high. The demo is a
# CLI sanity-check, but exercising it catches regressions in the print path
# and in case-list construction.
# --------------------------------------------------------------------------- #


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
