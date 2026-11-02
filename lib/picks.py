"""Pick the score: fans guess the final score of the Eagles' next game; points go on a season leaderboard.

Entering signs the fan up for the daily email (Buttondown's confirmation email still applies). Picks lock at kickoff.
After the game, score_finished() awards points once:
  correct winner 3, final margin within 3 points +2, exact score +5 (10 total).
Only the display name a fan chooses is ever shown; emails stay private.
"""
import json
import re
from datetime import datetime, timezone

from lib import store
from lib.espn import team_snapshot

TEAM = "eagles"
_NAME = re.compile(r"[^A-Za-z0-9 .'-]")


def _season(kickoff: datetime) -> int:
    return kickoff.year if kickoff.month >= 3 else kickoff.year - 1


def _picks_key(game_id: str) -> str:
    return store.key("picks", TEAM, game_id)


def _board_key(season: int) -> str:
    return store.key("picks", TEAM, "board", season)


def next_game() -> dict | None:
    """The upcoming game (cached 30 minutes so the page doesn't call ESPN on every view)."""
    r, k = store.client(), store.key("picks", TEAM, "next")
    if raw := r.get(k):
        return json.loads(raw) or None
    game = team_snapshot(TEAM).get("next_game")
    r.set(k, json.dumps(game or {}), ex=1800)
    return game


def is_open(game: dict) -> bool:
    return datetime.now(timezone.utc) < datetime.fromisoformat(game["kickoff_utc"])


def clean_name(name: str) -> str:
    return " ".join(_NAME.sub("", name or "").split())[:20]


def submit(game: dict, email: str, name: str, ours: int, theirs: int) -> str:
    """Save or replace this email's pick. Returns "ok", "closed" or "invalid"."""
    if not is_open(game):
        return "closed"
    name = clean_name(name)
    if not name or not (0 <= ours <= 99 and 0 <= theirs <= 99) or ours == theirs:
        return "invalid"
    store.client().hset(_picks_key(game["id"]), email.strip().lower(), json.dumps({
        "name": name, "ours": ours, "theirs": theirs, "at": int(datetime.now(timezone.utc).timestamp()),
        "opponent": game["opponent"], "kickoff_utc": game["kickoff_utc"]}))
    store.client().expire(_picks_key(game["id"]), 400 * 86400)
    return "ok"


def count(game_id: str) -> int:
    return store.client().hlen(_picks_key(game_id))


def points(pick: dict, ours: int, theirs: int) -> int:
    won, picked_win = ours > theirs, pick["ours"] > pick["theirs"]
    if won != picked_win:
        return 0
    pts = 3
    if abs((pick["ours"] - pick["theirs"]) - (ours - theirs)) <= 3:
        pts += 2
    if (pick["ours"], pick["theirs"]) == (ours, theirs):
        pts += 5
    return pts


def score_finished() -> dict | None:
    """Award points for the last completed game, once. Returns that game's results, or None."""
    last = team_snapshot(TEAM).get("last_game")
    r = store.client()
    if not last or not last.get("completed") or r.get(store.key("picks", TEAM, "scored", last["id"])):
        return None
    try:
        ours, theirs = int(last["our_score"]), int(last["their_score"])
    except (TypeError, ValueError):
        return None
    picks = {e: json.loads(v) for e, v in r.hgetall(_picks_key(last["id"])).items()}
    board = _board_key(_season(datetime.fromisoformat(last["kickoff_utc"])))
    results = []
    for email, pick in picks.items():
        pts = points(pick, ours, theirs)
        r.zincrby(board, pts, email)
        r.hset(store.key("picks", TEAM, "names"), email, pick["name"])
        results.append({"name": pick["name"], "pick": f"{pick['ours']}-{pick['theirs']}", "points": pts})
    results.sort(key=lambda x: -x["points"])
    summary = {"game_id": last["id"], "opponent": last["opponent"], "final": f"{ours}-{theirs}",
               "entries": len(results), "top": results[:5]}
    r.set(store.key("picks", TEAM, "scored", last["id"]), json.dumps(summary), ex=400 * 86400)
    r.set(store.key("picks", TEAM, "last_results"), json.dumps(summary), ex=10 * 86400)
    return summary


def last_results() -> dict | None:
    raw = store.client().get(store.key("picks", TEAM, "last_results"))
    return json.loads(raw) if raw else None


def leaderboard(limit: int = 10, season: int | None = None) -> list[dict]:
    r = store.client()
    season = season or _season(datetime.now(timezone.utc))
    rows = r.zrevrange(_board_key(season), 0, limit - 1, withscores=True)
    names = r.hmget(store.key("picks", TEAM, "names"), [e for e, _ in rows]) if rows else []
    return [{"rank": i + 1, "name": n or "Fan", "points": int(p)} for i, ((_, p), n) in enumerate(zip(rows, names))]
