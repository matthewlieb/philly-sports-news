"""Tweet writers for each slot.

The model writes only the tweet's words; links are appended in code so they
are never truncated or mangled, and length is measured the way X measures it
(every link counts as 23 characters).
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Literal

from lib import briefs
from lib.search import tavily_search
from lib.teams import TEAMS, TEAM_SLUGS, brief_url, team_url
from twitter_bot import state

SlotType = Literal["brief", "article", "day_review", "historic"]

X_MAX_CHARS = 280
X_LINK_CHARS = 23
_LINK_RE = re.compile(r"https?://\S+|\b[\w-]+(?:\.[\w-]+)*\.(?:com|net|org|io|co)(?:/\S*)?", re.I)
_TEAM_KEYWORDS = {
    "eagles": ("eagles", "hurts", "sirianni", "saquon", "barkley"),
    "sixers": ("sixers", "76ers", "embiid", "maxey", "nick nurse"),
    "phillies": ("phillies", "harper", "schwarber", "wheeler", "citizens bank park"),
    "flyers": ("flyers", "tocchet", "michkov", "konecny"),
}


class Tweet:
    def __init__(self, text: str, url: str | None = None, team: str | None = None, headline: str = ""):
        self.text = text
        self.url = url
        self.team = team
        self.headline = headline


def get_tweet_slot() -> SlotType:
    """TWEET_SLOT overrides; otherwise the UTC hour of the scheduled run picks the slot."""
    slot = (os.environ.get("TWEET_SLOT") or "").strip().lower()
    if slot in ("brief", "article", "day_review", "historic"):
        return slot
    hour = datetime.now(timezone.utc).hour
    if hour in (12, 13):
        return "brief"
    if hour in (2, 3):
        return "day_review"
    return "article"


def x_length(text: str) -> int:
    return len(_LINK_RE.sub("x" * X_LINK_CHARS, text))


def compose(body: str, links: list[str] = ()) -> str:
    """Body (shortened at a word boundary if needed) followed by links, within X's limit."""
    body = _LINK_RE.sub("", body or "").replace("—", ",").strip()
    body = " ".join(body.split())
    budget = X_MAX_CHARS - sum(X_LINK_CHARS + 1 for _ in links)
    if x_length(body) > budget:
        body = body[: budget - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return " ".join([body, *links]).strip()


def infer_team(*texts: str) -> str | None:
    blob = " ".join(t or "" for t in texts).lower()
    for team, words in _TEAM_KEYWORDS.items():
        if any(w in blob for w in words):
            return team
    return None


def _voice() -> str:
    from twitter_bot.config.voice import EXAMPLE_TWEETS, VOICE_DESCRIPTION
    examples = "\n".join(f'- "{e}"' for e in EXAMPLE_TWEETS)
    return f"{VOICE_DESCRIPTION.strip()}\n\nExamples of your tweets (match the voice, not the content):\n{examples}"


def _ask(system: str, user: str) -> dict:
    from openai import OpenAI
    resp = OpenAI().chat.completions.create(
        model=os.environ.get("TWEET_MODEL", "gpt-5.4-mini"),
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": f"{_voice()}\n\n{system}\n\n{_GROUNDING}"},
                  {"role": "user", "content": user}],
    )
    return json.loads(resp.choices[0].message.content or "{}")


_NO_LINKS = "Do NOT include any URL, domain name or 'phillysportdaily.com'; links are added separately."
_GROUNDING = ("Accuracy rule: every name, number, opponent, date and claim in the tweet must appear in the material "
              "provided. Do not add stats or context from memory, even if you believe it is true.")


# --- Brief (morning): promote today's daily brief on the site ---

def brief_tweet() -> Tweet | None:
    day = briefs.local_today()
    available = [t for t in TEAM_SLUGS if briefs.get_brief(t, day)]
    if not available:
        print(f"No briefs for {day} yet.", file=sys.stderr)
        return None
    last = state.last_team()
    start = (TEAM_SLUGS.index(last) + 1) if last else 0
    order = TEAM_SLUGS[start:] + TEAM_SLUGS[:start]
    team = next(t for t in order if t in available)
    brief = briefs.get_brief(team, day)

    out = _ask(
        f"""Write ONE tweet that makes {TEAMS[team]['name']} fans want to read today's brief.
- Lead with the most interesting specific detail or stake from the brief, as your own take. Not a summary of everything.
- At most 200 characters. One hashtag at most ({TEAMS[team]['hashtag']} if it fits).
- Use only facts stated in the brief. {_NO_LINKS}
Return JSON: {{"text": "..."}}""",
        f"Brief headline: {brief['headline']}\nSummary: {brief['summary']}",
    )
    url = brief_url(team, day)
    return Tweet(compose(out.get("text", ""), [url]), url=url, team=team, headline=brief["headline"])


