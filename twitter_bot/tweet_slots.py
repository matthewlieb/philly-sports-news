"""
Three daily tweet slots for @sport_philly:
1. historic — morning: "on this day" in Philadelphia sports history (Tavily)
2. article — midday: one article reference for Eagles/Sixers/Flyers/Phillies (Tavily)
3. day_review — ~10pm ET: day in review for Philly sports (Tavily)

Only the article tweet (midday) ends with phillysportdaily.com. Historic and day_review are pure fan tweets, no domain. No DALE/images.
"""

from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Literal

SlotType = Literal["historic", "article", "day_review"]

# Repo root for imports
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def get_tweet_slot() -> SlotType:
    """Determine which slot to run: env TWEET_SLOT overrides; else derive from UTC hour.
    Cron: 13:00 UTC = morning (historic), 18:00 UTC = article, 02:00 or 03:00 UTC = day_review.
    """
    slot = (os.environ.get("TWEET_SLOT") or "").strip().lower()
    if slot in ("historic", "article", "day_review"):
        return slot
    now = datetime.now(timezone.utc)
    h = now.hour
    if h == 13:
        return "historic"
    if h == 18:
        return "article"
    if h in (2, 3):
        return "day_review"
    # Manual run or other hour: default to article so we always have something to try
    return "article"


# ---------------------------------------------------------------------------
# Tavily search helpers
# ---------------------------------------------------------------------------

def _tavily_client():
    try:
        from tavily import TavilyClient
        key = os.environ.get("TAVILY_API_KEY")
        if key:
            return TavilyClient(api_key=key)
    except Exception:
        pass
    return None


def tavily_search(
    query: str,
    topic: str = "news",
    search_depth: str = "basic",
    max_results: int = 8,
    time_range: str | None = None,
) -> list[dict]:
    """Run Tavily search; return list of result dicts (title, url, content)."""
    client = _tavily_client()
    if not client:
        return []
    try:
        kwargs = {
            "query": query,
            "topic": topic,
            "search_depth": search_depth,
            "max_results": max_results,
        }
        if time_range:
            kwargs["time_range"] = time_range
        resp = client.search(**kwargs)
        return list(resp.get("results") or [])
    except Exception as e:
        print(f"Tavily search failed: {e}", file=sys.stderr)
        return []


def search_historic_philly_sports() -> str:
    """Search for 'on this day' Philadelphia sports history. Returns context string for LLM."""
    now = datetime.now(timezone.utc)
    month_day = now.strftime("%B %d")  # e.g. "March 11"
    query = f"on this day in history {month_day} Philadelphia Eagles OR 76ers OR Sixers OR Phillies OR Flyers"
    results = tavily_search(query, topic="general", max_results=6)
    if not results:
        return f"On this day ({month_day}) in Philadelphia sports history. Pick a well-known moment involving the Eagles, 76ers, Phillies, or Flyers if you know one; otherwise a notable Philly sports moment from history."
    lines = []
    for r in results[:6]:
        title = (r.get("title") or "").strip()
        content = (r.get("content") or "")[:400].strip()
        url = (r.get("url") or "").strip()
        if title or content:
            lines.append(f"- {title}\n  {content}\n  URL: {url}" if url else f"- {title}\n  {content}")
    return "\n\n".join(lines) if lines else f"On this day ({month_day}) in Philadelphia sports. Eagles, 76ers, Phillies, Flyers."


