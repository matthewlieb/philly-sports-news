"""Write today's brief for every team. Scheduled daily on Railway: python -m jobs.daily_briefs"""
import sys

from dotenv import load_dotenv

load_dotenv()

from lib.briefs import generate_all  # noqa: E402

if __name__ == "__main__":
    written = generate_all(sys.argv[1] if len(sys.argv) > 1 else None)
    sys.exit(0 if written else 1)
