"""Background footage: hand-picked, team-neutral Pexels stadium/crowd and Philadelphia city clips, plus our own
AI-generated atmosphere clips (stadium, fans, tailgates, the city; no real players, logos or events) from the media
bucket under broll/ai/ (cartoon-*.mp4 in the hosts' Pixar-style look). Pexels license: free, no attribution
required. They sit under a heavy team-color tint, so they read as atmosphere rather than a specific game."""
import os
import random
from pathlib import Path

import requests

# Night stadiums, aerials and crowds. Picked to avoid visible soccer play and identifiable people.
STADIUM_IDS = [35970540, 35970584, 35970583, 30398376, 34561857, 34452578, 29250674, 16469399, 32337290, 34561859]
# Philadelphia: skyline at dusk and night, City Hall, Broad Street, aerials. No holiday lights, no faces.
PHILLY_IDS = [13082932, 37261867, 37261869, 33295883, 35192564, 37258796, 37261868, 37258675, 13674919, 13687405, 37104317]
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


def _ai_clips() -> list[Path]:
    """Our AI atmosphere clips, downloaded from the bucket once per container."""
    if not os.environ.get("S3_BUCKET"):
        return []
    try:
        import boto3
        s3 = boto3.client("s3", endpoint_url=os.environ["S3_ENDPOINT"], region_name="auto",
                          aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
                          aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"])
        keys = [o["Key"] for o in s3.list_objects_v2(Bucket=os.environ["S3_BUCKET"], Prefix="broll/ai/").get("Contents", [])
                if o["Key"].endswith(".mp4")]
        CACHE.mkdir(parents=True, exist_ok=True)
        paths = []
        for key in keys:
            path = CACHE / ("ai-" + key.rsplit("/", 1)[-1])
            if not path.exists():
                s3.download_file(os.environ["S3_BUCKET"], key, str(path))
            paths.append(path)
        return paths
    except Exception as e:
        print(f"AI b-roll unavailable: {e}")
        return []


def pick_clips(count: int, seed: str, cartoon: bool = False) -> list[Path]:
    """Up to `count` local clip paths, varied day to day. Empty if PEXELS_API_KEY is unset.

    cartoon=True (the days a cartoon host presents) uses our Pixar-style clips first, so the host and the footage
    share a look; otherwise those are left out and the footage stays realistic."""
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return []
    rnd = random.Random(seed)
    stadium, philly = STADIUM_IDS[:], PHILLY_IDS[:]
    ai = [p for p in _ai_clips() if p.name.startswith("ai-cartoon-") == cartoon]
    rnd.shuffle(stadium)
    rnd.shuffle(philly)
    rnd.shuffle(ai)
    if cartoon and len(ai) >= count:
        return ai[:count]
    # rotate our own atmosphere clips, game footage and the city
    order = [x for trio in zip(ai or [None] * len(stadium), stadium, philly) for x in trio if x is not None]
    clips = []
    for item in order:
        if len(clips) == count:
            break
        if isinstance(item, Path):
            clips.append(item)
        elif path := _download(item, key):
            clips.append(path)
    return clips
