# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

McEnroe is a hobby ping-pong robot. V2 is the **aim-and-swat** phase: a 3-axis turret with two MG996R servos (J1 yaw, J2 pitch) for aiming, and an A2212 1000 KV brushless motor driven by an ESC (J3) for an **open-loop** paddle swing. Deploy target is a Raspberry Pi 4 with an Adafruit PCA9685 PWM HAT at I2C `0x40` (pan=ch0, tilt=ch1, BLDC ESC=ch2). Single Logitech webcam at `/dev/video0` — depth is recovered monocularly from apparent ball radius.

**`V2_PLAN.md` is the source of truth** for module specs, wave structure, and hardware mapping. Read it before adding new modules; the existing source only covers the `aim.py` slice.

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

Branches: `main` / `develop` / `feature/*`. Conventional commits enforced by commitizen (`feat(scope):`, `fix(scope):`, `refactor(scope):`, `test(scope):`, `chore:`, `docs:`). Current state: `feature/aim` is ahead of `develop`; the plan is to merge it once the pydantic refactor is verified, then cut `feature/v2-control` from `develop` for the wave-based module build-out described in `V2_PLAN.md` §5.

## Python version note

`.python-version` pins 3.10 for local dev, but `pyproject` targets 3.11 (mypy/ruff), pre-commit hooks run under 3.13, and the Pi runs Bookworm's 3.11. Code must work on 3.10+; don't use 3.11-only syntax.
