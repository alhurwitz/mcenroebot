# McEnroe V3 — Defensive-Competitive Ping Pong Robot

Builds on [`V2_PLAN.md`](V2_PLAN.md). V2 was aim-and-swat: can make contact with a ball passing through a fixed strike plane, swing is open-loop, returns are uncontrolled. V3 is a **defensive competitive opponent** — robot that reliably returns most balls within reach with controlled trajectory (no lobs), can chase the ball along its end of the table, and runs a learned policy for the swing decision.

Read V2_PLAN.md first for the design rationale and existing module specifications; this document is the V3 build plan.

---

## 0. Context

**Goal:** A robot that plays defensive competitive ping pong. The robot's job is to *return* the ball — not to win points by attacking. It loses points when AJ hits placements it mechanically can't reach (drop shots, lobs, sharp angles), not when AJ hits it cleanly past. Think "wall that gives the ball back," Murray to AJ's Federer.

**Non-goals for V3:**
- Spin generation (paddle face is controllable mid-stroke via wrist servo, but no advanced spin shots)
- Smashing / offensive shot selection
- Multi-stroke variety (forehand vs backhand vs lob defense)
- Beating AJ at AJ's best — explicitly out of scope (see §9)

**Budget envelope:** $500–$1,500 incremental over V2. Targeting ~$500–$700 for the core build.

**Working directory:** `/Users/alberthurwitz/Projects/mcenroebot` (same as V2). Branching plan in §7.

---

## 1. Target performance

Quantitative targets the final V3 should hit, measured against AJ's normal recreational play (not AJ's full effort):

| Metric | Target | Notes |
|---|---|---|
| Return success rate (ball within reach) | 80–90% | "Within reach" = anywhere along the linear axis, within turret aim envelope |
| Return trajectory | Flat or slight topspin | Net clearance 5–15 cm above the net, lands on AJ's side within 30 cm of the far edge typically |
| Rally length | 8–20+ shots | Long enough that AJ has to actively try to win points |
| Latency (camera → motor command) | <100 ms | Includes prediction, policy inference, motor command issuance |
| Reach (along table edge) | ~1.5 m | Full width of one table-end |
| Reach (depth from net) | Fixed strike plane | No depth chase — accept this limitation |
| Point share against AJ's normal play | 25–40% to robot | Robot defends, AJ attacks |
| Point share against AJ's full effort | 5–15% to robot | Honest expectation — see §9 |

---

## 2. Architecture overview

V3 = V2 turret + closed-loop swing + linear axis + wrist + RL policy.

```
                      [ AJ ]
                        │
              ╔═════════╧═════════╗
              ║   PING PONG TABLE  ║
              ╠═══════════════════ ╣
                        │
                 [ robot side ]
   ◄───────────── 1.5 m linear rail ─────────────►
              │           │            │
              │    [ V2 turret    ]    │   ← rides on carriage
              │    [   on cart    ]    │
              │           │            │
              │           ▼            │
              │      ┌────────┐        │
              │      │ closed │        │
              │      │ loop   │        │  ← gimbal BLDC + AS5600 encoder
              │      │ swing  │        │
              │      └───┬────┘        │
              │          │             │
              │      [ wrist servo ]   │  ← small servo for paddle-face angle
              │          │             │
              │      [ paddle ]        │
```

Major changes vs V2:

1. The whole V2 turret (base plate, yaw bracket, pitch bracket, swing arm, paddle clamp) is mounted on a **moving carriage** on a 1.5 m linear axis at the back edge of the table.
2. The A2212 BLDC + ESC is replaced by a **brushless gimbal motor + AS5600 magnetic encoder + SimpleFOC controller** on an STM32 microcontroller. Closed-loop position control of the paddle.
3. A small **wrist servo (MG90)** between the swing arm and the paddle clamp lets the paddle face tilt independently of the swing arm angle.
4. The control loop runs a **learned policy** (PPO trained in PyBullet sim) instead of the open-loop `SwingProfile`.

