"""Step A.6: optimise the hybrid temple and export it as GLB for Lens Studio.

Run headless (after 02_build_hybrid_temple.py has written tools/blender/build/hybrid.blend):
  /Applications/Blender.app/Contents/MacOS/Blender -b -P tools/blender/03_optimise_export.py -- \
      tools/blender/build devpost/asset-review Assets/Temple [target_length_m] [target_triangles]

Steps: cull never-visible facade faces (underside, buried backfaces, back face under the
interior walls) -> weighted decimation protecting the colossi and niche figure -> textures
<= 2048 px, metallic map dropped, normal map kept -> rotate so the facade faces glTF +Z,
scale to the target length, origin at the base centre -> export GLB -> re-import to verify.
"""
import bpy, bmesh, sys, os, json, math, time
import numpy as np
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
builddir, outdir, assetdir = [os.path.abspath(a) for a in argv[:3]]
TARGET_LEN = float(argv[3]) if len(argv) > 3 else 0.78
TARGET_TRIS = int(argv[4]) if len(argv) > 4 else 85000
os.makedirs(outdir, exist_ok=True); os.makedirs(assetdir, exist_ok=True)
T0 = time.time()
def log(*a): print("[export %5.1fs]" % (time.time() - T0), *a)

bpy.ops.wm.open_mainfile(filepath=os.path.join(builddir, "hybrid.blend"))
scene = bpy.context.scene
rep = json.load(open(os.path.join(outdir, "hybrid_build_report.json")))
door = rep["doorway"]; wall_x = door["wall_x"]; cy = door["centre_y"]
facade = bpy.data.objects["Facade"]
report = {"target_length_m": TARGET_LEN, "target_triangles": TARGET_TRIS}
for o in list(bpy.data.objects):
    if o.type in ("CAMERA", "LIGHT") or o.name == "BeamPath":
        bpy.data.objects.remove(o)

def tri_count(o): return sum(len(p.vertices) - 2 for p in o.data.polygons)
def all_pts():
    out = []
    for o in bpy.data.objects:
        if o.type != "MESH": continue
        co = np.empty(len(o.data.vertices) * 3, dtype=np.float32); o.data.vertices.foreach_get("co", co)
        mw = np.array(o.matrix_world, dtype=np.float64); out.append(co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3])
    return np.concatenate(out)
P0 = all_pts(); lo0, hi0 = P0.min(0), P0.max(0); floor_z = float(lo0[2])
report["before"] = {o.name: tri_count(o) for o in bpy.data.objects if o.type == "MESH"}
log("loaded", report["before"])

# ---------------------------------------------------------------- renders (Workbench) helper
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"; scene.display.shading.color_type = "TEXTURE"; scene.display.shading.show_cavity = True
scene.render.resolution_x, scene.render.resolution_y = 1200, 900
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "Standard"
if scene.world is None: scene.world = bpy.data.worlds.new("W")
scene.world.color = (0.25, 0.25, 0.27)
def render(name, loc, target, lens=35, ortho=None):
    cd = bpy.data.cameras.new(name); cam = bpy.data.objects.new(name, cd); scene.collection.objects.link(cam)
    cam.location = Vector(loc); cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    if ortho: cd.type = "ORTHO"; cd.ortho_scale = ortho
    else: cd.lens = lens
    cd.clip_end = 100; scene.camera = cam
    path = os.path.join(outdir, name + ".png"); scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam); bpy.data.cameras.remove(cd)
    return path
COL_CAM = ((wall_x - 0.62, cy - 0.22, floor_z + 0.42), (wall_x + 0.05, cy - 0.12, floor_z + 0.24), 55)
before_png = render("colossi_before", *COL_CAM)

