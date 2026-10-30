"""Sanctuary statues for the hybrid temple (imported by 02_build_hybrid_temple.py).

The four rock-cut figures at the back of the Great Temple's sanctuary, left to right as seen
from the entrance: Ptah, Amun-Ra, the deified Ramesses II, Ra-Horakhty. References used for the
iconography (checked 30 Oct 2026, photographs of the sanctuary on Wikimedia Commons:
"Abu Simbel temple, four statues of divinities in sanctuary.jpg" and "Abu Simbel - Allerheiligstes.jpg"):

  Ptah         mummiform (wrapped body, no separate limbs), close-fitting skullcap, straight beard,
               fists together at the chest holding the was-djed sceptre
  Amun-Ra      flat-topped crown (modius) with two tall straight plumes, tripartite wig, divine beard
  Ramesses II  the khepresh ("blue crown"): a rounded helmet crown swelling up and back, with a uraeus
  Ra-Horakhty  falcon head, tripartite wig, large sun disc with a uraeus

All except Ptah sit upright on a throne block, hands flat on the knees, feet together, kilt.

Method (no AI generation): each figure is assembled from primitives in a local frame (lx toward
the entrance, ly to the figure's left... mirrored to world by a 180 degree turn, lz up from the sill),
fused with a voxel remesh and smoothed (the high-poly). Carved detail (kilt pleats, wig striations,
beard ridges, plume bands, crown studs and edges, collar rings, mummy wrappings, throne panels,
stone grain) is displaced into the high-poly. A decimated copy (3-5k triangles) is the exported
mesh; a shared 1024 px atlas gets a baked tangent-space normal map from the high-poly and a base
colour baked from the interior sandstone texture (box-projected, the same tiling as the walls)
with a little ambient occlusion so the carving reads. Each statue keeps its own material.
"""
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector, Matrix

ORDER = ["Statue_Ptah", "Statue_AmunRa", "Statue_Ramesses", "Statue_RaHorakhty"]
VOXEL = 0.0002          # high-poly remesh voxel (model metres; ~0.08 mm in the Lens)
LOW_TRIS = 4200         # target triangles per exported statue
ATLAS = 1024
TILES = 3.0             # sandstone repeats per metre, as the interior walls


# ------------------------------------------------------------------ primitive helpers (local frame)
def _ellipsoid(bm, c, r, rot=None, seg=24):
    g = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    M = Matrix.Translation(Vector(c)) @ (rot.to_4x4() if rot else Matrix.Identity(4)) @ Matrix.Diagonal((r[0], r[1], r[2], 1))
    bmesh.ops.transform(bm, matrix=M, verts=g["verts"])


def _capsule(bm, a, b, r1, r2=None, seg=16):
    """Tapered cylinder from a to b with spheres on both ends."""
    r2 = r1 if r2 is None else r2
    a, b = Vector(a), Vector(b)
    d = b - a
    g = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r1, radius2=r2, depth=d.length)
    rot = d.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation((a + b) / 2) @ rot, verts=g["verts"])
    _ellipsoid(bm, a, (r1, r1, r1), seg=seg)
    _ellipsoid(bm, b, (r2, r2, r2), seg=seg)


def _box(bm, lo, hi):
    lo, hi = Vector(lo), Vector(hi)
    g = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.transform(bm, matrix=Matrix.Translation((lo + hi) / 2) @ Matrix.Diagonal((*(hi - lo), 1)), verts=g["verts"])


def _cyl(bm, c, r, h, axis="Z", seg=32):
    g = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=h)
    R = {"Z": Matrix.Identity(4), "X": Matrix.Rotation(math.pi / 2, 4, "Y"), "Y": Matrix.Rotation(math.pi / 2, 4, "X")}[axis]
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(c)) @ R, verts=g["verts"])


# ------------------------------------------------------------------ figure assembly
# Local frame: lx forward (toward the entrance), ly lateral, lz up from the sill. Footprint stays
# inside lx [-0.0175, 0.0175], ly [-0.019, 0.019] (the old block statues), so the halos and pools
# that the Lens places from each statue's bounds keep their positions.
#
# Organic parts (body, limbs, head, wig) are metaball elements so the joints blend like carved
# stone; crisp parts (throne, crowns, plumes, disc, sceptre) are plain meshes. Both are fused by
# the voxel remesh. Metaballs are built 100x larger (their resolution has a floor) and scaled back.
MB_SCALE = 100.0
MB_K = 0.574            # surface radius / element radius at threshold 0.6, stiffness 2 (measured)


