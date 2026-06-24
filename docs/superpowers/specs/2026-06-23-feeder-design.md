# McEnroe V4 Feeder — Design Spec

Date: 2026-06-23
Status: Approved (brainstorming → implementation)
Branch: `feature/v4-feeder` (cut from `develop`)

This spec reconciles [`docs/V4_PLAN.md`](../../V4_PLAN.md) (mechanism source of truth) and
[`docs/v4-implementation-plan.md`](../../v4-implementation-plan.md) (build checklist) with the
**actual** state of the codebase as of 2026-06-23. Where the two plan docs disagree with reality,
this spec is authoritative for the software work.

---

## 1. Goal

Pivot McEnroe from an aim-and-swat / return-rally robot to a **feeder**: a spin/aim ball machine
that serves balls with controlled speed and spin to chosen court locations, with a closed recycle
loop (catch net → trough → auger → hopper → escapement → launch wheels).

**Explicitly out of scope** (the hard rally slice): incoming-ball 3D tracking, strike-plane
prediction, sub-100 ms timing. The feeder is a periodic scheduler driving actuators — not a
real-time vision control loop.

---

## 2. Codebase reconciliation (plan vs. reality)

A fresh inventory of `src/mcenroebot/` found the repo already contains the **entire V3 rally
stack**, not just the `aim/` slice the old CLAUDE.md describes. Findings that change the plan:

| Plan assumption | Reality | Resolution |
| --- | --- | --- |
| Reuse `aim/`, `clock/`, `camera/`, `drivers/servo/`, `drivers/bldc/` | All present and built | Reuse as-is |
| `drivers/bldc/` "extends `esc_arm`" | No `esc_arm`; ESC arming lives in `calibrate/EscCalibrator` (`calibrate/esc.py`) | `launch/` throttle helper + Wave 5 reuse `calibrate/EscCalibrator`; drop `esc_arm` references |
| Shelved: `predictor/`, `swing/`, `ball/`, `coordinator.RallyCoordinator` | All present and fully built | **Archive** to `_shelved/` (see §4) |
| Python floor `>=3.13`, reconcile to 3.11 before Pi | `pyproject.toml` already `requires-python = ">=3.11"` | **Resolved** — drop this open question |
| New: `launch/`, `drill/`, `drivers/feeder/`, `drivers/lift/`, `player/` | All correctly absent | Build per waves |
| Branch `feature/v4-feeder` from `develop` | Currently on `feature/v4`; `develop` exists but is behind | Cut `feature/v4-feeder` from `develop`, carry plan docs forward (see §3) |

Existing reused packages (do not modify): `aim/`, `clock/`, `camera/`, `calibrate/`,
`drivers/servo/`, `drivers/bldc/`.

---

## 3. Branch setup

- Cut `feature/v4-feeder` from `develop`.
- The V4 plan docs (`docs/V4_PLAN.md`, `docs/v4-implementation-plan.md`) and the untracked
  `docs/3d-models/generate_feeder_parts.py` currently live on `feature/v4`, not `develop`. Carry
  these files forward onto `feature/v4-feeder` so the plan travels with the work. The diff against
  `develop` is shown to the user before anything lands.
- Only feeder-relevant content is brought across; unrelated `feature/v4` commits are not merged.

---

## 4. Archive the V3 rally stack

Move the V3-only modules to `src/mcenroebot/_shelved/` (underscore prefix = clearly inactive, not
part of the public import surface). Verified safe: **nothing in the active/reused set imports the
V3-only set** — only `coordinator/rally.py` references `ball`/`predictor`/`swing`, and it moves too.

