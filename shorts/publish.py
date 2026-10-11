"""Post a rendered short to YouTube Shorts and Instagram Reels.

SHORTS_PRIVACY=private (default) | unlisted | public. Instagram has no private posts, so it is only
used when SHORTS_PRIVACY=public.

YouTube:   YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN (from scripts/youtube_auth.py)
Instagram: IG_USER_ID, IG_ACCESS_TOKEN (long-lived token, Instagram API with Instagram Login), and the
           S3_* bucket variables: Instagram downloads the video from a temporary presigned URL
"""
import os
import time
import uuid
from pathlib import Path

import requests

from lib import store
from lib.teams import TEAMS, brief_url

_IG_GRAPH = f"https://graph.instagram.com/{os.environ.get('IG_API_VERSION', 'v23.0')}"


def _texts(script: dict, team: str, day: str) -> tuple[str, str, list[str]]:
    hashtags = [h if h.startswith("#") else f"#{h}" for h in script.get("hashtags") or []][:5]
    title = script["title"].strip()[:100]
    description = (
        f"{script.get('caption', '').strip()}\n\n"
        f"Full {TEAMS[team]['name']} brief with sources: {brief_url(team, day)}\n\n"
        f"Facts from the reporting linked in the brief. Narration is AI-generated.\n\n"
        + " ".join(hashtags)
    )
    return title, description, hashtags


def upload_youtube(video: Path, title: str, description: str, tags: list[str], privacy: str) -> dict:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = Credentials(
        None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    body = {
        "snippet": {"title": title, "description": description[:4900],
                    "tags": [t.lstrip("#") for t in tags], "categoryId": "17"},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    request = youtube.videos().insert(part="snippet,status", body=body,
                                      media_body=MediaFileUpload(str(video), mimetype="video/mp4", resumable=True))
    response = None
    while response is None:
        _, response = request.next_chunk()
    return {"id": response["id"], "url": f"https://www.youtube.com/shorts/{response['id']}", "privacy": privacy}


def _ig_token() -> str:
    """Long-lived Instagram token, refreshed every ~20 days (they expire after 60) and kept in Redis."""
    r = store.client()
    token = r.get(store.key("ig", "token")) or os.environ["IG_ACCESS_TOKEN"]
    refreshed = float(r.get(store.key("ig", "token_refreshed")) or 0)
    if time.time() - refreshed > 20 * 86400:
        resp = requests.get("https://graph.instagram.com/refresh_access_token",
                            params={"grant_type": "ig_refresh_token", "access_token": token}, timeout=30)
        if resp.ok and resp.json().get("access_token"):
            token = resp.json()["access_token"]
            r.set(store.key("ig", "token"), token)
            r.set(store.key("ig", "token_refreshed"), str(time.time()))
        else:
            print(f"Instagram token refresh failed: {resp.text[:300]}")
    return token


def _staged_url(video: Path) -> tuple[str, callable]:
    """Instagram fetches the video from a URL, so put it in the Railway bucket and hand out a 1-hour
    presigned link. Returns the URL and a cleanup function."""
    import boto3

    s3 = boto3.client("s3", endpoint_url=os.environ["S3_ENDPOINT"], region_name="auto",
                      aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
                      aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"])
    bucket, key = os.environ["S3_BUCKET"], f"reels/{uuid.uuid4().hex}.mp4"
    s3.upload_file(str(video), bucket, key, ExtraArgs={"ContentType": "video/mp4"})
    url = s3.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600)
    return url, lambda: s3.delete_object(Bucket=bucket, Key=key)


def upload_instagram(video: Path, caption: str) -> dict:
    token, user = _ig_token(), os.environ["IG_USER_ID"]
    url, cleanup = _staged_url(video)
    try:
        container = requests.post(f"{_IG_GRAPH}/{user}/media", timeout=60, params={
            "media_type": "REELS", "video_url": url, "caption": caption[:2200],
            "share_to_feed": "true", "access_token": token}).json()
        if "id" not in container:
            raise RuntimeError(f"Instagram container failed: {container}")
        for _ in range(60):
            status = requests.get(f"{_IG_GRAPH}/{container['id']}", timeout=30,
                                  params={"fields": "status_code,status", "access_token": token}).json()
            if status.get("status_code") == "FINISHED":
                break
            if status.get("status_code") == "ERROR":
                raise RuntimeError(f"Instagram processing failed: {status}")
            time.sleep(10)
        else:
            raise RuntimeError("Instagram processing timed out")
        published = requests.post(f"{_IG_GRAPH}/{user}/media_publish", timeout=60,
                                  params={"creation_id": container["id"], "access_token": token}).json()
        if "id" not in published:
            raise RuntimeError(f"Instagram publish failed: {published}")
    finally:
        cleanup()
    link = requests.get(f"{_IG_GRAPH}/{published['id']}", timeout=30,
                        params={"fields": "permalink", "access_token": token}).json().get("permalink")
    return {"id": published["id"], "url": link}


def publish_all(video: Path, script: dict, team: str, day: str) -> dict:
    privacy = os.environ.get("SHORTS_PRIVACY", "private")
    title, description, hashtags = _texts(script, team, day)
    results = {}
    if os.environ.get("YOUTUBE_REFRESH_TOKEN"):
        try:
            results["youtube"] = upload_youtube(video, title, description, hashtags, privacy)
        except Exception as e:
            results["youtube"] = {"error": str(e)[:500]}
    if os.environ.get("IG_USER_ID") and privacy == "public":
        try:
            results["instagram"] = upload_instagram(video, description)
        except Exception as e:
            results["instagram"] = {"error": str(e)[:500]}
    return results