# ---------------------------------------------------------------- 1. cull never-visible facade faces
me = facade.data
n = len(me.polygons)
ctr = np.empty(n * 3, dtype=np.float32); me.polygons.foreach_get("center", ctr); ctr = ctr.reshape(-1, 3)
nrm = np.empty(n * 3, dtype=np.float32); me.polygons.foreach_get("normal", nrm); nrm = nrm.reshape(-1, 3)
xb = rep["facade_block_back_x"]
OUT, IN1 = 0.25, 0.18
H = rep.get("wall_heights_above_sill", {}).get("walls", 0.30)   # side wall height above the sill, from 02
sill = floor_z + door["sill_z_above_floor"]
underside = (nrm[:, 2] < -0.5) & (ctr[:, 2] < floor_z + 0.02)
back = (nrm[:, 0] > 0.5) & (ctr[:, 0] > xb - 0.012)
covered = back & (np.abs(ctr[:, 1] - cy) < OUT) & (ctr[:, 2] < sill + H) & ((np.abs(ctr[:, 1] - cy) > IN1) | (ctr[:, 2] < sill))
dg = bpy.context.evaluated_depsgraph_get()
buried = np.zeros(n, bool)
for i in range(n):
    if underside[i] or covered[i]: continue
    d = Vector(nrm[i]); o = Vector(ctr[i]) + d * 0.0015
    hit, loc, hn, fi, obj, mat = scene.ray_cast(dg, o, d)
    if hit and hn.dot(d) > 0.0 and (loc - o).length < 0.6:
        buried[i] = True
kill = underside | covered | buried
report["cull"] = {"underside": int(underside.sum()), "back_face_covered_by_interior": int(covered.sum()), "buried_backface_hits": int(buried.sum()), "total_removed": int(kill.sum())}
bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.where(kill)[0]], context="FACES")
bm.to_mesh(me); bm.free(); me.update()
report["after_cull"] = tri_count(facade)
log("culled", report["cull"], "->", report["after_cull"], "tris")

# ---------------------------------------------------------------- 2. two-pass decimation
# Blender's Decimate never collapses vertices whose (possibly inverted) group weight is 0, and its
# ratio targets the WHOLE mesh's face count. So: pass A collapses only the unprotected region,
# pass B only the protected region (colossi, fallen pieces, niche figure), each to its own budget.
mask_col = lambda c: (c[:, 0] < wall_x - 0.005) & (np.abs(c[:, 1] - cy) < 0.34) & (c[:, 2] < floor_z + 0.52)
mask_niche = lambda c: (np.abs(c[:, 1] - cy) < 0.06) & (c[:, 2] > floor_z + door["top_z_above_floor"]) & (c[:, 2] < floor_z + door["top_z_above_floor"] + 0.24) & (c[:, 0] < wall_x + 0.04)
def set_protect_group(obj):
    co = np.empty(len(obj.data.vertices) * 3, dtype=np.float32); obj.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    m = mask_col(co) | mask_niche(co)
    for g in list(obj.vertex_groups): obj.vertex_groups.remove(g)
    vg = obj.vertex_groups.new(name="Protect"); vg.add([int(i) for i in np.where(m)[0]], 1.0, "REPLACE")
    return int(m.sum())
def region_counts(obj):
    c = np.empty(len(obj.data.polygons) * 3, dtype=np.float32); obj.data.polygons.foreach_get("center", c); c = c.reshape(-1, 3)
    m = mask_col(c) | mask_niche(c); return int(m.sum()), int((~m).sum())
def decimate(obj, ratio, invert):
    set_protect_group(obj)
    mod = obj.modifiers.new("Decimate", "DECIMATE"); mod.decimate_type = "COLLAPSE"; mod.ratio = ratio
    mod.vertex_group = "Protect"; mod.vertex_group_factor = 1.0; mod.invert_vertex_group = invert; mod.use_collapse_triangulate = True
    dg2 = bpy.context.evaluated_depsgraph_get(); ev = obj.evaluated_get(dg2)
    new = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg2)
    obj.modifiers.clear(); old = obj.data; obj.data = new; new.name = "Facade"; bpy.data.meshes.remove(old)
