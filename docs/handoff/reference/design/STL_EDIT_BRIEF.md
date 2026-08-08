# STL editing brief — turn the McEnroe sculpt into the printable robot shell

**Input:** the McEnroe upper-body sculpt (headband, curly hair, white polo, arms at
sides, no legs, cut at the hips). **Units: millimeters. Up axis: Z. Face points +Y.**

Do the steps in order. Steps 1 is what prevents the holes/"missing spots".

---

## 1. Clean to a watertight solid  ← do this FIRST
- Remesh / voxel-remesh the sculpt into ONE closed, watertight, manifold solid
  (voxel size ~1.0 mm). No open edges, no self-intersections, no floating bits.
- Keep all surface detail (headband, hair, collar, sleeve folds).

## 2. Scale to exact size (uniform scale — do NOT distort)
Scale the whole model uniformly so the belly is **200 mm front-to-back**. Verify:

| Feature | Target |
|---|---|
| Overall figure height (crown → hip cut) | ~800 mm |
| Head (chin → crown) | ~205 mm |
| Shoulder width | ~340 mm |
| Torso height (shoulders → hip cut) | ~490 mm |
| **Torso cross-section, chest & belly (CRITICAL)** | **≥ 220 mm wide × ≥ 200 mm deep** |
| Hip / waist cut diameter | ~200 mm |

If any part of the chest-to-belly run is under 220 × 200 mm, scale up until it isn't.

## 3. Hollow it
- Shell the torso, head, and arms to a **uniform 3 mm wall**.
- Leave the **bottom open** (remove the flat cap at the hip cut) so it slips over the
  internal frame.
- Put a **Ø90 mm opening at the neck** (top) so the head interior connects to the torso.

## 4. Cut the working openings
Reference Z = 0 at the hip/waist cut (bottom), Z up; +Y = face/front; X = left–right, 0 = centerline.

- **Eyes (2 holes):** on the sculpted pupils, **~60 mm apart**, centered on the face,
  each **Ø15 mm**, drilled straight back (−Y) so they look forward. Directly behind
  them, hollow an internal pocket **82 (W) × 15 (deep) × 18 (H) mm** to seat a camera
  bar, its front flush to the inside of the face.
- **Mouth:** a rounded slot **44 (W) × 12 (H) mm**, ~40 mm below the eyes, through the face.
- **Belly launch port:** **Ø60 mm** hole through the front, centered on X, at **Z = 90 mm**.
- **Rear auger slot:** rectangular **56 (W) × 60 (H) mm** through the back (−Y side),
  centered on X, spanning **Z = 390–450 mm**.

## 5. Base / pedestal (separate part)
- A round pedestal **320 mm diameter × 100 mm tall**, hollow (~3 mm wall), flat bottom.
- Top has a rim the torso's open hip sits on; **4× M3 holes** to bolt the torso down.
- **Ø52 mm hole** through the center for wiring.

## 6. Split for a 256 × 256 mm printer
- Cut into pieces that each fit within **248 mm** on every axis.
- Torso: **front/back clamshell** (split on the Y=0 plane) so the halves wrap around
  the frame, then horizontal bands as needed.
- Add **Ø4 mm dowel/alignment holes** across every cut so pieces line up for gluing.
- Head: split front/back. Base: split into quadrants if over-bed.

## Output
Watertight STLs, one per printable piece, plus one full assembled STL for reference.
