"""Weekly trivia video: three questions, a ticking 3-second countdown after each, then the answer.

Quizzes are the format that breaks out most often relative to a channel's size: people answer in the comments,
rewatch, and share. A wrong answer would sink the account's credibility, so questions never come from the model's
memory. Each one is written from a Wikipedia article and must quote the sentence it rests on; the quote is checked
word for word against the article, the answer must appear in it, and the set then goes through the fact check.
Only settled history is asked about (no "current" or all-time record questions, which can go stale).
"""
import hashlib
import json
import os
import random
import re

import requests
from openai import OpenAI

from lib import store
from lib.factcheck import check
from lib.teams import TEAMS

_UA = {"User-Agent": "PhillySportDaily/1.0 (https://www.phillysportdaily.com)"}

TOPICS = {
    "eagles": [
        "Philadelphia Eagles", "History of the Philadelphia Eagles", "Super Bowl LII", "Super Bowl LIX", "Philly Special",
        "Super Bowl XV", "Super Bowl XXXIX", "1960 NFL Championship Game", "1948 NFL Championship Game",
        "1949 NFL Championship Game", "Fog Bowl (American football)", "Miracle at the New Meadowlands",
        "Lincoln Financial Field", "Veterans Stadium", "Franklin Field", "NovaCare Complex", "Fly, Eagles Fly", "Swoop (mascot)",
        "Brian Dawkins", "Reggie White", "Chuck Bednarik", "Jason Kelce", "Donovan McNabb", "Randall Cunningham",
        "Brian Westbrook", "Harold Carmichael", "Steve Van Buren", "Pete Pihos", "Tommy McDonald", "Fletcher Cox",
        "Brandon Graham", "Nick Foles", "Zach Ertz", "DeSean Jackson", "Michael Vick", "Wilbert Montgomery",
        "Ron Jaworski", "Dick Vermeil", "Andy Reid", "Buddy Ryan", "Doug Pederson", "Greasy Neale", "Jeffrey Lurie",
        "Eagles–Cowboys rivalry", "Eagles–Giants rivalry", "Bert Bell", "Jalen Hurts", "Saquon Barkley",
        "Lane Johnson", "Jason Peters", "Trent Cole", "Eric Allen", "Seth Joyner", "Jerome Brown",
    ],
}

_WRITE = """Write trivia questions for {name} fans from the Wikipedia article text below (article: "{title}").

Rules:
- Every question must be answerable from ONE sentence of the text. Copy that sentence EXACTLY, character for
  character, into "quote".
- The answer is 1 to 4 words and appears word for word in the quote (a name, a year, a number, a team, a place).
- Settled history only: no "current", "active", "still", "all-time", "most ever" or franchise-record questions, since
  those can change. Facts about specific past events, seasons, games, nicknames, firsts, draft picks, jersey numbers.
- Aim for what fans love and argue about: iconic plays and who made them, nicknames, jersey numbers, Super Bowl and
  playoff moments, legends' colleges and draft stories, firsts, famous quotes. A fan should be able to answer in
  3 seconds or groan "I knew that!" when it's revealed.
- Never: the answer is the {name} themselves, betting lines, attendance, TV ratings, contract dollar figures,
  obscure box-score numbers, or anything only answerable by reading this article.
- The question must make sense on its own to someone scrolling: name the player or game and give the year or
  context ("In Super Bowl LII, who caught the Philly Special touchdown?"), never "he", "this game" or "that season".
- "question": max 12 words, ends with "?". "spoken_answer": the answer plus one short fun fact from the quote,
  under 22 words, starting with the answer; write numbers as words a narrator would say.
- "answer_person": the answer's full name if the answer is a person, else "".
- "fun": 1 to 10, how much a casual {name} fan would enjoy this question. Be harsh.

Write 4 candidates. Return JSON: {{"questions": [{{"question": "...", "answer": "...", "quote": "...",
"spoken_answer": "...", "answer_person": "", "fun": 7}}]}}

Article text:
{text}"""


def _article(title: str) -> str:
    resp = requests.get("https://en.wikipedia.org/w/api.php", headers=_UA, timeout=30, params={
        "action": "query", "prop": "extracts", "explaintext": 1, "titles": title, "format": "json", "redirects": 1})
    resp.raise_for_status()
    page = next(iter(resp.json()["query"]["pages"].values()))
    return page.get("extract") or ""


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("–", "-").replace("—", "-").replace("’", "'")).strip().lower()


