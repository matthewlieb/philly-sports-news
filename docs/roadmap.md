# Roadmap

Status as of October 11, 2026 (evening).

## Done

- Hosting moved from Heroku to Railway + Upstash Redis (~$5/month instead of $10). Heroku is shut down.
- Site: one team template, daily briefs with archive, SEO tags, sitemap, robots.txt, ads.txt, About and Privacy pages.
- Measurement: Google Analytics (`G-T725JB9K0P`), Search Console verification, daily pageview counts in Redis.
- Tweet bot rebuilt (Redis memory, safe links, brief promotion). **Paused**: X API is pay-per-use since Feb 2026.
- Daily Eagles short pipeline (`shorts/`), scheduled on Railway at 11:30 UTC, OpenAI voice.
- Accounts connected: YouTube "Eagles Daily | Philly Sport Daily" and Instagram @eaglesdaily.psd. Videos upload to
  YouTube as **private** for review; Instagram starts when `SHORTS_PRIVACY=public`.
- Search Console verified and sitemap submitted.
- Freshness: sources carry publish dates (newest first, >4 days dropped), ESPN box scores feed briefs, recent leads aren't repeated.
- Accuracy: a fact-check pass (gpt-5.4) checks every brief sentence and video line/card/title against the evidence.
- Postgame videos: hourly run makes a result-first video 4.5-20h after kickoff and refreshes that day's brief.
- Name pronunciations for TTS (`lib/pronunciation.py`).
- **Public posting starts Oct 12** (`SHORTS_PRIVACY=public`): YouTube + Instagram Reels.

## Waiting on Matthew

1. **Watch the first public posts** and flag anything off.
2. **Confirm** the Google Cloud OAuth consent screen (project instabot-455700) is "In production".
3. **AdSense**: request a new review around late October, once a few weeks of briefs are indexed.
4. **X**: decide later whether to buy API credits (~$1.35-12.50/month depending on links).

## Next to build

1. **Cross-posting** to Facebook Reels and Threads (free APIs, same video and caption).
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
