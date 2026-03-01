# Satire images for tweets

Your best-performing tweet used a **satire image** (e.g. Saint Nick Foles – religious iconography + Eagles). Generating similar images occasionally to attach to tweets is feasible and would make posts stand out.

## Feasibility

- **DALL·E (OpenAI Images API)** and similar APIs (e.g. **Ideogram**, **Stable Diffusion** via Replicate) can generate satire/mashup images from a text prompt (e.g. “Philadelphia Eagles quarterback as a Renaissance religious painting, team logo on chest, dramatic lighting”).
- **Flow:** For some runs (e.g. 1 in 5, or when a headline is especially meme-worthy), generate an image from the article headline + your style, upload it via X API `create_tweet(text=..., media_ids=[...])`, then post.
- **Considerations:**
  - **Likeness:** Depicting real people (athletes, coaches) can touch on publicity rights and platform rules. Safer angles: generic “Eagles fan saint,” mascot, or non-photorealistic styles (illustration, painting) rather than “Nick Foles’s face on a saint.”
  - **Cost:** Image generation costs per call (OpenAI Images, Ideogram, etc.); use sparingly (e.g. once per day or a few times per week).
  - **Quality:** You may need to regenerate or discard some outputs; a “good enough” filter or manual review for special tweets is reasonable.

## Possible implementation

1. Add an optional step in `twitter_bot/run.py`: with some probability (or for certain headlines), call an image API with a prompt derived from the article (e.g. “Satirical oil painting of [team] fan as a saint, [team] logo, dramatic lighting, Philly sports meme style”).
2. Upload the image with Tweepy’s `client.media_upload(filename)` → get `media_id`, then `client.create_tweet(text=tweet, media_ids=[media_id])`.
3. Store prompts and maybe example outputs in `twitter_bot/config/` (e.g. `image_prompts.py`) so you can tune style without changing code.

Example reference images (e.g. your Saint Nick Foles) can live in `twitter_bot/assets/images/` for prompt inspiration or human review.
