"""Step A.3-5: hybrid temple. Keep the Meshy facade block, delete its interior block,
bore the doorway passage, build a new interior on the doorway axis, verify line of
sight, render review images, and save tools/blender/build/hybrid.blend for step 6.

Run headless:
  /Applications/Blender.app/Contents/MacOS/Blender -b -P tools/blender/02_build_hybrid_temple.py -- \
      assets_src/temple/<file>.usdz devpost/asset-review tools/blender/build

Never modifies the source USDZ.
Axes after import (Blender Z-up): X = length (facade at -X, axis runs +X), Y = depth, Z = height.
Seen from the entrance looking +X, the viewer's LEFT is +Y and RIGHT is -Y.
"""
import bpy, bmesh, sys, os, json, math, time
import numpy as np
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
usdz, outdir, builddir = [os.path.abspath(a) for a in argv[:3]]
os.makedirs(outdir, exist_ok=True); os.makedirs(builddir, exist_ok=True)
T0 = time.time()
def log(*a): print("[build %5.1fs]" % (time.time() - T0), *a)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.usd_import(filepath=usdz)
scene = bpy.context.scene
facade = [o for o in bpy.data.objects if o.type == "MESH"][0]
facade.name = "Facade"; facade.data.name = "Facade"
# bake the importer's Y-up -> Z-up object rotation into the mesh so local == world
facade.data.transform(facade.matrix_world); facade.matrix_world = Matrix.Identity(4); facade.data.update()
report = {}

def verts_world(obj):
    me = obj.data
    co = np.empty(len(me.vertices) * 3, dtype=np.float32); me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3); mw = np.array(obj.matrix_world, dtype=np.float64)
    return co @ mw[:3, :3].T + mw[:3, 3]

P = verts_world(facade)
bmin, bmax = P.min(0), P.max(0)
floor_z = float(bmin[2])
# facade block back face: max x among vertices well outside the old interior's Y band
xb = float(P[P[:, 1] > 0.12, 0].max())
report["facade_block_back_x"] = round(xb, 4)
log("bbox", bmin.round(3), bmax.round(3), "facade back x", round(xb, 3))

# ---------------------------------------------------------------- 1. doorway scan (before any edit)
dg = bpy.context.evaluated_depsgraph_get()
def scan_door(step=0.004):
    ys = np.arange(-0.14, 0.14 + 1e-9, step); zs = np.arange(floor_z + 0.002, floor_z + 0.26, step)
    stop = np.full((len(zs), len(ys)), np.nan)
    for j, z in enumerate(zs):
        for k, y in enumerate(ys):
            hit, loc, *_ = scene.ray_cast(dg, Vector((float(bmin[0]) - 0.05, y, z)), Vector((1, 0, 0)))
            if hit: stop[j, k] = loc.x
    return ys, zs, stop
ys, zs, stop = scan_door()
valid = stop[~np.isnan(stop)]
# the facade wall plane = most common stop x (1 cm bins) among rays that get past the colossi row
hist, edges = np.histogram(valid[valid > bmin[0] + 0.15], bins=np.arange(bmin[0], xb + 0.02, 0.01))
wall_x = float(edges[np.argmax(hist)])
door = stop > wall_x + 0.03
dj, dk = np.where(door)
door_y0, door_y1 = float(ys[dk.min()]), float(ys[dk.max()])
door_z0 = float(zs[dj.min()])
door_cy = (door_y0 + door_y1) / 2
kc = int(np.argmin(np.abs(ys - door_cy)))
jtop = dj.min()
while jtop + 1 < len(zs) and door[jtop + 1, kc]:
    jtop += 1
door_z1 = float(zs[jtop])
door_back_x = float(np.nanmax(stop[door]))
report["doorway"] = {"wall_x": round(wall_x, 3), "y_range": [round(door_y0, 3), round(door_y1, 3)],
                     "centre_y": round(door_cy, 3), "sill_z_above_floor": round(door_z0 - floor_z, 3),
                     "top_z_above_floor": round(door_z1 - floor_z, 3), "width": round(door_y1 - door_y0, 3),
                     "height": round(door_z1 - door_z0, 3), "recess_back_x": round(door_back_x, 3)}
log("doorway", report["doorway"])

