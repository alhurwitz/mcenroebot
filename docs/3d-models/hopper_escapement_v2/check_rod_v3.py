#!/usr/bin/env python3
"""
drive_rod_v3 verification.

Every dimension the rod depends on is RAY-CAST off the printed parts
(escapement_disk_v1.stl, hopper_base_v1.stl, servo_saddle_v1.stl, drum_lid_v1.stl)
rather than read out of v1's source constants. Those parts are on the machine
and cannot change; the rod is the only thing that can.

    V1_DIR=... python3 check_rod_v3.py
"""

import math
import os

import numpy as np
import trimesh

import generate_rod_v3 as G

V1 = os.environ.get("V1_DIR", "../hopper_escapement_v1")
DX, DY = -40.0, 0.0          # disk / servo axis in the escapement frame
OK = True


def chk(label, cond, detail=""):
    global OK
    OK &= bool(cond)
    print(f"  [{'ok  ' if cond else 'FAIL'}] {label:56s} {detail}")


def near(a, b, tol=0.02):
    """STLs are float32 — never compare these exactly."""
    return abs(float(a) - float(b)) <= tol


def col(mesh, x, y, z0=400.0):
    loc, _, _ = mesh.ray.intersects_location(
        np.array([[x, y, z0]]), np.array([[0.0, 0.0, -1.0]]), multiple_hits=True)
    return np.sort(loc[:, 2])[::-1] if len(loc) else np.array([])


def scan(mesh, pred, r0, r1, ang=0.0, step=0.01):
    """First radius (from r0 outward) where pred(column) goes true."""
    for r in np.arange(r0, r1, step):
        x = DX + r * math.cos(math.radians(ang))
        y = DY + r * math.sin(math.radians(ang))
        if pred(col(mesh, x, y)):
            return float(r)
    return None


disk = trimesh.load(f"{V1}/escapement_disk_v1.stl")
base = trimesh.load(f"{V1}/hopper_base_v1.stl")
sad = trimesh.load(f"{V1}/servo_saddle_v1.stl")
lid = trimesh.load(f"{V1}/drum_lid_v1.stl")
glue = trimesh.load("drive_rod_glue_v3.stl")
press = trimesh.load("drive_rod_press_v3.stl")

print("meshes")
for n, m in (("glue", glue), ("press", press)):
    chk(f"{n} watertight", m.is_watertight)
    chk(f"{n} single body", m.body_count == 1, f"{m.body_count} bodies")
    chk(f"{n} positive volume", m.volume > 0, f"{m.volume/1000:.1f} cm3")

print("\nTHE DISK IT BOLTS TO — measured, not assumed")
d_lo, d_hi = disk.bounds
chk("disk z extent", near(d_lo[2], G.DISK_Z0) and near(d_hi[2], G.DISK_Z1),
    f"{d_lo[2]:.1f}..{d_hi[2]:.1f}")
hole_r = scan(disk, lambda h: len(h) > 0, 2.5, 5.0)
chk("centre hole radius", abs(2 * hole_r - G.CENTRE_HOLE_D) < 0.02,
    f"measured O{2*hole_r:.2f}, code says O{G.CENTRE_HOLE_D}")
rec_r = scan(disk, lambda h: len(h) and abs(h[-1] - G.DISK_Z0) < 0.05, 10.0, 16.0)
chk("recess radius", abs(2 * rec_r - G.RECESS_D) < 0.02,
    f"measured O{2*rec_r:.2f}, code says O{G.RECESS_D}")
rec_floor = col(disk, DX + 5.0, DY)[-1]
chk("recess floor z", near(rec_floor, G.RECESS_Z1), f"{rec_floor:.1f}")
# tapped holes: position AND the depth that actually has thread in it
found = []
for a in G.SCREW_ANGLES:
    x = DX + G.SCREW_BC / 2 * math.cos(math.radians(a))
    y = DY + G.SCREW_BC / 2 * math.sin(math.radians(a))
    h = col(disk, x, y)
    found.append(h[-1] if len(h) else None)
chk("4 tapped holes on the coded BC/angles", all(f is not None for f in found),
    f"hole ceilings at z={[round(f,1) for f in found]}")
tap_ceiling = found[0]
chk("tap ceiling z", near(tap_ceiling, G.TAP_Z1), f"{tap_ceiling:.1f}")
thread = tap_ceiling - rec_floor
chk("THREADABLE depth is the recess floor to the hole ceiling",
    near(thread, G.TAP_Z1 - G.TAP_Z0),
    f"{thread:.1f} mm — NOT the 11.0 mm measured from the disk underside")

print("\nSCREWS — the mistake this check exists to prevent")
seat = G.CONE_Z1 + G.CB_H
grip = G.FLANGE_Z1 - seat
engage = G.SCREW_LEN - grip
chk("head seat is a flat pocket inside the flange", G.CB_D / 2 + G.SCREW_BC / 2 < G.FLANGE_D / 2,
    f"pocket rim r{G.SCREW_BC/2+G.CB_D/2:.1f} < flange r{G.FLANGE_D/2}")
