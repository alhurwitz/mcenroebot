"""Tests for TrajectoryPredictor — ballistic fit, strike prediction, and confidence."""

from __future__ import annotations

import math

import numpy as np
import numpy.testing as npt
import pytest

from mcenroebot.aim import Position3D
from mcenroebot.ball import BallObservation, BallState, StrikePrediction
from mcenroebot.predictor import TrajectoryPredictor

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

G = 9.81  # default gravity, m/s²


def _make_obs(
    t: float,
    x0: float,
    y0: float,
    z0: float,
    vx: float,
    vy: float,
    vz: float,
    g: float = G,
    noise: tuple[float, float, float] | None = None,
) -> BallObservation:
    """Return a BallObservation on the analytical ballistic trajectory at time ``t``."""
    x = x0 + vx * t
    y = y0 + vy * t
    z = z0 + vz * t - 0.5 * g * t * t
    if noise is not None:
        x += noise[0]
        y += noise[1]
        z += noise[2]
    return BallObservation(t=t, x=x, y=y, z=z)


def _feed(
    predictor: TrajectoryPredictor,
    x0: float,
    y0: float,
    z0: float,
    vx: float,
    vy: float,
    vz: float,
    times: list[float],
    g: float = G,
    rng: np.random.Generator | None = None,
    noise_std: float = 0.0,
) -> None:
    """Feed a sequence of observations into *predictor*."""
    for t in times:
        noisevec: tuple[float, float, float] | None = None
        if rng is not None and noise_std > 0.0:
            nv = rng.normal(0.0, noise_std, size=3)
            noisevec = (float(nv[0]), float(nv[1]), float(nv[2]))
        predictor.add(_make_obs(t, x0, y0, z0, vx, vy, vz, g=g, noise=noisevec))


# ---------------------------------------------------------------------------
# 1. Synthetic ballistic recovery
# ---------------------------------------------------------------------------


class TestSyntheticBallisticRecovery:
    """Feed a clean synthetic trajectory and verify the fit recovers the parameters."""

    X0, Y0, Z0 = 0.5, 0.1, 1.2
    VX, VY, VZ = 3.0, -0.5, 2.0
    TIMES = [i * 0.02 for i in range(11)]  # 0.0 … 0.20 s in steps of 20 ms

    def test_position_matches_last_sample(self) -> None:
        pred = TrajectoryPredictor()
        _feed(pred, self.X0, self.Y0, self.Z0, self.VX, self.VY, self.VZ, self.TIMES)
        state = pred.current_state()
        assert state is not None

        t_last = self.TIMES[-1]
        expected_x = self.X0 + self.VX * t_last
        expected_y = self.Y0 + self.VY * t_last
        expected_z = self.Z0 + self.VZ * t_last - 0.5 * G * t_last**2

        npt.assert_allclose(state.position.x, expected_x, atol=1e-3)
        npt.assert_allclose(state.position.y, expected_y, atol=1e-3)
        npt.assert_allclose(state.position.z, expected_z, atol=1e-3)

    def test_velocity_recovers_true_vx_vy_vz(self) -> None:
        """The model's vz is the instantaneous z-velocity at t_ref (not at t=0),
        because the ballistic model is parameterised around the most-recent
        observation: z(t) = z0 + vz*(t−t_ref) − 0.5*g*(t−t_ref)².
        """
        pred = TrajectoryPredictor()
        _feed(pred, self.X0, self.Y0, self.Z0, self.VX, self.VY, self.VZ, self.TIMES)
        state = pred.current_state()
        assert state is not None

        t_ref = self.TIMES[-1]
        # vz at t_ref: the time-derivative of z = VZ - g*t_ref.
        vz_at_tref = self.VZ - G * t_ref

        npt.assert_allclose(state.velocity.x, self.VX, atol=1e-2)
        npt.assert_allclose(state.velocity.y, self.VY, atol=1e-2)
        npt.assert_allclose(state.velocity.z, vz_at_tref, atol=1e-2)

    def test_state_t_equals_last_obs_time(self) -> None:
        pred = TrajectoryPredictor()
        _feed(pred, self.X0, self.Y0, self.Z0, self.VX, self.VY, self.VZ, self.TIMES)
        state = pred.current_state()
        assert state is not None
        assert state.t == pytest.approx(self.TIMES[-1])