# ---------------------------------------------------------------- 2. sample facade base colour texture
mat0 = facade.data.materials[0]
base_img = None
for nd in mat0.node_tree.nodes:
    if nd.type == "TEX_IMAGE" and nd.image and any(l.to_socket.name == "Base Color" for l in nd.outputs[0].links):
        base_img = nd.image
small = base_img.copy(); small.scale(256, 256)
px = np.empty(256 * 256 * 4, dtype=np.float32); small.pixels.foreach_get(px)
px = px.reshape(-1, 4)[:, :3]
mean_rgb = px.mean(0); std_rgb = px.std(0)
lum = float(0.2126 * mean_rgb[0] + 0.7152 * mean_rgb[1] + 0.0722 * mean_rgb[2])
report["facade_texture"] = {"mean_rgb": [round(float(v), 3) for v in mean_rgb], "std_rgb": [round(float(v), 3) for v in std_rgb], "mean_luminance": round(lum, 3)}
bpy.data.images.remove(small)
for nd in mat0.node_tree.nodes:  # metallic map statistics for step 6
    if nd.type == "TEX_IMAGE" and nd.image and "metallic" in nd.image.name:
        m = nd.image.copy(); m.scale(128, 128)
        mp = np.empty(128 * 128 * 4, dtype=np.float32); m.pixels.foreach_get(mp)
        report["metallic_map"] = {"mean": round(float(mp.reshape(-1, 4)[:, 0].mean()), 3), "std": round(float(mp.reshape(-1, 4)[:, 0].std()), 3)}
        bpy.data.images.remove(m)
log("facade texture", report["facade_texture"], report.get("metallic_map"))

# interior sandstone texture: facade mean colour + fractal noise, saved as PNG
rng = np.random.default_rng(7)
N = 512
noise = np.zeros((N, N))
for s, w in ((8, 1.0), (16, 0.6), (32, 0.4), (64, 0.25), (128, 0.15)):
    r = rng.random((s, s)); r = np.repeat(np.repeat(r, N // s, 0), N // s, 1)
    k = max(1, N // s // 2)
    c = np.cumsum(np.cumsum(np.pad(r, k, mode="wrap"), 0), 1)
    blur = (c[2 * k:, 2 * k:] - c[:-2 * k, 2 * k:] - c[2 * k:, :-2 * k] + c[:-2 * k, :-2 * k]) / (2 * k) ** 2
    noise += w * (blur[:N, :N] - 0.5)
noise /= np.abs(noise).max()
var = float(min(0.14, max(0.06, std_rgb.mean() / max(mean_rgb.mean(), 1e-3))))
tex = np.clip(mean_rgb[None, None, :] * (1 + var * noise[:, :, None]), 0, 1)
tex_img = bpy.data.images.new("InteriorSandstone", N, N)
tex_px = np.concatenate([tex, np.ones((N, N, 1))], 2).astype(np.float32)
tex_img.pixels.foreach_set(tex_px.ravel())
tex_path = os.path.join(builddir, "InteriorSandstone.png")
tex_img.filepath_raw = tex_path; tex_img.file_format = "PNG"; tex_img.save()
tex_img = bpy.data.images.load(tex_path); tex_img.name = "InteriorSandstone"
report["interior_texture"] = {"path": tex_path, "variation": round(var, 3)}

def make_material(name, image):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.9; bsdf.inputs["Metallic"].default_value = 0.0
    ti = nt.nodes.new("ShaderNodeTexImage"); ti.image = image; ti.location = (-400, 300)
    nt.links.new(ti.outputs["Color"], bsdf.inputs["Base Color"])
    m.diffuse_color = (float(mean_rgb[0]), float(mean_rgb[1]), float(mean_rgb[2]), 1.0)
    return m
mat_interior = make_material("InteriorSandstone", tex_img)
statue_mats = {n: make_material(n, tex_img) for n in ("Statue_Ptah", "Statue_AmunRa", "Statue_Ramesses", "Statue_RaHorakhty")}

# ---------------------------------------------------------------- 3. cut the Meshy interior off, bore the passage
me = facade.data
x_cut = xb + 0.003
co = np.empty(len(me.vertices) * 3, dtype=np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
beyond = co[:, 0] > x_cut
lv = np.empty(len(me.loops), dtype=np.int32); me.loops.foreach_get("vertex_index", lv)
ltot = np.empty(len(me.polygons), dtype=np.int32); me.polygons.foreach_get("loop_total", ltot)
pol = np.repeat(np.arange(len(me.polygons)), ltot)
any_b = np.zeros(len(me.polygons), bool); all_b = np.ones(len(me.polygons), bool)
np.logical_or.at(any_b, pol, beyond[lv]); np.logical_and.at(all_b, pol, beyond[lv])
straddle = int((any_b & ~all_b).sum())
report["faces_straddling_cut_plane"] = straddle
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
if straddle:
    res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                                 plane_co=(x_cut, 0, 0), plane_no=(1, 0, 0), clear_outer=True, clear_inner=False)
    cut_edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    fill = bmesh.ops.holes_fill(bm, edges=cut_edges, sides=0)
else:
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in np.where(beyond)[0]], context="VERTS")
    fill = {"faces": []}
me.materials.append(mat_interior)
inner_slot = len(me.materials) - 1
for f in fill["faces"]:
    f.material_index = inner_slot
bm.to_mesh(me); bm.free(); me.update()
report["facade_after_cut"] = {"vertices": len(me.vertices), "triangles": sum(len(p.vertices) - 2 for p in me.polygons), "fill_faces": len(fill["faces"])}
log("cut interior off", report["facade_after_cut"])

# passage: delete every face whose centre lies inside the passage volume, then line the tunnel
pw = max(door_y1 - door_y0, 0.06) / 2
pz0, pz1 = door_z0, max(door_z1, door_z0 + 0.10)
bx0, bx1 = door_back_x - 0.025, x_cut + 0.01
by0, by1 = door_cy - pw, door_cy + pw
ctr = np.empty(len(me.polygons) * 3, dtype=np.float32); me.polygons.foreach_get("center", ctr); ctr = ctr.reshape(-1, 3)
inside = (ctr[:, 0] > bx0) & (ctr[:, 0] < bx1) & (ctr[:, 1] > by0 + 0.0005) & (ctr[:, 1] < by1 - 0.0005) & (ctr[:, 2] > pz0 - 0.0025) & (ctr[:, 2] < pz1 - 0.0005)
bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.where(inside)[0]], context="FACES")
lx0, lx1 = bx0 + 0.005, x_cut
v = {}
for xi, xv in ((0, lx0), (1, lx1)):
    for yi, yv in ((0, by0), (1, by1)):
        for zi, zv in ((0, pz0 - 0.002), (1, pz1)):
            v[(xi, yi, zi)] = bm.verts.new((xv, yv, zv))