def _window(text: str, rnd: random.Random, size: int = 9000) -> str:
    """A random stretch of the article (skipping reference lists), so repeat topics yield new questions."""
    text = re.split(r"\n== (See also|References|Notes|External links|Further reading) ==", text)[0]
    if len(text) <= size:
        return text
    start = rnd.randrange(0, len(text) - size)
    return text[start:start + size]


def _candidates(team: str, title: str, rnd: random.Random) -> list[dict]:
    full = _article(title)
    if len(full) < 1500:
        return []
    resp = OpenAI().chat.completions.create(
        model=os.environ.get("SHORTS_MODEL", "gpt-5.4-mini"),
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": _WRITE.format(name=TEAMS[team]["full_name"], title=title,
                                                             text=_window(full, rnd))}],
    )
    out = []
    norm_full = _norm(full)
    for q in json.loads(resp.choices[0].message.content or "{}").get("questions") or []:
        quote, answer = _norm(q.get("quote") or ""), _norm(q.get("answer") or "")
        question = " ".join(str(q.get("question") or "").split())
        stale = re.search(r"\b(current|currently|active|still|all-time|most ever|record)\b", question, re.I)
        own_team = re.search(TEAMS[team]["name"], q.get("answer") or "", re.I)
        if (len(quote) > 30 and quote in norm_full and answer and answer in quote and question.endswith("?")
                and len(question.split()) <= 13 and not stale and not own_team
                and int(q.get("fun") or 0) >= 7):
            out.append({**q, "question": question, "source": title})
    return out


def _key(q: dict) -> str:
    return hashlib.sha1(_norm(q["question"] + "|" + q["answer"]).encode()).hexdigest()[:16]


def pick_questions(team: str, week: str, count: int = 3) -> list[dict]:
    """`count` verified questions from different articles, none asked before."""
    r = store.client()
    used_q = store.key("quiz", team, "asked")
    used_topics = store.key("quiz", team, "topics")
    recent_topics = set(r.lrange(used_topics, 0, 29))
    rnd = random.Random(f"{team}-{week}")
    topics = [t for t in TOPICS[team] if t not in recent_topics] or TOPICS[team][:]
    rnd.shuffle(topics)
    chosen = []
    for title in topics:
        if len(chosen) == count:
            break
        try:
            cands = [c for c in _candidates(team, title, rnd) if not r.sismember(used_q, _key(c))]
        except Exception as e:
            print(f"Quiz topic {title} failed: {e}")
            continue
        if not cands:
            continue
        evidence = "\n".join(f"[{c['source']}] {c['quote']}" for c in cands)
        items = [f"Q: {c['question']} A: {c['answer']}. {c.get('spoken_answer', '')}" for c in cands]
        fixes = check(items, evidence)
        good = [c for i, c in enumerate(cands) if i not in fixes]
        if good:
            chosen.append(max(good, key=lambda c: int(c.get("fun") or 0)))
    return chosen


def build_script(team: str, questions: list[dict]) -> dict:
    name = TEAMS[team]["name"]
    beats = [{"say": f"Only real {name} fans get all {len(questions)}.", "person": "", "card": None}]
    for n, q in enumerate(questions, 1):
        beats.append({"say": q["question"], "person": "", "countdown": 3,
                      "card": {"kind": "question", "label": f"Question {n} of {len(questions)}", "value": q["question"]}})
        answer = " ".join(str(q.get("spoken_answer") or q["answer"]).split())
        beats.append({"say": answer, "person": q.get("answer_person") or "",
                      "card": {"kind": "text", "label": "Answer", "value": q["answer"][:28], "detail": ""}})
    beats.append({"say": "How many did you get? Comment your score.", "person": "", "card": None})
    sources = sorted({q["source"] for q in questions})
    return {
        "kind": "quiz",
        "beats": beats,
        "hook_text": f"CAN YOU GET {len(questions)}/{len(questions)}?",
        "title": f"Only real {name} fans get all {len(questions)} 🦅 #{name}",
        "caption": f"{name} trivia: {len(questions)} questions, 3 seconds each. Comment your score.",
        "hashtags": [f"#{name}", f"#{name}Trivia", "#NFL", "#FlyEaglesFly" if team == "eagles" else "#Philly"],
        "sources": [f"https://en.wikipedia.org/wiki/{s.replace(' ', '_')}" for s in sources],
        "questions": questions,
    }


def record(team: str, script: dict) -> None:
    r = store.client()
    for q in script["questions"]:
        r.sadd(store.key("quiz", team, "asked"), _key(q))
        r.lpush(store.key("quiz", team, "topics"), q["source"])
    r.ltrim(store.key("quiz", team, "topics"), 0, 29)
