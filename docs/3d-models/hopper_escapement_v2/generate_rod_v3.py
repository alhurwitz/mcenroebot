#!/usr/bin/env python3
"""
drive_rod_v3 — ONE part: servo spline -> all the way THROUGH escapement_disk_v1.

AJ, 2026-08-29: "make me a drive rod that goes through the existing escapement
disk and can attach the spline of the servo."

This replaces the spline_coupler_v2 + spline_hub_v3 pair with a single piece,
and it keeps the disk you already printed. Nothing gets reprinted but this.

WHAT IT ACTUALLY BOLTS TO — RAY-CAST OFF escapement_disk_v1.stl, NOT ASSUMED
===========================================================================
    disk body                       z 64.4 .. 108.4   (Ø136)
    underside recess Ø26.0          z 64.4 .. 67.9    (3.5 deep)
    4x tapped Ø3.2 holes, BC 16.0   z 67.9 .. 75.4    at 45/135/225/315 deg
    centre hole Ø6.5, THROUGH       z 64.4 .. 108.4
and off hopper_base_v1.stl:
    floor slab                      z 51.4 .. 64.0
    spline bore Ø28 through it      (open to r<14 on the disk axis)
    lid underside                   z 109.4

NOTE the tap depth. Memory said "11 mm deep"; that is 64.4->75.4, but the first
3.5 mm of that is the RECESS, which is open space. There is only **7.5 mm of
threadable material**, 67.9..75.4. Use M3x10. An M3x12 or M3x16 bottoms out and
jacks the rod off its seat. check_rod_v3.py asserts this.

WHY A THROUGH-ROD IS BETTER THAN THE v2b COUPLER
================================================
generate_reuse.py flagged its own worst property: reusing the printed disk moves
the drive down to a 3.5 mm flange at the disk's underside, "strictly the weaker
joint," because the disk is then only held square by 3.5 mm of spigot.

Running the rod all the way through fixes exactly that, for free. The Ø6 pin
journals the rod to the disk over **39.5 mm** instead of 3.5. The disk cannot
cock on the rod no matter what the four screws do. That is AJ's idea and it is
the right one.

It also costs nothing to print (~6 cm3) and needs no drilling: the pin goes
through the Ø6.5 centre hole the disk already has. v2b needed that hole opened
to Ø13. This does not.

THE ONE NUMBER THIS PROJECT KEEPS GETTING WRONG — AND HOW THIS PART DODGES IT
=============================================================================
Spline height above the tab plane. It killed SV_TAB_TO_HORN=13.0, and I cannot
recover it from the STLs either: the saddle (z 45.4..51.4, cutout 18x42 for the
servo body) and the flat floor underside at 51.4 do not pin down where the
spline top lands. So this part does not have an opinion about it.

    socket mouth  z 48.0      (3.4 mm INTO the saddle cutout)
    socket end    z 67.9
    -> a 19.9 mm socket. The spline lands wherever it lands.

The nose is deliberately LONG. If it fouls the servo case, saw it back — there
are scribe rings at 2 mm intervals so you can cut to a known length and finally
READ OFF what the real spline height is. Long-and-trimmable is the recoverable
direction; short is a reprint. Same logic as generate_hub.py's undersized bores,
applied to length instead of diameter.

GLUE IS THE PRIMARY VARIANT, AND THAT IS NOT LAZINESS
=====================================================
A press fit needs the interference to be exactly where the spline sits. On a
19.9 mm socket with an unknown spline height, you cannot place a 10 mm
interference band and know the spline is inside it — put it at the mouth and a
high spline sits in clear air above it. A uniform Ø5.2 interference over 19.9 mm
is a 20 mm press, which is the galling failure drive_rod_v1 was rejected for.

Adhesive does not care where the spline stops. That is the whole reason it wins
here. AJ already accepted press/glue on 2026-08-29, so this is not a new ask.

    drive_rod_glue_v3    bore 5.6, 4 adhesive grooves.  PRINT THIS ONE.
    drive_rod_press_v3   bore 5.2, uniform. Only if 5.6 feels loose on your
                         spline. Expect a hard push; open it with a 5.5 mm bit
                         if it will not start. Too tight is fixable, too loose
                         is a reprint.

NOTHING CARRIES THE DISK BUT THE FLOOR
======================================
v1 hung the disk off the spline; that is the only reason its height mattered.
Here the disk sits on the base floor (its underside drops the 0.4 mm v1 left as
DISK_GAP) and the rod hangs from the disk. The rod has no shoulder anywhere near
the disk's underside, on purpose — its only contact with the disk is the flange
TOP face against the recess floor at z=67.9, which the four screws pull up into.
The Ø3 vent up the pin means the spline can never bottom in the socket and lift
the disk either.
"""

