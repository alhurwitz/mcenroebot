# McEnroe V4 (Feeder) — Implementation Plan

Actionable, wave-by-wave code plan for the **feeder** — the spin/aim ball machine with a closed
recycle loop. Derived from [`V4_PLAN.md`](V4_PLAN.md) (design source of truth — read it first for
mechanism rationale, dimensions, and BOM). This document is the build checklist for the software.

The feeder is a *feeder*, not a return-rally robot: it serves balls with controlled speed/spin to
chosen court locations, the human returns into a catch net, and an auger recycles balls to the
hopper. There is **no incoming-ball tracking, no strike-plane prediction, no sub-100 ms timing**.
The V3 rally path (`predictor/`, `swing/`, `RallyCoordinator`) is untouched and unused here.

---

## 0. Snapshot

| Item | Value |
| --- | --- |
| Working directory | `/Users/alberthurwitz/Projects/mcenroebot` |
| Package | `src/mcenroebot/` (src-layout) |
| Tests | `tests/` mirror at `tests/test_<name>/test_<concern>.py` |
| Python | match `pyproject.toml` (≥3.13 floor; Pi/Bookworm 3.11 reconcile is a pre-deploy task, not a code task) |
| Dep manager | `uv` (`uv add` / `uv add --optional pi` — never hand-edit deps) |
| Coverage floor | 85% project; **≥95% on pure-math (`launch/`)** |
| Branch | cut `feature/v4-feeder` from `develop` after V2 has merged |
| Reuses unchanged | `clock/`, `aim/`, `drivers/servo/`, `drivers/bldc/`, `camera/` (vision phase only) |
| Shelved (do not import) | `predictor/`, `swing/`, `ball/`, `coordinator.RallyCoordinator` |

### Conventions (mandatory — copy from `aim/` and `drivers/servo/`)

- Every component is a **package** (`__init__.py` + files split by responsibility: `protocol.py`,
  real impl, `mock.py`, `value_objects.py`, `controller.py`, `__main__.py` demo). Re-export public
  API via `__init__.py`.
- Value objects are **pydantic v2 `BaseModel`, `frozen=True`**, keyword-only at call sites. Range
  checks in `@field_validator`. Tests assert `ValidationError`, not `ValueError`.
- Controllers are **stateless apart from injected config**. Out-of-envelope → return `None`, don't raise.
- Every GPIO-touching driver: a `Protocol`, a real impl with Adafruit/GPIO libs **lazy-imported
  inside `__init__`**, and a `Mock<Name>Driver` that records calls. Higher layers test against mocks.
  Real drivers are `@pytest.mark.integration`, skipped off-Pi.
- Conventional commits (`feat(scope):`…), one logical commit per package.

### Coordinate system / spin sign conventions (used by `launch/`)

- Reuse V2 frame: `+X` forward (toward the player), `+Y` left, `+Z` up. Meters, degrees for servo I/O.
- **Topspin > 0** (ball top rotates toward the player). Backspin < 0.
- `head_roll_deg`: rotation of the two-wheel head about the shot axis. `0°` = spin axis horizontal
  → pure top/backspin. `90°` = spin axis vertical → pure sidespin. General angle → mix.

---

## 1. Module dependency graph

```
        clock/ (reuse)         camera/ (reuse, vision phase only)
           │                        │
           │                        ▼
           │                   player/ (NEW, Phase B)
           │                        │
   ┌───────┴───────────┐            │
   ▼                   ▼            ▼
drivers/feeder/   drivers/lift/   drill/ ──── AimStrategy (Protocol)
   │                   │            │           ├─ FixedPatternStrategy (Phase A)
   │                   │            │           └─ VisionPlacementStrategy (Phase B)
   │                   │            ▼
   │                   │         launch/ (NEW, pure math)  aim/ (reuse)
   │                   │            │                         │
   └───────────────────┴───────┐    │   drivers/bldc/ (reuse) │  drivers/servo/ (reuse)
                               ▼    ▼            │            ▼            │
                          coordinator.FeederCoordinator (NEW) ────────────┘
```

---

## 2. Wave 1 — pure-math launch controller (no hardware)

The analog of `aim/`. Build and fully cover this first; everything else depends on its value objects.

### `launch/`

| File | Contents |
| --- | --- |
| `value_objects.py` | `ShotSpec`, `WheelCommand`, `LaunchGeometry`, `ThrottleMap` |
| `controller.py` | `LaunchController` |
| `__main__.py` | demo: print `WheelCommand` for a few `ShotSpec`s |

