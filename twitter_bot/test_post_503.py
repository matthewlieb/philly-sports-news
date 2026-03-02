#!/usr/bin/env python3
"""
Test X API posting with aggressive 503 workaround.

Uses your keys from .env_x to:
  1. Verify credentials (get_me)
  2. Attempt to post a test tweet with exponential backoff retry

X recommends exponential backoff for 503: start 5s, double each attempt.
This script uses 6 attempts: 5s, 10s, 20s, 40s, 80s, 160s (total ~5 min).

Run from repo root:
  python -m twitter_bot.test_post_503           # post test tweet
  python -m twitter_bot.test_post_503 --dry-run  # verify keys only, no post
  python -m twitter_bot.test_post_503 --persist  # retry every 5 min until success
"""

import argparse
import os
import sys
import time

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
os.chdir(_REPO_ROOT)

# Load .env_x and .env
for name in (".env_x", ".env"):
    path = os.path.join(_REPO_ROOT, name)
    if not os.path.isfile(path):
        continue
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip("'\"").strip()
            if k and v and k not in os.environ:
                os.environ[k] = v
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_REPO_ROOT, ".env_x"))
    load_dotenv(os.path.join(_REPO_ROOT, ".env"))
except ImportError:
    pass


def get_client(use_xdk=False):
    """Return (client, backend_name) for tweepy or xdk."""
    api_key = os.environ.get("X_API_KEY") or os.environ.get("X_CONSUMER_KEY")
    api_secret = os.environ.get("X_API_SECRET") or os.environ.get("X_CONSUMER_SECRET")
    access = os.environ.get("X_ACCESS_TOKEN")
    access_secret = os.environ.get("X_ACCESS_TOKEN_SECRET")
    if not all((api_key, api_secret, access, access_secret)):
        return None, "Missing X credentials in .env_x or .env"

    if use_xdk:
        try:
            from xdk import Client
            from xdk.oauth1_auth import OAuth1
            oauth1 = OAuth1(api_key=api_key, api_secret=api_secret, callback="oob", access_token=access, access_token_secret=access_secret)
            return Client(auth=oauth1), "xdk"
        except ImportError:
            return None, "xdk not installed (pip install xdk)"
    else:
        import tweepy
        return tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access,
            access_token_secret=access_secret,
        ), "tweepy"


def _dump_response(e, prefix=""):
    """Print full response details for debugging 503."""
    if not hasattr(e, "response") or e.response is None:
        return
    r = e.response
    print(f"{prefix}Status: {getattr(r, 'status_code', getattr(r, 'status', '?'))}", file=sys.stderr)
    try:
        if hasattr(r, "headers") and r.headers:
            for hk in ("x-rate-limit-limit", "x-rate-limit-remaining", "x-rate-limit-reset", "retry-after"):
                v = r.headers.get(hk) if hasattr(r.headers, "get") else None
                if v is not None:
                    print(f"{prefix}{hk}: {v}", file=sys.stderr)
    except Exception:
        pass
    if hasattr(r, "text") and r.text:
        print(f"{prefix}Body: {r.text[:500]}", file=sys.stderr)


def test_get_me(client, backend: str):
    """Test read endpoint (often works when POST /2/tweets returns 503)."""
    try:
        if backend == "xdk":
            me = client.users.get_me()
            data = me.get("data") if isinstance(me, dict) else getattr(me, "data", me)
            if data:
                uname = data.get("username") or getattr(data, "username", None)
                name = data.get("name") or getattr(data, "name", "")
                return True, f"@{uname} ({name})" if uname else str(data)
            return False, "No user data"
        else:
            me = client.get_me(user_fields=["username", "name"])
            if me.data:
                return True, f"@{me.data.username} ({me.data.name})"
            return False, "No user data"
    except Exception as e:
        _dump_response(e, "  [get_me] ")
        return False, str(e)


def post_with_retry(client, text: str, backend: str, max_attempts: int = 6) -> tuple[bool, str | None]:
    """
    Post with exponential backoff. X recommends: start 5s, double each attempt.
    Attempts: 5s, 10s, 20s, 40s, 80s, 160s (total ~5 min).
    """
    base_wait = 5
    last_err = None
    for attempt in range(1, max_attempts + 1):
        try:
            if backend == "xdk":
                from xdk.posts.models import CreateRequest
                resp = client.posts.create(CreateRequest(text=text))
                data = resp.get("data") if isinstance(resp, dict) else resp
                tid = data.get("id") if isinstance(data, dict) else getattr(data, "id", None)
                return True, str(tid) if tid else None
            else:
                resp = client.create_tweet(text=text)
                return True, resp.data.get("id")
        except Exception as e:
            last_err = str(e)
            if attempt == 1:
                _dump_response(e, f"  [create_tweet via {backend}] ")
            err_lower = last_err.lower()
            is_retryable = "503" in err_lower or "429" in err_lower or "service unavailable" in err_lower or "rate limit" in err_lower
            wait = base_wait * (2 ** (attempt - 1))
            if hasattr(e, "response") and e.response is not None:
                headers = getattr(e.response, "headers", None)
                if headers and hasattr(headers, "get"):
                    ra = headers.get("Retry-After")
                    if ra is not None:
                        wait = min(int(ra) if str(ra).isdigit() else 60, 180)
            if attempt < max_attempts and is_retryable:
                print(f"  Attempt {attempt}/{max_attempts} failed: {e}", file=sys.stderr)
                print(f"  Retrying in {wait}s (exponential backoff)...", file=sys.stderr)
                time.sleep(wait)
            else:
                return False, last_err
    return False, last_err


def main():
    parser = argparse.ArgumentParser(description="Test X API posting with 503 workaround")
    parser.add_argument("--dry-run", action="store_true", help="Only verify credentials, do not post")
    parser.add_argument("--persist", action="store_true", help="Retry every 5 min until post succeeds")
    parser.add_argument("--xdk", action="store_true", help="Use official X SDK (api.x.com) instead of Tweepy (api.twitter.com)")
    parser.add_argument("--text", default="Test from philly-sports-news bot (503 workaround).", help="Tweet text")
    args = parser.parse_args()

    client, err_or_backend = get_client(use_xdk=args.xdk)
    if client is None:
        print(f"Error: {err_or_backend}", file=sys.stderr)
        sys.exit(1)
    backend = err_or_backend
    print(f"Using {backend} ({'api.x.com' if args.xdk else 'api.twitter.com'})")
    print("Step 1: Verifying credentials (get_me)...")
    ok, msg = test_get_me(client, backend)
    if not ok:
        print(f"  FAIL: {msg}", file=sys.stderr)
        sys.exit(1)
    print(f"  OK: {msg}")

    if args.dry_run:
        print("Dry-run: credentials OK. Run without --dry-run to test posting.")
        sys.exit(0)

    text = args.text[:280] if len(args.text) > 280 else args.text

    while True:
        print("\nStep 2: Posting test tweet (exponential backoff)...")
        success, result = post_with_retry(client, text, backend)
        if success:
            print(f"  SUCCESS: Posted tweet id {result}")
            break
        print(f"  FAIL: {result}", file=sys.stderr)
        if not args.persist:
            print("\nX API returned 503/429. Try --persist to retry every 5 min until it works.", file=sys.stderr)
            sys.exit(1)
        print("  Retrying in 5 min...")
        time.sleep(300)


if __name__ == "__main__":
    main()