---

## 3. Hardware additions and BOM

| Item | Purpose | Est. cost (USD) |
|---|---|---|
| **Closed-loop swing module** | | |
| BGM4108-130 (or equiv) brushless gimbal motor | J3 swing, replaces A2212 | $40 |
| AS5600 magnetic encoder breakout + diametric magnet | Paddle angular position feedback | $10 |
| STM32 "Blue Pill" or Bluepill+ (F103) | SimpleFOC controller runtime | $15 |
| Dual L6234 / DRV8313 driver board | 3-phase motor driver for gimbal motor | $15 |
| 12V 3A bench PSU (or repurpose existing) | Gimbal motor power | $20 |
| **Wrist axis** | | |
| MG90S micro servo | Paddle-face angle (±45° range) | $5 |
| 3D-printed wrist bracket (`06_wrist_yoke.stl`) | Couples swing arm to paddle clamp via servo | $0 (print) |
| **Linear axis** | | |
| NEMA 17 stepper motor (1.8°, ~45 N·cm) | Carriage drive | $20 |
| TMC2209 stepper driver (silent, microstepping) | Motor driver | $10 |
| 1.5 m V-slot 2040 aluminum extrusion | Carriage rail base | $50 |
| 2× 1.5 m MGN12 linear rails + carriages | Precision motion | $80 |
| GT2 belt (3 m) + 20T pulley + tensioner | Belt drive | $20 |
| End caps, motor mount, idler pulley bracket | Mechanical assembly | $30 |
| Limit switches (2, end-of-travel) | Homing / safety | $5 |
| Raspberry Pi GPIO → step/dir pulse generator (or use PCA9685 spare) | Step pulse source | $0 (reuse) |
| **Carriage adaptor** | | |
| 3D-printed carriage plate (`07_carriage_plate.stl`) | Bolts MGN12 carriages to V2's `01_base_plate.stl` | $0 (print) |
| **Misc** | | |
| Drag chain for cables | Cable management as carriage moves | $15 |
| Extra 5V/3A PSU | Wrist servo + logic power | $15 |
| Hardware (M3/M4 screws, T-nuts, brackets) | Fastening | $20 |

**Subtotal:** ~$370–$430 for parts + ~$50 contingency = **$450 target**, $600 worst case.

**Reused from V2 (nothing new bought):**
Raspberry Pi 4, PCA9685 HAT, MG996R servos (J1 yaw, J2 pitch — kept), Logitech webcam, 3S LiPo + B6 charger, 608ZZ bearings, F-clamps, plywood base, hardware kits, V2 3D-printed brackets (01–05).

**Deliberately skipped for V3 (deferred to V4):**
- Faster aiming servos (DS3225 etc.) — MG996Rs are *just* fast enough at recreational pace
- Higher-fps camera (Pi Global Shutter, Arducam B0392) — defensive play tolerates 30 fps OK
- Z-axis (vertical reach) — accepts loss to lobs and drop shots
- Multi-camera / stereo — monocular depth from ball radius is adequate for V3

---

## 4. Software architecture

V3 adds three new packages and modifies two existing ones. Layout under `src/mcenroebot/`:

```
mcenroebot/
├── aim/            (V2, unchanged)
├── ball/           (V2, unchanged)
├── camera/         (V2, unchanged)
├── clock/          (V2, unchanged)
├── predictor/      (V2, unchanged)
├── calibrate/      (V2, unchanged)
├── drivers/
│   ├── servo/      (V2, unchanged — still drives J1, J2, and new wrist)
│   ├── bldc/       (DEPRECATED — replaced by foc/ in V3; kept on develop until V4 migration)
│   ├── foc/        (NEW — SimpleFOC-over-serial driver for closed-loop swing motor)
│   └── stepper/    (NEW — TMC2209-over-step/dir driver for the linear axis)
├── swing/          (REPLACED — was open-loop SwingProfile; now wraps the closed-loop FOC driver)
├── linear/         (NEW — carriage controller, homing, position planner)
├── wrist/          (NEW — paddle-face servo controller)
├── policy/         (NEW — three-layer policy stack; see §5)
├── sim/            (NEW — PyBullet world + episode runner + training infrastructure; dev-machine only)
└── coordinator/    (MODIFIED — now wires predictor → policy → {aim, linear, swing, wrist})
```

