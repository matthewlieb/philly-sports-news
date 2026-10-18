"""Make (and optionally publish) a team's short.

  python -m shorts.run --team eagles                       # render today's morning video only
  python -m shorts.run --team eagles --publish             # render and post
  python -m shorts.run --team eagles --auto --publish      # what the hourly schedule runs (see below)
  python -m shorts.run --team eagles --script s.json       # re-render an existing script (e.g. another voice)

--auto decides what is due each run (every 30 minutes):
  morning   once today's brief exists (written ~7am ET) and today's morning video hasn't gone out
  postgame  4.5 to 20 hours after kickoff of a finished game that hasn't had one: refreshes today's
            brief with the recaps, then makes a result-first video
  breaking  when neither is due: a major new development nobody has covered (see shorts/breaking.py)
"""
import argparse
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from lib import briefs, store  # noqa: E402
from lib.espn import hours_since, team_snapshot  # noqa: E402
from lib.teams import TEAMS  # noqa: E402
from shorts.photos import beat_photos  # noqa: E402
from shorts.render import render  # noqa: E402
from shorts.script import write_script  # noqa: E402
from shorts.voice import narrate  # noqa: E402

POSTGAME_WINDOW_HOURS = (4.5, 20)


def _recent_hooks(team: str, limit: int = 4) -> list[str]:
    r = store.client()
    hooks = []
    for day in briefs.brief_dates(team, limit=4):
        for kind in ("postgame", "morning"):
            if raw := r.get(store.key("shortscript", team, day, kind)):
                hooks.append(f"{day} {kind}: {json.loads(raw).get('hook_text', '')}")
    return hooks[:limit]


def make_short(team: str, day: str, out_dir: Path, kind: str = "morning", snapshot: dict | None = None,
               script_path: str | None = None, breaking: str | None = None) -> tuple[Path, dict]:
    if script_path:
        script = json.loads(Path(script_path).read_text())
    elif breaking:
        script = write_script(team, None, snapshot if snapshot is not None else team_snapshot(team),
                              recent_hooks=_recent_hooks(team), breaking=breaking)
    else:
        brief = briefs.get_brief(team, day)
        if not brief:
            raise SystemExit(f"No {team} brief for {day}")
        script = write_script(team, brief, snapshot if snapshot is not None else team_snapshot(team),
                              postgame=kind == "postgame", recent_hooks=_recent_hooks(team))
    print(json.dumps(script, indent=1))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{team}-{day}-{kind}.json").write_text(json.dumps(script, indent=1))

    workdir = Path(tempfile.mkdtemp(prefix=f"short-{team}-"))
    voice, timeline = narrate(script["beats"], workdir)
    total = timeline[-1]["end"] + 0.6
    try:
        pictures, script["photo_credits"] = beat_photos(script, team, workdir)
    except Exception as e:
        print(f"Photos unavailable, using footage only: {e}")
        pictures, script["photo_credits"] = [], []
    label = {"postgame": "POSTGAME", "breaking": "BREAKING"}.get(kind, "DAILY")
    tag = f"{TEAMS[team]['name']} {label} · {datetime.fromisoformat(day):%b %-d}".upper()
    out = out_dir / f"{team}-{day}-{kind}.mp4"
    render(script, timeline, voice, total, team, tag, workdir, out, pictures)
    print(f"Rendered {out} ({total:.1f}s)")
    return out, script


def _due(team: str, day: str) -> tuple[str | None, dict]:
    """Which video, if any, the hourly run should make now."""
    r = store.client()
    snapshot = team_snapshot(team)
    game = snapshot.get("last_game")
    if game and game["completed"] and POSTGAME_WINDOW_HOURS[0] <= hours_since(game["kickoff_utc"]) <= POSTGAME_WINDOW_HOURS[1]:
        if not r.get(store.key("shorts", team, "postgame", game["id"])):
            return "postgame", snapshot
    if briefs.get_brief(team, day) and not r.get(store.key("shorts", team, day)):
        return "morning", snapshot
    return None, snapshot


