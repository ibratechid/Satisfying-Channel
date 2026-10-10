"""Konfigurasi global. Semua bisa di-override lewat environment variable."""
import os

CHANNEL = "Satisfying Relaxation"

FPS = int(os.environ.get("SR_FPS", "30"))
DURATION = float(os.environ.get("SR_MINUTES", "8")) * 60.0   # detik
OUT_H = int(os.environ.get("SR_HEIGHT", "1080"))             # 720 / 1080 / 1440
OUT_W = OUT_H * 16 // 9
SEED = int(os.environ.get("SR_SEED", "7"))                   # ubah seed -> warna & nada beda

# Canvas internal (di-upscale ke OUT_W x OUT_H -> glow lebih halus & render jauh lebih cepat)
W, H = 960, 540

N_SCENES = 4
SCENE_LEN = DURATION / N_SCENES
XFADE = min(3.0, SCENE_LEN / 3)
