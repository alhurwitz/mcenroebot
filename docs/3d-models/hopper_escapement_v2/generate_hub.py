#!/usr/bin/env python3
"""
spline_hub_v3 — press and glue variants. REPLACES spline_clamp_v2.

WHY THE CLAMP IS GONE
=====================
spline_clamp_v2 was a split collar with a Ø24 body around a Ø6.2 bore — an
8.9 mm wall. It could never have worked: a clamp grips by ELASTICALLY DEFORMING
its collar, ring stiffness goes as wall^3, and that section is ~38x stiffer than
a real collar. The M3 would have stripped its threads in the PETG long before
the bore closed the ~0.9 mm it needed. My error.

AJ is fine pressing and gluing, which makes the whole clamp mechanism
unnecessary. No slit, no pinch bolt, no ears, no flexing section to get wrong.
A solid bushing is a simpler part with fewer ways to be wrong, and glue makes it
permanent — which is what he wanted from the joint in the first place.

WHY THE BORES ARE SMALLER THAN "THE SPEC"
=========================================
Every part I have cut for this spline has come back too loose, three times.
AJ, holding it: "you continuously make it too large / just trust me ur
measurements are wrong."

He is right, and the repo already said so before I did. docs/mg996r_fit_precheck
.md: "clone tolerances are real. Caliper the actual MG996R ... before cutting or
printing anything." The Ø5.92 I have been designing to is a PUBLISHED
Tower-Pro figure, not a measurement of the servo on this bench. A published
figure that has failed three empirical tests is not the better evidence.

So these are sized off the only real datum in play — that a modelled Ø6.2 came
out visibly loose — rather than off the datasheet.

    spline_hub_press_v3   bore 5.2   interference. Broaches on.
    spline_hub_glue_v3    bore 5.6   bond line for adhesive.

ERR SMALL, ON PURPOSE: a bore that is too tight opens up in seconds with a
drill bit. A bore that is too loose is a reprint. The recoverable direction is
down, so both of these sit below where I would have guessed.

EVERYTHING ELSE IS UNCHANGED, so these still mate with the spline_coupler_v2
you may already have printed: Ø10 AF hex, 28 mm long, body 10 mm tall. That
keeps the engagement window (-13.4/+6.5 mm on servo height) exactly as checked.
"""

import numpy as np
import trimesh
from trimesh.creation import cylinder

SEG = 128

# ---- LOCKED: these three set the fit to spline_coupler_v2. Do not touch. ----
BODY_H = 10.0                 # bore depth AND the height that sets the window
HEX_AF = 10.0
HEX_BOSS_H = 28.0

BODY_D = 16.0                 # was 24 — the bulk was only there for the clamp
VENT_D = 4.0                  # air escape for glue + sight line to check seating
MOUTH_CHAMFER = 0.8           # so it starts square on the spline

VARIANTS = {
    "spline_hub_press_v3": dict(bore=5.2, grooves=False),
    "spline_hub_glue_v3": dict(bore=5.6, grooves=True),
}
GROOVE_DEPTH, GROOVE_W = 0.6, 1.5
GROOVE_Z = (2.5, 6.5)


def cyl(r, z0, z1, seg=SEG):
    c = cylinder(radius=r, height=z1 - z0, sections=seg)
    c.apply_translation([0, 0, (z0 + z1) / 2.0])
    return c


def hexa(af, z0, z1):
    return cyl(af / np.sqrt(3.0), z0, z1, seg=6)


def hub(bore, grooves):
    solids = [cyl(BODY_D / 2, 0.0, BODY_H),
              hexa(HEX_AF, BODY_H, BODY_H + HEX_BOSS_H)]
    cuts = [cyl(bore / 2, -0.5, BODY_H),
            cyl(VENT_D / 2, 0.0, BODY_H + HEX_BOSS_H + 1.0)]

    # lead-in chamfer at the bore mouth
    ch = cylinder(radius=bore / 2 + MOUTH_CHAMFER, height=MOUTH_CHAMFER * 2,
                  sections=SEG)
    v = ch.vertices.copy()
    v[v[:, 2] > 0, :2] *= (bore / 2) / (bore / 2 + MOUTH_CHAMFER)
    ch.vertices = v
    ch.apply_translation([0, 0, MOUTH_CHAMFER])
    cuts.append(ch)

    if grooves:
        # somewhere for adhesive to live so the press does not squeeze it all out
        for z in GROOVE_Z:
            cuts.append(cyl(bore / 2 + GROOVE_DEPTH, z, z + GROOVE_W))

    return trimesh.boolean.difference(
        [trimesh.boolean.union(solids, engine="manifold"),
         trimesh.boolean.union(cuts, engine="manifold")], engine="manifold")


def main():
    ok = True
    for name, cfg in VARIANTS.items():
        m = hub(cfg["bore"], cfg["grooves"])
        m.export(f"{name}.stl")
        e = m.extents
        good = m.is_watertight and m.body_count == 1
        ok &= good
        print(f"{name:22s} bore Ø{cfg['bore']}  {e[0]:5.1f} x {e[1]:5.1f} x "
              f"{e[2]:5.1f} mm  {m.volume/1000:4.1f} cm3  wt={good}")

    print("\n  hex/body geometry identical to spline_clamp_v2, so the")
    print("  engagement window against spline_coupler_v2 is unchanged.")
    print("\nPRINT  hex UP, bore on the bed. No supports, 4 perimeters, 50%.")
    print("       Ø16 footprint is small for a 38 mm part — use a brim.")
    print("\nFIT    press one: should need firm thumb pressure and stay put.")
    print("       glue one:  should slide on with slight drag, then adhesive.")
    print("       TOO TIGHT IS FIXABLE — open the bore with a drill (5.5 / 5.8)")
    print("       until it starts. Too loose is a reprint, which is why both")
    print("       of these err small.")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
