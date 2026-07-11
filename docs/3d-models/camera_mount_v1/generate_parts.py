#!/usr/bin/env python3
"""camera_mount_v1 — ELP stereo camera mount for the shooter stand deck.

Camera: ELP-USB3DGS1200P01 binocular global-shutter USB module.
  Bare PCB 80 x 16.5mm, ~45g, dual M12 lenses, USB-C, 112 deg HFOV.

Three printed parts + M3 hardware:

  cam_shell_back   PCB sits component-side-down on corner ledges inside a
                   walled tray; rear cavity clears components. USB-C exit
                   windows on BOTH short ends (fits either orientation).
  cam_shell_front  clamps the PCB via 4x M3 self-taps into back-shell
                   bosses; one wide lens slot — exact lens pitch and barrel
                   size don't matter.
  mast             clevis on top (M3 cross-bolt + nyloc = friction tilt,
                   about -45..+45 deg), 60x40 base with 4x M3 through-holes;
                   self-tap into Ø2.8 pilots drilled in the deck (same
                   fastening as feet/risers on shooter_stand_v2_pan).

MEASURE-AND-CONFIRM placeholders (marked *PLACEHOLDER* below):
  PCB_COMP_H   rear component clearance — measure tallest rear component
  LENS_SLOT_H  lens slot height — measure lens holder base height/width
  USB_END      USB-C window size/position — windows cut on both ends anyway

PRINT: PETG. Shells flat (front face down / back face down), mast base down
(clevis needs supports, or split — it's small).
HARDWARE: 4x M3x10 self-tap (shell), 1x M3x30 + nyloc (tilt), 4x M3x12
self-tap into deck pilots.
"""

import numpy as np
import trimesh
from trimesh.creation import box, cylinder
from trimesh.transformations import rotation_matrix

# ---------------- camera facts (datasheet) ----------------
PCB_W, PCB_H, PCB_T = 80.0, 16.5, 1.7      # board outline + thickness
PCB_COMP_H = 5.0        # *PLACEHOLDER* rear component clearance depth
LENS_SLOT_W = 66.0      # front slot width (covers any lens pitch on 80 board)
LENS_SLOT_H = 15.0      # *PLACEHOLDER* slot height; lens holders ~14 sq
USB_END = (12.0, 8.0)   # *PLACEHOLDER* end-window w x h, both ends cut

# ---------------- fit / hardware ----------------
CLR = 0.4               # PCB pocket clearance per side
WALL = 3.0
M3, M3P = 3.4, 2.8      # through, self-tap pilot (matches stand convention)
LEDGE = 2.5             # corner ledges under PCB edges (keep off components)

# ---------------- mast ----------------
MAST_H = 110.0          # lens height above deck ~= MAST_H + shell half
MAST_W, MAST_T = 26.0, 10.0
BASE = (60.0, 40.0, 6.0)
BASE_HOLE_XY = [(-24, -14), (24, -14), (-24, 14), (24, 14)]
CLEVIS_GAP = 14.0       # inner gap: fits shell's 13.6 tongue + washers
CLEVIS_ARM = 6.0
PIVOT_DROP = 15.0       # pivot below shell body (tilt clearance geometry)
PIVOT_Z = MAST_H + 9.0  # pivot height on mast (tongue tip clears column top)

SEG = 96


def B(x0, x1, y0, y1, z0, z1):
    b = box(extents=[x1 - x0, y1 - y0, z1 - z0])
    b.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return b


def cyl(r, h, axis, at):
    c = cylinder(radius=r, height=h, sections=SEG)
    if axis == "x":
        c.apply_transform(rotation_matrix(np.pi / 2, [0, 1, 0]))
    elif axis == "y":
        c.apply_transform(rotation_matrix(np.pi / 2, [1, 0, 0]))
    c.apply_translation(at)
    return c


def union(x):
    return trimesh.boolean.union(x, engine="manifold")


def diff(x):
    return trimesh.boolean.difference(x, engine="manifold")


# Shell coordinate frame: PCB centered at origin, lenses face +Y,
# +Z up (PCB long axis = X, short axis = Z). Components on -Y side.
PKT_W = PCB_W + 2 * CLR                    # pocket dims
PKT_H = PCB_H + 2 * CLR
IN_W = PKT_W + 2 * WALL                    # shell outer dims
IN_H = PKT_H + 2 * WALL
BACK_D = PCB_COMP_H + WALL                 # back shell depth behind PCB face
FRONT_D = 5.0                              # front cover thickness
SCREW_XZ = [(-PKT_W / 2 + 3, -PKT_H / 2 + 3), (PKT_W / 2 - 3, -PKT_H / 2 + 3),
            (-PKT_W / 2 + 3, PKT_H / 2 - 3), (PKT_W / 2 - 3, PKT_H / 2 - 3)]


