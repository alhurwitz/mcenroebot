# McEnroe V2 — Implementation Plan

Actionable, wave-by-wave execution plan derived from [`V2_PLAN.md`](V2_PLAN.md). Read V2_PLAN.md first for the design rationale and module specifications; this document is the build checklist.

---

## 0. Snapshot

| Item | Value |
| --- | --- |
| Working directory | `/Users/alberthurwitz/Projects/mcenroebot` |
| Package | `src/mcenroebot/` (src-layout) |
| Tests | `tests/` |
| Python | ≥3.13 (per `pyproject.toml`; Pi/Bookworm 3.11 target not yet reconciled) |
| Dep manager | `uv` (never hand-edit `pyproject.toml` deps) |
| Coverage floor | 85% (aim ≥95% on pure-math modules) |
| Current branch | `feature/v2-control` |
| Done | **All four waves complete.** `aim/`, `clock/`, `camera/`, `ball/`, `drivers/{servo,bldc}/`, `predictor/`, `swing/`, `calibrate/`, `coordinator/` packages all landed. **343 tests pass**, 6 correctly skipped (pi-only), 94%+ project coverage |
| Next | Open PR `feature/v2-control` → `develop`; Pi deployment after merge |
| Structure | Each component is a **package** under `src/mcenroebot/<name>/` (`__init__.py`, split files by responsibility); tests mirror at `tests/test_<name>/test_<concern>.py` |

### Module dependency graph

```
                 ┌──────────────┐
                 │   clock.py   │  (no deps)
                 └──────┬───────┘
                        │
              ┌─────────┴──────────┐
              ▼                    ▼
       ┌────────────┐       ┌─────────────┐
       │   ball.py  │◄──────│  camera.py  │
       └─────┬──────┘       └─────────────┘
             │
             ▼
     ┌────────────────┐    ┌──────────────────┐
     │ predictor.py   │    │ drivers/servo.py │
     └───────┬────────┘    │ drivers/bldc.py  │
             │             └────────┬─────────┘
             │                      │
             │     ┌────────────────┤
             │     ▼                ▼
             │  ┌──────────┐   ┌──────────────┐
             │  │ swing.py │   │ calibrate.py │
             │  └─────┬────┘   └──────────────┘
             │        │
             ▼        ▼
        ┌──────────────────┐    ┌────────────┐
        │  coordinator.py  │───►│   aim.py   │ (already exists)
        └──────────────────┘    └────────────┘
```

---

## 1. Wave 0 — verify the pydantic refactor (✅ done)

The pydantic v2 migration of `aim.py` and `tests/test_aim.py` is committed (`632a8e9`). Before starting Wave 1, run the gates once:

```bash
uv sync
uv run pytest -q          # all 30 tests pass, coverage ≥85%
uv run mypy src/          # clean under strict
uv run ruff check src/    # clean
```

---

## 2. Wave 1 — foundation modules (sequential, with subagent review)

Each module is a **package** under `src/mcenroebot/<name>/` (`__init__.py` + split files), tested via mirror layout under `tests/test_<name>/`.

| # | Package | Status | Public surface | Tests required |
| --- | --- | --- | --- | --- |
| 1A | `aim/` | ✅ done (`56950c4`) | `AimController`, `Position3D`, `ServoAngles`, `TurretGeometry` split into `value_objects.py` + `controller.py` | n/a — already covered |
| 1B | `clock/` | ✅ done (`56950c4`) | `Clock(Protocol)`, `SystemClock`, `FakeClock` split into `protocol.py`, `system.py`, `fake.py` | Protocol compliance; monotonicity; `FakeClock.sleep` non-blocking; `SystemClock.sleep` real-time; negative durations raise `ValueError` |
| 1C | `camera/` | ✅ done (`3698c8c`) | `CameraIntrinsics` + `pixel_to_ray(u, v)` in `intrinsics.py` | Round-trip a known projection; default distortion is zero; `ValidationError` on negative focal length |
| 1D | `ball/` | ✅ done (`9b305d5`) | `BallObservation`, `BallState`, `StrikePrediction`, `PixelObservation` in `value_objects.py`; `DepthEstimator(Protocol)`, `BallRadiusDepthEstimator`, stubs in `depth.py` | Round-trip known geometry through `BallRadiusDepthEstimator`; frozen-ness of all models; `confidence` ∈ `[0, 1]`; `ValidationError` on negative `radius_px` |
| 1E | `drivers/servo/`, `drivers/bldc/` | ✅ done (`b9a9fb0` deps, `547c1be` code) | `ServoDriver(Protocol)` + `PCA9685ServoDriver` (lazy `adafruit_servokit` import) + `MockServoDriver`; `BLDCDriver(Protocol)` + `PCA9685BLDCDriver` (throttle 0→1000 µs, 1→2000 µs) + `MockBLDCDriver` | Mock drivers record calls in order; real driver doesn't require Adafruit libs at import-time; real-driver smoke tests are `@pytest.mark.integration` and skipped off-Pi; throttle outside `[0, 1]` rejected; `set_throttle` pre-arm raises `RuntimeError` |

