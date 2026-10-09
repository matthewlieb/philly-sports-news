"""On-screen graphics, drawn with Pillow as transparent 1080x1920 frames.

Everything visual (hook title, stat/matchup cards, karaoke captions, progress bar, brand tag) is
rendered here so FFmpeg only has to composite images; no libass/drawtext build is required.
Key content stays inside the area Shorts/Reels UI doesn't cover (roughly y 140-1480, x 70-1010).
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FONT_DIR = Path(__file__).parent / "assets" / "fonts"
DISPLAY = str(FONT_DIR / "Anton-Regular.ttf")
SANS = str(FONT_DIR / "Montserrat.ttf")

THEMES = {
    "eagles": {"dark": (0, 52, 58), "accent": (105, 190, 40), "muted": (165, 172, 175)},
    "sixers": {"dark": (0, 43, 92), "accent": (237, 23, 76), "muted": (190, 200, 215)},
    "phillies": {"dark": (40, 45, 74), "accent": (232, 24, 40), "muted": (205, 205, 210)},
    "flyers": {"dark": (20, 20, 20), "accent": (247, 73, 2), "muted": (200, 200, 200)},
}


def _sans(size: int, weight: int = 800) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(SANS, size)
    try:
        font.set_variation_by_axes([weight])
    except Exception:
        pass
    return font


def _display(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(DISPLAY, size)


def _wrap(text: str, font, max_width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if font.getlength(trial) <= max_width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line] if line else lines


def _fit_display(text: str, max_width: int, max_lines: int, start: int, minimum: int):
    size = start
    while size > minimum:
        font = _display(size)
        lines = _wrap(text, font, max_width)
        if len(lines) <= max_lines and all(font.getlength(l) <= max_width for l in lines):
            return font, lines
        size -= 6
    font = _display(minimum)
    return font, _wrap(text, font, max_width)


def _shadowed(img: Image.Image, radius: int = 18, opacity: int = 150) -> Image.Image:
    """Soft drop shadow under an RGBA element, so text reads over any footage."""
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow.putalpha(img.getchannel("A").point(lambda a: a * opacity // 255))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius))
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.alpha_composite(shadow, (0, 8))
    out.alpha_composite(img)
    return out


def tint_layer(team: str) -> Image.Image:
    """Static team-colored wash over the background footage, darker toward the bottom for captions."""
    img = Image.new("RGBA", (W, H), (*THEMES[team]["dark"], 255))
    img.putalpha(Image.linear_gradient("L").resize((W, H)).point(lambda v: 150 + v * 70 // 255))
    return img


def brand_tag(label: str, team: str) -> Image.Image:
    theme = THEMES[team]
    font = _sans(36, 800)
    pad_x, h = 26, 64
    w = int(font.getlength(label)) + pad_x * 2
    img = Image.new("RGBA", (W, 240), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x0 = (W - w) // 2
    d.rounded_rectangle([x0, 150, x0 + w, 150 + h], radius=h // 2, fill=(*theme["accent"], 255))
    d.text((W // 2, 150 + h // 2), label, font=font, fill=(255, 255, 255), anchor="mm")
    return img


def _line_height(font) -> int:
    top, bottom = font.getbbox("ÁGJQ@", anchor="lt")[1::2]
    return bottom - top


def hook(text: str, team: str) -> Image.Image:
    """Opening title. Kept to 3 lines so it never reaches the caption area."""
    theme = THEMES[team]
    font, lines = _fit_display(text.upper(), 920, 3, 160, 84)
    line_h = int(_line_height(font) * 1.1)
    img = Image.new("RGBA", (W, line_h * len(lines) + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        color = theme["accent"] if i == len(lines) - 1 and len(lines) > 1 else (255, 255, 255)
        d.text((W // 2, i * line_h), line, font=font, fill=color, anchor="mt", stroke_width=4, stroke_fill=(0, 0, 0))
    return _shadowed(img)


MAX_CARD_HEIGHT = 600


def card(c: dict, team: str) -> Image.Image:
    """Label, big value, optional detail. Never taller than MAX_CARD_HEIGHT, so it can't reach the captions."""
    theme = THEMES[team]
    pw, pad = 900, 48
    label_font = _sans(42, 800)
    detail_font = _sans(44, 700)
    detail_lines = _wrap(c.get("detail") or "", detail_font, pw - pad * 2)[:2] if c.get("detail") else []
    start = 230
    while True:
        value_font, value_lines = _fit_display(c["value"].upper(), pw - pad * 2, 2, start, 90)
        value_line_h = int(_line_height(value_font) * 1.08)
        value_h = value_line_h * len(value_lines)
        ph = pad + 50 + 20 + value_h + (24 + 56 * len(detail_lines) if detail_lines else 0) + pad
        if ph <= MAX_CARD_HEIGHT or value_font.size <= 90:
            break
        start = value_font.size - 10
    img = Image.new("RGBA", (W, ph + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x0 = (W - pw) // 2
    d.rounded_rectangle([x0, 0, x0 + pw, ph], radius=36, fill=(*theme["dark"], 238))
    d.rounded_rectangle([x0, 0, x0 + pw, 14], radius=7, fill=(*theme["accent"], 255))
    y = pad + 4
    if c.get("label"):
        d.text((x0 + pad, y), c["label"].upper(), font=label_font, fill=theme["muted"])
    y += 50 + 20
    for line in value_lines:
        d.text((x0 + pad, y), line, font=value_font, fill=(255, 255, 255), anchor="lt")
        y += value_line_h
    y += 24
    for line in detail_lines:
        d.text((x0 + pad, y), line, font=detail_font, fill=(235, 240, 240))
        y += 56
    return _shadowed(img, radius=24, opacity=170)


def caption(words: list[str], active: int, team: str) -> Image.Image:
    """2-4 words with the one being spoken highlighted."""
    theme = THEMES[team]
    font = _display(112)
    big = _display(124)
    text = [w.upper() for w in words]
    space = font.getlength(" ")
    widths = [(big if i == active else font).getlength(w) for i, w in enumerate(text)]
    total = sum(widths) + space * (len(text) - 1)
    if total > 960:
        font, big = _display(int(112 * 960 / total)), _display(int(124 * 960 / total))
        space = font.getlength(" ")
        widths = [(big if i == active else font).getlength(w) for i, w in enumerate(text)]
        total = sum(widths) + space * (len(text) - 1)
    img = Image.new("RGBA", (W, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = (W - total) / 2
    for i, (w, wd) in enumerate(zip(text, widths)):
        f = big if i == active else font
        color = theme["accent"] if i == active else (255, 255, 255)
        d.text((x, 100), w, font=f, fill=color, anchor="lm", stroke_width=9, stroke_fill=(0, 0, 0))
        x += wd + space
    return _shadowed(img, radius=10, opacity=200)


def progress(fraction: float, team: str) -> Image.Image:
    img = Image.new("RGBA", (W, 12), (255, 255, 255, 60))
    ImageDraw.Draw(img).rectangle([0, 0, int(W * max(0.0, min(1.0, fraction))), 12], fill=(*THEMES[team]["accent"], 255))
    return img


def scaled(img: Image.Image, factor: float) -> Image.Image:
    """Scale an element about its center (used for the pop-in animation)."""
    if abs(factor - 1) < 1e-3:
        return img
    w, h = img.size
    s = img.resize((max(1, int(w * factor)), max(1, int(h * factor))), Image.LANCZOS)
    if factor > 1:
        left, top = (s.width - w) // 2, (s.height - h) // 2
        return s.crop((left, top, left + w, top + h))
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.alpha_composite(s, ((w - s.width) // 2, (h - s.height) // 2))
    return out
