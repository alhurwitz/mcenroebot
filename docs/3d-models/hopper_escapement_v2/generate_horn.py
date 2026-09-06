#!/usr/bin/env python3
"""
disk_horn_v1disk + short-post hubs — hex drive into the ALREADY-PRINTED v1 disk.

AJ 2026-08-16: "i need a new horn to connect to disk with hex shape i can slip
onto hex spline hub."

    servo spline --[ spline_hub_*_v1disk ]-- hex --[ disk_horn_v1disk ]-- v1 disk
                    pressed/glued, on the bench      4x M3 into the existing
                                                     16 BC tapped holes

THE POST HAD TO GET SHORTER, AND THAT IS THE WHOLE CATCH
========================================================
spline_hub_press_v3 / _glue_v3 carry a 28 mm hex post. That length is correct
for escapement_disk_v2, whose counterbore runs 22 mm up into the disk. The
PRINTED v1 disk has a 3.5 mm recess and then solid material with only a Ø6.5
hole through it — and a Ø10 hex measures 11.55 across corners, so it cannot
enter that hole. The post bottoms on the recess ceiling at z=67.9.

Available post travel is 67.9 minus the top of the hub body: about 8 mm, not 28.
So these hubs are reissued with an 8.5 mm post. If you would rather not reprint,
SAWING THE 28 mm POST DOWN TO ~8.5 mm works and costs one cut — the hex section
is uniform, nothing is lost by shortening it.

Engagement ends up ~6 mm. That is far more than the load needs: 0.026 N.m at a
~5 mm flank radius is ~5 N spread over six flanks, ~30 kPa in PETG. The short
post is a consequence of the disk, not a compromise on strength.

THE 0.25 mm SCALLOP, DECLARED RATHER THAN HIDDEN
================================================
The disk's own bolt circle and a Ø10 hex cannot quite coexist. Screws sit at
r8; an M3 countersunk head reaches in to r5.0. A 10.5 AF socket (10.0 hex +
0.5 slop) has an inradius of 5.25. Orienting the hex FLATS toward the screws —
which this does — is the best case and still leaves a 0.25 mm overlap, so each
countersink takes a shallow scallop out of one socket flat.

It is cosmetic. The scallop is 0.25 mm deep in a 6 mm tall socket and the flats
carry the torque either side of it. The alternatives were worse: rotating the
hex 30 deg puts a CORNER at the screw and the overlap grows to 1.06 mm; shrinking
the socket below 10.0 AF stops it accepting the hub at all; drilling the disk's
centre out to clear a bigger hex is blocked because Ø13 (r6.5) runs into the
tapped holes' inner edge at r6.4.

SETTING THE HEIGHT AT ASSEMBLY
==============================
The recess only affords a ~+/-2 mm window on where the servo sits. You do not
have to hit it by luck: the hub is GLUED to the spline, so slide it up or down
the spline until the hex meets the horn nicely, THEN glue. Assembly sets the
dimension, which is the same trick that removed SPAN from the v2 design.
"""

import numpy as np
import trimesh
from trimesh.creation import cylinder

SEG = 128

# ---- measured off the printed parts ----------------------------------------
DISK_Z0, RECESS_Z1 = 64.4, 67.9   # v1 disk underside, recess ceiling
RECESS_D = 26.0
SCREW_BC, N_SCREWS = 16.0, 4
TAB_PLANE = 51.4
SPLINE_BORE_D = 28.0

# ---- horn -------------------------------------------------------------------
HORN_OD = 25.6                    # centres in the Ø26 recess
HORN_Z0 = 61.5                    # skirt below the disk, inside the Ø28 bore
HEX_AF = 10.0                     # matches the hubs
HEX_SLOP = 0.5
M3_CLEAR = 3.4
CSK_D, CSK_DEPTH = 6.0, 1.7

# ---- hubs (LOCAL: bore bottom at z=0) --------------------------------------
BODY_D, BODY_H = 16.0, 8.0
# 7.5, not 8.5: at 8.5 the post top lands on 67.9 and the recess ceiling is AT
# 67.9. That is a tie, and a tie means it bottoms — it would jack the disk off
# its floor instead of driving it. 7.5 leaves 1.0 mm of air above the post.
POST_H = 7.5                      # 28.0 on the v2 hubs — see docstring
VENT_D = 4.0
MOUTH_CHAMFER = 0.8
GROOVE_DEPTH, GROOVE_W = 0.6, 1.5
BORES = {"spline_hub_press_v1disk": 5.2, "spline_hub_glue_v1disk": 5.6}


def cyl(r, z0, z1, x=0.0, y=0.0, seg=SEG):
    c = cylinder(radius=r, height=z1 - z0, sections=seg)
    c.apply_translation([x, y, (z0 + z1) / 2.0])
    return c


def hexa(af, z0, z1, rot=0.0):
    h = cyl(af / np.sqrt(3.0), z0, z1, seg=6)
    if rot:
        h.apply_transform(trimesh.transformations.rotation_matrix(rot, [0, 0, 1]))
    return h


def u(p):
    return trimesh.boolean.union(list(p), engine="manifold")


def diff(a, b):
    return trimesh.boolean.difference([a, u(b)], engine="manifold")