```python
class ShotSpec(BaseModel):
    model_config = ConfigDict(frozen=True)
    speed_mps: float            # desired ball exit speed; > 0
    spin_rad_s: float           # signed magnitude of spin; + = topspin at roll 0
    spin_axis_deg: float        # head roll: 0 = top/back, 90 = side; [0, 360)

class WheelCommand(BaseModel):
    model_config = ConfigDict(frozen=True)
    top_rpm: float              # >= 0
    bottom_rpm: float           # >= 0
    head_roll_deg: float        # [0, 180] servo range (validate)

class LaunchGeometry(BaseModel):     # injected config, mirrors TurretGeometry
    model_config = ConfigDict(frozen=True)
    wheel_diameter_m: float          # e.g. 0.055
    ball_radius_m: float = 0.02
    grip_efficiency: float = 0.85    # eta: ball speed / mean surface speed; calibrated
    spin_efficiency: float = 0.85    # eta_spin; calibrated
    max_wheel_rpm: float             # from no-load BLDC rpm at the deploy voltage

class ThrottleMap(BaseModel):        # calibrated rpm <-> ESC throttle [0,1]
    model_config = ConfigDict(frozen=True)
    rpm_at_full_throttle: float      # measured no-load (or loaded) rpm at throttle = 1.0
    # linear model for v1: throttle = rpm / rpm_at_full_throttle, clamped [0,1]
```

`LaunchController.compute(spec) -> WheelCommand | None`

Math (two counter-rotating wheels; ball gripped between them):

```
mean_surface = speed_mps / grip_efficiency           # m/s
diff_surface = 2 * ball_radius_m * spin_rad_s / spin_efficiency
u_top    = mean_surface + diff_surface / 2           # m/s
u_bottom = mean_surface - diff_surface / 2
rpm(u)   = u * 60 / (pi * wheel_diameter_m)
top_rpm, bottom_rpm = rpm(u_top), rpm(u_bottom)
head_roll_deg = spin_axis_deg folded into [0, 180]   # 180 head symmetry
```

Return `None` (out of envelope) when `u_top < 0` or `u_bottom < 0` (spin too high for the speed) or
either rpm `> max_wheel_rpm`. Provide `LaunchController.throttles(cmd, throttle_map) -> tuple[float, float]`
helper that converts a `WheelCommand` to two ESC throttles for the bldc layer.

### Tests `tests/test_launch/`

- Zero spin → `top_rpm == bottom_rpm`; both equal `rpm(speed/grip_efficiency)`.
- Positive spin → `top_rpm > bottom_rpm`; negative → reversed.
- Round-trip: pick `(u_top, u_bottom)`, derive the `ShotSpec` they'd produce, confirm `compute`
  recovers those wheel speeds within 1e-6.
- Spin too high for speed → `compute` returns `None` (not a negative rpm).
- rpm over `max_wheel_rpm` → `None`.
- `head_roll_deg` folds to `[0, 180]`; `WheelCommand` raises `ValidationError` outside it.
- `ThrottleMap` clamps to `[0, 1]`.
- Frozen-ness of all four value objects. **Target ≥95% coverage.**

Commit: `feat(launch): add LaunchController + ShotSpec/WheelCommand/LaunchGeometry value objects`

---

## 3. Wave 2 — actuator drivers (mock-tested, real gated)

### `drivers/feeder/` (escapement)

```python
class FeederDriver(Protocol):
    def set_rate(self, balls_per_min: float) -> None: ...   # v1 continuous CR servo
    def stop(self) -> None: ...
    def fire(self) -> None: ...                             # index-upgrade path; v1 raises NotImplementedError

class Pca9685FeederDriver:   # continuous-rotation servo on a PCA9685 channel
    """Lazy adafruit_servokit import in __init__. Maps balls_per_min -> continuous_servo
    throttle [-1, 1] via a calibrated linear factor (see scripts/calibrate_feeder.py)."""

class MockFeederDriver:      # records (set_rate / stop / fire) calls in order
```

Tests: rate→throttle monotonic and clamped; `stop()` sets throttle 0; mock records order; real
driver imports cleanly without adafruit installed (lazy import); real smoke test `@integration`.

### `drivers/lift/` (auger)