import math

import numpy as np
import trimesh
from trimesh.creation import cylinder, revolve

SEG = 128

# ---- measured off the REAL printed parts (see check_rod_v3.py) -------------
DISK_Z0, DISK_Z1 = 64.4, 108.4
RECESS_D, RECESS_Z1 = 26.0, 67.9      # O26 x 3.5 deep in the underside
CENTRE_HOLE_D = 6.5                   # through, 64.4..108.4
SCREW_BC = 16.0
SCREW_ANGLES = (45.0, 135.0, 225.0, 315.0)
TAP_Z0, TAP_Z1 = 67.9, 75.4           # 7.5 mm of threadable material. That is all.
FLOOR_Z0, FLOOR_Z1 = 51.4, 64.0       # base floor slab
SPLINE_BORE_D = 28.0
LID_Z0 = 109.4

# ---- the rod ---------------------------------------------------------------
NOSE_Z0 = 48.0                        # 3.4 mm into the saddle cutout. TRIMMABLE.
NOSE_D = 10.0
NOSE_Z1 = 54.0
CONE_Z1 = 61.6                        # 45 deg: 7.6 rise for 7.6 mm of radius
FLANGE_D = 25.2                       # in a O26 recess. Loose on purpose: the
                                      # PIN is the centring datum, not this.
FLANGE_Z1 = RECESS_Z1                 # 67.9 - seats on the recess floor
PIN_D = 6.0                           # through the disk's O6.5 hole
PIN_Z1 = DISK_Z1 - 1.0                # 107.4: stops short of the disk top so it
                                      # can NEVER touch the lid at 109.4

VENT_D = 3.0                          # glue vent + sight/probe line out the top
SOCKET_Z1 = RECESS_Z1                 # 67.9

M3_CLEAR = 3.4
CB_D, CB_H = 6.4, 3.0                 # head pocket, floor at 64.6
SCREW_LEN = 10.0                      # M3x10. NOT x12, NOT x16 - see below.
MOUTH_CHAMFER = 0.8
SCRIBE_Z = (49.0, 52.0)               # cut-to-length marks on the nose
SCRIBE_DEPTH, SCRIBE_W = 0.35, 0.6

VARIANTS = {
    "drive_rod_glue_v3": dict(bore=5.6, grooves=True),
    "drive_rod_press_v3": dict(bore=5.2, grooves=False),
}
GROOVE_DEPTH, GROOVE_W = 0.6, 1.5
GROOVE_Z = (50.5, 55.0, 59.5, 64.0)


def cyl(r, z0, z1, x=0.0, y=0.0, seg=SEG):
    c = cylinder(radius=r, height=z1 - z0, sections=seg)
    c.apply_translation([x, y, (z0 + z1) / 2.0])
    return c


def ring(r_in, r_out, z0, z1, seg=SEG):
    """Annular cut - built by revolve so it can never leave sliver faces."""
    prof = [(r_in, z0), (r_out, z0), (r_out, z1), (r_in, z1), (r_in, z0)]
    return revolve(np.array(prof, dtype=float), sections=seg)


def shell(bore):
    """The whole rod as ONE solid of revolution: no boolean union, no slivers.

    Profile runs up the outside and back down the through-bore, so the socket
    and the vent are part of the revolve rather than subtractions.
    """
    rb, rv = bore / 2.0, VENT_D / 2.0
    prof = [
        (rb, NOSE_Z0),                      # bore mouth
        (NOSE_D / 2, NOSE_Z0),              # bottom face
        (NOSE_D / 2, NOSE_Z1),              # nose
        (FLANGE_D / 2, CONE_Z1),            # 45 deg cone
        (FLANGE_D / 2, FLANGE_Z1),          # flange
        (PIN_D / 2, FLANGE_Z1),             # flange top - THE seating face
        (PIN_D / 2, PIN_Z1),                # pin
        (rv, PIN_Z1),                       # pin top face
        (rv, SOCKET_Z1),                    # vent, coming back down
        (rb, SOCKET_Z1),                    # socket blind end (annular)
        (rb, NOSE_Z0),                      # socket wall, back to the mouth
    ]
    return revolve(np.array(prof, dtype=float), sections=SEG)


