"""Metadata YouTube (judul, deskripsi + chapter, tag) -> metadata.json"""
import json

from . import config as C
from . import scenes


def _ts(sec):
    m, s = divmod(int(sec), 60)
    return f"{m:02d}:{s:02d}"


def build():
    mins = int(C.DURATION // 60)
    chapters = "\n".join(f"{_ts(i * C.SCENE_LEN)} {name}" for i, (name, _) in enumerate(scenes.SCENES))
    title = (f"{mins} Minutes of Satisfying Relaxation ✦ Calm Visuals & Ambient Sound "
             "| Sleep, Study, Stress Relief")[:100]
    desc = f"""{mins} minutes of soothing, satisfying motion with gentle ambient music. Let your mind slow down.

Perfect for: relaxing, studying, working, meditation, falling asleep, background ambience.

Chapters:
{chapters}

All visuals and audio are generated procedurally with code (no stock footage or third-party music).

Subscribe to {C.CHANNEL} for more calming loops.

#satisfying #relaxing #ambient #sleep #calm
"""
    tags = ["satisfying", "relaxing", "relaxation", "ambient", "calming", "sleep", "study music",
            "stress relief", "oddly satisfying", "meditation", "pendulum wave", "loop", C.CHANNEL.lower()]
    return {"title": title, "description": desc, "tags": tags, "categoryId": "22"}


def write(path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(build(), fh, ensure_ascii=False, indent=2)