Each package follows V2's convention: directory with `__init__.py`, split files (protocol.py, real impl, mock impl, value objects, `__main__.py` for demo), tests under `tests/test_<name>/`.

### 4.1 `drivers/foc/`

Closed-loop swing motor driver. SimpleFOC runs on the STM32, exposes a serial protocol; the Pi talks to it via USB-serial.

```python
class FocDriver(Protocol):
    def home(self) -> None: ...                          # set current position as zero
    def move_to(self, angle_rad: float) -> None: ...     # blocking move with PID
    def velocity(self, omega_rad_s: float) -> None: ...  # constant velocity command
    def stop(self) -> None: ...
    @property
    def position_rad(self) -> float: ...                 # latest reported position
    @property
    def velocity_rad_s(self) -> float: ...

class SerialFocDriver:
    def __init__(self, port: str = "/dev/ttyACM0", baud: int = 115200): ...

class MockFocDriver:
    """Records all commands for tests; simulates the position trajectory."""
```

### 4.2 `drivers/stepper/`

```python
class StepperDriver(Protocol):
    def home(self) -> None: ...                          # rapid until limit switch
    def move_to_m(self, x_m: float) -> None: ...         # blocking position move
    def set_velocity(self, v_mps: float) -> None: ...    # constant velocity
    @property
    def position_m(self) -> float: ...

class TMC2209StepperDriver:
    """GPIO step/dir pulse generator, optionally with UART feedback for current limit."""
    def __init__(self, step_pin: int, dir_pin: int, enable_pin: int, steps_per_m: float): ...

class MockStepperDriver: ...
```

### 4.3 `swing/`

Replaces V2's `SwingProfile` + open-loop `SwingController`. New API:

```python
class SwingCommand(BaseModel):
    model_config = ConfigDict(frozen=True)
    target_angle_rad: float    # paddle angle at strike (in swing arm frame)
    target_velocity_rad_s: float  # angular velocity at strike
    fire_time: float           # absolute time to start the swing
    wrist_angle_rad: float     # paddle face angle relative to swing arm

class SwingController:
    """Closed-loop swing. Pre-positions paddle, then accelerates to target
    velocity at fire_time, hitting target_angle with target_velocity at T0."""
    def __init__(self, driver: FocDriver, wrist: WristController, clock: Clock): ...
    async def execute(self, cmd: SwingCommand) -> None: ...
```

### 4.4 `linear/`

```python
class LinearCarriage:
    """1-DOF cart along table edge. Position 0 = home (left limit)."""
    def __init__(self, driver: StepperDriver, max_velocity_mps: float = 1.0): ...
    async def go_to(self, x_m: float) -> None: ...
    async def home(self) -> None: ...
    @property
    def position_m(self) -> float: ...
```

### 4.5 `wrist/`

Thin wrapper around `ServoDriver` for the MG90 on a dedicated PCA9685 channel.

### 4.6 `policy/`

Three implementations behind a single Protocol — the key V3 abstraction. See §5.

### 4.7 `sim/`

Dev-machine only — not deployed to Pi. PyBullet world with:

- Ball: point mass + drag + (optional) Magnus force
- Table: plane primitive with COR
- Paddle: flat plate primitive with COR
- Robot: kinematic model matching real geometry (V2 turret on linear carriage)
- Opponent: scripted ball server that varies launch position, velocity, spin

```python
class PingPongSim:
    def reset(self) -> Observation: ...
    def step(self, action: SwingCommand) -> tuple[Observation, float, bool, dict]: ...
    # Standard Gymnasium-compatible env interface
```

### 4.8 `coordinator/`

