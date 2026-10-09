"""Per-team settings shared by the site, the daily-brief job and the tweet bot."""

SITE_NAME = "Philly Sport Daily"
SITE_URL = "https://www.phillysportdaily.com"
X_HANDLE = "sport_philly"

TEAMS = {
    "eagles": {
        "slug": "eagles",
        "name": "Eagles",
        "full_name": "Philadelphia Eagles",
        "path": "/",
        "league": "NFL",
        "image": "phillySportsNewsEagles.png",
        "hashtag": "#FlyEaglesFly",
    },
    "sixers": {
        "slug": "sixers",
        "name": "Sixers",
        "full_name": "Philadelphia 76ers",
        "path": "/sixers",
        "league": "NBA",
        "image": "phillySportsNewsSixers.png",
        "hashtag": "#TTP",
    },
    "phillies": {
        "slug": "phillies",
        "name": "Phillies",
        "full_name": "Philadelphia Phillies",
        "path": "/phillies",
        "league": "MLB",
        "image": "phillySportsNewsPhillies.png",
        "hashtag": "#RingTheBell",
    },
    "flyers": {
        "slug": "flyers",
        "name": "Flyers",
        "full_name": "Philadelphia Flyers",
        "path": "/flyers",
        "league": "NHL",
        "image": "phillySportsNewsFlyers.png",
        "hashtag": "#LetsGoFlyers",
    },
}

TEAM_SLUGS = tuple(TEAMS)


def team_url(slug: str) -> str:
    return SITE_URL + TEAMS[slug]["path"]


def brief_path(slug: str, day: str) -> str:
    return f"/{slug}/brief/{day}"


def brief_url(slug: str, day: str) -> str:
    return SITE_URL + brief_path(slug, day)
