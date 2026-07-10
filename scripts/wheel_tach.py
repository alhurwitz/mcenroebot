#!/usr/bin/env python3
"""Optical wheel tachometer using the ELP OV9281 global-shutter USB camera.

Setup
-----
1. Put ONE strip of white tape (or paint) on the wheel's side face.
2. Aim one camera eye at the wheel side, close enough that the stripe's
   sweep fills a chunk of the frame. Good light helps; global shutter
   means no smear, but short exposure keeps the stripe crisp.
3. Run with --show first to position the ROI box over the stripe's path,
   then measure.

How it works
------------
Mean brightness of a small ROI is sampled every frame; each stripe pass is
a brightness spike. An FFT of a few seconds of that signal gives the pass
frequency: rpm = 60 * freq / stripes.

Nyquist limit: max measurable speed = (fps / 2) / stripes rev/s
  - 120 fps, 1 stripe -> 3,600 rpm  (covers the 10-30% throttle band)
  - full-throttle rpm ALIASES and cannot be measured this way; fit the
    ThrottleMap from low-band points instead.

Usage
-----
  python3 scripts/wheel_tach.py --show                 # aim the ROI
  python3 scripts/wheel_tach.py --seconds 5            # measure
  python3 scripts/wheel_tach.py --selftest             # no camera needed
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any

import numpy as np

DEFAULT_DEVICE = 0
DEFAULT_SECONDS = 5.0
DEFAULT_FPS = 120
DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 400
MIN_PEAK_HZ = 2.0  # ignore DC / slow lighting drift below this


def measure_rpm(samples: np.ndarray, fps: float, stripes: int) -> tuple[float, float]:
    """Return (rpm, peak_strength 0-1) from a brightness time series."""
    x = samples - samples.mean()
    if np.allclose(x, 0.0):
        return 0.0, 0.0
    window = np.hanning(len(x))
    spectrum = np.abs(np.fft.rfft(x * window))
    freqs = np.fft.rfftfreq(len(x), d=1.0 / fps)
    valid = freqs >= MIN_PEAK_HZ
    if not valid.any() or spectrum[valid].max() == 0.0:
        return 0.0, 0.0
    peak_idx = np.argmax(spectrum * valid)
    peak_hz = float(freqs[peak_idx])
    strength = float(spectrum[peak_idx] / spectrum[valid].sum())
    return 60.0 * peak_hz / stripes, strength


def _open_camera(device: int, width: int, height: int, fps: int) -> tuple[Any, Any]:
    """
    Opens and configures a camera device for capturing video.

    This function initializes a camera using OpenCV and sets specific
    configuration parameters including resolution and frames per second
    (fps). It raises a system exit if OpenCV is not installed or the
    camera device cannot be opened.

    Parameters:
    device (int): The ID of the camera device to open.
    width (int): The desired width of the video frame.
    height (int): The desired height of the video frame.
    fps (int): The desired frame rate for the video capture.

    Returns:
        tuple: A tuple containing the OpenCV module and the video capture object.
    """
    try:
        import cv2
    except ImportError:
        sys.exit("opencv-python required for capture: uv add opencv-python (or pip install)")
    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        sys.exit(f"cannot open camera device {device}")
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    return cv2, cap


def _roi_slice(args: argparse.Namespace, frame_shape: tuple[int, ...]) -> tuple[slice, slice]:
    h, w = frame_shape[:2]
    rx = args.roi_x if args.roi_x >= 0 else w // 2 - args.roi_size // 2
    ry = args.roi_y if args.roi_y >= 0 else h // 2 - args.roi_size // 2
    return slice(ry, ry + args.roi_size), slice(rx, rx + args.roi_size)


def show_preview(args: argparse.Namespace) -> int:
    cv2, cap = _open_camera(args.device, args.width, args.height, args.fps)
    print("preview: ROI box shown; 'q' to quit. Position the stripe path inside the box.")
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        ys, xs = _roi_slice(args, frame.shape)
        cv2.rectangle(frame, (xs.start, ys.start), (xs.stop, ys.stop), (255, 255, 255), 2)
        cv2.imshow("wheel_tach ROI", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()
    return 0


def capture_and_measure(args: argparse.Namespace) -> int:
    cv2, cap = _open_camera(args.device, args.width, args.height, args.fps)
    values: list[float] = []
    t0 = time.monotonic()
    while time.monotonic() - t0 < args.seconds:
        ok, frame = cap.read()
        if not ok:
            sys.exit("frame grab failed mid-capture")
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        ys, xs = _roi_slice(args, gray.shape)
        values.append(float(gray[ys, xs].mean()))
    elapsed = time.monotonic() - t0
    cap.release()

    real_fps = len(values) / elapsed
    max_rpm = 60.0 * (real_fps / 2.0) / args.stripes
    rpm, strength = measure_rpm(np.asarray(values), real_fps, args.stripes)
    print(
        f"frames: {len(values)}  measured fps: {real_fps:.1f}  "
        f"nyquist limit: {max_rpm:.0f} rpm ({args.stripes} stripe(s))"
    )
    if strength < 0.05:
        print("WARNING: weak peak — check ROI placement, lighting, or wheel not spinning")
    print(f"wheel speed: {rpm:.0f} rpm  (peak strength {strength:.2f})")
    if rpm > 0.9 * max_rpm:
        print("WARNING: near nyquist limit — reading may be aliased; reduce throttle")
    return 0


def selftest() -> int:
    """Synthetic check: 40 rev/s (2400 rpm), 1 stripe, 120 fps, 5 s, with noise."""
    rng = np.random.default_rng(42)
    fps, rev_hz, seconds = 120.0, 40.0, 5.0
    t = np.arange(int(fps * seconds)) / fps
    # narrow stripe pass = brief brightness spike each revolution
    phase = (t * rev_hz) % 1.0
    signal = np.where(phase < 0.1, 200.0, 40.0) + rng.normal(0, 5.0, t.size)
    rpm, strength = measure_rpm(signal, fps, stripes=1)
    expected = 60.0 * rev_hz
    ok = abs(rpm - expected) < 15.0 and strength > 0.05
    print(
        f"selftest: expected {expected:.0f} rpm, measured {rpm:.0f} "
        f"(strength {strength:.2f}) -> {'PASS' if ok else 'FAIL'}"
    )
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    p.add_argument("--device", type=int, default=DEFAULT_DEVICE, help="V4L2/UVC device index")
    p.add_argument("--seconds", type=float, default=DEFAULT_SECONDS)
    p.add_argument("--fps", type=int, default=DEFAULT_FPS)
    p.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    p.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    p.add_argument("--stripes", type=int, default=1, help="tape stripes on the wheel")
    p.add_argument("--roi-x", type=int, default=-1, help="ROI left px (-1 = centered)")
    p.add_argument("--roi-y", type=int, default=-1, help="ROI top px (-1 = centered)")
    p.add_argument("--roi-size", type=int, default=40, help="ROI box side px")
    p.add_argument("--show", action="store_true", help="preview to position the ROI")
    p.add_argument("--selftest", action="store_true", help="verify FFT path, no camera")
    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.selftest:
        return selftest()
    if args.show:
        return show_preview(args)
    return capture_and_measure(args)


if __name__ == "__main__":
    raise SystemExit(main())
