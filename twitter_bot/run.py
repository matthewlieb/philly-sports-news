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
                        "team": team,
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
_LAST_TWEETED_TEAM_FILE = os.path.join(_REPO_ROOT, "twitter_bot", "data", "last_tweeted_team.txt")
_LAST_CONTENT_TYPE_FILE = os.path.join(_REPO_ROOT, "twitter_bot", "data", "last_content_type.txt")
_LAST_TWEET_PREVIEW_FILE = os.path.join(_REPO_ROOT, "twitter_bot", "data", "last_tweet_preview.json")
_MAX_TWEETED_URLS = 500
_MAX_PREVIEW_HEADLINES = 3
# Keep total tweet ≤240 so "phillysportdaily.com" is never truncated in UI
_MAX_TWEET_CHARS = 240
_PHILLYSPORTDAILY_SUFFIX = " phillysportdaily.com"  # 22 chars
_PHILLYSPORTDAILY_SUFFIX_ALT = " more: phillysportdaily.com"  # 28 chars
_STANDALONE_INCLUDE_PLUG_PROB = 0.5  # ~50% of standalones omit domain (bio link = main conversion)

# Content types: article (link to story), standalone (trending, no article). No AI-generated images.
CONTENT_TYPES = ("article", "standalone")
# Weights: article 67%, standalone 33%. Avoid streaks by down-weighting last type.
_CONTENT_WEIGHTS = {"article": 0.67, "standalone": 0.33}


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


def _load_last_tweeted_team() -> str | None:
    """Load last tweeted team for sports rotation."""
    if not os.path.isfile(_LAST_TWEETED_TEAM_FILE):
        return None
    try:
        with open(_LAST_TWEETED_TEAM_FILE) as f:
            t = f.read().strip().lower()
            return t if t in ("eagles", "sixers", "phillies", "flyers") else None
    except OSError:
        return None


def _save_last_tweeted_team(team: str) -> None:
    """Save last tweeted team for sports rotation."""
    team = (team or "").strip().lower()
    if team not in ("eagles", "sixers", "phillies", "flyers"):
        return
    try:
        os.makedirs(os.path.dirname(_LAST_TWEETED_TEAM_FILE), exist_ok=True)
        with open(_LAST_TWEETED_TEAM_FILE, "w") as f:
            f.write(team + "\n")
    except OSError as e:
        print(f"Warning: could not save last tweeted team: {e}", file=sys.stderr)


def _load_last_content_type() -> str | None:
    """Load last content type for variety (avoid streaks)."""
    if not os.path.isfile(_LAST_CONTENT_TYPE_FILE):
        return None
    try:
        with open(_LAST_CONTENT_TYPE_FILE) as f:
            t = f.read().strip().lower()
            return t if t in CONTENT_TYPES else None
    except OSError:
        return None


def _save_last_content_type(content_type: str) -> None:
    """Save last content type for variety."""
    if content_type not in CONTENT_TYPES:
        return
    try:
        os.makedirs(os.path.dirname(_LAST_CONTENT_TYPE_FILE), exist_ok=True)
        with open(_LAST_CONTENT_TYPE_FILE, "w") as f:
            f.write(content_type + "\n")
    except OSError as e:
        print(f"Warning: could not save last content type: {e}", file=sys.stderr)


def _load_last_tweet_preview() -> tuple[str | None, list[str]]:
    """Load last tweet opening (first ~35 chars) and last N headlines to avoid same story / same opening."""
    opening: str | None = None
    headlines: list[str] = []
    if not os.path.isfile(_LAST_TWEET_PREVIEW_FILE):
        return opening, headlines
    try:
        import json
        with open(_LAST_TWEET_PREVIEW_FILE) as f:
            data = json.load(f)
        opening = (data.get("opening") or "").strip()[:35] or None
        headlines = list(data.get("headlines") or [])[:_MAX_PREVIEW_HEADLINES]
    except (OSError, ValueError):
        pass
    return opening, headlines


