# Roadmap

Status as of October 9, 2026.

## Done

- Hosting moved from Heroku to Railway + Upstash Redis (~$5/month instead of $10). Heroku is shut down.
- Site: one team template, daily briefs with archive, SEO tags, sitemap, robots.txt, ads.txt, About and Privacy pages.
- Measurement: Google Analytics (`G-T725JB9K0P`), Search Console verification, daily pageview counts in Redis.
- Tweet bot rebuilt (Redis memory, safe links, brief promotion). **Paused**: X API is pay-per-use since Feb 2026.
- Daily Eagles short pipeline (`shorts/`), scheduled on Railway at 11:30 UTC. Skips until an account is connected.

## Waiting on Matthew

1. **Pick a voice** from `~/Desktop/eagles-short-samples/` (OpenAI ~free, or ElevenLabs Starter ~$5-6/month).
2. **YouTube channel**: create it, set the Google Cloud OAuth consent screen to "In production", run
   `python scripts/youtube_auth.py <client_secrets.json>` and share the printed values.
3. **Instagram account**: switch to Creator/Business, create a Meta app with Instagram login, share
   `IG_USER_ID` and a long-lived `IG_ACCESS_TOKEN`.
4. **Search Console**: click Verify and submit `sitemap.xml`.
5. **AdSense**: request a new review around late October, once a few weeks of briefs are indexed.
6. **X**: decide later whether to buy API credits (~$1.35-12.50/month depending on links).

## Next to build

1. **Go live with shorts**: connect accounts, post privately for a few days, review, then switch
   `SHORTS_PRIVACY=public` (Instagram starts posting at that point).
2. **Cross-posting** to Facebook Reels and Threads (free APIs, same video and caption).
3. **Page-management agents** (only actions the platforms allow):
   - Comment assistant: reply to genuine questions on our own posts, hide spam. Starts in draft/review mode.
   - Weekly growth analyst: pull YouTube Analytics and Instagram Insights (retention, views, follows per video),
     write a short report, and feed what works (hook styles, topics, length) back into the script prompt.
     Needs about two weeks of posted videos first.
   - Not doing: auto-follow, auto-like, mass DMs or commenting on other accounts. These break platform rules
     and get automated accounts banned.
4. **AI-generated b-roll**: rent a GPU for an hour or two (~$1/hour) and generate a reusable library of 30-50
   Eagles-themed clips with an open model (LTX-2 or Wan 2.2). No real players or team logos.
5. **More teams**: Sixers, Phillies, Flyers shorts use the same pipeline (`--team`), once Eagles is working.
