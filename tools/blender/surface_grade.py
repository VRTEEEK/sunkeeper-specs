"""The ONE colour grade shared by the facade (03_optimise_export.py) and every rear texture
(interior_surfaces.py): warm sandy beige and muted ochre, with subtle reddish-brown variation.

grade(rgb) works on sRGB-encoded values in 0..1. The raw Meshy texture is a strong yellow ochre
(hue ~32 deg, saturation ~0.62), so the grade pulls saturation down, turns the hue slightly toward
red-brown and spreads the value range around a FIXED reference (REF_V), so every texture graded
with it lands in the same tonal range whatever its own average.
"""
import numpy as np

SAT_GAIN = 0.95
HUE_SHIFT_DEG = -2.0          # toward red-brown: less lemon, more sandstone
VALUE_CONTRAST = 1.25
VALUE_OFFSET = -0.08          # a touch deeper overall, never dark: the AO does the rest
REF_V = 0.78                  # value pivot (about the Meshy facade's mean HSV value), shared by all
AO_FLOOR = 0.45               # baked AO multiplier: base * (AO_FLOOR + (1 - AO_FLOOR) * ao^AO_GAMMA)
AO_GAMMA = 1.3


def srgb_to_lin(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def luminance(rgb):
    rgb = np.asarray(rgb)
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def _rgb_to_hsv(rgb):
    mx = rgb.max(axis=-1); mn = rgb.min(axis=-1); d = mx - mn
    s = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    dd = np.maximum(d, 1e-6)
    h = np.where(mx == r, ((g - b) / dd) % 6, np.where(mx == g, (b - r) / dd + 2, (r - g) / dd + 4)) / 6.0
    return np.where(d > 1e-6, h, 0), s, mx


def _hsv_to_rgb(h, s, v):
    i = np.floor(h * 6) % 6; f = h * 6 - np.floor(h * 6)
    p = v * (1 - s); q = v * (1 - s * f); t = v * (1 - s * (1 - f))
    r = np.choose(i.astype(int), [v, q, p, p, t, v])
    g = np.choose(i.astype(int), [t, v, v, q, p, p])
    b = np.choose(i.astype(int), [p, p, t, v, v, q])
    return np.stack([r, g, b], -1)


def grade(rgb, mean_v=REF_V):
    rgb = np.clip(np.asarray(rgb, dtype=np.float64), 0, 1)
    h, s, v = _rgb_to_hsv(rgb)
    v2 = np.clip(mean_v + (v - mean_v) * VALUE_CONTRAST + VALUE_OFFSET, 0, 1)
    s2 = np.clip(s * SAT_GAIN, 0, 1)
    h2 = (h + HUE_SHIFT_DEG / 360.0) % 1.0
    return np.clip(_hsv_to_rgb(h2, s2, v2), 0, 1)


def ao_factor(ao):
    return AO_FLOOR + (1 - AO_FLOOR) * np.power(np.clip(ao, 0, 1), AO_GAMMA)