# --- Article (midday): a take on one story, linking to it and to the team page ---

def _candidate_articles() -> list[dict]:
    results = tavily_search("Philadelphia Eagles 76ers Phillies Flyers news", topic="news", max_results=10, time_range="day")
    articles = [{"title": (r.get("title") or "").strip(), "url": (r.get("url") or "").strip(),
                 "snippet": (r.get("content") or "")[:300]} for r in results]
    if len(articles) < 3:
        from lib.articles import collect_ranked_articles
        for team in TEAM_SLUGS:
            articles += [{"title": a["title"], "url": a["url"], "snippet": a["description"][:300], "team": team}
                         for a in collect_ranked_articles(team, max_articles=5)]
    for a in articles:
        a["team"] = a.get("team") or infer_team(a["title"], a["url"])
    done = state.tweeted_urls()
    return [a for a in articles if a["title"] and a["url"].startswith("http") and a["url"] not in done and a["team"]]


def article_tweet() -> Tweet | None:
    candidates = _candidate_articles()[:10]
    if not candidates:
        print("No untweeted articles found.", file=sys.stderr)
        return None
    last = state.last_team()
    numbered = "\n\n".join(f"[{i}] ({a['team']}) {a['title']}\n{a['snippet']}" for i, a in enumerate(candidates, 1))
    out = _ask(
        f"""Pick ONE story and write a tweet reacting to it.
- Lead with your take, joke, question or the key detail. Never just restate the headline. Never write "BREAKING".
- At most 200 characters. Only facts from that story's text.
- {"Prefer a team other than the " + last + " if a good story exists." if last else "Any team is fine."}
- {_NO_LINKS}
Return JSON: {{"choice": <story number>, "text": "..."}}""",
        numbered,
    )
    choice = out.get("choice")
    if not isinstance(choice, int) or not 1 <= choice <= len(candidates):
        choice = 1
    a = candidates[choice - 1]
    team_link = team_url(a["team"]).removeprefix("https://www.").rstrip("/")
    body = f"{out.get('text', '')} More {TEAMS[a['team']]['name']}:"
    return Tweet(compose(body, [team_link, a["url"]]), url=a["url"], team=a["team"], headline=a["title"])


# --- Day in review (night): no link ---

def day_review_tweet() -> Tweet | None:
    results = tavily_search("Philadelphia Eagles 76ers Phillies Flyers news today", topic="news", max_results=12, time_range="day")
    if not results:
        return None
    context = "\n".join(f"- {r.get('title', '')}: {(r.get('content') or '')[:300]}" for r in results)
    out = _ask(
        f"""Write ONE "day in review" tweet wrapping up today's Philly sports news.
- Hit the 2 or 3 biggest storylines with your take. Short sentences. Hashtags only if they fit.
- Only facts from the context. At most 270 characters. {_NO_LINKS}
Return JSON: {{"text": "..."}}""",
        context,
    )
    return Tweet(compose(out.get("text", "")))


# --- On this day (manual only): must be grounded in a search result for today's date ---

def historic_tweet() -> Tweet | None:
    month_day = datetime.now(timezone.utc).strftime("%B %-d")
    results = tavily_search(f'"{month_day}" Philadelphia Eagles OR 76ers OR Phillies OR Flyers history on this day',
                            topic="general", max_results=8)
    if not results:
        return None
    context = "\n\n".join(f"- {r.get('title', '')}\n{(r.get('content') or '')[:400]}" for r in results)
    out = _ask(
        f"""Today is {month_day}. Write ONE "On this day" tweet about a Philadelphia Eagles, 76ers, Phillies or Flyers moment.
- Use ONLY a moment the context below explicitly dates to {month_day} (with its year). If none qualifies, set found to false.
- At most 270 characters. {_NO_LINKS}
Return JSON: {{"found": true/false, "text": "..."}}""",
        context,
    )
    if not out.get("found"):
        print(f"No verifiable {month_day} moment in search results.", file=sys.stderr)
        return None
    return Tweet(compose(out.get("text", "")))


WRITERS = {"brief": brief_tweet, "article": article_tweet, "day_review": day_review_tweet, "historic": historic_tweet}