def search_article_philly_sports() -> list[dict]:
    """Search for today's Philly sports articles (Eagles, Sixers, Phillies, Flyers). Returns list of {title, url, content}."""
    query = "Philadelphia Eagles 76ers Sixers Phillies Flyers news today"
    results = tavily_search(query, topic="news", max_results=10, time_range="day")
    articles = []
    seen_urls = set()
    for r in results:
        url = (r.get("url") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        title = (r.get("title") or "").strip()
        content = (r.get("content") or "")[:300].strip()
        if title or content:
            articles.append({"title": title, "url": url, "content": content})
    return articles


def search_day_review_philly_sports() -> str:
    """Search for today's Philly sports news across all four teams. Returns context for day-in-review tweet."""
    query = "Philadelphia Eagles 76ers Sixers Phillies Flyers news today"
    results = tavily_search(query, topic="news", max_results=12, time_range="day")
    if not results:
        return "Philadelphia Eagles, 76ers, Phillies, Flyers: today's news. Summarize the main headlines or storylines from the day."
    lines = []
    for r in results[:12]:
        title = (r.get("title") or "").strip()
        content = (r.get("content") or "")[:350].strip()
        if title or content:
            lines.append(f"- {title}: {content}")
    return "\n".join(lines) if lines else "Philly sports today: Eagles, Sixers, Phillies, Flyers."


# ---------------------------------------------------------------------------
# Tweet tracking (DB or file) — avoid duplicates and same-slot twice in one day
# ---------------------------------------------------------------------------

def _content_hash(text: str) -> str:
    """Normalized hash for dedup (strip, lower, remove extra spaces)."""
    normalized = " ".join((text or "").strip().lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def content_hash_for_dedup(text: str) -> str:
    """Return content hash for a tweet (for duplicate check)."""
    return _content_hash(text)


def already_posted_slot_today(slot_type: SlotType) -> bool:
    """True if we already posted this slot today (UTC date)."""
    if os.environ.get("DATABASE_URL"):
        return _already_posted_slot_today_db(slot_type)
    return _already_posted_slot_today_file(slot_type)


def _already_posted_slot_today_file(slot_type: SlotType) -> bool:
    data_dir = os.path.join(_REPO_ROOT, "twitter_bot", "data")
    path = os.path.join(data_dir, "last_slot_date.txt")
    if not os.path.isfile(path):
        return False
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        with open(path) as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2 and parts[0] == slot_type and parts[1] == today:
                    return True
    except OSError:
        pass
    return False


def _already_posted_slot_today_db(slot_type: SlotType) -> bool:
    try:
        import psycopg2
        url = os.environ["DATABASE_URL"]
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute(
            """SELECT 1 FROM tweet_log WHERE slot_type = %s AND (posted_at AT TIME ZONE 'UTC')::date = CURRENT_DATE LIMIT 1""",
            (slot_type,),
        )
        found = cur.fetchone() is not None
        cur.close()
        conn.close()
        return found
    except Exception as e:
        print(f"DB check slot today failed: {e}", file=sys.stderr)
        return False


def content_hash_seen_recently(content_hash: str, days: int = 14) -> bool:
    """True if we already posted a tweet with this content hash in the last `days` days."""
    if os.environ.get("DATABASE_URL"):
        return _content_hash_seen_db(content_hash, days)
    return _content_hash_seen_file(content_hash, days)


def _content_hash_seen_file(content_hash: str, days: int) -> bool:
    data_dir = os.path.join(_REPO_ROOT, "twitter_bot", "data")
    path = os.path.join(data_dir, "tweet_hashes.txt")
    if not os.path.isfile(path):
        return False
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Format: "hash YYYY-MM-DD"
                parts = line.split()
                if len(parts) >= 2 and parts[0] == content_hash:
                    if parts[1] >= cutoff:
                        return True
    except OSError:
        pass
    return False


def _content_hash_seen_db(content_hash: str, days: int) -> bool:
    try:
        import psycopg2
        url = os.environ["DATABASE_URL"]
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute(
            """SELECT 1 FROM tweet_log WHERE content_hash = %s AND posted_at > NOW() - (%s::text || ' days')::interval LIMIT 1""",
            (content_hash, days),
        )
        found = cur.fetchone() is not None
        cur.close()
        conn.close()
        return found
    except Exception as e:
        print(f"DB content_hash check failed: {e}", file=sys.stderr)
        return False


def record_tweet(slot_type: SlotType, tweet_text: str, article_url: str | None = None) -> None:
    """Record that we posted this tweet (for duplicate/slot tracking)."""
    content_hash = _content_hash(tweet_text)
    if os.environ.get("DATABASE_URL"):
        _record_tweet_db(slot_type, tweet_text, content_hash, article_url)
    else:
        _record_tweet_file(slot_type, tweet_text, content_hash, article_url)


def _record_tweet_file(slot_type: SlotType, tweet_text: str, content_hash: str, article_url: str | None) -> None:
    data_dir = os.path.join(_REPO_ROOT, "twitter_bot", "data")
    os.makedirs(data_dir, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # Append this slot+date so we don't post same slot twice today
    slot_date_path = os.path.join(data_dir, "last_slot_date.txt")
    try:
        with open(slot_date_path, "a") as f:
            f.write(f"{slot_type} {today}\n")
        # Trim to last ~200 lines (multiple slots per day)
        with open(slot_date_path) as f:
            lines = f.readlines()
        if len(lines) > 200:
            with open(slot_date_path, "w") as f:
                f.writelines(lines[-200:])
    except OSError as e:
        print(f"Could not save last_slot_date: {e}", file=sys.stderr)
    hash_path = os.path.join(data_dir, "tweet_hashes.txt")
    try:
        with open(hash_path, "a") as f:
            f.write(f"{content_hash} {today}\n")
        # Trim to last ~500 lines
        with open(hash_path) as f:
            lines = f.readlines()
        if len(lines) > 500:
            with open(hash_path, "w") as f:
                f.writelines(lines[-500:])
    except OSError as e:
        print(f"Could not save tweet hash: {e}", file=sys.stderr)


def _record_tweet_db(slot_type: SlotType, tweet_text: str, content_hash: str, article_url: str | None) -> None:
    try:
        import psycopg2
        url = os.environ["DATABASE_URL"]
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS tweet_log (
                id SERIAL PRIMARY KEY,
                slot_type TEXT NOT NULL,
                tweet_text TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                article_url TEXT,
                posted_at TIMESTAMPTZ DEFAULT NOW()
            )"""
        )
        conn.commit()
        cur.execute(
            "INSERT INTO tweet_log (slot_type, tweet_text, content_hash, article_url) VALUES (%s, %s, %s, %s)",
            (slot_type, tweet_text[:500], content_hash, article_url),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Could not record tweet to DB: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# LangChain generators (structured output, system prompts)
# ---------------------------------------------------------------------------

def _get_voice_block() -> str:
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
            block += "\n".join(f'- "{ex.strip()}"' for ex in examples[:5])
    return block


# Article tweet only: max 240 chars so "phillysportdaily.com" is never truncated
_MAX_TWEET_CHARS = 240
_SUFFIX = " phillysportdaily.com"
_SUFFIX_ALT = " more: phillysportdaily.com"
_MAX_PURE_FAN_CHARS = 280  # historic and day_review: no domain


def _trim_to_280(text: str) -> str:
    """Trim to 280 chars (for tweets without phillysportdaily.com)."""
    text = (text or "").strip()
    if len(text) <= _MAX_PURE_FAN_CHARS:
        return text
    return text[:_MAX_PURE_FAN_CHARS].rstrip()


def _ensure_suffix(text: str) -> str:
    import random
    if "phillysportdaily.com" not in text:
        text = text.rstrip()
        suffix = random.choice((_SUFFIX, _SUFFIX_ALT))
        if len(text) + len(suffix) <= _MAX_TWEET_CHARS:
            text += suffix
        else:
            text = text[: _MAX_TWEET_CHARS - len(suffix)].rstrip() + suffix
    if len(text) > _MAX_TWEET_CHARS:
        idx = text.find("phillysportdaily.com")
        if idx >= 0:
            suffix_part = text[idx:]
            text = text[: _MAX_TWEET_CHARS - len(suffix_part)].rstrip() + " " + suffix_part
        else:
            text = text[:_MAX_TWEET_CHARS]
    return text


# --- Historic (on this day) ---

class HistoricTweetOutput:
    def __init__(self, tweet_text: str):
        self.tweet_text = tweet_text


def generate_historic_tweet(openai_api_key: str) -> HistoricTweetOutput | None:
    """Generate one 'on this day' Philly sports history tweet. No article URL."""
    from pydantic import BaseModel, Field
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    class _Out(BaseModel):
        tweet_text: str = Field(
            description="Single tweet text, max 280 characters. No URL, no phillysportdaily.com. Lead with 'On this day' or similar. One historic moment only."
        )

    context = search_historic_philly_sports()
    voice = _get_voice_block()
    now = datetime.now(timezone.utc)
    month_day = now.strftime("%B %d")

    system = f"""{voice}

You write ONE tweet for the @sport_philly account: "On this day" in Philadelphia sports history.
- tweet_text MUST be at most 280 characters. Do NOT include phillysportdaily.com or any URL. Pure fan content; the bio link handles discovery.
- Lead with "On this day" (or "OTD") and one specific moment: Eagles, 76ers, Phillies, or Flyers. Include year or era. No generic fluff.
- One concrete moment per tweet. Sound like a fan, not a headline. Short and punchy.
- No article link in this tweet. This is a standalone historic fact.
- Do not repeat the same moment we may have used recently; prefer a different team or year if the context gives options."""

    user = f"""Today's date: {month_day}.

Use this search context to pick ONE "on this day" moment in Philadelphia sports history. Write a single tweet. Do NOT include phillysportdaily.com or any link. Max 280 characters.

Context:
{context}

Respond with only tweet_text (the full tweet)."""

    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", user)])
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=openai_api_key, temperature=0.6)
    structured = llm.with_structured_output(_Out)
    chain = prompt | structured
    try:
        out = chain.invoke({})
        if out and out.tweet_text:
            return HistoricTweetOutput(_trim_to_280(out.tweet_text.strip()))
    except Exception as e:
        print(f"Historic tweet generation failed: {e}", file=sys.stderr)
    return None


# --- Article (one article of the day) ---

class ArticleTweetOutput:
    def __init__(self, tweet_text: str, article_url: str, headline_used: str):
        self.tweet_text = tweet_text
        self.article_url = article_url
        self.headline_used = headline_used


def generate_article_tweet(
    articles: list[dict],
    openai_api_key: str,
    tweeted_urls: set[str],
    last_tweeted_team: str | None = None,
) -> ArticleTweetOutput | None:
    """Generate one tweet referencing a single article. Uses LangChain structured output."""
    from pydantic import BaseModel, Field
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    class _Out(BaseModel):
        tweet_text: str = Field(description="Full tweet text, max 240 chars, includes article URL and ends with phillysportdaily.com.")
        article_url: str = Field(description="Exact URL from the list you chose.")
        headline_used: str = Field(description="Exact headline from that article.")

    candidates = [a for a in articles if (a.get("url") or "").strip() not in tweeted_urls]
    if not candidates:
        return None

    voice = _get_voice_block()
    lines = []
    for i, a in enumerate(candidates[:10], 1):
        title = (a.get("title") or "").strip()
        url = (a.get("url") or "").strip()
        content = (a.get("content") or "")[:200].strip()
        if title and url:
            lines.append(f"{i}. {title}\n   URL: {url}\n   {content}")
    articles_block = "\n\n".join(lines)
    allowed_urls = [a.get("url", "").strip() for a in candidates if a.get("url")]

    system = f"""{voice}

Rules for this tweet:
- tweet_text MUST be at most 240 characters and MUST include the exact article_url you choose and MUST end with "phillysportdaily.com" or "more: phillysportdaily.com".
- article_url MUST be one of the exact URLs from the list below. Pick ONE article; the tweet must be only about that article.
- Do not just repeat the headline. Lead with YOUR reaction, take, or angle, then include the link and phillysportdaily.com.
- Balance teams (Eagles, Sixers, Phillies, Flyers). Prefer a different team than last time when possible."""

    rotation = ""
    if last_tweeted_team:
        others = [t for t in ("eagles", "sixers", "phillies", "flyers") if t != last_tweeted_team]
        rotation = f"Last tweet was about {last_tweeted_team}. Prefer one of: {', '.join(others)}.\n\n"

    user = f"""{rotation}Pick ONE article from this list. Write a tweet that reacts to it, includes that article's exact URL, and ends with phillysportdaily.com. Max 240 characters.

{articles_block}

Respond with tweet_text, article_url (exact URL from list), and headline_used."""

    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", user)])
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=openai_api_key, temperature=0.7)
    structured = llm.with_structured_output(_Out)
    chain = prompt | structured
    try:
        out = chain.invoke({})
        if not out or out.article_url not in allowed_urls:
            a = candidates[0]
            url = (a.get("url") or "").strip()
            title = (a.get("title") or "").strip()
            out = _Out(
                tweet_text=f"{title[:160]} {url} phillysportdaily.com",
                article_url=url,
                headline_used=title,
            )
        text = out.tweet_text.strip()
        if out.article_url and out.article_url not in text:
            text = text.rstrip() + " " + out.article_url
        return ArticleTweetOutput(_ensure_suffix(text), out.article_url, out.headline_used or "")
    except Exception as e:
        print(f"Article tweet generation failed: {e}", file=sys.stderr)
    return None


# --- Day in review ---

class DayReviewTweetOutput:
    def __init__(self, tweet_text: str):
        self.tweet_text = tweet_text


def generate_day_review_tweet(openai_api_key: str) -> DayReviewTweetOutput | None:
    """Generate one 'day in review' tweet covering Eagles, Sixers, Phillies, Flyers."""
    from pydantic import BaseModel, Field
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    class _Out(BaseModel):
        tweet_text: str = Field(
            description="Single tweet, max 280 characters. Day-in-review summary touching Eagles, Sixers, Phillies, and/or Flyers. No URL, no phillysportdaily.com."
        )

    context = search_day_review_philly_sports()
    voice = _get_voice_block()

    system = f"""{voice}

You write ONE "day in review" tweet for @sport_philly: a brief summary of the day's Philly sports news.
- tweet_text MUST be at most 280 characters. Do NOT include phillysportdaily.com or any URL. Pure fan content; the bio link handles discovery.
- Cover Eagles, 76ers, Phillies, and/or Flyers in one punchy summary. One line per team or one overall take. No article links in this tweet.
- Sound like a fan wrapping up the day. Short sentences. Hashtags if they fit (#FlyEaglesFly #TTP #sixers #phillies #flyers)."""

    user = f"""Use this context about today's Philly sports news to write a single "day in review" tweet. Do NOT include phillysportdaily.com or any link. Max 280 characters.

{context}

Respond with only tweet_text."""

    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", user)])
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=openai_api_key, temperature=0.6)
    structured = llm.with_structured_output(_Out)
    chain = prompt | structured
    try:
        out = chain.invoke({})
        if out and out.tweet_text:
            return DayReviewTweetOutput(_trim_to_280(out.tweet_text.strip()))
    except Exception as e:
        print(f"Day review tweet generation failed: {e}", file=sys.stderr)
    return None
