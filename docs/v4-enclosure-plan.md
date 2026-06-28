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
   `LaunchGeometry.launch_height_m`, currently the hardcoded 0.3 m placeholder in
   `LaunchController.__init__`. A torso-height exit (~0.7–0.9 m) changes the ballistics materially:
   for a near target the low arc needs a downward fire angle — e.g. a 1 m / 6 m/s shot moves from
   ~81° tilt at 0.3 m to ~58° at 0.8 m, about 20° further nose-down. The solver itself stays in
   range (for any realistic table target the elevation never reaches the −90° that would push
   `tilt_angle_for` outside [0, 180]), so the real constraint is **mechanical**: the head must be
   able to physically tilt that far nose-down, and `pitch_neutral_deg` must be calibrated to the
   actual mount. So the frame must commit to a **measurable** exit height; then update
   `launch_height_m`, define the robot-frame origin relative to the build, and re-run
   `python -m mcenroebot.coordinator` to confirm tilt stays in range across the intended target
   depths. If the head can't reach the needed down-angle, mount the launcher slightly nose-down
   and/or set `pitch_neutral_deg` to recenter the available travel.

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
- **Feed coupling vs aiming (open decision, not yet settled).** `channel_map.py` only assigns ch5
  to the escapement servo — it does **not** pin down whether the escapement is physically on the
  moving head. Two options:
  - *Escapement rides the head* → ball-drop-into-nip geometry stays invariant under aim, but the
    fixed hopper can't feed straight down into a moving intake: it must terminate in an oversized
    funnel covering the intake's **full swept area** across pan and tilt, bridged by a soft boot
    (which adds mass to the aim servos — see the torque note). **Mitigation:** place the escapement
    intake as close to the pan/tilt pivot axes as possible to minimize the swept area, shrinking the
    funnel and boot.
  - *Escapement stays fixed* → simple straight drop, but the ball-into-nip handoff shifts as the
    head aims, and the launcher must tolerate that.
  Pick one before modeling the feed path; model the swept intake volume either way.
- **Camera isolation + stability.** The camera sits in the **static head**, not on the launcher, so
  motor vibration reaches it through shared structure rather than a direct mount — a weaker path, but
  still worth compliant mounts so the stereo feed doesn't blur and hurt `SimpleBlobDetector`. And the
  tall shell with ~80 balls high in the chest is top-heavy: give the base a wide footprint and low CG
  (the LiPo drawer helps) so it doesn't tip — the real risk is **tip-over**, not firing recoil, which
  from a ~2.7 g ball is negligible.
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
  the build, and re-run the coordinator demo. The solver stays in range for table targets; the thing
  to confirm is that the head can physically tilt nose-down far enough for near targets — adjust
  `pitch_neutral_deg` / mount nose-down if not.
- **Feed coupling:** decide escapement-on-head vs escapement-fixed (see §1). If on-head, place the
  intake near the pivot axes and size the funnel + soft boot to the swept area; model the swept
  intake volume either way.
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
- **Confirm second launch motor:** the dual-wheel launcher needs two A2212-class motors. Four ESCs
  are confirmed on hand; the second *motor* is unconfirmed — verify both are mounted before
  dual-wheel bring-up.
- **Launcher wheel arrangement:** reconcile top/bottom stack (front cutaway, ch3 top / ch4 bottom)
  vs "one behind the other" (side view) — these are different geometries and change the bracket.

**Resolved (were open):** second-ESC blocker — four ESCs on hand.

---

## 8. Printed support parts (fabrication record)

The concrete brackets/mounts that realize the bay and launcher. Each comes from a parametric
generator (trimesh, same `generate_*.py` pattern as `generate_auger_wide.py`); nominal dims are
confirmed by bench fit and tuned from there. These map onto the diagram's subsystems:
**Electronics** (ESC rack), **Power** (battery drawer + frame), **Launch** (bracket + coupon).

| Part | Generator | Holds / role | Key dims (mm, X×Y×Z) | Material | Status |
|---|---|---|---|---|---|
| ESC rack | `generate_esc_rack.py` | 4 ESCs on edge, 13 mm air gaps, zip-tie retention; 4× M3 into the tray | 91 × 62 × 7 | PETG (heat zone) | **Printed ✓ — fits** |
| Battery drawer | `generate_battery_drawer.py` | LiPo lies flat, pull-out at waistband; XT60 + leads exit the back; velcro-strap windows | 44 × 82 × 30 | PLA ok / PETG nicer | Printing |
| Battery frame | `generate_battery_drawer.py` | drawer guide (0.5 mm slide), back wire pass-through + rear stop; 4× M3 to bay floor | 51 × 82 × 28 | PLA ok / PETG nicer | Printing |
| Launcher bracket v0 | `generate_launcher_bracket.py` | holds 2× A2212 at 91 mm nip spacing; wheels cantilever to a coplanar nip; back flange + placeholder gimbal interface | 52 × 20 × 123 | PETG (loads + vibration) | Designed — gated on coupon |
| Motor-mount coupon | `generate_launcher_bracket.py` | verify the A2212 hole pattern before the full bracket | 43 × 43 × 5 | any | Designed — **print first** |
| Auger tube segment | `generate_tube_segment_final.py` | one stackable lift section: hex-mesh wall, flush 102 mm bore, spigot/socket lap joint (10 mm overlap) | 114 × 114 × 160 | PLA (bring-up) / PETG | **Printed ✓** |
| Auger screw segment | `generate_screw_segment.py` | 3-turn flight on M8 rod; flush-clipped ends + peg/hole clocking for in-phase stacking | Ø97 × 154 | PLA (bring-up) / PETG | **Printed ✓** |
| Rod-guide spider | `generate_rod_guide.py` | centers the M8 rod on a 608ZZ bearing at each tube end (3 open spokes); sits **outside** the ball path | Ø114 × 12 | PLA / PETG | Printed ✓ — print 2 |