def rod(bore, grooves):
    cuts = []

    # bore mouth lead-in - the spline has to start square, blind, from below
    ch = cylinder(radius=bore / 2 + MOUTH_CHAMFER, height=MOUTH_CHAMFER * 2,
                  sections=SEG)
    v = ch.vertices.copy()
    v[v[:, 2] > 0, :2] *= (bore / 2) / (bore / 2 + MOUTH_CHAMFER)
    ch.vertices = v
    ch.apply_translation([0, 0, NOSE_Z0 + MOUTH_CHAMFER])
    cuts.append(ch)

    # screws: clearance through the flange, head pocketed so nothing proud can
    # bear on the disk underside or on the floor
    for a in SCREW_ANGLES:
        x = SCREW_BC / 2 * math.cos(math.radians(a))
        y = SCREW_BC / 2 * math.sin(math.radians(a))
        cuts.append(cyl(M3_CLEAR / 2, CONE_Z1 - 1.0, FLANGE_Z1 + 0.5, x, y))
        cuts.append(cyl(CB_D / 2, CONE_Z1 - 0.5, CONE_Z1 + CB_H, x, y))

    # cut-to-length marks, so trimming the nose MEASURES the spline height
    for z in SCRIBE_Z:
        cuts.append(ring(NOSE_D / 2 - SCRIBE_DEPTH, NOSE_D / 2 + 0.5,
                         z, z + SCRIBE_W))

    if grooves:
        for z in GROOVE_Z:
            cuts.append(ring(bore / 2, bore / 2 + GROOVE_DEPTH, z, z + GROOVE_W))

    return trimesh.boolean.difference(
        [shell(bore), trimesh.boolean.union(cuts, engine="manifold")],
        engine="manifold")


def main():
    ok = True
    engage = SCREW_LEN - (FLANGE_Z1 - (CONE_Z1 + CB_H))
    for name, cfg in VARIANTS.items():
        m = rod(cfg["bore"], cfg["grooves"])
        m.export(f"{name}.stl")
        lo, hi = m.bounds
        good = m.is_watertight and m.body_count == 1 and m.volume > 0
        ok &= good
        print(f"{name:20s} bore {cfg['bore']:.1f}  O{m.extents[0]:.1f} x "
              f"{m.extents[2]:.1f} mm tall   z {lo[2]:.1f}..{hi[2]:.1f}   "
              f"{m.volume/1000:.1f} cm3  wt={good}")

    print(f"\nsocket {SOCKET_Z1-NOSE_Z0:.1f} mm deep, mouth z={NOSE_Z0} - the "
          f"spline lands anywhere in it")
    print(f"pin journals the disk over {PIN_Z1-FLANGE_Z1:.1f} mm "
          f"(v2b's flange managed 3.5)")
    print(f"pin top z={PIN_Z1}, lid underside z={LID_Z0} -> "
          f"{LID_Z0-PIN_Z1:.1f} mm clear")
    print(f"\nHARDWARE  4x M3x{SCREW_LEN:.0f} ONLY. Threadable depth is "
          f"{TAP_Z1-TAP_Z0:.1f} mm ({TAP_Z0}..{TAP_Z1});")
    print(f"          M3x{SCREW_LEN:.0f} engages {engage:.1f} mm. Anything "
          f"longer than M3x{SCREW_LEN+(TAP_Z1-TAP_Z0-engage):.0f} bottoms in the")
    print("          tap and jacks the rod off its seat.")
    print("\nPRINT     nose DOWN, brim (O10 footprint under a 59 mm part),")
    print("          4 perimeters, 40%, no supports. ~6 cm3, well under an hour.")
    print("\nFIT       pin O6.0 into the disk's printed O6.5 hole. If it will")
    print("          not enter, run a 6.5 mm bit through once - it self-pilots.")
    print("          Do NOT force it; the pin is the centring datum.")
    print("\nASSEMBLE  1. disk upside down on the bench")
    print("          2. rod pin-first through the centre hole, flange into the")
    print("             recess, 4x M3x10 up. The flange TOP seats on the recess")
    print("             floor - that is the only face that touches the disk.")
    print("          3. drop disk+rod into the drum from above. Disk lands on")
    print("             the FLOOR. Rod hangs down the O28 bore.")
    print("          4. adhesive on the spline, lift the servo up until its")
    print("             tabs meet the saddle, screw the saddle. The spline")
    print("             slides into the socket as far as it goes and STOPS")
    print("             THERE. Nothing is forced, nothing is measured.")
    print("          5. look down the O3 vent from the disk's top face before")
    print("             the adhesive goes off. Lid, cone, done.")
    print("\nIF THE NOSE FOULS THE SERVO: saw it back at a scribe ring")
    print(f"          (rings at z={SCRIBE_Z}, i.e. {SCRIBE_Z[0]-NOSE_Z0:.0f} and "
          f"{SCRIBE_Z[1]-NOSE_Z0:.0f} mm up from the tip).")
    print("          Write down which ring you cut to - that number is the")
    print("          spline height this project has never actually had.")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