| Move from | Move to |
| --- | --- |
| `src/mcenroebot/ball/` | `src/mcenroebot/_shelved/ball/` |
| `src/mcenroebot/predictor/` | `src/mcenroebot/_shelved/predictor/` |
| `src/mcenroebot/swing/` | `src/mcenroebot/_shelved/swing/` |
| `src/mcenroebot/coordinator/rally.py` + `coordinator/__main__.py` | `src/mcenroebot/_shelved/rally/` |
| `tests/test_ball/`, `tests/test_predictor/`, `tests/test_swing/` | `tests/_shelved/...` |
| `tests/test_coordinator/test_rally.py` | `tests/_shelved/test_rally/...` |

Rules for the move:
- Rewrite internal imports within the moved set to `mcenroebot._shelved.*`. `ball/depth.py` keeps
  importing `mcenroebot.camera` (camera stays active; archive→active dependency is fine).
- **Tests move with their code and keep passing** so the 85% coverage floor holds across the move.
- `src/mcenroebot/__init__.py` keeps exporting only the aim symbols (already the case) — no
  `_shelved` symbols are re-exported at the top level.
- After the move, `coordinator/` holds only `__init__.py`, rewritten to export nothing (`__all__ =
  []`) until Wave 4 adds `FeederCoordinator`. The package is then ready to host `feeder.py`.
- `_shelved/__init__.py` documents the package as inactive V3 code, retained for reference.
- This is committed **first** on `feature/v4-feeder`, before any new feeder code, so the active
  surface is unambiguous. Phase gate: `uv run pytest` green, `uv run mypy src/` clean.

---

## 5. Conventions (mandatory — copy from `aim/` and `drivers/servo/`)

- Every component is a **package** (`__init__.py` + files split by responsibility: `protocol.py`,
  real impl, `mock.py`, `value_objects.py`, `controller.py`, `__main__.py` demo). Re-export the
  public API via `__init__.py`.
- Value objects are **pydantic v2 `BaseModel`, `frozen=True`**, keyword-only at all call sites.
  Range checks in `@field_validator`. Tests assert `ValidationError`, not `ValueError`.
- Controllers are **stateless apart from injected config**. Out-of-envelope → return `None`, don't raise.
- Every GPIO-touching driver: a `Protocol`, a real impl with Adafruit/GPIO libs **lazy-imported
  inside `__init__`**, and a `Mock<Name>Driver` that records calls. Higher layers test against
  mocks; real drivers are `@pytest.mark.integration`, skipped off-Pi.
- Conventional commits (`feat(scope):` …), one logical commit per package.
- Pi-only deps go in `[project.optional-dependencies] pi`, added via `uv add --optional pi`.

### Coordinate / spin conventions (used by `launch/`)

- Reuse the V2 frame: `+X` forward (toward the player), `+Y` left, `+Z` up. Meters internally,
  degrees for servo I/O, seconds for time.
- **Topspin > 0** (ball top rotates toward the player). Backspin < 0.
- `head_roll_deg`: rotation of the two-wheel head about the shot axis. `0°` = spin axis horizontal
  → pure top/backspin. `90°` = spin axis vertical → pure sidespin. General angle → mix.

---

## 6. Module architecture & waves

```
        clock/ (reuse)         camera/ (reuse, vision phase only)
           │                        │
           │                        ▼
           │                   player/ (NEW, Wave 6)
           │                        │
   ┌───────┴───────────┐            │
   ▼                   ▼            ▼
drivers/feeder/   drivers/lift/   drill/ ──── AimStrategy (Protocol)
   │                   │            │           ├─ FixedPatternStrategy (Wave 3)
   │                   │            │           └─ VisionPlacementStrategy (Wave 6)
   │                   │            ▼
   │                   │         launch/ (NEW, pure math)  aim/ (reuse)
   │                   │            │                         │
   └───────────────────┴───────┐    │   drivers/bldc/ (reuse) │  drivers/servo/ (reuse)
                               ▼    ▼            │            ▼            │
                          coordinator.FeederCoordinator (NEW) ────────────┘
```

### Wave 1 — `launch/` (pure math, no hardware) — **this session**

