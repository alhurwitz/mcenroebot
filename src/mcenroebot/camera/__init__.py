"""Pinhole camera model — intrinsics and pixel-to-ray projection.

This package provides the ``CameraIntrinsics`` value object that captures
the output of ``cv2.calibrateCamera`` (or hand-crafted test values), plus
a ``pixel_to_ray`` helper that maps image pixels to normalised 3-D rays in
camera coordinates. Those rays feed the downstream depth estimator and
ground-plane intersection logic.

Layout
------
    intrinsics.py  — CameraIntrinsics (frozen pydantic) + pixel_to_ray.
    __main__.py    — entry point for `python -m mcenroebot.camera`.

Coordinate system
-----------------
    Camera-coordinate convention (OpenCV / standard):
        +x  right (along image columns).
        +y  down  (along image rows).
        +z  into the scene (optical axis).

    ``pixel_to_ray`` returns unit vectors in this frame. The calling code
    (ball depth estimator, ground-plane intersector) is responsible for
    transforming from camera frame into the robot frame (+X forward, +Y
    left, +Z up) using the extrinsic rotation/translation determined during
    camera mounting calibration.

Simplifications for V1
----------------------
    Distortion coefficients are stored but not applied in ``pixel_to_ray``.
    This is intentional — the Logitech webcam's barrel distortion is small
    enough that a pixel-radius depth estimate from apparent ball size will
    not be materially affected. A ``# TODO: apply distortion`` note marks
    the site in the implementation.
"""

from __future__ import annotations

from mcenroebot.camera.intrinsics import CameraIntrinsics, _demo

__all__ = ["CameraIntrinsics", "_demo"]