liner = [
    bm.faces.new((v[0, 0, 0], v[1, 0, 0], v[1, 1, 0], v[0, 1, 0])),   # floor, normal +Z
    bm.faces.new((v[0, 1, 1], v[1, 1, 1], v[1, 0, 1], v[0, 0, 1])),   # ceiling, normal -Z
    bm.faces.new((v[0, 0, 0], v[0, 0, 1], v[1, 0, 1], v[1, 0, 0])),   # side at y0, normal +Y
    bm.faces.new((v[0, 1, 0], v[1, 1, 0], v[1, 1, 1], v[0, 1, 1])),   # side at y1, normal -Y
]
for f in liner: f.material_index = inner_slot
bm.to_mesh(me); bm.free(); me.update()
report["passage_faces_removed"] = int(inside.sum())
report["facade_after_passage"] = {"vertices": len(me.vertices), "triangles": sum(len(p.vertices) - 2 for p in me.polygons)}
log("passage bored", report["facade_after_passage"])
# new passage faces have no UVs: give the whole interior-slot + passage region box-projected UVs below

# ---------------------------------------------------------------- 4. build the new interior
sill = door_z0
H = 0.30                       # half-height walls above the sill
DEPTH = 1.40                   # 2.27 x facade height (0.617)
x0 = x_cut                     # interior starts at the facade block's back
cy = door_cy                   # the axis
OUT = 0.25; WALL = 0.07
IN1 = OUT - WALL               # great hall half width 0.18
IN2 = 0.13                     # rear section half width
boxes = {}                     # object name -> list of (x0,x1,y0,y1,z0,z1)
def B(obj, x0_, x1_, y0_, y1_, z0_, z1_): boxes.setdefault(obj, []).append((x0_, x1_, cy + y0_, cy + y1_, z0_, z1_))

