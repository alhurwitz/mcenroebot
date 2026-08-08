# 3D model index (as of 2026-07-12)

Two locations. **C** = Cowork project folder `~/Claude/Projects/Mcenroebot/3d-models/` (**not in git**).
**R** = repo `~/Projects/mcenroebot/docs/3d-models/` (in git).

Every part has a `generate_parts.py` (or similar) next to its STL — **regenerate, don't hand-edit meshes.**

## Current — the machine as it stands

| Part | Loc | Status |
|---|---|---|
| `launcher_bracket_v4_tri` | C | **CURRENT** launcher — 3× 60 mm wheels @120°, printed, fires |
| `feed_unit_v1` | C | **CURRENT** feed housing — printed, metering works |
| `feed_servo_wall_v2` | C | **CURRENT** servo mount (replaced the snapped thin wall) |
| `scoop_arm_cup26_v3` | C | **CURRENT** arm — ring stopper, double-feed solved, bench-confirmed |
| `feed_launcher_coupler_v1` | C | **CURRENT** — telescoping, gap 55–85 mm; set to ~101 mm on the stand |
| `shooter_stand_v2_pan` | C | **CURRENT** stand — 5 parts, staged (feet → pan drum → full v1); rev-B risers, plain |
| `auger_lift_v2` | C | **CURRENT** auger — 658 mm lift @60°; ⚠️ drive choice (GB37RG vs servo) unresolved |
| `hopper_neckdown_v1` | C | Ø165 hopper, parametric; rides the feed-chute top |
| `motor_mount_coupon_v3` | C + R | Fit coupon — confirmed the X-mount outer-hole pattern |
| `camera_mount_v1` | R | ELP stereo module mount (shell + clevis + mast); 3 placeholder dims to measure |
| `mcenroe_shell_v6` | C | **CURRENT** cosmetic shell — slip-over cover, 14 pieces ≤248 mm; **deferred** until shots work |
| `torso_scaffold_v3` | C | **CURRENT** internal structure — 3 shell-structural plates + pedestal |
| `tube_segment_hex_FINAL`, `screw_segment_3turn` | C (in `auger_lift_v2/reference/`) + R | AJ's own honeycomb auger segments — the standard the auger is built around |
| `align_gauge_v1` | R | Alignment gauge |
| `battery_drawer`, `battery_frame`, `electronics_tray`, `esc_rack`, `stomach_port_ring`, `rod_guide_spider_press` | R | Chassis/electronics accessories, not yet integrated |

## Superseded / obsolete — do not print

| Part | Loc | Replaced by |
|---|---|---|
| `launcher_bracket_v1` / `v3` (+ `L2_launcher_bracket`, `L1_motor_mount_coupon`) | C + R | `launcher_bracket_v4_tri` |
| `launcher_bench_dock_v1` (+ 0/10/20/30° wedges) | C | `shooter_stand_v2_pan` (dock fit poorly; AJ props/clamps) |
| `pan_base_v1`, `launcher_tilt_v1` | C | `shooter_stand_v2_pan` / `shooter_stand_v1` |
| `shooter_stand_v1` | C | **Not obsolete — it's STAGE 3** (full servo pan/tilt) of the v2 plan |
| `auger_lift_v1` | C | `auger_lift_v2` |
| `scoop_arm_cup26_v1` / `v2`, `scoop_arm_v0`, `scoop_chute_v0`, `scoop_servo_cradle_v1` | C + R | `scoop_arm_cup26_v3` (v2 sector = lighter alternative, still valid) |
| `scoop_endstops_v1` | C | Not needed — positional feed servo holds its angles |
| `mcenroe_shell_v1`–`v5` | C | `mcenroe_shell_v6` |
| `torso_scaffold_v1` / `v2` | C | `torso_scaffold_v3` (v2 is still useful as a shell-less integration jig) |
| `docs/3d-models/archive/**` | R | V2 swat-arm + first feeder parts (escapement disk, hopper cone, wide auger) |
