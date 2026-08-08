# Auger lift — print list (servo path, 2 ft)

Continuous-servo drive (HD3512MG-class), round-disc horn, bolt-on flat base.
~658 mm vertical lift at 60°.

| Part | Qty | File | Orientation / supports |
|---|---|---|---|
| Servo mount + stand (fused, light) | 1 | `servo_stand_light.stl` | Feet flat on bed. Supports under the tilted bowl. Replaces servo_mount + wedge base (249cm³ vs 2400). |
| Plain tube segment | 4 | `reference/tube_segment_hex_FINAL.stl` (your file) | Vertical, socket down. Honeycomb self-supports. |
| Discharge segment (top) | 1 | `discharge_segment.stl` | Socket down. Supports under the window roof + catch shelf. |
| Drive screw (bottom) | 1 | `drive_screw_servo.stl` | Lay on its SIDE (your 6h trick) — grain + no flight supports. |
| Screw stack segment | 4 | `screw_stack.stl` | On its side too. |
| Screw top pin (journal) | 1 | `screw_top_pin.stl` | Upright, tiny. |
| Servo test coupon (optional) | 1 | `servo_mount_coupon.stl` | Flat. Print FIRST to fit-check the servo + horn. |

## What changed (reprint these; the rest you already have)
- `drive_screw_servo` — flat bolt-on base + M2 horn pilot rings + wide X slots.
- `servo_mount` — tab holes fixed (both ends), body-sized window.
- `screw_top_pin` — now a 66mm journal (old short stub didn't reach the bore).
- `servo_wedge_base` — the pedestal, still to print.

## Assembly (bottom → top)
1. Servo into `servo_mount` from below; tabs bolt to the plate; slide to center
   the spline on the tube axis; spline pokes up into the bowl.
2. Screw the round horn onto the spline. Bolt `drive_screw_servo`'s base to the
   horn — small servo screws into the M2 pilot ring that matches your horn.
3. Drop `servo_mount` into `servo_wedge_base`; pin with the 2 rim screws.
4. Stack: tube → `screw_stack` (hex coupling + M3 cross-pin) → repeat ×4.
5. `discharge_segment` on top; the `screw_top_pin` journal lands in its bore.

## Material / settings
- Screws: PETG (torque). Tubes/base: PLA fine, PETG for keeps.
- Servo caution: run in bursts, don't stall it against a jam (no current limit).

## NOT for the servo path (shelved gear-motor fallback — don't print)
`motor_mount.stl`, `base_stand.stl`, `drive_screw.stl` — GB37RG + L298N design.
