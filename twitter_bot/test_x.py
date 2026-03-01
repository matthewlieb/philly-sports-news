#!/usr/bin/env python3
"""
Test X (Twitter) API credentials without posting.

Run from repo root:
  python -m twitter_bot.test_x

Verifies OAuth 1.0a credentials by calling the API (e.g. get_me).
If you see "X API OK" then credentials and permissions are fine.
503 when posting is a known intermittent X API issue; retry later.
"""

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
os.chdir(_REPO_ROOT)

# Load .env_x
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


def main():
    import tweepy

    api_key = os.environ.get("X_API_KEY") or os.environ.get("X_CONSUMER_KEY")
    api_secret = os.environ.get("X_API_SECRET") or os.environ.get("X_CONSUMER_SECRET")
    access = os.environ.get("X_ACCESS_TOKEN")
    access_secret = os.environ.get("X_ACCESS_TOKEN_SECRET")

    if not all((api_key, api_secret, access, access_secret)):
        print("Missing X credentials. Set X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET in .env_x", file=sys.stderr)
        sys.exit(1)

    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access,
        access_token_secret=access_secret,
    )

    try:
        me = client.get_me(user_fields=["username", "name"])
        if me.data:
            print(f"X API OK — logged in as @{me.data.username} ({me.data.name})")
            print("Your API keys are working. Posting should work when X is not returning 503.")
        else:
            print("X API responded but no user data.", file=sys.stderr)
            sys.exit(1)
    except tweepy.TwitterServerError as e:
        code = getattr(e.response, "status_code", None) or getattr(e.response, "status", None)
        print(f"X API returned HTTP {code} (server error).", file=sys.stderr)
        print("This is X's side — their servers are overloaded or down, not your keys.", file=sys.stderr)
        print("Try again in a few minutes or check status.twitter.com.", file=sys.stderr)
        sys.exit(1)
    except tweepy.Unauthorized:
        print("X API returned 401 Unauthorized.", file=sys.stderr)
        print("Your API keys or access token are invalid or expired. Check .env_x and regenerate tokens in the X Developer Portal.", file=sys.stderr)
        sys.exit(1)
    except tweepy.Forbidden:
        print("X API returned 403 Forbidden.", file=sys.stderr)
        print("App may be Read-only. Set User authentication → App permissions to Read and write, then regenerate the Access Token.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"X API error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