xe = x0 + DEPTH
B("Interior_Shell", x0, xe, -OUT, OUT, floor_z, sill)                        # floor slab
B("Interior_Shell", x0, xe, IN1, OUT, sill, sill + H)                         # side wall +Y (viewer's left)
B("Interior_Shell", x0, xe, -OUT, -IN1, sill, sill + H)                       # side wall -Y
B("Interior_Shell", xe - 0.06, xe, -OUT, OUT, sill, sill + H)                 # back wall
# great hall x0+0.02 .. x0+0.62
xh1a, xh1b = x0, x0 + 0.62
for sgn in (1, -1):
    for i in range(4):
        px_ = x0 + 0.14 + i * 0.13
        y = sgn * 0.095
        B("Interior_Pillars", px_ - 0.03, px_ + 0.03, y - 0.03, y + 0.03, sill, sill + H - 0.02)        # pillar
        yf = y - sgn * 0.03                                                                              # face toward the axis
        B("Interior_Pillars", px_ - 0.018, px_ + 0.018, yf - sgn * 0.012, yf, sill + 0.03, sill + 0.19)    # figure body
        B("Interior_Pillars", px_ - 0.013, px_ + 0.013, yf - sgn * 0.014, yf, sill + 0.19, sill + 0.22)    # head
        B("Interior_Pillars", px_ - 0.008, px_ + 0.008, yf - sgn * 0.012, yf, sill + 0.22, sill + 0.255)   # crown
def partition(x0_, x1_, half_in, door_w, door_h):
    B("Interior_Shell", x0_, x1_, door_w / 2, half_in, sill, sill + H)
    B("Interior_Shell", x0_, x1_, -half_in, -door_w / 2, sill, sill + H)
    B("Interior_Shell", x0_, x1_, -door_w / 2, door_w / 2, sill + door_h, sill + H)
partition(x0 + 0.62, x0 + 0.66, IN1, 0.10, 0.16)
# rear section narrows: fill blocks from IN2 to IN1 on both sides, x0+0.66 .. xe
B("Interior_Shell", x0 + 0.66, xe, IN2, IN1, sill, sill + H)
B("Interior_Shell", x0 + 0.66, xe, -IN1, -IN2, sill, sill + H)
# second hall x0+0.66 .. x0+0.98, four square pillars
for sgn in (1, -1):
    for px_ in (x0 + 0.76, x0 + 0.88):
        B("Interior_Pillars", px_ - 0.022, px_ + 0.022, sgn * 0.085 - 0.022, sgn * 0.085 + 0.022, sill, sill + H - 0.02)
partition(x0 + 0.98, x0 + 1.02, IN2, 0.13, 0.15)
# vestibule x0+1.02 .. x0+1.16
partition(x0 + 1.16, x0 + 1.19, IN2, 0.14, 0.14)
# sanctuary x0+1.19 .. xe-0.06 ; statues against the back wall
STATUE_X = xe - 0.06 - 0.035
order = ["Statue_Ptah", "Statue_AmunRa", "Statue_Ramesses", "Statue_RaHorakhty"]   # left -> right from the entrance = +Y -> -Y
statue_y = {n: 0.0675 - i * 0.045 for i, n in enumerate(order)}
for n in order:
    y = statue_y[n]; sx = STATUE_X
    B(n, sx - 0.0175, sx + 0.0175, y - 0.02, y + 0.02, sill, sill + 0.035)                 # seat
    B(n, sx - 0.011, sx + 0.011, y - 0.015, y + 0.015, sill + 0.035, sill + 0.08)           # torso
    B(n, sx - 0.0175, sx - 0.0025, y - 0.013, y + 0.013, sill + 0.035, sill + 0.055)        # lap / knees toward -X
    B(n, sx - 0.01, sx + 0.01, y - 0.01, y + 0.01, sill + 0.08, sill + 0.10)                # head
    B(n, sx - 0.007, sx + 0.007, y - 0.007, y + 0.007, sill + 0.10, sill + 0.12)            # crown

