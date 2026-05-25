"""Tests for the frozen pydantic value objects in mcenroebot.aim.value_objects."""

from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from mcenroebot.aim import Position3D, ServoAngles, TurretGeometry


class TestPosition3D:
    def test_horizontal_distance_uses_xy_only(self) -> None:
        p = Position3D(x=3.0, y=4.0, z=99.0)
        assert p.horizontal_distance == pytest.approx(5.0)

    def test_magnitude_uses_all_three_components(self) -> None:
        p = Position3D(x=1.0, y=2.0, z=2.0)
        # sqrt(1 + 4 + 4) = 3
        assert p.magnitude == pytest.approx(3.0)

    def test_as_array_returns_length_three_float_array(self) -> None:
        p = Position3D(x=1.0, y=-2.0, z=3.5)
        arr = p.as_array()
        assert isinstance(arr, np.ndarray)
        assert arr.shape == (3,)
        assert arr.dtype == float
        np.testing.assert_allclose(arr, [1.0, -2.0, 3.5])

    def test_is_frozen(self) -> None:
        p = Position3D(x=0.0, y=0.0, z=0.0)
        with pytest.raises(ValidationError):
            p.x = 1.0  # type: ignore[misc]


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
        # Pydantic wraps the underlying ValueError; the original message is
        # preserved inside ValidationError's str repr, so the regex still
        # finds it.
        with pytest.raises(ValidationError, match=r"out of MG996R servo range"):
            ServoAngles(yaw_deg=yaw, pitch_deg=pitch)


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


class TestImmutability:
    def test_servoangles_is_frozen(self) -> None:
        a = ServoAngles(yaw_deg=10.0, pitch_deg=20.0)
        with pytest.raises(ValidationError):
            a.yaw_deg = 99.0  # type: ignore[misc]

    def test_turretgeometry_is_frozen(self) -> None:
        g = TurretGeometry()
        with pytest.raises(ValidationError):
            g.arm_length_m = 0.5  # type: ignore[misc]

    def test_position3d_is_hashable(self) -> None:
        # Frozen pydantic models are hashable, which is useful for caching
        # aim solutions keyed on (position, geometry).
        p = Position3D(x=1.0, y=2.0, z=3.0)
        assert hash(p) == hash(Position3D(x=1.0, y=2.0, z=3.0))
