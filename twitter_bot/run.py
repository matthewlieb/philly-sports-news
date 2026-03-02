#!/usr/bin/env python3
"""
Daily Philly sports tweet bot for @sport_philly (Matthew Lieb).

Run from repo root:
  python -m twitter_bot.run

Uses scrapers and utils from the parent philly-sports-news app; loads env from
repo root .env_x (or .env). See README.md in this folder.
"""
import os
import sys

# Repo root = parent of twitter_bot (so .env_x and scrapers/ live there)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
os.chdir(_REPO_ROOT)

# Use certifi for SSL so RSS (and other urllib) work on macOS when system certs are missing
try:
    import ssl
    import certifi
    ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())
except ImportError:
    pass


def _load_env():
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


_load_env()


# ---------------------------------------------------------------------------
# Gather articles (reuse philly-sports-news scrapers + merge/rank)
# ---------------------------------------------------------------------------

def _build_all_articles():
    from scrapers.source_collectors import collect_articles_for_team
    from utils.article_filter import get_source_name_from_url, merge_and_rank_articles

    all_articles = []
    for team in ("eagles", "sixers", "phillies", "flyers"):
        try:
            sources = collect_articles_for_team(team)
            for src in sources:
                titles = src.get("titles", [])
                urls = src.get("urls", [])
                images = src.get("images", []) or [None] * len(titles)
                blurbs = src.get("blurbs", [])
                authors = src.get("authors", []) or ["-- Unknown"] * len(titles)
                n = max(len(titles), len(urls), len(blurbs), len(authors), len(images))
                for i in range(n):
                    url = urls[i] if i < len(urls) else ""
                    if not url or not url.startswith("http"):
                        continue
                    all_articles.append({
                        "title": (titles[i] if i < len(titles) else "").strip(),
                        "url": url,
                        "image": images[i] if i < len(images) else None,
                        "description": (blurbs[i] if i < len(blurbs) else "").strip(),
                        "author": authors[i] if i < len(authors) else "-- Unknown",
                        "source": get_source_name_from_url(url),
                    })
        except Exception as e:
            print(f"Warning: collect_articles_for_team({team}) failed: {e}", file=sys.stderr)
            continue

    ranked = merge_and_rank_articles(all_articles, max_articles=20)
    return ranked


# ---------------------------------------------------------------------------
# Track tweeted article URLs (avoid reusing the same article)
# ---------------------------------------------------------------------------

_TWEETED_URLS_FILE = os.path.join(_REPO_ROOT, "twitter_bot", "data", "tweeted_urls.txt")
_MAX_TWEETED_URLS = 500


def _load_tweeted_urls() -> set[str]:
    """Load set of already-tweeted article URLs from DB (if DATABASE_URL) or file."""
    if os.environ.get("DATABASE_URL"):
        return _load_tweeted_urls_from_db()
    return _load_tweeted_urls_from_file()


def _load_tweeted_urls_from_file() -> set[str]:
    out = set()
    if not os.path.isfile(_TWEETED_URLS_FILE):
        return out
    try:
        with open(_TWEETED_URLS_FILE) as f:
            for line in f:
                u = line.strip()
                if u and u.startswith("http"):
                    out.add(u)
    except OSError:
        pass
    return out


def _load_tweeted_urls_from_db() -> set[str]:
    out = set()
    try:
        import psycopg2
        url = os.environ["DATABASE_URL"]
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS tweeted_urls (id SERIAL PRIMARY KEY, url TEXT NOT NULL, created_at TIMESTAMPTZ DEFAULT NOW())"
        )
        conn.commit()
        cur.execute(
            "SELECT url FROM tweeted_urls ORDER BY created_at DESC LIMIT %s",
            (_MAX_TWEETED_URLS,),
        )
        for (u,) in cur.fetchall():
            if u and u.startswith("http"):
                out.add(u)
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Warning: DB load tweeted_urls failed ({e}), using file", file=sys.stderr)
        return _load_tweeted_urls_from_file()
    return out


def _append_tweeted_url(url: str) -> None:
    """Append URL to tweeted list (DB if DATABASE_URL, else file)."""
    url = (url or "").strip()
    if not url or not url.startswith("http"):
        return
    if os.environ.get("DATABASE_URL"):
        _append_tweeted_url_to_db(url)
    else:
        _append_tweeted_url_to_file(url)


def _append_tweeted_url_to_file(url: str) -> None:
    try:
        os.makedirs(os.path.dirname(_TWEETED_URLS_FILE), exist_ok=True)
        lines = []
        if os.path.isfile(_TWEETED_URLS_FILE):
            with open(_TWEETED_URLS_FILE) as f:
                lines = [ln.strip() for ln in f if ln.strip() and ln.strip().startswith("http")]
        lines.append(url)
        if len(lines) > _MAX_TWEETED_URLS:
            lines = lines[-_MAX_TWEETED_URLS:]
        with open(_TWEETED_URLS_FILE, "w") as f:
            for u in lines:
                f.write(u + "\n")
    except OSError as e:
        print(f"Warning: could not save tweeted URL: {e}", file=sys.stderr)


