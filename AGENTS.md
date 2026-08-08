# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project

McEnroe is a hobby ping-pong robot. **The current direction is V4 — the feeder**: a spin/aim ball machine that serves balls with controlled speed/spin to chosen court locations, with a closed recycle loop (catch net → trough → auger → hopper → escapement → two launch wheels). There is **no incoming-ball tracking, no strike-plane prediction, no real-time loop** — it is a periodic scheduler driving actuators. The earlier **V2 aim-and-swat** return-rally stack (`ball/`, `predictor/`, `swing/`, `RallyCoordinator`) is shelved under `src/mcenroebot/_shelved/` and is not imported by the feeder.

**Sources of truth:** [`docs/superpowers/specs/2026-06-23-feeder-design.md`](docs/superpowers/specs/2026-06-23-feeder-design.md) (reconciled feeder design + wave plan), derived from [`docs/V4_PLAN.md`](docs/V4_PLAN.md) (mechanism/BOM) and [`docs/v4-implementation-plan.md`](docs/v4-implementation-plan.md). Read the spec before adding feeder modules. (`docs/V2_PLAN.md` documents the shelved V2 phase.)

**Hardware.** Deploy target is a Raspberry Pi 4 with an Adafruit PCA9685 PWM HAT at I2C `0x40`. Planned V4 channel map (confirm channel assignment + shared-ground/power budget before wiring — see spec §9):

| Ch | Actuator | Driver |
|---|---|---|
| 0 | pan servo (yaw) | `drivers/servo` |
| 1 | tilt servo (pitch) | `drivers/servo` |
| 2 | head-roll servo | `drivers/servo` |
| 3 | top wheel ESC | `drivers/bldc` |
| 4 | bottom wheel ESC | `drivers/bldc` |
| 5 | feed servo (MG996R positional, was escapement CR) | `drivers/feeder` |
| 6 | auger MOSFET PWM | `drivers/lift` |

The hopper-full endstop (optional) is on a GPIO pin via `drivers/lift.GpioHopperSensor`, not the PCA9685. Single Logitech webcam at `/dev/video0` is used only for the optional Wave-6 player-placement vision (no 3D ball tracking).

## Common commands

`uv` manages everything. Never hand-edit dependency lists in `pyproject.toml` — use `uv add <pkg>` / `uv remove <pkg>`.

```bash
uv sync                                    # refresh venv (laptop dev)
uv sync --extra pi                         # on the Pi only, installs adafruit-blinka etc.

uv run pytest                              # full suite; coverage runs automatically (fails if <85%)
uv run pytest -q                           # quiet
uv run pytest tests/test_aim.py::TestAimControllerCompute::test_directly_forward_gives_neutral_pose
uv run pytest -m unit                      # by marker (unit / integration / perf / adapter)

uv run mypy src/                           # strict mode, with pydantic.mypy plugin
uv run ruff check src/                     # lint (line-length 100, target py311)
uv run ruff format src/

uv run pre-commit install --hook-type pre-commit --hook-type commit-msg   # one-time hook install
uv run pre-commit run --all-files                                          # run all hooks manually

uv run python -m mcenroebot.aim            # aim-module sanity demo
```

Pre-commit runs ruff, ruff-format, mypy, detect-secrets, and commitizen on commit-msg; pytest runs on **pre-push**.

## Architecture and conventions

### Package layout (mandatory)

**Every logical component under `src/mcenroebot/` is a Python package — a directory with `__init__.py`, never a single flat `.py` file.** Inside, split by responsibility (Protocol, real impl, mock impl, value objects, demo) into focused files. Re-export the public API via `__init__.py` so callers can keep writing `from mcenroebot.<name> import Foo`. Provide a `__main__.py` if the package has a runnable demo.

Tests mirror this 1:1 under `tests/test_<name>/test_<concern>.py`.

Existing examples to copy from: `src/mcenroebot/aim/` and `src/mcenroebot/clock/`.

### Coordinate system (used everywhere)