TILES = 3.0  # texture repeats per metre
def box_uv_project(me_, scale=TILES):
    uv = me_.uv_layers.new(name="UVMap") if not me_.uv_layers else me_.uv_layers[0]
    n = len(me_.polygons)
    normals = np.empty(n * 3, dtype=np.float32); me_.polygons.foreach_get("normal", normals); normals = normals.reshape(-1, 3)
    co = np.empty(len(me_.vertices) * 3, dtype=np.float32); me_.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    lv = np.empty(len(me_.loops), dtype=np.int32); me_.loops.foreach_get("vertex_index", lv)
    lstart = np.empty(n, dtype=np.int32); me_.polygons.foreach_get("loop_start", lstart)
    ltot = np.empty(n, dtype=np.int32); me_.polygons.foreach_get("loop_total", ltot)
    poly_of_loop = np.repeat(np.arange(n), ltot)
    axis = np.argmax(np.abs(normals), 1)[poly_of_loop]
    c = co[lv]
    u = np.where(axis == 0, c[:, 1], c[:, 0]); v = np.where(axis == 2, c[:, 1], c[:, 2])
    flat = np.stack([u, v], 1).astype(np.float32).ravel() * scale
    try:
        uv.uv.foreach_set("vector", flat)
    except Exception:
        uv.data.foreach_set("uv", flat)

def build(name, blist, mat):
    verts, faces = [], []
    for (ax0, ax1, ay0, ay1, az0, az1) in blist:
        b = len(verts)
        verts += [(ax0, ay0, az0), (ax1, ay0, az0), (ax1, ay1, az0), (ax0, ay1, az0), (ax0, ay0, az1), (ax1, ay0, az1), (ax1, ay1, az1), (ax0, ay1, az1)]
        faces += [tuple(b + i for i in f) for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))]
    m = bpy.data.meshes.new(name); m.from_pydata(verts, [], faces); m.update()
    m.materials.append(mat); box_uv_project(m)
    o = bpy.data.objects.new(name, m); scene.collection.objects.link(o); return o
objs = {}
for name, blist in boxes.items():
    objs[name] = build(name, blist, statue_mats.get(name, mat_interior))
# UVs for the facade's new (fill + passage) faces: box-project only loops of faces in the interior slot or with zero UVs
fme = facade.data
if fme.uv_layers:
    uvl = fme.uv_layers[0]
    nloops = len(fme.loops)
    old_uv = np.empty(nloops * 2, dtype=np.float32)
    try: uvl.uv.foreach_get("vector", old_uv)
    except Exception: uvl.data.foreach_get("uv", old_uv)
    old_uv = old_uv.reshape(-1, 2)
    mi = np.empty(len(fme.polygons), dtype=np.int32); fme.polygons.foreach_get("material_index", mi)
    ltot = np.empty(len(fme.polygons), dtype=np.int32); fme.polygons.foreach_get("loop_total", ltot)
    poly_of_loop = np.repeat(np.arange(len(fme.polygons)), ltot)
    zero = (np.abs(old_uv).sum(1) < 1e-6)
    sel_poly = np.zeros(len(fme.polygons), bool)
    np.logical_or.at(sel_poly, poly_of_loop, zero)
    sel_poly |= (mi == inner_slot)
    mi[sel_poly] = inner_slot; fme.polygons.foreach_set("material_index", mi)
    tmp = fme.copy(); box_uv_project(tmp)
    new_uv = np.empty(nloops * 2, dtype=np.float32)
    try: tmp.uv_layers[0].uv.foreach_get("vector", new_uv)
    except Exception: tmp.uv_layers[0].data.foreach_get("uv", new_uv)
    new_uv = new_uv.reshape(-1, 2)
    sel_loop = sel_poly[poly_of_loop]
    old_uv[sel_loop] = new_uv[sel_loop]
    try: uvl.uv.foreach_set("vector", old_uv.ravel())
    except Exception: uvl.data.foreach_set("uv", old_uv.ravel())
    bpy.data.meshes.remove(tmp)
    report["facade_faces_reassigned_to_interior_material"] = int(sel_poly.sum())
fme.update()
log("interior built:", {k: len(v) for k, v in boxes.items()})

# ---------------------------------------------------------------- 5. line of sight
dg = bpy.context.evaluated_depsgraph_get()
origin = Vector((wall_x - 0.03, cy, sill + min(0.05, (pz1 - sill) * 0.5)))
los = {}
for n in order:
    target = Vector((STATUE_X, cy + statue_y[n], sill + 0.06))
    d = (target - origin); dist = d.length; d.normalize()
    hit, loc, nrm, fi, obj, mat = scene.ray_cast(dg, origin, d)
    los[n] = {"hit": obj.name if hit else None, "clear": bool(hit and obj.name == n), "distance_to_hit": round(float((loc - origin).length), 3) if hit else None, "distance_to_statue": round(float(dist), 3)}
