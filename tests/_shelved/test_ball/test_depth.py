"""Tests for depth estimators in mcenroebot._shelved.ball.depth."""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from mcenroebot._shelved.ball import (
    BallRadiusDepthEstimator,
    DepthEstimator,
    RealSenseDepthEstimator,
    StereoDepthEstimator,
)
from mcenroebot._shelved.ball.value_objects import BallObservation, PixelObservation
from mcenroebot.camera import CameraIntrinsics


# ---------------------------------------------------------------------------
# Shared helpers.
# ---------------------------------------------------------------------------


def _make_cam(
    *,
    fx_px: float = 600.0,
    fy_px: float = 600.0,
    cx_px: float = 320.0,
    cy_px: float = 240.0,
    image_width: int = 640,
    image_height: int = 480,
) -> CameraIntrinsics:
    return CameraIntrinsics(
        fx_px=fx_px,
        fy_px=fy_px,
        cx_px=cx_px,
        cy_px=cy_px,
        image_width=image_width,
        image_height=image_height,
    )


# ---------------------------------------------------------------------------
# 1. Round-trip known geometry — optical axis, depth=1.0 m.
# ---------------------------------------------------------------------------


class TestRoundTripKnownGeometry:
    def test_on_axis_depth_one_metre(self) -> None:
        """
        Given fx=fy=600, ball at 1.0 m on axis, apparent radius = 600*0.020/1.0 = 12.0 px.
        Returned BallObservation should be (0, 0, 1.0) within float tolerance.
        """
        cam = _make_cam()
        estimator = BallRadiusDepthEstimator(intrinsics=cam, ball_radius_m=0.020)
        obs = PixelObservation(t=0.5, u_px=320.0, v_px=240.0, radius_px=12.0)
        result = estimator.estimate(obs)

        assert result.t == pytest.approx(0.5)
        assert result.x == pytest.approx(0.0, abs=1e-6)
        assert result.y == pytest.approx(0.0, abs=1e-6)
        assert result.z == pytest.approx(1.0, abs=1e-6)

    def test_timestamp_is_propagated(self) -> None:
        cam = _make_cam()
        estimator = BallRadiusDepthEstimator(intrinsics=cam)
        obs = PixelObservation(t=3.14, u_px=320.0, v_px=240.0, radius_px=12.0)
        result = estimator.estimate(obs)
        assert result.t == pytest.approx(3.14)


# ---------------------------------------------------------------------------
# 2. Off-axis depth — magnitude equals depth.
# ---------------------------------------------------------------------------


class TestOffAxisDepth:
    def test_magnitude_equals_depth(self) -> None:
        """
        The result is depth * unit_ray, so |position| = depth regardless of direction.
        """
        cam = _make_cam()
        estimator = BallRadiusDepthEstimator(intrinsics=cam)
        obs = PixelObservation(t=0.0, u_px=400.0, v_px=300.0, radius_px=12.0)
        result = estimator.estimate(obs)

        # Expected depth: (0.020 * 600) / 12.0 = 1.0 m
        expected_depth = (0.020 * 600.0) / 12.0
        magnitude = math.sqrt(result.x**2 + result.y**2 + result.z**2)
        assert magnitude == pytest.approx(expected_depth, rel=1e-6)

    def test_another_off_axis_point(self) -> None:
        cam = _make_cam()
        estimator = BallRadiusDepthEstimator(intrinsics=cam, ball_radius_m=0.020)
        obs = PixelObservation(t=0.0, u_px=160.0, v_px=120.0, radius_px=6.0)
        result = estimator.estimate(obs)

        # depth = 600 * 0.020 / 6.0 = 2.0
        expected_depth = (0.020 * 600.0) / 6.0
        magnitude = math.sqrt(result.x**2 + result.y**2 + result.z**2)
        assert magnitude == pytest.approx(expected_depth, rel=1e-6)


# ---------------------------------------------------------------------------
# 3. Depth scales with 1/radius — doubling radius halves depth.
# ---------------------------------------------------------------------------


class TestDepthScaling:
    @pytest.mark.parametrize(
        "radius_px,expected_depth",
        [
            (6.0, 2.0),   # 600 * 0.020 / 6 = 2.0
            (12.0, 1.0),  # 600 * 0.020 / 12 = 1.0
            (24.0, 0.5),  # 600 * 0.020 / 24 = 0.5
            (4.0, 3.0),   # 600 * 0.020 / 4  = 3.0
        ],
    )
    def test_depth_inversely_proportional_to_radius(
        self, radius_px: float, expected_depth: float
    ) -> None:
        cam = _make_cam()
        estimator = BallRadiusDepthEstimator(intrinsics=cam, ball_radius_m=0.020)
        # On-axis observation so depth == z-component directly.
        obs = PixelObservation(t=0.0, u_px=320.0, v_px=240.0, radius_px=radius_px)
        result = estimator.estimate(obs)
        assert result.z == pytest.approx(expected_depth, rel=1e-6)

    def test_doubling_radius_halves_depth(self) -> None:
        cam = _make_cam()
        estimator = BallRadiusDepthEstimator(intrinsics=cam)
        obs1 = PixelObservation(t=0.0, u_px=320.0, v_px=240.0, radius_px=10.0)
        obs2 = PixelObservation(t=0.0, u_px=320.0, v_px=240.0, radius_px=20.0)
        r1 = estimator.estimate(obs1)
        r2 = estimator.estimate(obs2)
        assert r1.z == pytest.approx(2.0 * r2.z, rel=1e-9)


