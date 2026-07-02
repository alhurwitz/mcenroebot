import numpy as np
import trimesh
from shapely.geometry import Polygon
from trimesh.creation import extrude_polygon

ID = 102.0
OD = 108.0
SEG_H = 150.0
r_in = ID / 2
r_out = OD / 2
COLLAR_R = 57.0
RING = 10.0
SPIGOT_H = 10.0
SOCKET_DEPTH = 10.0
FIT = 0.4
HEX_AF = 6.0  # hexagon across-flats (the hole size)
WEB = 2.0  # wall between hexes

# base tube: wall + bottom collar + top spigot
body = trimesh.creation.annulus(r_min=r_in, r_max=r_out, height=SEG_H)
body.apply_translation([0, 0, SEG_H / 2])
collar = trimesh.creation.annulus(r_min=r_out, r_max=COLLAR_R, height=RING)
collar.apply_translation([0, 0, RING / 2])
spigot = trimesh.creation.annulus(r_min=r_in, r_max=r_out, height=SPIGOT_H)
spigot.apply_translation([0, 0, SEG_H + SPIGOT_H / 2])
tube = trimesh.boolean.union([body, collar, spigot])
tube.merge_vertices()

# honeycomb of hex prisms in the mesh band
R = HEX_AF / np.sqrt(3)  # circumradius (pointy-top)
hexpoly = Polygon(
    [(R * np.cos(np.radians(90 + 60 * k)), R * np.sin(np.radians(90 + 60 * k))) for k in range(6)]
)
r_mid = (r_in + r_out) / 2
depth = (r_out - r_in) * 3
d_h = HEX_AF + WEB
d_v = d_h * np.sqrt(3) / 2
circ = 2 * np.pi * r_mid
ncols = int(circ / d_h)
z0, z1 = 14, SEG_H - 3
nrows = int((z1 - z0) / d_v)

cutters = []
for j in range(nrows + 1):
    zc = z0 + j * d_v
    off = d_h / 2 if j % 2 else 0.0
    for i in range(ncols):
        u = off + i * d_h
        th = u / r_mid
        rad = np.array([np.cos(th), np.sin(th), 0])
        tan = np.array([-np.sin(th), np.cos(th), 0])
        ax = np.array([0, 0, 1.0])
        M = np.eye(4)
        M[:3, 0] = tan
        M[:3, 1] = ax
        M[:3, 2] = rad
        M[:3, 3] = (r_mid - depth / 2) * rad + zc * ax
        c = extrude_polygon(hexpoly, depth)
        c.apply_transform(M)
        cutters.append(c)

tube = tube.difference(trimesh.util.concatenate(cutters))

socket = trimesh.creation.cylinder(radius=r_out + FIT, height=SOCKET_DEPTH + 1)
socket.apply_translation([0, 0, (SOCKET_DEPTH - 1) / 2])
tube = tube.difference(socket)
tube.merge_vertices()
trimesh.repair.fix_normals(tube)

tube.export("tube_segment_hex_FINAL.stl")
rt = trimesh.load("tube_segment_hex_FINAL.stl")
rt.merge_vertices()
d = tube.bounds[1] - tube.bounds[0]
print(
    "tube hex volume=",
    rt.is_volume,
    " watertight=",
    rt.is_watertight,
    f" bbox {d[0]:.0f} x {d[1]:.0f} x {d[2]:.0f}",
)
print(f"{len(cutters)} hex holes, {HEX_AF:.0f}mm across-flats, {WEB:.0f}mm webs")