def _organic_seated():
    o = [("ell", (-0.0072, 0.0, 0.0640), (0.0048, 0.0118, 0.0080)),                                 # chest, broad and flat
         ("ell", (-0.0080, 0.0, 0.0505), (0.0036, 0.0086, 0.0125)),                                 # waist, flat in front
         ("cube", (-0.0115, -0.0094, 0.0315), (0.0098, 0.0094, 0.0425), 0.0028),                    # kilt over hips and lap
         ("cap", (-0.0066, 0.0, 0.0725), (-0.0063, 0.0, 0.0782), 0.0032)]                           # neck
    for s in (1, -1):
        o += [("ell", (-0.0036, s * 0.0046, 0.0648), (0.0024, 0.0040, 0.0030)),                     # pectoral
              ("ell", (-0.0072, s * 0.0121, 0.0686), (0.0034, 0.0036, 0.0034)),                     # shoulder
              ("cap", (-0.0072, s * 0.0124, 0.0676), (-0.0068, s * 0.0112, 0.0478), 0.0023),        # upper arm, close to the body
              ("cap", (-0.0066, s * 0.0110, 0.0466), (0.0104, s * 0.0078, 0.0420), 0.0019),         # forearm along the thigh
              ("ell", (0.0131, s * 0.0072, 0.0412), (0.0032, 0.0020, 0.0010)),                      # hand flat on the knee
              ("cap", (-0.0075, s * 0.0046, 0.0365), (0.0118, s * 0.0044, 0.0360), 0.0043),         # thigh
              ("cap", (0.0124, s * 0.0038, 0.0328), (0.0130, s * 0.0029, 0.0058), 0.0025),          # shin
              ("ell", (0.0146, s * 0.0023, 0.0036), (0.0040, 0.0019, 0.0015))]                      # foot, together
    return o


def _organic_mummy():
    o = [("ell", (-0.0075, 0.0, 0.0560), (0.0058, 0.0104, 0.0170)),                                 # wrapped torso
         ("ell", (-0.0068, 0.0, 0.0660), (0.0057, 0.0116, 0.0063)),                                 # shoulders under the shroud
         ("cube", (-0.0115, -0.0090, 0.0310), (0.0130, 0.0090, 0.0420), 0.0028),                    # wrapped lap
         ("cube", (0.0080, -0.0070, 0.0035), (0.0156, 0.0070, 0.0390), 0.0024),                     # shins together
         ("ell", (0.0150, 0.0, 0.0036), (0.0040, 0.0058, 0.0016)),                                  # feet
         ("cap", (-0.0066, 0.0, 0.0725), (-0.0063, 0.0, 0.0782), 0.0032)]                           # neck
    for s in (1, -1):
        o.append(("ell", (0.0010, s * 0.0013, 0.0640), (0.0018, 0.0016, 0.0020)))                  # fists gripping the sceptre
    return o


def _organic_head(beard):
    o = [("ell", (-0.0055, 0.0, 0.0848), (0.0058, 0.0051, 0.0062)),                                 # head
         ("ell", (0.0001, 0.0, 0.0842), (0.0007, 0.0006, 0.0012)),                                  # nose
         ("ell", (-0.0016, 0.0, 0.0800), (0.0020, 0.0028, 0.0014))]                                 # chin and jaw
    for s in (1, -1):
        o.append(("ell", (-0.0060, s * 0.0050, 0.0845), (0.0010, 0.0007, 0.0016)))                 # ear
    if beard:
        o.append(("cap", (-0.0013, 0.0, 0.0788), (-0.0008, 0.0, 0.0728), 0.0010))                  # beard
        o.append(("cap", (-0.0030, 0.0, 0.0784), (-0.0024, 0.0, 0.0734), 0.0010))                  # stone web joining it to the throat
        if beard == "divine":
            o.append(("ell", (-0.0002, 0.0, 0.0725), (0.0009, 0.0010, 0.0008)))                    # curled tip
    return o


