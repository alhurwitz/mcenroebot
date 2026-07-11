# Vision Event Pipeline — design

How raw camera pixels become "he shanked it, announce 15–0" — the layer between the USB camera and the MATCH/TRAINING voice modes in VOICE_PLAN.

## Layered architecture

```
camera (USB, Mac now → Pi later)
  │ frames
  ▼
ball_detect.py ──► observations (t, x, y, r)          player_track.py ──► pan error (deg)
  │                                                      │
  ▼                                                      ▼
events.py ──► rally events (LAUNCH, BOUNCE, ...)      pan controller (existing)
  │
  ▼
scorer (state machine over events) ──► point outcomes
  │
  ▼
voice layer (VOICE_PLAN) ──► canned smack talk (fast path) + live TTS (color)
```

Each layer only consumes the layer below, so every piece is testable offline: log a `track.csv` once, replay it through `events.py` forever while tuning.

## Event vocabulary (v1, single fixed camera)

| Event | Detector heuristic | Feeds |
|---|---|---|
| LAUNCH | speed spike > 400 px/s from idle | scoring (rally start), "incoming!" |
| BOUNCE | vy sign flip: falling → rising | scoring, training (bounce location) |
| RETURN_HIT | vx reversal after ≥1 bounce | scoring (player returned), praise/smack |
| DOUBLE_BOUNCE | 2 bounces, no return | point to machine → smack talk |
| BALL_LOST | track gap > 0.5 s mid-rally | ambiguity handler (see below) |

All thresholds are in the CONSTANTS block of `events.py` — image-space px/s, so they change with camera placement and must be re-tuned when the camera moves onto the bot.

## Scoring state machine (next to build, ~50 lines)

Rally outcome per launch: `RETURN_HIT` → player point (or "good return" in training), `DOUBLE_BOUNCE` → machine point, `BALL_LOST` low in frame → probable miss, machine point; `BALL_LOST` high/at frame edge → ball left FOV, no call (announce "too fast for me"). Accumulate into tennis scoring (15/30/40, deuce) for MATCH mode; in TRAINING mode count streaks (returns in a row) instead.

## Smack-talk hook

`events.py` emits JSON lines. The voice layer subscribes and maps event → line bucket: DOUBLE_BOUNCE → insult bucket (canned, instant), RETURN_HIT streak ≥5 → grudging-respect bucket, BALL_LOST → self-deprecation. Latency budget: canned clips fire < 300 ms after the event so the trash talk lands while the miss still stings; live-TTS color commentary can lag a rally.

## Known limits of v1 (accepted for bring-up)

Single camera = no depth: bounce *position* on court is unknown, only that a bounce happened. "In/out" calls need either court-line homography (calibrate.py's intrinsics + 4 clicked court corners → flat-ground homography, doable later) or a second camera. Occlusion by the player reads as BALL_LOST. Machine-end vs player-end direction is baked into the vx sign convention — set once when the camera is mounted.

## Bring-up order (camera on Mac, tonight)

1. `cam_bringup.py --scan` then `--cam N` — confirm device, real FPS. 30 fps is workable for bounce detection; a launched ball at 26 m/s crosses a 60° FOV in a few frames, so LAUNCH detection must trigger on 2–3 observations (it does: MIN_TRACK_PTS=3).
2. `cam_bringup.py --cam N --fov <w> <d>` — measure hFOV (also gates eye-cam placement in the head).
3. `ball_detect.py --tune` — lock HSV for your lighting; then bounce a ball by hand in view.
4. `ball_detect.py --cam N > track.csv` while tossing/bouncing → `events.py --replay track.csv` — check LAUNCH/BOUNCE/RETURN_HIT fire correctly; tune CONSTANTS.
5. `calibrate.py --make-board`, print, `--cam N` — intrinsics for later homography work.
6. `player_track.py` — verify deg-err sign convention matches pan drum direction.
