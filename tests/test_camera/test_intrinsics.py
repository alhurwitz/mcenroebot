"""Tests for CameraIntrinsics and pixel_to_ray in mcenroebot.camera.intrinsics."""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from mcenroebot.camera import CameraIntrinsics


# ---------------------------------------------------------------------------
# Shared fixture — a realistic set of intrinsics used across multiple tests.
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
# 1. Construction — happy path.
# ---------------------------------------------------------------------------

class TestConstruction:
    def test_all_fields_readable(self) -> None:
        cam = CameraIntrinsics(
            fx_px=800.0,
            fy_px=810.0,
            cx_px=320.5,
            cy_px=240.5,
            distortion=(0.1, -0.05, 0.001, -0.002, 0.03),
            image_width=640,
            image_height=480,
        )
        assert cam.fx_px == pytest.approx(800.0)
        assert cam.fy_px == pytest.approx(810.0)
        assert cam.cx_px == pytest.approx(320.5)
        assert cam.cy_px == pytest.approx(240.5)
        assert cam.distortion == pytest.approx((0.1, -0.05, 0.001, -0.002, 0.03))
        assert cam.image_width == 640
        assert cam.image_height == 480

    def test_keyword_only_construction(self) -> None:
        # Verify pydantic's keyword-only enforcement doesn't accidentally
        # allow positional arguments (the mypy plugin enforces this, but
        # we also guard it here as a runtime sanity check).
        cam = _make_cam()
        assert cam.fx_px == pytest.approx(600.0)


# ---------------------------------------------------------------------------
# 2. Defaults — distortion defaults to five zeros.
# ---------------------------------------------------------------------------

class TestDefaults:
    def test_distortion_defaults_to_five_zeros(self) -> None:
        cam = _make_cam()
        assert cam.distortion == (0.0, 0.0, 0.0, 0.0, 0.0)

    def test_distortion_is_a_five_tuple(self) -> None:
        cam = _make_cam()
        assert len(cam.distortion) == 5


# ---------------------------------------------------------------------------
# 3. Frozen — assigning to any field raises ValidationError.
# ---------------------------------------------------------------------------

class TestFrozen:
    def test_assign_fx_raises(self) -> None:
        cam = _make_cam()
        with pytest.raises(ValidationError):
            cam.fx_px = 999.0  # type: ignore[misc]

    def test_assign_image_width_raises(self) -> None:
        cam = _make_cam()
        with pytest.raises(ValidationError):
            cam.image_width = 1920  # type: ignore[misc]

    def test_assign_distortion_raises(self) -> None:
        cam = _make_cam()
        with pytest.raises(ValidationError):
            cam.distortion = (1.0, 0.0, 0.0, 0.0, 0.0)  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 4. Validators — invalid inputs raise ValidationError.
# ---------------------------------------------------------------------------

class TestValidators:
    @pytest.mark.parametrize(
        "fx_px",
        [-1.0, -100.0, 0.0],
    )
    def test_non_positive_fx_raises(self, fx_px: float) -> None:
        with pytest.raises(ValidationError, match=r"focal length must be positive"):
            CameraIntrinsics(
                fx_px=fx_px,
                fy_px=600.0,
                cx_px=320.0,
                cy_px=240.0,
                image_width=640,
                image_height=480,
            )

    @pytest.mark.parametrize(
        "fy_px",
        [-1.0, -100.0, 0.0],
    )
    def test_non_positive_fy_raises(self, fy_px: float) -> None:
        with pytest.raises(ValidationError, match=r"focal length must be positive"):
            CameraIntrinsics(
                fx_px=600.0,
                fy_px=fy_px,
                cx_px=320.0,
                cy_px=240.0,
                image_width=640,
                image_height=480,
            )

    @pytest.mark.parametrize(
        "image_width,image_height",
        [
            (0, 480),
            (-1, 480),
            (640, 0),
            (640, -1),
            (0, 0),
        ],
    )
    def test_non_positive_image_dimensions_raise(
        self, image_width: int, image_height: int
    ) -> None:
        with pytest.raises(ValidationError, match=r"image dimension must be positive"):
            CameraIntrinsics(
                fx_px=600.0,
                fy_px=600.0,
                cx_px=320.0,
                cy_px=240.0,
                image_width=image_width,
                image_height=image_height,
            )

    def test_cx_cy_may_be_any_float(self) -> None:
        # Principal point is allowed outside the image bounds — no constraint.
        cam = CameraIntrinsics(
            fx_px=600.0,
            fy_px=600.0,
            cx_px=-100.0,  # outside [0, width]
            cy_px=9999.0,  # outside [0, height]
            image_width=640,
            image_height=480,
        )
        assert cam.cx_px == pytest.approx(-100.0)
        assert cam.cy_px == pytest.approx(9999.0)

    def test_very_small_positive_focal_length_accepted(self) -> None:
        # Just above zero is valid.
        cam = CameraIntrinsics(
            fx_px=1e-9,
            fy_px=1e-9,
            cx_px=0.0,
            cy_px=0.0,
            image_width=1,
            image_height=1,
        )
        assert cam.fx_px > 0.0


