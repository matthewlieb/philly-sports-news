"""Compose the final 1080x1920 MP4: background footage + team tint + animated graphics + narration."""
import random
import subprocess
from pathlib import Path

from PIL import Image

from shorts import graphics as g
from lib.teams import SITE_URL
from shorts.broll import pick_clips
from shorts.photos import cartoon_style
from shorts.host import HEIGHT as HOST_HEIGHT, fit_clip, render_host

FPS = 30
_POP = [(0.0, 0.86), (0.05, 1.06), (0.10, 1.0)]
_CAPTION_Y, _MIDDLE_Y, _PROGRESS_Y = 1180, 520, 120
_PHOTO_HOOK_TOP, _PHOTO_CARD_Y, _PHOTO_CARD_MAX, _URL_Y = 640, 740, 420, 1400
_ZOOM = 0.07  # slow push-in on photos over each beat
_PUNCH = 0.16  # extra zoom at the mid-beat cut
# On a host beat: photo on top, host below the split, captions on the seam.
_SPLIT = 1920 - HOST_HEIGHT
_HOST_CAPTION_Y, _HOST_CARD_MAX, _HOST_URL_Y = _SPLIT - 100, 280, _SPLIT - 190
# which rows of a full-height photo frame land in the top part: the face sits above the (short) card, not behind it.
# Cartoon frames put the face higher (photos.CARTOON_FACE_Y), so they start nearer the top.
_HOST_PHOTO_TOP, _HOST_CARTOON_TOP = 200, 40


def _chunks(words: list[tuple[str, float, float]]) -> list[list[int]]:
    """Group a beat's words into caption lines of up to 3 words / ~16 characters."""
    out, cur = [], []
    for i, (w, _, _) in enumerate(words):
        if cur and (len(cur) == 3 or sum(len(words[j][0]) for j in cur) + len(w) > 16):
            out.append(cur)
            cur = []
        cur.append(i)
    return out + [cur] if cur else out


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def _background(timeline: list[dict], total: float, seed: str, team: str, photos: list[Path | None],
                workdir: Path, host_beats: frozenset = frozenset(), cartoon: bool = False,
                scenes: dict[int, Path] | None = None) -> Path:
    """One segment per beat: the beat's photo with a slow push-in, its own drawn scene (shorts.scenes, shown in full
    color), or tinted stadium footage. Host beats show the middle of the picture in the top part, above the split."""
    scenes = scenes or {}
    out = workdir / "bg.mp4"
    clips = pick_clips(len(timeline), seed, cartoon=cartoon)
    tint = workdir / "tint.png"
    g.tint_layer(team).save(tint)
    rnd = random.Random(seed)
    inputs, filters, n = [], [], 0
    for i, beat in enumerate(timeline):
        photo = photos[i] if i < len(photos) else None
        top = _HOST_CARTOON_TOP if photo and "-cartoon" in photo.name else _HOST_PHOTO_TOP
        fit = f",crop={g.W}:{_SPLIT}:0:{top},pad={g.W}:{g.H}:0:0" if i in host_beats else ""
        end = timeline[i + 1]["start"] if i + 1 < len(timeline) else total
        dur = end - beat["start"]
        frames = max(1, round(dur * FPS))
        if i in scenes:
            inputs += ["-stream_loop", "-1", "-t", f"{dur:.3f}", "-i", str(scenes[i])]
            filters.append(f"[{n}:v]scale={g.W}:{g.H}:force_original_aspect_ratio=increase,crop={g.W}:{g.H},setsar=1,"
                           f"fps={FPS},trim=duration={dur:.3f},setpts=PTS-STARTPTS{fit},format=yuv420p,setsar=1[v{i}]")
            n += 1
        elif photo:
            inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", str(photo)]
            # a picture held over 4 s gets a punch-in cut partway, so the frame changes every few seconds
            punch = f"+{_PUNCH}*gte(on,{round(frames * 0.45)})" if dur > 4 else ""
            filters.append(
                f"[{n}:v]scale={g.W * 2}:{g.H * 2},zoompan=z='1+{_ZOOM}*on/{frames}{punch}':x='iw/2-(iw/zoom/2)':"
                f"y='ih/2-(ih/zoom/2)':d=1:s={g.W}x{g.H}:fps={FPS}{fit},trim=duration={dur:.3f},setsar=1,"
                f"setpts=PTS-STARTPTS[v{i}]")
            n += 1
        elif clips:
            inputs += ["-stream_loop", "-1", "-ss", f"{rnd.uniform(0, 4):.2f}", "-t", f"{dur:.3f}", "-i", str(clips[i % len(clips)]),
                       "-loop", "1", "-t", f"{dur:.3f}", "-i", str(tint)]
            filters.append(
                f"[{n}:v]scale={g.W}:{g.H}:force_original_aspect_ratio=increase,crop={g.W}:{g.H},setsar=1,fps={FPS},"
                f"eq=saturation=0.55:brightness=-0.04,trim=duration={dur:.3f},setpts=PTS-STARTPTS[c{i}];"
                f"[c{i}][{n + 1}:v]overlay=0:0:shortest=1{fit},format=yuv420p,setsar=1[v{i}]")
            n += 2
        else:
            inputs += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", f"color=c=0x0b2a30:s={g.W}x{g.H}:r={FPS}"]
            filters.append(f"[{n}:v]noise=alls=8:allf=t,setsar=1[v{i}]")
            n += 1
    filters.append("".join(f"[v{i}]" for i in range(len(timeline))) + f"concat=n={len(timeline)}:v=1:a=0,format=yuv420p[bg]")
    _run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[bg]",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(out)])
    return out