# ---------------------------------------------------------------------------
# 2. predict_strike round-trip
# ---------------------------------------------------------------------------


class TestPredictStrikeRoundTrip:
    """Using a known trajectory, verify the predicted impact matches analytic truth."""

    X0, Y0, Z0 = 0.0, 0.2, 1.5
    VX, VY, VZ = 4.0, 0.3, 1.0
    TIMES = [i * 0.02 for i in range(11)]  # 0.0 … 0.20 s

    @pytest.mark.parametrize(
        "strike_plane_x",
        [
            # Both planes must be AHEAD of the ball's position at t_ref=0.2s.
            # At t_ref=0.2s: x_at_tref = X0 + VX*0.2 = 0 + 4*0.2 = 0.8 m.
            1.2,   # the ball reaches x=1.2 at t = 1.2/4.0 = 0.3 s (> t_ref)
            2.0,   # the ball reaches x=2.0 at t = 2.0/4.0 = 0.5 s (> t_ref)
        ],
    )
    def test_impact_point_and_time_match_analytic(self, strike_plane_x: float) -> None:
        pred = TrajectoryPredictor()
        _feed(pred, self.X0, self.Y0, self.Z0, self.VX, self.VY, self.VZ, self.TIMES)

        result = pred.predict_strike(strike_plane_x=strike_plane_x)
        assert result is not None

        # Analytic solution using absolute time from t=0:
        # x0 + vx * t_impact = strike_plane_x  =>  t_impact = strike_plane_x / vx
        t_impact_abs = (strike_plane_x - self.X0) / self.VX
        y_impact = self.Y0 + self.VY * t_impact_abs
        z_impact = self.Z0 + self.VZ * t_impact_abs - 0.5 * G * t_impact_abs**2

        npt.assert_allclose(result.impact_point.x, strike_plane_x, atol=1e-6)
        npt.assert_allclose(result.impact_point.y, y_impact, atol=5e-3)
        npt.assert_allclose(result.impact_point.z, z_impact, atol=5e-3)
        npt.assert_allclose(result.impact_time, t_impact_abs, atol=5e-3)

    def test_impact_x_equals_strike_plane(self) -> None:
        pred = TrajectoryPredictor()
        _feed(pred, self.X0, self.Y0, self.Z0, self.VX, self.VY, self.VZ, self.TIMES)
        result = pred.predict_strike(strike_plane_x=0.8)
        assert result is not None
        assert result.impact_point.x == pytest.approx(0.8, abs=1e-9)


# ---------------------------------------------------------------------------
# 3. min_observations gate
# ---------------------------------------------------------------------------


class TestMinObservationsGate:
    """current_state() and predict_strike() return None before min_observations."""

    @pytest.mark.parametrize("n_obs", [0, 1, 2])
    def test_current_state_none_below_min(self, n_obs: int) -> None:
        pred = TrajectoryPredictor(min_observations=3)
        for i in range(n_obs):
            pred.add(BallObservation(t=float(i) * 0.01, x=float(i), y=0.0, z=1.0))
        assert pred.current_state() is None

    @pytest.mark.parametrize("n_obs", [0, 1, 2])
    def test_predict_strike_none_below_min(self, n_obs: int) -> None:
        pred = TrajectoryPredictor(min_observations=3)
        for i in range(n_obs):
            pred.add(BallObservation(t=float(i) * 0.01, x=float(i), y=0.0, z=1.0))
        assert pred.predict_strike(strike_plane_x=5.0) is None

    def test_current_state_returns_after_min_reached(self) -> None:
        pred = TrajectoryPredictor(min_observations=3)
        for i in range(3):
            pred.add(BallObservation(t=float(i) * 0.01, x=float(i) * 0.1, y=0.0, z=1.0))
        assert pred.current_state() is not None