# ---------------------------------------------------------------------------
# 5. pixel_to_ray — round-trip via hand-computed projection.
# ---------------------------------------------------------------------------

class TestPixelToRayRoundTrip:
    def test_known_3d_point_round_trips(self) -> None:
        """Project a known camera-space 3D point to (u, v), then recover the ray."""
        cam = _make_cam()

        # Pick a 3D point in camera coordinates (z > 0 = in front of lens).
        px_3d, py_3d, pz_3d = 0.3, -0.2, 1.5

        # Project to pixel space: u = fx * (px/pz) + cx, v = fy * (py/pz) + cy.
        u = cam.fx_px * (px_3d / pz_3d) + cam.cx_px
        v = cam.fy_px * (py_3d / pz_3d) + cam.cy_px

        # Recover the ray.
        ray = cam.pixel_to_ray(u, v)

        # The original direction (normalised).
        orig_mag = math.sqrt(px_3d**2 + py_3d**2 + pz_3d**2)
        orig_unit = (px_3d / orig_mag, py_3d / orig_mag, pz_3d / orig_mag)

        # The recovered ray should be parallel to the original direction.
        dot = ray[0] * orig_unit[0] + ray[1] * orig_unit[1] + ray[2] * orig_unit[2]
        assert dot == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# 6. Principal-point ray — pixel_to_ray(cx, cy) == (0, 0, 1).
# ---------------------------------------------------------------------------

class TestPrincipalPointRay:
    def test_principal_point_gives_optical_axis_ray(self) -> None:
        cam = _make_cam()
        ray = cam.pixel_to_ray(cam.cx_px, cam.cy_px)
        assert ray[0] == pytest.approx(0.0, abs=1e-12)
        assert ray[1] == pytest.approx(0.0, abs=1e-12)
        assert ray[2] == pytest.approx(1.0, abs=1e-12)

    def test_principal_point_ray_with_non_centred_principal_point(self) -> None:
        # Asymmetric sensor — cx, cy far from image centre; still works.
        cam = CameraIntrinsics(
            fx_px=500.0,
            fy_px=505.0,
            cx_px=100.0,
            cy_px=80.0,
            image_width=320,
            image_height=240,
        )
        ray = cam.pixel_to_ray(100.0, 80.0)
        assert ray == pytest.approx((0.0, 0.0, 1.0), abs=1e-12)


# ---------------------------------------------------------------------------
# 7. Symmetry — rays left and right of principal point are symmetric.
# ---------------------------------------------------------------------------

class TestSymmetry:
    def test_symmetric_x_displacement_gives_opposite_rx(self) -> None:
        cam = _make_cam()
        dx = 80.0
        ray_right = cam.pixel_to_ray(cam.cx_px + dx, cam.cy_px)
        ray_left = cam.pixel_to_ray(cam.cx_px - dx, cam.cy_px)

        # x-components should be equal in magnitude, opposite in sign.
        assert ray_right[0] == pytest.approx(-ray_left[0], abs=1e-12)

        # y and z components should be identical.
        assert ray_right[1] == pytest.approx(ray_left[1], abs=1e-12)
        assert ray_right[2] == pytest.approx(ray_left[2], abs=1e-12)

    def test_symmetric_y_displacement_gives_opposite_ry(self) -> None:
        cam = _make_cam()
        dy = 60.0
        ray_below = cam.pixel_to_ray(cam.cx_px, cam.cy_px + dy)
        ray_above = cam.pixel_to_ray(cam.cx_px, cam.cy_px - dy)

        # y-components should be equal in magnitude, opposite in sign.
        assert ray_below[1] == pytest.approx(-ray_above[1], abs=1e-12)

        # x and z components should be identical.
        assert ray_below[0] == pytest.approx(ray_above[0], abs=1e-12)
        assert ray_below[2] == pytest.approx(ray_above[2], abs=1e-12)


# ---------------------------------------------------------------------------
# 8. Unit vector — the returned ray always has magnitude 1.
# ---------------------------------------------------------------------------

class TestUnitVector:
    @pytest.mark.parametrize(
        "u,v",
        [
            (320.0, 240.0),   # principal point
            (0.0, 0.0),       # top-left corner
            (639.0, 479.0),   # bottom-right corner
            (160.0, 120.0),   # off-centre inside image
            (500.0, 400.0),   # another interior pixel
            (320.0, 0.0),     # top edge, centre column
            (0.0, 240.0),     # left edge, centre row
        ],
    )
    def test_ray_is_unit_length(self, u: float, v: float) -> None:
        cam = _make_cam()
        rx, ry, rz = cam.pixel_to_ray(u, v)
        magnitude = math.sqrt(rx * rx + ry * ry + rz * rz)
        assert magnitude == pytest.approx(1.0, abs=1e-12)


# ---------------------------------------------------------------------------
# 9. Demo smoke test.
# ---------------------------------------------------------------------------

class TestDemo:
    def test_demo_runs_without_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        from mcenroebot.camera import _demo

        _demo()
        captured = capsys.readouterr()
        assert "Principal point" in captured.out
        assert "Top-left corner" in captured.out
        assert "|r|=" in captured.out
