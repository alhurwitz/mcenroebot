# Meshy prompt + exact dimensions — McEnroeBot shell

## Best path for likeness
Use **Image-to-3D** with a straight-on, chest-up **front photo of John McEnroe**
(headband, curly hair, white polo) as the reference, and paste the text prompt
below for the pose/clothing/base. Text-to-3D alone won't nail his face; a photo
will. Generate at the **highest polycount / "quad" or "smooth" topology** option
and enable "watertight/solid" if offered — that's what stops the holes.

## Text prompt (copy-paste)
> John McEnroe, 1980s professional tennis player, upper-body statue. Curly brown
> hair with a white terrycloth headband across the forehead. Wearing a classic
> white short-sleeve tennis polo shirt with a folded collar and a short button
> placket. Standing upright, facing straight forward, both arms relaxed straight
> down at his sides, hands empty. No tennis racket. Body ends cleanly at the hips
> with no legs, and the flat waist sits on a short round display pedestal base.
> Realistic natural human proportions, calm neutral expression. Smooth, clean,
> symmetrical, solid surface, suitable for 3D printing. Studio figurine style.

## Negative prompt (copy-paste)
> legs, feet, tennis racket, ball, holding objects, action pose, extra arms,
> extra fingers, multiple people, text, watermark, deformed, melted, thin spikes

---

## Exact dimensions — scale the Meshy export to these
Meshy exports are unitless/normalized, so **scale the model after download** so the
measurements below are hit. The **torso cross-section is the critical one** — if it
comes out slimmer than the minimums, the ball launcher won't fit inside.

| Feature | Target size |
|---|---|
| Overall height (top of hair → bottom of base) | **~800 mm** |
| Figure only (top of hair → waist cut) | ~700 mm |
| **Head** (chin → top of hair) | **~205 mm tall**, ~185 wide, ~200 deep |
| Neck diameter | ~70 mm |
| Shoulder width (deltoid to deltoid) | ~340 mm |
| **Torso** (shoulders → waist cut), straight run | **~490 mm tall** |
| **Torso cross-section at chest/belly** (CRITICAL) | **≥ 220 mm wide × ≥ 200 mm deep** |
| Waist / hip cut diameter | ~200 mm |
| Pedestal base | ~320 mm dia × ~100 mm tall |

Rule of thumb: keep the torso **at least 220 × 200 mm** through the whole chest-to-belly
run. That's what guarantees a Ø165 mm hopper + the launcher stack fit once it's hollowed.

---

## Features to add AFTER (Meshy makes the shape; these are cut in a mesh/CAD tool)
Meshy gives you the solid look — it won't cut the working openings. Add:
- **Hollow** the torso + head to a **3–4 mm wall** (shell/offset).
- **Eyes:** two camera holes on the pupils, **~60 mm apart**, sized to your lens;
  behind them a pocket for the **80 × 16 × 13.2 mm** camera bar.
- **Mouth:** a ~44 × 12 mm slot for the speaker.
- **Belly launch port:** Ø60 mm hole, centered on the belly, **90 mm above the waist cut**.
- **Rear auger slot:** 56 mm wide, on the upper back.
- **Open bottom** so the shell slips over your scaffold; waist bolts to the base.

Once you have a clean, watertight Meshy export, send it over — with a clean mesh the
hollowing + these ports go in reliably (the holes were coming from the old file's
defects, not the cuts themselves).