### Auger — finalized geometry (supersedes the FEEDER_PLAN bore)

The original FEEDER_PLAN bore (46 mm ID / 44 mm screw) **does not work** — a 40 mm ball in a 46 mm
tube sits on the tube axis, exactly where the screw core is, so the flight can't get under it.
Sphere geometry, not disk: to let the ball sit beside a center shaft the bore must be **ID ≥ ~80 mm +
core**. Final working set:

- **Tube:** ID **102 mm**, OD 108 mm, 3 mm wall; joint collar OD **114 mm** (widest point — clear the bay around this).
- **Screw:** OD **97.2 mm**, core 12 mm, pitch 50 mm (one ball/turn), M8 bore → **2.4 mm flight-to-wall** clearance.
- **Catch fix:** a tapered **scoop lead-in** on the flight's leading edge + a steep (~55–65°) incline gives reliable seat-climb-hold. Verified on the bench.
- **Modular stack:** 3-pitch segments (150 mm / 6 in body). Tube segments join by a flush-bore spigot/socket lap (10 mm overlap, 0.4 mm slip); screw segments butt with peg/hole clocking so the helix stays continuous, and the whole screw stack clamps between two nuts on the rod (no per-segment set screws). Stack ≈ N × 6 in + ~0.4 in → 2 = 12.2 in, 3 = 18.1 in.
- **Rod support:** a 608ZZ-bearing spider caps each tube end. **The ball cannot pass a center hub** (same sphere overlap), so the guides sit *outside* the ball-travel zone and the ball enters/exits through **side ports**, not the ends — cut those into whichever segments land at the infeed (trough) and exit (hopper).
- **Material:** PLA fine for bring-up; move the screw + guides to PETG/PETG-CF for continuous running (heat + wear at the flight/wall rub).
- **Still to do:** scooped-bottom screw variant for the entry segment; side ports at infeed/exit; commit the trough→hopper-top span to fix the segment count.

### Fasteners / interfaces (shared conventions)

- **M3** throughout for module-to-tray and motor mounts (the Fgruh M3 kit + nuts/washers covers it).
- **Zip ties** retain ESCs (rack has the slots); **velcro strap** retains the LiPo (drawer has the windows).
- **Set screws** (Hapric M3–M8 cup-point kit) to lock the launch wheels onto the A2212 shafts — and
  the escapement disk + auger segments onto their rods. *Not yet designed into any part.*
- **Gimbal interface** on the bracket is a **placeholder** (4× M3 + a 6 mm axle hole on the back flange)
  pending the real pan/tilt geometry.
- Threading method across all parts not yet locked: clearance + nut/washer (free) vs heat-set inserts
  (cleaner for the rework-heavy bracket). Resize holes once chosen.

### Per-part confirms still open

- **ESC rack:** ESC body dims confirmed by fit ✓ (none open).
- **Battery:** confirm CNHL pack dims (used 73 × 36 × 31); tune `slide_gap` (0.5) if drawer is tight/loose.
- **Launcher:** (1) A2212 mount pattern — the coupon answers this; (2) wheel width + face-to-wheel offset
  (assumed 18 mm) → sets the nip position; (3) nip gap (36 mm) — grip vs slip, tune on the bench;
  (4) feed direction — assumed **top-fed** into the nip; add a throat if fed from behind.

### Support parts NOT yet generated (remaining fabrication)

- **Electronics tray** — the centerpiece that mounts Pi+PCA9685 / 4× ESC rack / L298N / bucks and ties
  the bay together. *Blocked on the swing-cone keep-out measurement (§7).*
- **Stomach port ring** — funnel + out-and-down lower lip. *Blocked on committed exit height + final aim cone.*
- **Feed-loop parts (remaining)** — escapement disk (90 mm OD, 42 mm pocket, 608 seat), hopper cone, trough.
  The **auger tube + screw are now generated as stackable segments** (see §8 “Auger — finalized geometry”)
  and supersede the FEEDER_PLAN bore. (Other feed geometry still per `FEEDER_PLAN.md`.)
- **Cosmetic shell** — face-front, hair/back, red headband (seam cover), polo collar, torso front/back,
  base/pedestal. → Blender, then boolean the mount features on.
- **Camera eye mounts** (ELP bar behind the eye sockets) and the **hopper→escapement funnel + boot**.

### Generators

The generators above were produced as parametric scripts and currently live as generated artifacts.
**Commit them to `docs/3d-models/`** — including the auger set (`generate_tube_segment_final.py`,
`generate_screw_segment.py`, `generate_rod_guide.py`) — so every printed part is reproducible and
versioned (matches the existing `generate_auger_wide.py` convention).
