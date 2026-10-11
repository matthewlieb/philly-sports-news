"""Post a rendered short to YouTube Shorts and Instagram Reels.

SHORTS_PRIVACY=private (default) | unlisted | public. Instagram, Facebook and Threads have no private posts,
so they are only used when SHORTS_PRIVACY=public. Each platform is skipped until its variables are set.

YouTube:   YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN (from scripts/youtube_auth.py)
Instagram: IG_USER_ID, IG_ACCESS_TOKEN (long-lived token, Instagram API with Instagram Login), and the
           S3_* bucket variables: Instagram downloads the video from a temporary presigned URL
Facebook:  FB_PAGE_ID, FB_PAGE_TOKEN
Threads:   THREADS_USER_ID, THREADS_ACCESS_TOKEN
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


def _staged_url(path: Path, content_type: str = "video/mp4") -> tuple[str, callable]:
    """Instagram fetches media from a URL, so put the file in the Railway bucket and hand out a 1-hour
    presigned link. Returns the URL and a cleanup function."""
    import boto3

    s3 = boto3.client("s3", endpoint_url=os.environ["S3_ENDPOINT"], region_name="auto",
                      aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
                      aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"])
    bucket, key = os.environ["S3_BUCKET"], f"media/{uuid.uuid4().hex}{path.suffix}"
    s3.upload_file(str(path), bucket, key, ExtraArgs={"ContentType": content_type})
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
        _ig_wait(container["id"], token)
        published = requests.post(f"{_IG_GRAPH}/{user}/media_publish", timeout=60,
                                  params={"creation_id": container["id"], "access_token": token}).json()
        if "id" not in published:
            raise RuntimeError(f"Instagram publish failed: {published}")
    finally:
        cleanup()
    link = requests.get(f"{_IG_GRAPH}/{published['id']}", timeout=30,
                        params={"fields": "permalink", "access_token": token}).json().get("permalink")
    return {"id": published["id"], "url": link}


def _ig_wait(container_id: str, token: str) -> None:
    for _ in range(60):
        status = requests.get(f"{_IG_GRAPH}/{container_id}", timeout=30,
                              params={"fields": "status_code,status", "access_token": token}).json()
        if status.get("status_code") == "FINISHED":
            return
        if status.get("status_code") == "ERROR":
            raise RuntimeError(f"Instagram processing failed: {status}")
        time.sleep(5)
    raise RuntimeError("Instagram processing timed out")


def upload_instagram_carousel(images: list[Path], caption: str) -> dict:
    token, user = _ig_token(), os.environ["IG_USER_ID"]
    staged = [_staged_url(p, "image/jpeg") for p in images]
    try:
        children = []
        for url, _ in staged:
            item = requests.post(f"{_IG_GRAPH}/{user}/media", timeout=60, params={
                "image_url": url, "is_carousel_item": "true", "access_token": token}).json()
            if "id" not in item:
                raise RuntimeError(f"Instagram carousel item failed: {item}")
            children.append(item["id"])
        for child in children:
            _ig_wait(child, token)
        container = requests.post(f"{_IG_GRAPH}/{user}/media", timeout=60, params={
            "media_type": "CAROUSEL", "children": ",".join(children), "caption": caption[:2200],
            "access_token": token}).json()
        if "id" not in container:
            raise RuntimeError(f"Instagram carousel container failed: {container}")
        _ig_wait(container["id"], token)
        published = requests.post(f"{_IG_GRAPH}/{user}/media_publish", timeout=60,
                                  params={"creation_id": container["id"], "access_token": token}).json()
        if "id" not in published:
            raise RuntimeError(f"Instagram carousel publish failed: {published}")
    finally:
        for _, cleanup in staged:
            cleanup()
    link = requests.get(f"{_IG_GRAPH}/{published['id']}", timeout=30,
                        params={"fields": "permalink", "access_token": token}).json().get("permalink")
    return {"id": published["id"], "url": link}


def upload_facebook_reel(video: Path, description: str, state: str = "PUBLISHED") -> dict:
    """Facebook Page Reel. FB_PAGE_ID + FB_PAGE_TOKEN (a Page token from a long-lived user token doesn't expire)."""
    page, token = os.environ["FB_PAGE_ID"], os.environ["FB_PAGE_TOKEN"]
    graph = f"https://graph.facebook.com/{os.environ.get('FB_API_VERSION', 'v23.0')}"
    start = requests.post(f"{graph}/{page}/video_reels", timeout=60,
                          params={"upload_phase": "start", "access_token": token}).json()
    if "video_id" not in start:
        raise RuntimeError(f"Facebook reel start failed: {start}")
    url, cleanup = _staged_url(video)
    try:
        up = requests.post(start["upload_url"], timeout=300,
                           headers={"Authorization": f"OAuth {token}", "file_url": url}).json()
        if not up.get("success"):
            raise RuntimeError(f"Facebook reel upload failed: {up}")
        done = requests.post(f"{graph}/{page}/video_reels", timeout=60, params={
            "upload_phase": "finish", "video_id": start["video_id"], "video_state": state,
            "description": description[:5000], "access_token": token}).json()
        if not done.get("success"):
            raise RuntimeError(f"Facebook reel publish failed: {done}")
        for _ in range(60):
            status = requests.get(f"{graph}/{start['video_id']}", timeout=30,
                                  params={"fields": "status", "access_token": token}).json().get("status", {})
            if status.get("video_status") in ("ready", "error") or status.get("processing_phase", {}).get("status") == "complete":
                break
            time.sleep(10)
    finally:
        cleanup()
    return {"id": start["video_id"], "url": f"https://www.facebook.com/reel/{start['video_id']}"}


def _threads_token() -> str:
    """Long-lived Threads token, refreshed every ~20 days and kept in Redis (same pattern as Instagram)."""
    r = store.client()
    token = r.get(store.key("threads", "token")) or os.environ["THREADS_ACCESS_TOKEN"]
    if time.time() - float(r.get(store.key("threads", "token_refreshed")) or 0) > 20 * 86400:
        resp = requests.get("https://graph.threads.net/refresh_access_token",
                            params={"grant_type": "th_refresh_token", "access_token": token}, timeout=30)
        if resp.ok and resp.json().get("access_token"):
            token = resp.json()["access_token"]
            r.set(store.key("threads", "token"), token)
            r.set(store.key("threads", "token_refreshed"), str(time.time()))
    return token


def upload_threads(video: Path, text: str) -> dict:
    token, user = _threads_token(), os.environ["THREADS_USER_ID"]
    graph = "https://graph.threads.net/v1.0"
    url, cleanup = _staged_url(video)
    try:
        c = requests.post(f"{graph}/{user}/threads", timeout=60, params={
            "media_type": "VIDEO", "video_url": url, "text": text[:500], "access_token": token}).json()
        if "id" not in c:
            raise RuntimeError(f"Threads container failed: {c}")
        for _ in range(60):
            st = requests.get(f"{graph}/{c['id']}", timeout=30, params={"fields": "status,error_message", "access_token": token}).json()
            if st.get("status") == "FINISHED":
                break
            if st.get("status") == "ERROR":
                raise RuntimeError(f"Threads processing failed: {st}")
            time.sleep(10)
        else:
            raise RuntimeError("Threads processing timed out")
        pub = requests.post(f"{graph}/{user}/threads_publish", timeout=60,
                            params={"creation_id": c["id"], "access_token": token}).json()
        if "id" not in pub:
            raise RuntimeError(f"Threads publish failed: {pub}")
    finally:
        cleanup()
    link = requests.get(f"{graph}/{pub['id']}", timeout=30, params={"fields": "permalink", "access_token": token}).json()
    return {"id": pub["id"], "url": link.get("permalink")}


def publish_all(video: Path, script: dict, team: str, day: str) -> dict:
    privacy = os.environ.get("SHORTS_PRIVACY", "private")
    title, description, hashtags = _texts(script, team, day)
    results = {}
    if os.environ.get("YOUTUBE_REFRESH_TOKEN"):
        try:
            results["youtube"] = upload_youtube(video, title, description, hashtags, privacy)
        except Exception as e:
            results["youtube"] = {"error": str(e)[:500]}
    if privacy != "public":
        return results
    social = [("instagram", "IG_USER_ID", lambda: upload_instagram(video, description)),
              ("facebook", "FB_PAGE_ID", lambda: upload_facebook_reel(video, description)),
              ("threads", "THREADS_USER_ID", lambda: upload_threads(video, f"{script.get('caption', '')} {' '.join(hashtags[:2])}\n\nFull brief: {brief_url(team, day)}"))]
    for name, env, upload in social:
        if os.environ.get(env):
            try:
                results[name] = upload()
            except Exception as e:
                results[name] = {"error": str(e)[:500]}
    return results
