"""Profile picture and YouTube banner for a team shorts account, in the same style as the videos.

  python scripts/make_brand_assets.py eagles ~/Desktop/eagles-brand
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shorts.graphics import THEMES, _display, _line_height, _sans  # noqa: E402
from lib.teams import TEAMS  # noqa: E402


def _field(size: tuple[int, int], team: str, line_gap: int) -> Image.Image:
    """Team-color gradient with faint yard lines."""
    w, h = size
    dark = THEMES[team]["dark"]
    base = Image.new("RGB", size, tuple(min(255, int(c * 1.5)) for c in dark))
    shade = Image.linear_gradient("L").resize(size).point(lambda v: 185 + v * 70 // 255)
    base = Image.composite(base, Image.new("RGB", size, (0, 0, 0)), shade)
    d = ImageDraw.Draw(base, "RGBA")
    for x in range(line_gap // 2, w, line_gap):
        d.line([(x, 0), (x, h)], fill=(255, 255, 255, 22), width=max(2, w // 400))
    return base


def profile(team: str) -> Image.Image:
    """1080x1080, everything inside the center circle that YouTube and Instagram crop to."""
    size, theme, name = 1080, THEMES[team], TEAMS[team]["name"].upper()
    img = _field((size, size), team, 135)
    d = ImageDraw.Draw(img)
    top, bottom = _display(250), _display(250)
    while top.getlength(name) > 760:
        top = _display(top.size - 10)
    h1, h2 = _line_height(top), _line_height(bottom)
    y = (size - (h1 + 30 + h2)) // 2 - 10
    d.text((size // 2, y), name, font=top, fill=(255, 255, 255), anchor="mt")
    d.text((size // 2, y + h1 + 30), "DAILY", font=bottom, fill=theme["accent"], anchor="mt")
    d.rounded_rectangle([size // 2 - 120, y + h1 + h2 + 70, size // 2 + 120, y + h1 + h2 + 86], radius=8,
                        fill=(255, 255, 255))
    return img


def banner(team: str) -> Image.Image:
    """2560x1440 YouTube banner; text kept in the 1546x423 center area visible on every device."""
    w, h, theme, name = 2560, 1440, THEMES[team], TEAMS[team]["name"].upper()
    img = _field((w, h), team, 160)
    d = ImageDraw.Draw(img)
    title, tag, site = _display(190), _sans(52, 700), _sans(40, 800)
    title_text = f"{name} DAILY"
    cy = h // 2
    d.text((w // 2, cy - 95), title_text, font=title, fill=(255, 255, 255), anchor="mm")
    accent_x = w // 2 + title.getlength(title_text) / 2 - title.getlength("DAILY")
    d.text((accent_x, cy - 95), "DAILY", font=title, fill=theme["accent"], anchor="lm")
    d.text((w // 2, cy + 50), f"Every {TEAMS[team]['name']} storyline in 30 seconds. New every morning.",
           font=tag, fill=(235, 240, 240), anchor="mm")
    d.rounded_rectangle([w // 2 - 300, cy + 115, w // 2 + 300, cy + 180], radius=32, fill=theme["accent"])
    d.text((w // 2, cy + 148), "PHILLYSPORTDAILY.COM", font=site, fill=(255, 255, 255), anchor="mm")
    return img


if __name__ == "__main__":
    team = sys.argv[1] if len(sys.argv) > 1 else "eagles"
    out = Path(sys.argv[2] if len(sys.argv) > 2 else ".").expanduser()
    out.mkdir(parents=True, exist_ok=True)
    profile(team).save(out / f"{team}-profile.png")
    banner(team).save(out / f"{team}-youtube-banner.png")
    print(f"Saved to {out}")
