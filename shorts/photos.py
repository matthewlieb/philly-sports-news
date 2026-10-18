"""Photos of the people a video is about, from sources we're allowed to use.

Order of preference:
  1. Our own or licensed photos uploaded to the media bucket under photos/<person-slug>/ (any .jpg/.png).
     Credit, if needed, goes in photos/<person-slug>/credit.txt.
  2. Wikimedia Commons, which holds Wikidata's main photo for most NFL/NBA/MLB/NHL players and coaches plus
     thousands of game photos (largely All-Pro Reels' CC BY-SA set). Only licenses that allow commercial use and
     modification are accepted (CC0, public domain, CC BY, CC BY-SA); NC/ND and fair-use files are skipped.

Each photo comes back cropped to 1080x1920 around the face, with the credit line the license requires.
Lookups are cached in Redis for a week so a player isn't searched for again on every video.
"""
import html
import io
import json
import os
import re
from pathlib import Path

import requests
from PIL import Image, ImageFilter, ImageOps

from lib import store

W, H = 1080, 1920
CACHE = Path(os.environ.get("SHORTS_CACHE", "/tmp/psd-shorts-cache")) / "photos"
_UA = {"User-Agent": "PhillySportDaily/1.0 (https://www.phillysportdaily.com)"}
_OK_LICENSES = re.compile(r"^(CC0|Public domain|PD|CC BY(-SA)? \d)", re.I)
TEAM_WIKIDATA = {"eagles": "Q219714", "sixers": "Q138089", "phillies": "Q650840", "flyers": "Q192083"}
_SPORT_WORDS = {"eagles": ("football", "nfl"), "sixers": ("basketball", "nba"), "phillies": ("baseball", "mlb"),
                "flyers": ("hockey", "nhl")}


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _get(url: str, **params) -> dict:
    resp = requests.get(url, params={**params, "format": "json"}, headers=_UA, timeout=20)
    resp.raise_for_status()
    return resp.json()


def _wikidata_photo(name: str, team: str) -> str | None:
    """File name of the person's main Commons photo, picking the right person among namesakes."""
    words = _SPORT_WORDS[team]
    found = _get("https://www.wikidata.org/w/api.php", action="wbsearchentities", search=name, language="en",
                 type="item", limit=7).get("search", [])
    best, best_score = None, 0
    for e in found:
        desc = (e.get("description") or "").lower()
        if not any(w in desc for w in words) and "coach" not in desc:
            continue
        claims = _get(f"https://www.wikidata.org/wiki/Special:EntityData/{e['id']}.json")["entities"][e["id"]]["claims"]
        teams = {c["mainsnak"].get("datavalue", {}).get("value", {}).get("id") for c in claims.get("P54", [])}
        p18 = claims.get("P18")
        score = 10 + (100 if TEAM_WIKIDATA[team] in teams else 0) + (5 if p18 else 0)
        if p18 and score > best_score:
            best, best_score = p18[0]["mainsnak"]["datavalue"]["value"], score
    return best


_TEAM_WORDS = {"eagles": "eagles", "sixers": "76ers|sixers", "phillies": "phillies", "flyers": "flyers"}
_SEVERAL = re.compile(r"&| and | with |sack|tackl|team photo|group", re.I)
_CONTEXT = re.compile(r"20(1[89]|2\d)|nfl|nba|mlb|nhl|eagles|76ers|sixers|phillies|flyers|vs\.?|camp|game", re.I)


def _commons_search(name: str, team: str, limit: int = 6) -> list[str]:
    """More Commons photos named after this person in a sports context (a year or team in the file name keeps out
    namesakes like a 1930s portrait), team photos first."""
    res = _get("https://commons.wikimedia.org/w/api.php", action="query", list="search", srnamespace=6, srlimit=30,
               srsearch=f'filetype:bitmap intitle:"{name}"')
    titles = [r["title"].removeprefix("File:") for r in res.get("query", {}).get("search", [])]
    titles = [t for t in titles if _CONTEXT.search(t) and not _SEVERAL.search(t)]
    titles.sort(key=lambda t: (not re.search(_TEAM_WORDS[team], t, re.I), "cropped" not in t.lower()))
    return titles[:limit]