Modified `RallyCoordinator`:

```python
class RallyCoordinator:
    def __init__(
        self,
        aim: AimController,
        predictor: TrajectoryPredictor,
        policy: Policy,                       # NEW
        carriage: LinearCarriage,             # NEW
        servo_driver: ServoDriver,
        swing: SwingController,
        wrist: WristController,               # NEW
        clock: Clock,
        ...
    ): ...
    async def step(self, obs: BallObservation) -> None:
        """1. push observation to predictor
           2. if prediction available: ask policy for SwingCommand
           3. dispatch carriage move, turret aim, wrist preset
           4. fire swing at SwingCommand.fire_time"""
```

---

## 5. The three-layer policy stack

V3's centerpiece. Each layer is a drop-in replacement for the previous, sharing a Policy Protocol:

```python
class Policy(Protocol):
    def act(
        self,
        prediction: StrikePrediction,
        robot_state: RobotState,
    ) -> SwingCommand | None: ...
```

### 5.1 `HeuristicPolicy` (Phase A)

Hand-tuned rules. **Ships first** so we have a working baseline before any learning. Examples:

- If ball arrives <0.8 m/s, set wrist to +5° (slight upward); else 0°
- Always strike at `paddle_angle_at_strike = π/2` (paddle horizontal, moving forward)
- Always strike at `paddle_velocity = 4 rad/s` (medium swing)
- Always target the center of opponent's side

Maybe 100 lines of code. Plays "competently dumb" — returns balls, slightly inefficient.

### 5.2 `AnalyticalPolicy` (Phase B)

Closed-form trajectory optimization. Given the predicted ball state and a desired landing point (e.g. far baseline center), solve for paddle face angle and velocity that produces a ball trajectory landing there. Uses the same ballistic + Magnus model the predictor uses (inverted).

This is the **strong baseline** for the RL policy to beat. In practice, an analytical policy often gets 80%+ of the RL ceiling on this kind of low-dim control problem.

### 5.3 `LearnedPolicy` (Phase C — the RL piece)

PPO-trained neural network. Architecture:

- Observation (~20 dims): predicted strike state (x, y, z, vx, vy, vz, time-to-impact, confidence), robot state (carriage position, J1, J2 angles, paddle angle, wrist angle, ready/busy flag), opponent indicator features (recent ball variance)
- Action (~5–6 dims, continuous, bounded): target paddle angle, target paddle velocity, wrist angle, carriage target offset, fire time delta
- Reward: +1 ball returned over net + on opponent's side; -1 missed/out; +shaping for low-arc trajectory + small action-magnitude penalty

Training:

- **Sim:** PyBullet world from §4.7
- **Algorithm:** PPO via stable-baselines3 (well-tested), 1–2M steps, runs overnight on a laptop GPU
- **Domain randomization:** ball mass (2.5–2.8 g), drag (±20%), paddle COR (0.80–0.92), servo latency (10–80 ms), motor torque (±20%), camera observation noise (Gaussian σ varied), table COR
- **Curriculum:** start with slow balls and narrow placement variance; ramp up speed/variance over training
- **Sim-to-real transfer:** deploy policy, log real-world rallies, retrain with parameters tuned to observed system. Two or three iterations of this typically closes the gap.

The learned policy gets loaded from a checkpoint at runtime; inference is a single PyTorch forward pass (~1 ms on Pi 4 CPU).

### 5.4 Why layer them

- **Baseline guarantee.** If the RL pipeline takes longer than expected (it will), V3 still ships with the analytical policy working. The hardware payoff doesn't depend on the RL payoff.
- **A/B comparison.** You get a real measurement of how much the RL adds over hand math. That's the interesting research finding even if both work.
- **Debugging.** When the RL policy misbehaves on real hardware, you can swap back to analytical to isolate "is this an RL problem or a hardware/sim problem?"

---

## 6. Build phases (waves)

### Wave 0 — V2 baseline lockdown (this week, prereq)

