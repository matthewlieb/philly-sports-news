# Deploying (Railway + Upstash)

Production runs on [Railway](https://railway.com) (project `philly-sports-news`) with a free [Upstash](https://upstash.com) Redis database (`philly-sports-news-cache`).

## Services

| Railway service | What it runs | Schedule (UTC) |
|---|---|---|
| `web` | `gunicorn` from the `Procfile`, serves phillysportdaily.com | always on |
| `daily-briefs` | `python -m jobs.daily_briefs` (writes one brief per team) | `0 11 * * *` (7am ET in summer, 6am in winter) |
| `tweet-bot` | `python -m twitter_bot.run` (one tweet per run) | `0 3,13,18 * * *` |

All three build from this GitHub repo. Cron services start, do their work and exit, so they cost almost nothing.

## Environment variables

| Variable | Services | Notes |
|---|---|---|
| `REDIS_URL` | all | Upstash `rediss://` URL. Append `?health_check_interval=30&socket_keepalive=true&retry_on_timeout=true&socket_timeout=10` |
| `OPENAI_API_KEY` | all | Briefs and tweets |
| `TAVILY_API_KEY` | all | News search |
| `API_KEY` | web | YouTube Data API key (optional; no video without it) |
| `GA_MEASUREMENT_ID` | web | Google Analytics 4 ID, e.g. `G-XXXXXXX` (optional) |
| `GOOGLE_SITE_VERIFICATION` | web | Search Console HTML-tag verification code (optional) |
| `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET` | tweet-bot | X OAuth 1.0a credentials |
| `BRIEF_MODEL`, `TWEET_MODEL` | optional | Override the OpenAI model (default `gpt-5.4-mini`) |

## Redis keys

Everything the app stores is under the `psd:` prefix (Flask-Caching uses `flask_cache_`):

- `psd:brief:<team>:<date>`, `psd:briefs:<team>`, `psd:briefs:all`: daily briefs (permanent)
- `psd:bot:*`: tweeted URLs, last team, posted slots, recent tweet hashes
- `psd:views:<date>:<path>`: daily pageview counts (bots excluded)

Keep **eviction off** on the Upstash database so briefs are never dropped; page cache entries all expire on their own.

## Domain

`www.phillysportdaily.com` is a CNAME to Railway (managed at Squarespace Domains, formerly Google Domains). The bare domain forwards to `www` through Squarespace.

## Useful commands

```bash
railway logs --service web
railway run --service daily-briefs python -m jobs.daily_briefs   # write today's briefs now
TWEET_SLOT=article python -m twitter_bot.run --dry-run            # preview a tweet locally
```