def _organic_falcon():
    return [("ell", (-0.0058, 0.0, 0.0850), (0.0056, 0.0047, 0.0062)),                              # head
            ("cap", (-0.0010, 0.0, 0.0868), (0.0024, 0.0, 0.0850), 0.0017),                         # beak
            ("cap", (0.0024, 0.0, 0.0850), (0.0031, 0.0, 0.0826), 0.0008)]                          # hooked tip


def _organic_wig():
    o = [("ell", (-0.0068, 0.0, 0.0836), (0.0064, 0.0062, 0.0086))]                                 # wig round the head
    for s in (1, -1):
        o.append(("cap", (-0.0060, s * 0.0062, 0.0820), (-0.0040, s * 0.0072, 0.0668), 0.0017))    # lappet onto the chest
    return o


def _throne(bm):
    _box(bm, (-0.0175, -0.019, 0.0), (0.0060, 0.019, 0.031))        # seat block
    _box(bm, (-0.0175, -0.0125, 0.030), (-0.0120, 0.0125, 0.071))   # back pillar against the wall
    _box(bm, (0.0055, -0.019, 0.0), (0.0175, 0.019, 0.0022))        # footrest base


def _uraeus(bm, f, z):
    _capsule(bm, (f, 0.0, z), (f + 0.0004, 0.0, z + 0.0028), 0.0007, 0.0006)


def figure(name):
    """Returns (metaball element specs, bmesh of the crisp parts) in the local frame."""
    bm = bmesh.new()
    _throne(bm)
    if name == "Statue_Ptah":
        org = _organic_mummy() + _organic_head("straight")
        _ellipsoid(bm, (-0.0057, 0.0, 0.0866), (0.0062, 0.0054, 0.0056))                            # close-fitting skullcap
        _cyl(bm, (0.0021, 0.0, 0.0560), 0.0008, 0.0290)                                             # was sceptre shaft
        for i in range(4):
            _cyl(bm, (0.0020, 0.0, 0.0700 + i * 0.0011), 0.0018, 0.0006)                            # djed bands
        _ellipsoid(bm, (0.0020, 0.0, 0.0752), (0.0012, 0.0015, 0.0010))                             # was head
    elif name == "Statue_AmunRa":
        org = _organic_seated() + _organic_head("divine") + _organic_wig()
        _cyl(bm, (-0.0060, 0.0, 0.0915), 0.0046, 0.0036)                                            # flat-topped crown (modius)
        for s in (1, -1):
            _box(bm, (-0.0069, s * 0.00225 - 0.00195, 0.0930), (-0.0051, s * 0.00225 + 0.00195, 0.1380))  # tall plume
            _ellipsoid(bm, (-0.0060, s * 0.00225, 0.1380), (0.0009, 0.00195, 0.0026))                # rounded plume top
    elif name == "Statue_Ramesses":
        org = _organic_seated() + _organic_head("straight")
        _ellipsoid(bm, (-0.0060, 0.0, 0.0880), (0.0064, 0.0056, 0.0058))                            # khepresh: band round the brow
        tilt = Matrix.Rotation(math.radians(-16), 3, "Y")
        _ellipsoid(bm, (-0.0084, 0.0, 0.0930), (0.0080, 0.0074, 0.0072), rot=tilt)                  # swelling up, out and back
        _uraeus(bm, 0.0003, 0.0868)
    elif name == "Statue_RaHorakhty":
        org = _organic_seated() + _organic_falcon() + _organic_wig()
        _cyl(bm, (-0.0090, 0.0, 0.1010), 0.0098, 0.0022, axis="X", seg=48)                          # sun disc, facing the entrance
        _uraeus(bm, -0.0076, 0.0912)
    return org, bm


def _metaball_mesh(scene, name, specs):
    mb = bpy.data.metaballs.new("MB_" + name); mb.resolution = 0.025; mb.render_resolution = 0.025; mb.threshold = 0.6
    ob = bpy.data.objects.new("MB_" + name, mb); scene.collection.objects.link(ob)
    S = MB_SCALE
    for sp in specs:
        e = mb.elements.new(); e.stiffness = 2.0
        if sp[0] == "ell":
            _, c, r = sp; m = min(r)
            e.type = "ELLIPSOID"; e.co = Vector(c) * S; e.radius = m * S / MB_K
            e.size_x, e.size_y, e.size_z = r[0] / m, r[1] / m, r[2] / m
        elif sp[0] == "cap":
            _, a, b, r = sp; a, b = Vector(a), Vector(b)
            e.type = "CAPSULE"; e.co = (a + b) / 2 * S; e.radius = r * S / MB_K
            e.size_x = (b - a).length / 2 * S; e.rotation = (b - a).normalized().to_track_quat("X", "Z")
        elif sp[0] == "cube":
            _, lo, hi, rr = sp; lo, hi = Vector(lo), Vector(hi)
            e.type = "CUBE"; e.co = (lo + hi) / 2 * S; e.radius = rr * S / MB_K
            h = (hi - lo) / 2
            e.size_x, e.size_y, e.size_z = [max(v - rr, 0.0001) * S for v in h]
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    me.transform(Matrix.Scale(1.0 / S, 4))
    bpy.data.objects.remove(ob); bpy.data.metaballs.remove(mb)
    return me


