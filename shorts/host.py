"""The on-screen host: one still character brought to life the way PNGtubers do it.

Each host is a base image plus a few masked edits of it (mouth closed / small / wide, eyes closed). Per video frame
we pick the mouth shape from how loud the narration is at that moment, blink every few seconds, and move the whole
character (sway, breathing, a lean and bounce on loud words) so it never sits still. Runs on CPU; no GPU or paid
avatar service. The output is a video of the bottom part of the screen that render.py lays under the photo.
"""
import json
import math
import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

ASSETS = Path(__file__).parent / "assets" / "hosts"
FPS = 30
WIDTH, HEIGHT = 1080, 920  # the host's part of the 1080x1920 frame
FACE_Y = 300  # where the face centre sits inside that part

HOSTS = {
    "pigeon": {
        "face": (520, 770), "scale": 1.25,
        "voice": "verse",
        "instructions": (
            "A wisecracking cartoon Philadelphia pigeon hosting the sports news. Thick South Philly accent: 'water' "
            "is 'wooder', 'Eagles' leans toward 'Iggles', the Philly 'eh-oh' in 'go' and 'home', dropped g's. "
            "Slightly raspy and nasal, quick comic timing, big personality. Say the text exactly as written, clearly."),
    },
    "superfan": {
        "face": (525, 650), "scale": 1.2,
        "voice": "ash",
        "instructions": (
            "Born-and-raised South Philly superfan hosting a sports update. Strong, authentic Philadelphia accent: "
            "'wooder', 'Iggles', the Philly 'eh-oh' in 'go' and 'home', dropped g's on -ing words, clipped consonants. "
            "Fast, punchy sports-radio energy with a little attitude. Say the text exactly as written, clearly."),
    },
    "anchor": {
        "face": (500, 720), "scale": 1.15,
        "voice": "coral",
        "instructions": (
            "Philadelphia TV sports anchor who grew up in Delaware County. Polished, quick delivery with a noticeable "
            "Philly accent on vowels ('wooder', the Philly 'oh' in 'go' and 'home'), confident and warm. Say the text "
            "exactly as written."),
    },
}


def _loudness(audio: Path, frames: int) -> np.ndarray:
    """Per video frame loudness of the narration, 0..1."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(audio), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    hop = 16000 // FPS
    rms = np.array([np.sqrt(np.mean(pcm[i * hop:(i + 1) * hop] ** 2)) if i * hop < len(pcm) else 0.0
                    for i in range(frames)])
    peak = np.percentile(rms[rms > 0], 95) if (rms > 0).any() else 1.0
    return np.clip(rms / (peak or 1.0), 0, 1)


def _mouths(level: np.ndarray, rnd: random.Random) -> list[str]:
    """Mouth shape per frame. Holds each shape at least two frames so it reads as speech, not flicker."""
    out, held = [], 0
    for v in level:
        want = "closed" if v < 0.12 else "small" if v < 0.35 else ("base" if v < 0.7 else "wide")
        if want in ("base", "wide") and out and out[-1] == want and held >= 3:
            want = "small" if rnd.random() < 0.5 else ("wide" if want == "base" else "base")  # keep a steady vowel moving
        if out and want != out[-1] and held < 2:
            want = out[-1]
        held = held + 1 if out and want == out[-1] else 1
        out.append(want)
    return out


def _blinks(frames: int, rnd: random.Random) -> set[int]:
    shut, t = set(), rnd.uniform(1.0, 2.5)
    while t * FPS < frames:
        start = int(t * FPS)
        shut.update(range(start, start + 4))
        t += rnd.uniform(2.5, 5.5)
    return shut


def _poses(name: str) -> dict[tuple[str, bool], Image.Image]:
    """Every mouth/eye combination, pre-composited at render scale."""
    host, folder = HOSTS[name], ASSETS / name
    meta = json.loads((folder / "meta.json").read_text())
    base = Image.open(folder / "base.jpg").convert("RGBA")
    poses = {}
    for mouth in ("base", "closed", "small", "wide"):
        for blink in (False, True):
            im = base.copy()
            if mouth != "base":
                im.alpha_composite(Image.open(folder / f"{mouth}.png"), tuple(meta[mouth]))
            if blink:
                im.alpha_composite(Image.open(folder / "blink.png"), tuple(meta["blink"]))
            size = (round(im.width * host["scale"]), round(im.height * host["scale"]))
            poses[(mouth, blink)] = im.resize(size, Image.LANCZOS)
    return poses


def render_host(name: str, audio: Path, total: float, out: Path, seed: str = "") -> Path:
    """A WIDTH x HEIGHT video of the host talking over `audio` for `total` seconds."""
    host = HOSTS[name]
    rnd = random.Random(seed)
    frames = math.ceil(total * FPS)
    level = _loudness(audio, frames)
    smooth = np.convolve(level, np.ones(9) / 9, mode="same")  # slower envelope for body motion
    mouths, blinks = _mouths(level, rnd), _blinks(frames, rnd)
    poses = _poses(name)
    fx, fy = (c * host["scale"] for c in host["face"])
    phase = rnd.uniform(0, 6.28)
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS),
         "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(out)],
        stdin=subprocess.PIPE)
    bg = poses[("base", False)].getpixel((8, 8))
    for i in range(frames):
        t = i / FPS
        e = float(smooth[i])
        angle = 1.6 * math.sin(t * 2 * math.pi / 4.1 + phase) + 2.2 * e * math.sin(t * 1.3 + phase)
        dx = 10 * math.sin(t * 2 * math.pi / 3.3 + phase) + 6 * e * math.sin(t * 2.1)
        dy = 5 * math.sin(t * 2 * math.pi / 2.4) - 14 * e  # breathe, and rise on loud words
        zoom = 1 + 0.012 * math.sin(t * 2 * math.pi / 2.4) + 0.025 * e
        im = poses[(mouths[i], i in blinks)]
        # rotate/scale around the face, then cut the window that puts the face at (WIDTH/2, FACE_Y)
        moved = im.transform(im.size, Image.AFFINE, _affine(angle, zoom, fx, fy), resample=Image.BILINEAR,
                             fillcolor=bg)
        left, top = round(fx - WIDTH / 2 - dx), round(fy - FACE_Y - dy)
        frame = moved.crop((left, top, left + WIDTH, top + HEIGHT)).convert("RGB")
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError("host render failed")
    return out


def _affine(angle_deg: float, zoom: float, cx: float, cy: float) -> tuple:
    """Inverse affine (output -> input) for a rotation by angle and scale by zoom about (cx, cy)."""
    a = math.radians(angle_deg)
    cos, sin = math.cos(a) / zoom, math.sin(a) / zoom
    return (cos, sin, cx - cos * cx - sin * cy, -sin, cos, cy + sin * cx - cos * cy)
