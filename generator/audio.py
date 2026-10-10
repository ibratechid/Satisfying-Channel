"""Sintesis audio 100% prosedural: pad ambient + ombak (noise) + bell pentatonik.

Bell pada scene "Bouncing Orbs" sinkron tepat dengan momen orb menyentuh lantai.
Tanpa file audio eksternal -> tidak ada masalah copyright.
"""
import wave

import numpy as np

from . import config as C
from . import scenes

SR = 44100
SCALE = [523.25, 587.33, 659.25, 783.99, 880.00, 1046.50, 1174.66]   # C pentatonik (C5..D6)

# Cmaj9 -> Am9 -> Fmaj7 -> G6/9 (progresi hangat & stabil)
CHORDS = [
    [65.41, 130.81, 196.00, 261.63, 329.63, 493.88],
    [55.00, 110.00, 164.81, 220.00, 261.63, 392.00],
    [43.65, 87.31, 130.81, 174.61, 220.00, 329.63],
    [49.00, 98.00, 146.83, 196.00, 246.94, 329.63],
]


def pad(n):
    out = np.zeros((2, n), np.float32)
    L, fade = 24.0, 6.0                       # tiap chord 24 dtk, crossfade 12 dtk (equal-power)
    k = 0
    while k * L < C.DURATION:
        t0, t1 = k * L - fade, (k + 1) * L + fade
        i0, i1 = max(0, int(t0 * SR)), min(n, int(t1 * SR))
        t = np.arange(i0, i1, dtype=np.float64) / SR
        w = (np.sin(np.pi / 2 * np.clip((t - t0) / (2 * fade), 0, 1))
             * np.cos(np.pi / 2 * np.clip((t - (t1 - 2 * fade)) / (2 * fade), 0, 1)))
        for f in CHORDS[k % len(CHORDS)]:
            lfo = 0.7 + 0.3 * np.sin(2 * np.pi * 0.07 * t + f)
            for ch, det in ((0, 0.998), (1, 1.002)):
                ph = 2 * np.pi * f * det * t
                voice = np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.08 * np.sin(3 * ph)
                out[ch, i0:i1] += (0.045 * w * lfo * voice).astype(np.float32)
        k += 1
    return out


def ocean(n, rng):
    spec = np.fft.rfft(rng.standard_normal(n).astype(np.float32))
    f = np.fft.rfftfreq(n, 1 / SR)
    spec *= (1 / np.sqrt(1 + (f / 350.0) ** 2)).astype(spec.real.dtype)
    x = np.fft.irfft(spec, n).astype(np.float32)
    x /= x.std() + 1e-9
    t = np.arange(n, dtype=np.float32) / SR
    swell = 0.3 + 0.7 * (0.5 + 0.5 * np.sin(2 * np.pi * t / 13.0 - 1.0)) ** 2
    left = x * swell * 0.11
    right = np.roll(x, 12345) * swell * 0.11
    return np.stack([left, right])


_BELLS = {}


def bell(freq):
    key = round(float(freq), 2)
    if key not in _BELLS:
        t = np.arange(int(4.5 * SR)) / SR
        tone = (np.sin(2 * np.pi * freq * t) * np.exp(-t * 1.4)
                + 0.35 * np.sin(2 * np.pi * 2.0 * freq * t) * np.exp(-t * 2.6)
                + 0.18 * np.sin(2 * np.pi * 3.01 * freq * t) * np.exp(-t * 4.2)
                + 0.08 * np.sin(2 * np.pi * 4.2 * freq * t) * np.exp(-t * 7.0))
        _BELLS[key] = (tone * (1 - np.exp(-t * 600))).astype(np.float32)
    return _BELLS[key]


def build_events(rng):
    ev, L = [], C.SCENE_LEN
    for idx, (name, _) in enumerate(scenes.SCENES):
        t0 = idx * L
        if name == "Bouncing Orbs":
            for i in range(scenes.BOUNCE_N):
                for t in scenes.bounce_impacts(i, -C.XFADE, L):
                    ev.append((t0 + t, SCALE[i], 0.75))
        else:
            t = t0 + rng.uniform(0, 2)
            while t < t0 + L:
                f = rng.choice(SCALE[:6]) * (0.5 if rng.random() < 0.25 else 1.0)
                ev.append((t, float(f), rng.uniform(0.25, 0.5)))
                t += rng.uniform(2.5, 6.5)
    return [e for e in ev if 0 <= e[0] < C.DURATION]


def bells(n, rng):
    out = np.zeros((2, n), np.float32)
    for t, freq, gain in build_events(rng):
        b = bell(freq) * gain * 0.22
        i0 = int(t * SR)
        i1 = min(n, i0 + len(b))
        pan = rng.uniform(-0.6, 0.6)
        ang = np.pi / 4 * (1 + pan)
        out[0, i0:i1] += b[: i1 - i0] * np.cos(ang)
        out[1, i0:i1] += b[: i1 - i0] * np.sin(ang)
    return out


def reverb(x):
    L, R = x[0], x[1]
    wl, wr = np.zeros_like(L), np.zeros_like(R)
    for dly, g in ((0.29, 0.35), (0.53, 0.26), (0.83, 0.19), (1.21, 0.13), (1.70, 0.08)):
        k = int(dly * SR)
        if k < len(L):
            wl[k:] += g * R[:-k]
            wr[k:] += g * L[:-k]
    return np.stack([L + wl, R + wr])


def generate(path):
    n = int(C.DURATION * SR)
    rng = np.random.default_rng(C.SEED)
    mix = pad(n) + ocean(n, rng) + reverb(bells(n, rng))
    t = np.arange(n, dtype=np.float32) / SR
    mix *= (np.clip(t / 3.0, 0, 1) * np.clip((C.DURATION - t) / 4.0, 0, 1))[None, :]
    mix = np.tanh(mix * 1.2)
    mix *= 0.89 / (np.abs(mix).max() + 1e-9)
    pcm = (mix.T * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path