def _graphics_frames(script: dict, timeline: list[dict], total: float, team: str, tag: str, photos: list[Path | None],
                     workdir: Path, host_beats: frozenset = frozenset()) -> Path:
    frames_dir = workdir / "frames"
    frames_dir.mkdir(exist_ok=True)
    brand = g.brand_tag(tag, team)
    has_photo = [bool(photos[i]) if i < len(photos) else False for i in range(len(timeline))]
    if has_photo[0]:
        big = g.big_hook(script["hook_text"], team)
        hook = (big, max(_PHOTO_HOOK_TOP, _CAPTION_Y - 20 - big.height))
    else:
        hook = (g.hook(script["hook_text"], team), _MIDDLE_Y)
    cards = {}
    for i, b in enumerate(script["beats"]):
        c = b.get("card")
        if not c:
            continue
        if c.get("kind") == "question":
            q = g.question_card(c.get("label") or "", c["value"], team)
            cards[i] = (q, _HOST_CAPTION_Y - q.height) if i in host_beats else (q, _MIDDLE_Y)
        elif i in host_beats:  # sits right above the captions so the photo's face stays clear
            card = g.card(c, team, _HOST_CARD_MAX)
            cards[i] = (card, _HOST_CAPTION_Y + 10 - card.height)
        elif has_photo[i]:
            cards[i] = (g.card(c, team, _PHOTO_CARD_MAX), _PHOTO_CARD_Y)
        else:
            cards[i] = (g.card(c, team), _MIDDLE_Y)
    url = g.url_tag(SITE_URL.removeprefix("https://").removeprefix("www."))
    chunks = [_chunks(beat["words"]) for beat in timeline]
    seam = Image.new("RGBA", (g.W, 8), (*g.THEMES[team]["accent"], 255))

    times = {0.0, total}
    for beat in timeline:
        times.update(beat["start"] + dt for dt, _ in _POP)
        times.update(s for _, s, _ in beat["words"])
        times.update(beat["end"] + 0.12 + k for k in range(beat.get("countdown") or 0))
    numbers = {}
    times = sorted(t for t in times if 0 <= t < total)

    caption_cache = {}
    lines = []
    for n, (a, b) in enumerate(zip(times, times[1:] + [total])):
        if b - a < 1 / FPS / 2:
            continue
        bi = max((i for i, beat in enumerate(timeline) if beat["start"] <= a + 1e-6), default=0)
        beat = timeline[bi]
        since = a - beat["start"]
        pop = next(f for dt, f in reversed(_POP) if since + 1e-6 >= dt)

        frame = Image.new("RGBA", (g.W, g.H), (0, 0, 0, 0))
        split = bi in host_beats
        caption_y = _HOST_CAPTION_Y if split else _CAPTION_Y
        if split:
            frame.alpha_composite(seam, (0, _SPLIT - 4))
        frame.alpha_composite(brand)
        frame.alpha_composite(g.progress(a / total, team), (0, _PROGRESS_Y))
        middle = hook if bi == 0 else cards.get(bi)
        if middle is not None:
            frame.alpha_composite(g.scaled(middle[0], pop), (0, middle[1]))
        if bi == len(timeline) - 1:
            frame.alpha_composite(url, (0, _HOST_URL_Y if split else _URL_Y))

        thinking = beat.get("countdown") and a >= beat["end"] + 0.12 - 1e-6
        if thinking:
            left = max(1, beat["countdown"] - int(a - beat["end"] - 0.12 + 1e-6))
            if left not in numbers:
                numbers[left] = g.countdown(left, team)
            frame.alpha_composite(numbers[left], (0, caption_y))
        else:
            spoken = [i for i, (_, s, _) in enumerate(beat["words"]) if s <= a + 1e-6]
            active = spoken[-1] if spoken else 0
            chunk = next(c for c in chunks[bi] if active in c)
            key = (bi, tuple(chunk), active)
            if key not in caption_cache:
                caption_cache[key] = g.caption([beat["words"][i][0] for i in chunk], chunk.index(active), team)
            frame.alpha_composite(caption_cache[key], (0, caption_y))

        name = f"f{n:04d}.png"
        frame.save(frames_dir / name, compress_level=1)
        lines.append(f"file 'frames/{name}'\nduration {b - a:.4f}\n")
    lines.append(lines[-1].split("\n")[0] + "\n")
    listing = workdir / "frames.txt"
    listing.write_text("".join(lines))
    return listing


