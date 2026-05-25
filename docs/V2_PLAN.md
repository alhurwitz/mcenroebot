# McEnroe V2 — Turret Control Software Build Plan

Paste this entire file into a fresh Claude Code session in `/Users/alberthurwitz/Projects/mcenroebot`. It is self-contained.

---

## 0. Context

**Project:** McEnroe is a hobby ping-pong robot. V2 is the aim-and-swat phase: a 3-axis turret with two MG996R servos (J1 yaw, J2 pitch) for aiming, and an A2212 1000 KV brushless motor driven by an ESC (J3) for the open-loop paddle swing.

**Hardware:**
- Raspberry Pi 4 (Bookworm, Python 3.11) is the deploy target
- Adafruit-style 16-channel PCA9685 PWM HAT at I2C `0x40` — pan=ch0, tilt=ch1, BLDC ESC=ch2 (proposed)
- Single Logitech webcam at `/dev/video0` (2D — depth recovered from ball-radius monocular estimation)
- 3S LiPo for the BLDC; servos run off the HAT's screw terminal 5V/3A PSU

**Coordinate system (used everywhere):**
- Origin: J1 yaw axis at J2 pitch pivot height
- +X forward (toward the ball)
- +Y left (viewed from above)
- +Z up
- Units: meters internally, degrees for servo I/O, seconds for time

**Repo layout:**
- Working directory: `/Users/alberthurwitz/Projects/mcenroebot`
- Source: `src/mcenroebot/`
- Tests: `tests/`
- Python ≥3.10, pyproject already configured (ruff, mypy strict, pytest, ≥85% coverage floor, `pydantic.mypy` plugin)
- `uv` for deps — never edit `pyproject.toml` deps by hand, use `uv add`

## 1. Coding standards (mandatory)

- **OOP everywhere.** Public surface is classes. No bare module-level functions in the public API (private `_demo()` etc. are fine).
- **Pydantic v2** for every value object — `class Foo(BaseModel)` with `model_config = ConfigDict(frozen=True)`. Use `@field_validator` for range checks, not `__post_init__`. **Do not use `@dataclass`.**
- **Pydantic constructor calls are keyword-only** — write `Position3D(x=0.1, y=0.0, z=0.0)`, not `Position3D(0.1, 0.0, 0.0)`.
- **Type hints everywhere.** mypy strict must pass.
- **pytest** in `tests/test_<module>.py`. Cover happy paths and edge cases. Parametrize when useful. Use `pytest-asyncio` (already configured, `asyncio_mode = "auto"`) for async tests.
- **Coverage ≥85%** is enforced by `[tool.coverage.report] fail_under = 85`. Aim higher (≥95%) on pure-math modules.
- **Hardware abstraction:** every GPIO-touching driver has a `Protocol` interface and a `Mock<Name>Driver` implementation. The control loop is tested against mocks; the real drivers are only exercised on the Pi.
- **Pi-only deps go in an optional extra** so laptop dev/tests don't need them:
  ```toml
  [project.optional-dependencies]
  pi = [
      "adafruit-blinka",
      "adafruit-circuitpython-pca9685",
      "adafruit-circuitpython-servokit",
  ]
  ```
  Install on the Pi with `uv sync --extra pi`. In real drivers, do the Adafruit imports lazily inside `__init__` so importing the package on a Mac doesn't blow up.

## 2. Gitflow

- Branches: `main` / `develop` / `feature/*`
- Conventional commits (`feat:`, `fix:`, `refactor:`, `test:`, `chore:`, `docs:`)
- Current state: `feature/aim` is ahead of `develop` with the aim module
- Strategy (Option A — chosen): finish the aim pydantic refactor on `feature/aim`, merge to `develop` once, then cut `feature/v2-control` for the rest

## 3. Status as of handoff

**Already done on `feature/aim` (committed):**
- `src/mcenroebot/aim.py` — `AimController`, `Position3D`, `ServoAngles`, `TurretGeometry`
- `tests/test_aim.py` — 34 test cases
- `pyproject.toml` — strict mypy, ruff, pytest config, ≥85% coverage floor
- `pydantic >= 2.13.4` added as dep (commit `1a800bb`)