def _save_last_tweet_preview(tweet_text: str, headline: str) -> None:
    """Save last tweet opening and headline so next run can avoid same story / repeated opening."""
    opening = (tweet_text or "").strip()[:35]
    if not opening:
        return
    try:
        import json
        os.makedirs(os.path.dirname(_LAST_TWEET_PREVIEW_FILE), exist_ok=True)
        prev_opening, prev_headlines = _load_last_tweet_preview()
        new_headlines = [headline.strip() for headline in [headline] if headline.strip()]
        for h in prev_headlines:
            if h and h != (headline or "").strip() and h not in new_headlines:
                new_headlines.append(h)
        data = {"opening": opening, "headlines": new_headlines[:_MAX_PREVIEW_HEADLINES]}
        with open(_LAST_TWEET_PREVIEW_FILE, "w") as f:
            json.dump(data, f, indent=0)
    except OSError as e:
        print(f"Warning: could not save last tweet preview: {e}", file=sys.stderr)


def choose_content_type() -> str:
    """Pick content type with weighted random, down-weighting last type to avoid streaks."""
    import random
    last = _load_last_content_type()
    weights = list(_CONTENT_WEIGHTS.items())
    if last:
        # Reduce weight of last type by half
        adjusted = []
        for ct, w in weights:
            if ct == last:
                adjusted.append((ct, w * 0.5))
            else:
                adjusted.append((ct, w))
        total = sum(w for _, w in adjusted)
        weights = [(ct, w / total) for ct, w in adjusted]
    choices, probs = zip(*weights)
    return random.choices(choices, weights=probs, k=1)[0]


# ---------------------------------------------------------------------------
# LangChain: structured output + voice (Matthew Lieb via config)
# ---------------------------------------------------------------------------
# All tweet generation uses LangChain (ChatOpenAI + with_structured_output) so
# outputs conform to Pydantic schemas. Article tweets always plug phillysportdaily.com;
# standalone tweets use include_plug (≈50%) so some tweets plug the site.

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
        description="The tweet text, max 240 characters. Must include the exact article_url and end with phillysportdaily.com or 'more: phillysportdaily.com'. Be concise."
    )
    article_url: str = Field(
        description="One of the exact article URLs from the list above. Copy it character-for-character."
    )
    headline_used: str = Field(
        description="The exact headline from the article you chose (for logging)."
    )