```python
class LiftDriver(Protocol):
    def set_duty(self, fraction: float) -> None: ...   # [0,1] PWM to MOSFET/L298N enable
    def off(self) -> None: ...

class HopperSensor(Protocol):
    def is_full(self) -> bool: ...

class Pca9685LiftDriver: ...        # PWM channel -> MOSFET gate (single direction); lazy import
class MockLiftDriver: ...           # records duty calls
class GpioHopperSensor: ...         # reads a GPIO endstop; lazy RPi.GPIO import
class MockHopperSensor: ...         # programmable is_full() for tests
```

Tests: duty clamped `[0,1]`; `off()` → duty 0; mock records; sensor mock toggles; real `@integration`.

Commit: `feat(drivers): add feeder (escapement) and lift (auger) drivers with mocks`

---

## 4. Wave 3 — drill engine + aim strategy (no hardware)

### `drill/`

```python
class AimStrategy(Protocol):
    def next_target(self, ctx: DrillContext) -> Position3D: ...   # court location to aim at

class Shot(BaseModel):
    model_config = ConfigDict(frozen=True)
    spec: ShotSpec
    target: Position3D            # reuse aim/.Position3D
    delay_s: float                # time until this shot fires (cadence)

class FixedPatternStrategy:       # Phase A — no vision
    """patterns: 'static', 'oscillate' (L/R baseline), 'random', 'figure8'.
    Pure function of shot index + RNG seed; fully deterministic under a fixed seed."""

class Drill:
    """Combines a spin/speed pattern + an AimStrategy + cadence into an iterator of Shot.
    Stateless config + an injected RNG (seed for reproducible tests)."""
    def shots(self, n: int | None = None) -> Iterator[Shot]: ...
```

Tests: each pattern produces targets inside the table bounds; fixed seed → identical Shot sequence
(determinism); cadence respected; figure-8 visits the expected quadrant order; `Shot`/`ShotSpec`
frozen. No hardware, pure logic — aim high coverage.

Commit: `feat(drill): add Drill engine, AimStrategy Protocol, FixedPatternStrategy`

---

## 5. Wave 4 — coordinator integration (no hardware)

Add a **new** `FeederCoordinator` alongside the existing `RallyCoordinator` in `coordinator/`
(new file `coordinator/feeder.py`). It must not import `predictor`/`swing`.

```python
class FeederCoordinator:
    def __init__(
        self,
        drill: Drill,
        launch: LaunchController,
        launch_geometry: LaunchGeometry,
        throttle_map: ThrottleMap,
        aim: AimController,                  # reuse: target Position3D -> ServoAngles
        servo: ServoDriver,                  # pan + tilt
        head_roll: ServoDriver,              # roll servo (or same driver, different channel)
        wheel_top: BLDCDriver,
        wheel_bottom: BLDCDriver,
        feeder: FeederDriver,
        lift: LiftDriver,
        clock: Clock,
        hopper: HopperSensor | None = None,
    ): ...

    async def run(self, n: int | None = None) -> None:
        """Periodic, NOT real-time. Per shot:
           1. ctx-> drill.next Shot
           2. launch.compute(spec) -> WheelCommand (skip + log if None)
           3. aim.compute(target)  -> ServoAngles (skip + log if None / unreachable)
           4. command head_roll, pan/tilt servos; set wheel ESC throttles via throttle_map
           5. let wheels + aim settle (settle_s)
           6. feeder.set_rate (v1) / feeder.fire (index upgrade) to release the ball
           7. run lift: duty on; if hopper and hopper.is_full(): lift.off()
           8. clock.sleep(shot.delay_s)
        On exit: wheels throttle 0, feeder.stop(), lift.off()."""
```

Tests `tests/test_coordinator/test_feeder.py` (mock everything + `FakeClock`):
- Happy path: N shots → expected ordered driver calls (aim set, then wheels, then settle, then feed).
- `launch.compute` → `None`: that shot is skipped, no wheel/feed calls, loop continues.
- `aim.compute` → `None` (unreachable target): shot skipped.
- Hopper full → `lift.off()` called; not full → lift runs.
- Clean shutdown: on normal end and on exception, wheels at 0, feeder stopped, lift off (try/finally).

Commit: `feat(coordinator): add FeederCoordinator wiring drill -> launch + aim + feeder + lift`

**Phase gate (Wave 4):** `uv run pytest` green, `uv run mypy src/` clean, coverage ≥85%
(`launch/` ≥95%). A simulated 100-shot drill issues correct, ordered commands for 100/100 cases.

---

## 6. Wave 5 — calibration scripts + first live feed (hardware)

