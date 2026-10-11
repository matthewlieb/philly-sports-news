"""One-time YouTube sign-in for the shorts uploader. Run locally:

  python scripts/youtube_auth.py path/to/client_secrets.json [env_file]

A browser opens; sign in and pick the channel that should receive uploads. The resulting
YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET and YOUTUBE_REFRESH_TOKEN are written to env_file
(default .env) rather than printed. The Google Cloud OAuth consent screen must be "In production";
in "Testing" the token stops working after 7 days.

Scopes cover uploading plus what the planned analytics and comment agents need, so they don't
require a second sign-in.
"""
import re
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

secrets = sys.argv[1] if len(sys.argv) > 1 else "client_secrets.json"
env_file = Path(sys.argv[2] if len(sys.argv) > 2 else ".env")

flow = InstalledAppFlow.from_client_secrets_file(secrets, SCOPES)
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
channel = build("youtube", "v3", credentials=creds, cache_discovery=False).channels().list(
    part="snippet", mine=True).execute()["items"][0]["snippet"]["title"]

values = {"YOUTUBE_CLIENT_ID": creds.client_id, "YOUTUBE_CLIENT_SECRET": creds.client_secret,
          "YOUTUBE_REFRESH_TOKEN": creds.refresh_token}
lines = [l for l in (env_file.read_text().splitlines() if env_file.exists() else [])
         if not re.match(r"\s*YOUTUBE_(CLIENT_ID|CLIENT_SECRET|REFRESH_TOKEN)\s*=", l)]
env_file.write_text("\n".join(lines + [f"{k}={v}" for k, v in values.items()]) + "\n")
print(f"Signed in to channel '{channel}'. Saved YouTube credentials to {env_file}.")
