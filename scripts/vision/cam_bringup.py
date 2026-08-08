#!/usr/bin/env python3
"""Camera bring-up: enumerate USB cameras, live preview, FPS/latency, FOV measurement.

Usage:
  python3 cam_bringup.py --scan            # list working camera indices
  python3 cam_bringup.py --cam 0           # live preview + FPS/latency overlay
  python3 cam_bringup.py --cam 0 --fov 21.6 200
                                           # FOV mode: target 21.6cm wide at 200cm.
                                           # Click its left edge, then right edge.

Preview keys: q=quit  s=save frame  r=reset FOV clicks
Results (measured FPS, resolution, FOV) are saved to camera_profile.json.
"""

import argparse
import json
import time
from math import atan, degrees
from pathlib import Path
from typing import Any

import cv2

PROFILE = Path(__file__).parent / "camera_profile.json"


def scan(max_idx: int = 5) -> list[int]:
    found = []
    for i in range(max_idx):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ok, frame = cap.read()
            if ok:
                h, w = frame.shape[:2]
                print(f"  index {i}: {w}x{h}  (reported fps {cap.get(cv2.CAP_PROP_FPS):.0f})")
                found.append(i)
        cap.release()
    if not found:
        print("  no cameras found — check USB connection / macOS camera permission for Terminal")
    return found


def save_profile(update: dict[str, Any]) -> None:
    profile = json.loads(PROFILE.read_text()) if PROFILE.exists() else {}
    profile.update(update)
    PROFILE.write_text(json.dumps(profile, indent=2))
    print(f"saved -> {PROFILE.name}: {update}")


def preview(cam: int, fov_target: tuple[float, float] | None) -> None:
    cap = cv2.VideoCapture(cam)
    if not cap.isOpened():
        raise SystemExit(f"camera {cam} failed to open")
    # Ask for the good stuff; camera gives what it can.
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    clicks: list[tuple[int, int]] = []

    def on_mouse(event: int, x: int, y: int, flags: int, param: Any) -> None:
        if event == cv2.EVENT_LBUTTONDOWN and fov_target:
            clicks.append((x, y))

    win = f"cam {cam}"
    cv2.namedWindow(win)
    cv2.setMouseCallback(win, on_mouse)

    times: list[float] = []
    n_saved = 0
    while True:
        t0 = time.perf_counter()
        ok, frame = cap.read()
        t1 = time.perf_counter()
        if not ok:
            print("frame grab failed")
            break
        times.append(t1 - t0)
        if len(times) > 60:
            times.pop(0)
        h, w = frame.shape[:2]
        fps = len(times) / sum(times) if times else 0.0
        lat_ms = 1000 * sum(times) / len(times)
        cv2.putText(
            frame,
            f"{w}x{h}  {fps:.1f} fps  grab {lat_ms:.0f} ms",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

        if fov_target:
            cv2.putText(
                frame,
                "FOV: click LEFT then RIGHT edge of target (r=reset)",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2,
            )
            for c in clicks:
                cv2.drawMarker(frame, c, (0, 0, 255), cv2.MARKER_CROSS, 20, 2)
            if len(clicks) >= 2:
                (x1, _), (x2, _) = clicks[0], clicks[1]
                px = abs(x2 - x1)
                target_w_cm, dist_cm = fov_target
                focal_px = px * dist_cm / target_w_cm
                hfov = degrees(2 * atan(w / (2 * focal_px)))
                vfov = degrees(2 * atan(h / (2 * focal_px)))
                msg = f"focal {focal_px:.0f}px  hFOV {hfov:.1f}deg  vFOV {vfov:.1f}deg"
                cv2.putText(frame, msg, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.line(frame, clicks[0], clicks[1], (0, 0, 255), 1)

        cv2.imshow(win, frame)
        k = cv2.waitKey(1) & 0xFF
        if k == ord("q"):
            break
        if k == ord("r"):
            clicks.clear()
        if k == ord("s"):
            fn = f"frame_{n_saved}.png"
            cv2.imwrite(fn, frame)
            print(f"saved {fn}")
            n_saved += 1

    result = {"cam_index": cam, "width": w, "height": h, "measured_fps": round(fps, 1)}
    if fov_target and len(clicks) >= 2:
        result.update(
            {"focal_px": round(focal_px, 1), "hfov_deg": round(hfov, 2), "vfov_deg": round(vfov, 2)}
        )
    save_profile(result)
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--cam", type=int, default=None)
    ap.add_argument("--fov", nargs=2, type=float, metavar=("TARGET_W_CM", "DIST_CM"))
    args = ap.parse_args()
    if args.scan or args.cam is None:
        print("scanning camera indices 0-4:")
        scan()
    if args.cam is not None:
        preview(args.cam, tuple(args.fov) if args.fov else None)
