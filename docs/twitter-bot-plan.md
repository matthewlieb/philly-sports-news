# Philly Sports Daily – X/Twitter Automation Plan

**Account:** [@sport_philly](https://x.com/sport_philly)  
**Goal:** Daily Philly sports tweets from scraped news + AI, driving traffic to phillysportdaily.com.

---

## Feasibility: **Yes**

You already have the main pieces:

| Piece | Status |
|-------|--------|
| **Content source** | philly-sports-news scrapers (Eagles, Sixers, Phillies, Flyers from Bleeding Green Nation, Liberty Ballers, PhillyVoice, NBC, official sites, etc.) |
| **AI generation** | Same pattern as instabot: OpenAI (or Anthropic) for short, on-brand copy from structured input |
| **X API posting** | Official API + Tweepy; free tier supports posting (see below) |
| **Scheduling** | Cron, Heroku Scheduler, or GitHub Actions so tweets go out daily |
| **Traffic to site** | Every tweet can include a link to phillysportdaily.com (and optional ad-friendly CTA) |

---

## X/Twitter API (2024–2025)

- **Posting:** [Manage Tweets API](https://developer.x.com/en/docs/twitter-api/tweets/manage-tweets/integrate) – create tweets (and optionally media) with OAuth 1.0a user context.
- **Free tier (typical):** ~1,500 posts/month at app level, write access, media posts allowed. Enough for 1–2 tweets per day.
- **Python:** [Tweepy](https://docs.tweepy.org/) 4.14+ with API v2; `client.create_tweet(text=...)` plus optional media.
- **Credentials:** API Key, API Key Secret, Access Token, Access Token Secret (and Bearer Token for some read ops). Set app to "Read and Write" in the [Developer Portal](https://developer.x.com/).

---

## Architecture (high level)

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. SCHEDULE (cron / Heroku Scheduler / GitHub Actions)           │
│    e.g. once per day at 9:00 AM ET                               │
└───────────────────────────────┬─────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. FETCH (reuse philly-sports-news)                             │
│    collect_articles_for_team("eagles") (and/or sixers, etc.)    │
│    → list of {title, url, image, blurb, source}                  │
└───────────────────────────────┬─────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. PICK (logic or random)                                       │
│    e.g. top 3–5 articles, or one per team, or "story of day"    │
└───────────────────────────────┬─────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. GENERATE (OpenAI or Anthropic)                               │
│    Input: title, blurb, source, link to phillysportdaily.com     │
│    Output: 1–2 short tweet texts (≤280 chars) + optional CTA   │
│    Optional: LangChain for structured output (e.g. Pydantic)      │
└───────────────────────────────┬─────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. POST (Tweepy + X API)                                        │
│    create_tweet(text=..., optional media=image)                 │
│    Always include phillysportdaily.com (e.g. in bio + in tweets) │
└─────────────────────────────────────────────────────────────────┘
```

---

## Reuse from your codebases

**From philly-sports-news**

- `scrapers/source_collectors.collect_articles_for_team(team)` → same articles you show on the site.
- Optionally reuse `scrapers/fetcher`, `scrapers/rss_scraper` if you want a smaller script that only pulls RSS.

**From instabot**

- **OpenAI:** Same pattern as `QuoteGenerator` / `generate_youtube_metadata`: env `OPENAI_API_KEY`, call `client.chat.completions.create()` with a system + user prompt.
- **Config:** Theme-style config (e.g. "tone: casual, Philly fan, include link to phillysportdaily.com") in a small config file or env.
- **Logging:** Same style (log to file + console, errors with traceback).

**Optional**

- **LangChain:** Use when you want structured output (e.g. "headline + tweet_body + hashtags" as JSON/Pydantic) or chained steps (fetch → summarize → tweet).
- **Tavily:** Only if you want to add *search* (e.g. "latest Eagles trade rumor") on top of your scraped articles; not required for "daily top from our scrapers."

**Voice (Matthew Lieb)**

- **`twitter_bot/config/voice.py`** holds `VOICE_DESCRIPTION` and `EXAMPLE_TWEETS` (few-shot). Paste real tweets from [@sport_philly](https://x.com/sport_philly) for best consistency.

---

## Suggested implementation steps

1. **X developer setup**  
   Create app at developer.x.com, enable Read and Write, get credentials. Add to `.env_x` (copy from `.env_x.example`): `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`. Generate "Access Token and Secret" for your user (Keys and tokens → User authentication) so the app can tweet as @sport_philly.

2. **Run the bot**  
   From repo root: `python -m twitter_bot.run`. The bot lives in the **`twitter_bot/`** folder (separate module). It loads `.env_x` from the repo root and uses the main app's `scrapers/` and `utils/`. Voice and few-shot examples: `twitter_bot/config/voice.py`.

3. **Include phillysportdaily.com in every tweet**  
   The LangChain prompt and script fallback in `twitter_bot/run.py` ensure every tweet includes phillysportdaily.com.

4. **Schedule**  
   - **Local:** cron `0 9 * * * cd /path/to/repo && python -m twitter_bot.run`  
   - **Heroku:** Heroku Scheduler add-on, one dyno run per day.  
   - **GitHub Actions:** workflow on schedule that runs the script (needs secrets for X + OpenAI).

5. **Later**  
   - Add image (article thumbnail or satire image) to tweets.  
   - Rotate teams (Eagles one day, Sixers another).  
   - Optional: satire images via DALL·E / image APIs (see `twitter_bot/docs/satire-images.md`).

---

## Summary

- **Feasible:** Yes. You have content (scrapers), AI (OpenAI/Anthropic like instabot), and a clear X API path (Tweepy, free tier).
- **Traffic + ads:** Using @sport_philly to tweet daily and link to phillysportdaily.com fits your goal of driving traffic and ad impressions.
- **Next step:** Create an X developer app, add **`twitter_bot/`** (run with `python -m twitter_bot.run`), set `.env_x`, then add a daily schedule.
