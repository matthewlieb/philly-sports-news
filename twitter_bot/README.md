# Twitter bot for @sport_philly

Daily Philly sports tweets: **3 tweets per day** (historic, article, day-in-review). Uses Tavily for up-to-date search, LangChain for structured output, and your voice from `config/voice.py`. No DALE/images. **Only the article tweet (midday) ends with phillysportdaily.com**; historic and day_review are pure fan tweets with no domain.

## Run from repo root

```bash
cd /path/to/philly-sports-news
pip install -r requirements.txt   # includes tweepy, langchain-openai, langchain-core, tavily-python
python -m twitter_bot.run
```

**Test X without posting:** `python -m twitter_bot.test_x` — verifies credentials. If it prints "X API OK", keys are fine.

**Dry-run (generate tweet but don't post):** `python -m twitter_bot.run --dry-run` or `DRY_RUN=1 python -m twitter_bot.run` — runs the full pipeline and prints what would be posted without calling the X API.

**Test posting with 503 workaround:** `python -m twitter_bot.test_post_503` — posts a test tweet with exponential backoff.

Env is loaded from the repo root: `.env_x` (or `.env`). Required keys:

- `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`
- `OPENAI_API_KEY`

Optional:

- `TAVILY_API_KEY` – used for all three slots (historic search, article search, day-in-review). Without it, historic/day_review use fallback context and article slot falls back to scrapers only.
- `DATABASE_URL` – if set (e.g. Postgres), the bot stores tweeted URLs and a `tweet_log` table (slot, text hash, URL) to avoid duplicates and same-slot twice per day across restarts.

## Three daily slots

Each run posts **one** tweet based on the current time (or `TWEET_SLOT` env):

| Slot        | Time (UTC) | Time (ET) | Content |
|------------|------------|-----------|---------|
| **historic**   | 13:00      | 8:00 AM   | “On this day” in Philadelphia sports history (Eagles, 76ers, Phillies, Flyers). Tavily + LangChain. No link, no domain. |
| **article**    | 18:00      | 1:00 PM   | One article of the day (Eagles/Sixers/Flyers/Phillies). Tavily first, scrapers as fallback. **Includes link and ends with phillysportdaily.com** (only tweet of the day with the domain). |
| **day_review** | 03:00      | 10:00 PM  | Day in review: wrap-up of Philly sports news across all four teams. Tavily + LangChain. No link, no domain. |

- **historic** and **day_review** are text-only, no article link and no phillysportdaily.com (pure fan content; bio link is the main conversion).
- **article** is the only tweet that ends with phillysportdaily.com and includes the article URL.
- The bot skips a slot if it already posted that slot today (by UTC date), and avoids posting very similar tweets (content hash) within 7–14 days.

Override the slot for a manual run: `TWEET_SLOT=historic python -m twitter_bot.run` (or `article`, `day_review`).

## Layout

- `run.py` – entry point: detect slot, generate tweet, post (Tweepy/xdk).
- `tweet_slots.py` – slot logic, Tavily search, LangChain generators, tweet tracking (file or DB).
- `config/voice.py` – `VOICE_DESCRIPTION` and `EXAMPLE_TWEETS`. Edit to match your voice.
- `data/tweeted_urls.txt` – Article URLs already tweeted (no reuse); trimmed to last 500.
- `data/last_tweeted_team.txt` – Last team used for article rotation.
- `data/last_slot_date.txt` – Which slot was posted on which date (avoid same slot twice per day).
- `data/tweet_hashes.txt` – Content hashes of recent tweets (avoid near-duplicates).
- `docs/` – bot-specific docs.

## Scheduling

GitHub Actions runs the workflow at **3 times per day** (see `.github/workflows/tweet-schedule.yml`): 03:00, 13:00, 18:00 UTC. The runner infers the slot from the hour and posts one tweet per run.

From repo root, e.g. cron:

```bash
0 3,13,18 * * * cd /path/to/philly-sports-news && python -m twitter_bot.run
```

Or Heroku Scheduler / GitHub Actions with the same command and env vars. Ensure **TAVILY_API_KEY** is set in secrets for best results.

## Database (optional)

If you set `DATABASE_URL` (e.g. Heroku Postgres or another Postgres):

- **tweeted_urls** – same as file: URLs we already tweeted (article slot).
- **tweet_log** – one row per posted tweet: `slot_type`, `tweet_text` (truncated), `content_hash`, `article_url`, `posted_at`. Used to:
  - Enforce “at most one post per slot per day”.
  - Avoid reposting the same or very similar tweet within a configurable window (e.g. 14 days for historic, 7 for day_review).

The bot creates the tables if they don’t exist. Without `DATABASE_URL`, it uses the `data/` files above (and the workflow commits them after each run).

## Ready to test

1. From repo root, install deps and run once (this will **post a real tweet** for the current slot):

   ```bash
   cd /path/to/philly-sports-news
   pip install -r requirements.txt
   python -m twitter_bot.run
   ```

2. Ensure `.env_x` has `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`, `OPENAI_API_KEY`, and `TAVILY_API_KEY`.

3. The script will pick the slot from the current UTC hour (or `TWEET_SLOT`), generate one tweet, and post to @sport_philly. Check [https://x.com/sport_philly](https://x.com/sport_philly) after running.

**Why “no articles” for some feeds?** The article slot uses Tavily first; if Tavily returns few results, it falls back to the same scrapers as the website (SBNation, NBC Sports, PhillyVoice, etc.). If a few sources fail, the rest still supply articles.
