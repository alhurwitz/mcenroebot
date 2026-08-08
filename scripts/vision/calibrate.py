#!/usr/bin/env python3
"""Camera intrinsics calibration with a printed checkerboard.

1. python3 calibrate.py --make-board     # writes checkerboard.png; print at 100% on letter
2. python3 calibrate.py --cam 0          # SPACE to capture (need >=10 varied poses), q=done
3. Intrinsics saved to camera_intrinsics.json (K, dist coeffs, RMS error)

Board: 9x6 inner corners, 20mm squares (fits letter landscape at 100% scale).
Verify with a ruler after printing: one square must be 20mm.
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

COLS, ROWS = 9, 6  # inner corners
SQUARE_MM = 20.0
OUT = Path(__file__).parent / "camera_intrinsics.json"


def make_board() -> None:
    px = 100  # px per square; print scaling is what sets physical size
    img = np.full(((ROWS + 1) * px, (COLS + 1) * px), 255, np.uint8)
    for r in range(ROWS + 1):
        for c in range(COLS + 1):
            if (r + c) % 2 == 0:
                img[r * px : (r + 1) * px, c * px : (c + 1) * px] = 0
    # white border so corner detection works at the edges
    img = cv2.copyMakeBorder(img, px, px, px, px, cv2.BORDER_CONSTANT, value=255)
    fn = Path(__file__).parent / "checkerboard.png"
    cv2.imwrite(str(fn), img)
    print(
        f"wrote {fn} — print at 100% scale, verify squares are {SQUARE_MM}mm, "
        f"tape to something flat"
    )


def calibrate(cam: int) -> None:
    objp = np.zeros((ROWS * COLS, 3), np.float32)
    objp[:, :2] = np.mgrid[0:COLS, 0:ROWS].T.reshape(-1, 2) * SQUARE_MM

    obj_pts: list[cv2.typing.MatLike] = []
    img_pts: list[cv2.typing.MatLike] = []
    cap = cv2.VideoCapture(cam)
    shape: tuple[int, ...] | None = None
    print("SPACE=capture when corners drawn, q=finish. Vary angle/distance/corner-of-frame.")
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        shape = gray.shape[::-1]
        found, corners = cv2.findChessboardCorners(gray, (COLS, ROWS), None)
        vis = frame.copy()
        if found:
            cv2.drawChessboardCorners(vis, (COLS, ROWS), corners, found)
        cv2.putText(
            vis,
            f"captures: {len(obj_pts)}  (need >=10)",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0) if found else (0, 0, 255),
            2,
        )
        cv2.imshow("calibrate", vis)
        k = cv2.waitKey(1) & 0xFF
        if k == ord(" ") and found:
            corners = cv2.cornerSubPix(
                gray,
                corners,
                (11, 11),
                (-1, -1),
                (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001),
            )
            obj_pts.append(objp)
            img_pts.append(corners)
            print(f"captured {len(obj_pts)}")
        elif k == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()

    if len(obj_pts) < 10 or shape is None:
        raise SystemExit(f"only {len(obj_pts)} captures — need >=10, rerun")
    rms, K, dist, _, _ = cv2.calibrateCamera(obj_pts, img_pts, shape, None, None)
    fx = K[0, 0]
    hfov = float(np.degrees(2 * np.arctan(shape[0] / (2 * fx))))
    OUT.write_text(
        json.dumps(
            {
                "rms_reprojection_error_px": round(float(rms), 3),
                "image_size": shape,
                "K": K.tolist(),
                "dist_coeffs": dist.ravel().tolist(),
                "hfov_deg": round(hfov, 2),
                "captures": len(obj_pts),
            },
            indent=2,
        )
    )
    print(f"RMS error {rms:.3f}px ({'good' if rms < 1 else 'redo with more varied poses'})")
    print(f"hFOV {hfov:.1f} deg   saved -> {OUT.name}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--make-board", action="store_true")
    ap.add_argument("--cam", type=int, default=None)
    args = ap.parse_args()
    if args.make_board:
        make_board()
    elif args.cam is not None:
        calibrate(args.cam)
    else:
        ap.print_help()
