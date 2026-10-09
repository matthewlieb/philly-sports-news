#!/usr/bin/env python3
"""@sport_philly tweet bot. Scheduled on Railway at 03:00, 13:00 and 18:00 UTC.

The UTC hour picks the slot:
  13:00  brief       hook + link to today's daily brief on phillysportdaily.com
  18:00  article     a take on one story, linking to it and the team page
  03:00  day_review  night wrap-up, no link
TWEET_SLOT=brief|article|day_review|historic overrides. --dry-run prints instead of posting.

Run from repo root: python -m twitter_bot.run
"""
import os
import sys
import time

from dotenv import load_dotenv

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_REPO_ROOT, ".env_x"))
load_dotenv(os.path.join(_REPO_ROOT, ".env"))

from twitter_bot import state, tweet_slots  # noqa: E402


def _post_via_xdk(text, api_key, api_secret, access, access_secret):
    from xdk import Client
    from xdk.oauth1_auth import OAuth1
    from xdk.posts.models import CreateRequest

    auth = OAuth1(api_key=api_key, api_secret=api_secret, callback="oob",
                  access_token=access, access_token_secret=access_secret)
    resp = Client(auth=auth).posts.create(CreateRequest(text=text))
    data = resp.get("data") if isinstance(resp, dict) else getattr(resp, "data", None)
    tid = (data.get("id") if isinstance(data, dict) else getattr(data, "id", None)) if data else None
    if not tid:
        raise RuntimeError(f"No tweet id in response: {resp}")
    return tid


def _post_via_tweepy(text, api_key, api_secret, access, access_secret):
    import tweepy

    client = tweepy.Client(consumer_key=api_key, consumer_secret=api_secret,
                           access_token=access, access_token_secret=access_secret)
    return client.create_tweet(text=text).data["id"]


def post_tweet(text: str) -> bool:
    """Post via the official X SDK, falling back to Tweepy; retries rate limits and outages."""
    creds = [os.environ.get(k) for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET")]
    if not all(creds):
        print("Missing X credentials (X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET).", file=sys.stderr)
        return False

    for attempt in range(1, 5):
        retryable = False
        for name, fn in (("xdk", _post_via_xdk), ("tweepy", _post_via_tweepy)):
            try:
                tid = fn(text, *creds)
                print(f"Posted tweet {tid} via {name}: https://x.com/i/status/{tid}")
                return True
            except Exception as e:
                err = str(e)
                print(f"Post via {name} failed: {err[:500]}", file=sys.stderr)
                retryable = retryable or any(s in err.lower() for s in ("503", "429", "service unavailable", "rate limit"))
        if not retryable:
            break
        time.sleep(15 * attempt)
    return False


def main():
    dry_run = "--dry-run" in sys.argv or os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")
    slot = tweet_slots.get_tweet_slot()
    print(f"Slot: {slot}{' (dry run)' if dry_run else ''}")

    if not dry_run and state.slot_posted_today(slot):
        print(f"Already posted the {slot} tweet today. Skipping.")
        return

    tweet = tweet_slots.WRITERS[slot]()
    if not tweet or not tweet.text:
        print(f"Nothing to tweet for {slot}.", file=sys.stderr)
        sys.exit(1)
    if not dry_run and state.seen_recently(tweet.text):
        print("An identical tweet went out recently. Skipping.")
        return

    print(f"Tweet ({tweet_slots.x_length(tweet.text)}/280):\n{tweet.text}")
    if dry_run:
        return
    if not post_tweet(tweet.text):
        sys.exit(1)
    state.record(slot, tweet.text, url=tweet.url, team=tweet.team)


if __name__ == "__main__":
    main()
