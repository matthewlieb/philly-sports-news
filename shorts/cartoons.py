"""Cartoon portraits of the roster, in the same Pixar-style look as the on-screen hosts.

They follow a player's licensed photos in rotation, so a video that talks about him twice doesn't show the same
picture twice. Each one is drawn from the player's headshot on the team's roster page (or, failing that, his licensed
photo) so the likeness is his; the reference itself is never shown. He wears a plain midnight-green jersey with his
number: no logos, team names or league marks. Nothing is used until a person approves it on /admin/cartoons, because a bad likeness gets roasted.
Images live in the media bucket under cartoons/<team>/<slug>.png; status lives in Redis.
"""
import base64
import io
import json
import os
import re
import time

import requests

from lib import store
from shorts.photos import find, slug

STYLE_REF = os.path.join(os.path.dirname(__file__), "assets", "hosts", "superfan", "base.jpg")
CREDIT = "Cartoon portrait: AI illustration by Philly Sport Daily"
_UA = {"User-Agent": "PhillySportDaily/1.0 (https://www.phillysportdaily.com)"}
ROSTER_PAGES = {"eagles": "https://www.philadelphiaeagles.com/team/players-roster/"}


def _plain(name: str) -> str:
    return re.sub(r"[^a-z]", "", name.lower())  # "A.J. Epenesa" on the team site is "AJ Epenesa" at ESPN


def roster_headshots(team: str) -> dict[str, str]:
    """{plain player name: 1000px headshot URL} from the team's own roster page."""
    if team not in ROSTER_PAGES:
        return {}
    page = requests.get(ROSTER_PAGES[team], headers={"User-Agent": "Mozilla/5.0"}, timeout=60).text
    shots = {}
    for row in re.findall(r"<tr>(.*?)</tr>", page, re.S):
        name, img = re.search(r'title="([^"]+)"', row), re.search(r'src="([^"]+)"', row)
        if name and img:
            # the table shows a lazy thumbnail; the same image comes 1000px square with another transformation
            big = re.sub(r"/t_thumb_squared/t_lazy/f_\w+/", "/t_headshot_desktop_3x/f_jpg/", img.group(1))
            shots[_plain(name.group(1))] = re.sub(r"\.(png|jpg|webp)$", "", big)
    return shots


def _s3():
    import boto3
    return boto3.client("s3", endpoint_url=os.environ["S3_ENDPOINT"], region_name="auto",
                        aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
                        aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"])


def _status_key(team: str) -> str:
    return store.key("cartoons", team)


def all_cartoons(team: str) -> dict[str, dict]:
    raw = store.client().get(_status_key(team))
    return json.loads(raw) if raw else {}


def _save_all(team: str, items: dict[str, dict]) -> None:
    store.client().set(_status_key(team), json.dumps(items))


def set_status(team: str, name_slug: str, status: str) -> None:
    items = all_cartoons(team)
    if name_slug in items:
        items[name_slug]["status"] = status
        _save_all(team, items)


def image_url(key: str, expires: int = 3600) -> str:
    return _s3().generate_presigned_url("get_object", Params={"Bucket": os.environ["S3_BUCKET"], "Key": key},
                                        ExpiresIn=expires)


def approved(name: str, team: str) -> list[dict]:
    """The approved cartoon of this person as a photo option (same shape as photos.find), or []."""
    item = all_cartoons(team).get(slug(name))
    if not item or item.get("status") != "approved" or not os.environ.get("S3_BUCKET"):
        return []
    return [{"url": image_url(item["key"]), "credit": CREDIT, "source": f"cartoon:{item['key']}", "primary": True}]


def _draw(reference: bytes, jersey: str, position: str) -> bytes:
    from openai import OpenAI

    outfit = (f"a plain midnight green football jersey with the number {jersey} in white" if jersey
              else "a plain midnight green quarter-zip coaching pullover" if position == "HC"
              else "a plain midnight green football jersey")
    resp = OpenAI().images.edit(
        model=os.environ.get("CARTOON_IMAGE_MODEL", "gpt-image-2"), size="1024x1536",
        image=[("person.jpg", io.BytesIO(reference), "image/jpeg"), ("style.jpg", open(STYLE_REF, "rb"), "image/jpeg")],
        prompt=(f"Create a Pixar-style 3D cartoon caricature of the person in the first image, in exactly the art style, "
                f"lighting and dark midnight-green studio background of the character in the second image. Keep the "
                f"person's recognizable face, skin tone, hair, facial hair and build. Chest-up, facing the camera, "
                f"confident friendly expression. He wears {outfit}. No logos, no team names, no NFL shield, no other "
                f"text anywhere. Vertical portrait with room at the top."))
    return base64.b64decode(resp.data[0].b64_json)


def generate(team: str, people: list[dict], redo: bool = False) -> dict[str, str]:
    """Draw a cartoon for each roster entry that has a reference photo. Returns {name: outcome}."""
    items = all_cartoons(team)
    headshots = roster_headshots(team)
    s3, bucket = _s3(), os.environ["S3_BUCKET"]
    out = {}
    for person in people:
        name, key_slug = person["name"], slug(person["name"])
        if key_slug in items and not redo and items[key_slug]["status"] != "rejected":
            out[name] = "exists"
            continue
        if _plain(name) in headshots:
            ref_url, ref_credit = headshots[_plain(name)], ROSTER_PAGES[team]
        elif photos := find(name, team, limit=1):
            ref_url, ref_credit = photos[0]["url"], photos[0].get("credit", "")
        else:
            out[name] = "no reference photo"
            continue
        try:
            reference = requests.get(ref_url, headers=_UA, timeout=60).content
            png = _draw(reference, person.get("jersey", ""), person.get("position", ""))
        except Exception as e:
            out[name] = f"failed: {str(e)[:150]}"
            continue
        key = f"cartoons/{team}/{key_slug}.png"
        s3.put_object(Bucket=bucket, Key=key, Body=png, ContentType="image/png")
        items = all_cartoons(team)  # re-read: approvals may have happened meanwhile
        items[key_slug] = {"name": name, "jersey": person.get("jersey", ""), "position": person.get("position", ""),
                           "key": key, "status": "pending", "made": int(time.time()),
                           "reference_credit": ref_credit,
                           # the website has no bucket credentials, so the review page shows a week-long signed link
                           "preview_url": image_url(key, expires=7 * 86400)}
        _save_all(team, items)
        out[name] = "drawn"
    return out


def refresh_previews(team: str) -> None:
    """Renew the week-long review links (run from somewhere with bucket credentials)."""
    items = all_cartoons(team)
    for item in items.values():
        item["preview_url"] = image_url(item["key"], expires=7 * 86400)
    _save_all(team, items)