**Uncommitted on `feature/aim` (refactor in flight):**
- `src/mcenroebot/aim.py` — rewritten to use `pydantic.BaseModel` + `ConfigDict(frozen=True)` + `@field_validator`
- `tests/test_aim.py` — `Position3D(...)` call sites updated to keyword args; `pytest.raises(ValueError, ...)` for ServoAngles range check changed to `pytest.raises(ValidationError, ...)`; `pytest.raises(Exception)` mutation tests tightened to `pytest.raises(ValidationError)`

**What Claude Code needs to do FIRST (Wave 0):**
1. `uv sync` (refresh the venv if needed)
2. `uv run pytest -q` — all 34 tests should pass, coverage should stay above 85%
3. `uv run mypy src/` — should pass clean under strict
4. `uv run ruff check src/` — should pass clean
5. If any of (2–4) fail, fix before proceeding. Most likely surprise: pydantic v2 `ValidationInfo` import path or `field_validator` signature.
6. Commit: `git add -A && git commit -m "refactor(aim): migrate value objects to pydantic v2"`

## 4. Module specifications

All new modules live under `src/mcenroebot/`. Each has a matching `tests/test_<module>.py` with parametrized happy-path + edge-case coverage.

### 4.1 `clock.py`

Tiny module for testable timing.

```python
from typing import Protocol

class Clock(Protocol):
    def now(self) -> float: ...               # seconds since epoch (monotonic-ish)
    async def sleep(self, seconds: float) -> None: ...

class SystemClock:
    """Real wall-clock + asyncio.sleep."""

class FakeClock:
    """Deterministic clock for tests.
    - now() returns the internal time
    - sleep(s) advances the internal time by s, does NOT actually sleep
    - exposes .advance(seconds) and .elapsed for assertions
    """
```

Tests: monotonicity, sleep advances FakeClock, SystemClock.sleep actually awaits (use a small timeout + measure).

### 4.2 `ball.py`

Value objects + the depth-estimation abstraction.

```python
from pydantic import BaseModel, ConfigDict, field_validator

class BallObservation(BaseModel):
    """One sample from the tracker, in robot frame."""
    model_config = ConfigDict(frozen=True)
    t: float           # seconds
    x: float
    y: float
    z: float

class BallState(BaseModel):
    """Estimated position + velocity at a given time."""
    model_config = ConfigDict(frozen=True)
    t: float
    position: Position3D     # reuse from aim.py
    velocity: Position3D     # m/s, same coordinate frame

class StrikePrediction(BaseModel):
    model_config = ConfigDict(frozen=True)
    impact_point: Position3D
    impact_time: float        # seconds (absolute, same clock as observations)
    confidence: float = Field(ge=0.0, le=1.0)
```

Then the depth-estimation protocol:

```python
class PixelObservation(BaseModel):
    model_config = ConfigDict(frozen=True)
    t: float
    u_px: float               # image x
    v_px: float               # image y
    radius_px: float          # apparent ball radius

class DepthEstimator(Protocol):
    def estimate(self, obs: PixelObservation) -> BallObservation: ...

class BallRadiusDepthEstimator:
    """Monocular depth from apparent ball size.
        depth = (real_radius * focal_length_px) / pixel_radius
    Requires camera intrinsics (see camera.py).
    """
    def __init__(self, intrinsics: CameraIntrinsics, ball_radius_m: float = 0.020): ...
    def estimate(self, obs: PixelObservation) -> BallObservation: ...

# Stubs for future implementations (raise NotImplementedError):
class StereoDepthEstimator: ...
class RealSenseDepthEstimator: ...
```

Tests: known-good geometry round-trips through `BallRadiusDepthEstimator`; frozen-ness of all models; confidence bounds enforced by validator; ValidationError on negative radius_px.

### 4.3 `camera.py`

```python
class CameraIntrinsics(BaseModel):
    """Pinhole camera model. Fill from cv2.calibrateCamera output."""
    model_config = ConfigDict(frozen=True)
    fx_px: float
    fy_px: float
    cx_px: float
    cy_px: float
    distortion: tuple[float, float, float, float, float] = (0.0,) * 5
    image_width: int
    image_height: int

    # Helper: pixel → normalized camera ray (for ground-plane intersection later).
    def pixel_to_ray(self, u: float, v: float) -> tuple[float, float, float]: ...
```

Tests: round-trip a known projection; default distortion is zero; ValidationError on negative focal length.

### 4.4 `drivers/servo.py`