# ---------------------------------------------------------------------------
# 4. Moving-away detection
# ---------------------------------------------------------------------------


class TestMovingAway:
    """predict_strike() returns None when the ball is moving away from the plane."""

    def test_positive_vx_ball_behind_strike_plane_returns_none(self) -> None:
        # Ball at x ≈ 1.0, moving forward (+vx), but strike plane is at x=0.0
        # => ball has already passed the plane, Δt < 0 => None.
        pred = TrajectoryPredictor()
        times = [i * 0.02 for i in range(8)]
        _feed(pred, 0.5, 0.0, 1.0, 3.0, 0.0, 0.0, times)
        result = pred.predict_strike(strike_plane_x=0.0)
        assert result is None

    def test_negative_vx_ball_ahead_of_strike_plane_returns_none(self) -> None:
        # Ball at x ≈ -0.7, moving backward (vx < 0), strike plane is ahead at x=0.0
        # => Δt < 0 => None.
        pred = TrajectoryPredictor()
        times = [i * 0.02 for i in range(8)]
        _feed(pred, -0.5, 0.0, 1.0, -3.0, 0.0, 0.0, times)
        result = pred.predict_strike(strike_plane_x=0.0)
        assert result is None

    def test_positive_vx_ahead_of_strike_plane_returns_prediction(self) -> None:
        # Ball at x ≈ 0.1, moving forward, plane at x=1.0 => valid.
        pred = TrajectoryPredictor()
        times = [i * 0.02 for i in range(8)]
        _feed(pred, 0.0, 0.0, 1.0, 3.0, 0.0, 0.0, times)
        result = pred.predict_strike(strike_plane_x=1.0)
        assert result is not None


# ---------------------------------------------------------------------------
# 5. Stationary X velocity
# ---------------------------------------------------------------------------


class TestStationaryXVelocity:
    """vx ≈ 0 must return None gracefully, not NaN or a crash."""

    def test_near_zero_vx_returns_none(self) -> None:
        # vx = 1e-9 m/s is effectively zero horizontal motion — below the
        # _VX_MIN_MS threshold (1e-6 m/s).  The predictor treats this as
        # stationary in x and returns None rather than a prediction with an
        # astronomically large Δt.
        pred = TrajectoryPredictor()
        times = [i * 0.02 for i in range(8)]
        _feed(pred, 0.0, 0.0, 1.0, 1e-9, 0.0, 0.0, times)
        result = pred.predict_strike(strike_plane_x=1.0)
        assert result is None

    def test_exactly_zero_vx_returns_none(self) -> None:
        # Pure zero vx: the ball never reaches a different plane.
        pred = TrajectoryPredictor()
        # All observations at the same x position.
        for i in range(5):
            pred.add(BallObservation(t=float(i) * 0.02, x=0.5, y=float(i) * 0.01, z=1.0))
        result = pred.predict_strike(strike_plane_x=1.0)
        assert result is None

    def test_ball_at_strike_plane_zero_vx_returns_none(self) -> None:
        # Ball at x=1.0 with vx=0: not moving toward any plane.
        pred = TrajectoryPredictor()
        for i in range(5):
            pred.add(BallObservation(t=float(i) * 0.02, x=1.0, y=0.0, z=1.0))
        result = pred.predict_strike(strike_plane_x=1.0)
        # vx will be fit as ~0 => None.
        assert result is None


# ---------------------------------------------------------------------------
# 6. Confidence increases with observation count
# ---------------------------------------------------------------------------


