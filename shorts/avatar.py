"""Talking host from Pruna's p-video-2-pro-avatar (Replicate), for the bookend beats only.

A full 35-second host costs about $1.40 a video; the two bookend lines (the one after the hook and the closing
question) are about 8-12 seconds, roughly $0.40. Each line's narration is sent with the host's still and comes back
as a lip-synced clip, framed like the hand-drawn host. Anything that goes wrong (no token, over the monthly budget,
an error, a slow queue) returns None and the renderer draws the host itself, so a video is never lost.

SHORTS_HOST_ENGINE=pvideo turns it on; AVATAR_MONTHLY_USD caps spending (default $40).
"""
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import requests

from lib import store
from shorts.host import ASSETS, fit_clip

MODEL = "prunaai/p-video-2-pro-avatar"
PRICE_PER_SECOND = 0.04  # 768p, per second of output (replicate.com/prunaai/p-video-2-pro-avatar)
TIMEOUT_SECONDS = int(os.environ.get("AVATAR_TIMEOUT_S", "900"))
PROMPTS = {
    "pigeon": "A cartoon pigeon sports news host talks to the camera with lively expressions and natural head movement.",
    "superfan": "A cartoon Philadelphia sports superfan talks into his microphone with lively expressions and natural "
                "head movement.",
    "anchor": "A TV sports news anchor talks to the camera with natural expressions and subtle head movement.",
}


def enabled() -> bool:
    return os.environ.get("SHORTS_HOST_ENGINE") == "pvideo" and bool(os.environ.get("REPLICATE_API_TOKEN"))


def _spend_key() -> str:
    return store.key("avatar", "seconds", datetime.now(timezone.utc).strftime("%Y-%m"))


def _within_budget(seconds: float) -> bool:
    used = float(store.client().get(_spend_key()) or 0)
    return (used + seconds) * PRICE_PER_SECOND <= float(os.environ.get("AVATAR_MONTHLY_USD", "40"))


def _record(seconds: float) -> None:
    r, k = store.client(), _spend_key()
    r.set(k, f"{float(r.get(k) or 0) + seconds:.1f}")
    r.expire(k, 40 * 86400)


def _clip(host: str, audio: Path, out: Path) -> Path:
    import replicate

    with open(ASSETS / host / "base.jpg", "rb") as image, open(audio, "rb") as speech:
        pred = replicate.models.predictions.create(model=MODEL, input={
            "image": image, "audio": speech, "prompt": PROMPTS.get(host, PROMPTS["anchor"]),
            "resolution": "768p", "prompt_upsampling": False})
    deadline = time.time() + TIMEOUT_SECONDS
    while pred.status not in ("succeeded", "failed", "canceled"):
        if time.time() > deadline:
            pred.cancel()
            raise TimeoutError(f"p-video took over {TIMEOUT_SECONDS}s")
        time.sleep(5)
        pred.reload()
    if pred.status != "succeeded":
        raise RuntimeError(f"p-video {pred.status}: {pred.error}")
    url = pred.output[0] if isinstance(pred.output, list) else pred.output
    out.write_bytes(requests.get(str(url), timeout=300).content)
    return out


def animate(host: str, voice: Path, spans: list[tuple[int, float, float]], workdir: Path
            ) -> list[tuple[float, float, Path]] | None:
    """A framed talking clip for each (beat, start, end) span, or None to fall back to the drawn host."""
    seconds = sum(e - s for _, s, e in spans)
    if not _within_budget(seconds):
        print("Avatar budget for this month is used up; drawing the host instead.")
        return None
    jobs = []
    for i, start, end in spans:
        audio = workdir / f"host-line{i}.mp3"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(voice), "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}",
                        "-b:a", "192k", str(audio)], check=True)
        jobs.append((i, start, end, audio))
    try:
        with ThreadPoolExecutor(len(jobs)) as pool:
            raws = list(pool.map(lambda j: _clip(host, j[3], workdir / f"host-line{j[0]}-raw.mp4"), jobs))
    except Exception as e:
        print(f"Avatar failed ({e}); drawing the host instead.")
        return None
    _record(seconds)
    return [(start, end, fit_clip(host, raw, end - start, workdir / f"host-line{i}.mp4"))
            for (i, start, end, _), raw in zip(jobs, raws)]
