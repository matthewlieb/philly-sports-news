# Satire image prompt config for @sport_philly.
# Tune these for DALL·E / image API style. Avoid depicting real people (use mascots, generic fans).
# See twitter_bot/docs/satire-images.md and twitter_bot/assets/images/README.md.

# Base style for Philly sports satire (religious iconography, painting style).
# Reference: eagles-qb-savior-satire.png, Saint Nick Foles.
DEFAULT_STYLE = (
    "Satirical oil painting in Renaissance religious iconography style, "
    "dramatic lighting, Philly sports meme aesthetic. "
    "Illustration style, not photorealistic. Avoid depicting real people (use mascots or generic symbols)."
)

# Team-specific visual hints (logo, mascot, colors).
TEAM_HINTS = {
    "eagles": "Eagles mascot or logo, green and silver, Philadelphia Eagles",
    "sixers": "76ers logo or mascot, red white blue, Philadelphia 76ers",
    "phillies": "Phillies logo or mascot, red white, Philadelphia Phillies",
    "flyers": "Flyers logo or mascot, orange black, Philadelphia Flyers",
}

def build_satire_prompt(headline: str, team: str) -> str:
    """Build a DALL·E prompt from headline and team."""
    team = (team or "").strip().lower()
    hint = TEAM_HINTS.get(team, "Philadelphia sports")
    # Keep headline short, avoid names that could trigger likeness issues
    clean_headline = (headline or "")[:60].strip()
    return f"{clean_headline}. {hint}. {DEFAULT_STYLE}"