The analog of `aim/`. Built first; everything depends on its value objects. Target **≥95% coverage**.

| File | Contents |
| --- | --- |
| `value_objects.py` | `ShotSpec`, `WheelCommand`, `LaunchGeometry`, `ThrottleMap` |
| `controller.py` | `LaunchController` |
| `__main__.py` | demo: print `WheelCommand` for a few `ShotSpec`s |
| `__init__.py` | re-export public API |

```python
class ShotSpec(BaseModel):          # frozen
    speed_mps: float                # desired ball exit speed; > 0
    spin_rad_s: float               # signed magnitude; + = topspin at roll 0
    spin_axis_deg: float            # head roll: 0 = top/back, 90 = side; [0, 360)

class WheelCommand(BaseModel):      # frozen
    top_rpm: float                  # >= 0
    bottom_rpm: float               # >= 0
    head_roll_deg: float            # [0, 180] servo range (validate)

class LaunchGeometry(BaseModel):    # frozen; injected config, mirrors TurretGeometry
    wheel_diameter_m: float         # e.g. 0.055
    ball_radius_m: float = 0.02
    grip_efficiency: float = 0.85   # eta: ball speed / mean surface speed; calibrated
    spin_efficiency: float = 0.85   # eta_spin; calibrated
    max_wheel_rpm: float            # from no-load BLDC rpm at deploy voltage

class ThrottleMap(BaseModel):       # frozen; calibrated rpm <-> ESC throttle [0,1]
    rpm_at_full_throttle: float     # measured rpm at throttle = 1.0
    # linear v1 model: throttle = rpm / rpm_at_full_throttle, clamped [0,1]
```

`LaunchController.compute(spec) -> WheelCommand | None`:

```
mean_surface = speed_mps / grip_efficiency
diff_surface = 2 * ball_radius_m * spin_rad_s / spin_efficiency
u_top    = mean_surface + diff_surface / 2
u_bottom = mean_surface - diff_surface / 2
rpm(u)   = u * 60 / (pi * wheel_diameter_m)
top_rpm, bottom_rpm = rpm(u_top), rpm(u_bottom)
head_roll_deg = spin_axis_deg folded into [0, 180]   # 180° head symmetry
```

Return `None` (out of envelope) when `u_top < 0` or `u_bottom < 0` (spin too high for the speed),
or either rpm `> max_wheel_rpm`. Also provide
`LaunchController.throttles(cmd, throttle_map) -> tuple[float, float]` converting a `WheelCommand`
to two ESC throttles for the bldc layer.

Tests `tests/test_launch/`:
- Zero spin → `top_rpm == bottom_rpm == rpm(speed/grip_efficiency)`.
- Positive spin → `top_rpm > bottom_rpm`; negative → reversed.
- Round-trip: pick `(u_top, u_bottom)`, derive the `ShotSpec` they'd produce, confirm `compute`
  recovers those wheel speeds within `1e-6`.
- Spin too high for speed → `None` (not a negative rpm). rpm over `max_wheel_rpm` → `None`.
- `head_roll_deg` folds to `[0, 180]`; `WheelCommand` raises `ValidationError` outside it.
- `ThrottleMap` clamps to `[0, 1]`. Frozen-ness of all four value objects.

Commit: `feat(launch): add LaunchController + ShotSpec/WheelCommand/LaunchGeometry value objects`

### Wave 2 — `drivers/feeder/` + `drivers/lift/` (mock-tested, real gated)

- `drivers/feeder/` (escapement): `FeederDriver` Protocol (`set_rate(balls_per_min)`, `stop()`,
  `fire()` — v1 `fire()` raises `NotImplementedError`), `Pca9685FeederDriver` (CR servo on a
  PCA9685 channel; lazy `adafruit_servokit`; rate→throttle linear factor), `MockFeederDriver`.