def host_beat_spans(timeline: list[dict], total: float) -> list[tuple[int, float, float]]:
    """The beats the host is on screen for: the first line after the hook and the closing question (the bookends;
    a face matters most right after the hook and at the call to comment). [(beat index, start, end)]"""
    if len(timeline) < 2:
        return []
    picks = sorted({1, len(timeline) - 1})
    return [(i, timeline[i]["start"], timeline[i + 1]["start"] if i + 1 < len(timeline) else total) for i in picks]


def render(script: dict, timeline: list[dict], voice: Path, total: float, team: str, tag: str,
           workdir: Path, out: Path, photos: list[Path | None] = (), host: str | None = None,
           host_video: Path | None = None, scenes: dict[int, Path] | None = None) -> Path:
    """photos: per beat, a prepared 1080x1920 photo (graphics.photo_frame) or None for stadium footage.
    host: a shorts.host.HOSTS name to put a talking host under the split on the bookend beats (host_beat_spans).
    It is animated by P-Video when SHORTS_HOST_ENGINE=pvideo (within the monthly budget), else drawn here.
    host_video: an already-animated talking video of that host for the whole narration, to use instead.
    scenes: {beat: clip} drawn for this video (shorts.scenes), shown on beats that have no photo."""
    photos = list(photos)
    spans = host_beat_spans(timeline, total) if host else []
    clips: list[tuple[float, float, Path, float]] = []  # (start, end, video, the video's time offset)
    if spans:
        try:
            if host_video:
                full = fit_clip(host, host_video, total, workdir / "host.mp4")
                clips = [(s, e, full, 0.0) for _, s, e in spans]
            else:
                from shorts import avatar
                segments = avatar.animate(host, voice, spans, workdir) if avatar.enabled() else None
                if segments:
                    clips = [(s, e, path, s) for (s, e, path) in segments]
                else:
                    full = render_host(host, voice, total, workdir / "host.mp4", seed=tag, timeline=timeline,
                                       beats=script.get("beats") or [])
                    clips = [(s, e, full, 0.0) for _, s, e in spans]
        except Exception as e:  # a broken host must never cost us the video
            print(f"Host {host} failed, rendering without it: {e}")
            clips = []
    script["host"] = host if clips else ""
    host_beats = frozenset(i for i, _, _ in spans) if clips else frozenset()
    bg = _background(timeline, total, tag, team, photos, workdir, host_beats=host_beats,
                     cartoon=bool(host_beats) or cartoon_style(),
                     scenes=scenes)
    frames = _graphics_frames(script, timeline, total, team, tag, photos, workdir, host_beats=host_beats)
    inputs = ["-i", str(bg), "-f", "concat", "-safe", "0", "-i", str(frames), "-i", str(voice)]
    chain, last = [], "0:v"
    for k, (s, e, path, offset) in enumerate(clips):
        inputs += ["-itsoffset", f"{offset:.3f}", "-i", str(path)]
        chain.append(f"[{last}][{3 + k}:v]overlay=0:{_SPLIT}:eof_action=pass:enable='between(t,{s:.3f},{e:.3f})'[h{k}]")
        last = f"h{k}"
    graph = ";".join(chain + [f"[1:v]fps={FPS},format=rgba[ov];[{last}][ov]overlay=0:0:eof_action=repeat[v]"])
    _run([
        "ffmpeg", "-y", *inputs,
        "-filter_complex", graph,
        "-map", "[v]", "-map", "2:a", "-t", f"{total:.3f}", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out),
    ])
    return out
