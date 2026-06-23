"""Ball-observation value objects and monocular depth estimator.

This package provides everything needed to turn raw camera data into 3-D
ball positions in the robot frame, and to express the estimator's output
as a stream of observations suitable for the trajectory predictor.

Layout
------
    value_objects.py  — BallObservation, BallState, StrikePrediction,
                        PixelObservation (frozen pydantic v2).
    depth.py          — DepthEstimator Protocol + BallRadiusDepthEstimator
                        implementation + StereoDepthEstimator and
                        RealSenseDepthEstimator stubs.
    __main__.py       — entry point for ``python -m mcenroebot._shelved.ball``.

Value objects
-------------
    ``BallObservation`` — a single sample in robot-frame (t, x, y, z).
    ``BallState``       — estimated position and velocity at a given time.
    ``StrikePrediction``— predicted impact point, time, and confidence.
    ``PixelObservation``— image-space sample fed into a DepthEstimator.

Depth estimation
----------------
    ``DepthEstimator`` is a ``@runtime_checkable`` structural Protocol. The
    only production implementation in V1 is ``BallRadiusDepthEstimator``,
    which recovers depth monocularly from the apparent pixel radius of the
    ball under the pinhole camera model::

        depth = (real_radius_m * focal_length_px) / apparent_radius_px

Coordinate system
-----------------
    Robot frame (shared with the aim subsystem):
        +X  forward (toward the ball).
        +Y  left (viewed from above).
        +Z  up.
        Origin: J1 yaw axis at J2 pitch pivot height.

    V1 simplification: the camera frame is treated as coincident with the
    robot frame (no extrinsic calibration). This will be refined in a future
    task once the camera is mounted and calibrated.
"""

from __future__ import annotations

from mcenroebot._shelved.ball.depth import (
    BallRadiusDepthEstimator,
    DepthEstimator,
    RealSenseDepthEstimator,
    StereoDepthEstimator,
    _demo,
)
from mcenroebot._shelved.ball.value_objects import (
    BallObservation,
    BallState,
    PixelObservation,
    StrikePrediction,
)

__all__ = [
    "BallObservation",
    "BallRadiusDepthEstimator",
    "BallState",
    "DepthEstimator",
    "PixelObservation",
    "RealSenseDepthEstimator",
    "StereoDepthEstimator",
    "StrikePrediction",
    "_demo",
]
