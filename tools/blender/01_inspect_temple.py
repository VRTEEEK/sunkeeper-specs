"""Step A.1-2: import the Meshy USDZ, measure it, and render review images.

Run headless:
  /Applications/Blender.app/Contents/MacOS/Blender -b -P tools/blender/01_inspect_temple.py -- \
      assets_src/temple/<file>.usdz devpost/asset-review

Never modifies the source USDZ. Writes to <outdir>:
  measurements.json, maps.txt (ASCII height / front-depth / line-of-sight maps),
  heightmap_top_1cm.png, and renders front / top / three-quarter / sanctuary / doorway.

Axes after import (Blender converts the USD Y-up file to Z-up):
  X = length (facade at -X, sanctuary at +X), Y = depth (USD -Z), Z = height.
"""
import bpy, sys, os, json, math
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
usdz = os.path.abspath(argv[0])
outdir = os.path.abspath(argv[1])
os.makedirs(outdir, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.usd_import(filepath=usdz)

report = {"source": usdz, "axes": "X length, Y depth, Z height (Blender Z-up)", "objects": [], "materials": [], "images": []}

# ---------------------------------------------------------------- objects
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
all_pts = []
for o in meshes:
    me = o.data
    me.calc_loop_triangles()
    n = len(me.vertices)
    co = np.empty(n * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    mw = np.array(o.matrix_world, dtype=np.float64)
    pts = co @ mw[:3, :3].T + mw[:3, 3]
    all_pts.append(pts)
    report["objects"].append({
        "name": o.name, "mesh": me.name, "vertices": n, "triangles": len(me.loop_triangles),
        "polygons": len(me.polygons), "materials": [m.name for m in me.materials if m],
        "matrix_world_scale": [round(v, 6) for v in o.matrix_world.to_scale()],
        "bbox_min": [round(float(v), 4) for v in pts.min(0)],
        "bbox_max": [round(float(v), 4) for v in pts.max(0)],
    })
P = np.concatenate(all_pts)
bmin, bmax = P.min(0), P.max(0)
report["bbox_min"] = [round(float(v), 4) for v in bmin]
report["bbox_max"] = [round(float(v), 4) for v in bmax]
report["size_m_xyz"] = [round(float(v), 4) for v in (bmax - bmin)]

# ---------------------------------------------------------------- materials / textures
for m in bpy.data.materials:
    entry = {"name": m.name, "textures": []}
    if m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == "TEX_IMAGE" and nd.image:
                links = [l.to_socket.name + "@" + l.to_node.name for l in nd.outputs[0].links]
                entry["textures"].append({"image": nd.image.name, "feeds": links})
    report["materials"].append(entry)
for img in bpy.data.images:
    report["images"].append({"name": img.name, "size": list(img.size), "filepath": img.filepath,
                             "packed": img.packed_file is not None, "channels": img.channels})

# ---------------------------------------------------------------- ASCII maps
CH = " .:-=+*#%@"
def ascii_map(grid):
    mx = grid[grid >= 0].max() if (grid >= 0).any() else 1.0
    lines = []
    for row in grid:
        lines.append("".join(" " if v < 0 else CH[min(9, int(v / mx * 9 + 0.5))] for v in row))
    return "\n".join(lines)

X, Y, Z = 0, 1, 2
cell = 0.02
maps = []
def idx(axis):
    return ((P[:, axis] - bmin[axis]) / cell).astype(int)
nx, ny, nz = [int(math.ceil((bmax[a] - bmin[a]) / cell)) + 1 for a in (X, Y, Z)]

# height map: rows = Y (depth, from +Y at top to -Y at bottom), cols = X
hmap = np.full((ny, nx), -1.0)
np.maximum.at(hmap, (idx(Y), idx(X)), P[:, Z] - bmin[Z])
maps.append("HEIGHT MAP (top view, max height per 2 cm cell). Rows = Y depth from +%.2f (top) to %.2f (bottom); columns = X from %.2f (left, facade) to %.2f (right, sanctuary). Darker = higher." % (bmax[Y], bmin[Y], bmin[X], bmax[X]))
maps.append(ascii_map(hmap[::-1]))

# front depth map seen from -X: rows = Z height (top first), cols = Y
dmap = np.full((nz, ny), np.inf)
np.minimum.at(dmap, (idx(Z), idx(Y)), P[:, X] - bmin[X])
d = np.where(np.isinf(dmap), -1.0, (bmax[X] - bmin[X]) - dmap)
maps.append("\nFRONT DEPTH MAP (seen from -X looking +X). Rows = Z height from %.2f (top) to %.2f (bottom); columns = Y from %.2f (left) to %.2f (right). Darker = nearer; light = far (an opening)." % (bmax[Z], bmin[Z], bmin[Y], bmax[Y]))
maps.append(ascii_map(d[::-1]))

# line of sight: rays along +X from in front of the facade, grid over (Z height, Y depth)
dg = bpy.context.evaluated_depsgraph_get()
scene = bpy.context.scene
x0 = float(bmin[X]) - 0.05
ys = np.arange(float(bmin[Y]), float(bmax[Y]) + 1e-6, cell)
zs = np.arange(float(bmin[Z]) + 0.01, float(bmin[Z]) + 0.42, cell)
los = np.full((len(zs), len(ys)), -1.0)
for j, z in enumerate(zs):
    for k, y in enumerate(ys):
        hit, loc, nrm, fi, obj, mat = scene.ray_cast(dg, Vector((x0, y, z)), Vector((1, 0, 0)))
        if hit:
            los[j, k] = loc.x - float(bmin[X])
maps.append("\nLINE OF SIGHT along +X from in front of the facade. Rows = Z height from %.2f (top) to %.2f (bottom); columns = Y depth from %.2f (left) to %.2f (right). Char = distance the ray travels before hitting geometry (darker = further); blank = no hit." % (zs[-1], zs[0], ys[0], ys[-1]))
maps.append(ascii_map(los[::-1]))
Lx = float(bmax[X] - bmin[X])
report["los_max_reach_m"] = round(float(los.max()), 3)
b = np.unravel_index(np.argmax(los), los.shape)
report["los_best_ray"] = {"z_above_floor": round(float(zs[b[0]] - bmin[Z]), 3), "y": round(float(ys[b[1]]), 3), "reach": round(float(los[b]), 3)}
deep = los > 0.6 * Lx
cols = np.where(deep.any(0))[0]
report["deep_ray_y_range"] = [round(float(ys[cols.min()]), 3), round(float(ys[cols.max()]), 3)] if len(cols) else None
rows = np.where(deep.any(1))[0]
report["deep_ray_height_range_above_floor"] = [round(float(zs[rows.min()] - bmin[Z]), 3), round(float(zs[rows.max()] - bmin[Z]), 3)] if len(rows) else None
# doorway: rays between 2 and 25 cm above the floor that get past the facade (> 12 cm in)
zsel = (zs - bmin[Z] >= 0.02) & (zs - bmin[Z] <= 0.25)
door = (los > 0.12) & zsel[:, None]
dcols = np.where(door.any(0))[0]
if len(dcols):
    drows = np.where(door.any(1))[0]
    reach = los[door]
    report["doorway"] = {
        "y_range": [round(float(ys[dcols.min()]), 3), round(float(ys[dcols.max()]), 3)],
        "y_centre": round(float((ys[dcols.min()] + ys[dcols.max()]) / 2), 3),
        "height_above_floor_range": [round(float(zs[drows.min()] - bmin[Z]), 3), round(float(zs[drows.max()] - bmin[Z]), 3)],
        "ray_reach_median_m": round(float(np.median(reach)), 3),
        "ray_reach_max_m": round(float(reach.max()), 3),
        "ray_stop_x_median": round(float(bmin[X] + np.median(reach)), 3),
        "ray_stop_x_max": round(float(bmin[X] + reach.max()), 3),
    }
else:
    report["doorway"] = None
# interior footprint: cells more than 20 cm right of the facade top with any geometry
inter = hmap[:, int(0.55 / cell):]
yrows = np.where((inter >= 0).any(1))[0]
report["interior_y_range_rows"] = [round(float(bmin[Y] + yrows.min() * cell), 3), round(float(bmin[Y] + yrows.max() * cell), 3)] if len(yrows) else None
open(os.path.join(outdir, "maps.txt"), "w").write("\n".join(maps))

# heightmap PNG at 1 cm (rows = -Y..+Y so the image reads like the top render)
c1 = 0.01
nx1, ny1 = [int(math.ceil((bmax[a] - bmin[a]) / c1)) + 1 for a in (X, Y)]
h1 = np.zeros((ny1, nx1))
np.maximum.at(h1, (((P[:, Y] - bmin[Y]) / c1).astype(int), ((P[:, X] - bmin[X]) / c1).astype(int)), P[:, Z] - bmin[Z])
h1 /= max(h1.max(), 1e-6)
img = bpy.data.images.new("heightmap", nx1, ny1)
px = np.repeat(h1[:, :, None], 4, axis=2); px[:, :, 3] = 1.0
img.pixels = px.ravel().tolist()
img.filepath_raw = os.path.join(outdir, "heightmap_top_1cm.png"); img.file_format = "PNG"; img.save()

# ---------------------------------------------------------------- renders (Workbench, textured)
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "TEXTURE"
scene.display.shading.show_cavity = True
scene.render.resolution_x, scene.render.resolution_y = 1600, 1200
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("W"); scene.world = world; world.color = (0.25, 0.25, 0.27)

center = Vector(((bmin[0] + bmax[0]) / 2, (bmin[1] + bmax[1]) / 2, (bmin[2] + bmax[2]) / 2))
size = Vector(bmax - bmin)
BMIN, BMAX = Vector(bmin.tolist()), Vector(bmax.tolist())
L = max(size.x, size.y)

def render(name, loc, target, ortho=None, lens=35):
    cam_data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam)
    cam.location = Vector(loc)
    direction = Vector(target) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    if ortho:
        cam_data.type = "ORTHO"; cam_data.ortho_scale = ortho
    else:
        cam_data.lens = lens
    cam_data.clip_end = 100
    scene.camera = cam
    scene.render.filepath = os.path.join(outdir, name + ".png")
    bpy.ops.render.render(write_still=True)

render("render_front", (BMIN.x - L * 1.0, center.y, center.z + size.z * 0.35), (center.x, center.y, center.z - 0.05))
render("render_top_ortho", (center.x, center.y, BMAX.z + 2), (center.x, center.y, center.z), ortho=L * 1.08)
render("render_three_quarter", (BMIN.x - L * 0.75, BMIN.y - L * 0.75, BMAX.z + L * 0.65), (center.x, center.y, center.z))
render("render_three_quarter_other_side", (BMIN.x - L * 0.75, BMAX.y + L * 0.75, BMAX.z + L * 0.65), (center.x, center.y, center.z))
sx = BMAX.x - 0.2 * size.x
render("render_sanctuary_top", (sx, center.y, BMAX.z + 2), (sx, center.y, center.z), ortho=size.y * 1.1)
render("render_sanctuary_three_quarter", (BMAX.x - 0.55 * size.x, center.y - size.y * 0.7, BMAX.z + 0.45), (BMAX.x - 0.12 * size.x, center.y, BMIN.z + 0.08), lens=50)
render("render_doorway_low_front", (BMIN.x - 0.8, center.y, BMIN.z + 0.12), (BMIN.x + 0.4, center.y, BMIN.z + 0.10), lens=40)

# close-ups for the counts the brief requires
render("render_hall1_from_side", (center.x - 0.35 * size.x, BMIN.y - 0.55, BMAX.z + 0.25), (center.x - 0.2 * size.x, center.y - 0.25, BMIN.z + 0.08), lens=40)
render("render_hall2_top", (BMIN.x + 0.62 * size.x, center.y - 0.22, BMAX.z + 2), (BMIN.x + 0.62 * size.x, center.y - 0.22, center.z), ortho=0.5)
render("render_sanctuary_along_axis", (BMIN.x + 0.72 * size.x, center.y - 0.25, BMIN.z + 0.14), (BMAX.x, center.y - 0.25, BMIN.z + 0.10), lens=28)
json.dump(report, open(os.path.join(outdir, "measurements.json"), "w"), indent=1)
print("INSPECT_DONE", json.dumps({k: report[k] for k in ("bbox_min", "bbox_max", "size_m_xyz", "los_max_reach_m", "los_best_ray", "deep_ray_y_range", "deep_ray_height_range_above_floor", "doorway", "interior_y_range_rows")}))
