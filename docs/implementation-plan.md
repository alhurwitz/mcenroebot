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
| Done | `aim.py` + 30 tests, pydantic v2 refactor (committed `632a8e9`) |
| Next | Wave 1 — clock / ball / camera / drivers |

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

## 2. Wave 1 — foundation modules (parallelizable, 2 streams)

Two agents can work in parallel. Stream B introduces the `pi` optional-dependency group.

### Stream A — pure-Python value objects and helpers

| Module | Public surface | Tests required |
| --- | --- | --- |
| `clock.py` | `Clock(Protocol)`, `SystemClock`, `FakeClock` (`now()`, `async sleep()`, `.advance()`, `.elapsed`) | Monotonicity; `FakeClock.sleep` advances internal time without blocking; `SystemClock.sleep` actually awaits (small timeout + measurement) |
| `ball.py` | `BallObservation`, `BallState`, `StrikePrediction`, `PixelObservation` (all `BaseModel`, frozen); `DepthEstimator(Protocol)`, `BallRadiusDepthEstimator`; stubs `StereoDepthEstimator` and `RealSenseDepthEstimator` raising `NotImplementedError` | Round-trip known geometry through `BallRadiusDepthEstimator`; frozen-ness of all models; `confidence` ∈ `[0, 1]`; `ValidationError` on negative `radius_px` |
| `camera.py` | `CameraIntrinsics` (`fx_px`, `fy_px`, `cx_px`, `cy_px`, `distortion`, `image_width`, `image_height`) + `pixel_to_ray(u, v)` helper | Round-trip a known projection; default distortion is zero; `ValidationError` on negative focal length |

**Commits**
```
feat(clock): add Clock protocol, SystemClock, FakeClock
feat(ball): add BallObservation, BallState, StrikePrediction, DepthEstimator
feat(camera): add pinhole CameraIntrinsics model
```

### Stream B — hardware drivers + `pi` optional extra

1. Add `[project.optional-dependencies] pi = [...]` to `pyproject.toml` (via `uv add --optional pi <pkg>`):
   - `adafruit-blinka`
   - `adafruit-circuitpython-pca9685`
   - `adafruit-circuitpython-servokit`
2. Create `src/mcenroebot/drivers/__init__.py` (empty re-export package).

| Module | Public surface | Tests required |
| --- | --- | --- |
| `drivers/servo.py` | `ServoDriver(Protocol)` with `write_angle(channel, angle_deg)`; `PCA9685ServoDriver(i2c_address=0x40, frequency_hz=50)` with **lazy** `adafruit_servokit` import inside `__init__`; `MockServoDriver` exposing `history: list[tuple[int, float]]` | `MockServoDriver` records calls in order; importing `PCA9685ServoDriver` does **not** require Adafruit libs at module import time; a real-driver smoke test is marked `@pytest.mark.integration` and skipped off-Pi |
| `drivers/bldc.py` | `BLDCDriver(Protocol)` with `arm()`, `set_throttle(0..1)`, `disarm()`; `PCA9685BLDCDriver(channel=2, i2c_address=0x40, frequency_hz=50)` mapping throttle 0→1000 µs, 1→2000 µs; `MockBLDCDriver` with `armed: bool` and `throttle_history: list[float]` | Throttle outside `[0, 1]` raises (`ValidationError` if pydantic-modeled, else `ValueError`); `set_throttle` before `arm()` raises `RuntimeError`; `disarm()` zeros throttle |

**Commits**
```
chore(deps): add pi optional extra (adafruit blinka + pca9685 + servokit)
feat(drivers): add ServoDriver + BLDCDriver protocols, real + mock impls
```

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
