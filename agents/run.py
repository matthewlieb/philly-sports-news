"""Scheduled page-management run: python -m agents.run --team eagles"""
import argparse

from dotenv import load_dotenv

load_dotenv()

from agents import comments  # noqa: E402
from lib.teams import TEAMS  # noqa: E402

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--team", default="eagles", choices=list(TEAMS))
    comments.run(p.parse_args().team)
