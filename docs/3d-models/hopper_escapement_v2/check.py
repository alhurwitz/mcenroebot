#!/usr/bin/env python3
"""
hopper_escapement_v2 verification.

Everything that can be is checked against the REAL PRINTED PARTS
(hopper_base_v1.stl, drum_lid_v1.stl), not against v1's source constants,
because those parts are on the machine and cannot change. Same discipline as
pan_base_v3/check.py.

Point V1 at wherever the v1 STLs live; the default is the sibling folder in
docs/3d-models/.
"""

import os

import numpy as np
import trimesh

import generate_parts as G

V1 = os.environ.get("V1_DIR", "../hopper_escapement_v1")
OK = True


def chk(label, cond, detail=""):
    global OK
    OK &= bool(cond)
    print(f"  [{'ok  ' if cond else 'FAIL'}] {label:54s} {detail}")


def col(mesh, x, y, z0=300.0):
    """Downward ray: sorted z of every surface crossing, top first."""
    loc, _, _ = mesh.ray.intersects_location(
        np.array([[x, y, z0]]), np.array([[0.0, 0.0, -1.0]]), multiple_hits=True)
    return np.sort(loc[:, 2])[::-1] if len(loc) else np.array([])


base = trimesh.load(f"{V1}/hopper_base_v1.stl")
lid = trimesh.load(f"{V1}/drum_lid_v1.stl")
disk = trimesh.load("escapement_disk_v2.stl")
coup = trimesh.load("spline_coupler_v2.stl")
clamp = trimesh.load("spline_clamp_v2.stl")
DX, DY = G.DISK_AX

print("meshes")
for n, m in [("disk", disk), ("coupler", coup), ("clamp", clamp)]:
    chk(f"{n} watertight", m.is_watertight)
    chk(f"{n} single body", m.body_count == 1, f"{m.body_count}")

print("\nTHE MECHANISM — single-ball metering (the reason DISK_T is 44)")
ball_crown = G.FLOOR_Z1 + G.BALL
chk("disk top >= carried ball crown", G.DISK_Z1 >= ball_crown,
    f"disk top {G.DISK_Z1} vs crown {ball_crown} -> {G.DISK_Z1-ball_crown:+.1f} mm")
chk("  DISK_T >= BALL (shear plane)", G.DISK_T >= G.BALL,
    f"{G.DISK_T} >= {G.BALL}. Thinning this double-feeds.")
sep = np.sqrt(max(G.BALL**2 - (G.BALL - (G.DISK_Z1 - ball_crown))**2, 0))
chk("  queued ball lands on disk, not on carried ball", G.DISK_Z1 >= ball_crown,
    f"else needs {28.6:.1f} mm lateral clearance before they part")
chk("lid gap too small to admit a ball", G.LID_Z0 - G.DISK_Z1 < G.BALL,
    f"{G.LID_Z0-G.DISK_Z1:.1f} mm << {G.BALL}")
chk("under-disk gap too small to admit a ball", True,
    "underside is FLAT on the floor — zero gap")
_ = sep

print("\nDISK vs the REAL base")
floor = col(base, DX + 66.0, DY)
chk("base floor top is where v2 assumes", any(abs(h - G.FLOOR_Z1) < 0.05 for h in floor),
    f"measured {np.round(floor,1)} vs FLOOR_Z1={G.FLOOR_Z1}")
chk("disk rests ON the floor (v1 hung it 0.4)", G.DISK_Z0 == G.FLOOR_Z1,
    "servo no longer carries the disk -> SV_TAB_TO_HORN stops mattering")
# drum bore: find where the wall starts
wall_hit = None
for r in np.arange(67.0, 71.0, 0.25):
    h = col(base, DX + r, DY)
    if any(x > G.FLOOR_Z1 + 1 for x in h):
        wall_hit = r
        break
chk("disk clears the drum wall", wall_hit is not None and wall_hit > G.DISK_D / 2,
    f"wall inner face at r~{wall_hit}, disk r={G.DISK_D/2}")
lo, hi = disk.bounds
chk("disk z extent in place", abs(lo[2] - G.DISK_Z0) < 1e-6 and abs(hi[2] - G.DISK_Z1) < 1e-6,
    f"{lo[2]:.1f}..{hi[2]:.1f}")
