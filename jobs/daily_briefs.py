"""Write today's brief for every team, then send the daily email. Scheduled daily on Railway: python -m jobs.daily_briefs"""
import sys

from dotenv import load_dotenv

load_dotenv()

from lib import newsletter  # noqa: E402
from lib.briefs import generate_all  # noqa: E402

if __name__ == "__main__":
    written = generate_all(sys.argv[1] if len(sys.argv) > 1 else None)
    if written:
        try:
            newsletter.send_daily(sys.argv[1] if len(sys.argv) > 1 else None)
        except Exception as e:
            print(f"Daily email failed: {e}")
    sys.exit(0 if written else 1)
