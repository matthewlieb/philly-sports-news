# Scheduling the Twitter bot (3–4 tweets per day)

The bot can run on a schedule so you tweet 3–4 times per day without hitting X API limits.

## X API rate limits (free tier)

- **500 posts per month** on the free tier.
- 3–4 tweets per day ≈ 90–120 posts/month — **well under the cap**.
- If you hit the limit, X returns 429; the bot retries with backoff. To avoid that, keep to **≤4 runs per day**.

References: [X API rate limits](https://developer.x.com/en/docs/twitter-api/rate-limits), [post cap](https://developer.x.com/en/docs/twitter-api/tweet-caps).

---

## Option A: Heroku Scheduler

If the main app is already on Heroku, use the Heroku Scheduler add-on.

### 1. Add the add-on

```bash
heroku addons:create scheduler:standard
```

Or: Heroku Dashboard → your app → **Resources** → **Add-ons** → search "Heroku Scheduler" → add.

### 2. Set config vars for the bot

In **Settings → Config Vars**, add (same values as in `.env_x` locally):

| Key | Description |
|-----|-------------|
| `X_API_KEY` | Consumer Key (API Key) |
| `X_API_SECRET` | Consumer Secret |
| `X_ACCESS_TOKEN` | Access Token |
| `X_ACCESS_TOKEN_SECRET` | Access Token Secret |
| `OPENAI_API_KEY` | OpenAI API key |

### 3. Add the job

- Open **Heroku Scheduler** from the add-on (or `heroku addons:open scheduler`).
- **Create job**, set the command to:

```bash
python -m twitter_bot.run
```

- Choose **Daily** and set the hour, or use **Every 10 minutes** and rely on a single run (Heroku Scheduler only allows one dyno type: daily at a fixed time, or every 10 min). For **3–4 times per day** you need multiple jobs:
  - Create **4 jobs**, each with the same command `python -m twitter_bot.run`, at different hours (e.g. 8:00, 12:00, 17:00, 20:00 UTC — adjust to your timezone).

Scheduler runs in a one-off dyno. The **list of tweeted URLs** is stored in `twitter_bot/data/tweeted_urls.txt`; on Heroku the filesystem is ephemeral, so that file is lost between runs and you may occasionally tweet the same article. To persist it, add **Heroku Postgres** and set `DATABASE_URL`; the bot will then store tweeted URLs in the database when `DATABASE_URL` is set (see “Persisting tweeted URLs on Heroku” below).

---

## Option B: GitHub Actions

Runs in GitHub’s runners on a cron schedule; no Heroku add-on needed. The workflow commits `twitter_bot/data/tweeted_urls.txt` after each run so the next run avoids repeating articles.

### 1. Add repository secrets

Repo → **Settings → Secrets and variables → Actions** → **New repository secret**. Add:

- `X_API_KEY`
- `X_API_SECRET`
- `X_ACCESS_TOKEN`
- `X_ACCESS_TOKEN_SECRET`
- `OPENAI_API_KEY`

(Use the same values as in `.env_x`.)

### 2. Add the workflow file

Create `.github/workflows/tweet-schedule.yml` (see below). It runs **4 times per day** (1:00, 13:00, 18:00, 21:00 UTC — roughly 8pm, 8am, 1pm, 6pm ET). Edit the `cron` if you want different times.

### 3. Allow the workflow to push

The workflow commits `twitter_bot/data/tweeted_urls.txt` after a successful tweet. In **Settings → Actions → General**, under “Workflow permissions”, choose **Read and write permissions**, then save.

---

## Persisting tweeted URLs on Heroku (optional)

On Heroku Scheduler, one-off dynos have an ephemeral filesystem, so by default `twitter_bot/data/tweeted_urls.txt` is lost between runs. To avoid re-tweeting the same articles:

1. Add **Heroku Postgres**: Resources → Add-ons → Heroku Postgres (e.g. Mini or Essential-0).
2. Heroku sets `DATABASE_URL` automatically. Redeploy the app so the bot has `psycopg2-binary` (already in `requirements.txt`).
3. The bot uses `DATABASE_URL` when set: it creates a `tweeted_urls` table and reads/writes there instead of the file. No code or config change needed.

---

## Summary

| Method | Runs/day | Persists tweeted URLs? |
|--------|----------|-------------------------|
| **Heroku Scheduler** | 1–4 (configure multiple jobs) | No (unless you add Postgres) |
| **GitHub Actions** | 4 (cron) | Yes (commits file to repo) |

Use **≤4 runs per day** to stay under the free tier’s 500 posts/month.
