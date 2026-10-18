# Daily Eagles shorts (YouTube Shorts + Instagram Reels)

Every morning, after the daily briefs are written, this turns the Eagles brief into a ~30 second vertical video and posts it.
After each game it also makes a result-first postgame video (an hourly `--auto` run decides what is due).

```
brief (lib/briefs, dated sources, newest first) + ESPN facts (lib/espn.py: score, stat leaders, schedule)
  -> script.py   hook-first script, 4-5 beats, ~80 words, on-screen cards, title/caption/hashtags
  -> voice.py    text-to-speech per beat (OpenAI or ElevenLabs, names respelled via lib/pronunciation.py) + word timings
  -> render.py   stadium b-roll (broll.py) + team tint + graphics.py frames (hook, cards, karaoke captions)
  -> publish.py  YouTube Shorts (private/unlisted/public) and Instagram Reels (public only)
```

Format choices come from what performs on Shorts/Reels: hook in the first 1-2 seconds, 25-35 seconds total,
word-by-word captions for muted viewing, a closing question that drives comments and loops into the hook.
Every fact must come from the brief or ESPN, and each video's substance changes daily (YouTube does not
monetize templated, repetitive uploads). No game footage, player images or team logos are used.

## Photos

Beats about a player or coach show their photo (slow push-in, face framed); other beats use stadium footage.
Photos come from, in order:

1. **Our own or licensed photos** in the media bucket under `photos/<name-slug>/`, e.g. `photos/tanner-mckee/1.jpg`.
   Add `photos/<name-slug>/credit.txt` if the license needs a credit line. These always win.
2. **Wikimedia Commons**: Wikidata's main photo of the person, plus Commons files named after them alone.
   Only CC0, public domain, CC BY and CC BY-SA files are used, and every credit goes in the description.

Never use photos from team sites, Getty/AP/Imagn, or game footage without a license: editing a photo doesn't
change who owns it, and NFL footage gets Content ID claims and strikes.

## Breaking news

Every 30 minutes (8am-11pm ET) `shorts/breaking.py` reads headlines it hasn't seen; a major new development
(injury status, trade, signing/release, QB or coach change, suspension) gets its own video, at most two a day.

## Run

```bash
python -m shorts.run --team eagles --out /tmp            # render only
python -m shorts.run --team eagles --publish             # render and post the morning video
python -m shorts.run --team eagles --auto --publish      # hourly: morning or postgame, whichever is due
python -m shorts.run --team eagles --script s.json       # re-render an existing script (e.g. another voice)
```

Needs `ffmpeg`/`ffprobe` on PATH. On Railway set `RAILPACK_DEPLOY_APT_PACKAGES=ffmpeg`.

## Settings

| Variable | Default | |
|---|---|---|
| `VOICE_PROVIDER` | `openai` | or `elevenlabs` (`ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`) |
| `OPENAI_TTS_VOICE` | `ash` | OpenAI voice |
| `VOICE_TEMPO` | `1.18` | speed-up applied to narration |
| `PEXELS_API_KEY` | | background stadium footage; plain team-color background without it |
| `SHORTS_PRIVACY` | `private` | `unlisted` / `public`; Instagram only posts when `public` |
| `SHORTS_MODEL` | `gpt-5.4-mini` | script writer |

## Account setup (one time)

**YouTube**
1. Create the channel (a Brand Account under your Google account works).
2. In the Google Cloud project that has the YouTube Data API enabled, use a Desktop OAuth client and make sure
   the OAuth consent screen is **In production** (tokens from "Testing" expire after 7 days).
3. `python scripts/youtube_auth.py client_secrets.json`, sign in, choose the new channel.
4. Put the printed `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN` on the Railway service.

**Instagram**
1. Create the account and switch it to a Professional (Creator or Business) account.
2. In Meta for Developers, create an app with the Instagram product ("API setup with Instagram login"),
   add the account as an Instagram tester and accept the invite in the Instagram app.
3. Generate a token for the account in the app dashboard (permissions `instagram_business_basic`,
   `instagram_business_content_publish`), exchange it for a long-lived token, and set `IG_USER_ID` and
   `IG_ACCESS_TOKEN`. The uploader refreshes the token itself every ~20 days.