```python
class ServoDriver(Protocol):
    def write_angle(self, channel: int, angle_deg: float) -> None: ...

class PCA9685ServoDriver:
    """Real driver. Lazily imports adafruit_servokit on first use.
    Maps angle [0, 180] → PWM duty per servo's pulse_width_min/max.
    """
    def __init__(self, i2c_address: int = 0x40, frequency_hz: int = 50): ...

class MockServoDriver:
    """Records every write for assertions in tests."""
    @property
    def history(self) -> list[tuple[int, float]]: ...
```

Tests: MockServoDriver records calls in order; PCA9685ServoDriver raises a clear error if Adafruit libs aren't installed (skip the import-success test unless on Pi, mark it `@pytest.mark.integration`).

### 4.5 `drivers/bldc.py`

```python
class BLDCDriver(Protocol):
    def arm(self) -> None: ...
    def set_throttle(self, throttle: float) -> None: ...   # 0.0 .. 1.0
    def disarm(self) -> None: ...

class PCA9685BLDCDriver:
    """1000–2000 µs ESC PWM. Throttle 0 → 1000 µs, 1 → 2000 µs."""
    def __init__(self, channel: int = 2, i2c_address: int = 0x40, frequency_hz: int = 50): ...

class MockBLDCDriver:
    @property
    def armed(self) -> bool: ...
    @property
    def throttle_history(self) -> list[float]: ...
```

Tests: throttle outside [0, 1] raises; set_throttle before arm() raises; disarm zeros throttle.

### 4.6 `predictor.py`

```python
class TrajectoryPredictor:
    """Maintains a rolling buffer of BallObservations and fits a 3D
    ballistic trajectory: constant velocity in X, Y; gravity (-g) in Z.

    fit() uses weighted least squares. Recent observations weighted higher
    via exponential decay (configurable half-life).

    predict_strike(strike_plane_x) returns the (y, z, t) where the ball
    crosses x = strike_plane_x, or None if the ball is moving away.
    """
    def __init__(self, buffer_size: int = 16, gravity_mps2: float = 9.81,
                 weight_halflife_s: float = 0.1, min_observations: int = 3): ...
    def add(self, obs: BallObservation) -> None: ...
    def current_state(self) -> BallState | None: ...
    def predict_strike(self, strike_plane_x: float) -> StrikePrediction | None: ...
```

Tests:
- Synthetic ballistic trajectory recovers correct state to within tolerance
- Fewer than `min_observations` returns None
- Ball moving away from strike plane returns None
- Confidence increases with observation count; decreases with residual error
- Weights work: noisy old + clean new observations bias toward new

### 4.7 `swing.py`

```python
class SwingProfile(BaseModel):
    """Open-loop throttle envelope for one swing."""
    model_config = ConfigDict(frozen=True)
    ramp_up_ms: float = Field(gt=0)
    hold_ms: float = Field(ge=0)
    ramp_down_ms: float = Field(gt=0)
    peak_throttle: float = Field(gt=0.0, le=1.0)

    @property
    def total_ms(self) -> float: ...

class SwingController:
    """Drives the BLDC through a SwingProfile open-loop. No encoder feedback.
    Safety: refuses to fire if not armed. Auto-zeros throttle on context exit.
    """
    def __init__(self, driver: BLDCDriver, clock: Clock): ...
    async def __aenter__(self) -> SwingController: ...
    async def __aexit__(self, *exc: object) -> None: ...
    def arm(self) -> None: ...
    async def fire(self, profile: SwingProfile) -> None: ...
```

Tests (use MockBLDCDriver + FakeClock):
- Fire without arming raises RuntimeError
- Throttle history matches profile shape within tolerance (sample at N points)
- Total elapsed time on FakeClock matches profile.total_ms
- Context manager disarms on exit even if fire() raises

### 4.8 `calibrate.py`

```python
class EscCalibrator:
    """One-shot ESC calibration routine.
       1. Power off ESC. set_throttle(1.0). Power on ESC. Wait for beeps.
       2. set_throttle(0.0). Wait for beeps.
       3. disarm().
    Console-driven prompts between steps.
    """
    def __init__(self, driver: BLDCDriver, clock: Clock,
                 prompt_fn: Callable[[str], None] = input): ...
    async def run(self) -> None: ...
```

Tests: with MockBLDCDriver, FakeClock, and a `prompt_fn` that records prompts, verify the throttle sequence is `[1.0, 0.0, disarm]` in the correct order with the prompts in between.

### 4.9 `coordinator.py`

