"""Interior and outer surfaces of the scripted temple body (imported by 02_build_hybrid_temple.py).

Interior_Shell and Interior_Pillars (walls, floor, partitions, pillars and the outer back and
sides of the "mountain") get one 2048 px atlas with a baked base colour and a normal map:

  stone   inner faces: sandstone matched to the Meshy facade's mean colour, with block courses
          (the saw-cut joints of the 1964-68 relocation, visible in the halls today), chisel
          streaks and per-block colour variation
  relief  the two long walls of the great hall: the stone plus simple sunk-relief panels
          (a frieze band, two registers of standing figures and columns of signs)
  rock    the outer sides and back: stratified, rough sandstone rock (the mountain's flanks)
  cut     the horizontal section plane of the museum cutaway: smoother cut stone

Baked with Cycles from procedural materials (no AI generation): albedo, soft sky light
(irradiance from a uniform sky through the open top, no sun: the sun stays a live light) and
ambient occlusion, combined into the base colour, plus a tangent-space normal map of the bump
detail. Colour is a saturated ochre-to-golden-brown sandstone; the AO is kept deep so carving,
pillars and corners read. The atlas is matched to the (graded) facade's mean brightness rather
than lifted above it. The statues keep their own objects, materials and atlas.
"""
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector
import surface_grade as sg

ATLAS = 2048
LIGHT_BAKE = 1024            # lighting is smooth: baked at half resolution, then upsampled
BLOCK_W, BLOCK_H = 0.11, 0.05    # relocation blocks (model metres; ~5.5 x 2.5 m real)
JOINT = 0.0008