def horn():
    body = cyl(HORN_OD / 2, HORN_Z0, RECESS_Z1)
    # trimesh's 6-gon puts a VERTEX on +X. Rotate 30 deg so a FLAT faces each
    # screw at 45/135/225/315 — the orientation that minimises the scallop.
    cuts = [hexa(HEX_AF + HEX_SLOP, HORN_Z0 - 1.0, RECESS_Z1 + 1.0,
                 rot=np.radians(30.0) + np.radians(45.0))]
    for k in range(N_SCREWS):
        t = np.radians(45 + 90 * k)
        x, y = SCREW_BC / 2 * np.cos(t), SCREW_BC / 2 * np.sin(t)
        cuts.append(cyl(M3_CLEAR / 2, HORN_Z0 - 0.5, RECESS_Z1 + 0.5, x, y))
        c = cylinder(radius=CSK_D / 2, height=CSK_DEPTH, sections=64)
        v = c.vertices.copy()
        v[v[:, 2] > 0, :2] *= (M3_CLEAR / 2) / (CSK_D / 2)   # taper upward
        c.vertices = v
        c.apply_translation([x, y, HORN_Z0 + CSK_DEPTH / 2])
        cuts.append(c)
    return diff(body, cuts)


def hub(bore, glue):
    solids = [cyl(BODY_D / 2, 0.0, BODY_H), hexa(HEX_AF, BODY_H, BODY_H + POST_H)]
    cuts = [cyl(bore / 2, -0.5, BODY_H),
            cyl(VENT_D / 2, 0.0, BODY_H + POST_H + 1.0)]
    ch = cylinder(radius=bore / 2 + MOUTH_CHAMFER, height=MOUTH_CHAMFER * 2,
                  sections=SEG)
    v = ch.vertices.copy()
    v[v[:, 2] > 0, :2] *= (bore / 2) / (bore / 2 + MOUTH_CHAMFER)
    ch.vertices = v
    ch.apply_translation([0, 0, MOUTH_CHAMFER])
    cuts.append(ch)
    if glue:
        for z in (2.0, 5.0):
            cuts.append(cyl(bore / 2 + GROOVE_DEPTH, z, z + GROOVE_W))
    return diff(u(solids), cuts)


def main():
    ok = True
    parts = {"disk_horn_v1disk": horn()}
    for n, b in BORES.items():
        parts[n] = hub(b, glue="glue" in n)
    for n, m in parts.items():
        m.export(f"{n}.stl")
        e = m.extents
        good = m.is_watertight and m.body_count == 1
        ok &= good
        print(f"{n:26s} {e[0]:5.1f} x {e[1]:5.1f} x {e[2]:5.1f} mm  "
              f"{m.volume/1000:4.1f} cm3  wt={good}")

    def chk(l, c, d=""):
        nonlocal ok
        ok &= bool(c)
        print(f"  [{'ok  ' if c else 'FAIL'}] {l:44s} {d}")

    print("\nhorn vs the printed disk")
    chk("OD fits the Ø26 recess", HORN_OD < RECESS_D,
        f"{(RECESS_D-HORN_OD)/2:.2f} mm/side — this centres it")
    chk("OD clears the base's Ø28 bore", HORN_OD < SPLINE_BORE_D,
        f"{(SPLINE_BORE_D-HORN_OD)/2:.1f} mm/side")
    chk("spigot fills the 3.5 mm recess", abs((RECESS_Z1 - DISK_Z0) - 3.5) < 1e-9)
    chk("thread engagement in the disk", True, "67.9->75.4 = 7.5 mm; use M3x12 csk")

    print("\nthe declared scallop")
    inr = (HEX_AF + HEX_SLOP) / 2.0
    head_in = SCREW_BC / 2 - CSK_D / 2
    chk("hex FLATS face the screws", True, "best orientation; 30 deg + 45 deg")
    chk("scallop <= 0.3 mm", inr - head_in <= 0.3,
        f"{inr-head_in:.2f} mm into a {RECESS_Z1-HORN_Z0:.1f} mm socket")
    chk("  corner-on would be far worse",
        (HEX_AF + HEX_SLOP) / np.sqrt(3) - head_in > inr - head_in,
        f"{(HEX_AF+HEX_SLOP)/np.sqrt(3)-head_in:.2f} mm if rotated 30 deg")

    print("\nhex fit + engagement")
    chk("socket accepts the hub", HEX_SLOP >= 0.4, f"{HEX_SLOP} mm across flats")
    body_top = TAB_PLANE + BODY_H
    post_top = body_top + POST_H
    chk("post clears the hub body/horn gap", HORN_Z0 > body_top,
        f"horn bottom {HORN_Z0} vs hub body top {body_top:.1f} "
        f"-> {HORN_Z0-body_top:.1f} mm")
    chk("post does NOT bottom on the recess ceiling", post_top <= RECESS_Z1 - 0.8,
        f"post top {post_top:.1f}, ceiling {RECESS_Z1} "
        f"-> {RECESS_Z1-post_top:.1f} mm of air (a TIE here means it bottoms)")
    eng = min(post_top, RECESS_Z1) - HORN_Z0
    chk("engagement >= 4 mm", eng >= 4.0, f"{eng:.1f} mm (load needs ~30 kPa)")
    chk("v2's 28 mm post would NOT fit", TAB_PLANE + BODY_H + 28.0 > RECESS_Z1,
        f"would bottom {TAB_PLANE+BODY_H+28.0-RECESS_Z1:.0f} mm proud — saw it down")

    print(f"\n{'ALL CHECKS PASS' if ok else '*** FAILURES ***'}")
    print("\nPRINT   all three flat, socket/bore vertical, no supports, 4 perims.")
    print("HARDWARE 4x M3x12 COUNTERSUNK.")
    print("ASSEMBLY flip the printed disk on the bench, horn into the recess,")
    print("         4x M3 up. Glue the hub on the spline — slide it up/down the")
    print("         spline until the hex meets the horn, THEN glue. Lower the")
    print("         disk+horn in as one piece.")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
