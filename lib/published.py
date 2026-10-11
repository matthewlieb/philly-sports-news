"""When was an article published? Read from the page's metadata, cached in Redis for a week."""
import hashlib
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

from lib import store

_PATTERNS = [
    re.compile(r'(?:property|name|itemprop)=["\'](?:article:published_time|datePublished|pubdate|publish-date|sailthru\.date|parsely-pub-date)["\'][^>]*?content=["\']([^"\']+)', re.I),
    re.compile(r'content=["\']([^"\']+)["\'][^>]*?(?:property|name|itemprop)=["\'](?:article:published_time|datePublished|pubdate)["\']', re.I),
    re.compile(r'"datePublished"\s*:\s*"([^"]+)"', re.I),
    re.compile(r'<time[^>]+datetime=["\']([^"\']+)', re.I),
]


def parse_date(value: str | None) -> datetime | None:
    """ISO 8601 or RFC 2822 date string to an aware UTC datetime."""
    if not value:
        return None
    value = value.strip()
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00").replace(" ", "T", 1))
    except ValueError:
        try:
            dt = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def _from_page(url: str) -> datetime | None:
    try:
        html = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"}).text[:400_000]
    except Exception:
        return None
    for pattern in _PATTERNS:
        if m := pattern.search(html):
            if dt := parse_date(m.group(1)):
                return dt
    return None


def published_at(url: str) -> datetime | None:
    r = store.client()
    key = store.key("pub", hashlib.sha1(url.encode()).hexdigest()[:16])
    cached = r.get(key)
    if cached:
        return None if cached == "unknown" else parse_date(cached)
    dt = _from_page(url)
    r.set(key, dt.isoformat() if dt else "unknown", ex=7 * 86400)
    return dt


def published_many(urls: list[str]) -> dict[str, datetime | None]:
    with ThreadPoolExecutor(max_workers=8) as pool:
        return dict(zip(urls, pool.map(published_at, urls)))
