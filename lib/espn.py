"""Team facts from ESPN's public site API: record, standing, last result (with stat leaders), next game."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests

_BASE = "https://site.api.espn.com/apis/site/v2/sports"
_SPORTS = {"eagles": "football/nfl", "sixers": "basketball/nba", "phillies": "baseball/mlb", "flyers": "hockey/nhl"}
_EASTERN = ZoneInfo("America/New_York")


def _get(url: str) -> dict:
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _score(c: dict):
    s = c.get("score")
    return s.get("displayValue") if isinstance(s, dict) else s


def _game(event: dict, team_abbr: str) -> dict:
    comp = event["competitions"][0]
    us = next(c for c in comp["competitors"] if c["team"]["abbreviation"] == team_abbr)
    them = next(c for c in comp["competitors"] if c is not us)
    kickoff = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
    return {
        "id": event["id"],
        "opponent": them["team"]["displayName"],
        "opponent_abbr": them["team"]["abbreviation"],
        "home": us.get("homeAway") == "home",
        "kickoff_utc": kickoff.isoformat(),
        "kickoff_et": kickoff.astimezone(_EASTERN).strftime("%a %b %-d, %-I:%M %p ET"),
        "completed": comp["status"]["type"]["completed"],
        "our_score": _score(us),
        "their_score": _score(them),
        "won": us.get("winner"),
        "venue": (comp.get("venue") or {}).get("fullName"),
    }


_TEAM_STATS = {"Total Yards", "Turnovers", "3rd down efficiency", "Possession", "Sacks-Yards Lost", "Penalties",
               "Field Goal %", "Three Point %", "Rebounds", "Shots", "Power Play Goals", "Hits", "Errors"}


def box_score(team: str, event_id: str, per_group: int = 3) -> list[str]:
    """Every stat labeled, zeros included, e.g. 'PHI passing - Jalen Hurts: C/ATT 21/40, YDS 220, TD 1, INT 0'.
    The labels matter: a summary that leaves out '0 INT' invites a model to guess."""
    try:
        summary = _get(f"{_BASE}/{_SPORTS[team]}/summary?event={event_id}")
    except Exception:
        return []
    box = summary.get("boxscore") or {}
    lines = []
    for side in box.get("teams") or []:
        abbr = side.get("team", {}).get("abbreviation", "")
        stats = [f"{s['label']} {s['displayValue']}" for s in side.get("statistics") or [] if s.get("label") in _TEAM_STATS]
        if stats:
            lines.append(f"{abbr} team: " + ", ".join(stats))
    for side in box.get("players") or []:
        abbr = side.get("team", {}).get("abbreviation", "")
        for group in side.get("statistics") or []:
            labels = group.get("labels") or group.get("keys") or []
            for athlete in (group.get("athletes") or [])[:per_group]:
                pairs = ", ".join(f"{l} {v}" for l, v in zip(labels, athlete.get("stats") or []))
                lines.append(f"{abbr} {group.get('name') or 'players'} - {athlete['athlete']['displayName']}: {pairs}")
    for side in summary.get("leaders") or []:
        abbr = side.get("team", {}).get("abbreviation", "")
        for cat in side.get("leaders") or []:
            if cat.get("leaders"):
                top = cat["leaders"][0]
                lines.append(f"{abbr} game leader, {cat.get('displayName')}: {top['athlete']['displayName']} ({top.get('displayValue')})")
    return lines


def team_snapshot(team: str) -> dict:
    """Facts safe to put on screen. Empty dict if ESPN is unreachable."""
    try:
        info = _get(f"{_BASE}/{_SPORTS[team]}/teams/phi")["team"]
        events = _get(f"{_BASE}/{_SPORTS[team]}/teams/phi/schedule").get("events", [])
    except Exception as e:
        print(f"ESPN lookup failed: {e}")
        return {}
    games = [_game(e, info["abbreviation"]) for e in events]
    played = [g for g in games if g["completed"]]
    upcoming = [g for g in games if not g["completed"]]
    last = played[-1] if played else None
    if last:
        last["box_score"] = box_score(team, last["id"])
    return {
        "record": (info.get("record", {}).get("items") or [{}])[0].get("summary"),
        "standing": info.get("standingSummary"),
        "last_game": last,
        "next_game": upcoming[0] if upcoming else None,
    }


def hours_since(iso: str) -> float:
    return (datetime.now(timezone.utc) - datetime.fromisoformat(iso)).total_seconds() / 3600


def facts_text(snapshot: dict) -> str:
    """ESPN facts as prompt text: authoritative for scores, records and schedule."""
    if not snapshot:
        return "ESPN facts: unavailable."
    lines = [f"Record: {snapshot.get('record')}", f"Standing: {snapshot.get('standing')}"]
    if g := snapshot.get("last_game"):
        ago = hours_since(g["kickoff_utc"])
        when = f"{ago:.0f} hours ago" if ago < 48 else g["kickoff_et"]
        lines.append(f"Last game (kicked off {when}): {'W' if g['won'] else 'L'} {g['our_score']}-{g['their_score']} "
                     f"{'vs' if g['home'] else 'at'} {g['opponent']}")
        if ago < 48:
            lines += [f"  {l}" for l in g.get("box_score") or []]
    if g := snapshot.get("next_game"):
        lines.append(f"Next game: {'vs' if g['home'] else 'at'} {g['opponent']} ({g['opponent_abbr']}), {g['kickoff_et']}"
                     + (f", {g['venue']}" if g.get("venue") else ""))
    return "ESPN facts (authoritative for scores, records, schedule):\n" + "\n".join(lines)
