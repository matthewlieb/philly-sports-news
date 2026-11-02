"""Cartoon scenes drawn for one video's own lines, for the beats that would otherwise fall back to stock footage.

Each scene is a Pixar-style still made for what that line says (from the player's approved cartoon when the line is
about one person), then animated into a 5-second clip. They illustrate the news ("Barkley is set to play" shows the
cartoon Barkley lacing up his cleats); they never depict a game moment as if it were real footage, and carry the same
no-logos, no-text rules as the rest of the cartoon media.

SHORTS_SCENES=1 turns it on for beats without a photo; SHORTS_SCENES=all draws every beat after the opener (whose
real photo is what stops the scroll). SCENES_MONTHLY_USD caps spending (default $60). Any failure leaves the beat as
it was.
"""
import base64
import io
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import requests

from lib import store

VIDEO_MODEL = "kwaivgi/kling-v2.5-turbo-pro"
COST_PER_SCENE = 0.55  # gpt-image-2 still (~$0.20) plus a 5 s Kling clip ($0.35)
STYLE = ("Pixar-style 3D animated film still, stylized characters with big expressive eyes, warm cinematic lighting, "
         "rich midnight green and silver palette. Vertical composition.")
RULES = "No logos, no team names, no NFL shield, no readable text, letters or numbers other than jersey numbers."


def enabled() -> bool:
    return bool(os.environ.get("SHORTS_SCENES")) and bool(os.environ.get("REPLICATE_API_TOKEN"))


def _spend_key() -> str:
    return store.key("scenes", "usd", datetime.now(timezone.utc).strftime("%Y-%m"))


def _within_budget(count: int) -> bool:
    used = float(store.client().get(_spend_key()) or 0)
    return used + count * COST_PER_SCENE <= float(os.environ.get("SCENES_MONTHLY_USD", "60"))


def _record(count: int) -> None:
    r, k = store.client(), _spend_key()
    r.set(k, f"{float(r.get(k) or 0) + count * COST_PER_SCENE:.2f}")
    r.expire(k, 40 * 86400)


def _ideas(script: dict, beats: list[int]) -> dict[int, dict]:
    """{beat: {"image": still prompt, "motion": animation prompt}} written for each beat's line."""
    from openai import OpenAI

    lines = "\n".join(f"{i}: {script['beats'][i]['say']} (about: {script['beats'][i].get('person') or 'the team'})"
                      for i in beats)
    resp = OpenAI().chat.completions.create(
        model=os.environ.get("SHORTS_MODEL", "gpt-5.4-mini"), response_format={"type": "json_object"},
        messages=[{"role": "system", "content": (
            "You storyboard a Philadelphia Eagles news short drawn as a Pixar-style cartoon. For each numbered line, "
            "describe one simple, funny or emotional cartoon scene that illustrates it: a symbolic everyday moment, "
            "not a recreation of a real play, game or press conference. Players wear plain midnight green jerseys; "
            "opponents and other teams are shown only symbolically (e.g. a road sign, a bus heading to a city). Keep "
            "each scene to one or two characters and one clear action, no words or signs to read. Return JSON "
            '{"scenes": {"<line number>": {"image": "<still description, 1-2 sentences>", '
            '"motion": "<what moves in 5 seconds, one sentence, slow camera>"}}}')},
            {"role": "user", "content": lines}])
    raw = json.loads(resp.choices[0].message.content or "{}").get("scenes") or {}
    return {int(k): v for k, v in raw.items() if str(k).isdigit() and int(k) in beats and v.get("image")}


def _still(idea: dict, cartoon: bytes | None) -> bytes:
    from openai import OpenAI

    model = os.environ.get("CARTOON_IMAGE_MODEL", "gpt-image-2")
    prompt = f"{STYLE} {idea['image']} {RULES}"
    if cartoon:
        resp = OpenAI().images.edit(model=model, size="1024x1536", image=[("player.png", io.BytesIO(cartoon), "image/png")],
                                    prompt=f"The cartoon football player from the reference image, same face and "
                                           f"jersey number, in this scene: {prompt}")
    else:
        resp = OpenAI().images.generate(model=model, size="1024x1536", prompt=prompt)
    return base64.b64decode(resp.data[0].b64_json)


def _animate(still: Path, motion: str, out: Path) -> Path:
    import replicate

    with open(still, "rb") as image:
        result = replicate.run(VIDEO_MODEL, input={"prompt": f"{motion} Pixar-style 3D animation. {RULES}",
                                                   "start_image": image, "duration": 5, "aspect_ratio": "9:16"})
    out.write_bytes((result[0] if isinstance(result, list) else result).read())
    return out


def _cartoon_of(person: str, team: str) -> bytes | None:
    from shorts.cartoons import approved

    options = approved(person, team) if person else []
    return requests.get(options[0]["url"], timeout=60).content if options else None


def beat_scenes(script: dict, team: str, pictures: list[Path | None], workdir: Path,
                limit: int = 3) -> dict[int, Path]:
    """{beat: scene clip} for up to `limit` beats (see SHORTS_SCENES). Empty when off, over budget, or on failure."""
    every = os.environ.get("SHORTS_SCENES") == "all"
    beats = [i for i in range(len(script["beats"]))
             if (every and i > 0) or i >= len(pictures) or not pictures[i]][:limit]
    if not enabled() or not beats or not _within_budget(len(beats)):
        return {}
    try:
        ideas = _ideas(script, beats)
    except Exception as e:
        print(f"Scene ideas failed: {e}")
        return {}

    def one(i: int) -> tuple[int, Path | None]:
        try:
            still = workdir / f"scene{i}.png"
            still.write_bytes(_still(ideas[i], _cartoon_of(script["beats"][i].get("person") or "", team)))
            return i, _animate(still, ideas[i].get("motion") or "Slow push in.", workdir / f"scene{i}.mp4")
        except Exception as e:
            print(f"Scene for beat {i} failed: {e}")
            return i, None

    with ThreadPoolExecutor(max(1, len(ideas))) as pool:
        made = {i: p for i, p in pool.map(one, list(ideas)) if p}
    if made:
        _record(len(made))
    return made