def generate_tweet(
    articles: list[dict],
    openai_api_key: str,
    last_tweeted_team: str | None = None,
    avoid_opening: str | None = None,
    recent_headlines: list[str] | None = None,
) -> TweetOutput | None:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    if not articles:
        return None

    lines = []
    for i, a in enumerate(articles[:10], 1):
        title = (a.get("title") or "").strip()
        url = (a.get("url") or "").strip()
        blurb = (a.get("description") or "")[:200].strip()
        team = (a.get("team") or "").strip()
        if title and url:
            team_tag = f" [TEAM: {team}]" if team else ""
            lines.append(f"{i}. HEADLINE: {title}\n   URL: {url}\n   BLURB: {blurb}{team_tag}")

    articles_block = "\n\n".join(lines) if lines else "No articles."
    allowed_urls = [a.get("url", "").strip() for a in articles if a.get("url")]
    voice_block = _get_voice_prompt_block()

    variety_rules = []
    if avoid_opening:
        variety_rules.append(f"- Do NOT start this tweet with the same opening as last time. Last tweet started with: \"{avoid_opening[:35]}...\". Use a different lead-in; no single formula.")
    else:
        variety_rules.append("- Vary your openings. Don't start multiple tweets in a row with the same phrase. Use whatever fits: a stat, a question, a hot take, BREAKING when it's actually breaking—no single formula.")
    if recent_headlines:
        variety_rules.append(f"- Do NOT write about the same story as these recent tweets. Pick a different article/topic. Recent headlines we already tweeted: {', '.join(repr(h[:50]) for h in recent_headlines[:3])}.")
    variety_rules_str = "\n".join(variety_rules)

    system = """{voice_block}

Rules for this tweet:
- tweet_text MUST be at most 240 characters total so the full tweet (including phillysportdaily.com) is visible and never truncated.
- tweet_text MUST include the exact article_url you choose and MUST end with "phillysportdaily.com" or "more: phillysportdaily.com" (vary which you use).
- article_url MUST be one of the exact URLs from the list below (copy character-for-character).
- CRITICAL: The tweet must be ONLY about the one article you choose. The link in your tweet must be that article's URL. Do not mention, summarize, or link to any other article or story. The tweet content must directly react to or discuss the headline and topic of the chosen article only.
- DO NOT just repeat or paraphrase the headline. Lead with YOUR reaction, take, joke, question, or angle—then reference the story and include the link.
{variety_rules_str}
- The list below contains only articles we have NOT tweeted yet; pick one of these.
- Balance teams: prefer Eagles, Sixers, Phillies, and Flyers in rotation. Do not tweet Eagles (or any one team) multiple times in a row. Prefer a different team than last time when possible."""

    rotation_hint = ""
    if last_tweeted_team:
        others = [t for t in ("eagles", "sixers", "phillies", "flyers") if t != last_tweeted_team]
        rotation_hint = f"\nLast tweet was {last_tweeted_team}. Prefer picking from {', '.join(others)} this time.\n\n"

    user = """{rotation_hint}Use ONLY the following articles. Pick ONE article. Your tweet must be exclusively about that article—do not reference or link to any other story. Use that article's exact URL in your tweet.

{articles_block}

Write a tweet that REACTS to or comments on the article you chose—do not just restate the headline. The tweet must be solely about that article; the link in the tweet must be that article's URL. Include the exact article URL and end with phillysportdaily.com or "more: phillysportdaily.com" (vary which you use). Keep it under 240 characters total so the domain is never cut off. Respond with tweet_text (full tweet), article_url (exact URL from the list for the article you wrote about), and headline_used (exact headline from that article)."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system),
        ("human", user),
    ])
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=openai_api_key, temperature=0.7)
    structured_llm = llm.with_structured_output(TweetOutput)
    chain = prompt | structured_llm
    out = chain.invoke({
        "articles_block": articles_block,
        "voice_block": voice_block,
        "variety_rules_str": variety_rules_str,
        "rotation_hint": rotation_hint,
    })

    if out.article_url not in allowed_urls:
        # Model returned a URL not in the list—don't use that tweet (would mismatch link and content). Generate for first candidate only.
        fallback_article = articles[0]
        fallback_out = _generate_tweet_for_single_article(
            fallback_article, openai_api_key, voice_block=voice_block, variety_rules_str=variety_rules_str
        )
        if fallback_out:
            return fallback_out
        out.article_url = allowed_urls[0] if allowed_urls else ""
        for a in articles:
            if (a.get("url") or "").strip() == out.article_url:
                out.headline_used = (a.get("title") or "").strip()
                break
    # Ensure tweet text contains the article URL we're using (tweet must be about this article)
    if out.article_url and out.article_url not in (out.tweet_text or ""):
        out.tweet_text = ((out.tweet_text or "").rstrip() + " " + out.article_url).strip()
    return out


def _generate_tweet_for_single_article(
    article: dict,
    openai_api_key: str,
    voice_block: str,
    variety_rules_str: str,
) -> TweetOutput | None:
    """Generate a tweet for exactly one article (LangChain structured output). Used when main generator returns wrong URL."""
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    url = (article.get("url") or "").strip()
    title = (article.get("title") or "").strip()
    blurb = (article.get("description") or "")[:200].strip()
    if not url or not title:
        return None

    system = f"""{voice_block}

Rules for this tweet:
- tweet_text MUST be at most 240 characters total and MUST end with "phillysportdaily.com" or "more: phillysportdaily.com".
- tweet_text MUST include this exact URL: {url}
- The tweet must be ONLY about this article. Do not reference any other story.
{variety_rules_str}
- Lead with YOUR reaction, take, joke, or angle—do not just restate the headline."""

    user = """Write a tweet about ONLY this article. Use the exact URL in your tweet and end with phillysportdaily.com or "more: phillysportdaily.com". Keep under 240 characters.

HEADLINE: {title}
URL: {url}
BLURB: {blurb}

Respond with tweet_text (full tweet including the URL), article_url (exact URL above), and headline_used (exact headline above)."""

    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", user)])
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=openai_api_key, temperature=0.7)
    structured_llm = llm.with_structured_output(TweetOutput)
    chain = prompt | structured_llm
    try:
        out = chain.invoke({"title": title, "url": url, "blurb": blurb})
    except Exception:
        return None
    if out and (out.article_url or "").strip() == url:
        if out.article_url not in (out.tweet_text or ""):
            out.tweet_text = ((out.tweet_text or "").rstrip() + " " + url).strip()
        return out
    return TweetOutput(tweet_text=f"{title[:180]} {url} phillysportdaily.com", article_url=url, headline_used=title)


class StandaloneTweetOutput(BaseModel):
    tweet_text: str = Field(
        description="The tweet text, max 240 characters. Must end with phillysportdaily.com or 'more: phillysportdaily.com'. No article link."
    )


class StandaloneTweetOutputNoPlug(BaseModel):
    tweet_text: str = Field(
        description="The tweet text, max 280 characters. No links or domains. Pure fan take: stat, hot take, reaction, or historical note."
    )


def generate_standalone_tweet(trending_context: str, openai_api_key: str, include_plug: bool = True) -> StandaloneTweetOutput | StandaloneTweetOutputNoPlug | None:
    """Generate a standalone tweet (no article) from trending/context. When include_plug is False, no domain (pure fan content)."""
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    voice_block = _get_voice_prompt_block()
    if include_plug:
        system = f"""{voice_block}