class TestConfidenceVsObservationCount:
    """More clean observations → higher confidence."""

    X0, Y0, Z0 = 0.0, 0.0, 1.0
    VX, VY, VZ = 3.0, 0.2, 0.5

    def test_more_observations_give_higher_confidence(self) -> None:
        # 4 clean observations.
        pred_few = TrajectoryPredictor(buffer_size=16)
        _feed(pred_few, self.X0, self.Y0, self.Z0, self.VX, self.VY, self.VZ,
              [i * 0.02 for i in range(4)])
        result_few = pred_few.predict_strike(strike_plane_x=1.0)
        assert result_few is not None

        # 12 clean observations, same trajectory, same buffer_size.
        pred_many = TrajectoryPredictor(buffer_size=16)
        _feed(pred_many, self.X0, self.Y0, self.Z0, self.VX, self.VY, self.VZ,
              [i * 0.02 for i in range(12)])
        result_many = pred_many.predict_strike(strike_plane_x=1.0)
        assert result_many is not None

        assert result_many.confidence > result_few.confidence


# ---------------------------------------------------------------------------
# 7. Confidence decreases with noise
# ---------------------------------------------------------------------------


class TestConfidenceVsNoise:
    """Noisy observations → lower confidence than clean ones."""

    X0, Y0, Z0 = 0.0, 0.0, 1.0
    VX, VY, VZ = 3.0, 0.2, 0.5
    N = 12
    TIMES = [i * 0.02 for i in range(N)]

    def test_clean_observations_give_higher_confidence_than_noisy(self) -> None:
        rng = np.random.default_rng(seed=42)

        pred_clean = TrajectoryPredictor(buffer_size=16)
        _feed(pred_clean, self.X0, self.Y0, self.Z0, self.VX, self.VY, self.VZ, self.TIMES)
        result_clean = pred_clean.predict_strike(strike_plane_x=1.0)
        assert result_clean is not None

        pred_noisy = TrajectoryPredictor(buffer_size=16)
        _feed(pred_noisy, self.X0, self.Y0, self.Z0, self.VX, self.VY, self.VZ, self.TIMES,
              rng=rng, noise_std=0.005)
        result_noisy = pred_noisy.predict_strike(strike_plane_x=1.0)
        assert result_noisy is not None

        assert result_clean.confidence > result_noisy.confidence


# ---------------------------------------------------------------------------
# 8. Weighting biases toward recent observations
# ---------------------------------------------------------------------------


class TestWeightingBiasedTowardRecent:
    """The exponential weighting should pull the fit toward recent observations."""

    X0, Y0, Z0 = 0.0, 0.0, 1.0
    VX, VY, VZ = 3.0, 0.0, 0.0
    NOISE_STD = 0.05  # relatively large noise for clear separation

    def _true_position_at_t(self, t: float) -> tuple[float, float, float]:
        return (
            self.X0 + self.VX * t,
            self.Y0 + self.VY * t,
            self.Z0 + self.VZ * t - 0.5 * G * t * t,
        )

    def test_clean_recent_beats_clean_old(self) -> None:
        """Noisy old + clean recent is closer to truth than clean old + noisy recent."""
        rng = np.random.default_rng(seed=7)

        # Case A: 5 noisy OLD observations, then 5 clean RECENT ones.
        pred_a = TrajectoryPredictor(buffer_size=16, weight_halflife_s=0.05)
        for i in range(5):
            t = float(i) * 0.02  # old: 0.00 … 0.08 s
            nv = rng.normal(0.0, self.NOISE_STD, size=3)
            pred_a.add(_make_obs(
                t, self.X0, self.Y0, self.Z0, self.VX, self.VY, self.VZ,
                noise=(float(nv[0]), float(nv[1]), float(nv[2])),
            ))
        for i in range(5, 10):
            t = float(i) * 0.02  # recent: 0.10 … 0.18 s
            pred_a.add(_make_obs(t, self.X0, self.Y0, self.Z0, self.VX, self.VY, self.VZ))

        # Case B: 5 clean OLD observations, then 5 noisy RECENT ones.
        pred_b = TrajectoryPredictor(buffer_size=16, weight_halflife_s=0.05)
        for i in range(5):
            t = float(i) * 0.02
            pred_b.add(_make_obs(t, self.X0, self.Y0, self.Z0, self.VX, self.VY, self.VZ))
        for i in range(5, 10):
            t = float(i) * 0.02
            nv = rng.normal(0.0, self.NOISE_STD, size=3)
            pred_b.add(_make_obs(
                t, self.X0, self.Y0, self.Z0, self.VX, self.VY, self.VZ,
                noise=(float(nv[0]), float(nv[1]), float(nv[2])),
            ))

        state_a = pred_a.current_state()
        state_b = pred_b.current_state()
        assert state_a is not None
        assert state_b is not None

        # t_ref is the time of the last observation in each buffer.
        t_ref_a = 9 * 0.02  # = 0.18 s
        t_ref_b = 9 * 0.02
        true_x_a, true_y_a, true_z_a = self._true_position_at_t(t_ref_a)
        true_x_b, true_y_b, true_z_b = self._true_position_at_t(t_ref_b)

        err_a = math.sqrt(
            (state_a.position.x - true_x_a) ** 2
            + (state_a.position.y - true_y_a) ** 2
            + (state_a.position.z - true_z_a) ** 2
        )
        err_b = math.sqrt(
            (state_b.position.x - true_x_b) ** 2
            + (state_b.position.y - true_y_b) ** 2
            + (state_b.position.z - true_z_b) ** 2
        )

        # Case A (clean recent) should be closer to the true position than
        # Case B (noisy recent).
        assert err_a < err_b, (
            f"Expected err_a ({err_a:.4f}) < err_b ({err_b:.4f}) — "
            "weighting should favour clean recent observations"
        )


