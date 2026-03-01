import os

# YouTube API key - set as environment variable API_KEY (or api_key in .env) for YouTube embeds.
# If not set, the app still runs; team pages just won't show an embedded video.
api_key = os.environ.get("API_KEY") or os.environ.get("api_key")
