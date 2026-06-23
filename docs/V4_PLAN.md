# FEEDER_PLAN.md

Source of truth for the **feeder** architecture — the spin/aim ball machine with a closed
recycle loop. Supersedes the aim-and-swat turret for this build direction. The aim math,
servo conventions, and driver patterns from `V2_PLAN.md` carry over; the rally/strike-plane
prediction path (`trajectory`, `predictor`, `swing`) is shelved, not deleted.

Ball reference: 40 mm diameter, ~2.7 g, ABS. All clearances below assume a 40 mm ball.

---

## 1. Escapement (single-ball feeder)

Meters loose balls from the hopper into the launch throat, one at a time, jam-free.

### Mechanism

Single-pocket **indexing disk** at the hopper floor. One cylindrical pocket scoops a ball at
the load station, carries it ~180°, drops it into the launch throat at discharge. The disk's
solid top face blocks the hopper outlet everywhere except the pocket — so single-ball metering
is **geometric, not timed**. One pocket = one ball per revolution. Fire rate = disk rpm.

### Dimensions

| Part | Value | Notes |
|---|---|---|
| Disk OD | 90 mm | |
| Pocket bore | 42 mm | ball + 2 mm clearance |
| Pocket depth | 22 mm | seats ball, releases clean |
| Hopper cone half-angle | ≥ 60° from horizontal | steep — 40 mm balls bridge easily |
| Disk shaft bearing | 608 (22 OD / 8 bore) | press-fit printed seat |
| Pocket lip | 1 mm chamfer | prevents pinch at load |

### Actuator — v1 vs upgrade

- **v1 (recommended): continuous-rotation servo, fixed rate.** Plugs into the existing PCA9685
  exactly like the aim servos — no new driver concept, no stepper board, no soldering. Run at
  constant speed → constant feed rate (set 40–60 balls/min). The machine just spits periodically,
  like a cheap commercial feeder. Sensorless.
- **Upgrade (only if per-ball timing matters): add one index endstop.** A 3-pin optical endstop
  (3D-printer style, solderless Dupont) trips once per revolution → a real `ball_fired` event.
  Needed only if you want vision placement tightly phased to each shot. Defer.

### Failure modes

- **Hopper bridging** (balls arch over the outlet, feed stops): steep cone + a stir-finger on the
  disk shaft sweeping the hopper floor.
- **Double-feed**: a fixed "roof" over the load station, gap = one ball height, so only one seats.
- **Edge pinch**: keep ≥ 2 mm pocket clearance + lip chamfer.

### Print

Disk face-down on smooth plate (or sand the bearing face), PETG for wear. Hopper as a cone,
printed in sections if it exceeds bed.

---

## 2. Auger lift (trough → hopper)

Returns balls from the floor-level catch trough up to the hopper. One motor, continuous, slow.

### Mechanism

Helical screw inside a close-fitting tube (Archimedes screw). Balls sit between flights and ride
up as the screw turns; the flight below each ball prevents fallback. **Inclined ~50–60°, not
vertical** — gravity seats balls into the flights at entry and stops rattle/fallback.

### Dimensions

| Part | Value | Notes |
|---|---|---|
| Tube ID | 46 mm | ball + 3 mm each side |
| Screw OD | 44 mm | 1 mm gap to tube |
| Screw core rod | 8 mm steel | smooth rod, cheap; screw segments key onto it |
| Flight pitch | 55 mm | > ball dia, so one ball fits per pitch |
| Incline | 50–60° | forgiving entry, fallback-resistant |
| Lift height | hopper inlet − trough | likely 700–900 mm |

### Print (the one fussy part)

Bed is ~256 mm, lift is ~800 mm → **tube + screw print in ~4 sections.**
- Screw: short **keyed segments stacked on the 8 mm steel rod** — do *not* try to print one long
  helix. Each segment prints helix-axis along Z with supports; sand the joints flush (a step at a
  joint catches balls).
- Tube: 4 slip-fit sections + printed external clamps/spine to hold them collinear. A non-straight
  tube jams.
- PETG (the screw rubs).

### Motor

12 V DC gearmotor, ~60 rpm, moderate torque. On/off (PWM optional if too fast). No precision
needed. Drive via a solderless MOSFET module or L298N off a 12 V buck from the LiPo.

### Throughput / why "no refill" works

The lift only has to beat **average** fire rate, not peak. The buffer hopper absorbs the mismatch:

- Hopper buffer: **~80 balls ≈ 4.5 L** (cone ~200 mm dia × 250 mm).
- At 55 mm pitch × 60 rpm the screw advances balls ~3 m/min — comfortably above a 40–60 balls/min
  feed rate, so the hopper stays topped up and you never run dry.
- Overflow path: a lip near the hopper top drains excess back toward the trough, or a hopper-full
  switch cuts the auger. Either is fine; recirculation is simplest.

### Failure modes

- **Ball slips past the screw**: keep tube/screw clearance < ball radius; incline helps.
- **Double-entry jam**: a single-ball lip at the tube mouth meters the entry.
- **Joint step**: sand screw segment joints flush.

### Catch net

**Buy a table-tennis-robot catch net, do not build the funnel.** Robot nets already slope to a
single low collection channel — that solves "gather scattered balls to one point" for you. The
trough sits at that channel and feeds the auger mouth.

---

## 3. New hardware (everything else carries over)

| Item | Qty | For |
|---|---|---|
| Brushless motor matched to A2212 + 30 A ESC | 1 | 2nd launch wheel (you have one set) |
| Grippy launch wheels (~50–60 mm, rubber/foam or TPU+band) | 2 | launch |
| Continuous-rotation servo | 1 | escapement disk |
| 12 V DC gearmotor ~60 rpm + MOSFET/L298N driver | 1 | auger |
| 608 bearings | 2 | disk + auger shaft |
| 8 mm steel rod (~900 mm) | 1 | auger core |
| Table-tennis robot catch net | 1 | catch + funnel |

Aim servos (MG996R ×3: pan, tilt, head-roll), PCA9685 HAT, Pi, LiPo all reused.
**De-risk order: print and bench-test the escapement and the auger as standalone subassemblies
before committing to a frame.** They're the only novel mechanisms; launch wheels are solved.

---

## 4. Control software

Yes, it needs code — but far less than the rally controller, and most drivers carry over. No
real-time vision loop, no strike-plane timing. It's a periodic scheduler + actuator drivers +
a drill library. New/changed packages (same `src/mcenroebot/<name>/` Protocol+Mock pattern):

| Package | State | Role |
|---|---|---|
| `drivers/bldc/` | reuse | throttle the 2 launch wheels via PCA9685 (extends `esc_arm`) |
| `drivers/servo/` | reuse | pan / tilt / head-roll |
| `drivers/feeder/` | new, tiny | escapement: `set_rate()` (v1) or `fire()` (+ index upgrade) |
| `drivers/lift/` | new, tiny | auger motor on/off/PWM, optional hopper-full switch |
| `launch/` | new | pure-math controller: `(speed, topspin, sidespin) → (top_rpm, bottom_rpm, head_roll°)`. Stateless + frozen value objects, mirrors `AimController`; target ≥95% coverage |
| `aim/` | reuse | existing yaw/pitch from a target point = "aim at this court location" |
| `drill/` | new | behavior engine: emits `Shot(speed, spin, target, interval)`; fixed patterns (oscillate / random / figure-8) **plus a pluggable `AimStrategy` Protocol** |
| `coordinator/` | simplify | periodic scheduler ticking the drill → launch + aim + feeder. Not a real-time loop |

Shelved (return-rally only): `trajectory`, `predictor`, `swing`.

---

## 5. Vision placement (the camera's role here)

Two different vision jobs — don't conflate them:

- **Rally-return prediction** (hard, shelved): see the incoming ball in 3D, predict the
  strike-plane crossing in < 100 ms. This is what drove the global-shutter stereo purchase. The
  feeder does not need it.
- **Placement aiming** (easy, and what you're now describing): look at the player / open court,
  decide where to send the *next* fed ball. Forgiving — you have the whole feed interval (1–2 s)
  to grab a frame, find the player, pick a target, and move the aim servos before the next ball
  reaches the wheels. **A single camera + simple player/zone detection is enough. No stereo, no
  3D ball tracking, no sub-100 ms timing.**

Architecturally this is just a `VisionPlacementStrategy` swapped in for `FixedPatternStrategy`
behind the `drill.AimStrategy` Protocol — zero change to the mechanism or the launch math. So:
v1 ships sensorless with fixed patterns; vision placement drops in later as a clean increment.

This does put an *easy* slice of vision back in the control path (last session it was "fully out").
That's fine — it's the slow, forgiving slice, not the hard rally slice.