**Commits** (one per package):
```
feat(camera): add pinhole CameraIntrinsics model
feat(ball): add BallObservation, BallState, StrikePrediction, DepthEstimator
chore(deps): add pi optional extra (adafruit blinka + pca9685 + servokit)
feat(drivers): add ServoDriver + BLDCDriver protocols, real + mock impls
```

Pi-only dependencies (`adafruit-blinka`, `adafruit-circuitpython-pca9685`, `adafruit-circuitpython-servokit`) live in `[project.optional-dependencies] pi = [...]` added via `uv add --optional pi <pkg>`. Real drivers import Adafruit libs **lazily inside `__init__`** so the package still imports cleanly on a Mac without the extra installed.

### End-of-Wave-1 housekeeping

1. `uv run pytest`, `uv run mypy src/`, `uv run ruff check src/` — all green.
2. Merge to `develop`:
   ```bash
   git checkout develop
   git merge --no-ff feature/aim
   git push origin develop
   ```
3. Cut the next feature branch:
   ```bash
   git checkout -b feature/v2-control
   ```

---

## 3. Wave 2 — modules that depend on Wave 1 (all ✅ done)

| # | Package | Status | Notes |
| --- | --- | --- | --- |
| 2A | `predictor/` | ✅ done (`a8a0c4e`) | `TrajectoryPredictor` with per-axis weighted least-squares fit (gravity on RHS for Z), exponential-decay weighting, confidence ∈ [0, 1], 47 tests covering recovery, gating, moving-away, weighting bias |
| 2B | `swing/` | ✅ done (`95d1381`) | `SwingProfile` (frozen, validated bounds) + `SwingController` (async context manager, lazy arm, tick-cadence envelope sampling, always ends at throttle 0, disarms on exit even when fire raises) |
| 2C | `calibrate/` | ✅ done (`0847c39`) | `EscCalibrator` one-shot routine: prompt → set_throttle(1.0) → prompt → settle → set_throttle(0.0) → prompt → settle → disarm; try/finally guarantees disarm on KeyboardInterrupt |

---

## 4. Wave 3 — integration (✅ done)

| # | Package | Status | Notes |
| --- | --- | --- | --- |
| 3 | `coordinator/` | ✅ done (`2f3ba26`) | `RallyCoordinator` wires `observations → TrajectoryPredictor → AimController → ServoDriver → SwingController`. Lazy swing arming on first reachable strike prediction. `rearm_min_interval_s` enforces one-fire-per-arc. 18 integration tests with mocks + `FakeClock`. |

### Final gates (all green)

```bash
uv run pytest          # 343 passed, 6 skipped (pi-only), 94%+ project coverage
```

Pre-commit hooks (ruff, ruff-format, mypy strict, detect-secrets, commitizen, pytest) pass on every commit.

Open PR `feature/v2-control` → `develop`.

---

## 5. Pi deployment (post-Wave 3)

1. SSH/SFTP repo to `~/mcenroebot/` on the Pi.
2. `uv sync --extra pi`
3. Wire hardware: PCA9685 HAT at I2C `0x40`, servos on ch0/ch1, ESC signal on ch2, 3S LiPo to BLDC, HAT 5V/3A PSU to servos.
4. `uv run python -m mcenroebot.calibrate` once to arm the ESC.
5. Run the coordinator against the live webcam feed.

---

## 6. Open questions / risks

These are flagged in `V2_PLAN.md §8`; they must be resolved before the system runs end-to-end:

- **Camera intrinsics are unknown.** `BallRadiusDepthEstimator` needs real `CameraIntrinsics`. Plan: add `scripts/calibrate_camera.py` (OpenCV checkerboard) during Wave 1 — or, at minimum, ship a placeholder intrinsics object in the demo and document the calibration step.
- **Strike plane location.** Defaults to `x = arm_length_m` (0.20 m forward). Confirm against the physical mount once the turret is assembled.
- **Swing latency** (`swing_latency_s = 0.05` s) is a guess. First hardware-in-loop test must measure actual mechanical latency and update the default.
- **Audio / trash-talk** is out of scope for V2. `RallyCoordinator` should expose a hook for a future `audio.py`.