def shell_back():
    # tray: back face at y=-BACK_D, PCB back face rests at y=-PCB_T
    body = B(-IN_W / 2, IN_W / 2, -BACK_D, 0, -IN_H / 2, IN_H / 2)
    cav_comp = B(-PKT_W / 2 + LEDGE, PKT_W / 2 - LEDGE,     # component cavity
                 -BACK_D + WALL, -PCB_T, -PKT_H / 2 + LEDGE, PKT_H / 2 - LEDGE)
    cav_pcb = B(-PKT_W / 2, PKT_W / 2, -PCB_T, 0.1,          # PCB pocket
                -PKT_H / 2, PKT_H / 2)
    cuts = [cav_comp, cav_pcb]
    for x0, x1 in ((IN_W / 2 - WALL - 2, IN_W / 2 + 1),      # USB end windows
                   (-IN_W / 2 - 1, -IN_W / 2 + WALL + 2)):
        cuts.append(B(x0, x1, -PCB_T - USB_END[1], -PCB_T + 2,
                      -USB_END[0] / 2, USB_END[0] / 2))
    for sx, sz in SCREW_XZ:                                  # self-tap pilots
        cuts.append(cyl(M3P / 2, BACK_D + 2, "y", [sx, -BACK_D / 2, sz]))
    # tilt tongue: centered under shell, drops into mast clevis.
    # Pivot 15mm below shell body + 6mm arm margin above pivot = clean
    # tilt to ~±35 deg before the shell bottom meets the arm tops.
    tongue = B(-6.8, 6.8, -BACK_D, 0, -IN_H / 2 - 22, -IN_H / 2)
    body = union([body, tongue])
    cuts.append(cyl(M3 / 2, 30, "x", [0, -BACK_D / 2, -IN_H / 2 - PIVOT_DROP]))
    return diff([body, union(cuts)])


def shell_front():
    body = B(-IN_W / 2, IN_W / 2, 0, FRONT_D, -IN_H / 2, IN_H / 2)
    cuts = [B(-LENS_SLOT_W / 2, LENS_SLOT_W / 2, -1, FRONT_D + 1,
              -LENS_SLOT_H / 2, LENS_SLOT_H / 2)]
    for sx, sz in SCREW_XZ:
        cuts.append(cyl(M3 / 2, FRONT_D + 2, "y", [sx, FRONT_D / 2, sz]))
        cuts.append(cyl(3.2, 2.6, "y", [sx, FRONT_D - 1.2, sz]))  # head recess
    return diff([body, union(cuts)])


def mast():
    base = B(-BASE[0] / 2, BASE[0] / 2, -BASE[1] / 2, BASE[1] / 2, 0, BASE[2])
    col = B(-MAST_W / 2, MAST_W / 2, -MAST_T / 2, MAST_T / 2, 0, MAST_H)
    # clevis arms on top, gap along X for the shell tongue
    arms = [B(-CLEVIS_GAP / 2 - CLEVIS_ARM, -CLEVIS_GAP / 2,
              -MAST_T / 2, MAST_T / 2, MAST_H - 4, PIVOT_Z + 6),
            B(CLEVIS_GAP / 2, CLEVIS_GAP / 2 + CLEVIS_ARM,
              -MAST_T / 2, MAST_T / 2, MAST_H - 4, PIVOT_Z + 6)]
    # gusset base->column
    gus = B(-MAST_W / 2, MAST_W / 2, -BASE[1] / 2, MAST_T / 2, 0, 26)
    body = union([base, col, gus] + arms)
    cuts = [cyl(M3 / 2, CLEVIS_GAP + 2 * CLEVIS_ARM + 4, "x",
                [0, 0, PIVOT_Z])]
    for hx, hy in BASE_HOLE_XY:
        cuts.append(cyl(M3 / 2, BASE[2] + 2, "z", [hx, hy, BASE[2] / 2]))
        cuts.append(cyl(3.2, 2.8, "z", [hx, hy, BASE[2] - 1.3]))
    return diff([body, union(cuts)])


def main():
    import pathlib
    out = pathlib.Path(__file__).parent
    parts = {"cam_shell_back": shell_back(),
             "cam_shell_front": shell_front(),
             "mast": mast()}
    for name, m in parts.items():
        assert m.is_watertight, f"{name} not watertight"
        m.export(out / f"{name}.stl")
        print(f"{name}: {m.extents.round(1)} mm, watertight={m.is_watertight}")

    # assembled preview; set TILT_CHECK to e.g. 35 to verify clearance
    TILT_CHECK = 0.0
    shell = union([parts["cam_shell_back"], parts["cam_shell_front"]])
    shell.apply_translation([0, 4, IN_H / 2 + PIVOT_DROP])   # pivot -> origin
    shell.apply_transform(rotation_matrix(np.radians(TILT_CHECK), [1, 0, 0]))
    shell.apply_translation([0, -4, PIVOT_Z])
    inter = trimesh.boolean.intersection([shell, parts["mast"]],
                                         engine="manifold")
    print(f"tilt {TILT_CHECK} deg shell/mast overlap volume: {inter.volume:.2f} mm^3"
          if inter.volume > 0.01 else f"tilt {TILT_CHECK} deg: no collision")
    asm = union([shell, parts["mast"]])
    asm.export(out / "assembled_preview.stl")
    print("assembled_preview exported")


if __name__ == "__main__":
    main()
