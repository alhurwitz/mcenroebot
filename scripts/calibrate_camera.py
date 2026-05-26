#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "opencv-python>=4.10",
#     "numpy>=1.24",
#     "pydantic>=2.13.4",
# ]
# ///
"""Webcam intrinsics calibration via OpenCV checkerboard.

Two-step workflow:

    # 1) Capture frames of a printed checkerboard from many angles.
    uv run scripts/calibrate_camera.py capture --device 0 --out captures/

       SPACE saves a frame, ESC quits. Aim for 15-25 frames covering
       different rotations, tilts, and positions across the image.

    # 2) Solve intrinsics from the saved frames.
    uv run scripts/calibrate_camera.py solve captures/ \
            --board 9x6 --square-mm 25 --out intrinsics.json

       Writes a JSON file that loads directly into a
       ``mcenroebot.camera.intrinsics.CameraIntrinsics`` instance:

           from mcenroebot.camera.intrinsics import CameraIntrinsics
           cam = CameraIntrinsics.model_validate_json(
               pathlib.Path("intrinsics.json").read_text()
           )

The "board" argument is the count of *internal* corners (not squares).
A standard A4 9x6 checkerboard with 25mm squares prints fine on letter
paper at ~95% scale.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Final

import cv2
import numpy as np

# OpenCV's distortion model returns (k1, k2, p1, p2, k3) in that order — same
# as the tuple expected by mcenroebot.camera.intrinsics.CameraIntrinsics.
_DISTORTION_LEN: Final[int] = 5
_SUBPIX_WIN: Final[tuple[int, int]] = (11, 11)
_SUBPIX_ZERO: Final[tuple[int, int]] = (-1, -1)
_SUBPIX_CRITERIA: Final[tuple[int, int, float]] = (
    cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER,
    30,
    1e-3,
)


# ---------------------------------------------------------------------------
# Board geometry
# ---------------------------------------------------------------------------


def parse_board(text: str) -> tuple[int, int]:
    """Parse '9x6' into (9, 6). Tolerates 'X' too."""
    parts = text.lower().replace("x", " ").split()
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(f"--board must be WxH (got {text!r})")
    try:
        w, h = int(parts[0]), int(parts[1])
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"--board components must be ints (got {text!r})") from exc
    if w < 2 or h < 2:
        raise argparse.ArgumentTypeError(f"--board sides must be >=2 (got {text!r})")
    return w, h


def make_object_points(board: tuple[int, int], square_mm: float) -> np.ndarray:
    """Generate the (N, 3) array of 3-D points for one view of the board.

    Points lie on the plane z=0; x/y are scaled by ``square_mm`` and converted
    to meters so the recovered focal length is in pixels (intrinsics are
    metric-independent for a planar target, but downstream code uses meters,
    so we may as well stay consistent).
    """
    cols, rows = board
    objp = np.zeros((rows * cols, 3), dtype=np.float32)
    objp[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2)
    objp *= square_mm / 1000.0  # mm -> m
    return objp


# ---------------------------------------------------------------------------
# capture mode
# ---------------------------------------------------------------------------


def capture(device: int, out_dir: Path, board: tuple[int, int]) -> int:
    """Live preview with checkerboard overlay; SPACE saves, ESC quits."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        print(f"error: could not open video device {device}", file=sys.stderr)
        return 1

    saved = 0
    print(f"capture: device={device}  board={board[0]}x{board[1]}  out={out_dir}")
    print("SPACE = save frame   ESC = quit")
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("warning: frame grab failed", file=sys.stderr)
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            found, corners = cv2.findChessboardCorners(gray, board, None)
            display = frame.copy()
            if found:
                cv2.drawChessboardCorners(display, board, corners, found)
            status = f"saved={saved}  found={'Y' if found else 'n'}"
            cv2.putText(
                display,
                status,
                (12, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0) if found else (0, 0, 255),
                2,
            )
            cv2.imshow("calibrate_camera — capture", display)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                break
            if key == 32 and found:  # SPACE, but only if board detected
                path = out_dir / f"frame_{saved:03d}.png"
                cv2.imwrite(str(path), frame)
                saved += 1
                print(f"  saved {path.name}")
            elif key == 32:
                print("  (no board detected — not saving)")
    finally:
        cap.release()
        cv2.destroyAllWindows()
    print(f"capture done: {saved} frame(s) written to {out_dir}")
    return 0


# ---------------------------------------------------------------------------
# solve mode
# ---------------------------------------------------------------------------


