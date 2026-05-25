"""Tests for frozen pydantic value objects in mcenroebot.ball.value_objects."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mcenroebot.aim import Position3D
from mcenroebot.ball import BallObservation, BallState, PixelObservation, StrikePrediction


# ---------------------------------------------------------------------------
# 1. Construction — each model constructs and reads back its fields.
# ---------------------------------------------------------------------------


class TestBallObservationConstruction:
    def test_fields_readable(self) -> None:
        obs = BallObservation(t=1.5, x=0.3, y=-0.1, z=0.8)
        assert obs.t == pytest.approx(1.5)
        assert obs.x == pytest.approx(0.3)
        assert obs.y == pytest.approx(-0.1)
        assert obs.z == pytest.approx(0.8)

    def test_negative_t_accepted(self) -> None:
        # BallObservation does NOT validate t — a FakeClock starting negative
        # is a legitimate use case.
        obs = BallObservation(t=-5.0, x=0.0, y=0.0, z=0.0)
        assert obs.t == pytest.approx(-5.0)

    def test_zero_position_accepted(self) -> None:
        obs = BallObservation(t=0.0, x=0.0, y=0.0, z=0.0)
        assert obs.x == pytest.approx(0.0)


class TestBallStateConstruction:
    def test_fields_readable(self) -> None:
        pos = Position3D(x=1.0, y=2.0, z=3.0)
        vel = Position3D(x=0.5, y=-0.2, z=0.1)
        state = BallState(t=0.25, position=pos, velocity=vel)
        assert state.t == pytest.approx(0.25)
        assert state.position.x == pytest.approx(1.0)
        assert state.velocity.y == pytest.approx(-0.2)


class TestStrikePredictionConstruction:
    def test_fields_readable(self) -> None:
        point = Position3D(x=1.5, y=0.0, z=0.3)
        pred = StrikePrediction(impact_point=point, impact_time=0.8, confidence=0.9)
        assert pred.impact_point.x == pytest.approx(1.5)
        assert pred.impact_time == pytest.approx(0.8)
        assert pred.confidence == pytest.approx(0.9)

    def test_boundary_confidence_accepted(self) -> None:
        point = Position3D(x=0.0, y=0.0, z=0.0)
        StrikePrediction(impact_point=point, impact_time=0.0, confidence=0.0)
        StrikePrediction(impact_point=point, impact_time=0.0, confidence=1.0)


class TestPixelObservationConstruction:
    def test_fields_readable(self) -> None:
        obs = PixelObservation(t=0.1, u_px=320.0, v_px=240.0, radius_px=12.0)
        assert obs.t == pytest.approx(0.1)
        assert obs.u_px == pytest.approx(320.0)
        assert obs.v_px == pytest.approx(240.0)
        assert obs.radius_px == pytest.approx(12.0)


# ---------------------------------------------------------------------------
# 2. Frozen — assigning to a field raises ValidationError.
# ---------------------------------------------------------------------------


class TestFrozen:
    def test_ball_observation_is_frozen(self) -> None:
        obs = BallObservation(t=0.0, x=0.0, y=0.0, z=0.0)
        with pytest.raises(ValidationError):
            obs.x = 1.0  # type: ignore[misc]

    def test_ball_state_is_frozen(self) -> None:
        state = BallState(
            t=0.0,
            position=Position3D(x=0.0, y=0.0, z=0.0),
            velocity=Position3D(x=0.0, y=0.0, z=0.0),
        )
        with pytest.raises(ValidationError):
            state.t = 1.0  # type: ignore[misc]

    def test_strike_prediction_is_frozen(self) -> None:
        pred = StrikePrediction(
            impact_point=Position3D(x=0.0, y=0.0, z=0.0),
            impact_time=0.0,
            confidence=0.5,
        )
        with pytest.raises(ValidationError):
            pred.confidence = 0.9  # type: ignore[misc]

    def test_pixel_observation_is_frozen(self) -> None:
        obs = PixelObservation(t=0.0, u_px=0.0, v_px=0.0, radius_px=1.0)
        with pytest.raises(ValidationError):
            obs.radius_px = 5.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 3. Hashability — frozen pydantic models are hashable.
# ---------------------------------------------------------------------------


class TestHashability:
    def test_ball_observation_is_hashable(self) -> None:
        obs = BallObservation(t=1.0, x=0.5, y=-0.2, z=1.1)
        assert hash(obs) == hash(BallObservation(t=1.0, x=0.5, y=-0.2, z=1.1))

    def test_ball_state_is_hashable(self) -> None:
        pos = Position3D(x=1.0, y=0.0, z=0.0)
        vel = Position3D(x=0.0, y=0.0, z=0.0)
        state = BallState(t=0.0, position=pos, velocity=vel)
        assert isinstance(hash(state), int)

    def test_strike_prediction_is_hashable(self) -> None:
        pred = StrikePrediction(
            impact_point=Position3D(x=1.0, y=0.0, z=0.0),
            impact_time=0.5,
            confidence=0.8,
        )
        assert isinstance(hash(pred), int)

    def test_pixel_observation_is_hashable(self) -> None:
        obs = PixelObservation(t=0.0, u_px=320.0, v_px=240.0, radius_px=10.0)
        assert isinstance(hash(obs), int)


# ---------------------------------------------------------------------------
# 4. confidence bounds — out-of-range values raise ValidationError.
# ---------------------------------------------------------------------------


class TestConfidenceBounds:
    @pytest.mark.parametrize("bad_confidence", [-0.01, -1.0, 1.01, 2.0])
    def test_out_of_range_confidence_raises(self, bad_confidence: float) -> None:
        with pytest.raises(ValidationError):
            StrikePrediction(
                impact_point=Position3D(x=0.0, y=0.0, z=0.0),
                impact_time=0.0,
                confidence=bad_confidence,
            )

    def test_confidence_zero_accepted(self) -> None:
        pred = StrikePrediction(
            impact_point=Position3D(x=0.0, y=0.0, z=0.0),
            impact_time=0.0,
            confidence=0.0,
        )
        assert pred.confidence == pytest.approx(0.0)

    def test_confidence_one_accepted(self) -> None:
        pred = StrikePrediction(
            impact_point=Position3D(x=0.0, y=0.0, z=0.0),
            impact_time=0.0,
            confidence=1.0,
        )
        assert pred.confidence == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# 5. radius_px validator — zero and negative rejected; positive accepted.
# ---------------------------------------------------------------------------


class TestRadiusPxValidator:
    @pytest.mark.parametrize("bad_radius", [0.0, -0.1, -10.0, -1e-9])
    def test_non_positive_radius_raises(self, bad_radius: float) -> None:
        with pytest.raises(ValidationError, match=r"radius_px must be strictly positive"):
            PixelObservation(t=0.0, u_px=0.0, v_px=0.0, radius_px=bad_radius)

    @pytest.mark.parametrize("good_radius", [0.001, 1.0, 12.0, 999.0])
    def test_positive_radius_accepted(self, good_radius: float) -> None:
        obs = PixelObservation(t=0.0, u_px=0.0, v_px=0.0, radius_px=good_radius)
        assert obs.radius_px == pytest.approx(good_radius)


# ---------------------------------------------------------------------------
# 6. Position3D reuse — BallState and StrikePrediction use the same type.
# ---------------------------------------------------------------------------


class TestPosition3DReuse:
    def test_ball_state_accepts_position3d_instances(self) -> None:
        pos = Position3D(x=1.0, y=2.0, z=3.0)
        vel = Position3D(x=0.1, y=0.2, z=0.3)
        state = BallState(t=0.0, position=pos, velocity=vel)
        # The returned fields should be the same type, not a shadow copy.
        assert isinstance(state.position, Position3D)
        assert isinstance(state.velocity, Position3D)

    def test_strike_prediction_accepts_position3d_instance(self) -> None:
        point = Position3D(x=0.5, y=0.5, z=0.5)
        pred = StrikePrediction(impact_point=point, impact_time=1.0, confidence=0.7)
        assert isinstance(pred.impact_point, Position3D)

    def test_position3d_is_not_redefined_in_ball_package(self) -> None:
        # Import Position3D from both packages and confirm they are the same class.
        from mcenroebot.aim import Position3D as AimPosition3D
        from mcenroebot.ball.value_objects import BallState as _BallState

        # The annotation on BallState.position is the aim Position3D.
        pos = AimPosition3D(x=1.0, y=0.0, z=0.0)
        state = _BallState(
            t=0.0,
            position=pos,
            velocity=AimPosition3D(x=0.0, y=0.0, z=0.0),
        )
        assert type(state.position) is AimPosition3D