hit, loc, *_ = scene.ray_cast(dg, origin, Vector((1, 0, 0)))
los["axis_ray"] = {"hit": (_[2].name if hit else None), "stop_x": round(float(loc.x), 3) if hit else None, "back_wall_x": round(float(xe - 0.06), 3)}
report["line_of_sight"] = los
report["line_of_sight_origin"] = [round(float(v), 3) for v in origin]
log("line of sight", json.dumps(los))

# ---------------------------------------------------------------- 6. save blend, render
report["totals"] = {o.name: {"triangles": sum(len(p.vertices) - 2 for p in o.data.polygons)} for o in bpy.data.objects if o.type == "MESH"}
report["model_size_m"] = None
allP = np.concatenate([verts_world(o) for o in bpy.data.objects if o.type == "MESH"])
report["model_bbox_min"] = [round(float(v), 4) for v in allP.min(0)]; report["model_bbox_max"] = [round(float(v), 4) for v in allP.max(0)]
report["model_size_m"] = [round(float(v), 4) for v in (allP.max(0) - allP.min(0))]
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(builddir, "hybrid.blend"))

# beam path marker (render only)
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.012, radius2=0.012, depth=(STATUE_X - 0.03) - (wall_x - 0.1))
beam_me = bpy.data.meshes.new("BeamPath"); bm.to_mesh(beam_me); bm.free()
beam = bpy.data.objects.new("BeamPath", beam_me); scene.collection.objects.link(beam)
beam.rotation_euler = (0, math.pi / 2, 0)
beam.location = ((wall_x - 0.1 + STATUE_X - 0.03) / 2, cy, sill + 0.05)
beam_mat = bpy.data.materials.new("BeamPath"); beam_mat.diffuse_color = (1.0, 0.85, 0.2, 1.0); beam_me.materials.append(beam_mat)
beam.hide_render = True

scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"; scene.display.shading.color_type = "TEXTURE"; scene.display.shading.show_cavity = True
scene.render.resolution_x, scene.render.resolution_y = 1600, 1200
scene.render.image_settings.file_format = "JPEG"; scene.render.image_settings.quality = 88
scene.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("W"); scene.world = world; world.color = (0.25, 0.25, 0.27)
lo, hi = allP.min(0), allP.max(0); C = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2)); S = Vector(hi - lo); L = max(S.x, S.y)
def render(name, loc, target, ortho=None, lens=35):
    cd = bpy.data.cameras.new(name); cam = bpy.data.objects.new(name, cd); scene.collection.objects.link(cam)
    cam.location = Vector(loc); cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    if ortho: cd.type = "ORTHO"; cd.ortho_scale = ortho
    else: cd.lens = lens
    cd.clip_end = 100; scene.camera = cam; scene.render.filepath = os.path.join(outdir, name + ".jpg")
    bpy.ops.render.render(write_still=True)
render("hybrid_front", (lo[0] - L * 0.9, C.y, C.z + S.z * 0.45), (C.x, C.y, C.z - 0.05))
render("hybrid_top", (C.x, C.y, hi[2] + 2), (C.x, C.y, C.z), ortho=L * 1.06)
render("hybrid_three_quarter", (lo[0] - L * 0.7, lo[1] - L * 0.7, hi[2] + L * 0.6), (C.x, C.y, C.z))
render("hybrid_three_quarter_other_side", (lo[0] - L * 0.7, hi[1] + L * 0.7, hi[2] + L * 0.6), (C.x, C.y, C.z))
render("hybrid_interior_closeup", (x0 + 0.25, cy - 0.70, sill + 0.80), (x0 + 0.75, cy, sill + 0.05), lens=40)
render("hybrid_sanctuary_closeup", (x0 + 1.06, cy - 0.12, sill + 0.40), (STATUE_X, cy, sill + 0.05), lens=40)
beam.hide_render = False
render("hybrid_top_beam_path", (C.x, C.y, hi[2] + 2), (C.x, C.y, C.z), ortho=L * 1.06)
render("hybrid_beam_three_quarter", (lo[0] - L * 0.5, lo[1] - L * 0.6, hi[2] + L * 0.5), (C.x + 0.1, C.y, C.z))

json.dump(report, open(os.path.join(outdir, "hybrid_build_report.json"), "w"), indent=1)
print("BUILD_DONE", json.dumps({k: report[k] for k in ("doorway", "facade_texture", "metallic_map", "facade_after_cut", "facade_after_passage", "line_of_sight", "totals", "model_size_m") if k in report}))
