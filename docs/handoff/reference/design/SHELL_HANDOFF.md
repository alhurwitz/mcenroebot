# Shell re-run handoff — requirements from torso_scaffold_v3

For the agent re-running `3d-models/mcenroe_shell_v1/generate_parts.py`.
Scaffold v3 makes the shell STRUCTURAL: three internal plates mount by screws
driven from outside through the shell wall. Everything below is computed by
`torso_scaffold_v3/generate_parts.py` (re-run it if any number here changes).

Datum: shell z = table z − 215 (launch axis 305 abs = PORT_Z 90 ✓ unchanged).

## 1. Dimensions (replaces v1 placeholders)
| Param | Value | Why |
|---|---|---|
| TORSO_H | **490** | hopper rim+cone tops at abs 686 |
| SHOULDER_Z | **370** | hopper plate at shell z 363–371 must sit in the straight zone |
| TORSO_W / TORSO_D | 210 / 190 | unchanged — scaffold ellipse derived from these; if you change them, scaffold re-runs |
| PORT_D / PORT_Z | 60 / 90 | unchanged |
| TOP_HOLE_D | 100 | unchanged — hopper centers under it |

## 2. Plate mounting holes — 18× Ø3.5, drilled radially
6 per plate at angles **45/90/135/225/270/315°** (measured from +X, +Y = front;
0/180° kept clear of the half seam):

| Plate | shell z | note |
|---|---|---|
| launcher | **149** | |
| feed | **253** | 270° is a PAIR at x ±10 (7 holes total) — shared with auger strut |
| hopper | **367** | 270° is a PAIR at x ±10 (7 holes total) — shared with auger strut |

Screws: M3×10 into plate boss pilots (Ø2.8). Plates slide in via the open
bottom — do NOT add internal ledges/ribs at or below these z's.

## 3. Bottom edge — waist seat
Shell bottom lands on the waist deck (abs 215). 4× Ø3.5 radial at angles
**45/135/225/315°, shell z 6**, into waist-tab pilots.

## 4. Auger discharge cutout
Rear taper, centered on −Y: **56 wide × shell z 390–450**. Chute flange takes
2× M3×8 through the shell beside it (flange pilots at x ±30, mid-cutout z).

## 5. Seam lugs — keep clear of plate bands
Plates + bosses occupy shell z **140–165, 244–269, 358–383** at the ±X walls.
Reposition the M3 lug pairs outside those bands (e.g. z 60, 200, 300, 440).

## 6. Bed
TORSO_H 490 → halves exceed the ~250 bed: waist-split each half (the v1
docstring already anticipates this). Put the split OUTSIDE the plate bands,
suggest shell z 210 (between launcher and feed plates); plates bridging the
split will stiffen it.

## Sync rule
`TORSO_W/D`, `PORT_Z`, wall 2.4 are shared SSOT with
`torso_scaffold_v3/generate_parts.py` (params at top). Change in one → re-run
both → diff the printed hole table against §2.