# ---------------------------------------------------------------------------
# 4. ball_radius_m parameter is respected — larger ball → larger depth.
# ---------------------------------------------------------------------------


class TestBallRadiusParameter:
    def test_larger_physical_ball_gives_larger_depth(self) -> None:
        cam = _make_cam()
        small_ball = BallRadiusDepthEstimator(intrinsics=cam, ball_radius_m=0.020)
        large_ball = BallRadiusDepthEstimator(intrinsics=cam, ball_radius_m=0.040)
        obs = PixelObservation(t=0.0, u_px=320.0, v_px=240.0, radius_px=12.0)

        result_small = small_ball.estimate(obs)
        result_large = large_ball.estimate(obs)

        # Larger physical radius at the same pixel size → twice the depth.
        assert result_large.z == pytest.approx(2.0 * result_small.z, rel=1e-9)

    def test_depth_proportional_to_ball_radius_m(self) -> None:
        cam = _make_cam()
        obs = PixelObservation(t=0.0, u_px=320.0, v_px=240.0, radius_px=12.0)
        for radius_m in [0.010, 0.020, 0.030, 0.050]:
            estimator = BallRadiusDepthEstimator(intrinsics=cam, ball_radius_m=radius_m)
            result = estimator.estimate(obs)
            expected_depth = (radius_m * 600.0) / 12.0
            assert result.z == pytest.approx(expected_depth, rel=1e-9)


# ---------------------------------------------------------------------------
# 5. ball_radius_m validation — zero and negative raise ValueError.
# ---------------------------------------------------------------------------


class TestBallRadiusMValidation:
    @pytest.mark.parametrize("bad_radius", [0.0, -0.01, -1.0])
    def test_non_positive_ball_radius_raises(self, bad_radius: float) -> None:
        cam = _make_cam()
        with pytest.raises(ValueError, match=r"ball_radius_m must be strictly positive"):
            BallRadiusDepthEstimator(intrinsics=cam, ball_radius_m=bad_radius)


# ---------------------------------------------------------------------------
# 6. DepthEstimator Protocol — BallRadiusDepthEstimator satisfies it.
# ---------------------------------------------------------------------------


class TestDepthEstimatorProtocol:
    def test_isinstance_check(self) -> None:
        """
        DepthEstimator is @runtime_checkable, so isinstance() works.
        BallRadiusDepthEstimator satisfies the structural Protocol.
        """
        cam = _make_cam()
        estimator = BallRadiusDepthEstimator(intrinsics=cam)
        assert isinstance(estimator, DepthEstimator)

    def test_typed_variable_assignment(self) -> None:
        """Static and runtime: assign to a DepthEstimator-typed variable."""
        cam = _make_cam()
        de: DepthEstimator = BallRadiusDepthEstimator(intrinsics=cam)
        obs = PixelObservation(t=0.0, u_px=320.0, v_px=240.0, radius_px=12.0)
        result = de.estimate(obs)
        assert isinstance(result, BallObservation)


# ---------------------------------------------------------------------------
# 7. Stubs raise NotImplementedError on construction.
# ---------------------------------------------------------------------------


class TestStubsRaise:
    def test_stereo_raises_on_construction(self) -> None:
        with pytest.raises(NotImplementedError):
            StereoDepthEstimator()

    def test_realsense_raises_on_construction(self) -> None:
        with pytest.raises(NotImplementedError):
            RealSenseDepthEstimator()


# ---------------------------------------------------------------------------
# 8. Negative radius_px cannot reach estimate — PixelObservation itself raises.
# ---------------------------------------------------------------------------


class TestNegativeRadiusBlockedAtObservation:
    @pytest.mark.parametrize("bad_radius", [0.0, -1.0, -0.001])
    def test_bad_radius_raises_at_observation_construction(self, bad_radius: float) -> None:
        """PixelObservation validation rejects non-positive radius before estimate is called."""
        with pytest.raises(ValidationError, match=r"radius_px must be strictly positive"):
            PixelObservation(t=0.0, u_px=320.0, v_px=240.0, radius_px=bad_radius)


# ---------------------------------------------------------------------------
# 9. Demo smoke test.
# ---------------------------------------------------------------------------


class TestDemo:
    def test_demo_runs_without_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        from mcenroebot._shelved.ball import _demo

        _demo()
        captured = capsys.readouterr()
        assert "On optical axis" in captured.out
        assert "|p|=" in captured.out