```python
class RallyCoordinator:
    """Top-level control loop. Wires:
       observations source → TrajectoryPredictor → AimController → SwingController
    """
    def __init__(
        self,
        aim: AimController,
        predictor: TrajectoryPredictor,
        servo_driver: ServoDriver,
        swing: SwingController,
        clock: Clock,
        strike_plane_x: float = 0.0,
        swing_latency_s: float = 0.05,   # how early to fire the swing
        servo_yaw_channel: int = 0,
        servo_pitch_channel: int = 1,
    ): ...

    async def step(self, obs: BallObservation) -> None:
        """Push one observation, update aim, decide whether to fire."""

    async def run(self, observation_stream: AsyncIterator[BallObservation]) -> None:
        """Main async loop. Pulls observations, calls step()."""
```

Tests (mocks + FakeClock):
- Synthetic incoming ballistic stream → servos receive aim updates → swing fires once at predicted impact_time - swing_latency
- Unreachable target: aim returns None, no swing fires
- Out-of-buffer (fewer than min_observations): swing does not fire
- Strike happens exactly once per "pass" — not retriggered

## 5. Wave structure for subagents

### Wave 0 — verify + commit the pydantic refactor (single agent or solo)
- Run pytest / mypy / ruff
- Fix any breakage
- Commit `refactor(aim): migrate value objects to pydantic v2`

### Wave 1 — independent foundation modules (parallel, 2 agents)
- **Agent 1A:** `clock.py`, `ball.py`, `camera.py` + tests
- **Agent 1B:** `drivers/__init__.py`, `drivers/servo.py`, `drivers/bldc.py` + tests + the `[project.optional-dependencies] pi = [...]` extra

After Wave 1: merge `feature/aim` → `develop` (`git checkout develop && git merge --no-ff feature/aim`), cut `feature/v2-control` from `develop`.

### Wave 2 — modules that depend on Wave 1 (parallel, 3 agents)
- **Agent 2A:** `predictor.py` + tests (depends on `ball.py`)
- **Agent 2B:** `swing.py` + tests (depends on `drivers/bldc.py`, `clock.py`)
- **Agent 2C:** `calibrate.py` + tests (depends on `drivers/bldc.py`, `clock.py`)

### Wave 3 — integration (single agent)
- **Agent 3A:** `coordinator.py` + integration tests
- Final: `uv run pytest`, `uv run mypy src/`, `uv run ruff check src/` all green
- Open PR `feature/v2-control` → `develop`

## 6. Commit hygiene

Each module + its tests should be its own conventional-commit. Examples:
```
feat(ball): add BallObservation, BallState, StrikePrediction, DepthEstimator
feat(camera): add pinhole CameraIntrinsics model
feat(drivers): add ServoDriver + BLDCDriver protocols, real + mock impls
feat(predictor): add TrajectoryPredictor with weighted ballistic fit
feat(swing): add SwingController + SwingProfile open-loop control
feat(calibrate): add EscCalibrator one-shot routine
feat(coordinator): wire predictor → aim → swing in RallyCoordinator
test(predictor): cover ballistic recovery, confidence, weighting
```

## 7. Pi deployment (deferred — after Wave 3 lands)

When the test suite is fully green on the laptop:
1. SSH/SFTP code to the Pi (`~/mcenroebot/`)
2. On Pi: `uv sync --extra pi`
3. Wire up: PCA9685 HAT at I2C `0x40`, servos on ch0/ch1, ESC signal wire on ch2
4. Run `python -m mcenroebot.calibrate` once to arm the ESC
5. Run the coordinator with the live webcam feed

## 8. Things to flag back to AJ before building

- **Camera intrinsics are not yet known.** `BallRadiusDepthEstimator` will need a real `CameraIntrinsics` instance. We should add a `scripts/calibrate_camera.py` (OpenCV checkerboard) as part of Wave 1 or call it out as a separate task. For now, ship with a placeholder intrinsics object in the demo and document the calibration step.
- **Strike plane location** is `x = arm_length_m` by default (0.20 m forward). Confirm this matches the physical setup once the turret is mounted.
- **Swing latency** (`swing_latency_s = 0.05`) is a guess. The first hardware-in-loop tests should measure actual mechanical latency and update this.
- **Trash talk audio** is out of scope for this plan. It can be added as a small `audio.py` later — `RallyCoordinator` should expose a hook.
