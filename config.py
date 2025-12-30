import os

# YouTube API key - MUST be set as environment variable for security
# Do not hardcode API keys in source code!
api_key = os.environ.get('API_KEY')
if not api_key:
    raise ValueError("API_KEY environment variable must be set. See README.md for setup instructions.")
