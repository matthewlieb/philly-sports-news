"""Make (and optionally publish) today's short for a team.

  python -m shorts.run --team eagles                 # render only, prints the file path
  python -m shorts.run --team eagles --publish       # render, then post to YouTube and Instagram

Scheduled on Railway after the daily briefs are written.
"""
import argparse
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from lib import briefs, store  # noqa: E402
from lib.teams import TEAMS  # noqa: E402
from shorts.espn import team_snapshot  # noqa: E402
from shorts.render import render  # noqa: E402
from shorts.script import write_script  # noqa: E402
from shorts.voice import narrate  # noqa: E402


def make_short(team: str, day: str, out_dir: Path, script_path: str | None = None) -> tuple[Path, dict]:
    if script_path:
        script = json.loads(Path(script_path).read_text())
    else:
        brief = briefs.get_brief(team, day)
        if not brief:
            raise SystemExit(f"No {team} brief for {day}")
        script = write_script(team, brief, team_snapshot(team))
    print(json.dumps(script, indent=1))
    (out_dir / f"{team}-{day}.json").write_text(json.dumps(script, indent=1))

    workdir = Path(tempfile.mkdtemp(prefix=f"short-{team}-"))
    voice, timeline = narrate(script["beats"], workdir)
    total = timeline[-1]["end"] + 0.6
    tag = f"{TEAMS[team]['name'].upper()} DAILY · {datetime.fromisoformat(day):%b %-d}".upper()
    out = out_dir / f"{team}-{day}.mp4"
    render(script, timeline, voice, total, team, tag, workdir, out)
    print(f"Rendered {out} ({total:.1f}s)")
    return out, script


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--team", default="eagles", choices=list(TEAMS))
    p.add_argument("--date", default=None, help="brief date (default: today in Philadelphia)")
    p.add_argument("--publish", action="store_true")
    p.add_argument("--out", default=".")
    p.add_argument("--script", default=None, help="reuse a script JSON instead of writing a new one")
    args = p.parse_args()
    day = args.date or briefs.local_today()

    posted_key = store.key("shorts", args.team, day)
    if args.publish and store.client().get(posted_key):
        print(f"Already published the {args.team} short for {day}.")
        return

    video, script = make_short(args.team, day, Path(args.out), args.script)
    if not args.publish:
        return

    from shorts.publish import publish_all
    results = publish_all(video, script, args.team, day)
    print(json.dumps(results, indent=1))
    if not any(r.get("id") for r in results.values()):
        sys.exit(1)
    store.client().set(posted_key, json.dumps(results))


if __name__ == "__main__":
    main()
