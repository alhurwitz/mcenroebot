#!/usr/bin/env python3
"""Section at y=0 through the disk axis — drive_rod_v3 in the printed hardware.

Draw the section. On this assembly the section drawing has caught a collision
that every numeric check missed (v2's clamp body vs coupler underside), so it
is not decoration.
"""
import os

import matplotlib
import numpy as np
import trimesh

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import generate_rod_v3 as G  # noqa: E402

V1 = os.environ.get("V1_DIR", "../hopper_escapement_v1")
DX = -40.0


def sect(mesh, ax, color, label, lw=1.2, ls="-"):
    s = mesh.section(plane_origin=[0, 0, 0], plane_normal=[0, 1, 0])
    if s is None:
        return
    for ent in s.entities:
        p = s.vertices[ent.points]
        ax.plot(p[:, 0], p[:, 2], color=color, lw=lw, ls=ls, label=label,
                solid_capstyle="round")
        label = None


fig, ax = plt.subplots(figsize=(11, 8.5))

for f in ("hopper_base_v1.stl", "drum_lid_v1.stl", "servo_saddle_v1.stl"):
    try:
        sect(trimesh.load(f"{V1}/{f}"), ax, "#8a8a8a",
             "printed, KEPT" if f.startswith("hopper") else None, lw=1.0)
    except Exception:
        pass

sect(trimesh.load(f"{V1}/escapement_disk_v1.stl"), ax, "#1f77b4",
     "escapement_disk_v1 (PRINTED — reused, not drilled)")

rod = trimesh.load("drive_rod_glue_v3.stl")
rod.apply_translation([DX, 0, 0])
sect(rod, ax, "#d62728", "drive_rod_glue_v3 (the new part)", lw=1.8)

# where the spline might be — the whole point is that it does not matter
for z, lab, c in ((51.4 + 4.0, "spline, if it sits LOW", "#2ca02c"),
                  (51.4 + 14.0, "spline, if it sits HIGH", "#2ca02c")):
    ax.plot([DX - 2.96, DX - 2.96, DX + 2.96, DX + 2.96],
            [z - 4.5, z, z, z - 4.5], color=c, lw=2.2, ls="-",
            label=lab if z < 60 else None)
    ax.annotate("", xy=(DX + 9, z), xytext=(DX + 9, z - 4.5),
                arrowprops=dict(arrowstyle="-", color=c, lw=0.8))

ax.annotate(f"socket {G.SOCKET_Z1-G.NOSE_Z0:.0f} mm deep, open at the bottom\n"
            "the spline stops WHEREVER it stops",
            xy=(DX + 3, 58), xytext=(-135, 34), fontsize=8, color="#d62728",
            arrowprops=dict(arrowstyle="->", color="#d62728", lw=1))
ax.annotate("pin journals the disk over 39.5 mm\n"
            "(v2b had 3.5 mm of spigot)",
            xy=(DX + 3, 90), xytext=(-150, 96), fontsize=8, color="#d62728",
            arrowprops=dict(arrowstyle="->", color="#d62728", lw=1))
ax.annotate("Ø3 vent — sight line from the disk's TOP face,\n"
            "and the spline can never bottom",
            xy=(DX, 105), xytext=(-20, 128), fontsize=8, color="#d62728",
            arrowprops=dict(arrowstyle="->", color="#d62728", lw=1))
ax.annotate("flange TOP on the recess floor z=67.9\n"
            "4x M3x10 up from below — the ONLY\nface that touches the disk",
            xy=(DX + 10, 67.9), xytext=(2, 74), fontsize=8, color="#1f77b4",
            arrowprops=dict(arrowstyle="->", color="#1f77b4", lw=1))
ax.annotate("disk sits on the FLOOR, not on the rod\n(v1 hung it off the spline)",
            xy=(DX + 26, 64.2), xytext=(-160, 58), fontsize=8, color="#1f77b4",
            arrowprops=dict(arrowstyle="->", color="#1f77b4", lw=1))
ax.annotate("nose is LONG on purpose — saw it back\nat a scribe ring if it fouls the servo",
            xy=(DX, 49), xytext=(-165, 18), fontsize=8, color="#2ca02c",
            arrowprops=dict(arrowstyle="->", color="#2ca02c", lw=1))

ax.axhline(G.FLOOR_Z1, color="#999", lw=0.6, ls=":")
ax.axhline(G.FLOOR_Z0, color="#999", lw=0.6, ls=":")
ax.set_aspect("equal")
ax.set_xlabel("x (mm)   —   chute axis at 0, disk/servo axis at -40")
ax.set_ylabel("z (mm)")
ax.set_title("drive_rod_v3 — one part, spline to disk, section at y=0", fontsize=11)
ax.legend(fontsize=8, loc="upper left")
ax.grid(alpha=0.25, lw=0.4)
plt.tight_layout()
plt.savefig("preview_rod_v3.png", dpi=150)
print("preview_rod_v3.png")
