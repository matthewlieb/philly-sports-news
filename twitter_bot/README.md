# Twitter bot for @sport_philly

Daily Philly sports tweets using scraped articles + LangChain + OpenAI. Voice and examples are in `config/voice.py`.

## Run from repo root

```bash
cd /path/to/philly-sports-news
pip install -r requirements.txt   # includes tweepy, langchain-openai, langchain-core
python -m twitter_bot.run
```

**Test X without posting:** `python -m twitter_bot.test_x` — verifies credentials. If it prints "X API OK", keys are fine.

**Test posting with 503 workaround:** `python -m twitter_bot.test_post_503` — posts a test tweet with exponential backoff (6 attempts over ~5 min). Use `--dry-run` to verify keys only, `--xdk` to use official X SDK (api.x.com) instead of Tweepy (api.twitter.com), or `--persist` to retry every 5 min until X accepts the post.

Env is loaded from the repo root: `.env_x` (or `.env`). Required keys:

- `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`
- `OPENAI_API_KEY`

## Layout

- `run.py` – entry point: fetch articles, generate tweet (LangChain + voice), post (Tweepy).
- `config/voice.py` – `VOICE_DESCRIPTION` and `EXAMPLE_TWEETS`. Edit to match your voice.
- `data/tweeted_urls.txt` – URLs we already tweeted (no reuse); trimmed to last 500.
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