Open the PR `feature/v2-control` → `develop` from current state. Run hardware once on the Pi to confirm V2 actually works end-to-end. Camera-calibrated. We need a **working V2** before we start replacing parts.

### Wave 1 — Closed-loop swing module (~2 weeks, $80–150 hardware)

1. New packages `drivers/foc/` + modified `swing/` with mock-driver tests.
2. Flash SimpleFOC onto STM32 with a serial command protocol.
3. Bench-test the gimbal motor + encoder closed-loop without paddle.
4. Mechanical: 3D-print a mount that replaces the A2212 in the V2 `03_pitch_bracket.stl` (parametric — regenerate via `generate_parts.py` with new constants).
5. Mount paddle, characterize step-response and bandwidth.
6. **Phase gate:** can the closed-loop swing land at a commanded `(angle, velocity)` within ±5° and ±0.5 rad/s of target on a stationary turret? If yes, proceed.

### Wave 2 — Wrist axis (~1 week, $5 hardware)

1. New package `wrist/` with mock-driver tests.
2. Mechanical: print `06_wrist_yoke.stl` — couples swing arm tip to paddle clamp via the MG90 servo.
3. Bench-test wrist range and accuracy.
4. **Phase gate:** can the wrist hold an arbitrary face angle in the range [−45°, +45°] within ±2°?

### Wave 3 — Linear axis (~3 weeks, $300–400 hardware)

This is the biggest mechanical build.

1. New packages `drivers/stepper/` + `linear/` with mock-driver tests.
2. Mechanical: V-slot extrusion bed, MGN12 rails, GT2 belt, NEMA17 + TMC2209 wiring.
3. 3D-print `07_carriage_plate.stl` to adapt MGN12 carriages to V2's `01_base_plate.stl`.
4. Limit-switch wiring + homing routine.
5. Calibrate steps-per-meter empirically.
6. **Phase gate:** can the carriage move to a commanded position in [0, 1.5] m within ±2 mm in <1 s?

### Wave 4 — Coordinator integration with `HeuristicPolicy` (~1 week, no hardware)

1. New package `policy/` with `HeuristicPolicy` only.
2. Modify `coordinator/` to wire all V3 axes together.
3. Integration tests with mock everything.
4. **Phase gate:** can the simulated rally coordinator return balls back over the net in 100/100 deterministic test cases?

### Wave 5 — First live rally (~1 week, no hardware)

1. SSH/deploy to Pi.
2. Wire all hardware: V2 turret on carriage, FOC over USB-serial, stepper via GPIO, wrist on PCA9685 spare channel.
3. Run rally with heuristic policy.
4. **Phase gate:** robot makes contact with >50% of balls AJ feeds at slow-medium recreational pace, returns at least 25% over the net. **Champagne moment.**

### Wave 6 — `AnalyticalPolicy` (~2 weeks, no hardware)

1. Closed-form trajectory inversion in `policy/analytical.py`.
2. A/B vs heuristic in offline tests + live rally.
3. **Phase gate:** analytical policy beats heuristic by ≥15% on return-success-rate over a 100-rally test.

### Wave 7 — `LearnedPolicy` (RL) (~4–8 weeks, no hardware initially)

1. Build `sim/` PyBullet world.
2. Implement PPO training loop with `stable-baselines3`.
3. Domain randomization config.
4. Train overnight; iterate on reward shaping.
5. Deploy checkpoint; collect real-world rally logs.
6. Sim-to-real iteration (2–3 cycles).
7. **Phase gate:** RL policy beats analytical by ≥10% on return success rate AND matches or beats it on average rally length.

### Wave 8 — Polish (~2 weeks)

Robust failure modes (lost predictions, overrun limit switches, paddle wedged at top of arc, etc.), audio cues / trash talk integration, README updates, demo video.

**Total V3 timeline:** roughly 4–6 months at evening pace. Hardware-build is the early gating factor; RL is the long-tail risk.

---

## 7. Branching strategy