Rules for this tweet:
- tweet_text MUST be at most 240 characters total. End with "phillysportdaily.com" or "more: phillysportdaily.com".
- NO article link. This is a standalone tweet: can be a reaction to trending news, a stat, a historical moment, a hot take, or a question—not everything has to be article-based.
- Lead with YOUR reaction, joke, stat, "On this day," hot take, or question. Vary openings; no single formula.
- Balance teams when relevant: Eagles, Sixers, Phillies, Flyers. Use hashtags when it fits (#Eagles #sixers #phillies #flyers #TTP #FlyEaglesFly)."""
        user = """Use this trending/context to write a standalone tweet (no article link):

{trending_context}

Write a tweet: reaction to news, a stat, a historical note, or a hot take about Philly sports. Include phillysportdaily.com or "more: phillysportdaily.com" at the end. Keep under 240 chars."""
        out_model = StandaloneTweetOutput
    else:
        system = f"""{voice_block}

Rules for this tweet:
- tweet_text MUST be at most 280 characters. Do NOT include phillysportdaily.com or any URL. This is pure fan content—no link, no plug. The bio link handles discovery.
- Standalone: a stat, a hot take, "on this day," a reaction to news, or a question. One concrete detail (number, name, year) beats vague praise.
- Lead with YOUR take. Vary openings; no single formula. Balance teams when relevant (Eagles, Sixers, Phillies, Flyers). Hashtags when it fits."""
        user = """Use this trending/context to write a standalone tweet with NO link and NO domain:

{trending_context}

Write a pure fan tweet: stat, hot take, historical moment, or reaction. No phillysportdaily.com. Max 280 characters."""
        out_model = StandaloneTweetOutputNoPlug

    prompt = ChatPromptTemplate.from_messages([
        ("system", system),
        ("human", user),
    ])
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=openai_api_key, temperature=0.8)
    structured_llm = llm.with_structured_output(out_model)
    chain = prompt | structured_llm
    return chain.invoke({"trending_context": trending_context})


def search_trending_philly_sports() -> str:
    """Search Tavily for trending Philly sports news. Returns context string for LLM."""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "Philadelphia Eagles, 76ers, Phillies, Flyers - general Philly sports news."

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        resp = client.search(
            "Philadelphia Eagles 76ers Phillies Flyers trending news today",
            topic="news",
            search_depth="basic",
            max_results=5,
        )
        results = resp.get("results") or []
        if not results:
            return "Philadelphia Eagles, 76ers, Phillies, Flyers - general Philly sports news."

        lines = []
        for r in results[:5]:
            title = (r.get("title") or "").strip()
            content = (r.get("content") or "")[:300].strip()
            if title or content:
                lines.append(f"- {title}: {content}")
        return "\n".join(lines) if lines else "Philadelphia Eagles, 76ers, Phillies, Flyers - general Philly sports news."
    except Exception as e:
        print(f"Warning: Tavily search failed ({e}), using fallback context", file=sys.stderr)
        return "Philadelphia Eagles, 76ers, Phillies, Flyers - general Philly sports news."


# ---------------------------------------------------------------------------
# Post to X
# ---------------------------------------------------------------------------
# Uses official X SDK (xdk) first — api.x.com per docs.x.com. Falls back to
# Tweepy (api.twitter.com) if xdk fails. Both use OAuth 1.0a, same credentials.

def _upload_media(media_path: str, api_key: str, api_secret: str, access: str, access_secret: str) -> str | None:
    """Upload media via Tweepy v1.1 API. Returns media_id or None."""
    import tweepy
    auth = tweepy.OAuth1UserHandler(
        api_key, api_secret, access, access_secret
    )
    api = tweepy.API(auth)
    try:
        media = api.media_upload(media_path)
        return str(media.media_id) if media and media.media_id else None
    except Exception as e:
        print(f"Warning: media upload failed: {e}", file=sys.stderr)
        return None