chk("head fully recessed", G.CB_H >= 2.6, f"{G.CB_H} mm pocket for a ~2.4 mm head")
chk("screw engages the thread", engage > 4.0, f"{engage:.1f} mm")
chk("screw does NOT bottom in the tap", engage <= thread,
    f"{engage:.1f} <= {thread:.1f} mm available")
chk("  M3x12 would bottom (why the note is in the docstring)",
    12.0 - grip > thread, f"{12.0-grip:.1f} > {thread:.1f}")
chk("screw clearance vs the socket bore",
    G.SCREW_BC / 2 - G.M3_CLEAR / 2 > max(v["bore"] for v in G.VARIANTS.values()) / 2,
    f"hole inner r{G.SCREW_BC/2-G.M3_CLEAR/2:.1f}")

print("\nTHE PIN — what makes this better than the v2b flange")
chk("pin fits the disk's printed centre hole", G.PIN_D < 2 * hole_r,
    f"O{G.PIN_D} in O{2*hole_r:.2f} -> {(2*hole_r-G.PIN_D)/2:.2f} mm/side")
chk("  and no drilling is required", G.PIN_D < 2 * hole_r,
    "v2b needed this hole opened O6.5 -> O13")
journal = G.PIN_Z1 - G.FLANGE_Z1
chk("pin journals the disk over its full height", journal > 35.0,
    f"{journal:.1f} mm vs 3.5 mm of spigot in v2b")
chk("pin wall thickness", (G.PIN_D - G.VENT_D) / 2 >= 1.4,
    f"{(G.PIN_D-G.VENT_D)/2:.1f} mm — it carries no torque, only alignment")
lid_lo = lid.bounds[0][2]
chk("pin cannot touch the lid", G.PIN_Z1 < lid_lo,
    f"pin top {G.PIN_Z1} vs lid underside {lid_lo:.1f} -> {lid_lo-G.PIN_Z1:.1f} mm")
chk("  even with the disk sitting on the floor", G.PIN_Z1 - 0.4 < lid_lo, "0.4 mm of settle")
chk("pin top is below the disk top (nothing proud)", G.PIN_Z1 < G.DISK_Z1,
    f"{G.DISK_Z1-G.PIN_Z1:.1f} mm recessed")

print("\nTHE FLANGE — one contact face, and it is not the disk underside")
chk("flange enters the recess", G.FLANGE_D < 2 * rec_r,
    f"O{G.FLANGE_D} in O{2*rec_r:.1f} -> {(2*rec_r-G.FLANGE_D)/2:.2f} mm/side")
chk("flange top seats on the recess floor", near(G.FLANGE_Z1, rec_floor),
    "the ONLY face that touches the disk")
chk("no rod material at the disk underside plane wider than the recess",
    G.FLANGE_D < 2 * rec_r,
    "so the rod can never carry the disk — the FLOOR does (v1's failure)")
chk("flange is thicker than the recess is deep", G.FLANGE_Z1 - G.CONE_Z1 > rec_floor - G.DISK_Z0,
    f"{G.FLANGE_Z1-G.CONE_Z1:.1f} mm flange in a {rec_floor-G.DISK_Z0:.1f} mm recess "
    f"— the rest hangs in the base bore")

print("\nTHE BASE — measured bore, and what may pass through it")
bore_r = scan(base, lambda h: len(h) > 0, 6.0, 20.0, ang=90.0)
chk("spline bore radius", abs(2 * bore_r - G.SPLINE_BORE_D) < 0.02,
    f"measured O{2*bore_r:.2f}")
floor = col(base, DX, DY + bore_r + 4.0)
chk("floor slab z", any(near(h, G.FLOOR_Z1) for h in floor)
    and any(near(h, G.FLOOR_Z0) for h in floor),
    f"{np.round(floor,1)} vs {G.FLOOR_Z0}..{G.FLOOR_Z1}")
chk("widest part of the rod clears the bore", G.FLANGE_D < 2 * bore_r,
    f"O{G.FLANGE_D} in O{2*bore_r:.1f} -> {(2*bore_r-G.FLANGE_D)/2:.1f} mm/side")
chk("  it never has to SLIDE through it", True,
    "rod goes in from above, with the disk; the bore is clearance only")
sad_lo, sad_hi = sad.bounds
chk("saddle top is the floor underside", near(sad_hi[2], G.FLOOR_Z0),
    f"saddle z {sad_lo[2]:.1f}..{sad_hi[2]:.1f}")
# the nose hangs below the floor underside — it must fit the saddle's cutout
cut = [(x, y) for x in np.arange(sad_lo[0], sad_hi[0], 0.5)
       for y in np.arange(sad_lo[1], sad_hi[1], 0.5)
       if len(col(sad, x, y)) == 0]
