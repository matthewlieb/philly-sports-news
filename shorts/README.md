# Daily Eagles shorts (YouTube Shorts + Instagram Reels)

Every morning, after the daily briefs are written, this turns the Eagles brief into a ~30 second vertical video and posts it.

```
brief (lib/briefs) + ESPN facts (espn.py)
  -> script.py   hook-first script, 4-5 beats, ~80 words, on-screen cards, title/caption/hashtags
  -> voice.py    text-to-speech per beat (OpenAI or ElevenLabs) + word timings (Whisper)
  -> render.py   stadium b-roll (broll.py) + team tint + graphics.py frames (hook, cards, karaoke captions)
  -> publish.py  YouTube Shorts (private/unlisted/public) and Instagram Reels (public only)
```

Format choices come from what performs on Shorts/Reels: hook in the first 1-2 seconds, 25-35 seconds total,
word-by-word captions for muted viewing, a closing question that drives comments and loops into the hook.
Every fact must come from the brief or ESPN, and each video's substance changes daily (YouTube does not
monetize templated, repetitive uploads). No game footage, player images or team logos are used.

## Run

```bash
python -m shorts.run --team eagles --out /tmp            # render only
python -m shorts.run --team eagles --publish             # render and post
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
