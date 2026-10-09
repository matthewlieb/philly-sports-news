"""Team facts from ESPN's public site API: record, standing, last result, next game."""
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

_BASE = "https://site.api.espn.com/apis/site/v2/sports"
_PATHS = {"eagles": "football/nfl/teams/phi", "sixers": "basketball/nba/teams/phi",
          "phillies": "baseball/mlb/teams/phi", "flyers": "hockey/nhl/teams/phi"}
_EASTERN = ZoneInfo("America/New_York")


def _get(url: str) -> dict:
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _game(event: dict, team_abbr: str) -> dict:
    comp = event["competitions"][0]
    us = next(c for c in comp["competitors"] if c["team"]["abbreviation"] == team_abbr)
    them = next(c for c in comp["competitors"] if c is not us)
    kickoff = datetime.fromisoformat(event["date"].replace("Z", "+00:00")).astimezone(_EASTERN)
    score = lambda c: (c.get("score") or {}).get("displayValue") if isinstance(c.get("score"), dict) else c.get("score")
    return {
        "opponent": them["team"]["displayName"],
        "opponent_abbr": them["team"]["abbreviation"],
        "home": us.get("homeAway") == "home",
        "kickoff_et": kickoff.strftime("%a %b %-d, %-I:%M %p ET"),
        "completed": comp["status"]["type"]["completed"],
        "our_score": score(us),
        "their_score": score(them),
        "won": us.get("winner"),
        "venue": (comp.get("venue") or {}).get("fullName"),
    }


def team_snapshot(team: str) -> dict:
    """Facts safe to put on screen. Empty dict if ESPN is unreachable."""
    try:
        info = _get(f"{_BASE}/{_PATHS[team]}")["team"]
        abbr = info["abbreviation"]
        events = _get(f"{_BASE}/{_PATHS[team]}/schedule").get("events", [])
    except Exception as e:
        print(f"ESPN lookup failed: {e}")
        return {}
    games = [_game(e, abbr) for e in events]
    played = [g for g in games if g["completed"]]
    upcoming = [g for g in games if not g["completed"]]
    record = (info.get("record", {}).get("items") or [{}])[0].get("summary")
    return {
        "record": record,
        "standing": info.get("standingSummary"),
        "last_game": played[-1] if played else None,
        "next_game": upcoming[0] if upcoming else None,
    }