- Origin: J1 yaw axis, at J2 pitch pivot height
- `+X` forward (toward the ball), `+Y` left (viewed from above), `+Z` up
- Meters internally, degrees for servo I/O, seconds for time

### Servo convention

MG996R, 180° range. Neutral pose = `yaw=90°, pitch=90°` (paddle sweeps forward in the vertical X-Z plane). Yaw decreases toward `-Y` (right); pitch increases as the sweep plane tilts up. `ServoAngles` validates the `[0, 180]` range.

### Value-object pattern (mandatory)

- **All value objects are pydantic v2 `BaseModel` with `model_config = ConfigDict(frozen=True)`.** Do **not** use `@dataclass`.
- Range/sanity checks go in `@field_validator`, not `__post_init__`.
- **Pydantic constructors are keyword-only at all call sites** — write `Position3D(x=0.1, y=0.0, z=0.0)`, never `Position3D(0.1, 0.0, 0.0)`. The pydantic.mypy plugin enforces this.
- Because models are frozen, validators raise `ValidationError` (wrapping the underlying `ValueError`). Tests that exercise validation must `pytest.raises(ValidationError, ...)`, not `ValueError`.

### Controller pattern

Controllers (e.g. `AimController`) are **stateless apart from injected configuration** (`TurretGeometry`). One instance is reused across many `compute()` calls. Reachability checks return `None` rather than raising; the caller decides what to do.

### Hardware abstraction (applies to every future driver under `src/mcenroebot/drivers/`)

- Every GPIO-touching driver defines a `Protocol` interface plus a `Mock<Name>Driver` implementation that records calls for assertions.
- The control loop and all higher-level modules are tested against mocks only. Real drivers are exercised only on the Pi and gated behind `@pytest.mark.integration`.
- Pi-only Adafruit dependencies live in `[project.optional-dependencies] pi = [...]` and must be imported **lazily inside the driver's `__init__`** so importing the package on a Mac still works without the extra installed.

### Testing rules

- Tests live in `tests/test_<module>.py` with parametrized happy-path + edge-case coverage.
- Pytest config treats warnings as errors (`filterwarnings = ["error"]`), enforces `xfail_strict`, `--strict-markers`, and `--strict-config`. Unknown markers fail the run — declare new markers in `pyproject.toml`.
- Coverage floor is **85%** (`[tool.coverage.report] fail_under = 85`); aim ≥95% on pure-math modules like `aim.py` and `predictor.py`.
- `asyncio_mode = "auto"` — async tests don't need the `@pytest.mark.asyncio` decorator.

### Gitflow

Branches: `main` / `develop` / `feature/*`. Conventional commits enforced by commitizen (`feat(scope):`, `fix(scope):`, `refactor(scope):`, `test(scope):`, `chore:`, `docs:`). Current state: `feature/v4-feeder` (cut from `develop`) carries the V4 feeder build — all software waves (`launch/`, `drivers/feeder` + `drivers/lift`, `drill/`, `coordinator/feeder.py`, the `scripts/calibrate_*` bring-up scripts, and `player/` + `VisionPlacementStrategy`) are committed. The plan is to merge `feature/v4-feeder` → `develop` after the Wave 5 hardware phase gate passes (live feed on the Pi); see [`docs/v4-bringup-checklist.md`](docs/v4-bringup-checklist.md) for the remaining hardware steps.

## Python version note

The project runs on **Python 3.13** for both local dev and the Raspberry Pi deploy (provisioned via a uv-managed 3.13 interpreter, not Bookworm's system Python 3.11). `.python-version` pins 3.13 and pre-commit hooks run under 3.13; provision it with `uv python install 3.13` if it isn't already present.

One intentional remaining drift: `pyproject.toml` still declares `requires-python = ">=3.11"` and mypy/ruff still target `py311`, so type/lint checks run against the 3.11 feature set even though the interpreter is 3.13. Raising those to `>=3.13`/`py313` is a separate config change, deliberately out of scope here. (Note: under a 3.13 venv `uv` installs numpy ≥2.5, whose stubs need a `py312`+ mypy target — if you hit a mypy numpy-stub syntax error, that's the cause.)