interior_tris = sum(tri_count(o) for o in bpy.data.objects if o.type == "MESH" and o is not facade)
budget = TARGET_TRIS - interior_tris
prot0, rest0 = region_counts(facade)
report["colossi_region_tris_before"] = [prot0, rest0]
prot_target = int(budget * 0.58); rest_target = budget - prot_target
history = []
# pass A: unprotected region (invert=True -> protected weights become 0 and never collapse)
for it in range(3):
    prot, rest = region_counts(facade); total = prot + rest
    if rest <= rest_target * 1.08: break
    decimate(facade, (prot + rest_target) / total, True)
    history.append({"pass": "A", "region": region_counts(facade)})
# pass B: protected region only (invert=False -> unprotected weights are 0 and never collapse)
for it in range(3):
    prot, rest = region_counts(facade); total = prot + rest
    if prot <= prot_target * 1.08: break
    decimate(facade, (rest + prot_target) / total, False)
    history.append({"pass": "B", "region": region_counts(facade)})
got = tri_count(facade); total = got + interior_tris
report["decimate_history"] = history
report["decimate"] = {"facade_tris": got, "interior_tris": interior_tris, "total_tris": total, "targets": {"protected": prot_target, "rest": rest_target}}
report["colossi_region_tris_after"] = list(region_counts(facade))
if not (60000 <= total <= 100000):
    raise SystemExit("Decimation landed outside the budget: %d" % total)
log("decimated", report["decimate"], "protected/rest", report["colossi_region_tris_before"], "->", report["colossi_region_tris_after"])
after_png = render("colossi_after", *COL_CAM)

# side-by-side composite
def load_px(p):
    im = bpy.data.images.load(p); w, h = im.size
    a = np.empty(w * h * 4, dtype=np.float32); im.pixels.foreach_get(a); bpy.data.images.remove(im); return a.reshape(h, w, 4)
A, B = load_px(before_png), load_px(after_png)
C = np.concatenate([A, np.ones((A.shape[0], 8, 4), dtype=np.float32), B], axis=1)
comp = bpy.data.images.new("colossi_before_after", C.shape[1], C.shape[0]); comp.pixels.foreach_set(C.ravel())
comp.filepath_raw = os.path.join(outdir, "colossi_before_after.png"); comp.file_format = "PNG"; comp.save()
os.remove(before_png); os.remove(after_png)

# ---------------------------------------------------------------- 3. textures
mat0 = facade.data.materials[0]
nt = mat0.node_tree; bsdf = nt.nodes["Principled BSDF"]
texdir = os.path.join(builddir, "textures"); os.makedirs(texdir, exist_ok=True)
def resave(img, name, fmt, size, colorspace):
    if max(img.size) > size: img.scale(size, size)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32); img.pixels.foreach_get(px)
    out = bpy.data.images.new(name, w, h); out.pixels.foreach_set(px); out.update()
    path = os.path.join(texdir, name + ("." + fmt.lower() if fmt != "JPEG" else ".jpg"))
    out.file_format = fmt
    out.save(filepath=path, quality=90)
    bpy.data.images.remove(out)
    ld = bpy.data.images.load(path); ld.colorspace_settings.name = colorspace; ld.name = name
    return ld
tex_report = {}
for nd in list(nt.nodes):
    if nd.type != "TEX_IMAGE" or not nd.image: continue
    feeds = [l.to_socket.name + "@" + l.to_node.name for l in nd.outputs[0].links]
    img = nd.image
    if "metallic" in img.name:
        for l in list(nd.outputs[0].links): nt.links.remove(l)
        nt.nodes.remove(nd); tex_report["metallic"] = "dropped"
    elif any("Base Color" in f for f in feeds):
        nd.image = resave(img, "Temple_BaseColor", "JPEG", 2048, "sRGB"); tex_report["base_color"] = list(nd.image.size)
    elif any("Normal" in f for f in feeds):
        nd.image = resave(img, "Temple_Normal", "PNG", 2048, "Non-Color"); tex_report["normal"] = list(nd.image.size)
    elif "roughness" in img.name:
        nd.image = resave(img, "Temple_Roughness", "JPEG", 2048, "Non-Color"); tex_report["roughness"] = list(nd.image.size)