# ------------------------------------------------------------------ carved detail (displacement)
def _detail(name, P, N):
    """Displacement (model metres, along the normal) for local positions P and normals N."""
    f, w, z = P[:, 0], P[:, 1], P[:, 2]
    d = np.zeros(len(P))
    ph = np.array([0.3, 1.7, 2.9, 4.1])
    d += 0.000012 * (np.sin(P @ np.array([2900., 1300., 1700.]) + ph[0]) * np.sin(P @ np.array([-900., 3100., 2300.]) + ph[1])
                     + 0.6 * np.sin(P @ np.array([5200., -4100., 3600.]) + ph[2]))                 # stone grain
    band = lambda x, period: 0.5 + 0.5 * np.cos(2 * np.pi * x / period)
    near = lambda x, c, s: np.exp(-((x - c) / s) ** 2)
    # throne side panels: a sunk border 2 mm inside the block edges
    side = (np.abs(w) > 0.0182) & (z < 0.0305) & (f < 0.0058)
    edge = np.minimum.reduce([np.abs(f + 0.0155), np.abs(f - 0.0040), np.abs(z - 0.0020), np.abs(z - 0.0290)])
    inside = (f > -0.0157) & (f < 0.0042) & (z > 0.0018) & (z < 0.0292)
    d -= side * inside * 0.00016 * np.exp(-(edge / 0.00035) ** 2)
    # broad collar on the chest: concentric rings round the neck
    r = np.hypot(w, z - 0.0765)
    collar = (f > -0.0045) & (z > 0.0615) & (z < 0.0745) & (r > 0.0040) & (r < 0.0105)
    d -= collar * 0.00008 * band(r, 0.0013)
    if name == "Statue_Ptah":
        wrapped = (z > 0.0030) & (z < 0.0610) & (np.abs(w) < 0.0125)
        d -= wrapped * 0.00006 * band(z + 0.35 * f, 0.0017)                                         # linen wrappings
        d += 0.00010 * near(z, 0.0862, 0.00035) * (np.hypot(f + 0.0058, w) > 0.0040)               # skullcap edge
    else:
        kilt = (z > 0.0305) & (z < 0.0440) & (f > -0.0115) & (np.abs(w) < 0.0102) & (N[:, 2] > -0.3)
        d -= kilt * 0.00011 * band(w, 0.0011)                                                       # kilt pleats
        d -= kilt * 0.00012 * near(z, 0.0425, 0.0004)                                               # belt line
    beard = (np.abs(w) < 0.0017) & (f > -0.0022) & (z > 0.0700) & (z < 0.0790)
    d -= beard * 0.00008 * band(z, 0.0007)                                                          # plaited beard
    if name in ("Statue_AmunRa", "Statue_RaHorakhty"):
        wig = (z > 0.0640) & (z < 0.0925) & (f < -0.0020) & (np.abs(w) > 0.0006)
        d -= wig * 0.00009 * band(w, 0.0010)                                                        # wig striations
    if name == "Statue_AmunRa":
        plume = (z > 0.0936) & (np.abs(w) < 0.0045)
        d -= plume * 0.00010 * band(z, 0.0028)                                                      # feather bands
        d -= plume * 0.00016 * near(w, 0.0, 0.00030)                                                # split between the plumes
        d -= plume * 0.00007 * (near(w, 0.00225, 0.00025) + near(w, -0.00225, 0.00025))             # quill ribs
        d += 0.00012 * near(z, 0.0932, 0.0003) * (np.hypot(f + 0.0060, w) > 0.0034)                 # modius rim
    if name == "Statue_Ramesses":
        crown = (z > 0.0840) & (f < -0.0005)
        s = np.cos(2 * np.pi * w / 0.0012) * np.cos(2 * np.pi * (z - 0.4 * f) / 0.0012)
        d -= crown * 0.00008 * np.clip(s, 0, 1) ** 4                                                # khepresh studs
        d += 0.00013 * near(z - 0.15 * (f + 0.006), 0.0828, 0.00030) * (f < 0.0005)                 # crown's lower edge
    if name == "Statue_RaHorakhty":
        rd = np.hypot(w, z - 0.1010)
        disc_front = (f > -0.0082) & (rd < 0.0101) & (z > 0.0910)
        d += disc_front * 0.00012 * near(rd, 0.0090, 0.0004)                                        # disc rim
    return d


