"""One-time YouTube sign-in for the shorts uploader. Run locally:

  python scripts/youtube_auth.py path/to/client_secrets.json

A browser opens; sign in and pick the channel that should receive uploads. Prints the three values
to store as YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET and YOUTUBE_REFRESH_TOKEN on the Railway service.
The Google Cloud OAuth consent screen must be "In production"; in "Testing" the token dies after 7 days.
"""
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

secrets = sys.argv[1] if len(sys.argv) > 1 else "client_secrets.json"
flow = InstalledAppFlow.from_client_secrets_file(secrets, ["https://www.googleapis.com/auth/youtube.upload"])
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
print(json.dumps({"YOUTUBE_CLIENT_ID": creds.client_id, "YOUTUBE_CLIENT_SECRET": creds.client_secret,
                  "YOUTUBE_REFRESH_TOKEN": creds.refresh_token}, indent=2))