# make sure the metallic input is a plain 0 and nothing else feeds it
for l in list(bsdf.inputs["Metallic"].links): nt.links.remove(l)
bsdf.inputs["Metallic"].default_value = 0.0
for nd in list(nt.nodes):  # remove orphaned separate-colour nodes
    if nd.type == "SEPARATE_COLOR" and not nd.inputs[0].links: nt.nodes.remove(nd)
report["textures"] = tex_report
log("textures", tex_report)

# ---------------------------------------------------------------- 4. orient, scale, origin
P = all_pts(); lo, hi = P.min(0), P.max(0)
length = float(hi[0] - lo[0]); s = TARGET_LEN / length
R = Matrix.Rotation(math.radians(90.0), 4, "Z")          # facade -X  ->  -Y (glTF +Z, toward the viewer)
centre = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]))
M = Matrix.Scale(s, 4) @ R @ Matrix.Translation(-centre)
for o in bpy.data.objects:
    if o.type == "MESH":
        o.data.transform(M @ o.matrix_world); o.matrix_world = Matrix.Identity(4); o.data.update()
P = all_pts(); lo, hi = P.min(0), P.max(0)
report["final_size_m_xyz"] = [round(float(v), 4) for v in (hi - lo)]
report["final_bbox_min"] = [round(float(v), 4) for v in lo]; report["final_bbox_max"] = [round(float(v), 4) for v in hi]
report["scale_factor"] = round(s, 5)
# statue positions in the final frame (metres), for Step B
report["statues_final_m"] = {}
for nme in ("Statue_Ptah", "Statue_AmunRa", "Statue_Ramesses", "Statue_RaHorakhty"):
    o = bpy.data.objects[nme]; c = np.empty(len(o.data.vertices) * 3, dtype=np.float32); o.data.vertices.foreach_get("co", c); c = c.reshape(-1, 3)
    report["statues_final_m"][nme] = [round(float(v), 4) for v in c.mean(0)]
d_final = {"door_centre_xyz": [0.0, round((sill - floor_z) * s, 4), None]}
report["doorway_final_m"] = {"y_sill": round(float((sill - floor_z) * s), 4), "y_top": round(float(door["top_z_above_floor"] * s), 4), "width": round(float(door["width"] * s), 4),
                             "z_facade_wall": round(float(-(wall_x - centre.x) * s), 4)}
log("scaled", report["final_size_m_xyz"], "scale", report["scale_factor"])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(builddir, "optimised.blend"))

# ---------------------------------------------------------------- 5. export GLB
glb = os.path.join(assetdir, "Temple.glb")
bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_image_format="AUTO", export_apply=True,
                          export_texcoords=True, export_normals=True, export_materials="EXPORT",
                          export_cameras=False, export_lights=False, export_yup=True, export_animations=False, export_skins=False)
report["glb"] = {"path": glb, "bytes": os.path.getsize(glb), "mb": round(os.path.getsize(glb) / 1e6, 2)}
log("exported", report["glb"])

# ---------------------------------------------------------------- 6. verify by re-import
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
ver = {}
for o in bpy.data.objects:
    if o.type == "MESH":
        co = np.empty(len(o.data.vertices) * 3, dtype=np.float32); o.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        mw = np.array(o.matrix_world, dtype=np.float64); w = co @ mw[:3, :3].T + mw[:3, 3]
        ver[o.name] = {"tris": tri_count(o), "materials": [m.name for m in o.data.materials if m], "bbox_min": [round(float(v), 3) for v in w.min(0)], "bbox_max": [round(float(v), 3) for v in w.max(0)]}
ver_imgs = {i.name: list(i.size) for i in bpy.data.images}
report["verify_reimport"] = {"objects": ver, "images": ver_imgs, "total_tris": sum(v["tris"] for v in ver.values())}
json.dump(report, open(os.path.join(outdir, "export_report.json"), "w"), indent=1)
print("EXPORT_DONE", json.dumps({k: report[k] for k in ("cull", "decimate", "colossi_region_tris_before", "colossi_region_tris_after", "decimate_history", "textures", "final_size_m_xyz", "glb", "statues_final_m", "doorway_final_m", "verify_reimport")}))
