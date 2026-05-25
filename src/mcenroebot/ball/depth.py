"""Depth estimators — map a pixel observation to a 3-D ball observation.

Layout
------
    DepthEstimator          — structural Protocol (runtime-checkable).
    BallRadiusDepthEstimator — monocular depth from apparent ball size.
    StereoDepthEstimator    — stub for future stereo depth.
    RealSenseDepthEstimator — stub for future RealSense depth.

Camera-frame vs robot-frame
---------------------------
    V1 simplification: the camera frame and the robot frame are treated as
    coincident (no extrinsic rotation/translation calibration yet). The depth
    estimator therefore returns coordinates directly in robot frame simply by
    using the camera-frame ray as-is.

    When a real extrinsic calibration is added (future task), the
    ``BallRadiusDepthEstimator`` should be extended to apply the
    camera-to-robot rotation and translation before constructing the
    ``BallObservation``. A ``# TODO: apply extrinsic transform`` note marks
    the site.

Stub behaviour
--------------
    ``StereoDepthEstimator`` and ``RealSenseDepthEstimator`` raise
    ``NotImplementedError`` in ``__init__``, so callers fail fast at
    construction time rather than at the first ``estimate()`` call.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from mcenroebot.ball.value_objects import BallObservation, PixelObservation
from mcenroebot.camera import CameraIntrinsics

__all__ = [
    "BallRadiusDepthEstimator",
    "DepthEstimator",
    "RealSenseDepthEstimator",
    "StereoDepthEstimator",
    "_demo",
]


@runtime_checkable
class DepthEstimator(Protocol):
    """Map a pixel observation to a 3-D ball observation in the robot frame.

    This is a structural Protocol decorated with ``@runtime_checkable``, so
    callers can use ``isinstance(obj, DepthEstimator)`` to check conformance
    at runtime in addition to static type checking.
    """

    def estimate(self, obs: PixelObservation) -> BallObservation:
        """Convert a pixel-space observation to a robot-frame observation."""
        ...


class BallRadiusDepthEstimator:
    """Monocular depth from apparent ball size.

    Physics
    -------
    A sphere of real radius ``R`` metres, at distance ``D`` metres along the
    optical axis, projects to a circle with apparent pixel radius::

        r_px = f * R / D   →   D = f * R / r_px

    where ``f`` is the focal length in pixels.  This implementation uses the
    average focal length ``(fx + fy) / 2`` for the depth calculation, then
    calls ``CameraIntrinsics.pixel_to_ray(u, v)`` to recover the 3-D unit
    direction.  The final 3-D point is ``depth * unit_ray``.

    V1 simplification
    -----------------
    The camera frame and robot frame are treated as coincident (no extrinsic
    calibration).  The returned ``BallObservation`` coordinates are therefore
    in camera frame, which is assumed equal to the robot frame.

    # TODO: apply extrinsic transform — multiply the camera-frame point by
    #       the camera-to-robot rotation matrix and add the translation vector
    #       once calibration data is available.

    Parameters
    ----------
    intrinsics : CameraIntrinsics
        Pinhole camera model (focal lengths, principal point).
    ball_radius_m : float
        Real-world radius of a standard ping-pong ball in metres.
        Default 0.020 m (40 mm diameter per ITTF specification).
        Must be strictly positive.
    """

    def __init__(
        self,
        intrinsics: CameraIntrinsics,
        ball_radius_m: float = 0.020,
    ) -> None:
        if ball_radius_m <= 0:
            raise ValueError(f"ball_radius_m must be strictly positive, got {ball_radius_m!r}")
        self._intrinsics = intrinsics
        self._ball_radius_m = ball_radius_m

    def estimate(self, obs: PixelObservation) -> BallObservation:
        """Return the ball's 3-D position in the robot frame.

        Parameters
        ----------
        obs : PixelObservation
            Image-space observation including timestamp, pixel centre, and
            apparent radius.

        Returns
        -------
        BallObservation
            Robot-frame (== camera-frame for V1) position with the same
            timestamp as the input observation.
        """
        avg_f = (self._intrinsics.fx_px + self._intrinsics.fy_px) / 2.0
        depth = (self._ball_radius_m * avg_f) / obs.radius_px

        rx, ry, rz = self._intrinsics.pixel_to_ray(obs.u_px, obs.v_px)

        # Scale the unit ray by depth to get the 3-D point.
        # V1: camera frame == robot frame (no extrinsic transform applied).
        return BallObservation(
            t=obs.t,
            x=depth * rx,
            y=depth * ry,
            z=depth * rz,
        )


class StereoDepthEstimator:
    """Stub for future stereo depth estimation.

    Raises ``NotImplementedError`` immediately on construction so callers
    fail fast rather than at the first ``estimate()`` call.
    """

    def __init__(self) -> None:
        raise NotImplementedError(
            "StereoDepthEstimator is not yet implemented. "
            "Use BallRadiusDepthEstimator for monocular depth."
        )

    def estimate(self, obs: PixelObservation) -> BallObservation:  # pragma: no cover
        raise NotImplementedError("StereoDepthEstimator is not yet implemented.")


class RealSenseDepthEstimator:
    """Stub for future Intel RealSense depth estimation.

    Raises ``NotImplementedError`` immediately on construction so callers
    fail fast rather than at the first ``estimate()`` call.
    """

    def __init__(self) -> None:
        raise NotImplementedError(
            "RealSenseDepthEstimator is not yet implemented. "
            "Use BallRadiusDepthEstimator for monocular depth."
        )

    def estimate(self, obs: PixelObservation) -> BallObservation:  # pragma: no cover
        raise NotImplementedError("RealSenseDepthEstimator is not yet implemented.")


def _demo() -> None:
    """Print a sanity-check depth estimate for a ball on the optical axis.

    Run with ``python -m mcenroebot.ball``.
    """
    import math

    from mcenroebot.ball.value_objects import PixelObservation
    from mcenroebot.camera import CameraIntrinsics

    cam = CameraIntrinsics(
        fx_px=600.0,
        fy_px=600.0,
        cx_px=320.0,
        cy_px=240.0,
        image_width=640,
        image_height=480,
    )
    estimator = BallRadiusDepthEstimator(intrinsics=cam, ball_radius_m=0.020)

    cases = [
        ("On optical axis, depth=1m", 320.0, 240.0, 12.0),
        ("On optical axis, depth=2m", 320.0, 240.0, 6.0),
        ("Off-axis, depth=1m (approx)", 400.0, 300.0, 12.0),
    ]

    print(
        f"Camera: {cam.image_width}x{cam.image_height}  "
        f"f=({cam.fx_px}, {cam.fy_px})  c=({cam.cx_px}, {cam.cy_px})"
    )
    print(f"Ball radius: {estimator._ball_radius_m * 1000:.0f} mm")
    print()

    for label, u, v, r in cases:
        obs = PixelObservation(t=0.0, u_px=u, v_px=v, radius_px=r)
        result = estimator.estimate(obs)
        dist = math.sqrt(result.x**2 + result.y**2 + result.z**2)
        print(f"=== {label} ===")
        print(f"  pixel=({u:.1f}, {v:.1f})  radius={r:.1f}px")
        print(f"  position=({result.x:+.4f}, {result.y:+.4f}, {result.z:+.4f}) m  |p|={dist:.4f} m")
        print()
