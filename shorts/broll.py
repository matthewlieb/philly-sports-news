"""Background footage: hand-picked, team-neutral Pexels stadium/crowd clips (Pexels license: free, no attribution
required). They sit under a heavy team-color tint, so they read as atmosphere rather than a specific game."""
import os
import random
from pathlib import Path

import requests

# Night stadiums, aerials and crowds. Picked to avoid visible soccer play and identifiable people.
CLIP_IDS = [35970540, 35970584, 35970583, 30398376, 34561857, 34452578, 29250674, 16469399, 32337290, 34561859]
CACHE = Path(os.environ.get("SHORTS_CACHE", "/tmp/psd-shorts-cache"))


def _download(clip_id: int, key: str) -> Path | None:
    path = CACHE / f"pexels-{clip_id}.mp4"
    if path.exists():
        return path
    try:
        info = requests.get(f"https://api.pexels.com/videos/videos/{clip_id}", headers={"Authorization": key}, timeout=20).json()
        files = [f for f in info["video_files"] if f.get("height") and f["height"] <= 1920 and f.get("link")]
        best = max(files, key=lambda f: f["height"])
        CACHE.mkdir(parents=True, exist_ok=True)
        with requests.get(best["link"], stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
        return path
    except Exception as e:
        print(f"Pexels clip {clip_id} unavailable: {e}")
        return None


def pick_clips(count: int, seed: str) -> list[Path]:
    """Up to `count` local clip paths, varied day to day. Empty if PEXELS_API_KEY is unset."""
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return []
    ids = CLIP_IDS[:]
    random.Random(seed).shuffle(ids)
    clips = []
    for clip_id in ids:
        if len(clips) == count:
            break
        if path := _download(clip_id, key):
            clips.append(path)
    return clips