def _post_via_xdk(text: str, api_key: str, api_secret: str, access: str, access_secret: str, media_ids: list[str] | None = None) -> tuple[bool, str | None]:
    """Post via official X SDK (api.x.com). Returns (success, error_hint)."""
    try:
        from xdk import Client
        from xdk.oauth1_auth import OAuth1
        from xdk.posts.models import CreateRequest, CreateRequestMedia

        oauth1 = OAuth1(
            api_key=api_key,
            api_secret=api_secret,
            callback="oob",
            access_token=access,
            access_token_secret=access_secret,
        )
        client = Client(auth=oauth1)
        media = CreateRequestMedia(media_ids=media_ids) if media_ids else None
        resp = client.posts.create(CreateRequest(text=text, media=media))
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


def _post_via_tweepy(text: str, api_key: str, api_secret: str, access: str, access_secret: str, media_ids: list[str] | None = None) -> tuple[bool, str | None]:
    """Post via Tweepy (api.twitter.com). Returns (success, error_hint)."""
    import tweepy

    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access,
        access_token_secret=access_secret,
    )
    try:
        kwargs = {"text": text}
        if media_ids:
            kwargs["media_ids"] = [int(m) if str(m).isdigit() else m for m in media_ids]
        resp = client.create_tweet(**kwargs)
        print(f"Posted tweet id: {resp.data['id']} (via tweepy/api.twitter.com)")
        return True, None
    except Exception as e:
        err_str = str(e).lower()
        hint = "503" if "503" in err_str or "service unavailable" in err_str else ("429" if "429" in err_str or "rate limit" in err_str else None)
        return False, hint or str(e)