def _srgb_to_lin(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def _lum(rgb):
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


# ------------------------------------------------------------------ relief artwork (numpy)
def _relief_maps(w=2048, h=512, seed=11):
    """Sunk relief for a hall wall: depth (0 surface .. 1 deepest) and an edge (cavity) map."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    depth = np.zeros((h, w))

    def rect(x0, y0, x1, y1, d=1.0):
        depth[int(y0):int(y1), int(x0):int(x1)] = np.maximum(depth[int(y0):int(y1), int(x0):int(x1)], d)

    def ellipse(cx, cy, rx, ry, d=1.0):
        m = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1
        depth[m] = np.maximum(depth[m], d)

    def figure(cx, base, hgt, facing):
        # a standing figure in Egyptian convention: head, shoulders square to the viewer, kilt, striding legs
        u = hgt / 10.0
        ellipse(cx, base - 9.0 * u, 0.75 * u, 0.85 * u)                       # head
        rect(cx - 0.35 * u, base - 8.2 * u, cx + 0.35 * u, base - 7.6 * u)    # neck
        rect(cx - 1.5 * u, base - 7.7 * u, cx + 1.5 * u, base - 7.0 * u)      # shoulders
        rect(cx - 0.9 * u, base - 7.0 * u, cx + 0.9 * u, base - 4.6 * u)      # torso
        rect(cx - 1.1 * u, base - 4.6 * u, cx + 1.1 * u, base - 3.4 * u)      # kilt
        rect(cx - 0.75 * u + facing * 0.5 * u, base - 3.4 * u, cx - 0.25 * u + facing * 0.5 * u, base)   # forward leg
        rect(cx + 0.15 * u - facing * 0.2 * u, base - 3.4 * u, cx + 0.6 * u - facing * 0.2 * u, base)    # back leg
        rect(cx + facing * 1.2 * u, base - 7.4 * u, cx + facing * 2.6 * u, base - 6.9 * u)               # raised arm
        rect(cx - facing * 1.4 * u, base - 7.2 * u, cx - facing * 1.0 * u, base - 4.8 * u)               # hanging arm

    def signs(x0, y0, y1, colw):
        # a column of hieroglyph-like signs: small varied blocks
        y = y0
        while y < y1 - colw:
            kind = rng.integers(0, 3)
            if kind == 0:
                rect(x0, y, x0 + colw, y + colw * 0.45)
            elif kind == 1:
                ellipse(x0 + colw / 2, y + colw / 2, colw * 0.42, colw * 0.42)
            else:
                rect(x0 + colw * 0.3, y, x0 + colw * 0.7, y + colw)
            y += colw * 1.35

    m = 0.035 * h
    rect(0, m, w, m + 0.03 * h, 0.6)                    # frieze band (kheker line)
    for i in range(0, w, int(0.02 * w)):
        rect(i, m + 0.035 * h, i + 0.006 * w, m + 0.08 * h, 0.7)   # frieze teeth
    rect(0, 0.52 * h, w, 0.535 * h, 0.5)                # register divider
    for reg_base, hgt in ((0.50 * h, 0.34 * h), (0.95 * h, 0.36 * h)):
        x = 0.03 * w
        facing = 1
        while x < w - 0.05 * w:
            figure(x, reg_base, hgt, facing)
            signs(x + 0.025 * w, reg_base - hgt, reg_base - hgt * 0.45, 0.010 * w)
            x += rng.uniform(0.055, 0.075) * w
            if rng.random() < 0.15:
                facing = -facing
    # soften the carving (a few box blurs) so the bake gets bevelled edges
    for _ in range(2):
        k = 2
        p = np.pad(depth, k, mode="edge")
        c = np.cumsum(np.cumsum(p, 0), 1)
        c = np.pad(c, ((1, 0), (1, 0)))
        depth = (c[2 * k + 1:, 2 * k + 1:] - c[:-2 * k - 1, 2 * k + 1:] - c[2 * k + 1:, :-2 * k - 1] + c[:-2 * k - 1, :-2 * k - 1]) / (2 * k + 1) ** 2
    gy, gx = np.gradient(depth)
    edge = np.clip(np.hypot(gx, gy) * 6.0, 0, 1)
    return depth, edge


def _image_from_array(name, arr, path):
    h, w = arr.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=True, float_buffer=False)
    px = np.ones((h, w, 4), dtype=np.float32)
    if arr.ndim == 2:
        px[..., 0] = px[..., 1] = px[..., 2] = arr
    else:
        px[..., :3] = arr[..., :3]
    img.pixels.foreach_set(px[::-1].ravel())          # Blender rows start at the bottom
    img.filepath_raw = path; img.file_format = "PNG"; img.save()
    ld = bpy.data.images.load(path); ld.colorspace_settings.name = "Non-Color"; ld.name = name
    bpy.data.images.remove(img)
    return ld


# ------------------------------------------------------------------ procedural materials
def _plane_vector(nt, plane):
    """Object-space coordinates projected onto the face plane: X faces use (y, z), Y faces (x, z), Z faces (x, y)."""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    a, b = {"X": ("Y", "Z"), "Y": ("X", "Z"), "Z": ("X", "Y")}[plane]
    nt.links.new(sep.outputs[a], comb.inputs["X"]); nt.links.new(sep.outputs[b], comb.inputs["Y"])
    return comb.outputs[0], tc.outputs["Object"]


def _mix(nt, a, b, fac, blend="MIX"):
    m = nt.nodes.new("ShaderNodeMix"); m.data_type = "RGBA"; m.blend_type = blend
    if isinstance(fac, (int, float)): m.inputs["Factor"].default_value = fac
    else: nt.links.new(fac, m.inputs["Factor"])
    for sock, v in ((m.inputs[6], a), (m.inputs[7], b)):
        if isinstance(v, tuple): sock.default_value = v
        else: nt.links.new(v, sock)
    return m.outputs[2]


def _math(nt, op, a, b=None):
    n = nt.nodes.new("ShaderNodeMath"); n.operation = op
    for i, v in enumerate((a, b)):
        if v is None: continue
        if isinstance(v, (int, float)): n.inputs[i].default_value = v
        else: nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def _swatch(nt, obj, img, tile, scale=1.0, rot=(0.0, 0.0, 0.0), loc=(0.0, 0.0, 0.0)):
    """A swatch image box-projected in object space (no UV stretching on any face), tile in metres."""
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0 / (tile * scale),) * 3
    mp.inputs["Rotation"].default_value = rot; mp.inputs["Location"].default_value = loc
    nt.links.new(obj, mp.inputs["Vector"])
    ti = nt.nodes.new("ShaderNodeTexImage"); ti.image = img; ti.interpolation = "Cubic"
    ti.projection = "BOX"; ti.projection_blend = 0.3; ti.extension = "REPEAT"
    nt.links.new(mp.outputs[0], ti.inputs["Vector"])
    return ti.outputs["Color"]


def _untiled(nt, obj, img, tile, seed):
    """Two differently scaled and rotated samples of one swatch, mixed by a broad noise mask, so the
    tile never repeats visibly across a wall or the rock mass."""
    a = _swatch(nt, obj, img, tile, 1.0, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    b = _swatch(nt, obj, img, tile, 1.37, (0.0, 0.0, 1.13 + seed), (0.29, 0.53, 0.11))   # about Z only: tilting the
    # projection planes smears the box projection on sloped faces
    n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 3.0 + seed; n.inputs["Detail"].default_value = 2.0
    nt.links.new(obj, n.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0.42; mr.inputs["From Max"].default_value = 0.58
    nt.links.new(n.outputs["Fac"], mr.inputs["Value"])
    return _mix(nt, a, b, mr.outputs["Result"])


def _large_variation(nt, obj, col, amount=1.0):
    """Large-scale weathering: patches of subtle reddish brown and paler sand, and broad value drift."""
    n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 3.5; n.inputs["Detail"].default_value = 3.0
    nt.links.new(obj, n.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    e = ramp.color_ramp.elements
    e[0].position = 0.28; e[0].color = (1 - 0.10 * amount, 1 - 0.17 * amount, 1 - 0.20 * amount, 1)   # reddish brown
    e[1].position = 0.78; e[1].color = (1 + 0.04 * amount, 1 + 0.04 * amount, 1 + 0.05 * amount, 1)   # paler sand
    mid = e.new(0.5); mid.color = (1, 1, 1, 1)
    nt.links.new(n.outputs["Fac"], ramp.inputs["Fac"])
    col = _mix(nt, col, ramp.outputs["Color"], 1.0, "MULTIPLY")
    n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 1.2; n2.inputs["Detail"].default_value = 1.0
    nt.links.new(obj, n2.inputs["Vector"])
    drift = _math(nt, "ADD", 1.0 - 0.06 * amount, _math(nt, "MULTIPLY", n2.outputs["Fac"], 0.12 * amount))
    return _mix(nt, col, drift, 1.0, "MULTIPLY")


def make_surface_material(name, kind, plane, swatches, relief=None, hall=None, band=None):
    """kind: 'stone' | 'relief' | 'rock' | 'cut'. swatches: {'Stone'|'Rock'|'Cut': (image, tile_m)}, all
    sampled from the Meshy facade (facade_swatch.py), so every surface shares its grain and colour.
    relief: (depth_img, edge_img); hall: (x0, length, z0, height) of the great hall wall mapping.
    band: (x_facade_back, width): rock within this distance of the facade's back blends into the
    facade's dressed stone, so the join has no step in colour or texture."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.9; bsdf.inputs["Metallic"].default_value = 0.0
    uv2, obj = _plane_vector(nt, plane)
    seed = {"stone": 0.0, "relief": 0.0, "rock": 0.4, "cut": 0.8}[kind]
    sw = {"stone": "Stone", "relief": "Stone", "rock": "Rock", "cut": "Cut"}[kind]
    col = _untiled(nt, obj, swatches[sw][0], swatches[sw][1], seed)
    bw = nt.nodes.new("ShaderNodeRGBToBW"); nt.links.new(col, bw.inputs[0])
    grain = bw.outputs[0]
    col = _large_variation(nt, obj, col, 0.7 if kind == "cut" else 1.0)
    if kind == "cut":
        # the cutaway's section plane: the same sandstone, sawn smooth
        height = _math(nt, "MULTIPLY", grain, 0.3)
        bump_strength, bump_dist = 0.12, 0.0003
    elif kind in ("stone", "relief"):
        brick = nt.nodes.new("ShaderNodeTexBrick")
        brick.inputs["Scale"].default_value = 1.0
        brick.inputs["Brick Width"].default_value = BLOCK_W; brick.inputs["Row Height"].default_value = BLOCK_H
        brick.inputs["Mortar Size"].default_value = JOINT; brick.inputs["Mortar Smooth"].default_value = 0.4
        brick.inputs["Bias"].default_value = 0.0
        brick.offset = 0.37; brick.offset_frequency = 3; brick.squash = 0.8; brick.squash_frequency = 2
        brick.inputs["Color1"].default_value = (1.0, 1.0, 1.0, 1); brick.inputs["Color2"].default_value = (0.96, 0.95, 0.95, 1)
        brick.inputs["Mortar"].default_value = (0.8, 0.77, 0.75, 1)
        nt.links.new(uv2, brick.inputs["Vector"])
        col = _mix(nt, col, brick.outputs["Color"], 1.0, "MULTIPLY")             # faint relocation joints
        joint = _math(nt, "SUBTRACT", 1.0, brick.outputs["Fac"])                  # 1 on blocks, 0 in joints
        height = _math(nt, "ADD", _math(nt, "MULTIPLY", joint, 0.8), _math(nt, "MULTIPLY", grain, 0.8))
        if kind == "relief":
            x0, length, z0, hgt = hall
            sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(obj, sep.inputs[0])
            comb = nt.nodes.new("ShaderNodeCombineXYZ")
            nt.links.new(_math(nt, "DIVIDE", _math(nt, "SUBTRACT", sep.outputs["X"], x0), length), comb.inputs["X"])
            nt.links.new(_math(nt, "DIVIDE", _math(nt, "SUBTRACT", sep.outputs["Z"], z0), hgt), comb.inputs["Y"])
            imgs = []
            for img in relief:
                ti = nt.nodes.new("ShaderNodeTexImage"); ti.image = img; ti.extension = "CLIP"; ti.interpolation = "Cubic"
                nt.links.new(comb.outputs[0], ti.inputs["Vector"]); imgs.append(ti)
            depth, edge = imgs[0].outputs["Color"], imgs[1].outputs["Color"]
            dsep = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(depth, dsep.inputs[0])
            esep = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(edge, esep.inputs[0])
            height = _math(nt, "SUBTRACT", height, _math(nt, "MULTIPLY", dsep.outputs[0], 2.2))
            col = _mix(nt, col, _math(nt, "SUBTRACT", 1.0, _math(nt, "MULTIPLY", esep.outputs[0], 0.45)), 1.0, "MULTIPLY")
            col = _mix(nt, col, _math(nt, "SUBTRACT", 1.0, _math(nt, "MULTIPLY", dsep.outputs[0], 0.08)), 1.0, "MULTIPLY")
        bump_strength, bump_dist = 0.3, 0.0006
    else:
        # rock: the facade's cliff grain, broken into large weathered lumps and faint strata
        strata = nt.nodes.new("ShaderNodeTexWave"); strata.wave_type = "BANDS"; strata.bands_direction = "Z"
        strata.inputs["Scale"].default_value = 7.0; strata.inputs["Distortion"].default_value = 1.5; strata.inputs["Detail"].default_value = 2.0
        nt.links.new(obj, strata.inputs["Vector"])
        vor = nt.nodes.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 28.0
        nt.links.new(obj, vor.inputs["Vector"])
        crev = _math(nt, "ADD", 0.9, _math(nt, "MULTIPLY", _math(nt, "MINIMUM", _math(nt, "MULTIPLY", vor.outputs["Distance"], 2.5), 1.0), 0.1))
        col = _mix(nt, col, crev, 1.0, "MULTIPLY")
        height = _math(nt, "ADD", _math(nt, "MULTIPLY", vor.outputs["Distance"], 1.2),
                       _math(nt, "ADD", _math(nt, "MULTIPLY", grain, 1.0), _math(nt, "MULTIPLY", strata.outputs["Fac"], 0.15)))
        bump_strength, bump_dist = 0.55, 0.0012
        if band is not None:
            xb, width = band
            stone = _large_variation(nt, obj, _untiled(nt, obj, swatches["Stone"][0], swatches["Stone"][1], 0.0))
            sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(obj, sep.inputs[0])
            nb = nt.nodes.new("ShaderNodeTexNoise"); nb.inputs["Scale"].default_value = 40.0; nb.inputs["Detail"].default_value = 3.0
            nt.links.new(obj, nb.inputs["Vector"])
            d = _math(nt, "ADD", _math(nt, "DIVIDE", _math(nt, "SUBTRACT", sep.outputs["X"], xb), width),
                      _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", nb.outputs["Fac"], 0.5), 0.8))
            mr = nt.nodes.new("ShaderNodeMapRange"); mr.interpolation_type = "SMOOTHSTEP"
            mr.inputs["From Min"].default_value = 0.0; mr.inputs["From Max"].default_value = 1.0
            mr.inputs["To Min"].default_value = 0.0; mr.inputs["To Max"].default_value = 1.0
            nt.links.new(d, mr.inputs["Value"])
            rockness = mr.outputs["Result"]                     # 0 at the facade, 1 one band width behind it
            col = _mix(nt, stone, col, rockness)
            height = _math(nt, "MULTIPLY", height, rockness)
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = bump_dist
    nt.links.new(height, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(col, bsdf.inputs["Base Color"])
    tgt = nt.nodes.new("ShaderNodeTexImage"); tgt.name = "BakeTarget"
    nt.nodes.active = tgt
    return m


# ------------------------------------------------------------------ face roles
def assign_roles(obj, cy, x0, xe, in1, floor_z, sill, mats, h_cut=None, enclosed=False):
    """mats: dict role -> material (role = stone_X/Y/Z, relief, rock_X/Y, cut). Deletes never-seen
    faces; with `enclosed` (the rock mass wraps the halls) the shell's own outer faces go too."""
    me = obj.data
    bm = bmesh.new(); bm.from_mesh(me)
    # never-seen faces: anything facing down onto the plinth or the floor slab, and faces lying in
    # the plane of a larger face of another box (the side walls' end caps inside the back wall's
    # outer face), which would z-fight and bake as fully occluded
    hidden = [f for f in bm.faces if f.normal.z < -0.9 and f.calc_center_median().z <= sill + 1e-4]
    if enclosed and obj.name == "Interior_Shell":
        # the rock mass wraps the halls: the shell's outward faces (sides, back) are inside it
        for f in bm.faces:
            n, c = f.normal, f.calc_center_median(); dy = c.y - cy
            if f in hidden or abs(n.z) > 0.5 or c.x < x0 - 1e-4: continue
            if (abs(n.y) > 0.9 and abs(dy) > in1 + 0.01 and np.sign(n.y) == np.sign(dy)) or (n.x > 0.9 and c.x > xe - 0.001):
                hidden.append(f)
    for f in bm.faces:
        if f in hidden: continue
        c = f.calc_center_median(); a = f.calc_area()
        for g in bm.faces:
            if g is f or g.calc_area() <= a * 1.01: continue
            if f.normal.dot(g.normal) > 0.999 and abs((c - g.calc_center_median()).dot(g.normal)) < 1e-5:
                lo = [min(v.co[i] for v in g.verts) - 1e-5 for i in range(3)]
                hi = [max(v.co[i] for v in g.verts) + 1e-5 for i in range(3)]
                if all(lo[i] <= v.co[i] <= hi[i] for v in f.verts for i in range(3)):
                    hidden.append(f); break
    bmesh.ops.delete(bm, geom=hidden, context="FACES")
    bm.to_mesh(me); bm.free(); me.update()
    me.materials.clear()
    order = list(mats.keys())
    for k in order: me.materials.append(mats[k])
    idx = {k: i for i, k in enumerate(order)}
    counts = {k: 0 for k in order}
    for p in me.polygons:
        n, c = p.normal, p.center
        ax = "XYZ"[int(np.argmax(np.abs([n.x, n.y, n.z])))]
        dy = c.y - cy
        outer = abs(n.z) < 0.5 and ((abs(n.y) > 0.9 and abs(dy) > in1 + 0.01 and np.sign(n.y) == np.sign(dy))
                                     or (n.x > 0.9 and c.x > xe - 0.001))
        hall_wall = abs(n.y) > 0.9 and abs(abs(dy) - in1) < 0.002 and np.sign(n.y) == -np.sign(dy) and obj.name == "Interior_Shell"
        section = h_cut is not None and n.z > 0.9 and abs(c.z - h_cut) < 1e-4
        if obj.name in ("Mountain", "Facade_Backing", "Back_Plate"):
            role = "cut" if section else "rock_X"
        elif section: role = "cut"
        elif outer: role = "rock_" + ("X" if ax == "X" else "Y")
        elif hall_wall: role = "relief"
        else: role = "stone_" + ax
        p.material_index = idx[role]; counts[role] += 1
    return counts


# ------------------------------------------------------------------ the mountain (rock mass) and facade backing
def _noise2(a, b, seed=3):
    rng = np.random.default_rng(seed)
    out = np.zeros_like(a)
    for f, w in ((9.0, 1.0), (19.0, 0.5), (41.0, 0.25)):
        ph = rng.uniform(0, 2 * np.pi, 4); k = rng.uniform(0.6, 1.4, 2)
        out += w * np.sin(a * f * k[0] + ph[0]) * np.sin(b * f * k[1] + ph[1]) + 0.5 * w * np.sin((a + b) * f * 0.7 + ph[2])
    return out / 2.0


def _resample(poly, counts):
    """poly: list of corner points (open polyline); counts: samples per segment."""
    pts = []
    for (a, b), n in zip(zip(poly[:-1], poly[1:]), counts):
        a, b = np.array(a), np.array(b)
        for i in range(n):
            pts.append(a + (b - a) * i / n)
    pts.append(np.array(poly[-1]))
    return np.array(pts)


def build_mountain(scene, cy, x0, xe, out_half, floor_z, h_cut):
    """The cliff the temple is cut into, sliced by one horizontal section plane at h_cut: a flat
    cut-stone ring around the halls (meeting the hall walls' cut tops) with rock flanks and back
    sloping down to the plinth. The front stays inside the facade's width so nothing pokes out.
    Dense enough (about 1.5 cm between vertices) that the lumpy surface stays smooth: the noise is
    band-limited well below the vertex spacing and the rock is smooth-shaded, with sharp edges only
    at the cut ring and the base, so no triangle facets show."""
    BB, RUN = 0.06, 0.18                       # back band beyond the back wall; back slope run
    Wt0, Wt1, Wb0, Wb1 = 0.40, 0.34, 0.46, 0.52
    counts = (90, 30, 90)
    top = _resample([(x0, cy + Wt0), (xe + BB, cy + Wt1), (xe + BB, cy - Wt1), (x0, cy - Wt0)], counts)
    base = _resample([(x0, cy + Wb0), (xe + BB + RUN, cy + Wb1), (xe + BB + RUN, cy - Wb1), (x0, cy - Wb0)], counts)
    inner = _resample([(x0, cy + out_half), (xe, cy + out_half), (xe, cy - out_half), (x0, cy - out_half)], counts)
    rows = 20
    bm = bmesh.new()
    grid = []
    ncol = len(top)
    for r in range(rows + 1):
        v = r / rows
        row = []
        for i in range(ncol):
            p = top[i] + (base[i] - top[i]) * v
            z = h_cut + (floor_z - h_cut) * (v ** 0.85)
            # rocky surface: push outward with smooth noise, zero at the cut edge, the base and the
            # front ends (fading over the first 6 columns so the flank meets the facade cleanly)
            d = base[i] - top[i]; dn = d / max(np.linalg.norm(d), 1e-6)
            edge = min(1.0, min(i, ncol - 1 - i) / 6.0)
            # amplitude x vertical frequency is kept below the flank's own slope (~0.3 run per
            # unit height), so the surface never folds over itself: folds face inward and bake dark
            amp = 0.01 * math.sin(math.pi * v) * edge
            k = _noise2(np.array(p[0] * 2.2), np.array(z * 1.2 + p[1] * 1.0))
            p = p + dn * amp * float(k)
            z = z + 0.006 * math.sin(math.pi * v) * edge * float(_noise2(np.array(p[1] * 2.5), np.array(p[0] * 2.0), seed=8))
            row.append(bm.verts.new((float(p[0]), float(p[1]), float(z))))
        grid.append(row)
    rock_faces = []
    for r in range(rows):
        for i in range(ncol - 1):
            rock_faces.append(bm.faces.new((grid[r][i], grid[r][i + 1], grid[r + 1][i + 1], grid[r + 1][i])))
    inner_v = [bm.verts.new((float(q[0]), float(q[1]), h_cut)) for q in inner]
    for i in range(ncol - 1):
        bm.faces.new((inner_v[i], inner_v[i + 1], grid[0][i + 1], grid[0][i]))
    # front ends (pressed against the facade's back; closed so nothing shows through)
    for i, sgn in ((0, 1), (ncol - 1, -1)):
        col = [grid[r][i] for r in range(rows + 1)]
        a = bm.verts.new((x0, cy + sgn * out_half, floor_z))
        bm.faces.new([inner_v[i]] + col + [a])
    # one consistent orientation for the whole shell (flipping faces one by one by a direction test
    # left a few noise-tilted faces inverted: dark specks in the bake), then outward: the cut ring faces up
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    ring = [f for f in bm.faces if abs(f.calc_center_median().z - h_cut) < 1e-5 and abs(f.normal.z) > 0.9]
    if ring and sum(f.normal.z for f in ring) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.normal_update()
    rock = set(rock_faces)
    for f in bm.faces: f.smooth = f in rock
    for e in bm.edges:                          # sharp where the rock meets the cut ring, the ends and the base
        lf = e.link_faces
        e.smooth = not (len(lf) < 2 or (lf[0] in rock) != (lf[1] in rock) or lf[0].normal.dot(lf[1].normal) < 0.6)
    me = bpy.data.meshes.new("Mountain"); bm.to_mesh(me); bm.free()
    obj = bpy.data.objects.new("Mountain", me); scene.collection.objects.link(obj)
    return obj


def build_facade_backing(scene, facade, xb, x, floor_z, passage):
    """A rock skin just BEHIND the facade's back face (at x, facing +X), from the plinth up to the
    facade's top silhouette (sampled at 5 mm, 3 mm under the edge), open over the doorway passage
    (passage = (y0, y1, z_top)). It hides the Meshy model's flat, smeared back and its gaps, covers
    the old back plate's face (so there is no seam line between them), runs 8 mm past each end of
    the silhouette so no slit shows at the cliff corners, and its texture blends into the facade
    stone (transition band). It sits outside the facade block, so its bake sees the sky (the old
    skin was inside the block, baked almost black, and showed as dark triangles through the gaps)."""
    co = np.array([facade.matrix_world @ v.co for v in facade.data.vertices])
    near = co[(co[:, 0] > xb - 0.04) & (co[:, 0] < xb + 0.01)]
    ys = np.arange(near[:, 1].min() - 0.008, near[:, 1].max() + 0.008, 0.005)
    tops = []
    for y in ys:
        m = np.abs(near[:, 1] - y) < 0.004
        tops.append(near[m, 2].max() - 0.003 if m.any() else None)
    t = np.array([np.nan if v is None else v for v in tops])
    good = ~np.isnan(t)
    t = np.interp(np.arange(len(t)), np.nonzero(good)[0], t[good])   # fills holes, holds the end heights
    py0, py1, pz = passage
    bm = bmesh.new()
    prev = None
    def col(y, tz):
        bottom = pz if py0 < y < py1 else floor_z
        return bm.verts.new((x, float(y), bottom)), bm.verts.new((x, float(y), float(tz)))
    # break the strip at the passage edges so its opening is exact
    yy = sorted(set(list(ys) + [py0, py1]))
    tt = np.interp(yy, ys, t)
    for y, tz in zip(yy, tt):
        cur = col(y, tz)
        if prev:
            mid = 0.5 * (prev[2] + y)
            if py0 - 1e-6 <= mid <= py1 + 1e-6:      # over the passage: only above its top
                lo0 = bm.verts.new((x, float(prev[2]), pz)); lo1 = bm.verts.new((x, float(y), pz))
                f = bm.faces.new((lo0, lo1, cur[1], prev[1]))
            else:
                a = prev[0] if prev[0].co.z == floor_z else bm.verts.new((x, float(prev[2]), floor_z))
                b = cur[0] if cur[0].co.z == floor_z else bm.verts.new((x, float(y), floor_z))
                f = bm.faces.new((a, b, cur[1], prev[1]))
            f.normal_update()
            if f.normal.x < 0: f.normal_flip()
        prev = (cur[0], cur[1], y)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    me = bpy.data.meshes.new("Facade_Backing"); bm.to_mesh(me); bm.free()
    obj = bpy.data.objects.new("Facade_Backing", me); scene.collection.objects.link(obj)
    return obj


def _split_t_junctions(bm, eps=1e-5):
    """Split every edge that has another vertex lying inside it (same plane), so coplanar faces
    meeting in T-junctions share vertices and can be welded."""
    for _ in range(8):
        hits = []
        by_z = {}
        for v in bm.verts: by_z.setdefault(round(v.co.z / eps), []).append(v)
        for e in bm.edges:
            a, b = e.verts[0].co, e.verts[1].co
            if abs(a.z - b.z) > eps: continue                  # only edges lying in a horizontal plane
            d = b - a; L2 = d.length_squared
            if L2 < eps * eps: continue
            k = round(a.z / eps)
            for v in by_z.get(k, []) + by_z.get(k - 1, []) + by_z.get(k + 1, []):
                if v in e.verts: continue
                t = (v.co - a).dot(d) / L2
                if eps < t < 1 - eps and (a + d * t - v.co).length < eps:
                    hits.append((e, t)); break
        if not hits: return
        for e, t in hits:
            if e.is_valid: bmesh.utils.edge_split(e, e.verts[0], t)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=eps)


def merge_faces(src, dst, face_filter=None):
    """Move src's faces (all, or those passing face_filter) into dst, keeping material indices
    (every object gets the same role-material list from assign_roles). Removes src when emptied."""
    bs = bmesh.new(); bs.from_mesh(src.data)
    bd = bmesh.new(); bd.from_mesh(dst.data)
    move = [f for f in bs.faces if face_filter is None or face_filter(f)]
    vmap = {}
    for f in move:
        vs = []
        for v in f.verts:
            if v not in vmap: vmap[v] = bd.verts.new(src.matrix_world @ v.co)
            vs.append(vmap[v])
        nf = bd.faces.new(vs); nf.material_index = f.material_index; nf.smooth = False
    # weld onto dst where they touch (the wall tops meet each other and the rock's cut ring). The
    # box tops meet in T-junctions (a corner in the middle of the neighbour's edge), which leave
    # hairline cracks showing the black, sandwiched faces below: split those edges first
    _split_t_junctions(bd)
    bmesh.ops.remove_doubles(bd, verts=bd.verts[:], dist=1e-5)
    bd.to_mesh(dst.data); bd.free()
    n = len(move)
    if face_filter is None or n == len(bs.faces):
        bs.free(); me = src.data; bpy.data.objects.remove(src); bpy.data.meshes.remove(me)
    else:
        bmesh.ops.delete(bs, geom=move, context="FACES"); bs.to_mesh(src.data); bs.free()
    return n


# ------------------------------------------------------------------ bake
def _bake_image(name, size, float_buffer):
    img = bpy.data.images.new(name, size, size, alpha=True, float_buffer=float_buffer)
    img.colorspace_settings.name = "Non-Color"
    img.generated_color = (0, 0, 0, 0)
    return img


def _set_targets(objs, img):
    for o in objs:
        for m in o.data.materials:
            nd = m.node_tree.nodes["BakeTarget"]; nd.image = img; m.node_tree.nodes.active = nd


def _pixels(img):
    a = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32); img.pixels.foreach_get(a)
    return a.reshape(img.size[1], img.size[0], 4)


def _bake_group(scene, objs, name, texdir, log, calm=None, section_z=None):
    """One shared atlas for objs: albedo (DIFFUSE colour), soft sky light, AO and a tangent normal map,
    then the shared colour grade (surface_grade.grade, the same call 03 applies to the facade) and
    the AO, exactly as the facade gets them. calm(x) -> factor, applied per texel from its baked
    world position (the halls grow calmer toward the sanctuary). section_z: texels lying on the
    cutaway's section plane get no AO (nothing above can shade it; the bake left a dark groove
    there along the hall rims). Returns (material, report)."""
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for o in objs:
        o.select_set(True)
        while o.data.uv_layers: o.data.uv_layers.remove(o.data.uv_layers[0])
        o.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004, area_weight=0.0, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")

    def run(kind, size, samples, **kw):
        img = _bake_image("bake_%s_%s" % (name, kind), size, True)
        _set_targets(objs, img)
        scene.cycles.samples = samples
        bpy.ops.object.bake(type=kind, **kw)
        log("baked", name, kind, size)
        a = _pixels(img); bpy.data.images.remove(img)
        return a

    albedo = run("DIFFUSE", ATLAS, 1, pass_filter={"COLOR"})
    irr = run("DIFFUSE", LIGHT_BAKE, 96, pass_filter={"DIRECT", "INDIRECT"})
    ao = run("AO", LIGHT_BAKE, 96)
    pos = run("POSITION", ATLAS, 1) if (calm or section_z is not None) else None
    nimg = _bake_image("bake_%s_normal" % name, ATLAS, False)
    _set_targets(objs, nimg)
    scene.cycles.samples = 4
    bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT")
    log("baked", name, "NORMAL", ATLAS)

    def up(a):                                    # LIGHT_BAKE -> ATLAS
        r = ATLAS // a.shape[0]
        return np.repeat(np.repeat(a, r, 0), r, 1)
    mask = albedo[..., 3] > 0.5
    irr_u = up(irr[..., :3].mean(axis=2)); ao_u = up(ao[..., :3].mean(axis=2))
    ref = np.percentile(irr_u[mask], 92) if mask.any() else 1.0
    light = np.clip(irr_u / max(ref, 1e-4), 0, 1.1)
    if section_z is not None:
        on_plane = np.abs(pos[..., 2] - section_z) < 2e-4
        ao_u = np.where(on_plane, 1.0, ao_u); light = np.where(on_plane, 1.0, light)
    shade = (0.82 + 0.18 * light) * sg.ao_factor(ao_u)          # mostly AO: the live lights do the rest
    if calm:
        shade = shade * calm(pos[..., 0])
    graded = sg.grade(_lin_to_srgb(albedo[..., :3]))           # ONE grade, shared with the facade
    srgb = _lin_to_srgb(sg.srgb_to_lin(graded) * shade[..., None])
    srgb[~mask] = srgb[mask].mean(axis=0)                     # unbaked gutter: mean colour, no black mip bleed
    rep = {"mean_luminance": round(float(_lum(srgb[mask]).mean()), 3),
           "mean_srgb": [round(float(v), 3) for v in srgb[mask].mean(axis=0)]}

    col_path = os.path.join(texdir, name + "_BaseColor.jpg"); nrm_path = os.path.join(texdir, name + "_Normal.jpg")
    out = bpy.data.images.new(name + "_BaseColor", ATLAS, ATLAS, alpha=False, float_buffer=False)
    px = np.ones((ATLAS, ATLAS, 4), dtype=np.float32); px[..., :3] = srgb
    out.pixels.foreach_set(px.ravel()); out.filepath_raw = col_path; out.file_format = "JPEG"
    out.save(filepath=col_path, quality=90)
    npx = _pixels(nimg).copy(); npx[~mask] = (0.5, 0.5, 1.0, 1.0)
    nimg.pixels.foreach_set(npx.ravel()); nimg.file_format = "JPEG"; nimg.save(filepath=nrm_path, quality=92)
    bpy.data.images.remove(nimg); bpy.data.images.remove(out)
    col_img = bpy.data.images.load(col_path); col_img.name = name + "_BaseColor"
    nrm_img = bpy.data.images.load(nrm_path); nrm_img.name = name + "_Normal"; nrm_img.colorspace_settings.name = "Non-Color"

    final = bpy.data.materials.new(name); final.use_nodes = True
    nt = final.node_tree; bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.9; bsdf.inputs["Metallic"].default_value = 0.0
    tc = nt.nodes.new("ShaderNodeTexImage"); tc.image = col_img
    tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = nrm_img
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tc.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tn.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    rep["bytes"] = os.path.getsize(col_path) + os.path.getsize(nrm_path)
    return final, rep


def build(scene, interior, rock, swatch_paths, cy, x0, xe, in1, floor_z, sill, hall_height, texdir, log=print, h_cut=None):
    """interior: {name: obj} for Interior_Shell, Interior_Pillars; rock: {name: obj} for Mountain,
    Facade_Backing, Back_Plate. swatch_paths: facade_swatch.build() result.
    The section tops of the shell move into Mountain and the back plate into Facade_Backing, so the
    halls (InteriorStone atlas, lit as the interior) and everything seen from outside (RockStone
    atlas: rock, section plane, facade backing) are two objects groups with one atlas each.
    Returns a report dict."""
    os.makedirs(texdir, exist_ok=True)
    report = {}
    sw = {}
    for k in ("Stone", "Rock", "Cut"):
        path, tile = swatch_paths[k]
        img = bpy.data.images.load(path); img.name = "Swatch_" + k
        sw[k] = (img, tile)
    depth, edge = _relief_maps()
    relief_imgs = (_image_from_array("Relief_Depth", depth, os.path.join(texdir, "Relief_Depth.png")),
                   _image_from_array("Relief_Edge", edge, os.path.join(texdir, "Relief_Edge.png")))
    hall = (x0, 0.62, sill, hall_height)
    band = (x0, 0.03)
    mats = {f"stone_{a}": make_surface_material(f"Stone_{a}", "stone", a, sw) for a in "XYZ"}
    mats["relief"] = make_surface_material("Relief_Y", "relief", "Y", sw, relief_imgs, hall)
    mats["rock_X"] = make_surface_material("Rock_X", "rock", "X", sw, band=band)
    mats["rock_Y"] = make_surface_material("Rock_Y", "rock", "Y", sw, band=band)
    mats["cut"] = make_surface_material("Cut_Z", "cut", "Z", sw)
    allobjs = list(interior.values()) + list(rock.values())
    report["face_roles"] = {o.name: assign_roles(o, cy, x0, xe, in1, floor_z, sill, mats, h_cut, True) for o in allobjs}
    log("surface roles", report["face_roles"])
    cut_idx = list(mats.keys()).index("cut")
    shell = interior["Interior_Shell"]
    report["section_faces_moved"] = merge_faces(shell, rock["Mountain"], lambda f: f.material_index == cut_idx)
    report["back_plate_faces_moved"] = merge_faces(rock.pop("Back_Plate"), rock["Facade_Backing"])
    log("regrouped", report["section_faces_moved"], report["back_plate_faces_moved"])

    scene.render.engine = "CYCLES"; scene.cycles.device = "CPU"
    world = scene.world or bpy.data.worlds.new("BakeSky"); scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (1, 1, 1, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    world.light_settings.distance = 0.06
    bake = scene.render.bake
    bake.use_selected_to_active = False; bake.margin = 6; bake.use_clear = True
    bake.target = "IMAGE_TEXTURES"
    lights_hidden = [o for o in scene.objects if o.type == "LIGHT" and not o.hide_render]
    for o in lights_hidden: o.hide_render = True

    # the halls grow calmer toward the sanctuary (it stays the calmest part until the sun arrives)
    xs0, xs1 = x0 + 0.62, xe - 0.06
    def calm(x):
        t = np.clip((x - xs0) / (xs1 - xs0), 0, 1)
        return 1.0 - 0.18 * t * t * (3 - 2 * t)
    groups = (("InteriorStone", list(interior.values()), calm, None), ("RockStone", list(rock.values()), None, h_cut))
    report["atlases"] = {}
    for name, objs, cf, sz in groups:
        final, rep = _bake_group(scene, objs, name, texdir, log, cf, sz)
        for o in objs:
            o.data.materials.clear(); o.data.materials.append(final)
            for pl in o.data.polygons: pl.material_index = 0
        report["atlases"][name] = rep
        log("atlas", name, rep)
    for o in lights_hidden: o.hide_render = False
    for m in mats.values(): bpy.data.materials.remove(m)
    for img in list(relief_imgs) + [v[0] for v in sw.values()]: bpy.data.images.remove(img)
    report["swatch_tile_m"] = round(sw["Stone"][1], 4)
    return report