```
develop (V2 complete)
   │
   ├── feature/v3-foc        — Wave 1
   ├── feature/v3-wrist      — Wave 2
   ├── feature/v3-linear     — Wave 3
   ├── feature/v3-policy     — Waves 4 + 6 (heuristic + analytical)
   ├── feature/v3-sim        — Wave 7 (sim + PPO training, dev-only)
   └── feature/v3-integrate  — Wave 5 + 8
```

Each merges into `develop` after its phase gate is green. V3 production-release tag once all eight waves land.

---

## 8. Sim-to-real strategy

The single largest risk on V3 is the sim-to-real gap. Mitigation:

1. **Build sim AFTER hardware exists, not before.** This is counter to most RL projects but crucial here. Real-world measurements (servo step response, motor latency, paddle COR, table COR, lighting/camera noise) feed directly into sim parameter ranges. Sim built in a vacuum is fiction.
2. **Domain randomization is non-negotiable.** Single-parameter sim policies overfit and break on contact with real-world variance.
3. **Validate sim against real rallies regularly.** Periodically run a "sim replay" of a logged real-world rally and compare predicted vs actual ball trajectory. If sim diverges, fix sim before training new policies.
4. **Keep the analytical policy as the safety net.** If RL goes off the rails after sim-to-real, fall back.

---

## 9. Open questions and honest limitations

### 9.1 What V3 will *not* do

- **Spin estimation from incoming ball.** Requires 60+ fps stereo or DVS camera. Deferred to V4.
- **Lob defense or drop-shot defense.** No Z-axis = no vertical reach. Deferred to V4.
- **Multiple shot types (smash, slice).** Defensive scope only.
- **Beating AJ at AJ's best.** That's V4+ territory: high-fps cameras, possibly a full multi-DOF arm, and offensive shot selection. V3 is the foundation for that, not the destination.

### 9.2 Risks specific to V3

- **Closed-loop swing tuning.** Gimbal motor + AS5600 + SimpleFOC is well-trodden territory (lots of community resources), but tuning the PID gains for a paddle-loaded arm with high-impulse strikes is non-trivial. Budget extra time on Wave 1.
- **Belt-driven linear axis precision under acceleration.** 1.5 m belt at high carriage acceleration can introduce position errors >5 mm if belt tension drifts. May need ballscrew or rack-and-pinion in V3.5 if precision turns out to be insufficient.
- **Mechanical latency stacking.** Camera (33 ms) + prediction (5 ms) + policy (1 ms) + serial comms (5 ms) + motor response (20 ms) + mechanical (15 ms) ≈ 80 ms total. Tight against the 100 ms target. Need to measure on real hardware and budget aggressively.
- **PPO + sim-to-real overrun.** This kind of project routinely overruns. Wave 7 is timeboxed at 4–8 weeks; if it goes past 12, ship V3 with the analytical policy and call the RL pass V3.5.

### 9.3 Things to revisit after Wave 5 (first live rally)

- Is MG996R aim speed adequate, or do we need DS3225 servos? (V3.5 add-on if needed.)
- Is 30 fps camera adequate, or do we need 60+ fps for prediction tightness? (V3.5 add-on if needed.)
- Does the gimbal motor have enough torque for paddle-load impact, or do we need a bigger one? (Could redesign Wave 1 hardware in V3.5.)

---

## 10. Success criteria for the whole of V3

V3 is "done" when:

1. The robot rallies with AJ for ≥10 consecutive shots in a row, more than once per session, at recreational pace.
2. AJ wins games against the robot by *placement* (drop shots, corners, lobs), not by *power* (clean drives).
3. The RL policy has been shown to beat the analytical baseline by a measurable margin (≥10% return success rate) on a fixed 100-rally test set, OR we've documented in the codebase exactly why it doesn't and what V4 would need to change.
4. The full test suite is green; coverage stays ≥85%; the README documents the deploy + calibrate + play workflow.

That's the goal. V4 is a separate document, written after V3 ships.
