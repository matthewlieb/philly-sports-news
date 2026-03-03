# Twitter bot for @sport_philly

Daily Philly sports tweets using scraped articles + LangChain + OpenAI. Voice and examples are in `config/voice.py`.

## Run from repo root

```bash
cd /path/to/philly-sports-news
pip install -r requirements.txt   # includes tweepy, langchain-openai, langchain-core
python -m twitter_bot.run
```

**Test X without posting:** `python -m twitter_bot.test_x` — verifies credentials. If it prints "X API OK", keys are fine.

**Dry-run (generate tweet but don't post):** `python -m twitter_bot.run --dry-run` or `DRY_RUN=1 python -m twitter_bot.run` — runs the full pipeline (fetch articles or trending, generate tweet) and prints what would be posted without calling the X API.

**Test posting with 503 workaround:** `python -m twitter_bot.test_post_503` — posts a test tweet with exponential backoff (6 attempts over ~5 min). Use `--dry-run` to verify keys only, `--xdk` to use official X SDK (api.x.com) instead of Tweepy (api.twitter.com), or `--persist` to retry every 5 min until X accepts the post.

Env is loaded from the repo root: `.env_x` (or `.env`). Required keys:

- `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`
- `OPENAI_API_KEY`

Optional:

- `TAVILY_API_KEY` – for standalone/trending tweets (search). Without it, standalone tweets use fallback context.

## Content types (varied automatically)

Each run picks one:

- **article** (~52%) – React to a scraped article, include link + phillysportdaily.com
- **satire_image** (~23%) – Same as article, plus a DALL·E 3–generated satire image
- **standalone** (~25%) – No article link; comment on trending Philly sports (Tavily search). About half of standalones omit the site (pure fan content); the rest may end with phillysportdaily.com.

State is tracked in `data/last_content_type.txt` to avoid streaks. The bot also keeps `data/last_tweet_preview.json` (last opening + recent headlines) so it avoids back-to-back same-article tweets and repeated openings. Tweets that include the site are capped at 240 characters so `phillysportdaily.com` stays visible.

**Promotion strategy:** The **bio link** is the main conversion surface. Article and satire tweets always end with the domain (varied as `phillysportdaily.com` or `more: phillysportdaily.com`). About half of **standalone** tweets are pure fan content with no link or plug; the rest can include the domain. This keeps the feed from feeling like every tweet is an ad.

## Layout

- `run.py` – entry point: choose content type, fetch/generate, post (Tweepy/xdk).
- `config/voice.py` – `VOICE_DESCRIPTION` and `EXAMPLE_TWEETS`. Edit to match your voice.
- `config/image_prompts.py` – Satire image prompt templates for DALL·E 3.
- `data/tweeted_urls.txt` – URLs we already tweeted (no reuse); trimmed to last 500.
- `data/last_tweeted_team.txt` – Last team tweeted (Eagles/Sixers/Phillies/Flyers rotation).
- `data/last_content_type.txt` – Last content type (article/satire_image/standalone).
- `data/last_tweet_preview.json` – Last tweet opening + recent headlines (avoids same-article and "So..." repetition).
- `docs/` – bot-specific docs (e.g. satire-images.md).

## Scheduling

From repo root, e.g. cron:

```bash
0 9 * * * cd /path/to/philly-sports-news && python -m twitter_bot.run
```

Or Heroku Scheduler / GitHub Actions with the same command and env vars.

## Ready to test

1. From repo root, install deps and run once (this will **post a real tweet**):

   ```bash
   cd /path/to/philly-sports-news
   pip install -r requirements.txt
   python -m twitter_bot.run
   ```

2. Ensure `.env_x` has `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`, and `OPENAI_API_KEY`.

3. The script will fetch articles, generate one tweet in your voice, and post it to @sport_philly. Check [https://x.com/sport_philly](https://x.com/sport_philly) after running.

**Why "no articles" for some feeds?** The bot and the website both use many sources per team (SBNation RSS, NBC Sports, PhillyVoice, official sites, FanSided). If a few RSS URLs return HTML or empty data, the rest still supply plenty — so you still see "Ranked 20 articles" and the site works. The warnings are only for the feeds that failed that run.
