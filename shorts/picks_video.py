"""Weekly "pick the score" video: names the next game, shouts out the last game's best call, points to /picks.

It replaces the weekly trivia video (which drew about a tenth of a news video's YouTube views) and gives viewers a
reason to visit the site, since entering a pick joins the daily email. The script is built from ESPN's schedule and
our own contest results, so there is nothing for a model to get wrong. Leaderboard names are typed by fans, so one is
only read out after it passes OpenAI's moderation check.
"""
from datetime import datetime

from lib import briefs, picks
from lib.teams import TEAMS

PICKS_PATH = "/picks"


def _when(kickoff_utc: str) -> str:
    """'Sunday at 1' / 'Monday at 8:15', as a narrator would say it."""
    k = datetime.fromisoformat(kickoff_utc).astimezone(briefs.EASTERN)
    time = f"{k:%-I}" if k.minute == 0 else f"{k:%-I:%M}"
    return f"{k:%A} at {time}"


def _speakable(name: str) -> bool:
    try:
        from openai import OpenAI
        return not OpenAI().moderations.create(model="omni-moderation-latest", input=name).results[0].flagged
    except Exception:
        return False


def build_script(team: str, game: dict) -> dict:
    name = TEAMS[team]["name"]
    where = "vs." if game["home"] else "at"
    beats = [{"say": f"{name} {where} {game['opponent']}, {_when(game['kickoff_utc'])}. Call the final score.",
              "person": "", "card": {"kind": "text", "label": "Pick the score",
                                     "value": f"PHI {'vs' if game['home'] else '@'} {game['opponent_abbr']}",
                                     "detail": game["kickoff_et"]}}]
    last = picks.last_results()
    if last and last.get("top") and _speakable(last["top"][0]["name"]):
        best = last["top"][0]
        ours, theirs = best["pick"].split("-")
        beats.append({"say": f"Last game's best call: {best['name']}, with {ours} to {theirs}. {best['points']} points.",
                      "person": "", "card": {"kind": "text", "label": "Last game's best call", "value": best["name"],
                                             "detail": f"{best['pick']} · {best['points']} pts"}})
    beats.append({"say": "Right winner gets three points. Nail the exact score and it's ten.", "person": "",
                  "card": {"kind": "text", "label": "Scoring", "value": "Exact score: 10",
                           "detail": "Right winner 3 · margin within 3 +2"}})
    beats.append({"say": "Lock in your pick at the link on screen, it's free, then drop your score in the comments.",
                  "person": "", "card": None})
    opp = game["opponent"].split()[-1]
    return {
        "kind": "picks",
        "cta": "picks",
        "beats": beats,
        "hook_text": "CALL THE SCORE",
        "title": f"Call the {name}-{opp} final score 🦅 #{name}",
        "caption": f"{name} {where} {game['opponent']}: what's the final? Lock in your pick, free: "
                   f"phillysportdaily.com{PICKS_PATH}",
        "hashtags": [f"#{name}", "#FlyEaglesFly" if team == "eagles" else "#Philly", "#NFL"],
        "link_path": PICKS_PATH,
        "link_label": "PICK THE SCORE",
        "game_id": game["id"],
    }
