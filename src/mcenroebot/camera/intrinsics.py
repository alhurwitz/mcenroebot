"""Pinhole camera intrinsics model and pixel-to-ray projection."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, field_validator

__all__ = ["CameraIntrinsics", "_demo"]


class CameraIntrinsics(BaseModel):
    """Pinhole camera model.

    Fill from `cv2.calibrateCamera` output, or hand-construct for testing.

    Attributes
    ----------
    fx_px : float
        Focal length along the x axis, in pixels. Must be positive.
    fy_px : float
        Focal length along the y axis, in pixels. Must be positive.
    cx_px : float
        Principal point x coordinate, in pixels. May be any float.
    cy_px : float
        Principal point y coordinate, in pixels. May be any float.
    distortion : tuple[float, float, float, float, float]
        OpenCV-style distortion coefficients (k1, k2, p1, p2, k3).
        Stored but not applied in ``pixel_to_ray`` — see TODO below.
    image_width : int
        Sensor width in pixels. Must be positive.
    image_height : int
        Sensor height in pixels. Must be positive.
    """

    model_config = ConfigDict(frozen=True)

    fx_px: float
    fy_px: float
    cx_px: float
    cy_px: float
    distortion: tuple[float, float, float, float, float] = (0.0, 0.0, 0.0, 0.0, 0.0)
    image_width: int
    image_height: int

    @field_validator("fx_px", "fy_px")
    @classmethod
    def _check_focal_length_positive(cls, value: float) -> float:
        if value <= 0.0:
            raise ValueError(f"focal length must be positive, got {value!r}")
        return value

    @field_validator("image_width", "image_height")
    @classmethod
    def _check_image_dimension_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError(f"image dimension must be positive, got {value!r}")
        return value

    def pixel_to_ray(self, u: float, v: float) -> tuple[float, float, float]:
        """Map a pixel (u, v) to a normalized 3-D ray in camera coordinates.

        Returns a unit vector pointing into the scene along the ray that
        the camera centre projects to (u, v). Used downstream by the depth
        estimator / ground-plane intersection logic.

        Parameters
        ----------
        u : float
            Pixel column coordinate (x in image space).
        v : float
            Pixel row coordinate (y in image space).

        Returns
        -------
        tuple[float, float, float]
            Unit vector ``(rx, ry, rz)`` in camera coordinates, where ``+z``
            points into the scene (the optical axis direction).

        Notes
        -----
        Pinhole math: ``(u, v) -> ((u - cx) / fx, (v - cy) / fy, 1.0)``
        then normalise to unit length.

        # TODO: apply distortion — undistort (u, v) before applying pinhole
        #       formula once V2 ball-radius depth estimator is calibrated.
        """
        rx = (u - self.cx_px) / self.fx_px
        ry = (v - self.cy_px) / self.fy_px
        rz = 1.0
        magnitude = math.sqrt(rx * rx + ry * ry + rz * rz)
        return (rx / magnitude, ry / magnitude, rz / magnitude)


def _demo() -> None:
    """Print sanity-check projections for a few representative pixels.

    Run with `python -m mcenroebot.camera`.
    """
    # Typical webcam-ish intrinsics (VGA 640x480, ~75° hFoV).
    cam = CameraIntrinsics(
        fx_px=600.0,
        fy_px=600.0,
        cx_px=320.0,
        cy_px=240.0,
        image_width=640,
        image_height=480,
    )
    cases = [
        ("Principal point (cx, cy)", cam.cx_px, cam.cy_px),
        ("Top-left corner", 0.0, 0.0),
        ("Bottom-right corner", float(cam.image_width - 1), float(cam.image_height - 1)),
        ("Right of centre", cam.cx_px + 100.0, cam.cy_px),
        ("Above centre", cam.cx_px, cam.cy_px - 100.0),
    ]
    print(
        f"Camera: {cam.image_width}x{cam.image_height}  "
        f"f=({cam.fx_px}, {cam.fy_px})  c=({cam.cx_px}, {cam.cy_px})"
    )
    print()
    for label, u, v in cases:
        rx, ry, rz = cam.pixel_to_ray(u, v)
        magnitude = math.sqrt(rx * rx + ry * ry + rz * rz)
        print(f"=== {label} ===")
        print(f"  pixel=({u:.1f}, {v:.1f})")
        print(f"  ray=({rx:+.6f}, {ry:+.6f}, {rz:+.6f})  |r|={magnitude:.6f}")
        print()
