"""The on-screen host: one still character brought to life the way PNGtubers do it.

Each host is a base image plus a few masked edits of it (mouth closed / small / wide / "oo", eyes closed, brows raised
or drawn down). Per video frame we pick the mouth from the vowel being spoken (word timings from the narration) gated
by how loud it is, set the brows from the line's tone with a quick raise on names and numbers, blink every few
seconds, nod on stressed words and settle into a new head tilt at each sentence. Runs on CPU; no GPU or paid avatar
service. The output is a video of the bottom part of the screen that render.py lays under the photo.
"""
import json
import math
import os
import random
import re
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
        "elevenlabs_voice": os.environ.get("ELEVENLABS_VOICE_PIGEON"),
        "elevenlabs_tags": "[thick South Philadelphia accent] [wisecracking cartoon character]",
        "instructions": (
            "A wisecracking cartoon Philadelphia pigeon hosting the sports news. Thick South Philly accent: 'water' "
            "is 'wooder', 'Eagles' leans toward 'Iggles', the Philly 'eh-oh' in 'go' and 'home', dropped g's. "
            "Slightly raspy and nasal, quick comic timing, big personality. Say the text exactly as written, clearly."),
    },
    "superfan": {
        "face": (525, 650), "scale": 1.2,
        "voice": "ash",
        "elevenlabs_voice": os.environ.get("ELEVENLABS_VOICE_SUPERFAN"),
        "elevenlabs_tags": "[thick South Philadelphia accent] [fired up sports radio]",
        "instructions": (
            "Born-and-raised South Philly superfan hosting a sports update. Strong, authentic Philadelphia accent: "
            "'wooder', 'Iggles', the Philly 'eh-oh' in 'go' and 'home', dropped g's on -ing words, clipped consonants. "
            "Fast, punchy sports-radio energy with a little attitude. Say the text exactly as written, clearly."),
    },
    "anchor": {
        "face": (500, 720), "scale": 1.15,
        "voice": "coral",
        "elevenlabs_voice": os.environ.get("ELEVENLABS_VOICE_ANCHOR"),
        "elevenlabs_tags": "[Philadelphia accent] [confident TV sports anchor]",
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


_DOWN = re.compile(r"injur|\bout\b|\blos[est]|\bir\b|worse|problem|struggl|concern|miss|fined|suspend|torn|"
                   r"surgery|\bfell\b|\bfall|slump|blood clot|benched|cut\b|waive", re.I)
_UP = re.compile(r"\bwin|\bwon\b|return|\bback\b|huge|\bbig\b|signed|blowout|best|breakout|explod|statement|"
                 r"upset|\bwow\b|biggest|dominat", re.I)


def _tone(say: str) -> str | None:
    """Resting brows for a line: drawn down for bad news, up for good news or a question to the viewer."""
    if _DOWN.search(say):
        return "brows_down"
    if _UP.search(say) or say.rstrip().endswith("?"):
        return "brows_up"
    return None


def _vowel_mouth(word: str) -> list[str]:
    """Mouth shapes for a word's vowel sounds in order: only true "oo" sounds (oo, ou, u, ew) round the lips,
    e/i/y spread a little, a opens wide, a plain o is an open "oh"."""
    shapes = []
    for group in re.findall(r"[aeiou]+w?|y(?![aeiou])", word.lower()):
        if group in ("ou", "u", "ue", "ew", "ow", "uw") or group.startswith("oo"):
            shapes.append("oo")
        elif group[0] in "eiy":
            shapes.append("small")
        elif group[0] == "a":
            shapes.append("wide")
        else:
            shapes.append("base")
    return shapes or ["base"]


def _emphasis(word: str, first: bool) -> bool:
    """Numbers and names (capitalised mid-sentence) get a nod and a brow flash."""
    w = word.strip(".,!?;:'\"")
    return any(ch.isdigit() for ch in w) or (not first and w[:1].isupper() and len(w) > 2)


class _Poses:
    """Mouth / brows / blink combinations, composited at render scale on first use."""

    def __init__(self, name: str):
        self.host, self.folder = HOSTS[name], ASSETS / name
        self.meta = json.loads((self.folder / "meta.json").read_text())
        self.base = Image.open(self.folder / "base.jpg").convert("RGBA")
        self.layers = {k: Image.open(self.folder / f"{k}.png") for k in self.meta
                       if k not in ("mouth", "eyes") and (self.folder / f"{k}.png").exists()}
        self.cache: dict[tuple, Image.Image] = {}

    def has(self, layer: str) -> bool:
        return layer in self.layers

    def get(self, mouth: str, brows: str | None, blink: bool) -> Image.Image:
        key = (mouth, brows, blink)
        if key not in self.cache:
            im = self.base.copy()
            for layer in (brows, None if mouth == "base" else mouth, "blink" if blink else None):
                if layer and layer in self.layers:
                    im.alpha_composite(self.layers[layer], tuple(self.meta[layer]))
            size = (round(im.width * self.host["scale"]), round(im.height * self.host["scale"]))
            self.cache[key] = im.resize(size, Image.LANCZOS)
        return self.cache[key]


def _performance(timeline: list[dict], beats: list[dict], level: np.ndarray, frames: int, poses: _Poses,
                 rnd: random.Random) -> tuple[list[str], list[str | None], np.ndarray, np.ndarray]:
    """Per frame: mouth shape, brows, nod amount (0..1) and head tilt target in degrees."""
    mouths = ["closed"] * frames
    brows: list[str | None] = [None] * frames
    nod = np.zeros(frames)
    tilt = np.zeros(frames)
    flash_until = -1
    for b, beat in enumerate(timeline):
        start = round(beat["start"] * FPS)
        end = round((timeline[b + 1]["start"] if b + 1 < len(timeline) else beat["end"] + 0.6) * FPS)
        say = beats[b].get("say", "") if b < len(beats) else ""
        tone = _tone(say)
        tone = tone if tone and poses.has(tone) else None
        lean = rnd.uniform(-1.6, 1.6)
        for f in range(max(0, start), min(frames, end)):
            brows[f] = tone
            tilt[f] = lean
        for k, (word, ws, we) in enumerate(beat["words"]):
            f0, f1 = round(ws * FPS), max(round(ws * FPS) + 1, round(we * FPS))
            shapes = _vowel_mouth(word)
            span = max(1, (f1 - f0) / len(shapes))
            for f in range(f0, min(f1, frames)):
                shape = shapes[min(len(shapes) - 1, int((f - f0) / span))]
                if shape == "oo" and not poses.has("oo"):
                    shape = "small"
                if level[f] < 0.12:
                    shape = "closed"
                elif shape == "wide" and level[f] < 0.55:
                    shape = "base"
                mouths[f] = shape
            if _emphasis(word, k == 0) and f0 > flash_until:
                for f in range(f0, min(frames, f0 + 9)):  # a 0.3 s nod
                    nod[f] = max(nod[f], math.sin(math.pi * (f - f0) / 9))
                if tone != "brows_down" and poses.has("brows_up"):
                    for f in range(f0, min(frames, f0 + 12)):
                        brows[f] = "brows_up"
                flash_until = f0 + 45  # at most one emphasis every 1.5 s
    # hold each mouth at least two frames so it reads as speech, not flicker
    for f in range(1, frames - 1):
        if mouths[f] != mouths[f - 1] and mouths[f + 1] != mouths[f]:
            mouths[f] = mouths[f - 1]
    # ease the head tilt between sentences instead of snapping
    tilt = np.convolve(tilt, np.ones(13) / 13, mode="same")
    return mouths, brows, nod, tilt


def render_host(name: str, audio: Path, total: float, out: Path, seed: str = "", timeline: list[dict] | None = None,
                beats: list[dict] | None = None) -> Path:
    """A WIDTH x HEIGHT video of the host talking over `audio` for `total` seconds. With the narration timeline
    (word timings) and the script beats, the mouth follows the vowels and the face follows the lines; without them,
    the mouth follows loudness only."""
    host = HOSTS[name]
    rnd = random.Random(seed)
    frames = math.ceil(total * FPS)
    level = _loudness(audio, frames)
    smooth = np.convolve(level, np.ones(15) / 15, mode="same")  # slow envelope so the body drifts, never jerks
    poses = _Poses(name)
    blinks = _blinks(frames, rnd)
    if timeline:
        mouths, brows, nod, tilt = _performance(timeline, beats or [], level, frames, poses, rnd)
    else:
        mouths, brows, nod, tilt = _mouths(level, rnd), [None] * frames, np.zeros(frames), np.zeros(frames)
    fx, fy = (c * host["scale"] for c in host["face"])
    phase = rnd.uniform(0, 6.28)
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS),
         "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(out)],
        stdin=subprocess.PIPE)
    bg = poses.get("base", None, False).getpixel((8, 8))
    for i in range(frames):
        t = i / FPS
        e = float(smooth[i])
        # Subtle on purpose: a presenter mostly holds still; a tilt per sentence and a nod on stressed words
        # carry the performance, the drift only keeps the frame from looking frozen.
        angle = tilt[i] + 0.4 * math.sin(t * 2 * math.pi / 5.3 + phase) + 0.8 * nod[i]
        dx = 3 * math.sin(t * 2 * math.pi / 4.7 + phase) + 3 * tilt[i]
        dy = 2.5 * math.sin(t * 2 * math.pi / 3.2) - 4 * e + 9 * nod[i]  # breathe, lift on loud words, dip on a nod
        zoom = 1 + 0.004 * math.sin(t * 2 * math.pi / 3.2) + 0.008 * e
        im = poses.get(mouths[i], brows[i], i in blinks)
        if i and mouths[i] != mouths[i - 1]:  # one blended frame between mouth shapes
            im = Image.blend(poses.get(mouths[i - 1], brows[i], i in blinks), im, 0.6)
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


def fit_clip(name: str, src: Path, total: float, out: Path) -> Path:
    """Frame a talking-head video generated from the host's base image (any resolution, same aspect) the same way
    render_host frames the still: face at (WIDTH/2, FACE_Y), 30 fps, held on its last frame to `total` seconds."""
    host = HOSTS[name]
    w = round(1024 * host["scale"])
    fx, fy = (c * host["scale"] for c in host["face"])
    left, top = max(0, round(fx - WIDTH / 2)), max(0, round(fy - FACE_Y))
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-an", "-vf",
         f"scale={w}:-2:flags=lanczos,crop={WIDTH}:{HEIGHT}:{left}:{top},fps={FPS},tpad=stop_mode=clone:stop_duration=60",
         "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(out)],
        check=True)
    return out
