# McEnroe — Ping-Pong Robot (V2)

A hobby ping-pong robot. **V2** is the *aim-and-swat* phase: a 3-axis turret that orients a paddle at an incoming ball
and fires an open-loop swing to return it.

This repository holds the V2 control software. It runs against mocks on a laptop and on real hardware on a Raspberry Pi
4.

---

## How it works

A single webcam tracks the ball. Depth is recovered monocularly from the ball's apparent radius. A short rolling buffer
of observations is fit to a 3D ballistic trajectory, which predicts where (and when) the ball will cross the strike
plane. Two servos aim the paddle's sweep plane at that point; a brushless motor swings the paddle through it on a fixed
timing envelope.

```
 webcam ──► tracker ──► predictor ──► aim controller ──► servos (J1 yaw, J2 pitch)
                          │
                          └─────────► swing controller ──► BLDC (J3 swing)
```

### Hardware

| Part                                   | Role                                         |
|----------------------------------------|----------------------------------------------|
| Raspberry Pi 4 (Bookworm, Python 3.11) | Deploy target                                |
| Adafruit PCA9685 16-channel PWM HAT    | I²C `0x40` — pan=ch0, tilt=ch1, BLDC ESC=ch2 |
| 2× MG996R servos                       | J1 yaw, J2 pitch (paddle orientation)        |
| A2212 1000 KV brushless motor + ESC    | J3 paddle swing                              |
| 3S LiPo                                | BLDC supply                                  |
| HAT 5V/3A PSU                          | Servo supply                                 |
| Logitech webcam (`/dev/video0`)        | Ball tracking (2D + monocular depth)         |

### Coordinate frame

- **Origin:** J1 yaw axis, at J2 pitch pivot height.
- **+X** forward (toward the ball), **+Y** left (viewed from above), **+Z** up.
- Meters internally; degrees at servo I/O; seconds for time.

---

## Status

| Component                                                         | State                                |
|-------------------------------------------------------------------|--------------------------------------|
| `aim/` (AimController, Position3D, ServoAngles, TurretGeometry)   | ✅ Wave 1                             |
| `clock/` (Clock, SystemClock, FakeClock)                          | ✅ Wave 1                             |
| `camera/` (CameraIntrinsics, pixel_to_ray)                        | ✅ Wave 1                             |
| `ball/` (BallObservation/State/Prediction, BallRadiusDepth)       | ✅ Wave 1                             |
| `drivers/servo/`, `drivers/bldc/` (Protocols + PCA9685 + Mocks)   | ✅ Wave 1                             |
| `predictor/` (TrajectoryPredictor, weighted ballistic fit)        | ✅ Wave 2                             |
| `swing/` (SwingProfile + SwingController, open-loop envelope)     | ✅ Wave 2                             |
| `calibrate/` (EscCalibrator one-shot routine)                     | ✅ Wave 2                             |
| `coordinator/` (RallyCoordinator, full pipeline)                  | ✅ Wave 3                             |
| Pi deployment                                                     | ⏳ Hardware bring-up                  |

See [`docs/implementation-plan.md`](docs/implementation-plan.md) for the wave-by-wave build schedule and
[`docs/V2_PLAN.md`](docs/V2_PLAN.md) for the original design.

---

## Quickstart (laptop development)

Prereqs: `uv` (replaces `pip`/`venv`).

```bash
uv sync                          # install runtime + dev deps into .venv
uv run pre-commit install --hook-type pre-commit --hook-type commit-msg
uv run pytest                    # run the full suite with coverage
uv run python -m mcenroebot.aim  # print aim-controller sanity demo
```

### Common commands

```bash
uv run pytest                                       # full suite (coverage runs automatically)
uv run pytest -q                                    # quiet
uv run pytest tests/test_aim.py::TestAimControllerCompute::test_directly_forward_gives_neutral_pose
uv run pytest -m unit                               # by marker: unit / integration / perf / adapter

uv run mypy src/                                    # strict, with pydantic plugin
uv run ruff check src/                              # lint
uv run ruff format src/                             # format

uv add <package>                                    # add a runtime dep (never edit pyproject.toml by hand)
uv add --dev <package>                              # dev-only
uv add --optional pi <package>                      # Pi-only optional extra
```

Pre-commit runs ruff (lint + format), mypy, detect-secrets, and commitizen on commit; pytest runs on **pre-push**.

---

## Pi deployment

Deferred until Wave 3 lands. The high-level steps:

```bash
# On the Pi
cd ~/mcenroebot
uv sync --extra pi               # pulls adafruit-blinka, pca9685, servokit
uv run python -m mcenroebot.calibrate   # one-shot ESC arming
uv run python -m mcenroebot.coordinator # rally loop against live webcam
```

The real Adafruit drivers are imported **lazily** inside the driver constructors so the package still imports on a Mac (
where those libraries aren't installed).

---

## Coding standards

These are the non-negotiable ones. See [`CLAUDE.md`](CLAUDE.md) for the full set.

- **OOP everywhere.** Public API is classes; no bare module-level functions.
- **Pydantic v2 frozen models** (`BaseModel` + `ConfigDict(frozen=True)`) for every value object. No `@dataclass`. Range
  checks via `@field_validator`. Pydantic constructors are **keyword-only** at every call site.
- **Hardware abstraction.** Every GPIO-touching driver has a `Protocol` interface and a paired `Mock<Name>Driver`.
  Higher-level code is tested against mocks only.
- **Type hints everywhere**; `mypy --strict` must pass.
- **Coverage ≥85%** (enforced); aim ≥95% on pure-math modules.

---

## Project layout

```
src/mcenroebot/        # package source (src-layout)
  aim.py               # implemented
  ...                  # see docs/implementation-plan.md for the rest
tests/                 # pytest, mirrors src/mcenroebot/ structure
docs/
  implementation-plan.md  # actionable wave-by-wave plan
  V2_PLAN.md              # original design + module specs
CLAUDE.md              # guidance for Claude Code sessions
pyproject.toml         # ruff, mypy strict, pytest config, coverage floor
```

---

## Gitflow

`main` ← `develop` ← `feature/*`. Conventional commits enforced by commitizen on commit-msg (`feat(scope):`,
`fix(scope):`, `refactor(scope):`, `test(scope):`, `chore:`, `docs:`).

Current state: `feature/aim` holds the aim module and pydantic v2 refactor; it will merge to `develop`, then
`feature/v2-control` will be cut for Waves 1–3.