Standalone PEP 723 scripts under `scripts/` (inline metadata, own deps — same pattern as
`scripts/calibrate_camera.py`; do not pollute runtime deps).

- `scripts/calibrate_feeder.py` — sweep CR-servo throttle, count balls over 60 s, fit the
  `balls_per_min ↔ throttle` factor for `Pca9685FeederDriver`.
- `scripts/calibrate_launch.py` — for a grid of `(top_rpm, bottom_rpm)`, fire and measure landing
  distance (and, if available, video-measured spin); back out `grip_efficiency`, `spin_efficiency`,
  and `ThrottleMap.rpm_at_full_throttle`. Writes a JSON loadable via `LaunchGeometry.model_validate_json`.

Bring-up order on the Pi (`uv sync --extra pi`):
1. Arm both ESCs (reuse `calibrate/EscCalibrator`, once per wheel).
2. `calibrate_feeder.py` → feeder factor. `calibrate_launch.py` → launch constants.
3. Run `FeederCoordinator` with a `FixedPatternStrategy` `static` drill (one fixed target) at low rpm.

**Phase gate (Wave 5):** machine serves 20 consecutive balls to a chosen spot at a controlled
speed without jam or double-feed; auger keeps the hopper non-empty over a 5-minute run. **Champagne.**

---

## 7. Wave 6 — vision placement (optional, hardware; the camera's role)

Only after Wave 5 is solid. This is the *easy* slice of vision (player/court detection in the
forgiving 1–2 s feed interval), not incoming-ball 3D prediction.

### `player/` (NEW)

```python
class PlayerDetector(Protocol):
    def detect(self, frame: NDArray) -> PlayerPosition | None: ...   # where the human is

class PlayerPosition(BaseModel):
    model_config = ConfigDict(frozen=True)
    side_offset_m: float      # left/right of center along the player's baseline
    confidence: float         # [0,1]

class SimpleBlobDetector:     # background subtraction / contour centroid; reuse camera/ frame source
class MockPlayerDetector: ...
```

### `drill.VisionPlacementStrategy`

Implements `AimStrategy`: read latest `PlayerPosition`, aim the next ball to the *open* side (or a
configured "attack the weakness" target). Drops in behind the existing `AimStrategy` Protocol — no
change to `launch/`, `drill.Drill`, or `FeederCoordinator` beyond injecting a different strategy.

Tests: open-side selection given a player offset; low confidence → fall back to a fixed pattern;
mock detector drives deterministic targets.

Commit: `feat(player): add PlayerDetector + VisionPlacementStrategy for open-court targeting`

**Phase gate (Wave 6):** with the player standing left, ≥80% of served balls land right of center
(and vice versa), at recreational pace.

---

## 8. Branching

```
develop (V2 complete; V3 lives on its own feature branches)
   └── feature/v4-feeder
         ├── (Wave 1) launch/
         ├── (Wave 2) drivers/feeder + drivers/lift
         ├── (Wave 3) drill/
         ├── (Wave 4) coordinator/feeder.py
         ├── (Wave 5) scripts/calibrate_feeder.py + scripts/calibrate_launch.py
         └── (Wave 6) player/ + VisionPlacementStrategy
```

Merge `feature/v4-feeder` → `develop` after Wave 5's phase gate (vision is a clean follow-up).

---

## 9. Open questions / risks

- **ESC throttle → rpm is nonlinear under load.** The v1 linear `ThrottleMap` is a placeholder;
  if launch speed is inconsistent, upgrade `calibrate_launch.py` to fit a 2nd-order or lookup curve.
- **CR-servo feed rate drifts** (battery sag, load). If per-shot timing matters for vision sync,
  add the index endstop (`V4_PLAN.md §1`) and implement `FeederDriver.fire()` for a real
  `ball_fired` event instead of open-loop rate.
- **Two ESCs on one PCA9685.** Confirm channel assignment and shared-ground/power budget before
  wiring; document the channel map in `CLAUDE.md` like the V2 `pan=ch0, tilt=ch1, ESC=ch2` line.
- **Python floor drift.** `pyproject.toml` says ≥3.13, `implementation-plan.md` says ≥3.11, Pi is
  Bookworm 3.11. Reconcile before Pi deploy; not a blocker for Waves 1–4 (dev machine).
- **Head-roll servo channel.** Decide whether roll shares the servo driver instance (extra channel)
  or a second instance; reflect in `FeederCoordinator`'s constructor.
