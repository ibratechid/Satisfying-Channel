"""Orkestrator render:  audio -> video (paralel per-chunk via ffmpeg) -> concat + mux -> thumbnail.

Jalankan:  python -m generator.render --out out
"""
import argparse
import os
import subprocess
import sys
import time
from multiprocessing import Pool

from PIL import Image, ImageDraw

from . import audio, metadata, scenes
from . import config as C


def render_chunk(job):
    idx, f0, f1, path, preset, crf = job
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{C.OUT_W}x{C.OUT_H}", "-r", str(C.FPS), "-i", "-",
        "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-threads", "2",
        "-maxrate", "14M", "-bufsize", "28M",
        "-g", str(C.FPS * 2), "-keyint_min", str(C.FPS * 2), "-sc_threshold", "0",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-r", str(C.FPS), path,
    ]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for f in range(f0, f1):
            p.stdin.write(scenes.render_frame(f).tobytes())
    finally:
        p.stdin.close()
        rc = p.wait()
    if rc != 0:
        raise RuntimeError(f"ffmpeg chunk {idx} gagal (rc={rc})")
    return idx, f1 - f0


def make_thumbnail(path):
    img = scenes.SCENES[0][1](20.0).resize((1280, 720), Image.Resampling.BICUBIC).convert("RGBA")
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rectangle((0, 250, 1280, 490), fill=(0, 0, 0, 90))
    scenes.draw_tracked(d, 640, 335, "SATISFYING", scenes.font(110), (255, 255, 255, 255), 14)
    scenes.draw_tracked(d, 640, 445, f"RELAXATION  ·  {int(C.DURATION // 60)} MIN", scenes.font(64),
                        (255, 220, 200, 255), 10)
    Image.alpha_composite(img, ov).convert("RGB").save(path, quality=92)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--crf", type=int, default=18)
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    seg_dir = os.path.join(a.out, "segments")
    os.makedirs(seg_dir, exist_ok=True)
    total = int(C.DURATION * C.FPS)
    t_start = time.time()
    print(f"[info] {C.OUT_W}x{C.OUT_H}@{C.FPS}  {C.DURATION:.0f}s  {total} frame  {a.workers} worker", flush=True)

    wav = os.path.join(a.out, "audio.wav")
    print("[1/4] sintesis audio ...", flush=True)
    audio.generate(wav)
    print(f"      selesai {time.time() - t_start:.0f}s", flush=True)

    print("[2/4] render video paralel ...", flush=True)
    chunk = C.FPS * 15
    jobs = [(i, f0, min(total, f0 + chunk), os.path.join(seg_dir, f"seg_{i:04d}.mp4"), a.preset, a.crf)
            for i, f0 in enumerate(range(0, total, chunk))]
    done = 0
    with Pool(a.workers) as pool:
        for _, n in pool.imap_unordered(render_chunk, jobs):
            done += n
            el = time.time() - t_start
            print(f"      {done}/{total} frame ({done / total:.0%})  elapsed {el:.0f}s", flush=True)

    print("[3/4] concat + mux audio ...", flush=True)
    lst = os.path.join(seg_dir, "list.txt")
    with open(lst, "w") as fh:
        for j in jobs:
            fh.write(f"file '{os.path.abspath(j[3])}'\n")
    video = os.path.join(a.out, "satisfying-relaxation.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav,
        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
        "-movflags", "+faststart", "-metadata", f"title={C.CHANNEL}", "-metadata", f"artist={C.CHANNEL}",
        video], check=True)

    print("[4/4] thumbnail + metadata ...", flush=True)
    make_thumbnail(os.path.join(a.out, "thumbnail.jpg"))
    metadata.write(os.path.join(a.out, "metadata.json"))

    for f in os.listdir(seg_dir):
        os.remove(os.path.join(seg_dir, f))
    os.rmdir(seg_dir)
    os.remove(wav)
    size = os.path.getsize(video) / 1e6
    print(f"[done] {video}  {size:.0f} MB  total {time.time() - t_start:.0f}s", flush=True)


if __name__ == "__main__":
    sys.exit(main())