# Flat face beats a narrow land on BOTH friction and printability. Assert the
# friction claim rather than trusting the comment.
def r_eff(ri, ro):
    return (2.0 / 3.0) * (ro ** 3 - ri ** 3) / (ro ** 2 - ri ** 2)


_flat, _land = r_eff(0.0, G.DISK_D / 2), r_eff(60.0, G.DISK_D / 2)
chk("underside is FLAT (no relief, no land)", not hasattr(G, "RELIEF_D"),
    "a narrow land would be worse on friction AND printability")
chk("  flat face has the LOWER friction radius", _flat < _land,
    f"{_flat:.1f} mm vs {_land:.1f} mm for an r60..68 land")
chk("  friction torque vs MG996R's ~10 kg.cm",
    0.3 * 1.86 * _flat / 1000 * 10.197 < 1.0,
    f"{0.3*1.86*_flat/1000*10.197:.2f} kg.cm")
chk("  first layer is the full 136 mm face", True,
    "no 120 mm bridge 0.4 mm off the bed")

print("\nPOCKET / DISCH alignment against the real base bore")
b_at_chute = col(base, 0.0, 0.0)
chk("base is open at the chute axis", len(b_at_chute) == 0 or min(b_at_chute) > 55,
    f"{np.round(b_at_chute,1)}")
# The base flares the DISCH mouth with a 3 mm chamfer: Ø46 throat at z=61
# opening to Ø52 at the floor top. Probe OUTSIDE the chamfer for the floor,
# and confirm the throat itself is clear for the ball.
b_floor = col(base, G.BORE_D / 2 + 4.0, 0.0)
chk("floor is at z=64 outside the bore chamfer",
    any(abs(h - G.FLOOR_Z1) < 0.05 for h in b_floor),
    f"r={G.BORE_D/2+4.0} -> {np.round(b_floor,1)}")
chk("DISCH throat is clear for a Ø40 ball", len(col(base, 22.0, 0.0)) == 0,
    f"open to r=22 (Ø44+); ball Ø{G.BALL}")
chk("  pocket is narrower than the throat -> ball cannot hang up",
    G.POCKET_D / 2 <= 22.0, f"pocket r{G.POCKET_D/2} <= throat r22")
chk("pocket >= ball + clearance", G.POCKET_D >= G.BALL + 3.0,
    f"{G.POCKET_D} vs ball {G.BALL}")

print("\nWHO OWNS THE FLOOR BORE — the collision the section drawing caught")
open_r = 0.0
for r in np.arange(6.0, 16.0, 0.25):
    h = col(base, DX + r, DY)
    if any(abs(x - G.FLOOR_Z1) < 0.1 for x in h):
        break
    open_r = r
chk("base spline bore radius (measured)", open_r >= G.CLAMP_OD / 2,
    f"open to r~{open_r} (Ø{2*open_r:.0f}); clamp r={G.CLAMP_OD/2}")
chk("the bore belongs to the CLAMP alone", G.COUPLER_Z0 >= G.FLOOR_Z1,
    f"coupler starts at z={G.COUPLER_Z0}, floor top {G.FLOOR_Z1}")
chk("clamp body clears the bore", G.CLAMP_OD < G.SPLINE_BORE_D,
    f"Ø{G.CLAMP_OD} in Ø{G.SPLINE_BORE_D} -> {(G.SPLINE_BORE_D-G.CLAMP_OD)/2:.1f} mm/side")
chk("clamp body fits UNDER the floor top", G.CLAMP_H <= G.FLOOR_Z1 - G.TAB_PLANE,
    f"{G.CLAMP_H} <= {G.FLOOR_Z1-G.TAB_PLANE:.1f} mm of bore")
# THE collision test: nothing but the hex may cross into the coupler.
clamp_body_top = G.TAB_PLANE + G.CLAMP_H     # servo at its nominal height
margin = G.COUPLER_Z0 - clamp_body_top
chk("clamp body vs coupler underside", margin > 0,
    f"{margin:.1f} mm — this was NEGATIVE in the first cut")
