"""Comment assistant for our own YouTube videos and Instagram posts.

Each run: collect new comments, have the model decide reply / hide / ignore and draft replies, then
  COMMENT_MODE=review (default): queue drafts for approval at /admin/comments on the site
  COMMENT_MODE=auto: post replies and hide spam right away
and finally carry out anything approved on the review page since the last run.

Only acts on comments on our own posts. Never likes, follows, DMs or comments elsewhere.
"""
import json
import os
import time

import requests

from lib import store
from lib.teams import TEAMS

_SYSTEM = """You manage comments for the "{name} Daily" fan account (short daily {name} news videos).
For each comment decide:
- "reply": a genuine question, a real take worth engaging, or praise. Reply like a friendly, knowledgeable fan:
  1 to 2 short sentences, no hashtags, no links, no emojis spam (one is fine). Agree or disagree respectfully;
  answer questions only with facts from the post context below; if you don't know, say you'll keep an eye on it.
  Never argue, insult, discuss betting, or make promises.
- "hide": spam, scams, self-promotion, links to sketchy sites, hate, harassment, threats or sexual content.
- "ignore": everything else (emoji-only, low effort, already answered, or anything risky to touch).
Return JSON: {{"items": [{{"n": <number>, "action": "reply|hide|ignore", "reply": "...", "reason": "short"}}]}}"""


def _item_key(platform: str, cid: str) -> str:
    return store.key("comments", "item", platform, cid)


def _youtube():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(None, refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"], token_uri="https://oauth2.googleapis.com/token",
                        client_id=os.environ["YOUTUBE_CLIENT_ID"], client_secret=os.environ["YOUTUBE_CLIENT_SECRET"])
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def youtube_comments() -> list[dict]:
    yt = _youtube()
    channel = yt.channels().list(part="id", mine=True).execute()["items"][0]["id"]
    threads = yt.commentThreads().list(part="snippet", allThreadsRelatedToChannelId=channel, maxResults=50,
                                       order="time", textFormat="plainText").execute().get("items", [])
    titles = {}
    out = []
    for t in threads:
        top = t["snippet"]["topLevelComment"]
        sn = top["snippet"]
        if sn.get("authorChannelId", {}).get("value") == channel:
            continue
        vid = t["snippet"].get("videoId")
        if vid and vid not in titles:
            v = yt.videos().list(part="snippet", id=vid).execute().get("items", [])
            titles[vid] = (v[0]["snippet"]["title"] + "\n" + v[0]["snippet"]["description"][:600]) if v else ""
        out.append({"platform": "youtube", "id": top["id"], "author": sn.get("authorDisplayName", ""),
                    "text": sn.get("textDisplay", ""), "context": titles.get(vid, ""),
                    "link": f"https://www.youtube.com/watch?v={vid}&lc={top['id']}" if vid else ""})
    return out


def instagram_comments() -> list[dict]:
    from shorts.publish import _IG_GRAPH, _ig_token

    token, user = _ig_token(), os.environ["IG_USER_ID"]
    me = requests.get(f"{_IG_GRAPH}/me", params={"fields": "username", "access_token": token}, timeout=30).json().get("username")
    media = requests.get(f"{_IG_GRAPH}/{user}/media", timeout=30, params={
        "fields": "id,caption,permalink", "limit": 10, "access_token": token}).json().get("data", [])
    out = []
    for m in media:
        resp = requests.get(f"{_IG_GRAPH}/{m['id']}/comments", timeout=30, params={
            "fields": "id,text,username,replies{username}", "access_token": token}).json()
        if "error" in resp:
            print(f"Instagram comments unavailable: {resp['error'].get('message')}")
            return out
        for c in resp.get("data", []):
            if c.get("username") == me or any(r.get("username") == me for r in (c.get("replies") or {}).get("data", [])):
                continue
            out.append({"platform": "instagram", "id": c["id"], "author": c.get("username", ""), "text": c.get("text", ""),
                        "context": (m.get("caption") or "")[:600], "link": m.get("permalink", "")})
    return out