# ------------------------------------------------------------------ mesh utilities
def _apply_modifiers(obj):
    dg = bpy.context.evaluated_depsgraph_get(); ev = obj.evaluated_get(dg)
    new = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    obj.modifiers.clear(); old = obj.data; obj.data = new; bpy.data.meshes.remove(old); new.name = obj.name   # free the name first (no .001)


def _tris(obj): return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def _co(me):
    a = np.empty(len(me.vertices) * 3, dtype=np.float64); me.vertices.foreach_get("co", a); return a.reshape(-1, 3)


def _vnormals(me):
    a = np.empty(len(me.vertices) * 3, dtype=np.float64); me.vertex_normals.foreach_get("vector", a); return a.reshape(-1, 3)


def _sandstone_high_material(name, image):
    """Emission = box-projected sandstone x (0.75 + 0.25 AO): baked into the low-poly's base colour."""
    m = bpy.data.materials.new(name + "_HighBake"); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (TILES, TILES, TILES)
    ti = nt.nodes.new("ShaderNodeTexImage"); ti.image = image; ti.projection = "BOX"; ti.projection_blend = 0.25
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion"); ao.samples = 16; ao.inputs["Distance"].default_value = 0.004
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = 0.75; mr.inputs["To Max"].default_value = 1.0
    mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs["Factor"].default_value = 1.0
    em = nt.nodes.new("ShaderNodeEmission"); out = nt.nodes.new("ShaderNodeOutputMaterial")
    L = nt.links.new
    L(tc.outputs["Object"], mp.inputs["Vector"]); L(mp.outputs["Vector"], ti.inputs["Vector"])
    L(ao.outputs["AO"], mr.inputs["Value"])
    L(ti.outputs["Color"], mul.inputs[6]); L(mr.outputs["Result"], mul.inputs[7])
    L(mul.outputs[2], em.inputs["Color"]); L(em.outputs["Emission"], out.inputs["Surface"])
    return m


