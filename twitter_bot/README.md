# Tweet bot for @sport_philly

Posts three tweets a day, scheduled on Railway (service `tweet-bot`, cron `0 3,13,18 * * *`). The UTC hour of the run picks the slot:

| Slot | UTC | Eastern | Tweet |
|---|---|---|---|
| `brief` | 13:00 | 9am (8am in winter) | A hook from today's daily brief, linking to it on phillysportdaily.com |
| `article` | 18:00 | 2pm (1pm) | A take on one fresh story, linking to the story and the team page |
| `day_review` | 03:00 | 11pm (10pm) | Wrap-up of the day, no link |
| `historic` | manual only | | "On this day", only if a search result confirms a moment on today's date |

How it works:

- The model writes only the words; links are appended in code, and length is measured the way X does (every link counts as 23 characters), so links are never cut off.
- Every tweet must stick to facts in the material it was given (brief, article text or search results).
- What has been posted lives in Redis (`psd:bot:*`): one post per slot per day, no repeat articles, no identical tweets within 14 days, and team rotation.
- Voice and example tweets: `config/voice.py`.

## Running locally

```bash
python -m twitter_bot.run --dry-run                  # slot from current UTC hour, prints instead of posting
TWEET_SLOT=brief python -m twitter_bot.run --dry-run
python -m twitter_bot.test_x                         # check X credentials without posting
```

Env comes from `.env_x` / `.env` in the repo root: `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`, `OPENAI_API_KEY`, `TAVILY_API_KEY`, and `REDIS_URL` (without it, state is in-memory and forgotten after the run).
