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
| Current branch | `feature/aim` |
| Done | Wave 1 complete: `aim/`, `clock/`, `camera/`, `ball/`, `drivers/{servo,bldc}/` packages all landed; 237 tests pass, 6 correctly skipped (pi-only), 99%+ coverage |
| Next | Wave 1 close — merge `feature/aim` → `develop`, cut `feature/v2-control`, then Wave 2 (predictor / swing / calibrate) |
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

## 3. Wave 2 — modules that depend on Wave 1 (parallelizable, 3 streams)

### Stream A — `predictor.py` (depends on `ball.py`)

`TrajectoryPredictor`:
- Rolling buffer (`buffer_size=16` default) of `BallObservation`.
- Fits a 3D ballistic trajectory: constant velocity X, Y; gravity (`-g`) on Z. Weighted least squares with exponential decay (`weight_halflife_s=0.1` default).
- `add(obs)`, `current_state() -> BallState | None`, `predict_strike(strike_plane_x) -> StrikePrediction | None`.
- Constructor: `buffer_size: int = 16`, `gravity_mps2: float = 9.81`, `weight_halflife_s: float = 0.1`, `min_observations: int = 3`.

**Tests**
- Synthetic ballistic trajectory recovers state within tolerance.
- Fewer than `min_observations` returns `None`.
- Ball moving away from strike plane returns `None`.
- `confidence` increases with observation count, decreases with residual error.
- Old-noisy + new-clean observations bias toward new (weighting works).

**Commit:** `feat(predictor): add TrajectoryPredictor with weighted ballistic fit`

### Stream B — `swing.py` (depends on `drivers/bldc.py`, `clock.py`)

`SwingProfile` (frozen `BaseModel`):
- `ramp_up_ms: float = Field(gt=0)`
- `hold_ms: float = Field(ge=0)`
- `ramp_down_ms: float = Field(gt=0)`
- `peak_throttle: float = Field(gt=0.0, le=1.0)`
- `total_ms` property.

`SwingController`:
- `__init__(driver: BLDCDriver, clock: Clock)`.
- `async __aenter__` / `async __aexit__` — disarms on exit even if `fire` raises.
- `arm()`, `async fire(profile)`.

**Tests** (with `MockBLDCDriver` + `FakeClock`)
- `fire` without `arm` raises `RuntimeError`.
- `throttle_history` matches profile shape within tolerance (sample at N points).
- Total elapsed `FakeClock` time matches `profile.total_ms`.
- Context exit disarms even when `fire` raises.

**Commit:** `feat(swing): add SwingController + SwingProfile open-loop control`

### Stream C — `calibrate.py` (depends on `drivers/bldc.py`, `clock.py`)

`EscCalibrator`:
- `__init__(driver, clock, prompt_fn=input)`.
- `async run()` sequence: power-off prompt → `set_throttle(1.0)` → power-on prompt → wait for beeps → `set_throttle(0.0)` → wait for beeps → `disarm()`.

**Tests** (with `MockBLDCDriver`, `FakeClock`, and a recording `prompt_fn`)
- Throttle sequence is `[1.0, 0.0]` then `disarm` in that order.
- Prompts appear between the correct throttle steps.

**Commit:** `feat(calibrate): add EscCalibrator one-shot routine`

---

## 4. Wave 3 — integration (single stream)

### `coordinator.py`

`RallyCoordinator` wires `observations → TrajectoryPredictor → AimController → SwingController`.

Constructor:
- `aim: AimController`
- `predictor: TrajectoryPredictor`
- `servo_driver: ServoDriver`
- `swing: SwingController`
- `clock: Clock`
- `strike_plane_x: float = 0.0`
- `swing_latency_s: float = 0.05`
- `servo_yaw_channel: int = 0`
- `servo_pitch_channel: int = 1`

Methods:
- `async step(obs: BallObservation)` — push obs, update aim, decide whether to fire.
- `async run(stream: AsyncIterator[BallObservation])` — pull loop calling `step`.

**Integration tests** (all mocks + `FakeClock`)
- Synthetic ballistic stream → servos receive aim updates → swing fires exactly once at `impact_time - swing_latency_s`.
- Unreachable aim target: aim returns `None`; no swing.
- Buffer below `min_observations`: no swing.
- One swing per "pass" — strike does not retrigger on subsequent observations of the same arc.

**Commit:** `feat(coordinator): wire predictor → aim → swing in RallyCoordinator`

### Final gates

```bash
uv run pytest          # full suite green, coverage ≥85%
uv run mypy src/       # strict clean
uv run ruff check src/ # clean
```

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
