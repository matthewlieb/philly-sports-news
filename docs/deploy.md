# Deploying to Heroku

The app is set up for Heroku: `Procfile` runs gunicorn, and `.env` is gitignored so secrets stay local.

## 1. One-time setup (if new app)

```bash
# Login (if needed)
heroku login

# Create app (or use existing)
heroku create philly-sport-daily
# Or link existing app:
# heroku git:remote -a your-app-name
```

## 2. Config vars (required)

Set these in Heroku Dashboard → Settings → Config Vars (or via CLI):

| Key       | Description |
|----------|-------------|
| `API_KEY` | YouTube Data API key (for team page embeds). Optional but recommended. |

```bash
heroku config:set API_KEY=your_youtube_api_key
```

## 3. Deploy

```bash
git add .
git commit -m "Deploy philly sports news"
git push heroku main
# Or: git push heroku master
```

## 4. Custom domain (phillysportdaily.com)

If you still own the domain:

1. **Heroku:** Dashboard → your app → Settings → Domains → Add domain → `phillysportdaily.com` and `www.phillysportdaily.com`.
2. Heroku will show DNS targets (e.g. `something.herokudns.com`).
3. **At your domain registrar:** Add CNAME records:
   - `www` → target Heroku gives for `www.phillysportdaily.com`
   - For root `phillysportdaily.com`, use Heroku's root domain target (they'll show an A record or ALIAS/CNAME for root).
4. In Heroku, enable "Automatic TLS" for the custom domain so HTTPS is used.

After DNS propagates (up to 48 hours, often sooner), the site will be live at phillysportdaily.com.

## 5. Optional: Selenium (JS-heavy sites)

If you enable `USE_SELENIUM=1`, add the Chrome buildpack so headless Chrome works:

```bash
heroku buildpacks:add --index 1 heroku/chrome
heroku buildpacks:add --index 2 heroku/python
```

Otherwise the app runs with requests + BeautifulSoup only (no buildpack needed).

## 6. Check logs

```bash
heroku logs --tail
```