- `drivers/lift/` (auger): `LiftDriver` Protocol (`set_duty([0,1])`, `off()`), `HopperSensor`
  Protocol (`is_full()`), `Pca9685LiftDriver` (PWM → MOSFET gate, lazy import), `MockLiftDriver`,
  `GpioHopperSensor` (lazy `RPi.GPIO`), `MockHopperSensor`.
- Tests: rate/duty monotonic + clamped; `stop()`/`off()` → 0; mocks record call order; lazy
  imports succeed off-Pi; real smoke tests `@integration`.
- Document the new PCA9685 channel map (two wheel ESCs, roll servo, CR-servo feeder) in `CLAUDE.md`,
  mirroring the existing `pan=ch0, tilt=ch1, ESC=ch2` line.

Commit: `feat(drivers): add feeder (escapement) and lift (auger) drivers with mocks`

### Wave 3 — `drill/` (no hardware)

- `AimStrategy` Protocol (`next_target(ctx) -> Position3D`), `Shot` value object (`spec`, `target`,
  `delay_s`), `FixedPatternStrategy` (patterns: `static`, `oscillate`, `random`, `figure8`; pure
  function of shot index + RNG seed), `Drill.shots(n) -> Iterator[Shot]` (stateless config +
  injected seeded RNG).
- Tests: targets within table bounds; fixed seed → identical sequence; cadence respected; figure-8
  quadrant order; frozen value objects.

Commit: `feat(drill): add Drill engine, AimStrategy Protocol, FixedPatternStrategy`

### Wave 4 — `coordinator/feeder.py` (no hardware)

`FeederCoordinator` (new file in `coordinator/`, must not import `_shelved.*`). Constructor injects
`drill`, `launch` + `launch_geometry` + `throttle_map`, `aim` (`AimController`), `servo` (pan/tilt),
`head_roll` servo, `wheel_top`/`wheel_bottom` BLDC, `feeder`, `lift`, `clock`, optional `hopper`.

`async run(n)` per shot: next `Shot` → `launch.compute` (skip+log if `None`) → `aim.compute`
(skip+log if unreachable) → command head-roll + pan/tilt + wheel throttles → settle → release ball
(`set_rate` v1) → run lift (`off()` if `hopper.is_full()`) → `clock.sleep(delay_s)`. On exit
(try/finally): wheels throttle 0, `feeder.stop()`, `lift.off()`.

Tests (mock everything + `FakeClock`): happy path ordered calls; `launch.compute None` skips shot;
`aim.compute None` skips shot; hopper full → `lift.off()`; clean shutdown on normal end and on
exception.

Phase gate: `uv run pytest` green, `uv run mypy src/` clean, coverage ≥85% (`launch/` ≥95%); a
simulated 100-shot drill issues correct ordered commands for 100/100 cases.

Commit: `feat(coordinator): add FeederCoordinator wiring drill -> launch + aim + feeder + lift`

### Wave 5 — calibration scripts + first live feed (hardware)

PEP-723 standalone scripts under `scripts/` (inline metadata, own deps — same pattern as
`scripts/calibrate_camera.py`):
- `scripts/calibrate_feeder.py` — sweep CR-servo throttle, count balls / 60 s, fit
  `balls_per_min ↔ throttle`.
- `scripts/calibrate_launch.py` — grid of `(top_rpm, bottom_rpm)`, measure landing distance (+spin
  if video available), back out `grip_efficiency`, `spin_efficiency`, `rpm_at_full_throttle`; writes
  JSON loadable via `LaunchGeometry.model_validate_json`.

Bring-up on the Pi (`uv sync --extra pi`): arm both ESCs via `calibrate/EscCalibrator` (once per
wheel) → run calibration scripts → run `FeederCoordinator` with a `static` `FixedPatternStrategy`
at low rpm.

Phase gate: 20 consecutive balls to a chosen spot at controlled speed, no jam/double-feed; auger
keeps hopper non-empty over a 5-minute run.

