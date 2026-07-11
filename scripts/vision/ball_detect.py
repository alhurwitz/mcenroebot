#!/usr/bin/env python3
"""Tennis ball detection: live HSV tuner + tracker with trajectory trail.

Usage:
  python3 ball_detect.py --cam 0 --tune    # trackbars; tune until only the ball is white
  python3 ball_detect.py --cam 0           # track using saved ball_hsv.json

Tune keys: q=quit(saves)   Track keys: q=quit  c=clear trail
Emits one line per frame in track mode:  t,x,y,radius  (or 'lost').
events.py consumes this same observation stream.

Optic-yellow tennis ball defaults are pre-loaded; indoor lighting usually only
needs the V-min slider moved.
"""
import argparse
import json
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np

HSV_FILE = Path(__file__).parent / "ball_hsv.json"
# Orange ping pong ball defaults (OpenCV hue is 0-179).
# Optic-yellow tennis ball: h_lo 25, h_hi 45 — swap back when testing real balls.
DEFAULTS = {"h_lo": 4, "h_hi": 20, "s_lo": 120, "s_hi": 255, "v_lo": 90, "v_hi": 255}
MIN_RADIUS_PX = 5


def load_hsv() -> dict:
    if HSV_FILE.exists():
        return {**DEFAULTS, **json.loads(HSV_FILE.read_text())}
    return dict(DEFAULTS)


def mask_for(frame, p: dict):
    hsv = cv2.cvtColor(cv2.GaussianBlur(frame, (7, 7), 0), cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (p["h_lo"], p["s_lo"], p["v_lo"]), (p["h_hi"], p["s_hi"], p["v_hi"]))
    m = cv2.erode(m, None, iterations=2)
    return cv2.dilate(m, None, iterations=2)


def find_ball(mask):
    """Largest sufficiently-round contour -> (x, y, radius) or None."""
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    for c in cnts:
        (x, y), r = cv2.minEnclosingCircle(c)
        if r < MIN_RADIUS_PX:
            continue
        area = cv2.contourArea(c)
        circularity = area / (np.pi * r * r)  # 1.0 = perfect disc
        if circularity < 0.55:
            continue
        if best is None or r > best[2]:
            best = (x, y, r)
    return best


def tune(cam: int) -> None:
    p = load_hsv()
    cap = cv2.VideoCapture(cam)
    win = "tune (q=quit+save)"
    cv2.namedWindow(win)
    for k in DEFAULTS:
        top = 179 if k.startswith("h") else 255
        cv2.createTrackbar(k, win, p[k], top, lambda v: None)
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        for k in DEFAULTS:
            p[k] = cv2.getTrackbarPos(k, win)
        m = mask_for(frame, p)
        ball = find_ball(m)
        vis = cv2.bitwise_and(frame, frame, mask=m)
        if ball:
            x, y, r = ball
            cv2.circle(vis, (int(x), int(y)), int(r), (0, 255, 0), 2)
        cv2.imshow(win, np.hstack([frame, vis]))
        if (cv2.waitKey(1) & 0xFF) == ord("q"):
            break
    HSV_FILE.write_text(json.dumps(p, indent=2))
    print(f"saved -> {HSV_FILE.name}: {p}")
    cap.release()
    cv2.destroyAllWindows()


def track(cam: int, on_obs=None) -> None:
    """Track ball; call on_obs(t, x, y, r) per detection, on_obs(t, None...) when lost."""
    p = load_hsv()
    cap = cv2.VideoCapture(cam)
    trail: deque = deque(maxlen=48)
    t_start = time.perf_counter()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        t = time.perf_counter() - t_start
        ball = find_ball(mask_for(frame, p))
        if ball:
            x, y, r = ball
            trail.appendleft((int(x), int(y)))
            cv2.circle(frame, (int(x), int(y)), int(r), (0, 255, 0), 2)
            print(f"{t:.3f},{x:.1f},{y:.1f},{r:.1f}")
            if on_obs:
                on_obs(t, x, y, r)
        else:
            print(f"{t:.3f},lost")
            if on_obs:
                on_obs(t, None, None, None)
        for i in range(1, len(trail)):
            cv2.line(frame, trail[i - 1], trail[i], (0, 0, 255),
                     max(1, int(6 * (1 - i / len(trail)))))
        cv2.imshow("track (q=quit c=clear)", frame)
        k = cv2.waitKey(1) & 0xFF
        if k == ord("q"):
            break
        if k == ord("c"):
            trail.clear()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--tune", action="store_true")
    args = ap.parse_args()
    tune(args.cam) if args.tune else track(args.cam)