def solve(
    images_dir: Path,
    board: tuple[int, int],
    square_mm: float,
    out_path: Path,
) -> int:
    """Detect corners in each image, run cv2.calibrateCamera, write JSON."""
    paths = sorted(p for p in images_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"})
    if not paths:
        print(f"error: no images found in {images_dir}", file=sys.stderr)
        return 1

    objp = make_object_points(board, square_mm)
    image_points: list[np.ndarray] = []
    object_points: list[np.ndarray] = []
    image_size: tuple[int, int] | None = None
    used: list[str] = []
    skipped: list[str] = []

    for path in paths:
        img = cv2.imread(str(path))
        if img is None:
            skipped.append(f"{path.name} (unreadable)")
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        if image_size is None:
            image_size = (w, h)
        elif (w, h) != image_size:
            skipped.append(f"{path.name} (size {w}x{h} != {image_size[0]}x{image_size[1]})")
            continue
        found, corners = cv2.findChessboardCorners(gray, board, None)
        if not found:
            skipped.append(f"{path.name} (no board detected)")
            continue
        refined = cv2.cornerSubPix(gray, corners, _SUBPIX_WIN, _SUBPIX_ZERO, _SUBPIX_CRITERIA)
        image_points.append(refined)
        object_points.append(objp)
        used.append(path.name)

    if image_size is None or len(used) < 5:
        print(
            f"error: need at least 5 frames with detected board "
            f"(got {len(used)} usable, {len(skipped)} skipped)",
            file=sys.stderr,
        )
        for s in skipped:
            print(f"  skipped {s}", file=sys.stderr)
        return 1

    print(f"solve: {len(used)} frames used, {len(skipped)} skipped")
    ret_rms, K, dist, _rvecs, _tvecs = cv2.calibrateCamera(
        object_points,
        image_points,
        image_size,
        None,
        None,
    )
    fx_px = float(K[0, 0])
    fy_px = float(K[1, 1])
    cx_px = float(K[0, 2])
    cy_px = float(K[1, 2])
    distortion = tuple(float(x) for x in dist.ravel()[:_DISTORTION_LEN])
    if len(distortion) < _DISTORTION_LEN:
        distortion = distortion + (0.0,) * (_DISTORTION_LEN - len(distortion))

    payload = {
        "fx_px": fx_px,
        "fy_px": fy_px,
        "cx_px": cx_px,
        "cy_px": cy_px,
        "distortion": list(distortion),
        "image_width": int(image_size[0]),
        "image_height": int(image_size[1]),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n")

    fov_h_deg = math.degrees(2 * math.atan(image_size[0] / (2 * fx_px)))
    fov_v_deg = math.degrees(2 * math.atan(image_size[1] / (2 * fy_px)))
    print(f"  RMS reprojection error: {ret_rms:.4f} px")
    print(f"  fx={fx_px:.2f}  fy={fy_px:.2f}  cx={cx_px:.2f}  cy={cy_px:.2f}")
    print(
        f"  distortion (k1, k2, p1, p2, k3): "
        f"({distortion[0]:+.4f}, {distortion[1]:+.4f}, "
        f"{distortion[2]:+.4f}, {distortion[3]:+.4f}, {distortion[4]:+.4f})"
    )
    print(f"  image: {image_size[0]}x{image_size[1]}  hFoV={fov_h_deg:.1f}°  vFoV={fov_v_deg:.1f}°")
    print(f"  wrote {out_path}")
    if ret_rms > 1.0:
        print(
            f"warning: RMS error {ret_rms:.2f} px is high — consider recapturing "
            "with sharper, more varied frames",
            file=sys.stderr,
        )
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    description = (__doc__ or "").splitlines()[0]
    p = argparse.ArgumentParser(description=description)
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("capture", help="grab calibration frames from a webcam")
    pc.add_argument("--device", type=int, default=0, help="webcam device index (default 0)")
    pc.add_argument(
        "--out", type=Path, default=Path("captures"), help="output directory for saved frames"
    )
    pc.add_argument(
        "--board",
        type=parse_board,
        default=(9, 6),
        help="internal corner count, e.g. 9x6 (default)",
    )

    ps = sub.add_parser("solve", help="solve intrinsics from saved frames")
    ps.add_argument("images_dir", type=Path, help="directory of calibration frames")
    ps.add_argument(
        "--board", type=parse_board, required=True, help="internal corner count, e.g. 9x6"
    )
    ps.add_argument(
        "--square-mm",
        type=float,
        required=True,
        help="physical edge length of one square, in millimeters",
    )
    ps.add_argument(
        "--out",
        type=Path,
        default=Path("intrinsics.json"),
        help="where to write the intrinsics JSON",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "capture":
        return capture(args.device, args.out, args.board)
    if args.cmd == "solve":
        return solve(args.images_dir, args.board, args.square_mm, args.out)
    return 2


if __name__ == "__main__":
    sys.exit(main())
