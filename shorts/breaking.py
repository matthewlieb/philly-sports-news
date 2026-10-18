"""Breaking-news videos: spot a major new development and post about it within the hour.

Runs with the half-hourly schedule. Cheap until something happens: it reads the team's news feeds (free), and only
headlines it hasn't seen before, published in the last few hours, go to the model. The model decides whether one is a
major development nobody has covered yet (injury designations, trades, signings and releases, a QB change, coaching
changes, suspensions). Only then does it search for fuller reporting and write the script, which goes through the same
fact check as every other video.

Limits: 8am to 11pm Eastern, at most MAX_PER_DAY a day, never the same story twice.
"""
import json
import os
from datetime import datetime, timedelta, timezone

from openai import OpenAI

from lib import briefs, store
from lib.articles import collect_ranked_articles
from lib.published import published_many
from lib.search import tavily_search
from lib.teams import TEAMS

MAX_PER_DAY = 2
FRESH_HOURS = 3
QUIET_BEFORE, QUIET_AFTER = 8, 23

_DECIDE = """You run the {name} news desk for a fan account's short videos. Decide if any of these new headlines is
BREAKING: a major development fans need to hear about right now that the account hasn't covered.

Breaking: a starter or key player ruled out, placed on IR, or out for the season; a trade; signing or releasing a
notable player; a starting QB change; a head coach or coordinator fired or hired; a suspension or arrest; a big
contract extension for a core player.
Not breaking: previews, analysis, opinion, rankings, power rankings, betting odds, practice notes, routine injury
updates with no status change, rumors without a credible named reporter, anything about another team only.

Already covered (don't repeat these unless there's a real new development):
{covered}

New headlines (newest first):
{headlines}

Return JSON: {{"breaking": true or false, "story": "one sentence: what happened", "slug": "short-kebab-id-for-this-story",
"search": "a web search query for fuller reporting on this story", "headlines": [indexes of the headlines about it]}}"""


def _covered(team: str, day: str) -> list[str]:
    r = store.client()
    out = []
    if brief := briefs.get_brief(team, day):
        out.append(f"Today's brief: {brief['headline']}. {brief['summary']}")
    for kind in ("morning", "postgame", "breaking"):
        if raw := r.get(store.key("shortscript", team, day, kind)):
            out.append(f"Today's {kind} video: {json.loads(raw).get('title', '')}")
    out += [f"Breaking video: {s}" for s in r.lrange(store.key("breaking", team, "stories"), 0, 9)]
    return out or ["(nothing yet today)"]


def _fresh_headlines(team: str) -> list[dict]:
    """Articles from our feeds published in the last FRESH_HOURS that this check hasn't looked at before."""
    r = store.client()
    seen_key = store.key("breaking", team, "seen")
    articles = [a for a in collect_ranked_articles(team, max_articles=25) if a["title"]]
    new = [a for a in articles if not r.sismember(seen_key, a["url"])]
    if not new:
        return []
    r.sadd(seen_key, *[a["url"] for a in new])
    r.expire(seen_key, 7 * 86400)
    dates = published_many([a["url"] for a in new])
    cutoff = datetime.now(timezone.utc) - timedelta(hours=FRESH_HOURS)
    fresh = [{**a, "published": dates.get(a["url"])} for a in new]
    fresh = [a for a in fresh if a["published"] and a["published"] >= cutoff]
    return sorted(fresh, key=lambda a: a["published"], reverse=True)


def find_story(team: str, day: str) -> dict | None:
    """The breaking story to cover now, with its reporting as script material, or None."""
    now = datetime.now(briefs.EASTERN)
    if not QUIET_BEFORE <= now.hour < QUIET_AFTER:
        return None
    r = store.client()
    if r.llen(store.key("breaking", team, "days", day)) >= MAX_PER_DAY:
        return None
    fresh = _fresh_headlines(team)
    if not fresh:
        print("Breaking check: no new headlines.")
        return None
    headlines = "\n".join(f"{i}. [{a['source']}, {a['published']:%-I:%M %p UTC}] {a['title']}: {a['description'][:200]}"
                          for i, a in enumerate(fresh))
    resp = OpenAI().chat.completions.create(
        model=os.environ.get("SHORTS_MODEL", "gpt-5.4-mini"),
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": _DECIDE.format(
            name=TEAMS[team]["full_name"], covered="\n".join(f"- {c}" for c in _covered(team, day)), headlines=headlines)}],
    )
    decision = json.loads(resp.choices[0].message.content or "{}")
    if not decision.get("breaking") or not decision.get("slug"):
        print(f"Breaking check: {len(fresh)} new headline(s), nothing breaking.")
        return None
    slug = str(decision["slug"])[:60]
    if r.get(store.key("shorts", team, "breaking", slug)):
        return None
    picked = [fresh[i] for i in decision.get("headlines") or [] if isinstance(i, int) and 0 <= i < len(fresh)]
    reporting = [f"{a['source']} ({a['published']:%b %-d %-I:%M %p UTC}): {a['title']}. {a['description']}" for a in picked]
    for res in tavily_search(decision.get("search") or decision["story"], max_results=6, time_range="day"):
        if res.get("content"):
            reporting.append(f"{res.get('url', '')}: {res.get('title', '')}. {res['content'][:1200]}")
    print(f"Breaking: {decision['story']}")
    return {"slug": slug, "story": decision["story"],
            "material": f"Breaking story: {decision['story']}\n\nReporting:\n" + "\n\n".join(reporting)}


def record(team: str, day: str, story: dict) -> None:
    r = store.client()
    r.rpush(store.key("breaking", team, "days", day), story["slug"])
    r.expire(store.key("breaking", team, "days", day), 3 * 86400)
    r.lpush(store.key("breaking", team, "stories"), f"{day}: {story['story']}")
    r.ltrim(store.key("breaking", team, "stories"), 0, 19)