# ---------------------------------------------------------------------------
# 9. Buffer cap (FIFO eviction)
# ---------------------------------------------------------------------------


class TestBufferCap:
    """With buffer_size=4 and 10 observations fed, only the 4 most-recent are kept."""

    def test_len_respects_buffer_size(self) -> None:
        pred = TrajectoryPredictor(buffer_size=4)
        for i in range(10):
            pred.add(BallObservation(t=float(i) * 0.01, x=float(i) * 0.1, y=0.0, z=1.0))
        assert len(pred) == 4

    def test_fit_reflects_only_recent_observations(self) -> None:
        """The older 6 observations shift x in a completely different direction;
        only the last 4 (which have a clean ascending-x trajectory) should be fit.
        """
        # Older 6: x at very negative values (misleading)
        # Recent 4: x uniformly spaced from 0.0 to 0.06 m (vx ≈ 2 m/s)
        pred = TrajectoryPredictor(buffer_size=4, min_observations=3)

        # Misleading old observations far in the negative x direction
        for i in range(6):
            pred.add(BallObservation(t=float(i) * 0.01, x=-10.0 - float(i), y=0.0, z=1.0))

        # Clean recent observations: x starting near 0 and growing at ~2 m/s
        t_start = 0.10
        for i in range(4):
            t = t_start + float(i) * 0.01
            pred.add(BallObservation(t=t, x=float(i) * 0.02, y=0.0, z=1.0))

        state = pred.current_state()
        assert state is not None
        # The fit velocity should be positive and NOT dominated by the large
        # negative-x old observations.
        assert state.velocity.x > 0.0, (
            f"Expected positive vx (recent obs dominate), got {state.velocity.x!r}"
        )


# ---------------------------------------------------------------------------
# 10. Confidence bounds
# ---------------------------------------------------------------------------


