"""What the bot has already posted, kept in Redis so it survives between scheduled runs."""
import hashlib
import time
from datetime import datetime, timezone

from lib import store
from lib.teams import TEAM_SLUGS

_MAX_TWEETED_URLS = 500


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def slot_posted_today(slot: str) -> bool:
    return bool(store.client().exists(store.key("bot", "slot", slot, _today_utc())))


def tweeted_urls() -> set[str]:
    return set(store.client().zrevrange(store.key("bot", "tweeted_urls"), 0, -1))


def last_team() -> str | None:
    team = store.client().get(store.key("bot", "last_team"))
    return team if team in TEAM_SLUGS else None


def content_hash(text: str) -> str:
    normalized = " ".join((text or "").lower().split())
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def seen_recently(text: str) -> bool:
    return bool(store.client().exists(store.key("bot", "hash", content_hash(text))))


def record(slot: str, text: str, url: str | None = None, team: str | None = None, dedup_days: int = 14) -> None:
    r = store.client()
    r.set(store.key("bot", "slot", slot, _today_utc()), "1", ex=3 * 86400)
    r.set(store.key("bot", "hash", content_hash(text)), "1", ex=dedup_days * 86400)
    if url:
        urls_key = store.key("bot", "tweeted_urls")
        r.zadd(urls_key, {url: time.time()})
        if r.zcard(urls_key) > _MAX_TWEETED_URLS:
            r.zremrangebyrank(urls_key, 0, -_MAX_TWEETED_URLS - 1)
    if team in TEAM_SLUGS:
        r.set(store.key("bot", "last_team"), team)