def _draft(team: str, comments: list[dict]) -> list[dict]:
    from openai import OpenAI

    numbered = "\n\n".join(f"[{i}] On post: {c['context'][:300]!r}\nComment by {c['author']}: {c['text']}"
                           for i, c in enumerate(comments, 1))
    resp = OpenAI().chat.completions.create(
        model=os.environ.get("COMMENTS_MODEL", "gpt-5.4-mini"), response_format={"type": "json_object"},
        messages=[{"role": "system", "content": _SYSTEM.format(name=TEAMS[team]["name"])},
                  {"role": "user", "content": numbered}])
    decisions = {d.get("n"): d for d in json.loads(resp.choices[0].message.content or "{}").get("items") or []}
    for i, c in enumerate(comments, 1):
        d = decisions.get(i) or {"action": "ignore", "reason": "no decision"}
        c.update(action=d.get("action", "ignore"), draft=(d.get("reply") or "").strip(), reason=d.get("reason", ""))
    return comments


def _reply(item: dict, text: str) -> None:
    if item["platform"] == "youtube":
        _youtube().comments().insert(part="snippet", body={"snippet": {"parentId": item["id"], "textOriginal": text}}).execute()
    else:
        from shorts.publish import _IG_GRAPH, _ig_token
        r = requests.post(f"{_IG_GRAPH}/{item['id']}/replies", params={"message": text, "access_token": _ig_token()}, timeout=30).json()
        if "id" not in r:
            raise RuntimeError(r)


def _hide(item: dict) -> None:
    if item["platform"] == "youtube":
        _youtube().comments().setModerationStatus(id=item["id"], moderationStatus="rejected").execute()
    else:
        from shorts.publish import _IG_GRAPH, _ig_token
        r = requests.post(f"{_IG_GRAPH}/{item['id']}", params={"hide": "true", "access_token": _ig_token()}, timeout=30).json()
        if not r.get("success"):
            raise RuntimeError(r)


def _save(item: dict) -> None:
    r = store.client()
    r.set(_item_key(item["platform"], item["id"]), json.dumps(item), ex=60 * 86400)
    r.zadd(store.key("comments", "queue"), {f"{item['platform']}:{item['id']}": item.get("created", time.time())})


def _carry_out(item: dict) -> None:
    try:
        if item["status"] == "approved":
            _reply(item, item["draft"])
            item["status"] = "replied"
        elif item["status"] == "hide_approved":
            _hide(item)
            item["status"] = "hidden"
    except Exception as e:
        item["status"], item["error"] = "failed", str(e)[:300]
    _save(item)


def run(team: str) -> None:
    r = store.client()
    mode = os.environ.get("COMMENT_MODE", "review")
    new = []
    for source, env in ((youtube_comments, "YOUTUBE_REFRESH_TOKEN"), (instagram_comments, "IG_USER_ID")):
        if os.environ.get(env):
            try:
                new += [c for c in source() if not r.exists(_item_key(c["platform"], c["id"]))]
            except Exception as e:
                print(f"{source.__name__} failed: {e}")
    print(f"{len(new)} new comments")
    for c in (_draft(team, new) if new else []):
        c["created"] = time.time()
        if c["action"] == "ignore":
            c["status"] = "ignored"
        elif mode == "auto":
            c["status"] = "approved" if c["action"] == "reply" else "hide_approved"
        else:
            c["status"] = "pending"
        _save(c)

    for member in r.zrevrange(store.key("comments", "queue"), 0, 199):
        platform, cid = member.split(":", 1)
        raw = r.get(_item_key(platform, cid))
        if raw and (item := json.loads(raw))["status"] in ("approved", "hide_approved"):
            _carry_out(item)
            print(f"{platform} {cid}: {item['status']}")
