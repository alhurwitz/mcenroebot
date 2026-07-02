"""generate_align_gauge.py  (v1 — rebuilt)

Finds the HD3512MG spline offset by MOUNTING the servo, not guessing a rod hole.

How it works:
  - Two tab holes at the standard 49.5 mm spacing, centred on the plate (x=0 = tab/body
    centre). Bolt the servo down through them. If the screws don't line up, your tab
    spacing differs from 49.5 — tell me that.
  - The body drops through the pocket; the spline pokes up inside it, offset toward one
    end by ~10 mm (that's the unknown).
  - An engraved scale along the pocket's long edge reads the spline's offset from centre
    (0 = plate centre, long ticks every 5 mm, short ticks every 1 mm).
  - The pointer cap (separate tiny part) drops over the Ø5.9 spline; its tip points at
    the scale so you read the offset without parallax.

Report back: (1) did the screws fit the 49.5 holes, (2) the spline offset in mm and which
end it's toward (cable end or opposite). Two numbers -> I cut the real cradle coaxial
with the far-wall bushing. Everything here is plate-or-subtracted; no floating bits.
PLA, flat, ~4 mm.
"""

import numpy as np
import trimesh

BODY_L = 40.8
BODY_W = 20.4
TAB_SPACING = 49.5
TAB_HOLE = 3.4
PLATE_T = 4.0
MARGIN = 9.0
CLEAR = 0.6
SPLINE_BORE = 6.0  # pointer-cap bore over the Ø5.9 spline (slip)
SECTIONS = 64
EPS = 0.4
GROOVE_W = 0.7
GROOVE_D = 0.9


def box(l, w, h, x=0, y=0, z=0):
    b = trimesh.creation.box(extents=[l, w, h])
    b.apply_translation([x, y, z])
    return b


def zcyl(d, h, x=0, y=0, z=0):
    c = trimesh.creation.cylinder(radius=d / 2.0, height=h, sections=SECTIONS)
    c.apply_translation([x, y, z])
    return c


def cut_groove(plate, x, y0, length):
    """Engrave a y-running groove (tick) into the top face at column x."""
    g = box(
        GROOVE_W,
        length,
        GROOVE_D + EPS,
        x=x,
        y=y0 + length / 2.0,
        z=PLATE_T - GROOVE_D / 2.0 + EPS / 2.0,
    )
    return plate.difference(g, engine="manifold")


def build_plate():
    x_half = TAB_SPACING / 2.0 + MARGIN
    y_half = BODY_W / 2.0 + MARGIN
    plate = box(2 * x_half, 2 * y_half, PLATE_T, z=PLATE_T / 2.0)

    # body pocket (through), centred at x=0
    pocket = box(BODY_L + CLEAR, BODY_W + CLEAR, PLATE_T + 2 * EPS, z=PLATE_T / 2.0)
    plate = plate.difference(pocket, engine="manifold")

    # tab holes at standard spacing
    for sx in (-TAB_SPACING / 2.0, TAB_SPACING / 2.0):
        plate = plate.difference(
            zcyl(TAB_HOLE, PLATE_T + 2 * EPS, x=sx, z=PLATE_T / 2.0), engine="manifold"
        )

    # engraved offset scale along the +y pocket edge, x = -20..20
    y0 = BODY_W / 2.0 + 0.6
    for x in range(-20, 21):
        if x % 5 == 0:
            plate = cut_groove(plate, x, y0, 6.0)  # major
        else:
            plate = cut_groove(plate, x, y0, 3.0)  # minor
    # emphasise zero with a wider groove
    plate = plate.difference(
        box(1.6, 8.0, GROOVE_D + EPS, x=0, y=y0 + 4.0, z=PLATE_T - GROOVE_D / 2.0 + EPS / 2.0),
        engine="manifold",
    )

    # y=0 centreline grooves on the solid end-lands (to check spline is on-centre in y)
    land_in = BODY_L / 2.0 + 0.5
    for s in (-1, 1):
        L = x_half - land_in
        plate = plate.difference(
            box(
                L,
                GROOVE_W,
                GROOVE_D + EPS,
                x=s * (land_in + L / 2.0),
                y=0,
                z=PLATE_T - GROOVE_D / 2.0 + EPS / 2.0,
            ),
            engine="manifold",
        )
    return plate


def build_pointer_cap():
    disc = zcyl(14.0, 3.0, z=1.5)
    arm = box(2.0, 17.0, 2.5, x=0, y=7 + 17 / 2.0 - 2, z=1.25)  # +y blade
    # taper the tip
    tip = trimesh.creation.cylinder(radius=1.0, height=2.5, sections=24)
    tip.apply_translation([0, 7 + 17 - 2, 1.25])
    cap = disc.union(arm, engine="manifold").union(tip, engine="manifold")
    cap = cap.difference(zcyl(SPLINE_BORE, 3 + 2 * EPS, z=1.5), engine="manifold")
    return cap


def main():
    p = build_plate()
    p.merge_vertices()
    p.update_faces(p.nondegenerate_faces())
    p.export("align_gauge_v1.stl")
    c = build_pointer_cap()
    c.merge_vertices()
    c.update_faces(c.nondegenerate_faces())
    c.export("align_pointer_cap_v1.stl")
    print(
        "plate bodies:",
        len(p.split(only_watertight=False)),
        "bbox",
        np.round(p.extents, 1),
        "watertight",
        p.is_watertight,
    )
    print(
        "cap   bodies:",
        len(c.split(only_watertight=False)),
        "bbox",
        np.round(c.extents, 1),
        "watertight",
        c.is_watertight,
    )
    return p, c


if __name__ == "__main__":
    main()