class TestConfidenceBounds:
    """confidence is always in [0, 1]."""

    @pytest.mark.parametrize(
        "x0,y0,z0,vx,vy,vz,noise_std,n_obs,seed",
        [
            (0.0, 0.0, 1.0, 3.0, 0.1, 0.5, 0.0, 5, 0),
            (0.0, 0.0, 1.0, 3.0, 0.1, 0.5, 0.0, 16, 0),
            (0.0, 0.0, 1.0, 3.0, 0.1, 0.5, 0.001, 8, 1),
            (0.0, 0.0, 1.0, 3.0, 0.1, 0.5, 0.05, 12, 2),
            (0.0, 0.0, 1.0, 3.0, 0.1, 0.5, 0.1, 16, 3),
            (1.0, -0.5, 2.0, -2.0, 1.0, -1.0, 0.0, 7, 4),
            (1.0, -0.5, 2.0, -2.0, 1.0, -1.0, 0.02, 16, 5),
        ],
    )
    def test_confidence_in_unit_interval(
        self,
        x0: float,
        y0: float,
        z0: float,
        vx: float,
        vy: float,
        vz: float,
        noise_std: float,
        n_obs: int,
        seed: int,
    ) -> None:
        rng = np.random.default_rng(seed=seed) if noise_std > 0.0 else None
        pred = TrajectoryPredictor(buffer_size=16)
        _feed(pred, x0, y0, z0, vx, vy, vz,
              [i * 0.02 for i in range(n_obs)],
              rng=rng, noise_std=noise_std)

        # Try current_state confidence path (indirect)
        # and predict_strike confidence path.
        strike_plane = x0 + vx * (n_obs * 0.02 + 0.1)  # future plane
        if vx != 0.0:
            result = pred.predict_strike(strike_plane_x=strike_plane)
            if result is not None:
                assert 0.0 <= result.confidence <= 1.0


# ---------------------------------------------------------------------------
# 11. predict_strike returns StrikePrediction type
# ---------------------------------------------------------------------------


class TestReturnType:
    """predict_strike() returns a StrikePrediction instance, not a tuple or dict."""

    def test_predict_strike_returns_strike_prediction_instance(self) -> None:
        pred = TrajectoryPredictor()
        times = [i * 0.02 for i in range(8)]
        _feed(pred, 0.0, 0.0, 1.0, 3.0, 0.0, 0.0, times)
        result = pred.predict_strike(strike_plane_x=1.0)
        assert isinstance(result, StrikePrediction)

    def test_impact_point_is_position3d(self) -> None:
        pred = TrajectoryPredictor()
        times = [i * 0.02 for i in range(8)]
        _feed(pred, 0.0, 0.0, 1.0, 3.0, 0.0, 0.0, times)
        result = pred.predict_strike(strike_plane_x=1.0)
        assert result is not None
        assert isinstance(result.impact_point, Position3D)

    def test_current_state_returns_ball_state_instance(self) -> None:
        pred = TrajectoryPredictor()
        times = [i * 0.02 for i in range(8)]
        _feed(pred, 0.0, 0.0, 1.0, 3.0, 0.0, 0.0, times)
        state = pred.current_state()
        assert isinstance(state, BallState)


# ---------------------------------------------------------------------------
# 12. No mutation of past observations
# ---------------------------------------------------------------------------


class TestNoMutationOfPastObservations:
    """Calling add() does not mutate any previously returned BallState."""

    def test_add_does_not_mutate_previous_ball_state(self) -> None:
        pred = TrajectoryPredictor()
        times_first = [i * 0.02 for i in range(5)]
        _feed(pred, 0.0, 0.0, 1.0, 3.0, 0.0, 0.0, times_first)

        state_before = pred.current_state()
        assert state_before is not None

        # Record values before adding more observations.
        pos_x_before = state_before.position.x
        pos_y_before = state_before.position.y
        pos_z_before = state_before.position.z
        vel_x_before = state_before.velocity.x

        # Add more observations (new trajectory segment).
        _feed(pred, 0.0, 0.0, 1.0, 3.0, 0.0, 0.0, [0.10 + i * 0.02 for i in range(5)])

        # state_before must be unchanged (pydantic frozen model enforces this).
        assert state_before.position.x == pos_x_before
        assert state_before.position.y == pos_y_before
        assert state_before.position.z == pos_z_before
        assert state_before.velocity.x == vel_x_before

    def test_frozen_ball_state_rejects_attribute_mutation(self) -> None:
        """Direct attribute assignment on a BallState raises ValidationError."""
        from pydantic import ValidationError

        pred = TrajectoryPredictor()
        times = [i * 0.02 for i in range(5)]
        _feed(pred, 0.0, 0.0, 1.0, 3.0, 0.0, 0.0, times)
        state = pred.current_state()
        assert state is not None

        with pytest.raises(ValidationError):
            state.t = 999.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 13. Demo smoke test
