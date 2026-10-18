"""Durable storage for daily briefs, bot state and pageview counts.

Uses Redis when REDIS_URL is set. Without it (local development) an in-memory
stand-in is used, so nothing persists between processes.
"""
import os
import time

KEY_PREFIX = "psd:"


class _MemoryStore:
    """The subset of the redis-py API this project uses."""

    def __init__(self):
        self._data = {}
        self._expires = {}

    def _alive(self, key):
        exp = self._expires.get(key)
        if exp is not None and exp < time.time():
            self._data.pop(key, None)
            self._expires.pop(key, None)
        return key in self._data

    def get(self, key):
        return self._data.get(key) if self._alive(key) else None

    def set(self, key, value, ex=None, nx=False):
        if nx and self._alive(key):
            return None
        self._data[key] = value
        self._expires[key] = time.time() + ex if ex else None
        return True

    def sismember(self, key, member):
        return member in (self._data.get(key) or set())

    def sadd(self, key, *members):
        self._data.setdefault(key, set()).update(members)

    def lrange(self, key, start, end):
        items = self._data.get(key) or []
        return items[start:None if end == -1 else end + 1]

    def llen(self, key):
        return len(self._data.get(key) or [])

    def rpush(self, key, *values):
        self._data.setdefault(key, []).extend(values)

    def lpush(self, key, *values):
        for v in values:
            self._data.setdefault(key, []).insert(0, v)

    def ltrim(self, key, start, end):
        self._data[key] = self.lrange(key, start, end)

    def mget(self, keys):
        return [self.get(k) for k in keys]

    def exists(self, key):
        return 1 if self._alive(key) else 0

    def incr(self, key):
        self._data[key] = int(self.get(key) or 0) + 1
        return self._data[key]

    def expire(self, key, seconds):
        if self._alive(key):
            self._expires[key] = time.time() + seconds

    def zadd(self, key, mapping):
        z = self._data.setdefault(key, {})
        z.update(mapping)

    def zrevrange(self, key, start, end):
        z = self._data.get(key) or {}
        members = sorted(z, key=lambda m: z[m], reverse=True)
        return members[start:None if end == -1 else end + 1]

    def zscore(self, key, member):
        return (self._data.get(key) or {}).get(member)

    def zcard(self, key):
        return len(self._data.get(key) or {})

    def zremrangebyrank(self, key, start, end):
        z = self._data.get(key) or {}
        members = sorted(z, key=lambda m: z[m])
        for m in members[start:None if end == -1 else end + 1]:
            del z[m]


_client = None


def client():
    """Shared Redis client (decoded strings), or the in-memory stand-in."""
    global _client
    if _client is None:
        url = os.environ.get("REDIS_URL")
        if url:
            import redis
            _client = redis.Redis.from_url(url, decode_responses=True)
        else:
            _client = _MemoryStore()
    return _client


def key(*parts) -> str:
    return KEY_PREFIX + ":".join(str(p) for p in parts)
