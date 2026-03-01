# GitHub Actions: Tweet schedule setup

Use this checklist to turn on the 4x-daily tweet workflow.

## 1. Add repository secrets

On GitHub: open your repo → **Settings** → **Secrets and variables** → **Actions**.

Click **New repository secret** and add each of these (use the same values as in your local `.env_x`):

| Secret name | Value (from .env_x) |
|-------------|---------------------|
| `X_API_KEY` | Your X Consumer Key (API Key) |
| `X_API_SECRET` | Your X Consumer Secret |
| `X_ACCESS_TOKEN` | Your X Access Token |
| `X_ACCESS_TOKEN_SECRET` | Your X Access Token Secret |
| `OPENAI_API_KEY` | Your OpenAI API key |

**Important:** Names must match exactly (including case). The workflow will not see them if the names are wrong.

## 2. Allow the workflow to push

The workflow commits `twitter_bot/data/tweeted_urls.txt` after each run so the next run doesn’t repeat articles.

- Go to **Settings** → **Actions** → **General**.
- Under **Workflow permissions**, select **Read and write permissions**.
- Click **Save**.

## 3. Push your code

From your machine (repo root):

```bash
git add .
git status   # confirm .env_x is not listed (it’s gitignored)
git commit -m "Add GitHub Actions tweet schedule and update .gitignore"
git push origin main
```

(Use `master` instead of `main` if that’s your default branch.)

## 4. Confirm it’s enabled

- Open the **Actions** tab. You should see the workflow **Tweet schedule**.
- To run it once without waiting for the cron: open **Tweet schedule** → **Run workflow** → **Run workflow**.
- Check the run logs; if X returns 503, the run will fail but the workflow is set up correctly.

## Schedule

The workflow runs at **1:00, 13:00, 18:00, and 21:00 UTC** (about 8pm, 8am, 1pm, 6pm Eastern).  
To change times, edit the `cron` line in `.github/workflows/tweet-schedule.yml`.

## Troubleshooting

- **Secrets not found:** Secret names must be exactly `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`, `OPENAI_API_KEY`.
- **Push failed / 403:** In **Settings** → **Actions** → **General**, set **Workflow permissions** to **Read and write permissions** and save.
- **503 from X:** The API is temporarily down; the workflow is fine. Re-run the job later or wait for the next scheduled run.