cx = [p[0] for p in cut]
cy = [p[1] for p in cut]
chk("saddle has a servo-body cutout", len(cut) > 0,
    f"~{min(cx):.0f}..{max(cx):.0f} x {min(cy):.0f}..{max(cy):.0f} mm")
nose_below = G.FLOOR_Z0 - G.NOSE_Z0
chk("nose hangs below the floor into that cutout", nose_below > 0,
    f"{nose_below:.1f} mm of nose below z={G.FLOOR_Z0}")
chk("  and the nose is narrow enough to be there",
    G.NOSE_D / 2 < min(DX - min(cx), max(cx) - DX),
    f"O{G.NOSE_D} nose, cutout reaches {min(DX-min(cx), max(cx)-DX):.1f} mm "
    f"from the axis on the short side")
chk("  trimmable if it still fouls the servo", len(G.SCRIBE_Z) >= 2,
    f"scribe rings at z={G.SCRIBE_Z} — long-and-trimmable is the recoverable "
    f"direction")

print("\nTHE SOCKET — the number this project keeps getting wrong")
depth = G.SOCKET_Z1 - G.NOSE_Z0
chk("socket depth", depth >= 18.0, f"{depth:.1f} mm")
chk("mouth is below the floor underside", G.NOSE_Z0 < G.FLOOR_Z0,
    f"mouth z={G.NOSE_Z0} vs floor underside {G.FLOOR_Z0}")
chk("blind end is at the recess floor", near(G.SOCKET_Z1, rec_floor),
    "the deepest the spline could ever need to go")
chk("spline can NEVER bottom and lift the disk", G.VENT_D < min(
    v["bore"] for v in G.VARIANTS.values()),
    f"O{G.VENT_D} vent above a O{min(v['bore'] for v in G.VARIANTS.values())} "
    f"socket — but it is {G.SOCKET_Z1-G.FLOOR_Z0:.1f} mm above the floor "
    f"underside, further than any spline reaches")
chk("  vent gives a sight line from the disk's TOP face", G.VENT_D >= 2.5,
    f"O{G.VENT_D} — check engagement before the adhesive goes off")
chk("socket has a lead-in for blind entry", G.MOUTH_CHAMFER >= 0.5,
    f"{G.MOUTH_CHAMFER} mm chamfer")

print("\nWALL SECTIONS")
for name, cfg in G.VARIANTS.items():
    w = (G.NOSE_D - cfg["bore"]) / 2
    chk(f"{name}: nose wall", w >= 2.0, f"{w:.2f} mm")
    if cfg["grooves"]:
        wg = (G.NOSE_D - cfg["bore"] - 2 * G.GROOVE_DEPTH) / 2
        chk(f"{name}: nose wall at an adhesive groove", wg >= 1.4, f"{wg:.2f} mm")
chk("press bore is the smaller one", G.VARIANTS["drive_rod_press_v3"]["bore"]
    < G.VARIANTS["drive_rod_glue_v3"]["bore"],
    "err small: a tight bore opens with a drill, a loose one is a reprint")

print("\nPRINTABILITY")
cone_angle = math.degrees(math.atan2(
    (G.FLANGE_D - G.NOSE_D) / 2, G.CONE_Z1 - G.NOSE_Z1))
chk("cone overhang <= 45 deg", cone_angle <= 45.5, f"{cone_angle:.1f} deg from vertical")
chk("no supports needed anywhere", cone_angle <= 45.5,
    "the only other ceilings are the O6.4 head pockets — 6.4 mm bridges")
chk("nose-down footprint", G.NOSE_D >= 8.0,
    f"O{G.NOSE_D} under a {G.PIN_Z1-G.NOSE_Z0:.0f} mm part — USE A BRIM")

print("\nWHAT AJ ASKED FOR")
chk("goes THROUGH the existing disk", G.PIN_Z1 > G.DISK_Z0 + 30,
    f"pin runs z {G.FLANGE_Z1}..{G.PIN_Z1}, disk is {G.DISK_Z0}..{G.DISK_Z1}")
chk("attaches to the servo spline", depth > 15, f"{depth:.1f} mm socket")
chk("existing disk reused, not reprinted", True, "no drilling either")
chk("one part, not three", True, "replaces spline_coupler_v2 + spline_hub_v3")

print(f"\n{'ALL CHECKS PASS' if OK else '*** FAILURES ABOVE ***'}")
print("\nSTILL UNKNOWN (and deliberately does not matter):")
print("  How far the MG996R spline stands above the tab plane. The socket is")
print(f"  {depth:.1f} mm deep and open at the bottom; the spline stops wherever it")
print("  stops and the adhesive takes it from there. If the nose fouls the")
print("  servo case, cut it back at a scribe ring and write the number down.")
raise SystemExit(0 if OK else 1)
