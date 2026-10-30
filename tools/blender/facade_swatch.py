"""Stone and rock swatches sampled from the Meshy facade's own texture (imported by 02_build_hybrid_temple.py).

The rear of the temple (halls, rock mass, section tops, facade backing) must read as the same stone
as the photographic Meshy facade, so its albedo is built from the facade texture itself, not from
procedural colour:

  1. render the untouched facade flat (Workbench, texture colour, no lighting) in orthographic
     views: the front for dressed stone, the two cliff ends for rough rock. This turns Meshy's
     fragmented UV atlas into world-coherent images at a known texel density.
  2. keep only plain-stone pixels: inside the silhouette, low mid-scale structure (no colossi,
     no carving edges), not streaky (no grazing-angle smear), not deep shadow or highlight.
  3. flatten the low-frequency shading Meshy baked into the texture, so patches from different
     places join without a mosaic of light and dark chips.
  4. quilt random patches into a seamless (toroidal) swatch, choosing each patch by how well it
     matches its neighbours' overlap, with a short feathered seam.

No AI generation: every pixel comes from the existing Meshy facade texture. Works in sRGB values.
"""
import bpy, math, os
import numpy as np
from mathutils import Vector

SWATCH = 1024


def _box(a, r):
    """Box blur with radius r (wrap-free, edge clamped), 2D or 3D array."""
    if r < 1: return a
    pad = [(r + 1, r)] + [(r + 1, r)] + [(0, 0)] * (a.ndim - 2)
    c = np.pad(a, pad, mode="edge").cumsum(0).cumsum(1)
    k = 2 * r + 1
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


def _box_wrap(a, r):
    if r < 1: return a
    pad = [(r + 1, r)] + [(r + 1, r)] + [(0, 0)] * (a.ndim - 2)
    c = np.pad(a, pad, mode="wrap").cumsum(0).cumsum(1)
    k = 2 * r + 1
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


def _lum(rgb):
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def render_views(scene, facade, outdir, width=4096, log=print):
    """Flat texture-colour renders of the facade. Returns {view: (rgba float array, px_per_m)}."""
    os.makedirs(outdir, exist_ok=True)
    mat = facade.data.materials[0]
    for nd in mat.node_tree.nodes:                     # Workbench shows the active image node
        if nd.type == "TEX_IMAGE" and nd.image and any(l.to_socket.name == "Base Color" for l in nd.outputs[0].links):
            mat.node_tree.nodes.active = nd
    co = np.array([v.co for v in facade.data.vertices]); lo, hi = co.min(0), co.max(0); c = (lo + hi) / 2
    prev = (scene.render.engine, scene.camera, scene.render.resolution_x, scene.render.resolution_y, scene.render.film_transparent)
    scene.render.engine = "BLENDER_WORKBENCH"
    sh = scene.display.shading
    sh.light = "FLAT"; sh.color_type = "TEXTURE"; sh.show_cavity = False; sh.show_shadows = False
    sh.show_specular_highlight = False; sh.show_xray = False
    scene.display.render_aa = "8"
    scene.view_settings.view_transform = "Standard"; scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0; scene.view_settings.gamma = 1.0
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"; scene.render.image_settings.color_mode = "RGBA"
    # the cliff ends: only the outer 22% of the facade width at each side (the rock, not the colossi)
    views = {
        "front": (Vector((lo[0] - 1.0, c[1], c[2])), Vector((1, 0, 0)), hi[1] - lo[1], hi[2] - lo[2]),
        "side_pos": (Vector((c[0], hi[1] + 1.0, c[2])), Vector((0, -1, 0)), hi[0] - lo[0], hi[2] - lo[2]),
        "side_neg": (Vector((c[0], lo[1] - 1.0, c[2])), Vector((0, 1, 0)), hi[0] - lo[0], hi[2] - lo[2]),
    }
    out = {}
    ppm = width / float(max(views["front"][2], views["front"][3]))
    for name, (loc, fwd, w_m, h_m) in views.items():
        width = int(round(ppm * max(w_m, h_m)))
        cd = bpy.data.cameras.new("swatch_" + name); cd.type = "ORTHO"; cd.ortho_scale = float(max(w_m, h_m))
        cd.clip_start = 0.01; cd.clip_end = 5.0
        cam = bpy.data.objects.new("swatch_" + name, cd); scene.collection.objects.link(cam)
        cam.location = loc; cam.rotation_euler = fwd.to_track_quat("-Z", "Y").to_euler()
        scene.camera = cam
        rx = width; ry = int(round(width * h_m / w_m)) if w_m >= h_m else width
        if h_m > w_m: rx = int(round(width * w_m / h_m))
        scene.render.resolution_x, scene.render.resolution_y = rx, ry; scene.render.resolution_percentage = 100
        path = os.path.join(outdir, "facade_flat_%s.png" % name)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(path)
        a = np.empty(rx * ry * 4, dtype=np.float32); img.pixels.foreach_get(a)
        a = a.reshape(ry, rx, 4)[::-1].copy()        # top row first
        bpy.data.images.remove(img)
        out[name] = (a, rx / float(max(w_m, h_m)) if w_m >= h_m else ry / float(h_m))
        bpy.data.objects.remove(cam); bpy.data.cameras.remove(cd)
        log("swatch view", name, (rx, ry), "px/m %.0f" % out[name][1])
    scene.render.engine, scene.camera, scene.render.resolution_x, scene.render.resolution_y, scene.render.film_transparent = prev
    return out


