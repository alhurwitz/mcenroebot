# V4 Feeder — Hardware Bring-Up Checklist

The software (Waves 0–6) is complete and verified off-Pi. This checklist is the **operator
runbook** for the two remaining phase gates, which require the Raspberry Pi and the assembled
machine. Work top-to-bottom; do not skip the de-risk steps.

Design source of truth: [`docs/superpowers/specs/2026-06-23-feeder-design.md`](superpowers/specs/2026-06-23-feeder-design.md).
Mechanism/BOM: [`docs/V4_PLAN.md`](V4_PLAN.md).

> **SAFETY (read first).** Launch wheels throw 40 mm balls hard — clear the room and wear eye
> protection. The escapement disk and auger pinch — keep fingers clear. Bench-test the escapement
> and auger as standalone subassemblies *before* committing to a frame (`V4_PLAN.md §3`).

---

## 0. Mechanical de-risk (before any software)

- [ ] Print + bench-test the **escapement** disk/hopper standalone — single-ball metering, no jam.
- [ ] Print + bench-test the **auger** standalone — balls ride up, no fallback, joints sanded flush.
- [ ] Mount the **catch net** (bought, not built) feeding the trough → auger mouth.

## 1. Pi setup

- [ ] `uv sync --extra pi` on the Pi (installs `adafruit-blinka`, `-pca9685`, `-servokit`, `RPi.GPIO`).
- [ ] Confirm I2C is enabled and the PCA9685 responds at `0x40` (`i2cdetect -y 1`).
- [ ] Provision the uv-managed Python 3.13 interpreter on the Pi (dev + deploy both run 3.13, not Bookworm's system 3.11); `pyproject.toml` still declares `>=3.11`.

## 2. Wiring + channel map

Confirm the channel assignment **and the shared-ground / power budget for two ESCs** before
powering on (spec §9). Planned map (also in `CLAUDE.md`):

| Ch | Actuator | Driver |
|---|---|---|
| 0 | pan servo (yaw) | `drivers/servo` |
| 1 | tilt servo (pitch) | `drivers/servo` |
| 2 | head-roll servo | `drivers/servo` |
| 3 | top wheel ESC | `drivers/bldc` |
| 4 | bottom wheel ESC | `drivers/bldc` |
| 5 | escapement CR servo | `drivers/feeder` |
| 6 | auger MOSFET PWM | `drivers/lift` |

- [ ] Hopper-full endstop (optional) on a BCM GPIO pin → `drivers/lift.GpioHopperSensor`.

## 3. Wave 5 — calibration + first live feed

- [ ] **Arm both ESCs**, once per wheel: `mcenroebot.calibrate.EscCalibrator` (or `scripts/esc_arm.py`).
- [ ] **Feeder factor:**
      `uv run scripts/calibrate_feeder.py --channel 5 --seconds 60`
      → paste `throttle_per_bpm` into `Pca9685FeederDriver(channel=5, throttle_per_bpm=…)`.
- [ ] **Launch constants** (measure no-load full-throttle rpm first, via tach/slow-mo):
      `uv run scripts/calibrate_launch.py --top-channel 3 --bottom-channel 4 --max-wheel-rpm <measured> --out launch_geometry.json`
      → load with `LaunchGeometry.model_validate_json(Path("launch_geometry.json").read_text())`.
- [ ] **First feed:** run `FeederCoordinator` with a `FixedPatternStrategy("static")` drill at low rpm,
      one fixed target. Wire the calibrated `LaunchGeometry` + `ThrottleMap` + the real drivers.

**Phase gate (Wave 5):** 20 consecutive balls to a chosen spot at controlled speed, no jam /
double-feed; auger keeps the hopper non-empty over a 5-minute run. 🍾

## 4. Wave 6 — vision placement (optional, after Wave 5 is solid)

- [ ] Mount the webcam (`/dev/video0`), confirm a frame source feeds `SimpleBlobDetector`.
- [ ] Tune `SimpleBlobDetector(half_width_m, threshold, min_area_frac)` against the real backdrop.
- [ ] Swap `VisionPlacementStrategy` in for the fixed pattern (inject detector + frame source +
      a fixed-pattern fallback). No other coordinator/launch changes are needed.

**Phase gate (Wave 6):** with the player standing left, ≥80% of balls land right of center (and
vice versa), at recreational pace.

## 5. Integrate

- [ ] After the Wave 5 gate passes, merge `feature/v4-feeder` → `develop`
      (the spec gates this merge on Wave 5; vision is a clean follow-up).

---

### Tuning notes carried from the spec (§9)

- ESC throttle→rpm is nonlinear under load; if launch speed is inconsistent, upgrade
  `calibrate_launch.py` to a 2nd-order / lookup curve instead of the linear `ThrottleMap`.
- If per-shot timing matters for vision sync, add the index endstop (`V4_PLAN.md §1`) and
  implement `FeederDriver.fire()` for a real `ball_fired` event (set `use_index_feeder=True`).