def _append_tweeted_url_to_db(url: str) -> None:
    try:
        import psycopg2
        db_url = os.environ["DATABASE_URL"]
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS tweeted_urls (id SERIAL PRIMARY KEY, url TEXT NOT NULL, created_at TIMESTAMPTZ DEFAULT NOW())")
        conn.commit()
        cur.execute("INSERT INTO tweeted_urls (url) VALUES (%s)", (url,))
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM tweeted_urls")
        (n,) = cur.fetchone()
        if n > _MAX_TWEETED_URLS:
            cur.execute(
                "DELETE FROM tweeted_urls WHERE id IN (SELECT id FROM tweeted_urls ORDER BY id ASC LIMIT %s)",
                (n - _MAX_TWEETED_URLS,),
            )
            conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Warning: could not save tweeted URL to DB: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# LangChain: structured output + voice (Matthew Lieb via config)
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field


def _get_voice_prompt_block():
    try:
        from twitter_bot.config.voice import VOICE_DESCRIPTION, EXAMPLE_TWEETS
    except ImportError:
        VOICE_DESCRIPTION = "Philly sports fan, casual and not very serious."
        EXAMPLE_TWEETS = []
    block = VOICE_DESCRIPTION.strip()
    if EXAMPLE_TWEETS:
        examples = [e for e in EXAMPLE_TWEETS if isinstance(e, str) and e.strip()]
        if examples:
            block += "\n\nExamples of your tweets (match this voice and length):\n"
            block += "\n".join(f'- "{ex.strip()}"' for ex in examples)
    return block


class TweetOutput(BaseModel):
    tweet_text: str = Field(
        description="The tweet text, max 280 characters. Must include the exact article_url below and phillysportdaily.com. Be concise, Philly fan voice."
    )
    article_url: str = Field(
        description="One of the exact article URLs from the list above. Copy it character-for-character."
    )
    headline_used: str = Field(
        description="The exact headline from the article you chose (for logging)."
    )


