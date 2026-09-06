#!/usr/bin/env python3
"""Section through y=0 (disk axis + chute axis) — shows the drive stack."""
import os
import numpy as np, trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import generate_parts as G

V1 = os.environ.get("V1_DIR", "../hopper_escapement_v1")
CLAMP_Z = 51.4   # nominal servo height. Design tolerates -13.4 .. +6.5 mm.


def sect(mesh, ax, color, label, dz=0.0, lw=1.2):
    s = mesh.section(plane_origin=[0, 0, 0], plane_normal=[0, 1, 0])
    if s is None:
        return
    for ent in s.entities:
        p = s.vertices[ent.points]
        ax.plot(p[:, 0], p[:, 2] + dz, color=color, lw=lw,
                label=label, solid_capstyle="round")
        label = None


fig, ax = plt.subplots(figsize=(11, 8))
for f, c, n in [("hopper_base_v1.stl", "#8a8a8a", "base v1 (KEPT, printed)"),
                ("drum_lid_v1.stl", "#8a8a8a", None)]:
    try:
        sect(trimesh.load(f"{V1}/{f}"), ax, c, n, lw=1.0)
    except Exception:
        pass

sect(trimesh.load("escapement_disk_v2.stl"), ax, "#1f77b4", "escapement_disk_v2")
sect(trimesh.load("spline_coupler_v2.stl"), ax, "#d62728", "spline_coupler_v2")
clamp = trimesh.load("spline_clamp_v2.stl")
clamp.apply_translation([G.DISK_AX[0], 0, CLAMP_Z])
sect(clamp, ax, "#2ca02c", "spline_clamp_v2 (height set by servo)")

# balls
for (cx, cz, lab) in [(0.0, G.FLOOR_Z1 + G.BALL / 2, "carried ball, on the floor"),
                      (-74.6, G.DISK_Z1 + G.BALL / 2, "queued ball, on the disk top")]:
    t = np.linspace(0, 2 * np.pi, 80)
    ax.plot(cx + G.BALL / 2 * np.cos(t), cz + G.BALL / 2 * np.sin(t),
            "--", color="#ff7f0e", lw=1.2, label=lab)

ax.axhline(G.DISK_Z1, color="#ff7f0e", lw=0.7, ls=":")
ax.annotate("disk top z=108 — THE SHEAR PLANE\n(ball crown is 104; thinner disk = double feed)",
            xy=(38, G.DISK_Z1), fontsize=8, color="#ff7f0e", va="bottom")
ax.annotate("hex joint: 20 mm tolerance window\non the servo height = no SPAN",
            xy=(-40, 75), xytext=(15, 40), fontsize=8, color="#d62728",
            arrowprops=dict(arrowstyle="->", color="#d62728", lw=1))
ax.annotate("pinch bolt — tightened\nin your hand, off the machine",
            xy=(-31, CLAMP_Z + 5), xytext=(-135, 30), fontsize=8, color="#2ca02c",
            arrowprops=dict(arrowstyle="->", color="#2ca02c", lw=1))
ax.annotate("4x M3x35 from the TOP",
            xy=(-40, G.DISK_Z1), xytext=(-140, 120), fontsize=8, color="#1f77b4",
            arrowprops=dict(arrowstyle="->", color="#1f77b4", lw=1))

ax.set_aspect("equal")
ax.set_xlabel("x (mm)   —   chute axis at 0, disk axis at -40")
ax.set_ylabel("z (mm)")
ax.set_title("hopper_escapement_v2 — section at y=0", fontsize=11)
ax.legend(fontsize=8, loc="upper right")
ax.grid(alpha=0.25, lw=0.4)
plt.tight_layout()
plt.savefig("preview_section.png", dpi=140)
print("preview_section.png")
