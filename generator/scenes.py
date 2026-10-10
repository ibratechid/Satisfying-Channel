"""Scene procedural bertema 'satisfying'.

Setiap scene adalah fungsi MURNI dari waktu (detik) -> PIL.Image (W x H).
Karena murni, frame bisa dirender paralel di banyak proses tanpa state bersama.
"""
import colorsys
import functools
import math

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from . import config as C

W, H = C.W, C.H
TAU = math.tau
HUE0 = (C.SEED * 0.1618) % 1.0


# ----------------------------------------------------------------- helpers
def hsv(h, s=0.55, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def dim(c, k):
    return tuple(int(x * k) for x in c)


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


@functools.lru_cache(maxsize=None)
def _lut(k):
    return [min(255, int(i * k)) for i in range(256)] * 3


@functools.lru_cache(maxsize=None)
def _gradient(top, bottom, vignette=0.45):
    t = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    img = np.array(top, np.float32) * (1 - t) + np.array(bottom, np.float32) * t
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    v = 1 - vignette * np.clip(d - 0.35, 0, 1) ** 1.5
    return np.clip(img * v[..., None], 0, 255).astype(np.uint8)


def bg(top, bottom):
    return Image.fromarray(_gradient(top, bottom)).copy()


def composite(base, layer):
    """Tambah layer + glow berlapis (bloom murah)."""
    out = ImageChops.add(base, layer)
    out = ImageChops.add(out, layer.filter(ImageFilter.GaussianBlur(5)).point(_lut(1.0)))
    out = ImageChops.add(out, layer.filter(ImageFilter.GaussianBlur(18)).point(_lut(1.2)))
    return out


# ------------------------------------------------- scene 1: sunset waves
_X = np.linspace(0, 1, W, dtype=np.float32)[None, :]
_Y = np.arange(H, dtype=np.float32)[:, None]
_YY, _XX = np.mgrid[0:H, 0:W].astype(np.float32)
_SUN_D = np.sqrt((_XX - W * 0.5) ** 2 + (_YY - H * 0.40) ** 2)

# (base_y, amp, freq, speed, phase, warna_atas, warna_bawah)
_WAVES = [
    (0.53, 7, 1.6, 0.55, 0.0, (255, 196, 170), (226, 140, 170)),
    (0.58, 9, 1.2, -0.48, 1.3, (238, 150, 170), (180, 100, 160)),
    (0.64, 11, 1.0, 0.44, 2.1, (190, 110, 170), (120, 80, 160)),
    (0.71, 13, 0.8, -0.36, 3.4, (120, 86, 170), (70, 60, 140)),
    (0.79, 15, 0.65, 0.30, 4.2, (70, 64, 150), (36, 40, 110)),
    (0.88, 17, 0.5, -0.24, 5.0, (36, 44, 120), (16, 22, 70)),
]
_F32 = np.float32


@functools.lru_cache(maxsize=None)
def _sky():
    top, bot = np.array((22, 20, 70), _F32), np.array((250, 160, 150), _F32)
    t = np.linspace(0, 1, H, dtype=_F32)[:, None, None] ** 1.4
    return np.broadcast_to(top * (1 - t) + bot * t, (H, W, 3)).copy()


def scene_waves(s):
    img = _sky().copy()
    pulse = 1 + 0.04 * math.sin(s * 0.5)
    d2 = _SUN_D ** 2
    halo = np.exp(-d2 / (2 * (60 * pulse) ** 2))[..., None] * np.array([255, 180, 120], _F32) * 0.75
    halo2 = np.exp(-d2 / (2 * (190 * pulse) ** 2))[..., None] * np.array([140, 70, 100], _F32) * 0.6
    disk = np.clip((44 - _SUN_D) / 2.0, 0, 1)[..., None]
    img = img + halo + halo2
    img = img * (1 - disk) + disk * np.array([255, 236, 205], _F32)

    for base, amp, freq, speed, ph, ctop, cbot in _WAVES:
        edge = (base * H + amp * np.sin(TAU * freq * _X + speed * s + ph)
                + 0.4 * amp * np.sin(TAU * freq * 2.7 * _X - 1.3 * speed * s + ph * 2))
        mask = np.clip((_Y - edge) / 2.5 + 0.5, 0, 1)
        depth = np.clip((_Y - edge) / (H * 0.5), 0, 1)[..., None]
        col = np.array(ctop, _F32) * (1 - depth) + np.array(cbot, _F32) * depth
        img = img * (1 - mask[..., None]) + col * mask[..., None]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


# ------------------------------------------------ scene 2: pendulum wave
PEND_N = 21


def scene_pendulum(s):
    base = bg((8, 10, 32), (34, 14, 58))
    layer = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(layer)
    cy, amp = H * 0.5, H * 0.30
    xs = [W * (0.09 + 0.82 * i / (PEND_N - 1)) for i in range(PEND_N)]
    cols = [hsv(HUE0 + 0.5 + 0.55 * i / (PEND_N - 1), 0.5, 1.0) for i in range(PEND_N)]

    def y(i, t):  # siklus penuh 60 detik: bola ke-i selesai (30+i) osilasi -> pola menyatu lagi
        return cy + amp * math.sin(TAU * (30 + i) * t / 60.0)

    d.line([(W * 0.05, cy), (W * 0.95, cy)], fill=(40, 44, 80), width=1)
    d.line([(xs[i], y(i, s)) for i in range(PEND_N)], fill=(80, 90, 160), width=2, joint="curve")
    for i in range(PEND_N):
        for k in range(12, 0, -1):                       # jejak (trail)
            yy = y(i, s - k * 0.02)
            a, r = (1 - k / 13) ** 2 * 0.6, 11 * (1 - k * 0.025)
            d.ellipse((xs[i] - r, yy - r, xs[i] + r, yy + r), fill=dim(cols[i], a))
        yy = y(i, s)
        d.ellipse((xs[i] - 11, yy - 11, xs[i] + 11, yy + 11), fill=cols[i])
    return composite(base, layer)


# ----------------------------------------------- scene 3: bouncing orbs
BOUNCE_N = 7


def _bp(i):
    return 2.2 + 0.28 * i, 0.43 * i      # (periode, fase)


def bounce_impacts(i, s0, s1):
    """Waktu (lokal scene) saat orb ke-i menyentuh lantai. Dipakai juga oleh audio."""
    p, ph = _bp(i)
    t = ph + math.ceil((s0 - ph) / p) * p
    out = []
    while t < s1:
        out.append(t)
        t += p
    return out


def scene_bounce(s):
    base = bg((10, 10, 30), (38, 18, 62))
    layer = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(layer)
    floor = H * 0.78
    d.line([(W * 0.06, floor), (W * 0.94, floor)], fill=(70, 64, 130), width=2)
    pmax = _bp(BOUNCE_N - 1)[0]
    for i in range(BOUNCE_N):
        p, ph = _bp(i)
        x = W * (0.13 + 0.74 * i / (BOUNCE_N - 1))
        col = hsv(HUE0 + 0.08 + 0.72 * i / (BOUNCE_N - 1), 0.5, 1.0)
        u = ((s - ph) / p) % 1.0
        age = u * p
        hmax = floor * 0.80 * (p / pmax) ** 2
        r = 13
        for echo in (0.0, 0.38):                          # ring riak air
            a = age - echo
            if 0 <= a < 2.6:
                f, rad = (1 - a / 2.6) ** 1.6, r + a * 90
                d.ellipse((x - rad, floor - rad * 0.2, x + rad, floor + rad * 0.2),
                          outline=dim(col, f * 0.9), width=2)
        sq = max(0.0, 1 - age / 0.09)                     # squash saat mendarat
        rx, ry = r * (1 + 0.45 * sq), r * (1 - 0.4 * sq)
        yc = floor - ry - hmax * 4 * u * (1 - u)
        yr = floor + (floor - yc)                         # pantulan
        d.ellipse((x - rx, yr - ry, x + rx, yr + ry), fill=dim(col, 0.2))
        d.ellipse((x - rx, yc - ry, x + rx, yc + ry), fill=col)
    return composite(base, layer)


# --------------------------------------------- scene 4: glowing spirograph
_TH = np.linspace(0, TAU * 7, 1600)


def scene_spiro(s):
    base = bg((6, 6, 22), (24, 10, 40))
    layer = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(layer)
    R, r = 1.0, 7 / 20
    k = (R - r) / r
    for j, (dfac, rot, sc, hoff) in enumerate(((1.0, 0.05, 1.0, 0.0), (0.62, -0.07, 0.72, 0.35))):
        dd = r * (1.15 + 0.75 * math.sin(s * 0.11 + j * 1.7)) * dfac
        x = (R - r) * np.cos(_TH) + dd * np.cos(k * _TH)
        y = (R - r) * np.sin(_TH) - dd * np.sin(k * _TH)
        a = s * rot
        xr, yr = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
        scl = H * 0.40 * sc / (R - r + dd)
        pts = np.stack([W / 2 + xr * scl, H / 2 + yr * scl], 1)
        n, chunks = len(pts), 16
        for c in range(chunks):
            seg = pts[c * n // chunks: min(n, (c + 1) * n // chunks + 1)]
            col = hsv(HUE0 + hoff + s * 0.012 + c / chunks * 0.35, 0.55, 1.0)
            d.line(list(map(tuple, seg.tolist())), fill=dim(col, 0.9), width=2)
    return composite(base, layer)


SCENES = [
    ("Sunset Waves", scene_waves),
    ("Pendulum Wave", scene_pendulum),
    ("Bouncing Orbs", scene_bounce),
    ("Glowing Spirograph", scene_spiro),
]


# ------------------------------------------------------- frame assembly
def lowres(s):
    L, n = C.SCENE_LEN, len(SCENES)
    idx = min(int(s // L), n - 1)
    local = s - idx * L
    img = SCENES[idx][1](local)
    if idx < n - 1 and local > L - C.XFADE:                 # crossfade antar scene
        a = smooth((local - (L - C.XFADE)) / C.XFADE)
        img = Image.blend(img, SCENES[idx + 1][1](local - L), a)
    return img


@functools.lru_cache(maxsize=None)
def _noise():
    rng = np.random.default_rng(1)
    return rng.normal(0, 1.2, (4, H, W, 1)).astype(np.float32)   # dither anti-banding


def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf",
              "/Library/Fonts/Arial Bold.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default(size)


def draw_tracked(d, cx, cy, text, fnt, fill, tracking, shadow=True):
    widths = [fnt.getlength(ch) for ch in text]
    x = cx - (sum(widths) + tracking * (len(text) - 1)) / 2
    for ch, w in zip(text, widths):
        if shadow:
            d.text((x + 3, cy + 3), ch, font=fnt, fill=(0, 0, 0, 120), anchor="lm")
        d.text((x, cy), ch, font=fnt, fill=fill, anchor="lm")
        x += w + tracking


@functools.lru_cache(maxsize=None)
def _title_overlay():
    ov = Image.new("RGBA", (C.OUT_W, C.OUT_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    draw_tracked(d, C.OUT_W / 2, C.OUT_H * 0.46, "SATISFYING RELAXATION", font(C.OUT_H // 11),
                 (255, 255, 255, 255), C.OUT_H // 60)
    draw_tracked(d, C.OUT_W / 2, C.OUT_H * 0.56, f"{int(C.DURATION // 60)} MINUTES OF CALM",
                 font(C.OUT_H // 30), (255, 255, 255, 200), C.OUT_H // 90)
    return ov


def title_alpha(s):
    return smooth((s - 1.5) / 2.0) * (1 - smooth((s - 8.0) / 2.5))


def render_frame(f):
    s = f / C.FPS
    img = lowres(s)
    fade = smooth(s / 2.0) * smooth((C.DURATION - s) / 3.0)
    arr = (np.asarray(img, dtype=np.float32) + _noise()[f % 4]) * fade
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    out = out.resize((C.OUT_W, C.OUT_H), Image.Resampling.BICUBIC)
    a = title_alpha(s)
    if a > 0.003:
        ov = _title_overlay()
        layer = ov.copy()
        layer.putalpha(ov.getchannel("A").point([int(i * a) for i in range(256)]))
        out = Image.alpha_composite(out.convert("RGBA"), layer).convert("RGB")
    return out