### Wave 6 — vision placement (optional, hardware)

`player/` package: `PlayerDetector` Protocol (`detect(frame) -> PlayerPosition | None`),
`PlayerPosition` value object (`side_offset_m`, `confidence`), `SimpleBlobDetector` (background
subtraction / contour centroid over the `camera/` frame source), `MockPlayerDetector`.
`drill.VisionPlacementStrategy` implements `AimStrategy`: aim next ball to the open side; low
confidence → fall back to a fixed pattern. Drops in behind the existing `AimStrategy` Protocol — no
change to `launch/`, `Drill`, or `FeederCoordinator` beyond injecting a different strategy.

Phase gate: player standing left → ≥80% of balls land right of center (and vice versa).

Commit: `feat(player): add PlayerDetector + VisionPlacementStrategy for open-court targeting`

---

## 7. Branching summary

```
develop
   └── feature/v4-feeder
         ├── (commit 1) archive V3 stack -> _shelved/ + carry V4 plan docs
         ├── (Wave 1) launch/
         ├── (Wave 2) drivers/feeder + drivers/lift
         ├── (Wave 3) drill/
         ├── (Wave 4) coordinator/feeder.py
         ├── (Wave 5) scripts/calibrate_feeder.py + scripts/calibrate_launch.py
         └── (Wave 6) player/ + VisionPlacementStrategy
```

Merge `feature/v4-feeder` → `develop` after Wave 5's phase gate (vision is a clean follow-up).

---

## 8. This session's deliverable

1. Write + commit this spec.
2. Cut `feature/v4-feeder` from `develop`, carry plan docs forward.
3. Archive the V3 stack to `_shelved/` (commit 1); verify suite green + mypy clean.
4. Implement **Wave 1 `launch/`** via TDD to its phase gate (tests green, mypy clean, ≥95% coverage).

Waves 2–6 are left for follow-up sessions.

### Status (updated 2026-06-24) — all waves code-complete

Every wave is implemented and committed on `feature/v4-feeder` via TDD:

| Wave | Module(s) | State |
| --- | --- | --- |
| 0 | archive V3 → `_shelved/` | done |
| 1 | `launch/` | done — 100% coverage |
| 2 | `drivers/feeder/`, `drivers/lift/` | done — mock-tested, real `@integration` |
| 3 | `drill/` | done — 100% coverage |
| 4 | `coordinator/feeder.py` | done — 100% coverage, 100-shot sim passes |
| 5 | `scripts/calibrate_feeder.py`, `calibrate_launch.py` | code-complete; **live-feed gate needs Pi hardware** |
| 6 | `player/`, `drill.VisionPlacementStrategy` | done — 100% coverage; **live gate needs Pi hardware** |

Full suite: **473 passed, 8 skipped** (Pi-only `@integration`), **mypy clean**, **ruff clean**,
project coverage **96.48%** (`launch/` 100%). Remaining work is hardware-only: run the Wave 5
calibration + first-live-feed gate and the Wave 6 ≥80%-to-open-side gate on the Pi, then merge
`feature/v4-feeder` → `develop`.

---

## 9. Open questions / risks (carried forward)

- **ESC throttle → rpm is nonlinear under load.** The v1 linear `ThrottleMap` is a placeholder;
  upgrade `calibrate_launch.py` to a 2nd-order/lookup curve if launch speed is inconsistent.
- **CR-servo feed rate drifts** (battery sag, load). If per-shot timing matters for vision sync,
  add the index endstop (`V4_PLAN.md §1`) and implement `FeederDriver.fire()` for a real
  `ball_fired` event.
- **Two ESCs on one PCA9685.** Confirm channel assignment and shared-ground/power budget before
  wiring; document the channel map in `CLAUDE.md`.
- **Head-roll servo channel.** Decide whether roll shares the servo driver instance (extra channel)
  or a second instance; reflect in `FeederCoordinator`'s constructor.
