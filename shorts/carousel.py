"""Instagram carousels (1080x1350 JPEG slides): a postgame recap and a weekly "5 things".

All facts come from ESPN data or already fact-checked briefs; the weekly picks are checked again.
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw

from lib import briefs
from lib.factcheck import check
from lib.teams import TEAMS
from shorts.graphics import THEMES, _display, _fit_display, _line_height, _sans, _wrap, field_background

W, H = 1080, 1350
PAD = 90


def _base(team: str, page: int, pages: int, eyebrow: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    theme = THEMES[team]
    img = field_background((W, H), team, 135)
    d = ImageDraw.Draw(img)
    font = _sans(34, 800)
    w = font.getlength(eyebrow) + 52
    d.rounded_rectangle([PAD, PAD, PAD + w, PAD + 64], radius=32, fill=theme["accent"])
    d.text((PAD + 26, PAD + 32), eyebrow, font=font, fill=(255, 255, 255), anchor="lm")
    small = _sans(30, 700)
    d.text((PAD, H - PAD), f"{TEAMS[team]['name'].upper()} DAILY", font=small, fill=(255, 255, 255), anchor="ls")
    d.text((W - PAD, H - PAD), f"{page}/{pages}", font=small, fill=theme["muted"], anchor="rs")
    return img, d


def _big_lines(d, lines: list[tuple[str, tuple]], top: int, font) -> int:
    lh = int(_line_height(font) * 1.12)
    for i, (text, color) in enumerate(lines):
        d.text((PAD, top + i * lh), text, font=font, fill=color, anchor="lt")
    return top + lh * len(lines)


def _paragraph(d, text: str, top: int, size: int = 50, color=(240, 244, 244)) -> int:
    """Wrapped text, shrunk until it ends above the footer."""
    bottom = H - PAD - 70
    while True:
        font = _sans(size, 600)
        lines = _wrap(text, font, W - 2 * PAD)
        if top + len(lines) * int(size * 1.45) <= bottom or size <= 28:
            break
        size -= 2
    for line in lines:
        d.text((PAD, top), line, font=font, fill=color)
        top += int(size * 1.45)
    return top


def postgame_slides(team: str, snapshot: dict, brief: dict) -> list[Image.Image]:
    theme, g, nxt = THEMES[team], snapshot["last_game"], snapshot.get("next_game")
    name, them = TEAMS[team]["name"].upper(), g["opponent"].split()[-1].upper()
    ours, theirs = int(g["our_score"]), int(g["their_score"])
    pages = 4 if nxt else 3
    when = datetime.fromisoformat(g["kickoff_utc"]).strftime("%b %-d").upper()

    s1, d = _base(team, 1, pages, f"FINAL · {when}")
    rows = sorted([(name, ours), (them, theirs)], key=lambda r: -r[1])
    font = _display(190)
    y = 330
    for label, score in rows:
        won = score == max(ours, theirs) and ours != theirs
        color = theme["accent"] if won else (255, 255, 255)
        d.text((PAD, y), label, font=font, fill=color, anchor="lt")
        d.text((W - PAD, y), str(score), font=font, fill=color, anchor="rt")
        y += int(_line_height(font) * 1.25)
    sub = f"{'W' if g['won'] else 'L'} · {snapshot.get('record', '')} · {g.get('venue') or ''}".strip(" ·")
    _paragraph(d, sub, y + 30, 44, theme["muted"])

    s2, d = _base(team, 2, pages, "KEY NUMBERS")
    ours_abbr = next((l["team"] for l in g.get("leaders") or [] if l["team"] and l["team"] not in (g["opponent_abbr"],)), "")
    picks = [l for l in g.get("leaders") or [] if l["team"] == ours_abbr][:3]
    y = 250
    for l in picks:
        d.text((PAD, y), l["category"].upper(), font=_sans(34, 800), fill=theme["muted"])
        nf, nl = _fit_display(l["name"].upper(), W - 2 * PAD, 1, 96, 60)
        d.text((PAD, y + 48), nl[0], font=nf, fill=(255, 255, 255), anchor="lt")
        d.text((PAD, y + 48 + _line_height(nf) + 18), l["value"], font=_sans(42, 700), fill=(235, 240, 240))
        y += 310

    s3, d = _base(team, 3, pages, "WHAT IT MEANS")
    font, lines = _fit_display(brief["headline"].upper(), W - 2 * PAD, 3, 110, 70)
    y = _big_lines(d, [(l, (255, 255, 255)) for l in lines], 250, font)
    _paragraph(d, brief["summary"], y + 40, 46)

    slides = [s1, s2, s3]
    if nxt:
        s4, d = _base(team, 4, pages, "NEXT UP")
        opp = f"{'VS' if nxt['home'] else '@'} {nxt['opponent'].split()[-1].upper()}"
        font, lines = _fit_display(opp, W - 2 * PAD, 2, 200, 100)
        y = _big_lines(d, [(l, (255, 255, 255)) for l in lines], 330, font)
        y = _paragraph(d, nxt["kickoff_et"], y + 30, 50, theme["muted"])
        _paragraph(d, "Full breakdown every morning at phillysportdaily.com (link in bio).", y + 120, 44)
        slides.append(s4)
    return slides


_WEEKLY = """From these daily {team} briefs, pick the 5 storylines that mattered most this week, newest
developments first. For each: a title (max 6 words) and 1 to 2 sentences (max 35 words) saying what happened
and why it matters. Use ONLY facts in the briefs. Return JSON: {{"items": [{{"title": "...", "text": "..."}}]}}"""


def weekly_slides(team: str, today: str) -> tuple[list[Image.Image], str] | None:
    from openai import OpenAI

    start = (datetime.fromisoformat(today) - timedelta(days=7)).date().isoformat()
    week = [b for d in briefs.brief_dates(team, limit=8) if start <= d <= today and (b := briefs.get_brief(team, d))]
    if len(week) < 3:
        return None
    evidence = "\n\n".join(f"{b['date']}: {b['headline']}\n{b['summary']}\n" +
                           "\n".join(p for s in b["sections"] for p in s["paragraphs"]) for b in week)
    resp = OpenAI().chat.completions.create(
        model=os.environ.get("SHORTS_MODEL", "gpt-5.4-mini"), response_format={"type": "json_object"},
        messages=[{"role": "system", "content": _WEEKLY.format(team=TEAMS[team]["full_name"])},
                  {"role": "user", "content": evidence}])
    items = [i for i in json.loads(resp.choices[0].message.content or "{}").get("items") or [] if i.get("title") and i.get("text")][:5]
    fixes = check([f"{i['title']}: {i['text']}" for i in items], evidence)
    items = [i if k not in fixes else ({"title": i["title"], "text": fixes[k].split(": ", 1)[-1]} if fixes[k] else None)
             for k, i in enumerate(items)]
    items = [i for i in items if i]
    if len(items) < 3:
        return None

    theme, pages = THEMES[team], len(items) + 1
    cover, d = _base(team, 1, pages, "THIS WEEK")
    font, lines = _fit_display(f"{len(items)} THINGS FROM THE {TEAMS[team]['name'].upper()}' WEEK", W - 2 * PAD, 3, 150, 90)
    y = _big_lines(d, [(l, theme["accent"] if i == len(lines) - 1 else (255, 255, 255)) for i, l in enumerate(lines)], 280, font)
    _paragraph(d, "Swipe for what happened and why it matters.", y + 40, 46, theme["muted"])
    slides = [cover]
    for n, item in enumerate(items, 1):
        s, d = _base(team, n + 1, pages, f"{n} OF {len(items)}")
        font, lines = _fit_display(item["title"].upper(), W - 2 * PAD, 3, 120, 76)
        y = _big_lines(d, [(l, (255, 255, 255)) for l in lines], 260, font)
        _paragraph(d, item["text"], y + 40, 48)
        slides.append(s)
    caption = (f"{len(items)} things from the {TEAMS[team]['name']}' week. Full daily breakdowns at phillysportdaily.com "
               f"(link in bio).\n\n{TEAMS[team]['hashtag']} #{TEAMS[team]['name']} #NFL")
    return slides, caption


def postgame_caption(team: str, snapshot: dict, brief: dict) -> str:
    g = snapshot["last_game"]
    return (f"Final: {TEAMS[team]['name']} {g['our_score']}, {g['opponent']} {g['their_score']}. {brief['summary']}\n\n"
            f"Full breakdown at phillysportdaily.com (link in bio).\n\n{TEAMS[team]['hashtag']} #{TEAMS[team]['name']}")


def save(slides: list[Image.Image], out_dir: Path, stem: str) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, s in enumerate(slides, 1):
        p = out_dir / f"{stem}-{i}.jpg"
        s.convert("RGB").save(p, quality=92)
        paths.append(p)
    return paths