def generate_tweet(articles: list[dict], openai_api_key: str) -> TweetOutput | None:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    if not articles:
        return None

    lines = []
    for i, a in enumerate(articles[:10], 1):
        title = (a.get("title") or "").strip()
        url = (a.get("url") or "").strip()
        blurb = (a.get("description") or "")[:200].strip()
        if title and url:
            lines.append(f"{i}. HEADLINE: {title}\n   URL: {url}\n   BLURB: {blurb}")

    articles_block = "\n\n".join(lines) if lines else "No articles."
    allowed_urls = [a.get("url", "").strip() for a in articles if a.get("url")]
    voice_block = _get_voice_prompt_block()

    system = """{voice_block}

Rules for this tweet:
- tweet_text MUST be at most 280 characters.
- tweet_text MUST include the exact article_url you choose and "phillysportdaily.com".
- article_url MUST be one of the exact URLs from the list below (copy character-for-character).
- DO NOT just repeat or paraphrase the headline. The tweet must lead with YOUR reaction, take, joke, question, or angle (e.g. "BREAKING:", "This is wild.", "So we're doing this again?", a stat, or sarcasm)—then reference the story and include the link. If the tweet could be mistaken for a news headline, rewrite it to add your voice.
- The list below contains only articles we have NOT tweeted yet; pick one of these."""

    user = """Use ONLY the following articles. Pick one and use its exact URL.

{articles_block}

Write a tweet that REACTS to or comments on the article in your voice—do not just restate the headline. Include the exact article URL and phillysportdaily.com. Respond with tweet_text (full tweet, under 280 chars), article_url (exact URL from the list), and headline_used (exact headline from the article)."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system),
        ("human", user),
    ])
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=openai_api_key, temperature=0.7)
    structured_llm = llm.with_structured_output(TweetOutput)
    chain = prompt | structured_llm
    out = chain.invoke({"articles_block": articles_block, "voice_block": voice_block})

    if out.article_url not in allowed_urls:
        out.article_url = allowed_urls[0] if allowed_urls else ""
        for a in articles:
            if a.get("url") == out.article_url:
                out.headline_used = a.get("title", "")
                break
    return out


# ---------------------------------------------------------------------------
# Post to X
# ---------------------------------------------------------------------------
# Uses official X SDK (xdk) first — api.x.com per docs.x.com. Falls back to
# Tweepy (api.twitter.com) if xdk fails. Both use OAuth 1.0a, same credentials.

def _post_via_xdk(text: str, api_key: str, api_secret: str, access: str, access_secret: str) -> tuple[bool, str | None]:
    """Post via official X SDK (api.x.com). Returns (success, error_hint)."""
    try:
        from xdk import Client
        from xdk.oauth1_auth import OAuth1
        from xdk.posts.models import CreateRequest

        oauth1 = OAuth1(
            api_key=api_key,
            api_secret=api_secret,
            callback="oob",
            access_token=access,
            access_token_secret=access_secret,
        )
        client = Client(auth=oauth1)
        resp = client.posts.create(CreateRequest(text=text))
        data = resp.get("data") if isinstance(resp, dict) else getattr(resp, "data", None)
        if data:
            tid = data.get("id") if isinstance(data, dict) else getattr(data, "id", None)
            if tid:
                print(f"Posted tweet id: {tid} (via xdk/api.x.com)")
                return True, None
        return False, "No tweet id in response"
    except Exception as e:
        err_str = str(e).lower()
        hint = "503" if "503" in err_str or "service unavailable" in err_str else ("429" if "429" in err_str or "rate limit" in err_str else None)
        return False, hint or str(e)


def _post_via_tweepy(text: str, api_key: str, api_secret: str, access: str, access_secret: str) -> tuple[bool, str | None]:
    """Post via Tweepy (api.twitter.com). Returns (success, error_hint)."""
    import tweepy

    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access,
        access_token_secret=access_secret,
    )
    try:
        resp = client.create_tweet(text=text)
        print(f"Posted tweet id: {resp.data['id']} (via tweepy/api.twitter.com)")
        return True, None
    except Exception as e:
        err_str = str(e).lower()
        hint = "503" if "503" in err_str or "service unavailable" in err_str else ("429" if "429" in err_str or "rate limit" in err_str else None)
        return False, hint or str(e)


def post_tweet(text: str) -> tuple[bool, str | None]:
    """Returns (success, error_hint). Tries xdk (api.x.com) then tweepy (api.twitter.com) with retries."""
    import time

    api_key = os.environ.get("X_API_KEY") or os.environ.get("X_CONSUMER_KEY")
    api_secret = os.environ.get("X_API_SECRET") or os.environ.get("X_CONSUMER_SECRET")
    access = os.environ.get("X_ACCESS_TOKEN")
    access_secret = os.environ.get("X_ACCESS_TOKEN_SECRET")

    if not all((api_key, api_secret, access, access_secret)):
        print("Missing X credentials. Set X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET in .env_x (repo root)", file=sys.stderr)
        return False, None

    if len(text) > 280:
        text = text[:277] + "..."

    max_attempts = 6
    base_wait = 5
    last_err = None
    backends = [
        ("xdk (api.x.com)", lambda: _post_via_xdk(text, api_key, api_secret, access, access_secret)),
        ("tweepy (api.twitter.com)", lambda: _post_via_tweepy(text, api_key, api_secret, access, access_secret)),
    ]

    is_retryable = True
    for attempt in range(1, max_attempts + 1):
        for name, post_fn in backends:
            success, hint = post_fn()
            if success:
                return True, None
            last_err = hint
            err_lower = (hint or "").lower()
            is_retryable = "503" in err_lower or "429" in err_lower or "service unavailable" in err_lower or "rate limit" in err_lower
            print(f"Post via {name} failed ({hint})", file=sys.stderr)

        if attempt < max_attempts and is_retryable:
            wait = base_wait * (2 ** (attempt - 1))
            print(f"Retrying in {wait}s (attempt {attempt}/{max_attempts})...", file=sys.stderr)
            time.sleep(wait)

    hint = "503" if last_err and ("503" in str(last_err).lower() or "service unavailable" in str(last_err).lower()) else ("429" if last_err and ("429" in str(last_err).lower() or "rate limit" in str(last_err).lower()) else None)
    print(f"Post failed: {last_err}", file=sys.stderr)
    return False, hint


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        print("Set OPENAI_API_KEY in .env_x (repo root)", file=sys.stderr)
        sys.exit(1)

    print("Fetching articles...")
    articles = _build_all_articles()
    if not articles:
        print("No articles found.", file=sys.stderr)
        sys.exit(1)
    print(f"Ranked {len(articles)} articles.")

    tweeted_urls = _load_tweeted_urls()
    candidates = [a for a in articles if (a.get("url") or "").strip() not in tweeted_urls]
    if not candidates:
        print("No new articles to tweet (all have been used recently). Exiting.", file=sys.stderr)
        sys.exit(0)
    if len(candidates) < len(articles):
        print(f"Excluding {len(articles) - len(candidates)} already-tweeted articles; {len(candidates)} candidates.")

    print("Generating tweet (LangChain + your voice)...")
    out = generate_tweet(candidates, openai_key)
    if not out:
        print("Tweet generation failed.", file=sys.stderr)
        sys.exit(1)

    tweet = out.tweet_text.strip()
    if "phillysportdaily.com" not in tweet:
        tweet = tweet.rstrip()
        if len(tweet) + 24 <= 280:
            tweet += " phillysportdaily.com"
        else:
            tweet = tweet[:255].rstrip() + " phillysportdaily.com"

    print(f"Tweet ({len(tweet)} chars): {tweet[:80]}...")
    print(f"Article URL: {out.article_url}")
    print(f"Headline: {out.headline_used[:60]}...")

    success, hint = post_tweet(tweet)
    if success:
        _append_tweeted_url(out.article_url)
        print("Done.")
    else:
        if hint in ("503", "429"):
            print("X API unavailable (503/429). Will retry next scheduled run.", file=sys.stderr)
            sys.exit(0)
        sys.exit(1)


if __name__ == "__main__":
    main()
