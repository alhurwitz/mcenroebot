#!/usr/bin/env python3
"""launcher_bracket_v3 — dual-wheel launcher bracket, McEnroe Bot V4.

Back plate + 2 motor stations + vertical drop chute + top mounting flange.

Motor mount (per station, A2212 bare motor, single hole set):
  4x M3 plain clearance @ pitch radius 11 mm (test-card pad C), 45 deg
  positions, O6.5 x 3 mm counterbores on the BACK face (screw side),
  O8 shaft clearance, O17 x 2 mm hub relief on the FRONT face.

Launcher geometry (SSOT docs/feed_launch_reconciled.md):
  wheel centers 97 mm apart (X), 60 mm wheels -> 37 mm nip (3 mm squeeze
  on 40 mm ball). Tire width 28 mm, wheel band y 6..34, band center y=20.
  Drop chute: 44 mm inner, 3 mm wall, straight vertical, centered on the
  tire band; lower mouth clears wheel tops (z=30).

Frame: nip at origin, wheel axes along Y, plate at y[-6,0], +Z up.
All mm. trimesh + manifold3d.
"""
import numpy as np
import trimesh

# plate
PLATE_X, PLATE_Z, PLATE_T = 150.0, 96.0, 6.0
# motors
XSEP = 97.0
PR = 11.0
M3_R, CB_R, CB_D = 1.7, 3.25, 3.0
SHAFT_R = 4.0
HUB_R, HUB_D = 8.5, 2.0
ANGLES = (45, 135, 225, 315)
# wheels / chute
TIRE_Y0, TIRE_Y1 = 6.0, 34.0            # 28 mm tire band
BAND_Y = (TIRE_Y0 + TIRE_Y1) / 2        # 20
CHUTE_IN = 44.0
WALL = 3.0
CHUTE_OUT = CHUTE_IN + 2 * WALL         # 50
CHUTE_Z0, CHUTE_Z1 = 31.0, 95.0         # mouth just above wheel tops (z=30)
# flange
FLANGE_X, FLANGE_Y, FLANGE_T = 70.0, 60.0, 5.0
FLANGE_ZC = CHUTE_Z1 + FLANGE_T / 2     # 97.5
FLANGE_HOLES = [(sx, sy) for sx in (-28, 28) for sy in (BAND_Y - 22, BAND_Y + 22)]


def box(ex, ey, ez, x=0, y=0, z=0):
    b = trimesh.creation.box(extents=[ex, ey, ez])
    b.apply_translation([x, y, z])
    return b


def ycyl(r, y0, y1, x=0.0, z=0.0, s=64):
    c = trimesh.creation.cylinder(radius=r, height=y1 - y0, sections=s)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    c.apply_translation([x, (y0 + y1) / 2, z])
    return c


def zcyl(r, z0, z1, x=0.0, y=0.0, s=64):
    c = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=s)
    c.apply_translation([x, y, (z0 + z1) / 2])
    return c


def build():
    # back plate y[-PLATE_T, 0]; motors bolt from behind (heads on y=-PLATE_T face)
    plate = box(PLATE_X, PLATE_T, PLATE_Z, y=-PLATE_T / 2)

    cuts = []
    for cx in (-XSEP / 2, XSEP / 2):
        cuts.append(ycyl(SHAFT_R, -PLATE_T - 1, 1, x=cx))          # shaft through
        cuts.append(ycyl(HUB_R, -HUB_D, 1, x=cx))                  # hub relief, front
        for a in ANGLES:
            hx = cx + PR * np.cos(np.radians(a))
            hz = PR * np.sin(np.radians(a))
            cuts.append(ycyl(M3_R, -PLATE_T - 1, 1, x=hx, z=hz))   # M3 through
            cuts.append(ycyl(CB_R, -PLATE_T - 1, -PLATE_T + CB_D, x=hx, z=hz))  # cbore, back
    plate = plate.difference(cuts, engine="manifold")

    # vertical drop chute, square tube, centered on tire band
    chute = box(CHUTE_OUT, CHUTE_OUT, CHUTE_Z1 - CHUTE_Z0,
                y=BAND_Y, z=(CHUTE_Z0 + CHUTE_Z1) / 2)
    chute = chute.difference(
        box(CHUTE_IN, CHUTE_IN, CHUTE_Z1 - CHUTE_Z0 + 4, y=BAND_Y,
            z=(CHUTE_Z0 + CHUTE_Z1) / 2), engine="manifold")

    # (chute back wall overlaps the plate: outer back face y=-5 vs plate y[-6,0],
    #  so the tube fuses to the plate directly; no separate web/gussets needed)

    # top mounting flange (interface to feed unit)
    flange = box(FLANGE_X, FLANGE_Y, FLANGE_T, y=BAND_Y, z=FLANGE_ZC)
    fcuts = [zcyl(M3_R, FLANGE_ZC - FLANGE_T, FLANGE_ZC + FLANGE_T, x=fx, y=fy)
             for fx, fy in FLANGE_HOLES]
    # flange ball passage
    fcuts.append(box(CHUTE_IN, CHUTE_IN, FLANGE_T + 2, y=BAND_Y, z=FLANGE_ZC))
    flange = flange.difference(fcuts, engine="manifold")

    part = plate.union(chute, engine="manifold").union(flange, engine="manifold")
    # clear the full ball passage through any plate overlap
    part = part.difference(
        box(CHUTE_IN, CHUTE_IN, CHUTE_Z1 - CHUTE_Z0 + 2, y=BAND_Y,
            z=(CHUTE_Z0 + CHUTE_Z1) / 2), engine="manifold")
    part.merge_vertices()
    part.update_faces(part.nondegenerate_faces())
    return part


if __name__ == "__main__":
    p = build()
    p.export("launcher_bracket_v3.stl")
    print("extents", [round(v, 1) for v in p.extents], "watertight", p.is_watertight,
          "vol_cm3", round(p.volume / 1000, 1))