# ---------------------------------------------------------------------------


class TestDemo:
    def test_demo_runs_without_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        from mcenroebot.predictor import _demo

        _demo()
        captured = capsys.readouterr()
        assert "TrajectoryPredictor demo" in captured.out

    def test_demo_prints_predict_strike_lines(self, capsys: pytest.CaptureFixture[str]) -> None:
        from mcenroebot.predictor import _demo

        _demo()
        captured = capsys.readouterr()
        assert "predict_strike" in captured.out


# ---------------------------------------------------------------------------
# 14. Ball exactly at strike plane (Δt == 0)
# ---------------------------------------------------------------------------


class TestBallAtStrikePlane:
    """A ball whose current x position equals strike_plane_x should return
    a valid prediction with Δt == 0 (impact is now)."""

    def test_ball_at_strike_plane_returns_prediction(self) -> None:
        # Set up a trajectory where x0 (after fit, at t_ref) matches strike_plane_x.
        # The ball starts at x=0 and moves at vx=3.0.
        # t_ref = 0.14 (last obs at index 7 * 0.02), so x0 at t_ref = 3.0 * 0.14 = 0.42.
        pred = TrajectoryPredictor()
        x0, vx = 0.0, 3.0
        times = [i * 0.02 for i in range(8)]  # t_ref = 0.14
        _feed(pred, x0, 0.0, 1.0, vx, 0.0, 0.0, times)

        t_ref = times[-1]  # 0.14
        strike_plane_x = x0 + vx * t_ref  # = 0.42 — exactly where the ball is

        result = pred.predict_strike(strike_plane_x=strike_plane_x)
        assert result is not None, "Ball at the plane should yield a valid prediction (Δt=0)"
        npt.assert_allclose(result.impact_time, t_ref, atol=1e-4)


# ---------------------------------------------------------------------------
# 15. __len__ introspection
# ---------------------------------------------------------------------------


class TestLen:
    def test_empty_predictor_has_len_zero(self) -> None:
        pred = TrajectoryPredictor()
        assert len(pred) == 0

    def test_len_grows_with_each_add(self) -> None:
        pred = TrajectoryPredictor(buffer_size=8)
        for i in range(5):
            pred.add(BallObservation(t=float(i) * 0.01, x=0.0, y=0.0, z=1.0))
            assert len(pred) == i + 1

    def test_len_caps_at_buffer_size(self) -> None:
        pred = TrajectoryPredictor(buffer_size=4)
        for i in range(10):
            pred.add(BallObservation(t=float(i) * 0.01, x=0.0, y=0.0, z=1.0))
        assert len(pred) == 4


# ---------------------------------------------------------------------------
# 16. Constructor argument validation
# ---------------------------------------------------------------------------


class TestConstructorValidation:
    """Invalid constructor arguments raise ValueError immediately."""

    def test_buffer_size_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="buffer_size"):
            TrajectoryPredictor(buffer_size=0)

    def test_gravity_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="gravity_mps2"):
            TrajectoryPredictor(gravity_mps2=0.0)

    def test_gravity_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="gravity_mps2"):
            TrajectoryPredictor(gravity_mps2=-1.0)

    def test_weight_halflife_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="weight_halflife_s"):
            TrajectoryPredictor(weight_halflife_s=0.0)

    def test_min_observations_one_raises(self) -> None:
        with pytest.raises(ValueError, match="min_observations"):
            TrajectoryPredictor(min_observations=1)
