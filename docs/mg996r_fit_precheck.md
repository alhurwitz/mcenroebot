# MG996R fit pre-check — feed_unit_v1 mount (2026-07-04)

Research-only note: does the printed `feed_unit_v1` mount (cut for the HD3512MG-360)
accept the MG996R that replaced it? **Calipers on the actual servo are still the
gate** — MG996R clones vary a millimeter or so flange-to-flange; the numbers below
are published/standard-case figures, not measurements of our unit.

## What the mount was cut for (HD3512MG)

| Feature | As-printed |
|---|---|
| Long-axis mounting-hole spacing | **48.0 mm** (hole cutters at x = −34 / x = +14 rel. to spline center) |
| Spline center -> near hole | **14.0 mm** |
| Body window width (long axis) | **41.5 mm** |

## MG996R published dims (standard-size Futaba-style case)

Body **40.7 × 19.7 × 42.9 mm**, 55 g, 4× mounting holes in two flanges
([espboards](https://www.espboards.dev/sensors/mg996r/),
[components101](https://components101.com/motors/mg996r-servo-motor-datasheet),
[Tower Pro datasheet PDF](https://www.electronicoscaldas.com/datasheet/MG996R_Tower-Pro.pdf)).
The standard-size case puts the output spline ~9.9–10 mm behind the front body
face, flanges spanning ~53.6–54.5 mm overall, holes ~**49.5 mm** apart on the
long axis and ~10 mm on the short axis. Derived long-axis geometry (spline at 0):
near hole ~**+14.3 mm**, far hole ~**−35.2 mm**.

## Verdict per caliper check

| Check | Mount | MG996R (published) | Verdict |
|---|---|---|---|
| Spline -> near hole 14 mm | 14.0 | ~14.3 | **Likely PASS** — ~0.3 mm off; inside M3-clearance slop if holes are drilled 3.2–3.4 mm |
| Hole spacing 48 mm | 48.0 | ~49.5 | **Likely FAIL** — far hole lands ~1.2–1.5 mm inboard of the cutter; M3 clearance won't absorb it |
| Body window 41.5 mm | 41.5 | 40.7 body | **Likely PASS** — ~0.8 mm total clearance (snug; flanges sit on top of the window) |

Short-axis hole pitch (~10 mm on the MG996R) was not one of the caliper checks —
measure it too before committing.

## Fallback if the far hole misses

1. **Slot the two long-axis holes** ~2 mm outward (drill/file the printed part, or
   a one-line cutter change) — cheapest, keeps the print.
2. **Regenerate the mount plate** with the true MG996R pattern once calipered
   (spacing, spline offset, and 10 mm short-axis pitch) — do this if the window
   or spline offset also misses.

Again: clone tolerances are real. Caliper the actual MG996R (hole-to-hole, spline
-> near hole, body length) before cutting or printing anything.
