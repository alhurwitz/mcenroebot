# v4-enclosure-plan.md

Cosmetic enclosure ("the costume") for the V4 feeder machine: a humanoid John McEnroe shell
that the launcher fires **out of the stomach**. This is purely a shell on top of the existing
hardware — it does not touch any bring-up work. The launcher subassembly is identical wherever
it sits inside the costume.

All dimensions below are **nominal — confirm against your actual Amazon parts before printing.**
Ball reference: 40 mm.

---

## 0. The two decisions that drive everything

1. **The head is cosmetic. The face does NOT move with the launcher.**
   The aim head is three MG996R servos (pan ch0 / tilt ch1 / head-roll ch2) on a 5V/3A rail
   already flagged as marginal. Bolting a head shell to that plate cantilevers mass onto
   barely-sized servos and — worse — the head-roll axis would barrel-roll the whole face on every
   sidespin shot, eating spin authority and tangling cables. So the face is a static shell.

2. **The ball exits the stomach, not the mouth.**
   Moving the exit off the face frees the head completely (no aperture compromise, no
   static-vs-moving fight) and matches where the hardware already wants to be. The machine stacks
   vertically (trough → auger → hopper → escapement → launcher), so the launcher already sits at
   ~torso height to clear the net. Firing from the gut is where it naturally lands — and is
   on-brand for McEnroe rage.

   **Launch-height reconciliation (load-bearing for the software).** The stomach exit *sets*
   `LaunchGeometry.launch_height_m`, which is currently the 0.3 m placeholder. A torso-height exit
   (~0.7–0.9 m) is far higher and changes the ballistics: a near target on a 0.76 m table may need
   the ball fired level or angled *down* — an elevation below `pitch_neutral_deg` — which can drive
   the tilt-servo angle out of [0, 180] so `tilt_angle_for` returns None and the shot is skipped.
   So the frame must commit to a **measurable** exit height; then update `launch_height_m`, define
   the robot-frame origin relative to the build, and re-run `python -m mcenroebot.coordinator` to
   confirm tilt stays in range across the intended target depths. If a down-angle is needed, mount
   the launcher slightly nose-down and/or set `pitch_neutral_deg` so that elevation still maps
   inside the servo range.

Rejected alternatives: **mouth exit** (forces a static-vs-moving compromise on the head),
**chest** (fine, marginally higher net clearance, second choice), **tweener / between-the-legs**
(cute theme, but low launch height forces an upward fire angle and the leg clearance gets fussy),
**hands/racket** (looks great, mechanically impossible — launcher too heavy for an arm, and
ducting the ball post-wheels destroys spin/accuracy; keep a racket as pure decoration only).

---

## 1. Four-zone torso layout

The torso divides into four zones that don't fight each other:

| Zone | Contents | Why there |
|---|---|---|
| **Head** | ELP stereo camera (the eyes) | High vantage, looks down at the landing zone |
| **Chest / neck** | Hopper cone (~80 balls, ~200×250 mm) | Gravity-feeds straight down into the escapement |
| **Mid-torso** | Launcher: 2 wheels + 2 motors, pan/tilt/head-roll, escapement | Fires out the **stomach**. This is the **swing cone** — nothing else may intrude |
| **Lower belly + rear back** | Electronics tray + ESC rack (Pi+PCA9685, 4 ESCs, L298N, bucks) | Sits **under** the swing cone; heat exhausts up the back |
| **Base drawer** | LiPo (pull-out at the waistband) | Low CG, swappable, kept away from ESC heat |

### Hard constraints

- **Swing cone is sacred.** As the launcher pans (±~20°) and tilts, the wheels + motors sweep a
  forward wedge in the mid-torso. Electronics live **below and behind** that wedge, never inside
  it. Model the swept volume first; treat it as a keep-out.
- **Feed coupling survives aiming.** The escapement is rigidly coupled to the wheel nip and pans/
  tilts **with** the launcher, so the ball-drop-into-nip geometry stays invariant under aim. The
  fixed hopper therefore cannot feed "straight down" into a moving intake — it must terminate in an
  oversized funnel whose outlet covers the escapement intake's **full swept area** across pan and
  tilt, bridged by a soft boot. Model the swept intake and size the funnel to it.
- **Camera isolation + stability.** The head camera is otherwise bolted to the same frame as two
  ~10,000-rpm BLDCs — isolate it on compliant mounts or the stereo feed blurs and `SimpleBlobDetector`
  suffers. And the tall shell with ~80 balls high in the chest is top-heavy: give the base a wide
  enough footprint and low enough CG (the LiPo drawer helps) to absorb firing recoil without wobble.
- **Heat vs battery separation.** The ESCs (×4 at 30 A) and the L298N are the heat sources. The
  LiPo gets its own cool drawer, physically separated, with the XT60 reachable for charging
  without disassembly.

---

## 2. Electronics inventory + bay requirements

Confirm every dimension against your actual parts (you source on Amazon and want drop-in fits).

| Component | Qty | Nominal size (mm) | Mount / access needs |
|---|---|---|---|
| Raspberry Pi 5 | 1 | 85 × 56, holes 58×49 (M2.5) | Standoffs; USB edge free for camera; power edge free; airflow |
| PCA9685 servo HAT | 1 | stacks on Pi GPIO | ~40 mm vertical clearance above Pi for the stack |
| 30 A ESC | 4 | ~52 × 26 × 8 (+ leads) | Edge-mounted in a vented rack with air gaps; leads route up to motors |
| L298N (auger driver) | 1 | 43 × 43 × 27 (heatsink) | Posts at corner holes; heatsink needs air; GPIO18 PWM in, ENA out |
| 12 V buck (auger/L298N supply) | 1 | ~43 × 21 × 14 | Clip slot or 2 posts |
| 5 V BEC (servo rail, maybe 5A) | 1 | ~30 × 20 | Clip slot or 2 posts |
| Escapement servo (cont. rotation, ch5) | 1 | 40 × 20 × 40 | At the hopper floor, not in the bay |
| Auger gearmotor (12 V ~60 rpm) | 1 | ~Ø37 × 70 | On the auger/spine, not in the bay |
| CNHL 2200 mAh 3S LiPo | 1 (of 2) | ~72 × 35 × 30 | Pull-out drawer; XT60 strain relief; reachable for B6 charging |
| ELP dual-OV9281 stereo cam | 1 | ~100 × 15 bar | In the head behind the eye sockets; USB down to Pi |

