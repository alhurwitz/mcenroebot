#!/usr/bin/env python3
"""Player tracking -> pan error signal for base aiming.

Usage:
  python3 player_track.py --cam 0
  python3 player_track.py --cam 0 --hog     # force HOG fallback (no mediapipe)

Uses MediaPipe Pose if installed (pip install mediapipe), else OpenCV HOG
person detector. Prints one line per frame:

  t,px_err,deg_err        px_err = person center - frame center (pixels)
                          deg_err uses hfov_deg from camera_profile.json
                          (run cam_bringup.py --fov first, else assumes 60)

deg_err is exactly what the pan drum needs: positive = person is to the
right, pan right. Keys: q=quit
"""

import argparse
import json
import time
from pathlib import Path

import cv2

PROFILE = Path(__file__).parent / "camera_profile.json"


def get_hfov() -> float:
    if PROFILE.exists():
        hfov = json.loads(PROFILE.read_text()).get("hfov_deg")
        if hfov:
            return hfov
    print(
        "warning: no hfov_deg in camera_profile.json — assuming 60 deg. "
        "Run cam_bringup.py --fov to measure."
    )
    return 60.0


class MediaPipeDetector:
    def __init__(self):
        import mediapipe as mp  # noqa: import here so HOG path works without it

        self.pose = mp.solutions.pose.Pose(model_complexity=0)  # 0 = fastest

    def detect(self, frame):
        """Return (cx, cy, label) of torso center, or None."""
        h, w = frame.shape[:2]
        res = self.pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if not res.pose_landmarks:
            return None
        lm = res.pose_landmarks.landmark
        # torso = mean of shoulders + hips (indices 11,12,23,24)
        pts = [lm[i] for i in (11, 12, 23, 24)]
        cx = sum(p.x for p in pts) / 4 * w
        cy = sum(p.y for p in pts) / 4 * h
        return cx, cy, "pose"


class HogDetector:
    def __init__(self):
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def detect(self, frame):
        # HOG is slow at full res; detect on a half-size copy
        small = cv2.resize(frame, None, fx=0.5, fy=0.5)
        rects, weights = self.hog.detectMultiScale(small, winStride=(8, 8))
        if len(rects) == 0:
            return None
        best = max(zip(rects, weights), key=lambda rw: rw[1])[0]
        x, y, w, h = (v * 2 for v in best)
        return x + w / 2, y + h / 2, "hog"


def main(cam: int, force_hog: bool) -> None:
    if force_hog:
        det = HogDetector()
    else:
        try:
            det = MediaPipeDetector()
        except ImportError:
            print("mediapipe not installed (pip install mediapipe) — using HOG fallback")
            det = HogDetector()

    hfov = get_hfov()
    cap = cv2.VideoCapture(cam)
    t_start = time.perf_counter()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        t = time.perf_counter() - t_start
        h, w = frame.shape[:2]
        hit = det.detect(frame)
        if hit:
            cx, cy, label = hit
            px_err = cx - w / 2
            deg_err = px_err / w * hfov
            print(f"{t:.3f},{px_err:+.0f},{deg_err:+.2f}")
            cv2.drawMarker(frame, (int(cx), int(cy)), (0, 255, 0), cv2.MARKER_CROSS, 30, 2)
            cv2.putText(
                frame,
                f"pan err {deg_err:+.1f} deg ({label})",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )
        else:
            print(f"{t:.3f},lost")
            cv2.putText(frame, "no player", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.line(frame, (w // 2, 0), (w // 2, h), (255, 255, 0), 1)
        cv2.imshow("player track (q=quit)", frame)
        if (cv2.waitKey(1) & 0xFF) == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--hog", action="store_true")
    args = ap.parse_args()
    main(args.cam, args.hog)