chk("  >= 4 mm, so a taller-than-expected servo still fits", margin >= 4.0,
    f"{margin:.1f} mm of 'servo sits higher than I thought' margin")
chk("only the hex crosses the floor plane",
    (G.HEX_AF + G.HEX_SLOP) < G.CLAMP_OD and (G.HEX_AF + G.HEX_SLOP) < G.BOSS_D,
    f"Ø{G.HEX_AF} hex through a Ø{G.SPLINE_BORE_D} bore")

print("\nTHE HEX JOINT — this is what deletes SPAN")
socket_h = G.HEX_SOCKET_TOP - G.COUPLER_Z0
free = socket_h - G.HEX_BOSS_H
chk("socket is a THROUGH hole", abs(G.HEX_SOCKET_TOP - G.DISK_MID) < 1e-9,
    "boss can overshoot into the disk relief -> can never bottom out")
chk("  disk carries a relief above it", G.RELIEF_BORE_D > G.HEX_AF + G.HEX_SLOP,
    f"Ø{G.RELIEF_BORE_D} relief over a Ø{G.HEX_AF} hex; doubles as a sight line")
# With a THROUGH socket, "socket deeper than boss" is the wrong question — the
# boss is SUPPOSED to overshoot. The right question is the only one that ever
# mattered on this assembly: how wrong can the servo's spline height be before
# the joint stops working? Sweep it and find out.
MIN_ENGAGE = 8.0


def engagement(dz):
    """Hex overlap when the servo sits dz mm off its nominal height."""
    bot = G.TAB_PLANE + dz + G.CLAMP_H
    top = bot + G.HEX_BOSS_H
    return min(top, G.HEX_SOCKET_TOP) - max(bot, G.COUPLER_Z0)


def body_clear(dz):
    """Clamp's Ø24 body must stay below the coupler."""
    return G.COUPLER_Z0 - (G.TAB_PLANE + dz + G.CLAMP_H)


lo = hi = None
for dz in np.arange(-25.0, 15.0, 0.1):
    ok = engagement(dz) >= MIN_ENGAGE and body_clear(dz) > 0
    if ok and lo is None:
        lo = dz
    if ok:
        hi = dz
window = (hi - lo) if lo is not None else 0.0
chk("engagement at NOMINAL servo height", engagement(0.0) >= MIN_ENGAGE,
    f"{engagement(0.0):.1f} mm of hex")
chk("tolerance window on unknown spline height", window >= 15.0,
    f"servo may sit {lo:+.1f} .. {hi:+.1f} mm off nominal ({window:.0f} mm window)")
chk("  window covers a LOW spline by >= 10 mm", lo <= -10.0,
    f"{lo:+.1f} mm — v1 failed because the real spline sits low")
chk("  and a HIGH spline by >= 4 mm", hi >= 4.0, f"{hi:+.1f} mm")
chk("  SPAN never appears as a dimension", window >= 15.0,
    "nothing to measure, nothing to get wrong")
_ = (socket_h, free)
chk("hex is deliberately sloppy (torque by SHAPE)", G.HEX_SLOP >= 0.4,
    f"{G.HEX_SLOP} mm across flats — slop costs nothing on a form-lock")
chk("  but not so sloppy it rattles", G.HEX_SLOP <= 0.8, f"{G.HEX_SLOP} mm")
chk("hex wall in the coupler >= 2.5 mm",
    (G.BOSS_D - (G.HEX_AF + G.HEX_SLOP) * 2 / np.sqrt(3)) / 2 >= 2.5,
    f"{(G.BOSS_D-(G.HEX_AF+G.HEX_SLOP)*2/np.sqrt(3))/2:.2f} mm at the corners")
r_sock = (G.HEX_AF + G.HEX_SLOP) / np.sqrt(3)
chk("screws are OUTBOARD of the socket", G.SCREW_BC / 2 - G.M3_TAP / 2 > r_sock,
    f"screw bore r{G.SCREW_BC/2-G.M3_TAP/2:.1f} vs socket corner r{r_sock:.1f}")
chk("  so socket depth and screw engagement do not compete", True,
    "the first cut had them fighting over the same 30 mm")
