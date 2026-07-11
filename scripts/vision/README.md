# vision/ — USB camera CV toolkit (Mac bring-up)

**Overlap with existing repo code:** `calibrate.py` here duplicates `scripts/calibrate_camera.py`
(the repo one is more thorough — capture/solve split, feeds `camera.intrinsics.CameraIntrinsics`;
use it with `--board 9x6 --square-mm 20` for this folder's checkerboard.pdf, which prints at
20mm squares, not the 25mm default). `player_track.py` is a richer alternative to
`player/blob.py` (pose vs blob), same error-signal concept. Genuinely new: `ball_detect.py`,
`events.py` (rally event detection — see EVENT_PIPELINE.md), `cam_bringup.py` (FPS/FOV quick-look).

Setup:
```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
macOS will prompt for camera permission for Terminal on first run — allow it.

Run order (details in EVENT_PIPELINE.md):

1. `python3 cam_bringup.py --scan` → find the USB camera's index (built-in FaceTime cam is usually 0)
2. `python3 cam_bringup.py --cam N --fov 21.6 200` → live preview, FPS, FOV measure (example: letter paper 21.6cm wide, 200cm away; click its left then right edge) → writes `camera_profile.json`
3. `python3 ball_detect.py --cam N --tune` → HSV sliders until only the ball shows → writes `ball_hsv.json`
4. `python3 ball_detect.py --cam N > track.csv` → track a hand-tossed ball
5. `python3 events.py --replay track.csv` → see LAUNCH/BOUNCE/RETURN_HIT events; or `--cam N` for live
6. `python3 calibrate.py --make-board` → print `checkerboard.png` at 100%, then `--cam N` → intrinsics
7. `python3 player_track.py --cam N` → pan-error signal in degrees (uses FOV from step 2)

Generated files (`camera_profile.json`, `ball_hsv.json`, `camera_intrinsics.json`) are consumed by the later scripts — keep them next to the code.

All scripts are Pi-portable later; only cv2.imshow preview windows would need swapping for headless output.
