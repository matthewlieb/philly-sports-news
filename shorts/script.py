"""Turn today's brief (plus ESPN facts) into a ~30 second vertical-video script."""
import json
import os

from openai import OpenAI

from lib.teams import TEAMS

_SYSTEM = """You write the daily {team} short-form video (YouTube Shorts / Instagram Reels) for a {name} fan account.

Retention rules (these decide whether the video gets shown to anyone):
- Beat 1 is the hook. It must land in under 2 seconds: start mid-thought with the single most surprising or high-stakes fact. No greetings, no "today", no channel name.
- 4 to 5 beats total, 70 to 85 spoken words overall (about 30 seconds). Every sentence earns its place; cut filler.
- Never repeat a sentence. The comment question appears only once, as the entire last beat.
- Each beat is one idea. Short punchy sentences a fan would say out loud.
- The last beat asks fans one specific question to answer in the comments, phrased so it flows back into the hook if the video loops.

Accuracy rules:
- Use ONLY facts from the brief and the ESPN facts below. Never add stats, quotes, opponents, dates or player details from memory.
- Rumors must be called rumors. Attribute big claims to the outlet ("per PhillyVoice").

On-screen cards: each beat may show one card that shows the same fact the beat is saying at that moment (never a fact from a different beat).
- "stat": a number or short value (label like "RECORD", value like "2-2", detail like "2nd in NFC East")
- "matchup": next or last game (label "NEXT UP" or "FINAL", value like "@ JAX", detail like "Sun 9:30 AM ET, London"); only on a beat that talks about that game
- "text": a 2 to 6 word headline (label like "TRADE", value like "JURGENS TO BALTIMORE")
- "none": no card (use for the hook and the closing question)
Card values must be short (max 20 characters) and must be facts stated in the material.

Also write:
- title: under 70 characters, curiosity + specific detail, ends with #Eagles style team hashtag. No clickbait lies.
- caption: 1 to 2 sentences for the post description (no hashtags, no links).
- hashtags: 3 to 5 relevant hashtags.

Return JSON: {{"beats": [{{"say": "...", "card": {{"kind": "stat|matchup|text|none", "label": "", "value": "", "detail": ""}}}}], "hook_text": "max 7 words, the on-screen version of beat 1", "title": "...", "caption": "...", "hashtags": ["#..."]}}"""


def _facts_block(snapshot: dict) -> str:
    if not snapshot:
        return "ESPN facts: unavailable."
    lines = [f"Record: {snapshot.get('record')}", f"Standing: {snapshot.get('standing')}"]
    if g := snapshot.get("last_game"):
        result = "W" if g["won"] else "L"
        lines.append(f"Last game: {result} {g['our_score']}-{g['their_score']} {'vs' if g['home'] else 'at'} {g['opponent']} ({g['kickoff_et']})")
    if g := snapshot.get("next_game"):
        lines.append(f"Next game: {'vs' if g['home'] else 'at'} {g['opponent']} ({g['opponent_abbr']}), {g['kickoff_et']}"
                     + (f", {g['venue']}" if g.get("venue") else ""))
    return "ESPN facts:\n" + "\n".join(lines)


def _brief_block(brief: dict) -> str:
    body = "\n\n".join(f"{s['heading']}\n" + "\n".join(s["paragraphs"]) for s in brief["sections"])
    return f"Brief headline: {brief['headline']}\nSummary: {brief['summary']}\n\n{body}"


MAX_WORDS = 90


def _spoken_words(script: dict) -> int:
    return sum(len((b.get("say") or "").split()) for b in script.get("beats") or [])


def _clean(text: str) -> str:
    return " ".join(text.replace("—", ", ").replace("–", "-").replace(" ,", ",").split())


def write_script(team: str, brief: dict, snapshot: dict) -> dict:
    t = TEAMS[team]
    messages = [
        {"role": "system", "content": _SYSTEM.format(team=t["full_name"], name=t["name"])},
        {"role": "user", "content": f"{_brief_block(brief)}\n\n{_facts_block(snapshot)}"},
    ]
    for _ in range(2):
        resp = OpenAI().chat.completions.create(
            model=os.environ.get("SHORTS_MODEL", "gpt-5.4-mini"),
            response_format={"type": "json_object"},
            messages=messages,
        )
        raw = resp.choices[0].message.content or "{}"
        script = json.loads(raw)
        words = _spoken_words(script)
        if words <= MAX_WORDS:
            break
        messages += [{"role": "assistant", "content": raw},
                     {"role": "user", "content": f"That is {words} spoken words. Cut it to at most {MAX_WORDS - 10} "
                                                 "by removing the weakest details. Same JSON format."}]
    beats = []
    for b in script.get("beats") or []:
        say = _clean(b.get("say") or "")
        if say and not any(say in prev["say"] or prev["say"].endswith(say) for prev in beats):
            b["say"] = say
            beats.append(b)
    if len(beats) < 3:
        raise ValueError(f"Script has too few beats: {script}")
    for b in beats:
        card = b.get("card") or {}
        if card.get("kind") not in ("stat", "matchup", "text") or not card.get("value"):
            b["card"] = None
        else:
            b["card"] = {k: str(card.get(k) or "").strip()[:28] for k in ("kind", "label", "value", "detail")}
            b["card"]["detail"] = str(card.get("detail") or "").strip()[:48]
    script["beats"] = beats
    script["hook_text"] = _clean(script.get("hook_text") or beats[0]["say"]).rstrip(",")
    return script
