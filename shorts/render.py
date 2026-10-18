"""Compose the final 1080x1920 MP4: background footage + team tint + animated graphics + narration."""
import random
import subprocess
from pathlib import Path

from PIL import Image

from shorts import graphics as g
from lib.teams import SITE_URL
from shorts.broll import pick_clips

FPS = 30
_POP = [(0.0, 0.86), (0.05, 1.06), (0.10, 1.0)]
_CAPTION_Y, _MIDDLE_Y, _PROGRESS_Y = 1180, 520, 120
_PHOTO_HOOK_TOP, _PHOTO_CARD_Y, _PHOTO_CARD_MAX, _URL_Y = 640, 740, 420, 1400
_ZOOM = 0.07  # slow push-in on photos over each beat


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
                workdir: Path) -> Path:
    """One segment per beat: the beat's photo with a slow push-in, or tinted stadium footage when it has none."""
    out = workdir / "bg.mp4"
    clips = pick_clips(len(timeline), seed)
    tint = workdir / "tint.png"
    g.tint_layer(team).save(tint)
    rnd = random.Random(seed)
    inputs, filters, n = [], [], 0
    for i, beat in enumerate(timeline):
        end = timeline[i + 1]["start"] if i + 1 < len(timeline) else total
        dur = end - beat["start"]
        frames = max(1, round(dur * FPS))
        photo = photos[i] if i < len(photos) else None
        if photo:
            inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", str(photo)]
            filters.append(
                f"[{n}:v]scale={g.W * 2}:{g.H * 2},zoompan=z='1+{_ZOOM}*on/{frames}':x='iw/2-(iw/zoom/2)':"
                f"y='ih/2-(ih/zoom/2)':d=1:s={g.W}x{g.H}:fps={FPS},trim=duration={dur:.3f},setsar=1,"
                f"setpts=PTS-STARTPTS[v{i}]")
            n += 1
        elif clips:
            inputs += ["-stream_loop", "-1", "-ss", f"{rnd.uniform(0, 4):.2f}", "-t", f"{dur:.3f}", "-i", str(clips[i % len(clips)]),
                       "-loop", "1", "-t", f"{dur:.3f}", "-i", str(tint)]
            filters.append(
                f"[{n}:v]scale={g.W}:{g.H}:force_original_aspect_ratio=increase,crop={g.W}:{g.H},setsar=1,fps={FPS},"
                f"eq=saturation=0.55:brightness=-0.04,trim=duration={dur:.3f},setpts=PTS-STARTPTS[c{i}];"
                f"[c{i}][{n + 1}:v]overlay=0:0:shortest=1,format=yuv420p,setsar=1[v{i}]")
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
                     workdir: Path) -> Path:
    frames_dir = workdir / "frames"
    frames_dir.mkdir(exist_ok=True)
    brand = g.brand_tag(tag, team)
    has_photo = [bool(photos[i]) if i < len(photos) else False for i in range(len(timeline))]
    if has_photo[0]:
        big = g.big_hook(script["hook_text"], team)
        hook = (big, max(_PHOTO_HOOK_TOP, _CAPTION_Y - 20 - big.height))
    else:
        hook = (g.hook(script["hook_text"], team), _MIDDLE_Y)
    cards = {i: (g.card(b["card"], team, _PHOTO_CARD_MAX), _PHOTO_CARD_Y) if has_photo[i] else (g.card(b["card"], team), _MIDDLE_Y)
             for i, b in enumerate(script["beats"]) if b.get("card")}
    url = g.url_tag(SITE_URL.removeprefix("https://").removeprefix("www."))
    chunks = [_chunks(beat["words"]) for beat in timeline]

    times = {0.0, total}
    for beat in timeline:
        times.update(beat["start"] + dt for dt, _ in _POP)
        times.update(s for _, s, _ in beat["words"])
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
        frame.alpha_composite(brand)
        frame.alpha_composite(g.progress(a / total, team), (0, _PROGRESS_Y))
        middle = hook if bi == 0 else cards.get(bi)
        if middle is not None:
            frame.alpha_composite(g.scaled(middle[0], pop), (0, middle[1]))
        if bi == len(timeline) - 1:
            frame.alpha_composite(url, (0, _URL_Y))

        spoken = [i for i, (_, s, _) in enumerate(beat["words"]) if s <= a + 1e-6]
        active = spoken[-1] if spoken else 0
        chunk = next(c for c in chunks[bi] if active in c)
        key = (bi, tuple(chunk), active)
        if key not in caption_cache:
            caption_cache[key] = g.caption([beat["words"][i][0] for i in chunk], chunk.index(active), team)
        frame.alpha_composite(caption_cache[key], (0, _CAPTION_Y))

        name = f"f{n:04d}.png"
        frame.save(frames_dir / name, compress_level=1)
        lines.append(f"file 'frames/{name}'\nduration {b - a:.4f}\n")
    lines.append(lines[-1].split("\n")[0] + "\n")
    listing = workdir / "frames.txt"
    listing.write_text("".join(lines))
    return listing


def render(script: dict, timeline: list[dict], voice: Path, total: float, team: str, tag: str,
           workdir: Path, out: Path, photos: list[Path | None] = ()) -> Path:
    """photos: per beat, a prepared 1080x1920 photo (graphics.photo_frame) or None for stadium footage."""
    photos = list(photos)
    bg = _background(timeline, total, tag, team, photos, workdir)
    frames = _graphics_frames(script, timeline, total, team, tag, photos, workdir)
    _run([
        "ffmpeg", "-y", "-i", str(bg), "-f", "concat", "-safe", "0", "-i", str(frames), "-i", str(voice),
        "-filter_complex", f"[1:v]fps={FPS},format=rgba[ov];[0:v][ov]overlay=0:0:eof_action=repeat[v]",
        "-map", "[v]", "-map", "2:a", "-t", f"{total:.3f}", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out),
    ])
    return out