def _statue_material(name, col_img, nrm_img):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.9; bsdf.inputs["Metallic"].default_value = 0.0
    tc = nt.nodes.new("ShaderNodeTexImage"); tc.image = col_img; tc.location = (-500, 300)
    tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = nrm_img; tn.location = (-500, -100)
    nm = nt.nodes.new("ShaderNodeNormalMap"); nm.location = (-200, -100)
    nt.links.new(tc.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tn.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def _new_image(name, rgba, non_color):
    img = bpy.data.images.new(name, ATLAS, ATLAS, alpha=False, float_buffer=False)
    if non_color: img.colorspace_settings.name = "Non-Color"
    img.generated_color = rgba
    return img


def _select_only(objs, active):
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = active


# ------------------------------------------------------------------ main entry
def build(scene, sanctuary, sill, sandstone_img, texdir, log=print):
    """sanctuary: {name: (statue centre x, statue centre y)} in model space. Returns ({name: obj}, report)."""
    os.makedirs(texdir, exist_ok=True)
    col_img = _new_image("Statues_BaseColor", (0.6, 0.5, 0.4, 1.0), False)
    nrm_img = _new_image("Statues_Normal", (0.5, 0.5, 1.0, 1.0), True)
    report = {}
    lows, highs = {}, {}
    for i, name in enumerate(ORDER):
        sx, sy = sanctuary[name]
        to_world = Matrix.Translation((sx, sy, sill)) @ Matrix.Rotation(math.pi, 4, "Z")   # lx -> -X (toward the entrance)
        org, bm = figure(name)
        bm.from_mesh(_metaball_mesh(scene, name, org))
        me = bpy.data.meshes.new(name + "_High"); bm.to_mesh(me); bm.free()
        hi = bpy.data.objects.new(name + "_High", me); scene.collection.objects.link(hi)
        rm = hi.modifiers.new("Fuse", "REMESH"); rm.mode = "VOXEL"; rm.voxel_size = VOXEL; rm.adaptivity = 0.0
        sm = hi.modifiers.new("Soften", "SMOOTH"); sm.factor = 0.5; sm.iterations = 2
        _apply_modifiers(hi)
        # low-poly from the fused, softened form (before the fine carving)
        lo_me = hi.data.copy(); lo_me.name = name + "_Low"
        lo = bpy.data.objects.new(name, lo_me); scene.collection.objects.link(lo)
        dec = lo.modifiers.new("Decimate", "DECIMATE"); dec.decimate_type = "COLLAPSE"
        dec.ratio = min(1.0, LOW_TRIS / max(_tris(lo), 1)); dec.use_collapse_triangulate = True
        _apply_modifiers(lo)
        # carve the detail into the high-poly
        P = _co(hi.data); N = _vnormals(hi.data)
        d = _detail(name, P, N)
        hi.data.vertices.foreach_set("co", (P + N * d[:, None]).astype(np.float32).ravel()); hi.data.update()
        for o in (hi, lo):
            o.data.transform(to_world); o.data.update()
        report[name] = {"high_tris": _tris(hi), "low_tris": _tris(lo)}
        log("statue", name, report[name])
        lows[name], highs[name] = lo, hi

    # UVs: smart project each statue into its own quadrant of the shared atlas
    for i, name in enumerate(ORDER):
        lo = lows[name]
        _select_only([lo], lo)
        bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.01, area_weight=0.0, scale_to_bounds=True)
        bpy.ops.object.mode_set(mode="OBJECT")
        uv = lo.data.uv_layers[0]
        a = np.empty(len(lo.data.loops) * 2, dtype=np.float32); uv.uv.foreach_get("vector", a); a = a.reshape(-1, 2)
        a = a * 0.49 + np.array([(i % 2) * 0.5 + 0.005, (i // 2) * 0.5 + 0.005])
        uv.uv.foreach_set("vector", a.ravel())

    # bake: normal (high -> low) and base colour (sandstone x AO emission on the high -> low)
    scene.render.engine = "CYCLES"; scene.cycles.device = "CPU"; scene.cycles.samples = 24
    bake = scene.render.bake
    bake.use_selected_to_active = True; bake.cage_extrusion = 0.0006; bake.max_ray_distance = 0.0025
    bake.margin = 6; bake.use_clear = False
    for name in ORDER:
        lo, hi = lows[name], highs[name]
        hi.data.materials.clear(); hi.data.materials.append(_sandstone_high_material(name, sandstone_img))
        mat = _statue_material(name, col_img, nrm_img)
        lo.data.materials.clear(); lo.data.materials.append(mat)
        nt = mat.node_tree
        img_nodes = {n.image.name: n for n in nt.nodes if n.type == "TEX_IMAGE"}
        _select_only([hi, lo], lo)
        nt.nodes.active = img_nodes["Statues_Normal"]
        bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT")
        nt.nodes.active = img_nodes["Statues_BaseColor"]
        bpy.ops.object.bake(type="EMIT")
        log("baked", name)
    col_path = os.path.join(texdir, "Statues_BaseColor.jpg"); nrm_path = os.path.join(texdir, "Statues_Normal.png")
    col_img.file_format = "JPEG"; col_img.save(filepath=col_path, quality=90)
    nrm_img.file_format = "PNG"; nrm_img.save(filepath=nrm_path)
    for img, path in ((col_img, col_path), (nrm_img, nrm_path)):
        img.filepath = path; img.source = "FILE"; img.reload()
    nrm_img.colorspace_settings.name = "Non-Color"

    for hi in highs.values():                         # the high-polys only feed the bake
        me, mats = hi.data, [m for m in hi.data.materials if m]
        bpy.data.objects.remove(hi); bpy.data.meshes.remove(me)
        for m in mats: bpy.data.materials.remove(m)
    report["atlas"] = {"base_color": col_path, "normal": nrm_path, "size": ATLAS}
    return lows, report
