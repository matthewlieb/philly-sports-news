"""Compose the final 1080x1920 MP4: background footage + team tint + animated graphics + narration."""
import random
import subprocess
from pathlib import Path

from PIL import Image

from shorts import graphics as g
from shorts.broll import pick_clips

FPS = 30
_POP = [(0.0, 0.86), (0.05, 1.06), (0.10, 1.0)]
_CAPTION_Y, _MIDDLE_Y, _PROGRESS_Y = 1180, 520, 120


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


def _background(timeline: list[dict], total: float, seed: str, workdir: Path) -> Path:
    out = workdir / "bg.mp4"
    clips = pick_clips(len(timeline), seed)
    if not clips:
        _run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=0x0b2a30:s={g.W}x{g.H}:r={FPS}:d={total:.2f}",
              "-vf", "noise=alls=8:allf=t", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(out)])
        return out
    rnd = random.Random(seed)
    inputs, filters = [], []
    for i, beat in enumerate(timeline):
        end = timeline[i + 1]["start"] if i + 1 < len(timeline) else total
        dur = end - beat["start"]
        inputs += ["-stream_loop", "-1", "-ss", f"{rnd.uniform(0, 4):.2f}", "-t", f"{dur:.3f}", "-i", str(clips[i % len(clips)])]
        filters.append(
            f"[{i}:v]scale={g.W}:{g.H}:force_original_aspect_ratio=increase,crop={g.W}:{g.H},setsar=1,fps={FPS},"
            f"eq=saturation=0.55:brightness=-0.04,trim=duration={dur:.3f},setpts=PTS-STARTPTS[v{i}]")
    filters.append("".join(f"[v{i}]" for i in range(len(timeline))) + f"concat=n={len(timeline)}:v=1:a=0[bg]")
    _run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[bg]",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(out)])
    return out


def _graphics_frames(script: dict, timeline: list[dict], total: float, team: str, tag: str, workdir: Path) -> Path:
    frames_dir = workdir / "frames"
    frames_dir.mkdir(exist_ok=True)
    brand = g.brand_tag(tag, team)
    hook = g.hook(script["hook_text"], team)
    cards = {i: g.card(b["card"], team) for i, b in enumerate(script["beats"]) if b.get("card")}
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
            frame.alpha_composite(g.scaled(middle, pop), (0, _MIDDLE_Y))

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
           workdir: Path, out: Path) -> Path:
    bg = _background(timeline, total, tag, workdir)
    tint = workdir / "tint.png"
    g.tint_layer(team).save(tint)
    frames = _graphics_frames(script, timeline, total, team, tag, workdir)
    _run([
        "ffmpeg", "-y", "-i", str(bg), "-loop", "1", "-i", str(tint), "-f", "concat", "-safe", "0", "-i", str(frames),
        "-i", str(voice),
        "-filter_complex",
        f"[0:v][1:v]overlay=0:0:shortest=1[b1];[2:v]fps={FPS},format=rgba[ov];[b1][ov]overlay=0:0:eof_action=repeat[v]",
        "-map", "[v]", "-map", "3:a", "-t", f"{total:.3f}", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out),
    ])
    return out