def post_tweet(text: str, media_path: str | None = None) -> tuple[bool, str | None]:
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

    media_ids = None
    if media_path and os.path.isfile(media_path):
        media_id = _upload_media(media_path, api_key, api_secret, access, access_secret)
        if media_id:
            media_ids = [media_id]

    max_attempts = 6
    base_wait = 5
    last_err = None
    backends = [
        ("xdk (api.x.com)", lambda: _post_via_xdk(text, api_key, api_secret, access, access_secret, media_ids)),
        ("tweepy (api.twitter.com)", lambda: _post_via_tweepy(text, api_key, api_secret, access, access_secret, media_ids)),
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


def _strip_domain_from_text(text: str) -> str:
    """Remove phillysportdaily.com and 'more: phillysportdaily.com' from text (for no-plug standalones)."""
    if not text or "phillysportdaily.com" not in text:
        return text
    out = text.replace(" more: phillysportdaily.com", "").replace("more: phillysportdaily.com", "")
    out = out.replace(" phillysportdaily.com", "").replace("phillysportdaily.com", "")
    return " ".join(out.split()).strip()


def _ensure_suffix(tweet: str) -> str:
    """Ensure tweet has phillysportdaily.com (or 'more: phillysportdaily.com') and is ≤240 chars so the domain is never truncated in UI. Randomly uses plain or 'more:' when appending."""
    import random
    max_len = _MAX_TWEET_CHARS
    if "phillysportdaily.com" not in tweet:
        tweet = tweet.rstrip()
        suffix = random.choice((_PHILLYSPORTDAILY_SUFFIX, _PHILLYSPORTDAILY_SUFFIX_ALT))
        if len(tweet) + len(suffix) <= max_len:
            tweet += suffix
        else:
            tweet = tweet[: max_len - len(suffix)].rstrip() + suffix
    if len(tweet) > max_len:
        if "phillysportdaily.com" in tweet:
            idx = tweet.find("phillysportdaily.com")
            suffix_part = tweet[idx:]
            max_prefix = max_len - len(suffix_part)
            tweet = tweet[:max_prefix].rstrip() + " " + suffix_part
        else:
            tweet = tweet[:max_len]
    return tweet


# ---------------------------------------------------------------------------
# Main — 3 tweets per day: historic (morning), article (midday), day_review (~10pm ET)
# No DALE/images. All tweets end with phillysportdaily.com.
# ---------------------------------------------------------------------------

def main():
    dry_run = "--dry-run" in sys.argv or os.environ.get("DRY_RUN", "").strip().lower() in ("1", "true", "yes")
    if dry_run:
        print("DRY RUN: will not post to X.")

    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        print("Set OPENAI_API_KEY in .env_x (repo root)", file=sys.stderr)
        sys.exit(1)

    from twitter_bot import tweet_slots

    slot = tweet_slots.get_tweet_slot()
    print(f"Tweet slot: {slot}")

    if tweet_slots.already_posted_slot_today(slot):
        print(f"Already posted {slot} today. Skipping.")
        sys.exit(0)

    # ---- Historic (morning): on this day in Philly sports ----
    if slot == "historic":
        print("Searching on-this-day Philly sports history (Tavily)...")
        out = tweet_slots.generate_historic_tweet(openai_key)
        if not out:
            print("Historic tweet generation failed.", file=sys.stderr)
            sys.exit(1)
        tweet = out.tweet_text
        ch = tweet_slots.content_hash_for_dedup(tweet)
        if tweet_slots.content_hash_seen_recently(ch, days=14):
            print("Very similar historic tweet posted recently. Skipping to avoid duplicate.")
            sys.exit(0)
        print(f"Tweet ({len(tweet)} chars): {tweet[:80]}...")
        if dry_run:
            print(f"DRY RUN: would post: {tweet}")
            return
        success, hint = post_tweet(tweet)
        if success:
            tweet_slots.record_tweet("historic", tweet, None)
            print("Done.")
        else:
            if hint in ("503", "429"):
                print("X API unavailable (503/429). Will retry next scheduled run.", file=sys.stderr)
                sys.exit(0)
            sys.exit(1)
        return

    # ---- Article (midday): one article reference from Eagles/Sixers/Flyers/Phillies ----
    if slot == "article":
        print("Searching today's Philly sports articles (Tavily)...")
        articles = tweet_slots.search_article_philly_sports()
        if not articles or len(articles) < 2:
            print("Tavily returned few results; using scrapers as fallback.")
            ranked = _build_all_articles()
            articles = [
                {"title": a.get("title") or "", "url": (a.get("url") or "").strip(), "content": (a.get("description") or "")[:300]}
                for a in (ranked or [])
                if (a.get("url") or "").strip()
            ]
        if not articles:
            print("No articles found.", file=sys.stderr)
            sys.exit(1)
        print(f"Using {len(articles)} article(s).")
        tweeted_urls = _load_tweeted_urls()
        last_team = _load_last_tweeted_team()
        out = tweet_slots.generate_article_tweet(articles, openai_key, tweeted_urls, last_team)
        if not out:
            print("Article tweet generation failed.", file=sys.stderr)
            sys.exit(1)
        tweet = out.tweet_text
        print(f"Tweet ({len(tweet)} chars): {tweet[:80]}...")
        print(f"Article URL: {out.article_url}")
        if dry_run:
            print(f"DRY RUN: would post: {tweet}")
            return
        success, hint = post_tweet(tweet)
        if success:
            _append_tweeted_url(out.article_url)
            tweet_slots.record_tweet("article", tweet, out.article_url)
            # Infer team from URL/headline for rotation if possible
            for team in ("eagles", "sixers", "phillies", "flyers"):
                if team in (out.headline_used or "").lower() or team in (out.article_url or "").lower():
                    _save_last_tweeted_team(team)
                    break
            print("Done.")
        else:
            if hint in ("503", "429"):
                print("X API unavailable (503/429). Will retry next scheduled run.", file=sys.stderr)
                sys.exit(0)
            sys.exit(1)
        return

    # ---- Day in review (~10pm ET): Eagles, Sixers, Phillies, Flyers wrap-up ----
    if slot == "day_review":
        print("Searching day-in-review Philly sports (Tavily)...")
        out = tweet_slots.generate_day_review_tweet(openai_key)
        if not out:
            print("Day review tweet generation failed.", file=sys.stderr)
            sys.exit(1)
        tweet = out.tweet_text
        ch = tweet_slots.content_hash_for_dedup(tweet)
        if tweet_slots.content_hash_seen_recently(ch, days=7):
            print("Very similar day review posted recently. Skipping.")
            sys.exit(0)
        print(f"Tweet ({len(tweet)} chars): {tweet[:80]}...")
        if dry_run:
            print(f"DRY RUN: would post: {tweet}")
            return
        success, hint = post_tweet(tweet)
        if success:
            tweet_slots.record_tweet("day_review", tweet, None)
            print("Done.")
        else:
            if hint in ("503", "429"):
                print("X API unavailable (503/429). Will retry next scheduled run.", file=sys.stderr)
                sys.exit(0)
            sys.exit(1)
        return

    print("Unknown slot.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