def plain_mask(rgba, patch, x_keep=None, edge_pct=45, coh_max=0.55, grain_pct=10):
    """Pixels where a whole patch of plain stone fits. x_keep: (lo, hi) fraction band of columns kept."""
    rgb, alpha = rgba[..., :3], rgba[..., 3]
    L = _lum(rgb)
    inside = alpha > 0.99
    hp = L - _box(L, 4)
    structure = np.sqrt(np.maximum(_box(hp * hp, 12), 0))                    # fine grain energy
    mid = _box(L, 3) - _box(L, 24)
    mid_e = np.sqrt(np.maximum(_box(mid * mid, 24), 0))                      # carving edges, faces, joints
    gx = np.zeros_like(L); gy = np.zeros_like(L)
    gx[:, 1:-1] = L[:, 2:] - L[:, :-2]; gy[1:-1] = L[2:] - L[:-2]
    jxx, jyy, jxy = _box(gx * gx, 10), _box(gy * gy, 10), _box(gx * gy, 10)
    coh = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4 * jxy ** 2, 0)) / (jxx + jyy + 1e-6)   # 1 = streaks in one direction
    ok = inside.copy()
    v = L[inside]
    Ls = _box(L, 6)
    ok &= (Ls > np.percentile(v, 4)) & (Ls < np.percentile(v, 97))
    ok &= mid_e < np.percentile(mid_e[inside], edge_pct)
    ok &= coh < coh_max
    ok &= structure > np.percentile(structure[inside], grain_pct)     # not a smeared, featureless area
    if x_keep is not None:
        w = ok.shape[1]; cols = np.zeros(w, bool); cols[int(x_keep[0] * w):int(x_keep[1] * w)] = True
        ok &= cols[None, :]
    if os.environ.get("SWATCH_DEBUG"):
        print("mask", inside.mean(), ok.mean(), (mid_e < np.percentile(mid_e[inside], 45)).mean(), (coh < 0.55).mean())
    # whole patch must be ok: erode by a box test
    frac = _box(ok.astype(np.float32), patch // 2)
    return frac > 0.92


def flatten(rgb, alpha, r=40, keep=0.6):
    """Remove the low-frequency shading Meshy baked in, keeping `keep` of it, around the mean."""
    L = _lum(rgb)
    inside = (alpha > 0.5).astype(np.float32)
    lowL = _box(L * inside, r) / np.maximum(_box(inside, r), 1e-3)
    mean = float(L[alpha > 0.99].mean())
    gain = (mean / np.maximum(lowL, 1e-3)) ** (1.0 - keep)
    return np.clip(rgb * gain[..., None], 0, 1)


def quilt(sources, size=SWATCH, patch=128, overlap=32, seed=1, log=print, label="swatch"):
    """sources: list of (rgb, ok_mask). Seamless toroidal swatch of size x size."""
    rng = np.random.default_rng(seed)
    step = patch - overlap
    n = size // step
    size = n * step
    cands = []
    for si, (rgb, ok) in enumerate(sources):
        ys, xs = np.nonzero(ok)
        cands.append((rgb, ys, xs))
    total = sum(len(c[1]) for c in cands)
    if total == 0:
        raise RuntimeError("no plain-stone patches found for " + label)
    acc = np.zeros((size, size, 3)); wsum = np.zeros((size, size))
    ramp = np.ones(patch)
    t = np.linspace(0, 1, overlap + 2)[1:-1]
    ramp[:overlap] = t * t * (3 - 2 * t); ramp[-overlap:] = ramp[:overlap][::-1]
    win = np.outer(ramp, ramp)
    order = [(i, j) for i in range(n) for j in range(n)]
    for (i, j) in order:
        y0, x0 = i * step, j * step
        yy = (np.arange(patch) + y0 - overlap // 2) % size
        xx = (np.arange(patch) + x0 - overlap // 2) % size
        cur = acc[np.ix_(yy, xx)] / np.maximum(wsum[np.ix_(yy, xx)], 1e-6)[..., None]
        have = wsum[np.ix_(yy, xx)] > 1e-3
        best = None
        for k in range(24):
            r = rng.integers(total)
            for rgb, ys, xs in cands:
                if r < len(ys): break
                r -= len(ys)
            cy_, cx_ = ys[r], xs[r]
            p = rgb[cy_ - patch // 2: cy_ - patch // 2 + patch, cx_ - patch // 2: cx_ - patch // 2 + patch]
            if p.shape[:2] != (patch, patch): continue
            if rng.random() < 0.5: p = p[:, ::-1]
            cost = float(((p - cur) ** 2)[have].sum()) / max(int(have.sum()), 1) if have.any() else rng.random()
            if best is None or cost < best[0]: best = (cost, p)
        acc[np.ix_(yy, xx)] += best[1] * win[..., None]
        wsum[np.ix_(yy, xx)] += win
    out = acc / np.maximum(wsum, 1e-6)[..., None]
    log(label, "quilted", size, "from", total, "candidate centres")
    return out


def save_png(arr, path):
    h, w = arr.shape[:2]
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=False, float_buffer=False)
    px = np.ones((h, w, 4), dtype=np.float32); px[..., :3] = arr[::-1]
    img.pixels.foreach_set(px.ravel()); img.filepath_raw = path; img.file_format = "PNG"; img.save()
    bpy.data.images.remove(img)
    return path


def build(scene, facade, outdir, log=print):
    """Writes Swatch_Stone.png, Swatch_Rock.png, Swatch_Cut.png (sRGB, seamless) into outdir and
    returns {name: (path, tile_size_m)} plus statistics."""
    views = render_views(scene, facade, os.path.join(outdir, "flat"), log=log)
    patch = 128
    res = {}
    fr, ppm = views["front"]
    front = flatten(fr[..., :3], fr[..., 3])
    ok_front = plain_mask(fr, patch, edge_pct=60)
    rock_src = []
    for nm in ("side_pos", "side_neg"):
        sv, _ = views[nm]
        rock_src.append((flatten(sv[..., :3], sv[..., 3], keep=0.45), plain_mask(sv, patch, edge_pct=90, coh_max=0.7, grain_pct=55)))
    # the front's own cliff ends are rock too
    rock_src.append((front, plain_mask(fr, patch, (0.0, 0.16), 85, 0.7) | plain_mask(fr, patch, (0.84, 1.0), 85, 0.7)))
    stone = quilt([(front, ok_front)], patch=patch, seed=3, log=log, label="stone")
    rock = quilt(rock_src, patch=patch, seed=5, log=log, label="rock")
    # cut stone: the same stone, sawn smooth (fine grain softened, colour kept)
    cut = 0.55 * _box_wrap(stone, 2) + 0.45 * _box_wrap(stone, 6)
    tile = stone.shape[0] / ppm
    for nm, arr in (("Stone", stone), ("Rock", rock), ("Cut", cut)):
        res[nm] = (save_png(arr, os.path.join(outdir, "Swatch_%s.png" % nm)), tile)
    res["stats"] = {"px_per_m": round(ppm, 1), "tile_m": round(tile, 4),
                    "stone_mean_srgb": [round(float(v), 3) for v in stone.reshape(-1, 3).mean(0)],
                    "rock_mean_srgb": [round(float(v), 3) for v in rock.reshape(-1, 3).mean(0)],
                    "front_plain_px": int(ok_front.sum()), "rock_plain_px": int(sum(m.sum() for _, m in rock_src))}
    log("swatches", res["stats"])
    return res