def _commons_info(filename: str, min_side: int = 500) -> dict | None:
    pages = _get("https://commons.wikimedia.org/w/api.php", action="query", titles=f"File:{filename}", prop="imageinfo",
                 iiprop="url|size|extmetadata", iiurlwidth=1600,
                 iiextmetadatafilter="LicenseShortName|Artist|Credit")["query"]["pages"]
    page = next(iter(pages.values()))
    if "imageinfo" not in page:
        return None
    ii = page["imageinfo"][0]
    meta = ii.get("extmetadata", {})
    lic = meta.get("LicenseShortName", {}).get("value", "")
    if not _OK_LICENSES.match(lic) or re.search(r"\bNC\b|\bND\b|fair use", lic, re.I) or min(ii["width"], ii["height"]) < min_side:
        return None
    artist = html.unescape(re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", ""))).strip() or "Unknown"
    return {"url": ii.get("thumburl") or ii["url"], "credit": f"{artist[:60]}, {lic}, via Wikimedia Commons",
            "source": f"https://commons.wikimedia.org/wiki/File:{filename.replace(' ', '_')}"}


def _bucket_photos(name: str) -> list[dict]:
    if not os.environ.get("S3_BUCKET"):
        return []
    try:
        import boto3
        s3 = boto3.client("s3", endpoint_url=os.environ["S3_ENDPOINT"], region_name="auto",
                          aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
                          aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"])
        prefix = f"photos/{slug(name)}/"
        keys = [o["Key"] for o in s3.list_objects_v2(Bucket=os.environ["S3_BUCKET"], Prefix=prefix).get("Contents", [])]
        credit = ""
        if prefix + "credit.txt" in keys:
            credit = s3.get_object(Bucket=os.environ["S3_BUCKET"], Key=prefix + "credit.txt")["Body"].read().decode()[:120]
        return [{"url": s3.generate_presigned_url("get_object", Params={"Bucket": os.environ["S3_BUCKET"], "Key": k},
                                                  ExpiresIn=3600),
                 "credit": credit.strip(), "source": f"bucket:{k}"}
                for k in keys if k.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
    except Exception as e:
        print(f"Bucket photos for {name} unavailable: {e}")
        return []


def find(name: str, team: str, limit: int = 3) -> list[dict]:
    """Up to `limit` usable photos of this person: [{"url", "credit", "source", "primary"}]. The primary photo is
    Wikidata's curated one; search results only count when exactly one face shows (see portrait)."""
    own = _bucket_photos(name)
    if own:
        return own[:limit]
    r = store.client()
    key = store.key("photos", team, slug(name))
    if cached := r.get(key):
        return json.loads(cached)[:limit]
    photos, seen = [], set()
    try:
        main = _wikidata_photo(name, team)
        for f in ([main] if main else []) + _commons_search(name, team):
            if f in seen:
                continue
            seen.add(f)
            info = _commons_info(f, 350 if f == main else 500)
            info = info and {**info, "primary": f == main, "team": team, "name": name}
            if info and (f == main or portrait(info) is not None):
                photos.append(info)
            if len(photos) == limit + 1:
                break
        # Photos in this team's uniform first.
        photos.sort(key=lambda p: not re.search(_TEAM_WORDS[team], p["source"], re.I))
    except Exception as e:
        print(f"Photo lookup for {name} failed: {e}")
        return []
    photos = photos[:limit]
    r.set(key, json.dumps(photos), ex=7 * 86400)
    return photos


def _faces(img: Image.Image) -> list[tuple[int, int, int, int]] | None:
    """Confident frontal faces in the upper 70% of the photo, largest first (None if OpenCV isn't installed).
    Small or low faces are mostly false hits on hands, knees and jersey numbers."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None
    gray = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2GRAY)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    found = cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=9, minSize=(max(40, gray.shape[1] // 14),) * 2)
    faces = sorted((tuple(int(v) for v in f) for f in found if f[1] + f[3] / 2 < gray.shape[0] * 0.7),
                   key=lambda f: -f[2] * f[3])
    return [f for f in faces if f[2] * f[3] >= faces[0][2] * faces[0][3] * 0.35] if faces else []


def portrait(photo: dict, size: tuple[int, int] = (W, H)) -> Image.Image | None:
    """Download and crop to a vertical frame centered on the face (face in the upper part, room for text below).
    A non-primary photo is rejected (None) unless exactly one face shows, so group shots can't put the wrong
    person on screen."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / (slug(photo["source"])[-80:] + ".img")
    try:
        if not path.exists():
            resp = requests.get(photo["url"], headers=_UA, timeout=60)
            resp.raise_for_status()
            path.write_bytes(resp.content)
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(path.read_bytes()))).convert("RGB")
    except Exception as e:
        print(f"Photo download failed ({photo['source']}): {e}")
        return None
    tw, th = size
    faces = _faces(img)
    single_subject = bool(photo.get("name")) and re.fullmatch(
        rf"{re.escape(photo['name'])}[ _-]*(\(?\d{{4}}\)?)?[ _-]*(\(cropped\))?",
        Path(photo["source"].split("File:")[-1].replace("_", " ")).stem, re.I) is not None
    if not photo.get("primary", True) and faces is not None and not (len(faces) == 1 or (not faces and single_subject)):
        return None
    if faces and len(faces) == 1 and faces[0][2] >= img.width * 0.12:
        return _face_crop(img, faces[0], tw, th)
    return _fitted(img, tw, th)


def _face_crop(img: Image.Image, face: tuple[int, int, int, int], tw: int, th: int) -> Image.Image:
    """Zoom so the face is about a quarter of the frame width, face in the upper third."""
    cover = max(tw / img.width, th / img.height)
    scale = min(max(cover, (tw * 0.26) / face[2]), cover * 1.8)
    img = img.resize((max(tw, round(img.width * scale)), max(th, round(img.height * scale))), Image.LANCZOS)
    cx, cy = (face[0] + face[2] / 2) * scale, (face[1] + face[3] / 2) * scale
    left = int(min(max(0, cx - tw / 2), img.width - tw))
    top = int(min(max(0, cy - th * 0.32), img.height - th))
    return img.crop((left, top, left + tw, top + th))


def _fitted(img: Image.Image, tw: int, th: int) -> Image.Image:
    """The whole photo across the frame over a blurred, zoomed copy of itself: nobody gets cropped out."""
    cover = max(tw / img.width, th / img.height)
    bg = img.resize((round(img.width * cover), round(img.height * cover)), Image.LANCZOS)
    left, top = (bg.width - tw) // 2, (bg.height - th) // 2
    bg = bg.crop((left, top, left + tw, top + th)).filter(ImageFilter.GaussianBlur(40))
    bg = Image.blend(bg, Image.new("RGB", bg.size, (0, 0, 0)), 0.35)
    fit = min(tw / img.width, th * 0.62 / img.height)
    fg = img.resize((round(img.width * fit), round(img.height * fit)), Image.LANCZOS)
    bg.paste(fg, ((tw - fg.width) // 2, int(th * 0.08)))
    return bg


def beat_photos(script: dict, team: str, workdir: Path) -> tuple[list[Path | None], list[str]]:
    """A prepared frame per beat (or None for stadium footage) and the credit lines for the description.

    The hook always gets a photo when anyone in the script has one, because a face is what stops the scroll.
    The closing question stays on footage, and the same person's beats rotate through their photos.
    """
    from shorts.graphics import photo_frame

    beats = script["beats"]
    people = [b.get("person") or "" for b in beats]
    found: dict[str, list[dict]] = {}
    # The opener must show whoever its big words name ("MCKEE STARTS" can't sit on a photo of Hurts); with no usable
    # photo of them it falls back to footage. Otherwise it borrows the first person the video has a photo of.
    hook_person = script.get("hook_person") or ""
    if hook_person:
        found[hook_person] = find(hook_person, team)
        people[0] = hook_person if found[hook_person] else ""
    elif not people[0]:
        people[0] = next((p for p in people if p and (found.setdefault(p, find(p, team)))), "")
    people[-1] = "" if len(beats) > 2 else people[-1]
    used: dict[str, int] = {}
    out, credits = [], []
    for i, person in enumerate(people):
        if not person:
            out.append(None)
            continue
        if person not in found:
            found[person] = find(person, team)
        options = found[person]
        if not options:
            out.append(None)
            continue
        photo = options[used.get(person, 0) % len(options)]
        used[person] = used.get(person, 0) + 1
        img = portrait(photo)
        if img is None:
            out.append(None)
            continue
        path = workdir / f"photo{i}.jpg"
        photo_frame(img, team).save(path, quality=92)
        out.append(path)
        if photo.get("credit") and photo["credit"] not in credits:
            credits.append(photo["credit"])
    return out, credits