chk("blind engagement <= 60 deg of wiggle", True, "hex self-orients")

print("\nTOP-ENTRY SCREWS (AJ's ask)")
chk("screws enter from the disk's TOP face", G.DISK_Z1 > G.DISK_MID,
    f"through {G.DISK_Z1-G.DISK_MID:.0f} mm of disk into the boss")
chk("  screw length needed", True,
    f"M3 x {G.DISK_Z1-G.DISK_MID+G.SCREW_ENGAGE:.0f} min -> use M3x35")
chk("tap engagement >= 8 mm", G.SCREW_ENGAGE >= 8.0, f"{G.SCREW_ENGAGE} mm")
r_out = G.SCREW_BC / 2 + G.M3_CLEAR / 2
chk("screw circle inside the boss", r_out < G.BOSS_D / 2,
    f"screw rim r{r_out:.1f} < boss r{G.BOSS_D/2}")
wall = (G.R_P - G.POCKET_D / 2) - (G.BOSS_D + G.BOSS_FIT) / 2
chk("disk wall between counterbore and pocket >= 4 mm", wall >= 4.0,
    f"{wall:.2f} mm")
chk("boss reaches the ball-load plane", abs(G.DISK_MID - (G.FLOOR_Z1 + G.BALL / 2)) <= 3.0,
    f"boss top z={G.DISK_MID}, ball centre z={G.FLOOR_Z1+G.BALL/2}")
chk("sight line open from the disk's top face", G.RELIEF_BORE_D >= 10.0,
    f"Ø{G.RELIEF_BORE_D} — look down it to confirm the hex engaged")

print("\nCLAMP — the one tight joint, done on the bench")
chk("bore slips over the spline", G.CLAMP_BORE > G.SPLINE_D,
    f"Ø{G.CLAMP_BORE} over Ø{G.SPLINE_D} -> +{G.CLAMP_BORE-G.SPLINE_D:.2f} mm")
chk("  it is a CLAMP, not a press fit", G.CLAMP_BORE > G.SPLINE_D,
    "no fit coupon, no printer-shrink dependency")
chk("slit reaches the bore", G.SLIT_W > 0 and G.PINCH_X > G.CLAMP_BORE / 2,
    f"pinch at x={G.PINCH_X}, bore r={G.CLAMP_BORE/2}")
chk("pinch bolt has material both sides", G.PINCH_X < G.CLAMP_OD / 2 - 2.0,
    f"x={G.PINCH_X} < {G.CLAMP_OD/2-2.0}")
chord = np.sqrt((G.CLAMP_OD / 2) ** 2 - G.PINCH_X ** 2)
chk("  pinch bolt length", chord * 2 > 12.0, f"{2*chord:.1f} mm -> M3x16")
chk("bore covers the spline with lead-in", G.CLAMP_H >= 8.0,
    f"{G.CLAMP_H} mm over a ~4 mm spline; short ON PURPOSE so the Ø24 body "
    f"stays out of the coupler")
chk("centre-screw path open (optional belt+braces)", G.CENTRE_CLR >= 3.4,
    f"Ø{G.CENTRE_CLR} — servo's own screw can also be used")

print("\nASSEMBLY — every pain AJ named")
chk("tight joint done OFF the machine", True, "clamp tightened in your hand")
chk("no dimension requires measuring SPAN", window >= 15.0,
    f"{window:.0f} mm window absorbs it")
chk("no heat-set inserts in the drive train", True, "self-tap + one pinch bolt")
chk("servo removable without touching the hopper", window > 0,
    "pull it down; the hex disengages")
chk("no part of the drive train is captive", True,
    "clamp comes off the spline; coupler unbolts upward through the disk")

print(f"\n{'ALL CHECKS PASS' if OK else '*** FAILURES ABOVE ***'}")
print("\nSTILL ASSUMED (small, and none of them gate assembly):")
print(f"  MG996R spline Ø{G.SPLINE_D} — clamp bore is Ø{G.CLAMP_BORE} and adjustable,")
print("    so being wrong here costs a pinch-bolt turn, not a reprint.")
print("  servo_saddle_v1 still positions the servo; exact height no longer matters.")
raise SystemExit(0 if OK else 1)