**Power domains** (single 3S LiPo source):
- 11.1 V → 4× ESC (motors)
- 11.1 V → 12 V buck → auger gearmotor + L298N
- 11.1 V → 5 V BEC → Pi + PCA9685 logic + servo rail

**Cable runs the bay must provide ports for:**
- Up to launcher: 4× ESC→motor leads, 3× servo leads (pan/tilt/roll), escapement servo lead
- Down to base: L298N→auger leads, 12 V buck feed, LiPo XT60 from the drawer
- Head: camera USB down to a Pi USB port
- Pi → PCA9685: I2C (on the HAT stack); Pi GPIO18 → L298N ENA

---

## 3. Stomach exit port

Same aperture logic as the rejected mouth, but bigger and far more forgiving because the torso
panel is a large flat area.

- Size the bore to pass the **full pan/tilt aim cone** with margin. The exit point swings on the
  pan arc (≈ r·sinθ ≈ ±20 mm for r≈60 mm, ±20° pan) plus the ray spread — a generous port covers
  it with room to spare.
- Place the port plane **just forward of the wheel exit**, centered on the neutral aim ray, so the
  ball clears before the trajectory diverges.
- **Slope the lower lip out-and-down** (the one real gotcha): a weak dribbler must fall clear of
  the machine, not roll back into the throat. The lower lip = jam insurance.
- **Aim-envelope note:** the port must pass the full pan **and tilt** cone — tilt now varies per
  shot via the ballistic solver, so it is not a fixed angle. Also note ±~20° pan covers only ~±0.7 m
  lateral at 2 m range (about half a table width); confirm that matches the court coverage you want
  before fixing the gimbal, since widening it later is a redesign.
- Disguise: untucked-shirt gap or the waistband gap above the shorts.

---

## 4. Free integrations the build hands you

- **Eyes = the stereo camera.** Two OV9281 lenses → two eyes. Mount the ELP bar behind the eye
  sockets; vision placement gets a forward/down view and the face gets its most recognizable
  feature for free.
- **Caricature, not replica** (easier to print, keeps it homage): 80s perm as the top/back shell,
  **red headband across the brow** printed as a separate red part that also covers the seam
  between face-front and hair-back shells (identity + seam-hide + easy color = one part), polo
  collar as the base ring.
- **Ventilation** hidden in the hair texture or behind the headband; exhaust up the back over the
  ESC rack.
- **Audio (ties into V3 personality roadmap):** small speaker behind the mouth → "you cannot be
  serious!" as the fault/let trigger.

---

## 5. Print + assembly plan

- Bigger than the 256 mm bed, so split: **face-front, hair/back, headband, collar, torso-front,
  torso-back, base/drawer.** Registration pins + screw bosses between sections.
- Cosmetic shell: thin wall (1.2–2 mm), PLA is fine (static, no wear), hollow.
- Face-front prints on its back; split the nose on the centerline to kill the overhang.
- **Service access:** face-front and torso-back panels on magnets or screws so you can pull them to
  clear a throat jam and reload the hopper.
- Functional internals (electronics tray, ESC rack, drawer, port ring): PETG where it carries load
  or sees heat (ESC rack, drawer rails).

---

## 6. Workflow split

- **Functional internals → parametric generator** (trimesh, same pattern as
  `generate_auger_wide.py`): electronics tray with sized standoffs + cutouts, vented ESC rack,
  battery drawer + rails, stomach port ring sized to the real aim cone, shell registration tabs.
- **Organic shell (face/hair/torso) → Blender** (via the Blender MCP bridge): sculpt, then
  boolean the registration/mount features from the generator onto it.

---

## 7. Open items

- **Launch height + tilt range (do this first):** commit a measurable stomach exit height, update
  `LaunchGeometry.launch_height_m` (replacing the 0.3 placeholder), define the robot-frame origin on
  the build, and re-run the coordinator demo to confirm `tilt_angle_for` stays in [0, 180] across
  target depths. Adjust `pitch_neutral_deg` / mounting if a down-angle is needed.
- **Feed coupling:** lock the escapement-moves-with-the-launcher decision and size the hopper funnel
  + soft boot to cover the intake's full swept area; model the swept intake volume.
- **Servo torque:** verify a single MG996R can pan/tilt the full aimed mass (2 motors + 2 wheels +
  escapement) at its moment arm. If marginal, plan a stronger servo or a counterbalance — this ties
  to the 5V-rail current note below.
- **Camera isolation:** compliant head mount so motor vibration doesn't blur the stereo feed.
- **Servo rail current:** 5V/3A is fine for bring-up; a fully loaded head may want 5 A. Bay layout
  unchanged, just the BEC.
- **Swing-cone keep-out volume** measured off the assembled launcher before finalizing tray
  height/position.
- **Confirm part dimensions** against actual hardware before printing the tray (sizes here are
  nominal).

**Resolved (were open):** second launch motor — two motors are mounted and spinning; second-ESC
blocker — four ESCs on hand.