def _carousels(team: str, day: str, snapshot: dict, out_dir: Path) -> None:
    """Instagram carousels that are due: postgame recap (after the postgame video refreshed the brief)
    and the weekly "5 things" on Tuesdays from noon ET."""
    from shorts import carousel
    from shorts.publish import upload_instagram_carousel

    r = store.client()
    due = []
    game = snapshot.get("last_game")
    if (game and r.get(store.key("shorts", team, "postgame", game["id"]))
            and not r.get(store.key("carousel", team, "postgame", game["id"]))
            and (brief := briefs.get_brief(team, day))):
        due.append((store.key("carousel", team, "postgame", game["id"]), "postgame",
                    lambda: (carousel.postgame_slides(team, snapshot, brief), carousel.postgame_caption(team, snapshot, brief))))
    now = datetime.now(briefs.EASTERN)
    week = now.strftime("%G-W%V")
    if now.weekday() == 1 and now.hour >= 12 and not r.get(store.key("carousel", team, "weekly", week)):
        due.append((store.key("carousel", team, "weekly", week), "weekly", lambda: carousel.weekly_slides(team, day)))
    for key, kind, build in due:
        made = build()
        if not made:
            print(f"Not enough material for the {kind} carousel.")
            continue
        slides, caption = made
        paths = carousel.save(slides, out_dir, f"{team}-{day}-{kind}")
        try:
            result = upload_instagram_carousel(paths, caption)
        except Exception as e:
            print(f"{kind} carousel failed: {e}")
            continue
        print(f"Posted {kind} carousel: {result.get('url')}")
        r.set(key, json.dumps(result))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--team", default="eagles", choices=list(TEAMS))
    p.add_argument("--date", default=None, help="brief date (default: today in Philadelphia)")
    p.add_argument("--kind", default="morning", choices=["morning", "postgame"])
    p.add_argument("--auto", action="store_true", help="decide what is due (used by the hourly schedule)")
    p.add_argument("--publish", action="store_true")
    p.add_argument("--out", default=".")
    p.add_argument("--script", default=None, help="reuse a script JSON instead of writing a new one")
    args = p.parse_args()
    day = args.date or briefs.local_today()
    team, kind, snapshot = args.team, args.kind, None

    if args.publish and not (os.environ.get("YOUTUBE_REFRESH_TOKEN") or os.environ.get("IG_USER_ID")):
        print("No YouTube or Instagram account connected yet. Skipping.")
        return
    if args.auto:
        kind, snapshot = _due(team, day)
        social_ready = args.publish and os.environ.get("IG_USER_ID") and os.environ.get("SHORTS_PRIVACY") == "public"
        if kind:
            _video(args, team, day, kind, snapshot)
        else:
            print("No scheduled video due now.")
        if social_ready:
            _carousels(team, day, snapshot, Path(args.out))
            if not kind:
                _breaking(args, team, day, snapshot)
        return
    if kind == "postgame":
        snapshot = team_snapshot(team)
    _video(args, team, day, kind, snapshot)


def _breaking(args, team: str, day: str, snapshot: dict) -> None:
    from shorts import breaking

    try:
        story = breaking.find_story(team, day)
    except Exception as e:
        print(f"Breaking check failed: {e}")
        return
    if not story:
        return
    posted_key = store.key("shorts", team, "breaking", story["slug"])
    video, script = make_short(team, day, Path(args.out), "breaking", snapshot, breaking=story["material"])
    store.client().set(store.key("shortscript", team, day, "breaking"), json.dumps(script), ex=30 * 86400)
    from shorts.publish import publish_all
    results = publish_all(video, script, team, day)
    print(json.dumps(results, indent=1))
    if any(r.get("id") for r in results.values()):
        store.client().set(posted_key, json.dumps(results))
        breaking.record(team, day, story)


def _video(args, team: str, day: str, kind: str, snapshot: dict | None) -> None:
    print(f"Making the {kind} video for {team}, {day}")
    if kind == "postgame" and not args.script:
        brief = briefs.generate_brief(team, day, postgame=True)
        if brief:
            briefs.save_brief(brief)

    posted_key = (store.key("shorts", team, "postgame", snapshot["last_game"]["id"]) if kind == "postgame" and snapshot
                  else store.key("shorts", team, day))
    if args.publish and store.client().get(posted_key):
        print(f"Already published the {kind} video for {team} {day}.")
        return

    video, script = make_short(team, day, Path(args.out), kind, snapshot, args.script)
    store.client().set(store.key("shortscript", team, day, kind), json.dumps(script), ex=30 * 86400)
    if not args.publish:
        return

    from shorts.publish import publish_all
    results = publish_all(video, script, team, day)
    print(json.dumps(results, indent=1))
    if not any(r.get("id") for r in results.values()):
        sys.exit(1)
    store.client().set(posted_key, json.dumps(results))


if __name__ == "__main__":
    main()
